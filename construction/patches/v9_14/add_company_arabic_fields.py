import frappe


TARGETS = (
    {
        "dt": "Company",
        "fieldname": "company_name_ar",
        "label": "Company Name (Arabic)",
        "insert_after": "company_name",
        "is_norm": False,
    },
    {
        "dt": "Company",
        "fieldname": "company_name_ar_norm",
        "label": "Company Name Arabic (Search Key)",
        "insert_after": "company_name_ar",
        "source_field": "company_name_ar",
        "is_norm": True,
    },
)


def execute():
    """Add Arabic company_name and normalized search key custom fields on Company.

    Introduces bilingual display and server-authoritative Arabic normalization for
    Company (`company_name_ar`, `company_name_ar_norm`).

    Idempotent; safe to re-run. Reversible via `revert()`.
    """
    if not frappe.db.exists("DocType", "Custom Field"):
        return

    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except ImportError:
        frappe.log_error("Could not import create_custom_field", "Patch v9_14")
        return

    for target in TARGETS:
        dt = target["dt"]
        if not frappe.db.exists("DocType", dt):
            continue

        if target["is_norm"]:
            field_def = {
                "fieldname": target["fieldname"],
                "fieldtype": "Data",
                "label": target["label"],
                "insert_after": target["insert_after"],
                "translatable": 0,
                "read_only": 1,
                "hidden": 1,
                "no_copy": 1,
            }
        else:
            field_def = {
                "fieldname": target["fieldname"],
                "fieldtype": "Data",
                "label": target["label"],
                "insert_after": target["insert_after"],
                "translatable": 0,
                "read_only": 0,
                "hidden": 0,
            }

        exists = frappe.db.get_value(
            "Custom Field",
            {"dt": dt, "fieldname": target["fieldname"]},
            "name",
        )
        if not exists:
            try:
                create_custom_field(dt, field_def, ignore_validate=True)
            except Exception:
                frappe.log_error(
                    f"Failed to create custom field {target['fieldname']} on {dt}",
                    "Patch v9_14",
                )
        else:
            frappe.db.set_value(
                "Custom Field",
                exists,
                field_def,
                update_modified=False,
            )

        frappe.clear_cache(doctype=dt)

    _backfill_normalized_keys()


def _backfill_normalized_keys():
    """Backfill company_name_ar_norm for existing records with non-empty Arabic."""
    from construction.services.bilingual_registry import normalize_arabic

    dt = "Company"
    if not frappe.db.exists("DocType", dt):
        return

    meta = frappe.get_meta(dt)
    if not (meta.has_field("company_name_ar") and meta.has_field("company_name_ar_norm")):
        return

    records = frappe.get_all(
        dt,
        filters=[
            ["company_name_ar", "is", "set"],
            ["company_name_ar", "!=", ""],
        ],
        fields=["name", "company_name_ar", "company_name_ar_norm"],
        limit=0,
    )

    for r in records:
        ar_val = r.get("company_name_ar")
        current_norm = r.get("company_name_ar_norm")
        expected_norm = normalize_arabic(ar_val) if ar_val else ""
        if current_norm != expected_norm:
            frappe.db.set_value(
                dt,
                r["name"],
                "company_name_ar_norm",
                expected_norm,
                update_modified=False,
            )


def revert():
    """Remove Arabic company_name and norm fields on Company (for tests and teardown)."""
    for target in TARGETS:
        dt = target["dt"]
        fieldname = target["fieldname"]
        cf_name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname}, "name")
        if cf_name:
            frappe.delete_doc("Custom Field", cf_name, force=True, ignore_permissions=True)
        frappe.clear_cache(doctype=dt)
