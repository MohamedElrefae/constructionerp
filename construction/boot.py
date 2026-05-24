import frappe


def _translate_sidebar_labels(bootinfo):
    """Translate sidebar item labels that Frappe sends in bootinfo.

    Frappe v16 uses the top-level sidebar label as a lookup key in
    sidebar.js. Translating that title breaks Arabic sessions because the
    translated label no longer matches frappe.boot.workspace_sidebar_item.
    """
    sidebar_items = bootinfo.get("workspace_sidebar_item") or {}

    for sidebar in sidebar_items.values():
        for item in sidebar.get("items") or []:
            _translate_sidebar_item(item)


def _translate_sidebar_item(item):
    label = item.get("label")
    if label:
        item["label"] = frappe._(label)

    for child in item.get("nested_items") or []:
        _translate_sidebar_item(child)


def extend_bootinfo(bootinfo):
    if not frappe.session.user or frappe.session.user == "Guest":
        return bootinfo

    _translate_sidebar_labels(bootinfo)

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
