"""Align case-only legacy title aliases before Frappe converts them to Sidebar."""

import frappe


def execute():
    # This controller may exist in the new app code before its DocType has
    # been synced into an upgrading site's DB. Checking the DB for Sidebar
    # here would skip the repair before post-model-sync convert_sidebars.
    try:
        from frappe.desk.doctype.sidebar.sidebar import Sidebar
    except ImportError:
        return
    if not frappe.db.table_exists("Workspace Sidebar"):
        return

    changed = 0
    rows = frappe.get_all(
        "Workspace Sidebar",
        filters={"app": "construction", "for_user": ("is", "not set")},
        fields=["name", "title", "module"],
        limit_page_length=0,
    )
    for row in rows:
        if not row.module:
            continue
        owner = frappe.db.get_value("Module Def", {"name": row.module, "app_name": "construction"}, "name")
        # The converter groups rows by their stored module string. Its exact
        # casing is what Sidebar.validate compares, even when the linked
        # Module Def resolves through the DB's case-insensitive collation.
        module = row.module
        title = row.title or ""
        if not owner or title == module or title.casefold() != module.casefold():
            continue
        # Sidebar validates title == module with a case-sensitive comparison.
        # Keep the legacy record name, items and modified timestamp intact;
        # this store is now the converter's archive, not a live Sidebar.
        frappe.db.set_value("Workspace Sidebar", row.name, "title", module, update_modified=False)
        changed += 1
    if changed:
        frappe.clear_cache(doctype="Workspace Sidebar")
    print(f"[v9_17] Aligned {changed} legacy Construction sidebar title(s)")
