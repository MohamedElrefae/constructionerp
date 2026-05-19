"""
Scope validation utilities for User Scope Context
Validates cross-dimension alignment between company, branch, project, department
"""

import frappe


def validate_scope_dimensions(company=None, branch=None, project=None, department=None, throw=False):
    """
    Validate that scope dimensions are aligned (e.g., branch belongs to company)
    
    Args:
        company: Company name
        branch: Branch name
        project: Project name
        department: Department name
        throw: If True, throw exception on validation failure
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    errors = []
    
    # Validate branch belongs to company
    if branch and company:
        branch_company = frappe.db.get_value("Branch", branch, "company")
        if branch_company and branch_company != company:
            errors.append(f"Branch '{branch}' does not belong to Company '{company}'")
    
    # Validate project belongs to company
    if project and company:
        project_company = frappe.db.get_value("Project", project, "company")
        if project_company and project_company != company:
            errors.append(f"Project '{project}' does not belong to Company '{company}'")
    
    # Validate department belongs to company (if Department DocType exists with company field)
    if department and company:
        try:
            dept_company = frappe.db.get_value("Department", department, "company")
            if dept_company and dept_company != company:
                errors.append(f"Department '{department}' does not belong to Company '{company}'")
        except Exception:
            # Department may not have company field, ignore
            pass
    
    is_valid = len(errors) == 0
    error_message = "; ".join(errors) if errors else None
    
    if throw and not is_valid:
        frappe.throw(error_message)
    
    return is_valid, error_message
