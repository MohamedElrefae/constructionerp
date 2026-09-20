import frappe


def execute():
    """Add and maintain the normalized Arabic search key on Account (Stage 3).

    P1 remediation: canonical C3 requires server-authoritative Arabic search
    normalization (Alef variants, tatweel, diacritics). A raw SQL LIKE cannot
    normalize, so the governed bilingual service maintains the derived key
    `account_name_ar_norm` next to `account_name_ar`; this patch adds the
    hidden field and backfills it from existing stored values (derived data
    only — no Account names are read, changed, or migrated).

    Idempotent; safe to re-run. Reversible via `revert()`.
    """
    if not frappe.db.exists("DocType", "Account"):
        return
    if not frappe.db.exists("DocType", "Custom Field"):
        return

    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except ImportError:
        frappe.log_error("Could not import create_custom_field", "Patch v9_1")
        return

    field_def = {
        "fieldname": "account_name_ar_norm",
        "fieldtype": "Data",
        "label": "Account Name Arabic (Search Key)",
        "insert_after": "account_name_ar",
        "translatable": 0,
        "read_only": 1,
        "hidden": 1,
        "no_copy": 1,
    }

    exists = frappe.db.get_value(
        "Custom Field",
        {"dt": "Account", "fieldname": "account_name_ar_norm"},
        "name",
    )
    if not exists:
        try:
            create_custom_field("Account", field_def, ignore_validate=True)
        except Exception:
            frappe.log_error(
                "Failed to create custom field account_name_ar_norm on Account",
                "Patch v9_1",
            )

    _backfill()
    frappe.clear_cache(doctype="Account")


def _backfill():
    """Recompute the normalized key for every stored Arabic value."""
    from construction.services.bilingual_registry import normalize_arabic

    rows = frappe.get_all(
        "Account",
        filters={"account_name_ar": ("is", "set")},
        fields=["name", "account_name_ar"],
        limit_page_length=0,
    )
    changed = 0
    for row in rows:
        expected = normalize_arabic(row.account_name_ar or "")
        current = frappe.db.get_value("Account", row.name, "account_name_ar_norm")
        if current != expected:
            frappe.db.set_value("Account", row.name, "account_name_ar_norm", expected, update_modified=False)
            changed += 1
    return changed


def revert():
    """Reversal: remove the derived search key field (column dropped with it)."""
    name = frappe.db.get_value(
        "Custom Field", {"dt": "Account", "fieldname": "account_name_ar_norm"}, "name"
    )
    if name:
        frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
        frappe.clear_cache(doctype="Account")
