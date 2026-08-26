import json

import frappe
from frappe import _

from construction.construction.utils.scope_validation import validate_scope_dimensions

# ═══════════════════════════════════════════════════════════════
# Internal Helpers
# ═══════════════════════════════════════════════════════════════


def _is_privileged_scope_actor():
    return (
        frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()
    )


def get_allowed_scope_dimensions(user=None):
    """Single permission-correct source of allowed scope dimensions.

    Resolution per dimension (fail closed):
      1. Explicit User Permissions for the user define the allowed set.
      2. Without User Permissions, the set is every value the user can
         READ via ``frappe.get_list`` (role perms + User Permission
         filters). A user lacking read access gets an EMPTY set.
      3. An EMPTY allowed set means NOTHING is allowed — never "allow all".

    Uses ``frappe.get_list`` (permission-enforcing) — never plain
    ``frappe.get_all``, which bypasses permissions. Cross-user lookups
    are privileged-only (Administrator / System Manager).
    """
    user = user or frappe.session.user
    cross_user = user != frappe.session.user
    if cross_user and not _is_privileged_scope_actor():
        frappe.throw(
            _("Not authorized to inspect scope dimensions of another user."),
            frappe.PermissionError,
        )

    kw = {"ignore_permissions": True} if cross_user else {}

    def _user_permission_values(doctype):
        if cross_user:
            # Privileged actors inspecting another user's grants.
            return set(
                frappe.get_all(
                    "User Permission",
                    filters={"user": user, "allow": doctype},
                    pluck="for_value",
                    limit_page_length=0,
                )
            )
        try:
            return set(
                frappe.get_list(
                    "User Permission",
                    filters={"user": user, "allow": doctype},
                    pluck="for_value",
                    limit_page_length=0,
                )
            )
        except Exception:
            # A user who cannot read the "User Permission" doctype by role
            # may still read their OWN grant records — that is the exact
            # restriction set that defines their permitted scope. It is
            # pinned to ``user == self`` so it cannot leak other users'
            # grants or the wider hierarchy. This mirrors how Frappe itself
            # resolves user permissions.
            return set(
                frappe.get_all(
                    "User Permission",
                    filters={"user": user, "allow": doctype},
                    pluck="for_value",
                    limit_page_length=0,
                )
            )

    def _allowed_values(doctype, filters=None):
        ups = _user_permission_values(doctype)
        if ups:
            return ups
        try:
            rows = frappe.get_list(
                doctype,
                fields=["name"],
                filters=filters or {},
                limit_page_length=0,
                **kw,
            )
        except frappe.PermissionError:
            # No read access on this dimension at all → nothing allowed.
            return set()
        return {r["name"] for r in rows}

    project_filters = {"status": ["!=", "Completed"]}
    department_filters = {"disabled": 0} if frappe.db.has_column("Department", "disabled") else {}

    return {
        "company": _allowed_values("Company"),
        "cost_center": _allowed_values("Cost Center"),
        "project": _allowed_values("Project", project_filters),
        "department": _allowed_values("Department", department_filters),
    }


def get_user_scope_context(user=None):
    """
    Returns the User Scope Context document for the given user, or None.
    Internal helper — NOT whitelisted. Used by scope_enforcement.py and boot.py.
    """
    user = user or frappe.session.user
    name = frappe.db.get_value("User Scope Context", {"user": user})
    if name:
        return frappe.get_doc("User Scope Context", name)
    return None


