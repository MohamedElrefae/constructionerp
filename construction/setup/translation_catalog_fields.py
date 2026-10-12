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
            frappe.log_error(
                f"Failed to create custom field {field['fieldname']}", "Translation Catalog Setup"
            )


def ensure_translation_identity():
    """after_install / after_migrate hook: guarantee identity fields + digests.

    Fresh ``install-app`` marks app patches as executed without running them,
    so schema created only by patches (v8_6/v8_7) would be missing on new
    sites. This hook is idempotent: it creates the custom fields if needed and
    backfills digests / normalized search keys / origin for any row that lacks
    them. Safe to run repeatedly (second run changes nothing).
    """
    ensure_custom_fields()
    if not frappe.db.has_column("Translation", "ct_key_digest"):
        return {"skipped": True, "reason": "ct_key_digest column unavailable"}

    import hashlib
    import json

    from frappe.translate import strip_html_tags

    def _digest(lang, src, ctx, app, is_catalog):
        payload = (
            [lang or "", src or "", ctx or "", app or "", "catalog"]
            if is_catalog
            else [lang or "", src or "", ctx or "", "runtime"]
        )
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    backfilled = 0
    last_name = ""
    while True:
        # SQL NULL never matches IN ('', NULL). Also repair legacy NULL
        # catalog flags so those runtime overrides reach the loader's = 0 query.
        # Keyset pagination stays stable as repaired rows leave the result set.
        rows = frappe.db.sql(
            """
            SELECT name, language, source_text, context, ct_app,
                   ct_is_catalog_entry, ct_origin, ct_key_digest, ct_search_normalized
            FROM `tabTranslation`
            WHERE (ct_key_digest IS NULL OR ct_key_digest = '' OR ct_is_catalog_entry IS NULL)
              AND name > %(last_name)s
            ORDER BY name
            LIMIT 500
            """,
            {"last_name": last_name},
            as_dict=True,
        )
        if not rows:
            break
        pending = []
        identities = {}
        for r in rows:
            is_catalog = bool(r.get("ct_is_catalog_entry"))
            digest = _digest(r.language, r.source_text, r.context, r.get("ct_app"), is_catalog)
            owner = frappe.db.get_value("Translation", {"ct_key_digest": digest}, "name")
            if (owner and owner != r.name) or digest in identities:
                # Preserve both translations rather than guessing which value
                # a customer intended to keep under the existing unique index.
                frappe.throw(
                    "Legacy Translation identity collision; reconcile duplicate rows before retrying"
                )
            identities[digest] = r.name
            updates = {
                "ct_key_digest": digest,
                "ct_search_normalized": strip_html_tags(r.source_text or "").strip(),
            }
            if r.get("ct_is_catalog_entry") is None:
                updates["ct_is_catalog_entry"] = 0
            if not is_catalog and not (r.get("ct_origin") or "").strip():
                updates["ct_origin"] = "Site Override"
            pending.append((r.name, updates))
        for name, updates in pending:
            frappe.db.set_value("Translation", name, updates, update_modified=False)
            backfilled += 1
        last_name = rows[-1].name
    if backfilled:
        frappe.db.commit()
        from frappe.translate import clear_cache

        clear_cache()
    return {"backfilled": backfilled}


def apply():
    """Run from patches / migrate."""
    ensure_custom_fields()
    frappe.db.commit()


def count_incomplete_translation_identities():
    """Verify the migration postcondition without treating NULL as a value."""
    return frappe.db.sql(
        """
        SELECT COUNT(*) FROM `tabTranslation`
        WHERE ct_key_digest IS NULL OR ct_key_digest = '' OR ct_is_catalog_entry IS NULL
        """
    )[0][0]
