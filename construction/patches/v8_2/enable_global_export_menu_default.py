"""
Patch v8_2: Enable Global Export Menu Default

Sets the enable_global_export_menu field to 1 (enabled) on any existing
Construction Settings record so users can use the global export menu
immediately after migrating.
"""

import frappe


def execute():
    """
    Enable the global export menu toggle on existing installations.
    Uses frappe.db.set_value (no timestamp touch) per AGENTS.md §4.6.
    """
    try:
        # Only set to 1 if the field currently holds a falsy value.
        # frappe.db.set_value with update_modified=False avoids triggering
        # timestamp conflicts on the singleton settings document.
        current = frappe.db.get_single_value(
            "Construction Settings", "enable_global_export_menu"
        )
        if not current:
            frappe.db.set_value(
                "Construction Settings",
                None,
                "enable_global_export_menu",
                1,
                update_modified=False,
            )
    except Exception:
        # Graceful skip if settings not yet available (e.g. fresh install mid-migrate)
        pass
