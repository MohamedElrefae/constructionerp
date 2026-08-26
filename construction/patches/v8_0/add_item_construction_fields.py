import frappe


def execute():
    """Add construction custom fields to standard ERPNext Item.

    This patch idempotently creates the following custom fields:
    - is_construction_resource (Check)
    - construction_resource_type (Select)
    - default_cost_stream (Select)
    - default_wastage_pct (Percent)
    - default_productivity_qty_per_day (Float)
    - labor_trade_designation (Link -> Designation)
    - linked_asset (Link -> Asset)
    - item_name_ar (Data) — Arabic item name for bilingual BOQs/reports

    Does NOT modify core erpnext item.json.
    """
    if not frappe.db.exists("DocType", "Item"):
        return
    if not frappe.db.exists("DocType", "Custom Field"):
        return

    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except ImportError:
        frappe.log_error("Could not import create_custom_field", "Patch v8_0")
        return

    fields = _get_item_custom_fields()
    for field_def in fields:
        fieldname = field_def["fieldname"]
        exists = frappe.db.get_value(
            "Custom Field",
            {"dt": "Item", "fieldname": fieldname},
            "name",
        )
        if exists:
            _update_custom_field(exists, field_def)
        else:
            try:
                create_custom_field("Item", field_def, ignore_validate=True)
            except Exception:
                frappe.log_error(
                    f"Failed to create custom field {fieldname} on Item",
                    "Patch v8_0",
                )

    frappe.clear_cache(doctype="Item")


def _get_item_custom_fields():
    return [
        {
            "fieldname": "item_name_ar",
            "fieldtype": "Data",
            "label": "Item Name (Arabic)",
            "insert_after": "item_name",
            "translatable": 0,
        },
        {
            "fieldname": "is_construction_resource",
            "fieldtype": "Check",
            "label": "Is Construction Resource",
            "insert_after": "item_name_ar",
            "description": "Enable for items used in BOQ cost analysis",
            "default": "0",
            "in_list_view": 1,
            "in_standard_filter": 1,
        },
        {
            "fieldname": "construction_resource_type",
            "fieldtype": "Select",
            "label": "Construction Resource Type",
            "options": "\nMaterial\nLabor\nPlant\nSubcontract\nOverhead",
            "insert_after": "is_construction_resource",
            "depends_on": "eval:doc.is_construction_resource",
            "in_standard_filter": 1,
        },
        {
            "fieldname": "default_cost_stream",
            "fieldtype": "Select",
            "label": "Default Cost Stream",
            "options": "\nM\nL\nP\nS\nO",
            "insert_after": "construction_resource_type",
            "depends_on": "eval:doc.is_construction_resource",
            "in_standard_filter": 1,
        },
        {
            "fieldname": "default_wastage_pct",
            "fieldtype": "Percent",
            "label": "Default Wastage %",
            "insert_after": "default_cost_stream",
            "depends_on": "eval:doc.is_construction_resource",
        },
        {
            "fieldname": "default_productivity_qty_per_day",
            "fieldtype": "Float",
            "label": "Default Productivity Qty/Day",
            "insert_after": "default_wastage_pct",
            "depends_on": "eval:doc.is_construction_resource",
        },
        {
            "fieldname": "labor_trade_designation",
            "fieldtype": "Link",
            "label": "Labor Trade Designation",
            "options": "Designation",
            "insert_after": "default_productivity_qty_per_day",
            "depends_on": "eval:doc.is_construction_resource",
        },
        {
            "fieldname": "linked_asset",
            "fieldtype": "Link",
            "label": "Linked Asset",
            "options": "Asset",
            "insert_after": "labor_trade_designation",
            "depends_on": "eval:doc.is_construction_resource",
        },
    ]


def _update_custom_field(custom_field_name, field_def):
    try:
        doc = frappe.get_doc("Custom Field", custom_field_name)
        changed = False
        for key in (
            "label",
            "fieldtype",
            "options",
            "depends_on",
            "description",
            "default",
            "in_list_view",
            "in_standard_filter",
        ):
            if key in field_def and doc.get(key) != field_def[key]:
                doc.set(key, field_def[key])
                changed = True
        if changed:
            doc.save(ignore_permissions=True)
    except Exception:
        pass
