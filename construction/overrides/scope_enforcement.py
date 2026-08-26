import frappe

from construction.api.scope_context_api import get_allowed_scope_dimensions, get_user_scope_context

# Scope dimension columns recognized on documents.
_SCOPE_DIMENSION_FIELDS = ("company", "project", "cost_center", "department")

# Explicit service-only bypass token. Server code that MUST cross scope
# boundaries programmatically (e.g. system migrations driven outside
# install/patch flags) may set ``frappe.flags.construction_scope_bypass``.
# A plain ``doc.flags.ignore_permissions`` is NOT sufficient anymore.


def _in_system_install() -> bool:
    return bool(
        getattr(frappe.flags, "in_migrate", False)
        or getattr(frappe.flags, "in_install", False)
        or getattr(frappe.flags, "in_patch", False)
    )


def _scope_enabled_or_fail_closed() -> bool:
    """Read the feature flag. Any failure to load configuration fails CLOSED."""
    try:
        return bool(frappe.db.get_single_value("Construction Settings", "enable_scope_context") or False)
    except Exception as e:
        frappe.logger("scope_enforcement").error(f"Failed to read scope context settings: {e}")
        frappe.throw(
            frappe._("Security Error: Scope enforcement configuration could not be loaded."),
            frappe.PermissionError,
        )


def _validate_own_scope_context_write(doc):
    """Narrow validation for writes to ``User Scope Context`` itself.

    This is the ONLY bootstrap path that bypasses the generic scoped-document
    requirement; without it a user could never create the first context
    (the wildcard hook demanded an active scope before allowing the very
    record that establishes it — a deadlock).

    Policy:
      - System Manager / Administrator may manage any context.
      - Everyone else may ONLY create/update the context whose ``user``
        matches ``frappe.session.user`` (no forging other users' contexts,
        including via REST/doc.save where DocType-level ``if_owner``
        would not help because ``owner`` != ``user``).
      - Every supplied dimension must lie within the caller's permitted
        hierarchy (User Permissions), same policy as the whitelisted API.
    """
    session_user = frappe.session.user
    privileged = session_user == "Administrator" or "System Manager" in frappe.get_roles()

    if not privileged:
        if doc.user != session_user:
            frappe.throw(
                frappe._("You may only manage your own User Scope Context."),
                frappe.PermissionError,
            )
        # Permission-correct allowlists (get_list + User Permissions).
        # An EMPTY allowed set means NOTHING is allowed — never "allow all".
        allowed = get_allowed_scope_dimensions(session_user)
        for field, allowed_set in allowed.items():
            value = getattr(doc, field, None)
            if value and value not in allowed_set:
                frappe.throw(
                    frappe._("Not authorized: {0} '{1}' is outside your permitted hierarchy.").format(
                        field.replace("_", " ").title(), value
                    ),
                    frappe.PermissionError,
                )

    # Keep the branch/company integrity rule for the context document too.
    if getattr(doc, "branch", None) and getattr(doc, "company", None):
        branch_company = frappe.db.get_value("Branch", doc.branch, "company")
        if branch_company and branch_company != doc.company:
            frappe.throw(
                frappe._("Branch '{0}' belongs to Company '{1}', not '{2}.'").format(
                    doc.branch, branch_company, doc.company
                )
            )


def validate(doc, method):
    # ─────────────────────────────────────────────────────────
    # ALWAYS: Branch-Company integrity (regardless of scope context)
    # A document must never have a branch from a different company.
    # This runs on both INSERT and UPDATE.
    # ─────────────────────────────────────────────────────────
    if hasattr(doc, "branch") and doc.branch and hasattr(doc, "company") and doc.company:
        branch_company = frappe.db.get_value("Branch", doc.branch, "company")
        if branch_company and branch_company != doc.company:
            frappe.throw(
                frappe._("Branch '{0}' belongs to Company '{1}', not '{2}.'").format(
                    doc.branch, branch_company, doc.company
                )
            )

    # ─────────────────────────────────────────────────────────
    # SCOPE BOOTSTRAP: narrowly exempt writes to User Scope Context.
    # Must run BEFORE the generic active-scope requirement below,
    # otherwise the first scope can never be established.
    # ─────────────────────────────────────────────────────────
    if doc.doctype == "User Scope Context":
        _validate_own_scope_context_write(doc)
        return

    # In migration / setup / install, skip scope enforcement
    if _in_system_install():
        return

    # Explicit service-only bypass token (server-controlled flag).
    if getattr(frappe.flags, "construction_scope_bypass", False):
        return

    # ─────────────────────────────────────────────────────────
    # OPTIONAL: Scope context checks (only when feature is enabled).
    # Configuration-read failures fail CLOSED (see helper).
    # ─────────────────────────────────────────────────────────
    enabled = _scope_enabled_or_fail_closed()

    if not enabled:
        return

    user = frappe.session.user
    if user == "Administrator":
        return

    # Guests can never create or modify scoped business documents.
    if user == "Guest":
        frappe.throw(
            frappe._("Scope enforcement is active: Guest sessions cannot modify scoped documents."),
            frappe.PermissionError,
        )

    # Check if user has System Manager (document-write exemption).
    # NOTE: finance/report role exemptions apply to REPORTS only
    # (see overrides/scope_report.py) and deliberately do NOT bypass
    # document scope enforcement here.
    if "System Manager" in frappe.get_roles():
        return

    scope = get_user_scope_context(user)
    has_scope_fields = any(hasattr(doc, f) and getattr(doc, f, None) for f in _SCOPE_DIMENSION_FIELDS)
    if has_scope_fields and (not scope or not scope.company):
        frappe.throw(
            frappe._("Scope enforcement is active: An active User Scope Context is required to create or modify scoped documents."),
            frappe.PermissionError,
        )

    if not scope:
        return

    # Enforce company boundary for scoped non-admin users
    if hasattr(doc, "company") and doc.company and scope.company and doc.company != scope.company:
        frappe.throw(
            frappe._("Scope boundary violation: Document company '{0}' does not match active user scope '{1}.'").format(
                doc.company, scope.company
            ),
            frappe.PermissionError,
        )

    # Enforce project boundary for scoped non-admin users
    if hasattr(doc, "project") and doc.project and scope.project and doc.project != scope.project:
        frappe.throw(
            frappe._("Scope boundary violation: Document project '{0}' does not match active user scope '{1}.'").format(
                doc.project, scope.project
            ),
            frappe.PermissionError,
        )

    # Enforce cost center boundary for scoped non-admin users
    if hasattr(doc, "cost_center") and doc.cost_center and scope.cost_center:
        scope_cc = frappe.db.get_value("Cost Center", scope.cost_center, ["lft", "rgt"], as_dict=True)
        doc_cc = frappe.db.get_value("Cost Center", doc.cost_center, ["lft", "rgt"], as_dict=True)
        if scope_cc and doc_cc:
            if not (doc_cc.lft >= scope_cc.lft and doc_cc.rgt <= scope_cc.rgt):
                frappe.throw(
                    frappe._("Scope boundary violation: Document cost center '{0}' is outside active user scope '{1}.'").format(
                        doc.cost_center, scope.cost_center
                    ),
                    frappe.PermissionError,
                )
        elif doc.cost_center != scope.cost_center:
            frappe.throw(
                frappe._("Scope boundary violation: Document cost center '{0}' is outside active user scope '{1}.'").format(
                    doc.cost_center, scope.cost_center
                ),
                frappe.PermissionError,
            )
