# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""
Patch: set_erpnext_standard_filters

Creates idempotent Property Setters that hide the `company` standard filter
on ERPNext transactional DocTypes commonly used by Construction workflows.

This prevents restricted users from triggering unauthorized `search_link`
calls against the Company DocType when list views load, while the
construction app's scope_context_list_filter.js continues to enforce scope
server-side.
"""

import frappe

ERPNEXT_STANDARD_FILTER_OVERRIDES = {
    # DocType -> {fieldname: {"in_standard_filter": 0}}
    "Sales Invoice": {"company": {"in_standard_filter": 0}},
    "Purchase Invoice": {"company": {"in_standard_filter": 0}},
    "Journal Entry": {"company": {"in_standard_filter": 0}},
    "Purchase Order": {"company": {"in_standard_filter": 0}},
    "Delivery Note": {"company": {"in_standard_filter": 0}},
    "Material Request": {"company": {"in_standard_filter": 0}},
    "Purchase Receipt": {"company": {"in_standard_filter": 0}},
}


def execute():
    """Entry point for bench migrate patch runner."""
    setup_erpnext_standard_filters()


def setup_erpnext_standard_filters():
    """Idempotently create/update Property Setters for ERPNext standard filters."""
    if not frappe.db.exists("DocType", "Property Setter"):
        return

    for doctype, fields in ERPNEXT_STANDARD_FILTER_OVERRIDES.items():
        if not frappe.db.exists("DocType", doctype):
            continue

        for fieldname, props in fields.items():
            if not frappe.db.exists("DocField", {"parent": doctype, "fieldname": fieldname}):
                continue

            for property_name, value in props.items():
                _ensure_property_setter(doctype, fieldname, property_name, value)


def _ensure_property_setter(doctype, fieldname, property_name, value):
    """Create or update a single Property Setter record."""
    existing = frappe.db.get_value(
        "Property Setter",
        {
            "doc_type": doctype,
            "field_name": fieldname,
            "property": property_name,
        },
        "name",
    )

    if existing:
        current_value = frappe.db.get_value("Property Setter", existing, "value")
        if current_value == str(value):
            return
        frappe.db.set_value("Property Setter", existing, "value", value)
    else:
        frappe.get_doc(
            {
                "doctype": "Property Setter",
                "doc_type": doctype,
                "doctype_or_field": "DocField",
                "field_name": fieldname,
                "property": property_name,
                "property_type": "Check",
                "value": str(value),
            }
        ).insert(ignore_permissions=True)
