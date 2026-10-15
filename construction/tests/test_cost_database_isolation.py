"""F18: cost-database shared-master isolation and company enforcement regressions."""

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.services.cost_database_service import import_cost_database_from_excel


def _wb(resources, templates=None, rates=None):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Resources"
    ws.append(
        [
            "resource_code", "name_en", "name_ar", "resource_type", "cost_stream", "uom",
            "unit_price_egp", "currency", "exchange_rate", "company", "region", "price_date",
            "source_name", "supplier", "remarks",
        ]
    )
    for row in resources:
        ws.append(row)
    wt = wb.create_sheet("BOQItemTemplates")
    wt.append(
        ["template_name", "description_en", "description_ar", "category", "uom",
         "overhead_pct", "profit_pct", "tender_tax_pct", "currency"]
    )
    for row in templates or []:
        wt.append(row)
    wr = wb.create_sheet("RateAnalysis")
    wr.append(
        ["template_name", "resource_code", "qty_per_boq_unit", "wastage_pct", "cost_stream",
         "cost_rate", "rate_source", "supplier", "remarks"]
    )
    for row in rates or []:
        wr.append(row)
    import io

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _res(code, name="Res", company="", rtype="Material", stream="M", uom="Nos", price=10):
    return [code, name, "", rtype, stream, uom, price, "EGP", 1, company, "", "2026-10-01", "F18", "", ""]


class TestCostDatabaseIsolation(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        if not frappe.db.exists("Item", "F18-COMPAT"):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": "F18-COMPAT",
                    "item_name": "F18 compatible",
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                    "is_stock_item": 0,
                    "is_construction_resource": 1,
                    "construction_resource_type": "Material",
                    "default_cost_stream": "M",
                }
            ).insert(ignore_permissions=True)

    def _import(self, content, company="_Test Company", dry_run=True):
        return import_cost_database_from_excel(
            file_content=content, file_name="f18.xlsx", company=company, dry_run=dry_run
        )

    def test_compatible_item_reused_unchanged(self):
        out = self._import(
            _wb([["F18-COMPAT", "F18 compatible", "", "Material", "M", "Nos", 12, "EGP", 1, "", "", "2026-10-01", "F18", "", ""]]),
            dry_run=False,
        )
        self.assertTrue(out["success"], out["errors"])
        doc = frappe.get_doc("Item", "F18-COMPAT")
        self.assertEqual(doc.item_name, "F18 compatible")
        self.assertEqual(doc.stock_uom, "Nos")

    def test_conflicting_name_refused(self):
        content = _wb([["F18-COMPAT", "Different name", "", "Material", "M", "Nos", 12, "EGP", 1, "", "", "2026-10-01", "F18", "", ""]])
        preview = self._import(content, dry_run=True)
        self.assertFalse(preview["success"])
        self.assertTrue(any("conflicts" in e for e in preview["errors"]), preview["errors"])
        committed = self._import(content, dry_run=False)
        self.assertFalse(committed["success"])
        self.assertEqual(frappe.db.get_value("Item", "F18-COMPAT", "item_name"), "F18 compatible")

    def test_non_construction_item_refused(self):
        code = "_Test Extra Item 1"  # live ERPNext item, not a construction resource
        content = _wb([[code, "Hijack attempt", "", "Material", "M", "Nos", 12, "EGP", 1, "", "", "2026-10-01", "F18", "", ""]])
        before = frappe.get_doc("Item", code).item_name
        out = self._import(content, dry_run=False)
        self.assertFalse(out["success"])
        self.assertTrue(any("conflicts" in e for e in out["errors"]), out["errors"])
        self.assertEqual(frappe.get_doc("Item", code).item_name, before)
        self.assertFalse(frappe.get_doc("Item", code).get("is_construction_resource"))

    def test_row_company_mismatch_refused(self):
        content = _wb([["F18-X1", "X", "", "Material", "M", "Nos", 10, "EGP", 1, "Elrefae", "", "2026-10-01", "F18", "", ""]])
        for dry in (True, False):
            out = self._import(content, company="_Test Company", dry_run=dry)
            self.assertFalse(out["success"])
            self.assertTrue(any("does not match import company" in e for e in out["errors"]), out["errors"])
        self.assertFalse(frappe.db.exists("Item", "F18-X1"))

    def test_preview_lists_proposed_creates(self):
        content = _wb([["F18-NEWPROP", "New prop", "", "Material", "M", "Nos", 10, "EGP", 1, "", "", "2026-10-01", "F18", "", ""]])
        out = self._import(content, dry_run=True)
        self.assertTrue(out["success"], out["errors"])
        self.assertIn("F18-NEWPROP", (out.get("proposed_creates") or {}).get("items", []))
        self.assertFalse(frappe.db.exists("Item", "F18-NEWPROP"))
