import frappe
from frappe.tests.utils import FrappeTestCase

from construction.services.boq_lifecycle import validate_boq_structure_leaf_delete_safety
from construction.tests.test_boq_helpers import get_or_create_test_project


def run_boq_structure_delete_safety_smoke() -> dict:
    row = frappe.db.sql(
        """
        select mri.boq_structure, mri.boq_item, mri.parent as material_request
        from `tabMaterial Request Item` mri
        where ifnull(mri.boq_structure, '') != ''
          and ifnull(mri.boq_item, '') != ''
        limit 1
        """,
        as_dict=True,
    )
    if not row:
        frappe.throw("No BOQ-linked Material Request Item found for delete safety smoke.")

    row = row[0]
    structure_exists_before = bool(frappe.db.exists("BOQ Structure", row.boq_structure))
    item_exists_before = bool(frappe.db.exists("BOQ Item", row.boq_item))

    blocked = False
    message = None
    try:
        frappe.delete_doc("BOQ Structure", row.boq_structure, ignore_permissions=True)
    except Exception as exc:
        blocked = True
        message = str(exc)
        frappe.db.rollback()

    return {
        "material_request": row.material_request,
        "boq_structure": row.boq_structure,
        "boq_item": row.boq_item,
        "blocked": blocked,
        "message": message,
        "structure_exists_before": structure_exists_before,
        "item_exists_before": item_exists_before,
        "structure_exists_after": bool(frappe.db.exists("BOQ Structure", row.boq_structure)),
        "item_exists_after": bool(frappe.db.exists("BOQ Item", row.boq_item)),
    }


class TestBOQStructureDeleteSafety(FrappeTestCase):
    def test_leaf_with_stage_is_blocked_before_delete(self):
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": "Test Delete Safety",
                "project": get_or_create_test_project(),
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Delete Safety Leaf",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        item = frappe.get_doc(
            "BOQ Item",
            frappe.db.get_value("BOQ Item", {"structure": structure.name}, "name"),
        )
        item.quantity = 10
        item.has_stages = 1
        item.save(ignore_permissions=True)
        frappe.get_doc(
            {
                "doctype": "BOQ Item Stage",
                "boq_item": item.name,
                "stage_code": "DEL-001",
                "stage_name": "Delete Safety Stage",
                "planned_qty": 10,
            }
        ).insert(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            validate_boq_structure_leaf_delete_safety(structure)
