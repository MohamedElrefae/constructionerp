"""One-time patch: migrate enable_scope_branch → enable_scope_cost_center.

The field was renamed in construction_settings.json (Phase 1.4).
Frappe does NOT auto-copy data on field rename — the old column persists
but is no longer managed. This patch copies any existing value so that
previously-enabled scope-branch users don't lose their configuration.

Skip conditions:
- Construction Settings table doesn't exist yet
- Old column enable_scope_branch doesn't exist
- New column enable_scope_cost_center already has a truthy value (preserve explicit setting)
"""

import frappe


def execute():
    if not frappe.db.table_exists("tabConstruction Settings"):
        return
    if not frappe.db.has_column("Construction Settings", "enable_scope_branch"):
        return

    old_val = frappe.db.get_value(
        "Construction Settings", "Construction Settings", "enable_scope_branch"
    )
    if not old_val:
        return

    new_val = frappe.db.get_value(
        "Construction Settings", "Construction Settings", "enable_scope_cost_center"
    )
    if new_val:
        return

    frappe.db.set_value(
        "Construction Settings",
        "Construction Settings",
        "enable_scope_cost_center",
        1,
    )
    frappe.db.commit()
