import frappe


TARGETS = (
    {
        "dt": "BOQ Structure",
        "fieldname": "title_ar",
        "label": "Title (Arabic)",
        "insert_after": "title",
        "is_norm": False,
    },
    {
        "dt": "BOQ Structure",
        "fieldname": "title_ar_norm",
        "label": "Title Arabic (Search Key)",
        "insert_after": "title_ar",
        "source_field": "title_ar",
        "is_norm": True,
    },
    {
        "dt": "BOQ Header",
        "fieldname": "title_ar",
        "label": "Title (Arabic)",
        "insert_after": "title",
        "is_norm": False,
    },
    {
        "dt": "BOQ Header",
        "fieldname": "title_ar_norm",
        "label": "Title Arabic (Search Key)",
        "insert_after": "title_ar",
        "source_field": "title_ar",
        "is_norm": True,
    },
)


def execute():
    """Add Arabic title and normalized search key custom fields on BOQ Structure and BOQ Header.

    Introduces bilingual display and server-authoritative Arabic normalization for
    BOQ Structure and BOQ Header (`title_ar`, `title_ar_norm`).

    Idempotent; safe to re-run. Reversible via `revert()`.
    """
    if not frappe.db.exists("DocType", "Custom Field"):
        return

    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except ImportError:
        frappe.log_error("Could not import create_custom_field", "Patch v9_7")
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
                    "Patch v9_7",
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
    """Backfill title_ar_norm for existing records with non-empty Arabic."""
    from construction.services.bilingual_registry import normalize_arabic

    for dt in ("BOQ Structure", "BOQ Header"):
        if not frappe.db.exists("DocType", dt):
            continue

        meta = frappe.get_meta(dt)
        if not (meta.has_field("title_ar") and meta.has_field("title_ar_norm")):
            continue

        records = frappe.get_all(
            dt,
            filters=[
                ["title_ar", "is", "set"],
                ["title_ar", "!=", ""],
            ],
            fields=["name", "title_ar", "title_ar_norm"],
            limit=0,
        )

        for r in records:
            ar_val = r.get("title_ar")
            current_norm = r.get("title_ar_norm")
            expected_norm = normalize_arabic(ar_val) if ar_val else ""
            if current_norm != expected_norm:
                frappe.db.set_value(
                    dt,
                    r["name"],
                    "title_ar_norm",
                    expected_norm,
                    update_modified=False,
                )


def revert():
    """Remove Arabic title and norm fields on BOQ Structure and BOQ Header."""
    for target in TARGETS:
        dt = target["dt"]
        fieldname = target["fieldname"]
        cf_name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname}, "name")
        if cf_name:
            frappe.delete_doc("Custom Field", cf_name, force=True, ignore_permissions=True)
        frappe.clear_cache(doctype=dt)
