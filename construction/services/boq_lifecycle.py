import frappe
from frappe import _
from frappe.utils import flt

TRANSACTION_CHILD_DOCTYPES = (
    "Purchase Order Item",
    "Purchase Receipt Item",
    "Purchase Invoice Item",
    "Stock Entry Detail",
    "Timesheet Detail",
    "Journal Entry Account",
    "Sales Invoice Item",
    "Material Request Item",
)


def before_delete_boq_item_stage(doc, method=None):
    if doc.stage_status == "Certified" or flt(doc.certified_qty) > 0:
        frappe.throw(
            _("Cannot delete certified BOQ Item Stage {0}. Create an adjustment stage instead.").format(
                doc.name
            )
        )

    for doctype in TRANSACTION_CHILD_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        if not frappe.get_meta(doctype).has_field("boq_item_stage"):
            continue
        if frappe.db.exists(doctype, {"boq_item_stage": doc.name}):
            frappe.throw(
                _("Cannot delete BOQ Item Stage {0}: it is referenced by {1}").format(doc.name, doctype)
            )


def before_delete_boq_structure(doc, method=None):
    validate_boq_structure_leaf_delete_safety(doc)


def validate_boq_structure_leaf_delete_safety(doc):
    if doc.is_group:
        return

    item_name = frappe.db.get_value("BOQ Item", {"structure": doc.name}, "name")
    if not item_name:
        return

    if frappe.db.exists("BOQ Item Stage", {"boq_item": item_name}):
        frappe.throw(
            _("Cannot delete BOQ Structure {0}: linked BOQ Item {1} has stages.").format(doc.name, item_name)
        )

    for doctype in TRANSACTION_CHILD_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue

        meta = frappe.get_meta(doctype)
        if meta.has_field("boq_item") and frappe.db.exists(doctype, {"boq_item": item_name}):
            frappe.throw(
                _("Cannot delete BOQ Structure {0}: linked BOQ Item {1} is referenced by {2}.").format(
                    doc.name, item_name, doctype
                )
            )

        if meta.has_field("boq_structure") and frappe.db.exists(doctype, {"boq_structure": doc.name}):
            frappe.throw(
                _("Cannot delete BOQ Structure {0}: it is referenced by {1}.").format(doc.name, doctype)
            )
