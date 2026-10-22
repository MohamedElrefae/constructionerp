"""BOQ children inherit native parent authorization, independently of UI scope.

Returning True only allows Frappe's own child role/User Permission checks to
continue. It never grants permissions. Selected scope keeps its existing list
filter behavior; this module adds the missing document-parent boundary.
"""

import frappe

BOQ_CHILD_DOCTYPES = (
    "BOQ Item",
    "BOQ Structure",
    "BOQ Item Stage",
    "BOQ Quantity Revision",
    "BOQ Cost Analysis",
    "Variation Order",
)
WRITE_TYPES = {"write", "create", "delete", "submit", "cancel", "amend"}


def _headers(doc):
    headers = {doc.get("boq_header")}
    if doc.doctype != "BOQ Item" and doc.get("boq_item"):
        headers.add(frappe.db.get_value("BOQ Item", doc.boq_item, "boq_header"))
    structure = doc.get("structure") or doc.get("boq_structure")
    if structure:
        headers.add(frappe.db.get_value("BOQ Structure", structure, "boq_header"))
    return {header for header in headers if header}


def has_boq_parent_permission(doc, ptype, user=None, **kwargs):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    headers = _headers(doc)
    # A caller cannot move a forbidden existing child into an allowed parent
    # to make the first permission check pass.
    if not doc.is_new():
        stored = frappe.get_doc(doc.doctype, doc.name)
        headers.update(_headers(stored))
    if not headers:
        return doc.doctype == "BOQ Cost Analysis" and bool(doc.get("is_template"))
    parent_type = "write" if ptype in WRITE_TYPES else "read"
    if doc.doctype == "Variation Order" and ptype in ("write", "create"):
        # F06-D001 reconciliation (foundation program): the VO workflow
        # authorizes engineer approval to Site Engineer / Project Manager /
        # Construction Owner, and VO DocPerm grants those roles write — but
        # the parent gate demanded BOQ Header write, which Site Engineer does
        # not hold, so no ordinary-role chain could complete a VO. For
        # Variation Order writes/creates only, parent READ suffices here because VO
        # commercial integrity is enforced independently of this gate:
        # status-transition validity, segregation of duties, server-owned
        # audit identities, client-approved snapshot immutability and the
        # signed-PDF gate all run in the VO controller regardless of caller.
        # Header-write remains required for VO deletion and for the other five
        # child doctypes (except the stage measurement exception below),
        # whose edits directly mutate header aggregates. Moving a VO to a
        # header the caller cannot read is still refused, and scope
        # containment still applies through the doc_events hook.
        parent_type = "read"
    if doc.doctype == "BOQ Item Stage" and ptype in ("write", "create"):
        # F11-D003 reconciliation: Site Engineers record unapproved site
        # measurements while PM/Owner retain planning and certification
        # authority. Parent READ suffices for stage writes/creates; planning
        # fields and certification stay guarded in the stage controller
        # (measurement-only policy for callers without header write), and
        # certified records remain immutable for every role.
        parent_type = "read"
    if doc.doctype == "BOQ Cost Analysis" and ptype in ("write", "create"):
        # F18 reconciliation: the Cost Database Maintainer reprices eligible
        # Draft analyses without holding BOQ Header write. Parent READ
        # suffices here because pricing integrity is enforced independently:
        # Draft-only mutation, submit/cancel gates, manual/provenance rules
        # and the additive pricing rule all run in the analysis controller.
        # Deletion and submitted-history rewrites stay header-write guarded.
        parent_type = "read"
    if not _scope_allows(headers, user):
        return False
    return all(frappe.has_permission("BOQ Header", parent_type, doc=name, user=user) for name in headers)


