import frappe


def extend_bootinfo(bootinfo):
    if not frappe.session.user or frappe.session.user == "Guest":
        return bootinfo

    user = frappe.session.user

    settings = frappe.get_single("Construction Settings")

    scope_enabled = bool(settings.enable_scope_context or False)
    bootinfo["scope_context_enabled"] = scope_enabled

    bootinfo["scope_context_enabled_dimensions"] = {
        "company": bool(settings.enable_scope_company if scope_enabled else False),
        "cost_center": bool(settings.enable_scope_cost_center if scope_enabled else False),
        "project": bool(settings.enable_scope_project if scope_enabled else False),
        "department": bool(settings.enable_scope_department if scope_enabled else False),
    }

    if not scope_enabled:
        return bootinfo

    from construction.api.scope_context_api import get_user_scope_context, get_user_scope_hierarchy

    scope_doc = get_user_scope_context(user)
    scope_current = scope_doc.as_dict() if scope_doc else None
    if scope_current:
        for key in ["docstatus", "idx", "owner", "creation", "modified", "modified_by"]:
            scope_current.pop(key, None)

    hierarchy = get_user_scope_hierarchy(user)

    version = frappe.cache().get_value(f"scope_version:{user}") or frappe.utils.now()

    bootinfo["scope_context"] = {
        "current": scope_current,
        "hierarchy": hierarchy,
        "_version": version,
    }

    return bootinfo
