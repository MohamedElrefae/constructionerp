import frappe

# Per-request cache so we don't hit information_schema repeatedly
_column_cache = {}

# Per-request cache for dynamic scope filter exclusions
_exclusions_cache = None


def _has_column(doctype, fieldname):
    key = (doctype, fieldname)
    if key not in _column_cache:
        _column_cache[key] = frappe.db.has_column(doctype, fieldname)
    return _column_cache[key]


def _get_dynamic_exclusions():
    global _exclusions_cache
    if _exclusions_cache is not None:
        return _exclusions_cache
    try:
        meta = frappe.get_meta("Construction Settings")
        if not meta.has_field("scope_filter_exclusions"):
            _exclusions_cache = set()
            return _exclusions_cache
        custom = frappe.db.get_single_value("Construction Settings", "scope_filter_exclusions") or ""
        if custom:
            _exclusions_cache = {x.strip() for x in custom.replace("\n", ",").split(",") if x.strip()}
        else:
            _exclusions_cache = set()
    except Exception:
        # Fail closed: an unreadable exclusion list must never WIDEN visibility.
        _exclusions_cache = set()
    return _exclusions_cache


def _canonical_scope_dimensions(user):
    """Return the user's scope dimensions from the CANONICAL User Scope
    Context record (not possibly-stale session defaults).

    Results are cached per-request only (frappe.local), so a scope change
    is honoured on the next request without stale cross-request reads.

    Returns:
        dict: dimension -> value (may be empty when the user has no scope).
        None: when the canonical record could not be loaded (caller must
              FAIL CLOSED).
    """
    cache = getattr(frappe.local, "_construction_canonical_scope_dims", None)
    if cache is None:
        cache = frappe.local._construction_canonical_scope_dims = {}
    if user not in cache:
        try:
            from construction.api.scope_context_api import get_user_scope_context

            scope_doc = get_user_scope_context(user)
            cache[user] = (
                True,
                {
                    "company": getattr(scope_doc, "company", None) if scope_doc else None,
                    "cost_center": getattr(scope_doc, "cost_center", None) if scope_doc else None,
                    "project": getattr(scope_doc, "project", None) if scope_doc else None,
                    "department": getattr(scope_doc, "department", None) if scope_doc else None,
                },
            )
        except Exception as e:
            frappe.logger("scope_query").error(f"Failed to load canonical scope context for '{user}': {e}")
            cache[user] = (False, {})
    ok, dims = cache[user]
    return dims if ok else None


def add_scope_conditions(user, doctype=None):
    """
    Inject scope filters into ALL database queries via
    the permission_query_conditions hook with wildcard '*'.

    Called by Frappe for every DatabaseQuery and Engine query.
    Returns a SQL WHERE clause fragment (or '' to skip).

    Applies: list views, reports, charts, dashboards,
             recent documents, assigned-to widgets.

    Fail-closed policy:
      - Guests and restricted users with no canonical scope get ``1=0``
        on any DocType carrying scope columns.
      - Configuration or canonical-context load failures deny access.
    """
    # 1. Administrator always bypasses. Guest deliberately does NOT:
    #    guests fall through to the restricted path and receive 1=0
    #    on scoped DocTypes (fail closed).
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return ""

    try:
        enabled = bool(frappe.db.get_single_value("Construction Settings", "enable_scope_context") or False)
    except Exception as e:
        frappe.logger("scope_query").error(f"Failed to read scope context settings: {e}")
        enabled = True  # FAIL CLOSED on configuration-read errors

    if not enabled:
        return ""

    # 2. Skip system doctypes that never carry scope dimensions
    SKIP_DOCTYPES = {
        "User",
        "Role",
        "DocType",
        "DocField",
        "DocPerm",
        "File",
        "Version",
        "Email Queue",
        "Activity Log",
        "Error Log",
        "Scheduled Job Log",
        "Server Script",
        "Custom Field",
        "Property Setter",
        "Workflow",
        "Workflow State",
        "Workflow Action",
        "DocShare",
        "Comment",
        "Communication",
        "ToDo",
        "Prepared Report",
        "Document Naming Rule",
    }
    if doctype in SKIP_DOCTYPES or doctype in _get_dynamic_exclusions():
        return ""

    has_any_scope_col = any(_has_column(doctype, col) for col in ("company", "cost_center", "project", "department"))

    # 3. Read scope from the CANONICAL User Scope Context record.
    dimensions = _canonical_scope_dimensions(user)

    if dimensions is None:
        # Canonical context could not be loaded → fail closed.
        return "1=0" if has_any_scope_col else ""

    company = dimensions.get("company")
    cost_center = dimensions.get("cost_center")
    project = dimensions.get("project")
    department = dimensions.get("department")

    if not any([company, cost_center, project, department]):
        # No active scope at all → deny rows on scoped DocTypes.
        return "1=0" if has_any_scope_col else ""
    if not has_any_scope_col:
        return ""

    # 4. Build conditions with column-existence guards
    clauses = []

    if company and _has_column(doctype, "company"):
        clauses.append(f"`tab{doctype}`.`company` = {frappe.db.escape(company)}")

    if cost_center and _has_column(doctype, "cost_center"):
        # NestedSet expansion: include the selected node AND all descendants
        bounds = frappe.db.get_value("Cost Center", cost_center, ["lft", "rgt"], as_dict=True)
        if bounds and bounds.lft is not None and bounds.rgt is not None:
            clauses.append(
                f"`tab{doctype}`.`cost_center` IN ("
                f"  SELECT `name` FROM `tabCost Center`"
                f"  WHERE `lft` >= {int(bounds.lft)} AND `rgt` <= {int(bounds.rgt)}"
                f")"
            )
        else:
            # Node missing/tree corrupt → degrade to exact match (never widen).
            clauses.append(f"`tab{doctype}`.`cost_center` = {frappe.db.escape(cost_center)}")

    if project and _has_column(doctype, "project"):
        clauses.append(f"`tab{doctype}`.`project` = {frappe.db.escape(project)}")

    if department and _has_column(doctype, "department"):
        clauses.append(f"`tab{doctype}`.`department` = {frappe.db.escape(department)}")

    return " AND ".join(clauses)
