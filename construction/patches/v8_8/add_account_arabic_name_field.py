import frappe


def execute():
    """Add Construction-owned `account_name_ar` custom field on ERPNext Account.

    Stage 1B: bilingual schema foundation. Idempotent; safe to re-run.
    - Data, visible, non-translatable, inserted after `account_name`.
    - No DB/search index until query-plan evidence requires it.
    - Does NOT modify ERPNext `account.json`.
    - Does NOT populate values.
    """
    if not frappe.db.exists("DocType", "Account"):
        return
    if not frappe.db.exists("DocType", "Custom Field"):
        return

    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except ImportError:
        frappe.log_error("Could not import create_custom_field", "Patch v8_8")
        return

    field_def = {
        "fieldname": "account_name_ar",
        "fieldtype": "Data",
        "label": "Account Name (Arabic)",
        "insert_after": "account_name",
        "translatable": 0,
        # Stage 3 P0: the field is displayed for reference only. Writes are
        # confined to the governed bilingual API (server-enforced by the
        # Account validate hook + flag); the form must not offer direct edits.
        "read_only": 1,
    }

    exists = frappe.db.get_value(
        "Custom Field",
        {"dt": "Account", "fieldname": "account_name_ar"},
        "name",
    )
    if exists:
        _update_custom_field(exists, field_def)
    else:
        try:
            create_custom_field("Account", field_def, ignore_validate=True)
        except Exception:
            frappe.log_error(
                "Failed to create custom field account_name_ar on Account",
                "Patch v8_8",
            )

    frappe.clear_cache(doctype="Account")


def _update_custom_field(custom_field_name, field_def):
    try:
        doc = frappe.get_doc("Custom Field", custom_field_name)
        changed = False
        for key in ("label", "fieldtype", "insert_after", "translatable", "read_only", "hidden"):
            if key in field_def and doc.get(key) != field_def[key]:
                doc.set(key, field_def[key])
                changed = True
        if changed:
            doc.save(ignore_permissions=True)
    except Exception:
        pass
