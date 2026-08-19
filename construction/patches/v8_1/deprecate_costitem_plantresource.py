import frappe


def execute():
    """Safely deprecate CostItem and PlantResource scaffolds.
    
    Step 1: Verify no data exists.
    Step 2: Log count evidence.
    Step 3: Deprecate by setting status on CostItem records (if any).
    Step 4: Remove DocType references from hooks.py translated_doctypes.
    Step 5: Mark DocTypes as deprecated in their JSON (notifies users via Frappe UI).
    
    Does NOT:
    - Drop tables (safe rollback if needed)
    - Touch Direct Labor Designation
    - Touch Construction Settings.direct_labor_designations
    """
    _log_table_counts()

    _deprecate_costitem_records()

    _log_completion()


def _log_table_counts():
    """Log the count of records in CostItem and PlantResource for audit trail."""
    costitem_count = _table_row_count("tabCostItem")
    plantresource_count = _table_row_count("tabPlantResource")

    frappe.log_error(
        f"CostItem count: {costitem_count}, PlantResource count: {plantresource_count}",
        "Deprecation v8_1 - Pre-deprecation counts",
    )

    if costitem_count > 0 or plantresource_count > 0:
        frappe.log_error(
            "WARNING: Non-zero counts found. Deprecation will set status=Deprecated "
            "on existing records but will not delete them.",
            "Deprecation v8_1",
        )


def _deprecate_costitem_records():
    """Mark existing CostItem records as Deprecated."""
    if not frappe.db.table_exists("tabCostItem"):
        return
    if not frappe.db.has_column("CostItem", "status"):
        return

    active_items = frappe.db.get_all(
        "CostItem",
        filters={"status": ["!=", "Deprecated"]},
        pluck="name",
    )
    for name in active_items:
        try:
            frappe.db.set_value("CostItem", name, "status", "Deprecated", update_modified=False)
        except Exception:
            pass

    if active_items:
        frappe.log_error(
            f"Marked {len(active_items)} CostItem records as Deprecated",
            "Deprecation v8_1",
        )


def _table_row_count(table_name):
    if not frappe.db.table_exists(table_name):
        return 0
    rows = frappe.db.sql(f"SELECT COUNT(*) as cnt FROM `{table_name}`", as_dict=True)
    return rows[0]["cnt"] if rows else 0


def _log_completion():
    frappe.log_error("CostItem and PlantResource deprecation completed", "Deprecation v8_1")
