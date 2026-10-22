"""Privacy boundaries for personal Form Layout Profile records."""

import frappe


def has_form_layout_profile_permission(doc, ptype, user=None, **kwargs):
    """Deny ordinary users access to another user's personal profile.

    Frappe treats a falsey controller-hook result as a denial, so True is
    required to continue to its native DocType and role checks. This hook does
    not grant access: those checks still decide whether the request is allowed.
    """
    user = user or frappe.session.user
    if _may_inspect_foreign_personal_profiles(user):
        return True

    owner = doc.get("for_user") if doc else None
    if owner and owner != user:
        return False
    return True


def form_layout_profile_query_conditions(user, doctype=None):
    """Limit native profile lists to shared rows and the caller's own rows."""
    if _may_inspect_foreign_personal_profiles(user):
        return ""

    escaped_user = frappe.db.escape(user)
    return (
        "(`tabForm Layout Profile`.`for_user` IS NULL "
        "OR `tabForm Layout Profile`.`for_user` = '' "
        f"OR `tabForm Layout Profile`.`for_user` = {escaped_user})"
    )


def _may_inspect_foreign_personal_profiles(user):
    return user == "Administrator" or "System Manager" in frappe.get_roles(user)
