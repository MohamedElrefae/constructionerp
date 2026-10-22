"""Regressions against actual Frappe document lifecycles, not copied formulas."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.construction.utils.rollup import defer_boq_rollups
from construction.services.quantity_revisions import (
    approve_quantity_revision,
    create_lock_baseline,
    create_quantity_revision,
)
from construction.tests.test_boq_helpers import get_or_create_test_project


class TestCustomerReleaseFinancialGuards(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.delete("User Scope Context", {"user": "Administrator"})
        self.header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": "Release lifecycle regression",
                "project": get_or_create_test_project(),
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        self.group = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.header.name,
                "title": "Group",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        self.items = []
        for number, quantity in enumerate((3, 7)):
            structure = frappe.get_doc(
                {
                    "doctype": "BOQ Structure",
                    "boq_header": self.header.name,
                    "parent_structure": self.group.name,
                    "title": f"Leaf {number}",
                    "is_group": 0,
                }
            ).insert(ignore_permissions=True)
            item = frappe.get_doc("BOQ Item", {"structure": structure.name})
            item.quantity = quantity
            item.unit = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
            item.contract_unit_price = 10
            item.est_unit_cost = 4
            item.save(ignore_permissions=True)
            self.items.append(item)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def assert_totals(self, contract, count):
        self.header.reload()
        self.group.reload()
        self.assertEqual(self.header.total_contract_value, contract)
        self.assertEqual(self.group.total_contract_value, contract)
        self.assertEqual(self.group.item_count, count)
        # Compare each maintained financial aggregate with the real remaining
        # rows; this also covers the last-item-to-zero transition.
        expected = frappe.db.sql(
            """
            SELECT COALESCE(SUM(est_line_total), 0),
                   COALESCE(SUM(quantity * est_unit_cost * COALESCE(factor, 1)), 0),
                   COALESCE(SUM(COALESCE(current_revised_qty, quantity) *
                       COALESCE(current_revised_unit_price, contract_unit_price) * COALESCE(factor, 1)), 0)
            FROM `tabBOQ Item` WHERE boq_header = %s
        """,
            self.header.name,
        )[0]
        for field, value in zip(
            ("total_estimated_value", "total_budgeted_cost", "total_revised_value"), expected, strict=True
        ):
            self.assertAlmostEqual(float(self.header.get(field)), float(value), places=6)

    def test_direct_item_deletion_updates_header_and_structure(self):
        self.assert_totals(100, 2)
        frappe.delete_doc("BOQ Item", self.items[0].name)
        self.assert_totals(70, 1)
        frappe.delete_doc("BOQ Item", self.items[1].name)
        self.assert_totals(0, 0)

    def test_leaf_deletion_updates_remaining_totals(self):
        frappe.delete_doc("BOQ Structure", self.items[0].structure)
        self.assertFalse(frappe.db.exists("BOQ Item", self.items[0].name))
        self.assert_totals(70, 1)

    def test_deferred_batch_requires_and_accepts_explicit_flush(self):
        with defer_boq_rollups():
            for item in self.items:
                frappe.delete_doc("BOQ Item", item.name)
            self.header.reload()
            self.assertEqual(self.header.total_contract_value, 100)
        self.header.recalculate_phase1_totals()
        self.assert_totals(0, 0)

    def test_refused_linked_deletion_does_not_roll_up(self):
        create_lock_baseline(self.header.name)
        with patch.object(type(self.header), "recalculate_phase1_totals", autospec=True) as rollup:
            with self.assertRaises(frappe.LinkExistsError):
                frappe.delete_doc("BOQ Item", self.items[0].name)
            rollup.assert_not_called()
        self.assertTrue(frappe.db.exists("BOQ Item", self.items[0].name))
        self.assert_totals(100, 2)

    def _approved_revision(self):
        create_lock_baseline(self.header.name)
        return frappe.get_doc("BOQ Quantity Revision", self.items[0].reload().last_quantity_revision)

    def test_approved_commercial_and_attribution_fields_cannot_change(self):
        revision = self._approved_revision()
        for field, value in (
            ("revised_qty", 99),
            ("previous_qty", 88),
            ("revised_unit_price", 50),
            ("revised_unit_price", 10.001),
            ("contract_unit_price", 60),
            ("boq_item", self.items[1].name),
            ("reason", "Rewrite approval"),
            ("owner_ref_no", "Rewrite reference"),
            ("approved_on", "2020-01-01 00:00:00"),
            ("delta_value", 900),
            ("status", "Rejected"),
            ("status", "Draft"),
        ):
            with self.subTest(field=field):
                candidate = frappe.get_doc("BOQ Quantity Revision", revision.name)
                before = candidate.get(field)
                candidate.set(field, value)
                with self.assertRaises(frappe.ValidationError):
                    candidate.save(ignore_permissions=True)
                self.assertEqual(frappe.get_doc("BOQ Quantity Revision", revision.name).get(field), before)

    def test_approved_revision_cannot_be_deleted(self):
        revision = self._approved_revision()

        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("BOQ Quantity Revision", revision.name, ignore_permissions=True)

        self.assertTrue(frappe.db.exists("BOQ Quantity Revision", revision.name))

    def test_legacy_rejected_revision_with_approval_attribution_stays_frozen(self):
        revision = self._approved_revision()
        frappe.db.set_value("BOQ Quantity Revision", revision.name, "status", "Rejected")
        legacy = frappe.get_doc("BOQ Quantity Revision", revision.name)
        self.assertTrue(legacy.approved_by)
        self.assertTrue(legacy.approved_on)

        for field, value in (
            ("reason", "Rewrite legacy evidence"),
            ("approved_by", "Guest"),
            ("approved_on", "2020-01-01 00:00:00"),
            ("status", "Approved"),
        ):
            with self.subTest(field=field):
                candidate = frappe.get_doc("BOQ Quantity Revision", revision.name)
                candidate.set(field, value)
                with self.assertRaises(frappe.ValidationError):
                    candidate.save(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("BOQ Quantity Revision", revision.name, ignore_permissions=True)

        persisted = frappe.get_doc("BOQ Quantity Revision", revision.name)
        self.assertEqual(persisted.status, "Rejected")
        self.assertEqual(persisted.reason, revision.reason)
        self.assertEqual(persisted.approved_by, revision.approved_by)
        self.assertEqual(persisted.approved_on, revision.approved_on)

    def test_correction_is_recorded_as_a_new_approved_revision(self):
        approved = self._approved_revision()
        prior_evidence = {field: approved.get(field) for field in approved.APPROVAL_FROZEN_FIELDS}
        correction = create_quantity_revision(
            boq_item=approved.boq_item,
            previous_qty=approved.revised_qty,
            revised_qty=approved.revised_qty + 1,
            contract_unit_price=approved.contract_unit_price,
            revised_unit_price=approved.revised_unit_price,
            reason="Correct quantity through a new revision",
            rate_change_justification="Quantity change is reviewed against the original contract quantity.",
        )

        approve_quantity_revision(correction.name)

        approved.reload()
        correction.reload()
        self.assertEqual(approved.status, "Approved")
        self.assertEqual({field: approved.get(field) for field in prior_evidence}, prior_evidence)
        self.assertNotEqual(correction.name, approved.name)
        self.assertEqual(correction.status, "Approved")
        self.assertEqual(
            frappe.db.get_value("BOQ Item", approved.boq_item, "last_quantity_revision"), correction.name
        )
        self.assertEqual(
            frappe.db.get_value("BOQ Item", approved.boq_item, "current_revised_qty"), correction.revised_qty
        )

    def test_unchanged_approved_save_preserves_snapshot(self):
        revision = self._approved_revision()
        before = {field: revision.get(field) for field in revision.APPROVAL_FROZEN_FIELDS}
        # Simulate a later baseline adjustment: historical approval evidence
        # must remain the same even when today's BOQ projection changes.
        frappe.db.set_value("BOQ Item", revision.boq_item, "original_qty", 12)
        revision.save(ignore_permissions=True)
        revision.reload()
        self.assertEqual({field: revision.get(field) for field in before}, before)

    def test_direct_document_approval_projects_once_and_stamps_current_actor(self):
        original = self._approved_revision()
        correction = create_quantity_revision(
            boq_item=original.boq_item,
            previous_qty=original.revised_qty,
            revised_qty=original.revised_qty + 1,
            contract_unit_price=10,
            revised_unit_price=12,
            rate_change_justification="Reviewed correction",
        )
        correction.status = "Approved"
        correction.approved_by = "Guest"
        correction.approved_on = "2000-01-01 00:00:00"
        correction.save(ignore_permissions=True)
        self.assertEqual(correction.approved_by, "Administrator")
        self.assertNotEqual(str(correction.approved_on), "2000-01-01 00:00:00")
        self.assertEqual(self.items[0].reload().current_revised_qty, 4)
        self.assertEqual(self.header.reload().total_revised_value, 118)
        correction.save(ignore_permissions=True)
        self.assertEqual(self.header.reload().total_revised_value, 118)

    def test_old_approval_and_draft_cannot_replace_current_projection(self):
        from construction.services.quantity_revisions import apply_approved_revision

        original = self._approved_revision()
        correction = create_quantity_revision(
            boq_item=original.boq_item,
            previous_qty=3,
            revised_qty=4,
            contract_unit_price=10,
            revised_unit_price=12,
            rate_change_justification="Reviewed correction",
        )
        with self.assertRaises(frappe.ValidationError):
            apply_approved_revision(correction)
        approve_quantity_revision(correction.name)
        with self.assertRaises(frappe.ValidationError):
            apply_approved_revision(original)
        self.assertEqual(self.items[0].reload().last_quantity_revision, correction.name)
        self.assertEqual(self.header.reload().total_revised_value, 118)

    def test_stale_correction_and_forged_baseline_are_rejected(self):
        original = self._approved_revision()
        correction = create_quantity_revision(
            boq_item=original.boq_item,
            previous_qty=1,
            revised_qty=4,
            contract_unit_price=10,
            revised_unit_price=12,
            rate_change_justification="Stale correction",
        )
        with self.assertRaises(frappe.ValidationError):
            approve_quantity_revision(correction.name)
        self.assertEqual(correction.reload().status, "Draft")
        forged = frappe.get_doc(
            {
                "doctype": "BOQ Quantity Revision",
                "boq_item": original.boq_item,
                "boq_header": original.boq_header,
                "boq_structure": original.boq_structure,
                "revision_type": "Original Lock",
                "status": "Approved",
                "previous_qty": 0,
                "revised_qty": 3,
                "contract_unit_price": 10,
                "revised_unit_price": 10,
                "revision_date": frappe.utils.nowdate(),
            }
        )
        with self.assertRaises(frappe.ValidationError):
            forged.insert(ignore_permissions=True)
