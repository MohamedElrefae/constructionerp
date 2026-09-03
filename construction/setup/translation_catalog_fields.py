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
        "in_list_view": 1,
        "in_standard_filter": 1,
        "search_index": 1,
        "description": "Provenance only (frappe / erpnext / construction). NOT part of the runtime key — a blank value does not prevent a translation from applying. Editable for manually created rows.",
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
        "options": "\nPending\nLinguistic Reviewed\nDomain Reviewed\nQA Passed\nReleased\nRejected\nReverted\nDeprecated\nApproved",
        "insert_after": "ct_po_translation",
        "in_list_view": 1,
        "in_standard_filter": 1,
        "description": "Review state for catalog-sourced strings. Pending→Linguistic Reviewed→Domain Reviewed→QA Passed→Released; any→Rejected; Released→Reverted|Deprecated.",
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
    {
        "dt": "Translation",
        "fieldname": "ct_key_digest",
        "label": "Translation Key Digest",
        "fieldtype": "Data",
        "insert_after": "ct_catalog_synced_at",
        "read_only": 1,
        "in_standard_filter": 1,
        "search_index": 1,
        "description": "SHA-256 of [language, source_text, context, app/catalog or runtime]. Enforced UNIQUE.",
        "owner": "Administrator",
    },
    {
        "dt": "Translation",
        "fieldname": "ct_search_normalized",
        "label": "Search Normalized",
        "fieldtype": "Small Text",
        "insert_after": "ct_key_digest",
        "read_only": 1,
        "description": "strip_html_tags(source_text).strip() — search only, never a runtime key.",
        "owner": "Administrator",
    },
    {
        "dt": "Translation",
        "fieldname": "ct_proposed_translation",
        "label": "Proposed Translation",
        "fieldtype": "Code",
        "insert_after": "ct_search_normalized",
        "description": "Unreleased reviewer proposal; runtime unchanged until Released.",
        "owner": "Administrator",
    },
    {
        "dt": "Translation",
        "fieldname": "ct_origin",
        "label": "Origin",
        "fieldtype": "Select",
        "options": "\nPackaged Release\nSite Override",
        "insert_after": "ct_proposed_translation",
        "in_standard_filter": 1,
        "description": "Packaged Release vs Site Override. DB CHECK: catalog may be empty; runtime must be one of the two.",
        "owner": "Administrator",
    },
    {
        "dt": "Translation",
        "fieldname": "ct_release_version",
        "label": "Release Version",
        "fieldtype": "Data",
        "insert_after": "ct_origin",
        "read_only": 1,
        "description": "Version of the packaged release that produced this runtime row.",
        "owner": "Administrator",
    },
    {
        "dt": "Translation",
        "fieldname": "ct_released_at",
        "label": "Released At",
        "fieldtype": "Datetime",
        "insert_after": "ct_release_version",
        "read_only": 1,
        "description": "Runtime release timestamp.",
        "owner": "Administrator",
    },
    {
        "dt": "Translation",
        "fieldname": "ct_released_by",
        "label": "Released By",
        "fieldtype": "Data",
        "insert_after": "ct_released_at",
        "read_only": 1,
        "description": "Human or review-agent identifier that released this row.",
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
