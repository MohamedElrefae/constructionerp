import frappe


def validate_scope_dimensions(company=None, cost_center=None, project=None, department=None, throw=False):
    errors = []

    # Cost Center must belong to Company (native — Cost Center.company always exists)
    if cost_center and company:
        cc_company = frappe.get_cached_value("Cost Center", cost_center, "company")
        if cc_company and cc_company != company:
            errors.append(f"Cost Center '{cost_center}' does not belong to Company '{company}'")

    # Project must belong to Company
    if project and company:
        project_company = frappe.db.get_value("Project", project, "company")
        if project_company and project_company != company:
            errors.append(f"Project '{project}' does not belong to Company '{company}'")

    # Department must belong to Company
    if department and company:
        try:
            dept_company = frappe.db.get_value("Department", department, "company")
            if dept_company and dept_company != company:
                errors.append(f"Department '{department}' does not belong to Company '{company}'")
        except Exception:
            pass

    # Project ↔ Cost Center: advisory warning (Project.cost_center is a default, not mandatory)
    if project and cost_center:
        project_cc = frappe.db.get_value("Project", project, "cost_center")
        if project_cc and project_cc != cost_center:
            frappe.logger("scope_validation").warning(
                f"Project '{project}' has default cost_center '{project_cc}', "
                f"but scope selected '{cost_center}'"
            )

    # Department ↔ Cost Center: advisory warning (Department.cost_center is optional)
    if department and cost_center:
        if frappe.db.has_column("Department", "cost_center"):
            dept_cc = frappe.db.get_value("Department", department, "cost_center")
            if dept_cc and dept_cc != cost_center:
                frappe.logger("scope_validation").warning(
                    f"Department '{department}' has cost_center '{dept_cc}', "
                    f"but scope selected '{cost_center}'"
                )

    is_valid = len(errors) == 0
    error_message = "; ".join(errors) if errors else None

    if throw and not is_valid:
        frappe.throw(error_message)

    return is_valid, error_message
