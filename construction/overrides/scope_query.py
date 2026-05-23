import frappe


# Per-request cache so we don't hit information_schema repeatedly
_column_cache = {}


def _has_column(doctype, fieldname):
    key = (doctype, fieldname)
    if key not in _column_cache:
        _column_cache[key] = frappe.db.has_column(doctype, fieldname)
    return _column_cache[key]


def add_scope_conditions(user, doctype=None):
    """
    Inject scope filters into ALL database queries via
    the permission_query_conditions hook with wildcard '*'.

    Called by Frappe for every DatabaseQuery and Engine query.
    Returns a SQL WHERE clause fragment (or '' to skip).

    Applies: list views, reports, charts, dashboards,
             recent documents, assigned-to widgets.
    """
    # 1. Administrator always bypasses
    if user == "Administrator":
        return ""

    # 2. Skip system doctypes that never carry scope dimensions
    SKIP_DOCTYPES = {
        "User", "Role", "DocType", "DocField", "DocPerm",
        "File", "Version", "Email Queue", "Activity Log",
        "Error Log", "Scheduled Job Log", "Server Script",
        "Custom Field", "Property Setter", "Workflow",
        "Workflow State", "Workflow Action", "DocShare",
        "Comment", "Communication", "ToDo",
        "Prepared Report", "Document Naming Rule",
    }
    if doctype in SKIP_DOCTYPES:
        return ""

    # 3. Read scope from session defaults (zero DB round-trips)
    company = frappe.defaults.get_user_default("company", user)
    cost_center = frappe.defaults.get_user_default("cost_center", user)
    project = frappe.defaults.get_user_default("project", user)
    department = frappe.defaults.get_user_default("department", user)

    if not any([company, cost_center, project, department]):
        return ""

    # 4. Build conditions with column-existence guards
    clauses = []

    if company and _has_column(doctype, "company"):
        clauses.append(
            f"`tab{doctype}`.`company` = {frappe.db.escape(company)}"
        )

    if cost_center and _has_column(doctype, "cost_center"):
        # NestedSet expansion: include the selected node AND all descendants
        lft, rgt = frappe.db.get_value(
            "Cost Center", cost_center, ["lft", "rgt"]
        )
        clauses.append(
            f"`tab{doctype}`.`cost_center` IN ("
            f"  SELECT `name` FROM `tabCost Center`"
            f"  WHERE `lft` >= {lft} AND `rgt` <= {rgt}"
            f")"
        )

    if project and _has_column(doctype, "project"):
        clauses.append(
            f"`tab{doctype}`.`project` = {frappe.db.escape(project)}"
        )

    if department and _has_column(doctype, "department"):
        clauses.append(
            f"`tab{doctype}`.`department` = {frappe.db.escape(department)}"
        )

    return " AND ".join(clauses)
