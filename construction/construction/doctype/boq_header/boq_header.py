# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BOQHeader(Document):
    VALID_TRANSITIONS = {
        "Draft": "Pricing",
        "Pricing": "Frozen",
        "Frozen": "Locked",
    }

    def validate(self):
        self.validate_status_transition()
        self.calculate_total_value()

    def on_update(self):
        if self.status == "Locked" and self.has_value_changed("status"):
            self.db_set("locked_by", frappe.session.user, update_modified=False)
            self.db_set("locked_date", frappe.utils.now(), update_modified=False)

    def validate_status_transition(self):
        if self.is_new():
            return
        old_doc = self.get_doc_before_save()
        old_status = old_doc.status if old_doc else "Draft"
        if old_status != self.status:
            if self.VALID_TRANSITIONS.get(old_status) != self.status:
                frappe.throw(
                    _("Status can only move forward: Draft → Pricing → Frozen → Locked.")
                )

    def calculate_total_value(self):
        """Compute all 3 Phase 1 roll-up totals during header validate."""
        if self.is_new():
            self.total_contract_value = 0
            self.total_estimated_value = 0
            self.total_budgeted_cost = 0
            return
        totals = frappe.db.sql("""
            SELECT
                COALESCE(SUM(line_total), 0),
                COALESCE(SUM(est_line_total), 0),
                COALESCE(SUM(quantity * est_unit_cost * COALESCE(factor, 1.0)), 0)
            FROM `tabBOQ Item`
            WHERE boq_header = %s
        """, self.name)
        if totals and totals[0]:
            self.total_contract_value = totals[0][0]
            self.total_estimated_value = totals[0][1]
            self.total_budgeted_cost = totals[0][2]
        else:
            self.total_contract_value = 0
            self.total_estimated_value = 0
            self.total_budgeted_cost = 0

    def recalculate_phase1_totals(self):
        """Recalculate all Phase 1 roll-up totals from BOQ Items.
        Called by BOQ Item on_update and on_trash.
        Uses a single SQL query with 3 SUMs and db_set to avoid
        triggering a full save cycle.
        """
        totals = frappe.db.sql("""
            SELECT
                COALESCE(SUM(line_total), 0),
                COALESCE(SUM(est_line_total), 0),
                COALESCE(SUM(quantity * est_unit_cost * COALESCE(factor, 1.0)), 0)
            FROM `tabBOQ Item`
            WHERE boq_header = %s
        """, self.name)
        tcv = totals[0][0] if totals and totals[0] else 0
        tev = totals[0][1] if totals and totals[0] else 0
        tbc = totals[0][2] if totals and totals[0] else 0

        self.db_set("total_contract_value", tcv, update_modified=False)
        self.db_set("total_estimated_value", tev, update_modified=False)
        self.db_set("total_budgeted_cost", tbc, update_modified=False)
