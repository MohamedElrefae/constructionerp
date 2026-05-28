"""Manual rollback for BOQ cascade fields.

This patch is intentionally not listed in patches.txt. Run manually only when
the BOQ cascade rollout must be disabled without deleting captured data.
"""

import frappe

CASCADE_FIELDS_TO_HIDE = (
    "expense_category",
    "boq_header",
    "boq_structure",
    "boq_item_stage",
    "boq_selection_scope_type",
    "designation",
)

CASCADE_DOCTYPES = (
    "Purchase Order Item",
    "Purchase Receipt Item",
    "Purchase Invoice Item",
    "Stock Entry Detail",
    "Timesheet Detail",
    "Journal Entry Account",
    "Sales Invoice Item",
    "Material Request Item",
)


def execute():
    for doctype in CASCADE_DOCTYPES:
        _hide_fields(doctype)

    _disable_rollout_flag()
    frappe.db.commit()
    frappe.clear_cache()


def _hide_fields(doctype):
    for fieldname in CASCADE_FIELDS_TO_HIDE:
        name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname}, "name")
        if not name:
            continue

        doc = frappe.get_doc("Custom Field", name)
        doc.hidden = 1
        doc.read_only = 1
        doc.depends_on = None
        doc.read_only_depends_on = None
        doc.save(ignore_permissions=True)
        frappe.clear_cache(doctype=doctype)


def _disable_rollout_flag():
    if not frappe.db.exists("DocType", "Construction Settings"):
        return
    if not frappe.get_meta("Construction Settings", cached=False).has_field("enable_boq_cascade_filtering"):
        return
    frappe.db.set_single_value("Construction Settings", "enable_boq_cascade_filtering", "Off")
