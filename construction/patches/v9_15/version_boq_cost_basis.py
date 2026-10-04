"""Bind old cost history to its legacy arithmetic without repricing it."""

import frappe

from construction.services.boq_pricing import PRICING_RULE


def execute():
    # Patches can run before schema sync. These are additive standard fields.
    for doctype in ("boq_item", "boq_cost_analysis"):
        frappe.reload_doc("construction", "doctype", doctype, force=True)

    frappe.db.sql(
        """
        UPDATE `tabBOQ Cost Analysis`
        SET pricing_rule_version = %s
        WHERE docstatus > 0 AND COALESCE(pricing_rule_version, '') = ''
        """,
        "legacy-unversioned/v0",
    )
    # An old analysis has no reliable captured manual estimate. Preserve every
    # historical amount; reviewed conversion is a separate commercial operation.
    frappe.db.sql(
        """
        UPDATE `tabBOQ Item` item
        SET cost_basis = %s
        WHERE COALESCE(item.manual_cost_snapshot, '') = ''
          AND EXISTS (
            SELECT 1 FROM `tabBOQ Cost Analysis` analysis
            WHERE analysis.boq_item = item.name AND analysis.docstatus > 0
              AND analysis.pricing_rule_version = %s
          )
          AND NOT EXISTS (
            SELECT 1 FROM `tabBOQ Cost Analysis` active
            WHERE active.boq_item = item.name AND active.docstatus = 1
              AND active.analysis_status = 'Approved'
              AND active.pricing_rule_version = %s
          )
        """,
        ("Legacy Review", "legacy-unversioned/v0", PRICING_RULE),
    )
