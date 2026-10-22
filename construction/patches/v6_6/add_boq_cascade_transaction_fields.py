"""Add BOQ cascade transaction fields, indexes, and rollout defaults."""

import frappe

from construction.install import setup_boq_integration, setup_boq_rollout_mode


def execute():
    setup_boq_integration()
    setup_boq_rollout_mode()
    frappe.db.commit()
    frappe.clear_cache()
