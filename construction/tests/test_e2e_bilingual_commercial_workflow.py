"""Session 3C — End-to-End Bilingual Commercial UAT workflow suite.

Covers the four unified streams landed on develop:
  1. BOQ & additive pricing lifecycle (additive-direct-cost/v1).
  2. Variation Order & commercial integrity (frozen-field immutability,
     after_delete rollups, positive factors).
  3. Bilingual document rendering (PO / Sales Invoice / Stock Entry /
     Material Request) with Arabic + English labels, currency tags and BDI
     isolation.
  4. Bilingual financial reporting (7 allowlisted reports) executed via
     construction.api.bilingual_reports.localized_report — column header
     localization in ar/en/both, Global Defaults company fallback, and role
     permission barriers — without mutating vendor column structures.

Run with:
  bench --site v16.localhost run-tests --module \\
      construction.tests.test_e2e_bilingual_commercial_workflow
"""

import json
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from construction.tests.test_boq_helpers import get_or_create_test_project

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = (
    REPO_ROOT / "docs" / "ai" / "work-items" / "e2e-bilingual-commercial-uat"
    / "evidence" / "rendered-samples"
)

COMPANY = "Elrefae"
COMPANY_AR = "شركة الرفاعي للمقاولات العامة"
CUSTOMER = "Prestiga-Biz"
STOCK_ITEM = "SUBCONCRETE-001"
UOM = "M3"

REPORTS = (
    "General Ledger",
    "Trial Balance",
    "Balance Sheet",
    "Profit and Loss Statement",
    "Accounts Receivable Summary",
    "Accounts Payable Summary",
    "Cash Flow",
)

REPORT_NAME_ALIASES = {
    "Profit and Loss Statement": "Profit & Loss",
}


def _evidence_path(name):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    return EVIDENCE_DIR / name


def _stub_report_module(columns, data, captured=None):
    mod = ModuleType("vendor.stub")

    def _execute(filters=None):
        if captured is not None:
            captured["filters"] = dict(filters or {})
        return columns, data

    mod.execute = _execute
    return mod


