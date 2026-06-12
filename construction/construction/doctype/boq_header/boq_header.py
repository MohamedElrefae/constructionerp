import frappe
from frappe import _
from frappe.model.document import Document

from construction.api.scope_context_api import get_user_scope_context


class BOQHeader(Document):
    VALID_TRANSITIONS = {
        "Draft": "Pricing",
        "Pricing": "Frozen",
        "Frozen": "Locked",
    }

    def validate(self):
        self.validate_status_transition()
        self.sync_project_from_scope_context()
        self.sync_project_name()
        self.calculate_total_value()

    def sync_project_from_scope_context(self):
        scope_context = get_user_scope_context()
        scope_project = scope_context.project if scope_context else None

        if self.is_new():
            if scope_project:
                self.project = scope_project
                return
            frappe.throw(
                _(
                    "Project comes from Scope Context. Set a Project in the top bar before creating a BOQ Header."
                )
            )

        if not self.project:
            if scope_project:
                self.project = scope_project
                return
            frappe.throw(
                _(
                    "Project comes from Scope Context. Set a Project in the top bar before creating a BOQ Header."
                )
            )

    def sync_project_name(self):
        if not self.project:
            self.project_name = None
            return

        project = frappe.get_all(
            "Project",
            filters={"name": self.project},
            fields=["project_name"],
            limit=1,
        )
        if not project:
            frappe.throw(_("Project {0} does not exist.").format(self.project))

        self.project_name = project[0].project_name or self.project

    def on_update(self):
        if self.status == "Locked":
            old_status = self.get_doc_before_save().status if self.get_doc_before_save() else "Draft"
            if old_status != "Locked":
                self.db_set("locked_by", frappe.session.user, update_modified=False)
                self.db_set("locked_date", frappe.utils.now(), update_modified=False)
                # Create baseline quantity revisions
                from construction.services.quantity_revisions import create_lock_baseline
                create_lock_baseline(self.name)

    def validate_status_transition(self):
        if self.is_new():
            return
        old_doc = self.get_doc_before_save()
        old_status = old_doc.status if old_doc else "Draft"
        if old_status != self.status:
            if self.VALID_TRANSITIONS.get(old_status) != self.status:
                frappe.throw(_("Status can only move forward: Draft → Pricing → Frozen → Locked."))

    def calculate_total_value(self):
        """Compute all Phase 1 roll-up totals including total_revised_value.
        
        Variation items are excluded from contract totals but included in revised totals.
        """
        if self.is_new():
            self.total_contract_value = 0
            self.total_estimated_value = 0
            self.total_budgeted_cost = 0
            self.total_revised_value = 0
            return
        totals = frappe.db.sql(
            """
			SELECT
				COALESCE(SUM(CASE WHEN is_variation_item = 0 THEN line_total ELSE 0 END), 0),
				COALESCE(SUM(CASE WHEN is_variation_item = 0 THEN est_line_total ELSE 0 END), 0),
				COALESCE(SUM(CASE WHEN is_variation_item = 0 THEN quantity * est_unit_cost * COALESCE(factor, 1.0) ELSE 0 END), 0),
				COALESCE(SUM(COALESCE(current_revised_qty, quantity) * COALESCE(current_revised_unit_price, contract_unit_price) * COALESCE(factor, 1.0)), 0)
			FROM `tabBOQ Item`
			WHERE boq_header = %s
		""",
            self.name,
        )
        if totals and totals[0]:
            self.total_contract_value = totals[0][0]
            self.total_estimated_value = totals[0][1]
            self.total_budgeted_cost = totals[0][2]
            self.total_revised_value = totals[0][3]
        else:
            self.total_contract_value = 0
            self.total_estimated_value = 0
            self.total_budgeted_cost = 0
            self.total_revised_value = 0

    def recalculate_phase1_totals(self):
        """Recalculate all Phase 1 roll-up totals from BOQ Items.
        Called by BOQ Item on_update and on_trash.
        Uses a single SQL query with 4 SUMs and db_set to avoid
        triggering a full save cycle.
        
        Variation items are excluded from contract totals but included in revised totals.
        """
        totals = frappe.db.sql(
            """
			SELECT
				COALESCE(SUM(CASE WHEN is_variation_item = 0 THEN line_total ELSE 0 END), 0),
				COALESCE(SUM(CASE WHEN is_variation_item = 0 THEN est_line_total ELSE 0 END), 0),
				COALESCE(SUM(CASE WHEN is_variation_item = 0 THEN quantity * est_unit_cost * COALESCE(factor, 1.0) ELSE 0 END), 0),
                COALESCE(SUM(COALESCE(current_revised_qty, quantity) * COALESCE(current_revised_unit_price, contract_unit_price) * COALESCE(factor, 1.0)), 0)
			FROM `tabBOQ Item`
			WHERE boq_header = %s
		""",
            self.name,
        )
        tcv = totals[0][0] if totals and totals[0] else 0
        tev = totals[0][1] if totals and totals[0] else 0
        tbc = totals[0][2] if totals and totals[0] else 0
        trv = totals[0][3] if totals and totals[0] else 0

        self.db_set("total_contract_value", tcv, update_modified=False)
        self.db_set("total_estimated_value", tev, update_modified=False)
        self.db_set("total_budgeted_cost", tbc, update_modified=False)
        self.db_set("total_revised_value", trv, update_modified=False)
