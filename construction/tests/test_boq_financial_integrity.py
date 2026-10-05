import frappe
from frappe.tests.utils import FrappeTestCase

from construction.tests.test_boq_helpers import get_or_create_test_project


def _make_header_with_items(title, item_specs):
    header = frappe.get_doc(
        {
            "doctype": "BOQ Header",
            "title": title,
            "project": get_or_create_test_project(),
            "status": "Draft",
            "boq_type": "Tender",
        }
    ).insert(ignore_permissions=True)
    items = []
    for spec in item_specs:
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": f"{title} - {spec['title']}",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        item = frappe.get_doc("BOQ Item", {"structure": structure.name})
        item.quantity = spec.get("quantity", 10)
        item.unit = spec.get("unit", "Nos")
        item.contract_unit_price = spec.get("rate", 100)
        if "factor" in spec:
            item.factor = spec["factor"]
        item.save(ignore_permissions=True)
        items.append(item)
    return header, items


class TestBoqFinancialIntegrity(FrappeTestCase):
    def setUp(self):
        super().setUp()
        frappe.db.sql("DELETE FROM `tabBOQ Quantity Revision` WHERE boq_header LIKE '%%G%%'")
        frappe.db.sql("DELETE FROM `tabBOQ Item` WHERE name LIKE '%%G%%'")
        frappe.db.sql("DELETE FROM `tabBOQ Structure` WHERE title LIKE '%%G%%'")
        frappe.db.sql("DELETE FROM `tabBOQ Header` WHERE title LIKE '%%G%%'")

    
    def test_g01_item_deletion_updates_header_totals(self):
        header, items = _make_header_with_items(
            "G01 Deletion Rollup",
            [
                {"title": "A", "quantity": 10, "rate": 10},
                {"title": "B", "quantity": 20, "rate": 10},
            ],
        )
        totals = frappe.db.get_value("BOQ Header", header.name, ["total_contract_value", "total_revised_value"], as_dict=True)
        self.assertEqual(frappe.utils.flt(totals.total_contract_value), 300)

        frappe.delete_doc("BOQ Item", items[0].name, ignore_permissions=True)
        totals = frappe.db.get_value("BOQ Header", header.name, ["total_contract_value"], as_dict=True)
        self.assertEqual(frappe.utils.flt(totals.total_contract_value), 200)

    def test_g01_delete_last_item_zeroes_totals(self):
        header, items = _make_header_with_items(
            "G01 Last Item", [{"title": "A", "quantity": 5, "rate": 100}]
        )
        frappe.delete_doc("BOQ Item", items[0].name, ignore_permissions=True)
        totals = frappe.db.get_value("BOQ Header", header.name, ["total_contract_value"], as_dict=True)
        self.assertEqual(frappe.utils.flt(totals.total_contract_value), 0)

    def test_g02_approved_revision_blocks_commercial_edits(self):
        header, items = _make_header_with_items("G02 Approved", [{"title": "A", "quantity": 100, "rate": 10}])
        item = items[0]
        # Set original_qty so that change_pct_from_contract stays <25%
        # and validate_revision_rules does not throw before validate_approval_integrity
        item.original_qty = 100
        item.save(ignore_permissions=True)

        revision = frappe.get_doc(
            {
                "doctype": "BOQ Quantity Revision",
                "boq_header": header.name,
                "boq_structure": item.structure,
                "boq_item": item.name,
                "revision_date": frappe.utils.nowdate(),
                "revision_type": "Increase Within 25%",
                "previous_qty": 100,
                "revised_qty": 100,
                "contract_unit_price": 10,
                "revised_unit_price": 10,
                "status": "Approved",
                "approved_by": frappe.session.user,
                "approved_on": frappe.utils.now(),
                "rate_change_justification": "Justification for approved revision review",
            }
        ).insert(ignore_permissions=True)

        # Attempt to change revised_qty after approval -> ValidationError
        rev_fail1 = frappe.get_doc("BOQ Quantity Revision", revision.name)
        rev_fail1.revised_qty = 110
        with self.assertRaises(frappe.ValidationError):
            rev_fail1.save(ignore_permissions=True)

        # Attempt to change revised_unit_price after approval -> ValidationError
        rev_fail2 = frappe.get_doc("BOQ Quantity Revision", revision.name)
        rev_fail2.revised_unit_price = 12
        with self.assertRaises(frappe.ValidationError):
            rev_fail2.save(ignore_permissions=True)

        # Unchanged commercial fields + metadata-only change is allowed
        rev_ok = frappe.get_doc("BOQ Quantity Revision", revision.name)
        rev_ok.reason = "Administrative note"
        rev_ok.save(ignore_permissions=True)
        self.assertEqual(rev_ok.status, "Approved")

    def test_g04_zero_or_negative_factor_rejected(self):
        header, items = _make_header_with_items("G04 Factor", [{"title": "A", "quantity": 10, "rate": 10}])
        item = items[0]
        item_fail1 = frappe.get_doc("BOQ Item", item.name)
        item_fail1.factor = 0
        with self.assertRaises(frappe.ValidationError):
            item_fail1.save(ignore_permissions=True)

        item_fail2 = frappe.get_doc("BOQ Item", item.name)
        item_fail2.factor = -2
        with self.assertRaises(frappe.ValidationError):
            item_fail2.save(ignore_permissions=True)

    def test_g04_missing_factor_defaults_to_one(self):
        header, items = _make_header_with_items("G04 Default", [{"title": "A", "quantity": 10, "rate": 10}])
        item = items[0]
        item.factor = None
        item.save(ignore_permissions=True)
        actual_factor = frappe.utils.flt(frappe.db.get_value("BOQ Item", item.name, "factor"))
        self.assertEqual(actual_factor, 1.0)
        line_total = frappe.utils.flt(frappe.db.get_value("BOQ Item", item.name, "line_total"))
        self.assertEqual(line_total, 100)
