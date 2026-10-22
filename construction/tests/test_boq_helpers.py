import frappe


def _ensure_transit_warehouse_type():
    """ERPNext Company creation builds default warehouses that require a 'Transit' Warehouse Type."""
    if not frappe.db.exists("Warehouse Type", "Transit"):
        frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)


def get_or_create_test_project(project_name="_Test Construction BOQ Project"):
    company = frappe.db.get_value("Company", {"company_name": "_Test Company"}, "name")
    if not company:
        company = frappe.db.get_value("Company", {}, "name")
    if not company:
        # Create through ERPNext's native Company controller so the standard chart of
        # accounts, default warehouses and site defaults follow the normal lifecycle.
        # Country/currency match ERPNext's canonical CI test company
        # (`.github/ci/business_fixtures.py`, erpnext `test_records.json`: India / INR),
        # so ERPNext's preloaded standard test records stay valid.
        _ensure_transit_warehouse_type()
        company = (
            frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": "_Test Company",
                    "abbr": "_TC",
                    "default_currency": "INR",
                    "country": "India",
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    project = frappe.db.get_value("Project", {"project_name": project_name}, "name")
    if project:
        return project

    return (
        frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": project_name,
                "company": company,
                "naming_series": "PROJ-.####",
            }
        )
        .insert(ignore_permissions=True)
        .name
    )
