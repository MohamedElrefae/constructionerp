import frappe
from frappe.tests.utils import FrappeTestCase

from construction.tests.test_boq_helpers import get_or_create_test_project


def run_boq_structure_conversion_smoke() -> dict:
    cleanup_boq_structure_conversion_smoke_records()
    header = _make_header()
    try:
        group = _make_structure(header.name, "Empty Group", is_group=1)
        group.convert_group_to_ledger()
        item_name = frappe.db.get_value("BOQ Item", {"structure": group.name}, "name")

        staged_leaf = _make_structure(header.name, "Staged Leaf", is_group=0)
        staged_item = frappe.get_doc(
            "BOQ Item",
            frappe.db.get_value("BOQ Item", {"structure": staged_leaf.name}, "name"),
        )
        staged_item.quantity = 10
        staged_item.has_stages = 1
        staged_item.save(ignore_permissions=True)
        stage = frappe.get_doc(
            {
                "doctype": "BOQ Item Stage",
                "boq_item": staged_item.name,
                "stage_code": "CONV-001",
                "stage_name": "Conversion Stage",
                "planned_qty": 10,
            }
        ).insert(ignore_permissions=True)

        blocked = False
        message = None
        try:
            staged_leaf.convert_ledger_to_group()
        except Exception as exc:
            blocked = True
            message = str(exc)

        return {
            "boq_header": header.name,
            "group_to_leaf": {
                "structure": group.name,
                "is_group": frappe.db.get_value("BOQ Structure", group.name, "is_group"),
                "boq_item_created": bool(item_name),
                "boq_item": item_name,
            },
            "leaf_to_group_block": {
                "structure": staged_leaf.name,
                "boq_item": staged_item.name,
                "stage": stage.name,
                "blocked": blocked,
                "message": message,
                "is_group_after": frappe.db.get_value("BOQ Structure", staged_leaf.name, "is_group"),
                "item_exists_after": bool(frappe.db.exists("BOQ Item", staged_item.name)),
            },
        }
    finally:
        cleanup_boq_structure_conversion_smoke_records()


def cleanup_boq_structure_conversion_smoke_records() -> dict:
    headers = frappe.get_all(
        "BOQ Header",
        filters={"title": "Test Structure Conversion"},
        pluck="name",
    )
    for header in headers:
        frappe.db.delete("BOQ Item Stage", {"boq_header": header})
        frappe.db.delete("BOQ Item", {"boq_header": header})
        frappe.db.delete("BOQ Structure", {"boq_header": header})
        frappe.db.delete("BOQ Header", {"name": header})
    frappe.db.commit()
    return {"deleted_headers": headers, "count": len(headers)}


class TestBOQStructureConversion(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_group_to_leaf_creates_boq_item(self):
        header = _make_header()
        group = _make_structure(header.name, "Empty Group", is_group=1)

        group.convert_group_to_ledger()

        self.assertFalse(group.is_group)
        self.assertTrue(frappe.db.exists("BOQ Item", {"structure": group.name}))


def _make_header():
    return frappe.get_doc(
        {
            "doctype": "BOQ Header",
            "title": "Test Structure Conversion",
            "project": get_or_create_test_project(),
            "status": "Draft",
            "boq_type": "Tender",
        }
    ).insert(ignore_permissions=True)


def _make_structure(header, title, is_group=0):
    return frappe.get_doc(
        {
            "doctype": "BOQ Structure",
            "boq_header": header,
            "title": title,
            "is_group": is_group,
        }
    ).insert(ignore_permissions=True)
