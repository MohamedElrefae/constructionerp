import frappe


TARGETS = (
    {
        "dt": "Item Group",
        "fieldname": "item_group_name_ar",
        "label": "Item Group Name (Arabic)",
        "insert_after": "item_group_name",
        "is_norm": False,
    },
    {
        "dt": "Item Group",
        "fieldname": "item_group_name_ar_norm",
        "label": "Item Group Name Arabic (Search Key)",
        "insert_after": "item_group_name_ar",
        "source_field": "item_group_name_ar",
        "is_norm": True,
    },
    {
        "dt": "Customer Group",
        "fieldname": "customer_group_name_ar",
        "label": "Customer Group Name (Arabic)",
        "insert_after": "customer_group_name",
        "is_norm": False,
    },
    {
        "dt": "Customer Group",
        "fieldname": "customer_group_name_ar_norm",
        "label": "Customer Group Name Arabic (Search Key)",
        "insert_after": "customer_group_name_ar",
        "source_field": "customer_group_name_ar",
        "is_norm": True,
    },
    {
        "dt": "Supplier Group",
        "fieldname": "supplier_group_name_ar",
        "label": "Supplier Group Name (Arabic)",
        "insert_after": "supplier_group_name",
        "is_norm": False,
    },
    {
        "dt": "Supplier Group",
        "fieldname": "supplier_group_name_ar_norm",
        "label": "Supplier Group Name Arabic (Search Key)",
        "insert_after": "supplier_group_name_ar",
        "source_field": "supplier_group_name_ar",
        "is_norm": True,
    },
    {
        "dt": "Territory",
        "fieldname": "territory_name_ar",
        "label": "Territory Name (Arabic)",
        "insert_after": "territory_name",
        "is_norm": False,
    },
    {
        "dt": "Territory",
        "fieldname": "territory_name_ar_norm",
        "label": "Territory Name Arabic (Search Key)",
        "insert_after": "territory_name_ar",
        "source_field": "territory_name_ar",
        "is_norm": True,
    },
    {
        "dt": "UOM",
        "fieldname": "uom_name_ar",
        "label": "UOM Name (Arabic)",
        "insert_after": "uom_name",
        "is_norm": False,
    },
    {
        "dt": "UOM",
        "fieldname": "uom_name_ar_norm",
        "label": "UOM Name Arabic (Search Key)",
        "insert_after": "uom_name_ar",
        "source_field": "uom_name_ar",
        "is_norm": True,
    },
)


def execute():
    """Add Arabic name and normalized search key custom fields on Wave 2a classification masters.

    Introduces bilingual display and server-authoritative Arabic normalization for:
    - Item Group (`item_group_name_ar`, `item_group_name_ar_norm`)
    - Customer Group (`customer_group_name_ar`, `customer_group_name_ar_norm`)
    - Supplier Group (`supplier_group_name_ar`, `supplier_group_name_ar_norm`)
    - Territory (`territory_name_ar`, `territory_name_ar_norm`)
    - UOM (`uom_name_ar`, `uom_name_ar_norm`)

    Idempotent; safe to re-run. Reversible via `revert()`.
    """
    if not frappe.db.exists("DocType", "Custom Field"):
        return

    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except ImportError:
        frappe.log_error("Could not import create_custom_field", "Patch v9_4")
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
                    "Patch v9_4",
                )

    _backfill()

    for target in TARGETS:
        if frappe.db.exists("DocType", target["dt"]):
            frappe.clear_cache(doctype=target["dt"])


def _backfill():
    """Populate norm field for any existing records carrying an Arabic name."""
    try:
        from construction.services.bilingual_service import _normalize_arabic
    except ImportError:
        return

    for target in TARGETS:
        if not target.get("is_norm"):
            continue
        dt = target["dt"]
        source = target["source_field"]
        norm = target["fieldname"]
        if not frappe.db.exists("DocType", dt):
            continue
        meta = frappe.get_meta(dt)
        if not (meta.has_field(source) and meta.has_field(norm)):
            continue

        records = frappe.get_all(
            dt,
            filters={source: ["is", "set"]},
            fields=["name", source, norm],
            limit_page_length=0,
        )
        for r in records:
            src_val = r.get(source)
            if not src_val:
                continue
            expected = _normalize_arabic(src_val)
            if r.get(norm) != expected:
                frappe.db.set_value(dt, r.name, norm, expected, update_modified=False)


def revert():
    """Revert patch v9_4 by dropping all 10 created custom fields."""
    for target in reversed(TARGETS):
        cf_name = frappe.db.get_value(
            "Custom Field",
            {"dt": target["dt"], "fieldname": target["fieldname"]},
            "name",
        )
        if cf_name:
            frappe.delete_doc("Custom Field", cf_name, force=True, ignore_permissions=True)
        if frappe.db.exists("DocType", target["dt"]):
            frappe.clear_cache(doctype=target["dt"])
