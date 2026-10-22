"""Add BOQ Header + WBS Code uniqueness after read-only health preflight."""

import frappe

from construction.services.boq_wbs_health import ensure_wbs_unique_constraint


def execute():
    if not frappe.db.table_exists("tabBOQ Structure"):
        return

    ensure_wbs_unique_constraint()
    frappe.db.commit()
