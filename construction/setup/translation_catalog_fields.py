"""Custom fields on the core Translation DocType to support the catalog workbench.

These fields let the Construction app mirror every msgid from the Arabic .po
files as a Translation row, while keeping the runtime translation dict lean:
rows marked ``ct_is_catalog_entry = 1`` are excluded from the in-memory
``get_user_translations`` cache by the monkey-patch in ``construction.__init__``.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

CUSTOM_FIELDS = [
    {
        "dt": "Translation",
        "fieldname": "ct_is_catalog_entry",
        "label": "Catalog Entry",
        "fieldtype": "Check",
        "insert_after": "contributed",
        "read_only": 1,
        "in_list_view": 1,
        "in_standard_filter": 1,
        "search_index": 1,
        "description": "Auto-created from the app .po catalog. Excluded from runtime translation cache.",
        "owner": "Administrator",
    },
    {
        "dt": "Translation",
        "fieldname": "ct_app",
        "label": "App",
        "fieldtype": "Data",
        "insert_after": "ct_is_catalog_entry",
        "read_only": 1,
        "in_list_view": 1,
        "in_standard_filter": 1,
        "search_index": 1,
        "description": "Source app (frappe / erpnext / construction).",
        "owner": "Administrator",
    },
    {
        "dt": "Translation",
        "fieldname": "ct_po_translation",
        "label": "PO Translation",
        "fieldtype": "Code",
        "insert_after": "translated_text",
        "read_only": 1,
        "description": "Original Arabic translation from the .po catalog at last sync.",
        "owner": "Administrator",
    },
    {
        "dt": "Translation",
        "fieldname": "ct_review_status",
        "label": "Review Status",
        "fieldtype": "Select",
        "options": "\nPending\nApproved\nRejected",
        "insert_after": "ct_po_translation",
        "in_list_view": 1,
        "in_standard_filter": 1,
        "description": "Review state for catalog-sourced strings.",
        "owner": "Administrator",
    },
    {
        "dt": "Translation",
        "fieldname": "ct_catalog_synced_at",
        "label": "Catalog Synced At",
        "fieldtype": "Datetime",
        "insert_after": "ct_review_status",
        "read_only": 1,
        "owner": "Administrator",
    },
]


def ensure_custom_fields():
    """Idempotently create the Translation catalog custom fields."""
    for field in CUSTOM_FIELDS:
        try:
            create_custom_field(field["dt"], field, ignore_validate=True)
        except Exception:
            frappe.log_error(f"Failed to create custom field {field['fieldname']}", "Translation Catalog Setup")


def apply():
    """Run from patches / migrate."""
    ensure_custom_fields()
    frappe.db.commit()
