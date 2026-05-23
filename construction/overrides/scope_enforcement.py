import frappe
from construction.api.scope_context_api import get_user_scope_context


def validate(doc, method):
    # ─────────────────────────────────────────────────────────
    # ALWAYS: Branch-Company integrity (regardless of scope context)
    # A document must never have a branch from a different company.
    # This runs on both INSERT and UPDATE.
    # ─────────────────────────────────────────────────────────
    if (
        hasattr(doc, "branch")
        and doc.branch
        and hasattr(doc, "company")
        and doc.company
    ):
        branch_company = frappe.db.get_value("Branch", doc.branch, "company")
        if branch_company and branch_company != doc.company:
            frappe.throw(
                frappe._(
                    "Branch '{0}' belongs to Company '{1}', not '{2}'."
                ).format(doc.branch, branch_company, doc.company)
            )

    # ─────────────────────────────────────────────────────────
    # OPTIONAL: Scope context checks (only when feature is enabled)
    # ─────────────────────────────────────────────────────────
    try:
        enabled = bool(
            frappe.db.get_single_value("Construction Settings", "enable_scope_context") or False
        )
    except Exception:
        enabled = False

    if not enabled:
        return

    if frappe.session.user == "Administrator":
        return

    scope = get_user_scope_context(frappe.session.user)
    if not scope:
        return

    # Warn on company mismatch for NEW documents only
    if (
        doc.is_new()
        and hasattr(doc, "company")
        and doc.company
        and scope.company
        and doc.company != scope.company
    ):
        frappe.logger("scope_enforcement").warning(
            f"Scope mismatch: {frappe.session.user} creating {doc.doctype} "
            f"in {doc.company} but scoped to {scope.company}"
        )

    # Warn on cost_center mismatch for NEW documents only
    if (
        doc.is_new()
        and hasattr(doc, "cost_center")
        and doc.cost_center
        and scope.cost_center
        and doc.cost_center != scope.cost_center
    ):
        frappe.logger("scope_enforcement").warning(
            f"Scope mismatch: {frappe.session.user} creating {doc.doctype} "
            f"with cost_center {doc.cost_center} but scoped to {scope.cost_center}"
        )
