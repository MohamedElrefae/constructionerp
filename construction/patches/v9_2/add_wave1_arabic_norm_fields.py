import frappe


TARGETS = (
    {
        "dt": "Item",
        "fieldname": "item_name_ar_norm",
        "label": "Item Name Arabic (Search Key)",
        "insert_after": "item_name_ar",
        "source_field": "item_name_ar",
    },
    {
        "dt": "Customer",
        "fieldname": "customer_name_in_arabic_norm",
        "label": "Customer Name in Arabic (Search Key)",
        "insert_after": "customer_name_in_arabic",
        "source_field": "customer_name_in_arabic",
    },
    {
        "dt": "Supplier",
        "fieldname": "supplier_name_in_arabic_norm",
        "label": "Supplier Name in Arabic (Search Key)",
        "insert_after": "supplier_name_in_arabic",
        "source_field": "supplier_name_in_arabic",
    },
)


def execute():
    """Add and maintain normalized Arabic search keys on Wave 1 masters (Phase 1).

    Mirroring Patch v9_1 for Account, this patch introduces server-authoritative
    Arabic search normalization (Alef variants, tatweel, diacritics) for:
    - Item (`item_name_ar_norm`)
    - Customer (`customer_name_in_arabic_norm`)
    - Supplier (`supplier_name_in_arabic_norm`)

    Idempotent; safe to re-run. Reversible via `revert()`.
    """
    if not frappe.db.exists("DocType", "Custom Field"):
        return

    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except ImportError:
        frappe.log_error("Could not import create_custom_field", "Patch v9_2")
        return

    for target in TARGETS:
        dt = target["dt"]
        if not frappe.db.exists("DocType", dt):
            continue

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
                    "Patch v9_2",
                )

    _backfill()

    for target in TARGETS:
        if frappe.db.exists("DocType", target["dt"]):
            frappe.clear_cache(doctype=target["dt"])


def _backfill():
    """Recompute the normalized key for every stored Arabic value across targets."""
    from construction.services.bilingual_registry import normalize_arabic

    changed = 0
    for target in TARGETS:
        dt = target["dt"]
        if not frappe.db.exists("DocType", dt):
            continue
        src = target["source_field"]
        norm = target["fieldname"]
        if not frappe.get_meta(dt).has_field(norm):
            continue

        rows = frappe.get_all(
            dt,
            filters={src: ("is", "set")},
            fields=["name", src],
            limit_page_length=0,
        )
        for row in rows:
            val = row.get(src)
            if not val:
                continue
            expected = normalize_arabic(val or "")
            current = frappe.db.get_value(dt, row.name, norm)
            if current != expected:
                frappe.db.set_value(dt, row.name, norm, expected, update_modified=False)
                changed += 1
    return changed


def revert():
    """Reversal: remove the derived search key fields across targets."""
    for target in TARGETS:
        dt = target["dt"]
        norm = target["fieldname"]
        name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": norm}, "name")
        if name:
            frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
            frappe.clear_cache(doctype=dt)
