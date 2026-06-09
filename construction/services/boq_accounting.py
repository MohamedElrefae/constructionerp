import frappe
from frappe import _

from construction.services.boq_lookups import (
    get_header_for_item,
    get_project_for_header,
    get_status_for_header,
)
from construction.services.boq_scope_filters import ALLOWED_TRANSACTION_BOQ_STATUSES


def validate_transaction_row(row, parent_doc):
    if row.get("boq_item_stage") and not row.get("boq_item"):
        frappe.throw(_("Row {0}: BOQ Item Stage requires BOQ Item for BOQ attribution.").format(row.idx))

    if (row.get("boq_header") or row.get("boq_structure")) and not row.get("boq_item"):
        frappe.throw(
            _("Row {0}: BOQ attribution is incomplete. Select a BOQ Item or clear the BOQ fields.").format(
                row.idx
            )
        )

    if not row.get("boq_item"):
        return

    if not frappe.db.exists("BOQ Item", row.boq_item):
        frappe.throw(_("Row {0}: BOQ Item does not exist: {1}").format(row.idx, row.boq_item))

    boq_header = get_header_for_item(row.boq_item)
    boq_structure = frappe.db.get_value("BOQ Item", row.boq_item, "structure")
    if row.get("boq_header") != boq_header:
        row.boq_header = boq_header
    if row.get("boq_structure") != boq_structure:
        row.boq_structure = boq_structure

    header_status = get_status_for_header(boq_header)
    if header_status not in ALLOWED_TRANSACTION_BOQ_STATUSES:
        frappe.throw(
            _("Row {0}: BOQ Header {1} is {2}. Transaction attribution is allowed only for {3}.").format(
                row.idx,
                boq_header,
                header_status,
                ", ".join(ALLOWED_TRANSACTION_BOQ_STATUSES),
            )
        )

    boq_project = get_project_for_header(boq_header)
    row_project = getattr(parent_doc, "project", None) or row.get("project")
    if row_project and boq_project and row_project != boq_project:
        frappe.throw(
            _("Row {0}: Project mismatch. Transaction: {1}, BOQ: {2}").format(
                row.idx, row_project, boq_project
            )
        )

    if row.get("boq_item_stage"):
        stage_parent = frappe.db.get_value("BOQ Item Stage", row.boq_item_stage, "boq_item")
        if stage_parent != row.boq_item:
            frappe.throw(
                _("Row {0}: BOQ Item Stage {1} does not belong to selected BOQ Item {2}.").format(
                    row.idx,
                    row.boq_item_stage,
                    row.boq_item,
                )
            )
