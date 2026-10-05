"""Install the custom fields required by the already-active bilingual registry.

Frappe marks upgrade patches as applied on a fresh install. Required schema
must therefore also be provisioned by installation/migration hooks, rather
than relying on a site's historical patch execution. Existing fields and
business values are never overwritten here.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from construction.services.bilingual_service import get_mapping, get_registry


def ensure_bilingual_schema():
    registry = get_registry()
    fields = {}
    installed = []
    for doctype, mapping in registry.get("doctypes", {}).items():
        if mapping.get("state") not in ("active", "schema_installed"):
            continue
        # Optional applications (e.g. HRMS) may own absent DocTypes. Their
        # installation must call migrate; do not invent core DocTypes here.
        if not frappe.db.exists("DocType", doctype):
            continue
        installed.append(doctype)
        meta = frappe.get_meta(doctype, cached=False)
        for key in ("english_field", "code_field", "identity_field"):
            fieldname = mapping.get(key)
            if fieldname and fieldname != "name" and not meta.has_field(fieldname):
                frappe.throw(f"Bilingual schema for {doctype} requires existing field {fieldname}")
        definitions = []
        arabic = mapping.get("arabic_field")
        norm = mapping.get("norm_field")
        if arabic and not meta.has_field(arabic):
            definitions.append(
                {
                    "fieldname": arabic,
                    "fieldtype": "Data",
                    "label": "Name (Arabic)",
                    "insert_after": mapping.get("english_field") or "name",
                    "translatable": 0,
                }
            )
        if norm and not meta.has_field(norm):
            definitions.append(
                {
                    "fieldname": norm,
                    "fieldtype": "Data",
                    "label": "Arabic Name (Search Key)",
                    "insert_after": arabic or mapping.get("english_field") or "name",
                    "read_only": 1,
                    "hidden": 1,
                    "no_copy": 1,
                    "translatable": 0,
                }
            )
        if definitions:
            fields[doctype] = definitions
    if fields:
        # Match existing managed-schema patches: legacy scope property setters
        # intentionally hide mandatory links and prevent whole-DocType UI
        # validation. This bypass applies only to additive metadata; business
        # document validation and bilingual mapping checks remain enforced.
        create_custom_fields(fields, update=False, ignore_validate=True)
    # No silent success if field creation failed or a registry adapter drifted.
    frappe.local.ct_bilingual_mapping_cache = {}
    for doctype in installed:
        frappe.clear_cache(doctype=doctype)
        # Frappe's per-process metadata cache may have been populated while
        # collecting missing fields; refresh from DB before adapter validation.
        frappe.get_meta(doctype, cached=False)
        get_mapping(doctype)
    return {"doctypes_checked": len(installed), "fields_created": sum(map(len, fields.values()))}
