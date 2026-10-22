import frappe
from frappe import _
from frappe.model.document import Document

from construction.api.scope_context_api import get_user_scope_context
from construction.services.boq_transactions import lock_boq_header, read_boq_totals


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
        try:
            scope_context_enabled = bool(
                frappe.db.get_single_value("Construction Settings", "enable_scope_context") or False
            )
        except Exception:
            scope_context_enabled = False

        if not scope_context_enabled:
            return

        scope_context = get_user_scope_context()
        scope_project = scope_context.project if scope_context else None

        if self.project:
            if (
                scope_project
                and self.project != scope_project
                and frappe.session.user != "Administrator"
                and not self.flags.ignore_permissions
                and "System Manager" not in frappe.get_roles()
            ):
                frappe.throw(
                    _(
                        "Cannot create BOQ Header for Project '{0}' outside active Scope Context '{1}'."
                    ).format(self.project, scope_project),
                    frappe.PermissionError,
                )
            return
        elif scope_project:
            self.project = scope_project
            return

        frappe.throw(
            _("Project comes from Scope Context. Set a Project in the top bar before creating a BOQ Header.")
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
        totals = read_boq_totals(self.name)
        (
            self.total_contract_value,
            self.total_estimated_value,
            self.total_budgeted_cost,
            self.total_revised_value,
        ) = totals

    def recalculate_phase1_totals(self):
        """Recalculate all Phase 1 roll-up totals from BOQ Items.
        Called by BOQ Item on_update and after_delete.
        Uses a guarded current read with 4 SUMs and db_set to avoid
        triggering a full save cycle.

        Variation items are excluded from contract totals but included in revised totals.
        """
        totals = read_boq_totals(self.name)
        self.db_set(
            dict(
                zip(
                    (
                        "total_contract_value",
                        "total_estimated_value",
                        "total_budgeted_cost",
                        "total_revised_value",
                    ),
                    totals,
                    strict=True,
                )
            ),
            update_modified=False,
        )
        self.recalculate_structure_rollups()

    def recalculate_structure_rollups(self):
        """Sync BOQ Structure row roll-up fields for list/tree display."""
        if not self.name:
            return

        lock_boq_header(self.name)
        frappe.db.sql(
            """
            UPDATE `tabBOQ Structure` target
            JOIN (
                SELECT
                    s.name AS structure_name,
                    COUNT(DISTINCT i.name) AS item_count,
                    COALESCE(SUM(CASE WHEN i.docstatus < 2 THEN i.line_total ELSE 0 END), 0) AS total_contract_value,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN i.docstatus < 2 THEN i.quantity * i.est_unit_cost * COALESCE(i.factor, 1.0)
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_budgeted_cost
                FROM `tabBOQ Structure` s
                LEFT JOIN `tabBOQ Structure` d
                    ON d.boq_header = s.boq_header
                   AND d.lft >= s.lft
                   AND d.rgt <= s.rgt
                   AND d.docstatus < 2
                LEFT JOIN `tabBOQ Item` i
                    ON i.structure = d.name
                   AND i.docstatus < 2
                WHERE s.boq_header = %(header)s
                  AND s.docstatus < 2
                GROUP BY s.name
            ) agg ON target.name = agg.structure_name
            SET target.item_count = agg.item_count,
                target.total_contract_value = agg.total_contract_value,
                target.total_budgeted_cost = agg.total_budgeted_cost
            """,
            {"header": self.name},
        )
