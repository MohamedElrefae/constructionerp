import frappe
from frappe import _

from construction.services.boq_lookups import (
    get_header_for_item,
    get_project_for_header,
    get_quantity_state,
    get_status_for_header,
    is_omitted_boq_item,
)
from construction.services.boq_scope_filters import ALLOWED_TRANSACTION_BOQ_STATUSES


def _child_doctype_for(parent_doc, child_table_field):
    """Trusted child doctype for the parent's table field (registry/meta derived)."""
    if not parent_doc or not child_table_field:
        return None
    meta = getattr(parent_doc, "meta", None)
    if not meta or not meta.get_field(child_table_field):
        return None
    return meta.get_field(child_table_field).options


def is_new_or_changed_attribution(row, parent_doc=None, child_table_field=None):
    """True when this row's BOQ Item is being set for the first time or changed.

    Historical attribution must keep saving/submitting/cancelling after a later
    omission, so only newly attributed (or re-attributed) rows are refused.

    The historical exception is bound to the CURRENT parent: the persisted child
    row must belong to this parent document (parent / parenttype / parentfield,
    and the registry-derived child doctype) before its stored BOQ Item may be
    treated as an unchanged historical reference. A child row of another parent,
    a copied row identity, a not-yet-persisted parent, or a new child row never
    qualifies for the historical exception.
    """
    name = row.get("name")
    doctype = row.get("doctype")
    if not name or not doctype:
        return True

    child_doctype = _child_doctype_for(parent_doc, child_table_field)
    if child_doctype and doctype != child_doctype:
        return True

    if not frappe.db.exists(doctype, name):
        return True

    stored = frappe.db.get_value(
        doctype, name, ["boq_item", "parent", "parenttype", "parentfield"], as_dict=True
    )
    if not stored:
        return True

    parent_name = None
    parent_doctype = None
    if parent_doc is not None:
        if hasattr(parent_doc, "get"):
            parent_name = parent_doc.get("name")
            parent_doctype = parent_doc.get("doctype")
        else:
            parent_name = getattr(parent_doc, "name", None)
            parent_doctype = getattr(parent_doc, "doctype", None)

    if not parent_name or str(parent_name).startswith("new-"):
        # The parent itself is not persisted yet: nothing can be historical.
        return True

    if stored.parent != parent_name:
        return True
    if parent_doctype and stored.parenttype and stored.parenttype != parent_doctype:
        return True
    if child_table_field and stored.parentfield and stored.parentfield != child_table_field:
        return True

    return (stored.boq_item or "") != (row.get("boq_item") or "")


def validate_transaction_row(row, parent_doc, child_table_field=None):
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

    if is_new_or_changed_attribution(row, parent_doc, child_table_field) and is_omitted_boq_item(
        get_quantity_state(row.boq_item)
    ):
        frappe.throw(
            _("Row {0}: Omitted BOQ Item {1} cannot be newly attributed to this row.").format(
                row.idx, row.boq_item
            )
        )

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
