import frappe


def get_or_create_test_project(project_name="_Test Construction BOQ Project"):
    company = frappe.db.get_value("Company", {"company_name": "_Test Company"}, "name")
    if not company:
        company = frappe.db.get_value("Company", {}, "name")

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