def get_user_scope_hierarchy(user=None):
    """
    Returns the scope hierarchy (companies, cost centers, projects, departments)
    that the user is PERMITTED to access, based on session identity,
    role permissions and User Permissions.

    All queries are permission-enforcing (frappe.get_list). Results are
    Redis-cached with a 5-minute TTL keyed per user.
    """
    user = user or frappe.session.user
    cache_key = f"scope_hierarchy:{user}"

    # Try cache first
    cached = frappe.cache().get_value(cache_key)
    if cached is not None:
        return cached

    ignore_perms = False if user == frappe.session.user else True
    if ignore_perms and not _is_privileged_scope_actor():
        frappe.throw(
            _("Not authorized to inspect scope hierarchy of another user."),
            frappe.PermissionError,
        )
    kw = {} if not ignore_perms else {"ignore_permissions": True}

    def _safe_get_list(doctype, fields, filters=None, order_by=None):
        """Permission-enforcing fetch that degrades to an EMPTY list (never
        bypasses) when the caller lacks read access to the dimension."""
        try:
            return frappe.get_list(
                doctype,
                fields=fields,
                filters=filters,
                order_by=order_by,
                limit_page_length=0,
                **kw,
            )
        except frappe.PermissionError:
            return []

    # All companies (Company DocType has no disabled field) — permission enforced
    hierarchy = {
        "companies": _safe_get_list(
            "Company", ["name", "company_name"], order_by="company_name asc"
        ),
    }

    # All cost centers (NestedSet tree — include lft/rgt for descendant expansion)
    hierarchy["cost_centers"] = _safe_get_list(
        "Cost Center",
        ["name", "cost_center_name", "company", "is_group", "parent_cost_center", "lft", "rgt"],
        order_by="lft asc",
    )

    # Allowed projects (filter out completed only)
    project_fields = ["name", "project_name", "company"]
    if frappe.db.has_column("Project", "cost_center"):
        project_fields.append("cost_center")
    hierarchy["projects"] = _safe_get_list(
        "Project",
        project_fields,
        filters={"status": ["!=", "Completed"]},
        order_by="project_name asc",
    )

    # Allowed departments
    dept_fields = ["name", "department_name", "company"]
    if frappe.db.has_column("Department", "cost_center"):
        dept_fields.append("cost_center")
    dept_filters = {"disabled": 0} if frappe.db.has_column("Department", "disabled") else {}
    hierarchy["departments"] = _safe_get_list(
        "Department",
        dept_fields,
        filters=dept_filters,
        order_by="department_name asc",
    )

    # Cache for 5 minutes
    frappe.cache().set_value(cache_key, hierarchy, expires_in_sec=300)

    return hierarchy


def invalidate_scope_cache(user=None):
    """
    Invalidate Redis cache for user scope hierarchy.
    Called on User Permission changes via doc_events.
    """
    if user:
        frappe.cache().delete_value(f"scope_hierarchy:{user}")
    else:
        # Invalidate all users' caches
        user_list = frappe.get_all("User", pluck="name")
        for u in user_list:
            frappe.cache().delete_value(f"scope_hierarchy:{u}")


# ═══════════════════════════════════════════════════════════════
# Whitelisted APIs
# ═══════════════════════════════════════════════════════════════


_UNSPECIFIED = object()


