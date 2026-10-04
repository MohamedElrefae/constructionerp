"""Real legacy preservation, reviewed conversion and cancellation recovery."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.services.boq_legacy_cost_conversion import (
    apply_legacy_cost_conversion,
    preview_legacy_cost_conversion,
)
from construction.tests import test_cost_analysis_engine as fixtures


class TestBOQLegacyCostConversion(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.fixture = fixtures.TestCostAnalysisEngine(methodName="test_single_component_analysis_rolls_up")
        self.fixture.setUp()
        self.item = self.fixture.item
        code = self.fixture._make_item_doctype("Legacy conversion material")
        details = [
            {
                "cost_stream": "M",
                "item_code": code,
                "resource_uom": "Nos",
                "qty_per_boq_unit": 1,
                "cost_rate": 100,
            }
        ]
        self.legacy = self.fixture._make_cost_analysis(self.item.name, details=details)
        self.legacy.overhead_pct = 10
        self.legacy.profit_pct = 10
        self.legacy.save(ignore_permissions=True)
        self.legacy.submit()
        # A fixture of the prior arithmetic/provenance, never a customer write.
        frappe.db.set_value(
            "BOQ Cost Analysis",
            self.legacy.name,
            {
                "pricing_rule_version": "legacy-unversioned/v0",
                "total_unit_cost": 121,
                "suggested_sell_rate": 146.41,
            },
            update_modified=False,
        )
        frappe.db.set_value(
            "BOQ Item",
            self.item.name,
            {
                "cost_basis": "Legacy Review",
                "active_cost_analysis": None,
                "manual_cost_snapshot": None,
                "est_unit_cost": 121,
            },
            update_modified=False,
        )
        self.item.reload()
        self.replacement = self.fixture._make_cost_analysis(self.item.name, details=details)
        self.replacement.overhead_pct = 10
        self.replacement.profit_pct = 10
        self.replacement.save(ignore_permissions=True)
        self.manual = {"est_unit_cost": 80, "overhead_pct": 5, "profit_pct": 10, "tender_tax_pct": 0}
        self.reason = "Reviewed supplier evidence and original manual estimate."

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def preview(self):
        return preview_legacy_cost_conversion(self.item.name, self.replacement.name, self.manual, self.reason)

    def apply(self, digest):
        return apply_legacy_cost_conversion(
            self.item.name, self.replacement.name, self.manual, self.reason, digest
        )

    def test_preview_is_read_only_and_bound_to_legacy_and_replacement(self):
        before = self.item.as_dict()
        old = self.legacy.reload().as_dict()
        preview = self.preview()
        self.assertEqual(preview["before_unit_cost"], 121)
        self.assertEqual(preview["after_unit_cost"], 100)
        self.assertEqual(preview["after_suggested_rate"], 120)
        self.assertEqual(self.item.reload().as_dict(), before)
        self.assertEqual(self.legacy.reload().as_dict(), old)
        self.assertEqual(self.preview()["inputs_digest"], preview["inputs_digest"])

    def test_conversion_preserves_legacy_amounts_and_cancellation_restores_reviewed_manual(self):
        old = self.legacy.reload().as_dict()
        result = self.apply(self.preview()["inputs_digest"])
        self.assertTrue(result["applied"])
        converted = self.item.reload()
        self.assertEqual(converted.cost_basis, "Approved Analysis")
        self.assertEqual(converted.est_unit_cost, 100)
        self.assertEqual(converted.calculated_sell_price, 120)
        self.assertEqual(converted.active_cost_analysis, self.replacement.name)
        legacy = self.legacy.reload().as_dict()
        for field in (
            "total_unit_cost",
            "suggested_sell_rate",
            "total_direct_cost",
            "approved_by",
            "approved_on",
            "docstatus",
            "pricing_rule_version",
        ):
            self.assertEqual(legacy[field], old[field])
        self.assertEqual(legacy["analysis_status"], "Superseded")
        self.replacement.reload().cancel()
        restored = self.item.reload()
        self.assertEqual(restored.cost_basis, "Manual")
        self.assertEqual(restored.est_unit_cost, 80)
        self.assertEqual(restored.calculated_sell_price, 92)
        snapshot = frappe.parse_json(restored.manual_cost_snapshot)
        self.assertEqual(snapshot["conversion"]["inputs_digest"], result["inputs_digest"])

    def test_changed_replacement_or_manual_evidence_requires_fresh_review(self):
        digest = self.preview()["inputs_digest"]
        self.manual["est_unit_cost"] = 90
        with self.assertRaises(frappe.ValidationError):
            self.apply(digest)
        self.assertEqual(self.item.reload().cost_basis, "Legacy Review")
        self.assertEqual(self.legacy.reload().analysis_status, "Approved")
        self.manual["est_unit_cost"] = 80
        self.replacement.details[0].cost_rate = 110
        self.replacement.save(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            self.apply(digest)

    def test_failure_after_native_submission_rolls_back_entire_conversion(self):
        digest = self.preview()["inputs_digest"]
        with patch.object(
            type(self.replacement), "add_comment", side_effect=RuntimeError("audit unavailable")
        ):
            with self.assertRaises(RuntimeError):
                self.apply(digest)
        self.assertEqual(self.item.reload().cost_basis, "Legacy Review")
        self.assertFalse(self.item.manual_cost_snapshot)
        self.assertEqual(self.legacy.reload().analysis_status, "Approved")
        self.assertEqual(self.replacement.reload().docstatus, 0)

    def test_incomplete_manual_basis_and_non_owner_are_refused(self):
        del self.manual["tender_tax_pct"]
        with self.assertRaises(frappe.ValidationError):
            self.preview()
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            self.preview()

    def test_same_review_cannot_be_applied_twice(self):
        digest = self.preview()["inputs_digest"]
        self.apply(digest)
        with self.assertRaises(frappe.ValidationError):
            self.apply(digest)
        self.assertEqual(self.item.reload().active_cost_analysis, self.replacement.name)

    def test_multiple_legacy_approvals_require_reconciliation(self):
        second = self.fixture._make_cost_analysis(
            self.item.name,
            details=[
                {
                    "cost_stream": "M",
                    "item_code": self.legacy.details[0].item_code,
                    "resource_uom": "Nos",
                    "qty_per_boq_unit": 1,
                    "cost_rate": 50,
                }
            ],
        )
        frappe.db.set_value(
            "BOQ Cost Analysis",
            second.name,
            {"docstatus": 1, "analysis_status": "Approved", "pricing_rule_version": "legacy-unversioned/v0"},
        )
        with self.assertRaises(frappe.ValidationError):
            self.preview()

    def test_replacement_for_another_item_is_refused(self):
        other = self.fixture._make_item(self.fixture.header.name, "Other conversion item")
        frappe.db.set_value("BOQ Cost Analysis", self.replacement.name, "boq_item", other.name)
        with self.assertRaises(frappe.ValidationError):
            self.preview()