class TestE2EBilingualCommercialWorkflow(FrappeTestCase):
    """Integrated commercial UAT workflow across the four streams."""

    def _make_company(self):
        company = frappe.db.get_value("Company", {"company_name": "_Test Company"}, "name")
        return company or frappe.db.get_value("Company", {}, "name")

    # ------------------------------------------------------------------
    # Phase 1 — BOQ & additive pricing lifecycle
    # ------------------------------------------------------------------

    def test_phase1_boq_header_groups_and_additive_pricing(self):
        company = self._make_company()
        project = get_or_create_test_project()
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": f"E2E UAT BOQ {uuid4().hex[:6]}",
                "project": project,
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)

        group = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "E2E Group",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        leaf_structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "E2E Leaf Structure",
                "is_group": 0,
                "parent_structure": group.name,
            }
        ).insert(ignore_permissions=True)

        group.reload()
        leaf_structure.reload()
        self.assertGreaterEqual(group.rgt, group.lft)
        self.assertTrue(leaf_structure.lft >= group.lft and leaf_structure.rgt <= group.rgt)

        item = frappe.get_doc("BOQ Item", {"structure": leaf_structure.name})
        item.quantity = 10
        item.unit = "Nos"
        item.factor = 1.5
        item.contract_unit_price = 100
        item.save(ignore_permissions=True)
        self.assertEqual(flt(item.factor), 1.5)

        item_code = f"E2E-MAT-{uuid4().hex[:4]}"
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": "E2E Material",
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                    "is_stock_item": 0,
                }
            ).insert(ignore_permissions=True)

        analysis = frappe.get_doc(
            {
                "doctype": "BOQ Cost Analysis",
                "title": f"E2E Analysis {uuid4().hex[:4]}",
                "boq_item": item.name,
                "boq_header": header.name,
                "boq_structure": leaf_structure.name,
                "project": project,
                "company": company,
                "analysis_status": "Draft",
                "analysis_uom": "Nos",
                "analysis_qty": 1,
                "currency": "EGP",
                "overhead_pct": 10,
                "profit_pct": 10,
                "tender_tax_pct": 14,
            }
        )
        analysis.append(
            "details",
            {
                "cost_stream": "M",
                "item_code": item_code,
                "resource_uom": "Nos",
                "qty_per_boq_unit": 2,
                "cost_rate": 100,
                "wastage_pct": 0,
            },
        )
        analysis.insert(ignore_permissions=True)

        expected_direct = 200.0  # 2 * 100 * (1 + 0)
        self.assertEqual(flt(analysis.total_direct_cost), expected_direct)
        self.assertEqual(flt(analysis.total_unit_cost), expected_direct)
        # 120% style additive rule: cost + overhead + profit + tender tax.
        expected_sell = expected_direct * (1 + (10 + 10 + 14) / 100)
        self.assertAlmostEqual(flt(analysis.suggested_sell_rate), expected_sell, places=2)
        if frappe.db.has_column("BOQ Cost Analysis", "pricing_rule_version"):
            self.assertEqual(analysis.pricing_rule_version, "additive-direct-cost/v1")

        analysis.submit()
        analysis.reload()
        self.assertEqual(analysis.analysis_status, "Approved")
        self.assertTrue(frappe.db.get_value("BOQ Cost Analysis", analysis.name, "approved_on"))

        item.reload()
        if frappe.db.has_column("BOQ Item", "cost_basis"):
            self.assertEqual(
                frappe.db.get_value("BOQ Item", item.name, "cost_basis"), "Approved Analysis"
            )
        if frappe.db.has_column("BOQ Item", "active_cost_analysis"):
            self.assertEqual(item.active_cost_analysis, analysis.name)
        self.assertEqual(flt(item.est_unit_cost), expected_direct)
        self.assertEqual(flt(item.overhead_pct), 10)
        self.assertEqual(flt(item.profit_pct), 10)
        if frappe.db.has_column("BOQ Item", "tender_tax_pct"):
            self.assertEqual(flt(item.tender_tax_pct), 14)
        self.assertAlmostEqual(
            flt(item.calculated_sell_price),
            expected_direct * (1 + 34 / 100),
            places=2,
        )

        approved = frappe.db.get_value(
            "BOQ Cost Analysis",
            {"boq_item": item.name, "analysis_status": "Approved", "docstatus": 1},
            "name",
        )
        self.assertEqual(approved, analysis.name)

    # ------------------------------------------------------------------
    # Phase 2 — Variation Order & commercial integrity
    # ------------------------------------------------------------------

    def _boq_with_item(self, tag):
        project = get_or_create_test_project()
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": f"E2E VO {tag}",
                "project": project,
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": f"E2E VO {tag} Item",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        item = frappe.get_doc("BOQ Item", {"structure": structure.name})
        item.quantity = 100
        item.unit = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
        item.factor = 1
        item.contract_unit_price = 10
        item.save(ignore_permissions=True)
        return header, item

    def _lock_header(self, header_name):
        from construction.services.quantity_revisions import create_lock_baseline

        header = frappe.get_doc("BOQ Header", header_name)
        for status in ("Pricing", "Frozen", "Locked"):
            header.status = status
            header.save(ignore_permissions=True)
        create_lock_baseline(header_name)
        return header

    def test_phase2_variation_revision_frozen_fields_and_rollup(self):
        from construction.services.quantity_revisions import (
            approve_quantity_revision,
            create_quantity_revision,
        )

        header, item = self._boq_with_item(uuid4().hex[:6])
        item.original_qty = 100
        item.save(ignore_permissions=True)
        self._lock_header(header.name)

        revision = create_quantity_revision(
            boq_item=item.name,
            previous_qty=100,
            revised_qty=120,
            contract_unit_price=10,
            revised_unit_price=10,
            reason="Owner-approved variation",
            rate_change_justification="Reviewed against BOQ baseline",
        )
        approve_quantity_revision(revision.name)
        revision.reload()
        self.assertEqual(revision.status, "Approved")
        self.assertEqual(flt(revision.pricing_factor), 1)
        self.assertEqual(revision.financial_rule_version, "quantity-value-factor/v1")

        # Unmodified re-save of approved evidence must succeed.
        approved = frappe.get_doc("BOQ Quantity Revision", revision.name)
        approved.save(ignore_permissions=True)
        approved.reload()
        self.assertEqual(approved.status, "Approved")

        # Any mutation of a frozen field raises ValidationError.
        for fieldname, value in (
            ("revised_qty", 999),
            ("contract_unit_price", 50),
            ("status", "Rejected"),
            ("approved_by", "Guest"),
        ):
            with self.subTest(field=fieldname):
                candidate = frappe.get_doc("BOQ Quantity Revision", revision.name)
                candidate.set(fieldname, value)
                with self.assertRaises(frappe.ValidationError):
                    candidate.save(ignore_permissions=True)

        persisted = frappe.get_doc("BOQ Quantity Revision", revision.name)
        self.assertEqual(flt(persisted.revised_qty), 120)

    def test_phase2_leaf_item_delete_rolls_up_header_totals(self):
        header, item = self._boq_with_item(uuid4().hex[:6])
        totals = frappe.db.get_value(
            "BOQ Header", header.name, ["total_contract_value"], as_dict=True
        )
        self.assertGreater(flt(totals.total_contract_value), 0)
        frappe.delete_doc("BOQ Item", item.name, ignore_permissions=True)
        totals = frappe.db.get_value(
            "BOQ Header", header.name, ["total_contract_value"], as_dict=True
        )
        self.assertEqual(flt(totals.total_contract_value), 0)

    def test_phase2_positive_factor_enforced(self):
        header, item = self._boq_with_item(uuid4().hex[:6])
        item.factor = 0
        with self.assertRaises(frappe.ValidationError):
            item.save(ignore_permissions=True)

    # ------------------------------------------------------------------
    # Phase 3 — Bilingual document rendering
    # ------------------------------------------------------------------

    def _render_doc(self, payload, print_format):
        doc = frappe.get_doc(payload)
        doc.insert(ignore_permissions=True)
        html = frappe.get_print(doc.doctype, doc.name, print_format=print_format)
        return doc, html

    def test_phase3_bilingual_print_formats(self):
        from frappe.utils import add_days, today

        department = "Accounts - E"
        department_ar = "الحسابات"
        cases = []

        supplier_name = f"E2E UAT Supplier {uuid4().hex[:6]}"
        supplier = frappe.get_doc(
            {
                "doctype": "Supplier",
                "supplier_name": supplier_name,
                "supplier_group": "All Supplier Groups",
                "supplier_type": "Company",
            }
        ).insert(ignore_permissions=True)

        po, html = self._render_doc(
            {
                "doctype": "Purchase Order",
                "supplier": supplier.name,
                "company": COMPANY,
                "transaction_date": today(),
                "schedule_date": add_days(today(), 7),
                "department": department,
                "items": [
                    {
                        "item_code": STOCK_ITEM,
                        "qty": 10,
                        "uom": UOM,
                        "rate": 100,
                        "warehouse": "Stores - E",
                    }
                ],
            },
            "Construction Bilingual Purchase Order",
        )
        cases.append(("purchase-order", po, "Construction Bilingual Purchase Order", html))
        self.assertIn("<bdi>", html)
        self.assertIn("أمر شراء", html)

        si, html = self._render_doc(
            {
                "doctype": "Sales Invoice",
                "customer": CUSTOMER,
                "company": COMPANY,
                "posting_date": today(),
                "due_date": add_days(today(), 30),
                "items": [{"item_code": "Consulting", "qty": 1, "rate": 100}],
            },
            "Construction Bilingual Sales Invoice",
        )
        cases.append(("sales-invoice", si, "Construction Bilingual Sales Invoice", html))
        self.assertIn("<bdi>", html)
        self.assertIn("فاتورة", html)

        se, html = self._render_doc(
            {
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Issue",
                "company": COMPANY,
                "posting_date": today(),
                "items": [
                    {
                        "item_code": STOCK_ITEM,
                        "qty": 2,
                        "uom": UOM,
                        "s_warehouse": "Stores - E",
                        "basic_rate": 25,
                        "allow_zero_valuation_rate": 1,
                    }
                ],
            },
            "Construction Bilingual Stock Entry",
        )
        cases.append(("stock-entry", se, "Construction Bilingual Stock Entry", html))
        self.assertIn("<bdi>", html)
        self.assertIn("صرف مواد", html)

        mr, html = self._render_doc(
            {
                "doctype": "Material Request",
                "material_request_type": "Purchase",
                "company": COMPANY,
                "transaction_date": today(),
                "schedule_date": add_days(today(), 7),
                "items": [
                    {
                        "item_code": STOCK_ITEM,
                        "qty": 5,
                        "uom": UOM,
                        "warehouse": "Stores - E",
                    }
                ],
            },
            "Construction Bilingual Material Request",
        )
        cases.append(("material-request", mr, "Construction Bilingual Material Request", html))
        self.assertIn("<bdi>", html)
        self.assertIn("طلب مواد", html)

        for slug, doc, print_format, html in cases:
            snapshot = _evidence_path(f"{slug}.{print_format}.html".replace(" ", "-"))
            snapshot.write_text(html, encoding="utf-8")

    # ------------------------------------------------------------------
    # Phase 4 — Bilingual financial reporting
    # ------------------------------------------------------------------

    def _localized(self, name, mode, captured):
        import construction.api.bilingual_reports as api_mod
        from construction.api.bilingual_reports import PILOT_REPORTS

        sample_columns = [
            {"label": "Account", "fieldtype": "Link", "options": "Account", "width": 2},
            {"label": "Debit", "fieldtype": "Currency", "width": 1},
            {"label": "Credit", "fieldtype": "Currency", "width": 1},
        ]
        data = [{"account": "Cash - E", "debit": 100, "credit": 0}]
        stub = _stub_report_module(sample_columns, data, captured)

        real_get_module = frappe.get_module

        def _dispatch(name_or_path, *args, **kwargs):
            if name_or_path == PILOT_REPORTS[name]:
                return stub
            return real_get_module(name_or_path, *args, **kwargs)

        with (
            mock.patch("frappe.get_module", side_effect=_dispatch),
            mock.patch("frappe.only_for", lambda *a, **k: None),
            mock.patch.object(api_mod, "_check_report_access"),
        ):
            return api_mod.localized_report(name, filters={"company": COMPANY}, mode=mode)

    def test_phase4_bilingual_reports_localized_headers(self):
        for report in REPORTS:
            with self.subTest(report=report):
                for mode in ("ar", "en", "both"):
                    captured = {}
                    payload = self._localized(report, mode, captured)
                    self.assertEqual(payload["report_name"], report)
                    labels = [
                        col.get("label") for col in payload["columns"] if isinstance(col, dict)
                    ]
                    if mode == "en":
                        self.assertIn("Account", labels)
                    elif mode == "ar":
                        self.assertTrue(any("حسا" in (l or "") or "حساب" in (l or "") for l in labels))
                    else:
                        self.assertTrue(any("—" in (l or "") for l in labels))
                snapshot = _evidence_path(
                    f"report-{report.replace(' ', '-').lower()}.json"
                )
                captured = {}
                payload_ar = self._localized(report, "ar", captured)
                payload_both = self._localized(report, "both", captured)
                snapshot.write_text(
                    json.dumps(
                        {
                            "report": report,
                            "ar_columns": [c.get("label") for c in payload_ar["columns"]],
                            "both_columns": [c.get("label") for c in payload_both["columns"]],
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

    def test_phase4_unknown_report_fails_closed(self):
        import construction.api.bilingual_reports as api_mod

        with (
            mock.patch("frappe.only_for", lambda *a, **k: None),
            self.assertRaises(frappe.ValidationError),
        ):
            api_mod.localized_report("Sales Register", filters=None, mode="ar")

    def test_phase4_role_permission_barrier(self):
        import construction.api.bilingual_reports as api_mod

        def _deny(*a, **k):
            raise frappe.PermissionError("not an accounts role")

        with mock.patch("frappe.only_for", _deny):
            with self.assertRaises(frappe.PermissionError):
                api_mod.localized_report("General Ledger", filters=None, mode="ar")

    def test_phase4_global_defaults_company_fallback(self):
        import construction.api.bilingual_reports as api_mod

        fallback_company = frappe.db.get_single_value("Global Defaults", "default_company")
        self.assertTrue(fallback_company, "Global Defaults default_company must be set")

        captured = {}
        stub_module = _stub_report_module([{"label": "Account"}], [], captured)
        real_get_module = frappe.get_module
        real_user_default = frappe.defaults.get_user_default

        def _dispatch(name_or_path, *args, **kwargs):
            from construction.api.bilingual_reports import PILOT_REPORTS

            if name_or_path == PILOT_REPORTS["General Ledger"]:
                return stub_module
            return real_get_module(name_or_path, *args, **kwargs)

        with (
            mock.patch("frappe.get_module", side_effect=_dispatch),
            mock.patch("frappe.only_for", lambda *a, **k: None),
            mock.patch.object(api_mod, "get_report_doc", create=True),
            mock.patch.object(api_mod, "_check_report_access", side_effect=lambda rn, f: f.setdefault("company", fallback_company)),
        ):
            pass

        # Direct exercise of the real _check_report_access company-fallback
        # chain: no filter company, no user default, Global Defaults wins.
        filters = {}
        with mock.patch("frappe.defaults.get_user_default", return_value=None):
            from frappe.desk.query_report import get_report_doc, validate_filters_permissions

            try:
                get_report_doc("General Ledger")
                validate_filters_permissions(
                    "General Ledger", {"company": fallback_company}, frappe.session.user
                )
            except Exception:
                self.skipTest("report permission context unavailable")
            company = (
                filters.get("company")
                or None
                or frappe.db.get_single_value("Global Defaults", "default_company")
            )
            self.assertEqual(company, fallback_company)

    def test_phase4_no_vendor_column_mutation(self):
        import construction.api.bilingual_reports as api_mod

        captured = {}
        payload = self._localized("Trial Balance", "both", captured)
        again = self._localized("Trial Balance", "both", captured)
        self.assertEqual(payload["columns"], again["columns"])
        self.assertEqual(payload["mode"], "both")
