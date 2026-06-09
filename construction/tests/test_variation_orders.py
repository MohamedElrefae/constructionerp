import frappe
from frappe.tests.utils import FrappeTestCase

from construction.services.variation_orders import get_revised_boq_rows, get_revised_qty
from construction.services.boq_export_service import BOQExportService
from construction.tests.test_boq_helpers import get_or_create_test_project


class TestVariationOrders(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_variation_order_requires_locked_boq_header(self):
        header, item = self._make_boq_item("VO Lock Gate")

        vo = self._make_vo(header.name, item.name, delta_qty=2)
        with self.assertRaises(Exception):
            vo.insert(ignore_permissions=True)

        self._move_header_to_locked(header.name)
        vo = self._make_vo(header.name, item.name, delta_qty=2)
        vo.insert(ignore_permissions=True)
        self.assertEqual(vo.vo_number, "VO-001")

    def test_vo_numbering_is_sequential_per_boq_header(self):
        header, item = self._make_boq_item("VO Numbering A")
        other_header, other_item = self._make_boq_item("VO Numbering B")
        self._move_header_to_locked(header.name)
        self._move_header_to_locked(other_header.name)

        first = self._make_vo(header.name, item.name, delta_qty=1).insert(ignore_permissions=True)
        second = self._make_vo(header.name, item.name, delta_qty=1).insert(ignore_permissions=True)
        other = self._make_vo(other_header.name, other_item.name, delta_qty=1).insert(ignore_permissions=True)

        self.assertEqual(first.vo_number, "VO-001")
        self.assertEqual(second.vo_number, "VO-002")
        self.assertEqual(other.vo_number, "VO-001")

    def test_fidic_25_percent_rate_rule(self):
        header, item = self._make_boq_item("VO Rate Rule", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        within_limit = self._make_vo(header.name, item.name, delta_qty=25).insert(ignore_permissions=True)
        line = within_limit.lines[0]
        self.assertEqual(line.rate_change_triggered, 0)
        self.assertEqual(line.revised_unit_price, 50)

        over_limit = self._make_vo(header.name, item.name, delta_qty=26, revised_rate=60)
        with self.assertRaises(Exception):
            over_limit.insert(ignore_permissions=True)

        over_limit.lines[0].rate_change_justification = "Quantity changed beyond 25 percent."
        over_limit.insert(ignore_permissions=True)
        self.assertEqual(over_limit.lines[0].rate_change_triggered, 1)

    def test_client_approval_requires_signed_pdf_and_affects_revised_qty(self):
        header, item = self._make_boq_item("VO Revised Qty", quantity=100, rate=50)
        self._move_header_to_locked(header.name)
        vo = self._make_vo(header.name, item.name, delta_qty=10).insert(ignore_permissions=True)

        vo = self._approve_to_engineer(vo)
        with self.assertRaises(Exception):
            vo.status = "Approved by Client"
            vo.save(ignore_permissions=True)

        vo.reload()
        vo = self._approve_by_client(vo)

        self.assertEqual(get_revised_qty(item.name), 110)

    def test_revised_boq_view_and_export_tree_include_approved_vo_delta(self):
        header, item = self._make_boq_item("VO Revised BOQ View", quantity=100, rate=50)
        self._move_header_to_locked(header.name)
        vo = self._make_vo(header.name, item.name, delta_qty=10).insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        rows = get_revised_boq_rows(header.name)
        revised = next(row for row in rows if row["boq_item"] == item.name)
        self.assertEqual(revised["contract_qty"], 100)
        self.assertEqual(revised["vo_qty_delta"], 10)
        self.assertEqual(revised["revised_qty"], 110)
        self.assertEqual(revised["vo_value_delta"], 500)
        self.assertEqual(revised["revised_value"], 5500)

        tree = BOQExportService.get_tree_data(header.name)
        node = next(row for row in tree if row.get("items"))
        self.assertEqual(node["vo_qty_delta"], 10)
        self.assertEqual(node["revised_qty"], 110)
        self.assertEqual(node["vo_value_delta"], 500)
        self.assertEqual(node["revised_value"], 5500)

    def test_excel_export_includes_revised_boq_columns(self):
        import openpyxl

        header, item = self._make_boq_item("VO Export Revised Columns", quantity=100, rate=50)
        self._move_header_to_locked(header.name)
        vo = self._make_vo(header.name, item.name, delta_qty=10).insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        result = BOQExportService.export_to_excel(header.name)
        self.assertTrue(result["success"], result)

        path = frappe.get_site_path(result["file_url"].lstrip("/"))
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        headers = [ws.cell(row=5, column=col).value for col in range(1, ws.max_column + 1)]
        self.assertIn("VO Qty Delta", headers)
        self.assertIn("Revised Qty", headers)
        self.assertIn("VO Value Delta", headers)
        self.assertIn("Revised Value", headers)

        revised_qty_col = headers.index("Revised Qty") + 1
        revised_value_col = headers.index("Revised Value") + 1
        self.assertEqual(ws.cell(row=6, column=revised_qty_col).value, 110)
        self.assertEqual(ws.cell(row=6, column=revised_value_col).value, 5500)

    def test_pdf_export_accepts_revised_boq_columns(self):
        import os

        header, item = self._make_boq_item("VO PDF Revised Columns", quantity=100, rate=50)
        self._move_header_to_locked(header.name)
        vo = self._make_vo(header.name, item.name, delta_qty=10).insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        result = BOQExportService.export_to_pdf(header.name)
        self.assertTrue(result["success"], result)
        self.assertTrue(os.path.exists(frappe.get_site_path(result["file_url"].lstrip("/"))))

    def test_stage_distribution_uses_revised_quantity_after_approved_vo(self):
        header, item = self._make_boq_item("VO Stage Revised Qty", quantity=100, rate=50)
        self._move_header_to_locked(header.name)
        vo = self._make_vo(header.name, item.name, delta_qty=10).insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        stage = frappe.get_doc(
            {
                "doctype": "BOQ Item Stage",
                "boq_item": item.name,
                "stage_name": "Full revised distribution",
                "planned_qty": 110,
                "measured_executed_qty": 0,
                "certified_qty": 0,
            }
        )
        stage.insert(ignore_permissions=True)
        self.assertEqual(stage.planned_qty, 110)

    def test_new_item_creates_variation_boq_structure_and_item(self):
        header, _item = self._make_boq_item("VO New Item", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": header.name,
                "status": "Draft",
                "lines": [
                    {
                        "doctype": "VO Line",
                        "line_type": "New Item",
                        "title": "Additional excavation",
                        "unit": self._get_uom(),
                        "delta_qty": 12,
                        "revised_unit_price": 80,
                        "rate_change_justification": "New agreed item.",
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        vo = self._approve_by_client(self._approve_to_engineer(vo))

        vo.reload()
        line = vo.lines[0]
        self.assertTrue(line.created_boq_structure)
        self.assertTrue(line.created_boq_item)
        structure = frappe.get_doc("BOQ Structure", line.created_boq_structure)
        item = frappe.get_doc("BOQ Item", line.created_boq_item)
        self.assertEqual(structure.is_variation_item, 1)
        self.assertEqual(item.is_variation_item, 1)
        self.assertEqual(structure.wbs_code, "VO-001-01")
        self.assertEqual(item.quantity, 12)

    def test_omission_sets_revised_qty_to_zero(self):
        header, item = self._make_boq_item("VO Omission", quantity=20, rate=40)
        self._move_header_to_locked(header.name)

        vo = frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": header.name,
                "status": "Draft",
                "lines": [
                    {
                        "doctype": "VO Line",
                        "line_type": "Omission",
                        "boq_item": item.name,
                    }
                ],
            }
        ).insert(ignore_permissions=True)

        line = vo.lines[0]
        self.assertEqual(line.delta_qty, -20)
        self.assertEqual(line.revised_qty, 0)
        self.assertEqual(line.line_delta_value, -800)

    def _make_vo(self, header_name, item_name, delta_qty, revised_rate=None):
        line = {
            "doctype": "VO Line",
            "line_type": "Quantity Change",
            "boq_item": item_name,
            "delta_qty": delta_qty,
        }
        if revised_rate:
            line["revised_unit_price"] = revised_rate
        return frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": header_name,
                "status": "Draft",
                "lines": [line],
            }
        )

    def _approve_to_engineer(self, vo):
        vo.status = "Submitted"
        vo.save(ignore_permissions=True)
        vo.status = "Approved by Engineer"
        vo.save(ignore_permissions=True)
        vo.reload()
        return vo

    def _approve_by_client(self, vo):
        vo.status = "Approved by Client"
        vo.client_approval_document = "/private/files/signed-vo.pdf"
        vo.save(ignore_permissions=True)
        vo.reload()
        return vo

    def _make_boq_item(self, title, quantity=100, rate=50):
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": title,
                "project": get_or_create_test_project(),
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": f"{title} Item",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        item = frappe.get_doc("BOQ Item", {"structure": structure.name})
        item.quantity = quantity
        item.unit = self._get_uom()
        item.contract_unit_price = rate
        item.save(ignore_permissions=True)
        return header, item

    def _move_header_to_locked(self, header_name):
        header = frappe.get_doc("BOQ Header", header_name)
        for status in ("Pricing", "Frozen", "Locked"):
            header.status = status
            header.save(ignore_permissions=True)
        return header

    def _get_uom(self):
        return frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
