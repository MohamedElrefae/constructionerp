import frappe
from frappe.utils import flt


def effective_boq_quantity(item):
    """Canonical effective quantity of a BOQ Item row/document.

    Mirrors the VO-line rule (``vo_line.py``) and the link-query
    ``exclude_zero_revised`` filter (``COALESCE(current_revised_qty, quantity) > 0``):
    a NULL ``current_revised_qty`` means the item has never been revised, so the
    original contract quantity is effective. Returns a float; ``None``/missing
    rows yield ``0.0``.
    """
    if not item:
        return 0.0
    if hasattr(item, "get"):
        current_qty = item.get("current_revised_qty")
        original_qty = item.get("quantity")
    else:
        current_qty = getattr(item, "current_revised_qty", None)
        original_qty = getattr(item, "quantity", None)
    return flt(current_qty) if current_qty is not None else flt(original_qty)


def is_omitted_boq_item(item):
    """True when a BOQ Item is omitted (effective quantity <= 0) and no longer selectable."""
    return effective_boq_quantity(item) <= 0


def get_quantity_state(boq_item_name):
    return frappe.db.get_value("BOQ Item", boq_item_name, ["quantity", "current_revised_qty"], as_dict=True)


def get_header_for_item(boq_item_name):
    return frappe.db.get_value("BOQ Item", boq_item_name, "boq_header")


def get_project_for_header(boq_header_name):
    return frappe.db.get_value("BOQ Header", boq_header_name, "project")


def get_status_for_header(boq_header_name):
    return frappe.db.get_value("BOQ Header", boq_header_name, "status")


def get_stages_for_item(boq_item_name, exclude_name=None):
    filters = {"boq_item": boq_item_name, "docstatus": ["!=", 2]}
    if exclude_name:
        filters["name"] = ["!=", exclude_name]

    return frappe.get_all("BOQ Item Stage", filters=filters, fields=["name", "planned_qty"])