@frappe.whitelist()
def set_scope_context(
    company=_UNSPECIFIED,
    cost_center=_UNSPECIFIED,
    branch=_UNSPECIFIED,
    project=_UNSPECIFIED,
    department=_UNSPECIFIED,
    source="erpnext",
    client_id=None,
):
    """
    Dual-write API: writes to User Scope Context DocType (canonical),
    then syncs to Session Defaults (convenience layer).

    Args:
        company: Company name
        cost_center: Cost Center name
        branch: Branch name (legacy — use cost_center)
        project: Project name
        department: Department name
        source: Origin of the change ("erpnext" | "nextjs")
        client_id: Browser tab identifier (optional)

    Returns:
        dict: { success, scope_version, source }
    """
    user = frappe.session.user

    # 1. Build allowed hierarchies from the permission-correct service.
    allowed = get_allowed_scope_dimensions(user)
    allowed_companies = allowed["company"]
    allowed_cost_centers = allowed["cost_center"]
    allowed_projects = allowed["project"]
    allowed_depts = allowed["department"]

    # 2. Get or create User Scope Context (CANONICAL STORE)
    existing_name = frappe.db.get_value("User Scope Context", {"user": user})
    if existing_name:
        scope_doc = frappe.get_doc("User Scope Context", existing_name)
    else:
        scope_doc = frappe.new_doc("User Scope Context")
        scope_doc.user = user

    # 3. Resolve & update fields (supporting sentinel and form_dict fallback)
    target_company = company if company is not _UNSPECIFIED else frappe.form_dict.get("company", _UNSPECIFIED)
    target_cost_center = (
        cost_center if cost_center is not _UNSPECIFIED else frappe.form_dict.get("cost_center", _UNSPECIFIED)
    )
    target_branch = branch if branch is not _UNSPECIFIED else frappe.form_dict.get("branch", _UNSPECIFIED)
    target_project = project if project is not _UNSPECIFIED else frappe.form_dict.get("project", _UNSPECIFIED)
    target_department = (
        department if department is not _UNSPECIFIED else frappe.form_dict.get("department", _UNSPECIFIED)
    )

    if target_company is not _UNSPECIFIED:
        if not target_company:
            frappe.throw(_("Company is mandatory for Scope Context."))
        scope_doc.company = target_company
    if target_cost_center is not _UNSPECIFIED:
        scope_doc.cost_center = target_cost_center
    if target_branch is not _UNSPECIFIED:
        scope_doc.branch = target_branch
    if target_project is not _UNSPECIFIED:
        scope_doc.project = target_project
    if target_department is not _UNSPECIFIED:
        scope_doc.department = target_department

    if client_id:
        scope_doc.client_id = client_id

    # Auto-clear branch, cost center, project, and department if they do not match the company
    if scope_doc.branch and scope_doc.company:
        branch_comp = frappe.db.get_value("Branch", scope_doc.branch, "company")
        if branch_comp != scope_doc.company:
            scope_doc.branch = None

    if scope_doc.cost_center and scope_doc.company:
        cc_comp = frappe.db.get_value("Cost Center", scope_doc.cost_center, "company")
        if cc_comp != scope_doc.company:
            scope_doc.cost_center = None

    if scope_doc.project and scope_doc.company:
        proj_comp = frappe.db.get_value("Project", scope_doc.project, "company")
        if proj_comp and proj_comp != scope_doc.company:
            scope_doc.project = None

    if scope_doc.department and scope_doc.company:
        dept_comp = frappe.db.get_value("Department", scope_doc.department, "company")
        if dept_comp and dept_comp != scope_doc.company:
            scope_doc.department = None

    # 4. Authorization validation on final values
    if scope_doc.company and scope_doc.company not in allowed_companies:
        frappe.throw(_("Not authorized: Company '{0}'").format(scope_doc.company))
    if scope_doc.cost_center and scope_doc.cost_center not in allowed_cost_centers:
        frappe.throw(_("Not authorized: Cost Center '{0}'").format(scope_doc.cost_center))
    if scope_doc.project and scope_doc.project not in allowed_projects:
        frappe.throw(_("Not authorized: Project '{0}'").format(scope_doc.project))
    if scope_doc.department and scope_doc.department not in allowed_depts:
        frappe.throw(_("Not authorized: Department '{0}'").format(scope_doc.department))

    # 5. Cross-dimension validation
    is_valid, error_msg = validate_scope_dimensions(
        scope_doc.company, scope_doc.cost_center, scope_doc.project, scope_doc.department
    )
    if not is_valid:
        frappe.throw(_(error_msg))

    # 6. Save + sync Session Defaults in one transaction
    if scope_doc.is_new():
        scope_doc.owner = frappe.session.user
    scope_doc.save()

    frappe.defaults.set_user_default("company", scope_doc.company or "", user)
    if scope_doc.cost_center:
        frappe.defaults.set_user_default("cost_center", scope_doc.cost_center, user)
    else:
        frappe.defaults.clear_user_default("cost_center", user)
    if scope_doc.project:
        frappe.defaults.set_user_default("project", scope_doc.project, user)
    else:
        frappe.defaults.clear_user_default("project", user)
    if scope_doc.department:
        frappe.defaults.set_user_default("department", scope_doc.department, user)
    else:
        frappe.defaults.clear_user_default("department", user)

    # 7. Log source for cross-system debugging
    frappe.logger("scope_context").info(
        f"Scope changed: user={user}, company={scope_doc.company}, "
        f"cost_center={scope_doc.cost_center}, project={scope_doc.project}, "
        f"department={scope_doc.department}, source={source}, "
        f"scope_version={scope_doc.scope_version}"
    )

    # 8. Clear cache
    frappe.cache().delete_value(f"scope_hierarchy:{user}")
    frappe.clear_cache(user=user)

    # 10. Return
    return {
        "success": True,
        "scope_version": scope_doc.scope_version,
        "source": source,
    }


