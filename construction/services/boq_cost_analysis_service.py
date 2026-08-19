import frappe
from frappe import _
from frappe.utils import flt


def get_approved_analysis_for_boq_item(boq_item):
    """Get the approved BOQ Cost Analysis for a BOQ Item.
    
    Returns the doc or None.
    """
    name = frappe.db.get_value(
        "BOQ Cost Analysis",
        {
            "boq_item": boq_item,
            "analysis_status": "Approved",
            "docstatus": 1,
        },
        "name",
    )
    if name:
        return frappe.get_doc("BOQ Cost Analysis", name)
    return None


def get_approved_analysis_total_direct_cost(boq_item):
    """Get the total_direct_cost from the approved analysis for a BOQ Item."""
    name = frappe.db.get_value(
        "BOQ Cost Analysis",
        {
            "boq_item": boq_item,
            "analysis_status": "Approved",
            "docstatus": 1,
        },
        "name",
    )
    if name:
        return flt(frappe.db.get_value("BOQ Cost Analysis", name, "total_unit_cost"))
    return None


def refresh_boq_header_budget_totals(boq_header):
    """Refresh BOQ Header budget totals after cost analysis changes."""
    if not boq_header:
        return
    header = frappe.get_doc("BOQ Header", boq_header)
    header.recalculate_phase1_totals()