def _scope_allows(headers, user):
    """Selected-scope authorization boundary for direct document access (F11-D002).

    With ``enable_scope_context`` on, an ordinary user's active scope must
    cover every header touched by the operation — on direct reads as well as
    writes, matching the list/report/socket filtering already provided by
    ``permission_query_conditions``. Administrator and System Manager bypass,
    mirroring ``scope_query``. Users without an active scope company/project
    are denied scoped documents (missing scope is not a wildcard).
    """
    if user == "Administrator":
        return True
    try:
        if "System Manager" in frappe.get_roles(user):
            return True
    except Exception:
        return False
    try:
        enabled = bool(frappe.db.get_single_value("Construction Settings", "enable_scope_context"))
    except Exception:
        return False
    if not enabled:
        return True
    dims = _cached_scope_dims(user)
    if not dims:
        return False
    for header in headers:
        project = frappe.db.get_value("BOQ Header", header, "project")
        if not project:
            return False
        if dims.get("project") and project != dims["project"]:
            return False
        if dims.get("company"):
            company = frappe.db.get_value("Project", project, "company")
            if company and company != dims["company"]:
                return False
    return True


def _cached_scope_dims(user):
    """Per-request cache of the user's scope dimensions (company/project only)."""
    try:
        cache = getattr(frappe.local, "_boq_perm_scope_dims", None)
        if cache is None:
            cache = frappe.local._boq_perm_scope_dims = {}
        if user not in cache:
            from construction.api.scope_context_api import get_user_scope_context

            scope = get_user_scope_context(user)
            cache[user] = (
                {"company": scope.company, "project": scope.project}
                if scope and (scope.company or scope.project)
                else None
            )
        return cache[user]
    except Exception:
        return None


def has_boq_header_permission(doc, ptype, user=None, **kwargs):
    """has_permission hook for BOQ Header itself: native checks continue, then the scope boundary.

    Returning True only lets Frappe's own role/User Permission checks continue;
    the scope comparison below is the additional boundary. Administrator and
    System Manager bypass, mirroring ``scope_query``.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    try:
        if "System Manager" in frappe.get_roles(user):
            return True
    except Exception:
        return False
    project = doc.get("project") if doc else None
    if not project and doc is not None and getattr(doc, "name", None):
        project = frappe.db.get_value("BOQ Header", doc.name, "project")
    if not _scope_allows_header(project, user):
        return False
    return True


def _scope_allows_header(project, user):
    if user == "Administrator":
        return True
    try:
        if "System Manager" in frappe.get_roles(user):
            return True
    except Exception:
        return False
    if not project:
        return False
    try:
        enabled = bool(frappe.db.get_single_value("Construction Settings", "enable_scope_context"))
    except Exception:
        return False
    if not enabled:
        return True
    dims = _cached_scope_dims(user)
    if not dims:
        return False
    if dims.get("project") and project != dims["project"]:
        return False
    if dims.get("company"):
        company = frappe.db.get_value("Project", project, "company")
        if company and company != dims["company"]:
            return False
    return True


def boq_parent_query_conditions(user, doctype=None):
    """Use native parent query permissions without materializing all headers."""
    if user == "Administrator" or doctype not in BOQ_CHILD_DOCTYPES:
        return ""
    from frappe.model.db_query import DatabaseQuery

    try:
        match = DatabaseQuery("BOQ Header", user=user).build_match_conditions()
    except frappe.PermissionError:
        return "1=0"
    # The table identifier comes exclusively from the fixed DocType allowlist;
    # match is the framework's escaped role/User Permission/shared predicate.
    parent = f"`tab{doctype}`.`boq_header`"
    condition = f"{parent} IN (SELECT `tabBOQ Header`.`name` FROM `tabBOQ Header`"
    if match:
        condition += " WHERE " + match
    condition += ")"
    if doctype == "BOQ Cost Analysis":
        condition = f"(({condition}) OR ({parent} IS NULL OR {parent} = '') AND `tabBOQ Cost Analysis`.`is_template` = 1)"
    return condition


def scope_company_allows(company, user=None):
    """Selected-company boundary for company-wide services without a BOQ parent."""
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    try:
        if "System Manager" in frappe.get_roles(user):
            return True
        if not frappe.db.get_single_value("Construction Settings", "enable_scope_context"):
            return True
        active_company = _cached_scope_dims(user).get("company")
        return bool(active_company and active_company == company)
    except Exception:
        return False