@frappe.whitelist()
def get_scope_hierarchy_detail():
    """
    Returns full hierarchy data with link status for management UI.

    System Manager ONLY: this endpoint exposes the complete company /
    cost-center / project / department structure of the site and is a
    management tool, not a general-user read API.
    """
    if not _is_privileged_scope_actor():
        frappe.throw(_("Not authorized"), frappe.PermissionError)

    companies = frappe.get_all("Company", fields=["name", "company_name"], order_by="company_name asc")
    cost_centers = frappe.get_all(
        "Cost Center",
        fields=["name", "cost_center_name", "company", "is_group", "parent_cost_center"],
        order_by="lft asc",
    )
    projects = frappe.get_all(
        "Project",
        fields=["name", "project_name", "company", "cost_center", "status"],
        order_by="project_name asc",
    )
    dept_fields = ["name", "department_name", "company", "disabled"]
    if frappe.db.has_column("Department", "cost_center"):
        dept_fields.append("cost_center")
    depts = frappe.get_all(
        "Department",
        fields=dept_fields,
        order_by="department_name asc",
    )

    tree = []
    for c in companies:
        c_cost_centers = [cc for cc in cost_centers if cc.company == c.name]
        c_projects = [p for p in projects if p.company == c.name]
        c_depts = [d for d in depts if d.company == c.name]

        for cc in c_cost_centers:
            cc._projects = [p for p in c_projects if p.cost_center == cc.name]
            cc._depts = [d for d in c_depts if d.cost_center == cc.name]

        tree.append(
            {
                "name": c.name,
                "title": c.company_name or c.name,
                "cost_centers": [
                    {
                        "name": cc.name,
                        "label": cc.cost_center_name or cc.name,
                        "is_group": bool(cc.is_group),
                        "linked": bool(cc.company),
                        "projects": [
                            {
                                "name": p.name,
                                "label": p.project_name or p.name,
                                "company_ok": bool(p.company),
                                "cost_center_ok": bool(p.cost_center),
                            }
                            for p in cc._projects
                        ],
                        "departments": [
                            {
                                "name": d.name,
                                "label": d.department_name or d.name,
                                "company_ok": bool(d.company),
                                "cost_center_ok": bool(d.cost_center),
                            }
                            for d in cc._depts
                        ],
                    }
                    for cc in c_cost_centers
                ],
                "orphan_projects": [
                    {
                        "name": p.name,
                        "label": p.project_name or p.name,
                        "company_ok": bool(p.company),
                        "cost_center_ok": bool(p.cost_center),
                    }
                    for p in c_projects
                    if not p.cost_center or not any(cc.name == p.cost_center for cc in c_cost_centers)
                ],
                "orphan_depts": [
                    {
                        "name": d.name,
                        "label": d.department_name or d.name,
                        "company_ok": bool(d.company),
                        "cost_center_ok": bool(d.cost_center),
                    }
                    for d in c_depts
                    if not d.cost_center or not any(cc.name == d.cost_center for cc in c_cost_centers)
                ],
            }
        )

    return tree


@frappe.whitelist()
def quick_create(doctype, values):
    """Create a new record with given values (for quick-add in management UI)."""
    if not frappe.has_permission(doctype, "create"):
        frappe.throw(_("Not permitted to create {0}").format(doctype))
    doc = frappe.new_doc(doctype)
    for k, v in json.loads(values).items():
        doc.set(k, v)
    doc.insert(ignore_permissions=False)
    return doc.name


@frappe.whitelist()
def get_active_scope_summary():
    """
    Returns summary of active user scope contexts.
    System Manager only.
    """
    if "System Manager" not in frappe.get_roles():
        frappe.throw(_("Not authorized"), frappe.PermissionError)

    return frappe.get_all(
        "User Scope Context",
        fields=["user", "company", "cost_center", "project", "department", "last_active_at"],
        filters={
            "last_active_at": [">=", frappe.utils.add_days(frappe.utils.now(), -1)],
        },
        order_by="last_active_at desc",
    )


@frappe.whitelist()
def get_project_display_name(project):
    """Return the display label for a Project.

    Authorization policy (fail closed, non-disclosing):
      - Callers with Project READ permission may resolve any project they
        can read (frappe.get_list enforces User Permissions).
      - Otherwise the caller may ONLY resolve their ACTIVE scope project.
      - Missing and unauthorized projects return the SAME generic denial —
        no existence oracle.
    """
    if not project:
        return {"project_name": ""}

    permitted = False
    try:
        permitted = bool(frappe.has_permission("Project", "read"))
    except Exception:
        permitted = False

    if not permitted:
        scope_doc = get_user_scope_context(frappe.session.user)
        if not (scope_doc and scope_doc.project and scope_doc.project == str(project).strip()):
            # Identical denial for missing AND unauthorized names.
            frappe.throw(_("Not authorized to access this project."), frappe.PermissionError)

    rows = frappe.get_list(
        "Project",
        filters={"name": project},
        fields=["project_name"],
        limit=1,
    )
    if not rows:
        if permitted:
            # Privileged readers may learn a name does not exist.
            frappe.throw(_("Project {0} does not exist.").format(project))
        frappe.throw(_("Not authorized to access this project."), frappe.PermissionError)

    return {"project_name": rows[0].project_name or project}


# ═══════════════════════════════════════════════════════════════
# Option A+ — dimension permission probe
# ═══════════════════════════════════════════════════════════════


@frappe.whitelist()
def get_scope_dimension_permissions():
    """
    Return the current session user's read permission flags for the three
    scope dimensions. Used by the report filter hardening JS to decide
    whether to lock Link/MultiSelectList filters or leave them editable.

    Returns a small dict; safe to call from the client (returns booleans only).
    """
    return {
        "Company": bool(frappe.has_permission("Company", "read")),
        "Project": bool(frappe.has_permission("Project", "read")),
        "Cost Center": bool(frappe.has_permission("Cost Center", "read")),
        "Account": bool(frappe.has_permission("Account", "read")),
    }
