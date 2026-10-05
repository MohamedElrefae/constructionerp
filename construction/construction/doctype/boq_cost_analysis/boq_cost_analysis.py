import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from construction.services.boq_pricing import (
    PERCENT_FIELDS,
    PRICING_RULE,
    number,
    positive_factor,
    tender_amounts,
)
from construction.services.boq_transactions import current_boq_sql, lock_boq_item_header


class BOQCostAnalysis(Document):
    def before_insert(self):
        if self.get("supersedes_analysis"):
            frappe.throw(_("Previous approved analysis is managed by the approval service."))

    def validate(self):
        previous = self.get_doc_before_save()
        if (self.get("supersedes_analysis") or "") != ((previous.get("supersedes_analysis") if previous else None) or ""):
            frappe.throw(_("Previous approved analysis is managed by the approval service."))
        self.validate_boq_item()
        self.validate_scope_context()
        self.calculate_totals()

    def before_submit(self):
        self.validate_approvable()
        self.deactivate_other_approved_analyses()
        self.calculate_totals()
        self.update_boq_item_estimated_cost()

    def on_submit(self):
        self.db_set("analysis_status", "Approved", update_modified=False)
        self.db_set("approved_by", frappe.session.user, update_modified=False)
        self.db_set("approved_on", frappe.utils.now(), update_modified=False)

    def before_cancel(self):
        if self.boq_item:
            lock_boq_item_header(self.boq_item)
        self._restoration_target()  # fail before cancellation if the required evidence is missing
        # Self-links are immutable approval/amendment history, not downstream
        # transactions. Keep native cancellation checks for every other DocType.
        self.ignore_linked_doctypes = ["BOQ Cost Analysis"]
        self.db_set("analysis_status", "Cancelled", update_modified=False)

    def on_cancel(self):
        self.restore_prior_analysis_if_any()

    def validate_boq_item(self):
        if not self.boq_item:
            if not self.is_template:
                frappe.throw(_("BOQ Item is required for non-template analyses."))
            return
        if not frappe.db.exists("BOQ Item", self.boq_item):
            frappe.throw(_("BOQ Item {0} does not exist.").format(self.boq_item))
        actual_header = lock_boq_item_header(self.boq_item)
        item = frappe.get_doc("BOQ Item", self.boq_item, for_update=True)
        header = frappe.get_doc("BOQ Header", actual_header, for_update=True)
        for field, actual in (
            ("boq_header", actual_header),
            ("boq_structure", item.structure),
            ("project", header.project),
        ):
            if self.get(field) and self.get(field) != actual:
                frappe.throw(
                    _("Cost analysis {0} must match its BOQ Item.").format(self.meta.get_label(field))
                )
            self.set(field, actual)
        if frappe.session.user != "Administrator":
            frappe.has_permission("BOQ Item", "read", doc=item, throw=True)

    def validate_scope_context(self):
        if not self.company:
            frappe.throw(_("Company is required."))
        if self.boq_header:
            header_project = frappe.db.get_value("BOQ Header", self.boq_header, "project")
            if header_project:
                if self.project and header_project != self.project:
                    frappe.throw(
                        _(
                            "Project mismatch: Analysis project '{0}' does not match BOQ Header project '{1}'."
                        ).format(self.project, header_project)
                    )
                header_company = frappe.db.get_value("Project", header_project, "company")
                if header_company and header_company != self.company:
                    frappe.throw(
                        _(
                            "Company mismatch: Analysis company '{0}' does not match Project company '{1}'."
                        ).format(self.company, header_company)
                    )

    def calculate_totals(self):
        previous = self.get_doc_before_save()
        if previous and previous.docstatus == 1:
            return  # never reinterpret historical approved amounts during cancellation
        qty = number(self.analysis_qty, _("Analysis quantity"), positive=True)
        total_direct = 0.0
        for row in self.get("details") or []:
            resource_qty = number(row.qty_per_boq_unit, _("Resource quantity"))
            rate = number(row.cost_rate, _("Resource cost rate"))
            wastage = number(row.wastage_pct, _("Wastage percentage"), maximum=100)
            row.amount = number(resource_qty * rate * (1 + wastage / 100), _("Resource amount"))
            total_direct += row.amount
        self.total_direct_cost = number(total_direct, _("Direct resource cost"))
        self.total_unit_cost = self.total_direct_cost / qty
        for field in PERCENT_FIELDS:
            self.set(field, number(self.get(field), self.meta.get_label(field), maximum=100))
        self.suggested_sell_rate = tender_amounts(
            self.total_unit_cost, *(self.get(f) for f in PERCENT_FIELDS)
        )[3]
        self.pricing_rule_version = PRICING_RULE

    def validate_approvable(self):
        if self.analysis_status != "Draft":
            frappe.throw(_("Only Draft analyses can be submitted."))
        if not self.get("details"):
            frappe.throw(_("At least one cost detail row is required."))

    def deactivate_other_approved_analyses(self):
        if not self.boq_item:
            return

        lock_boq_item_header(self.boq_item)

        other_approved = current_boq_sql(
            """
            SELECT name FROM `tabBOQ Cost Analysis`
            WHERE boq_item = %(boq_item)s
              AND analysis_status = 'Approved'
              AND name != %(name)s
              AND docstatus = 1
            ORDER BY name
            FOR UPDATE NOWAIT
            """,
            {"boq_item": self.boq_item, "name": self.name},
            as_dict=True,
        )

        if len(other_approved) > 1:
            frappe.throw(_("Multiple approved analyses require reconciliation before a new approval."))
        item = frappe.get_doc("BOQ Item", self.boq_item, for_update=True)
        if item.get("cost_basis") == "Legacy Review":
            frappe.throw(
                _(
                    "Legacy cost basis requires reviewed conversion and restoration evidence before a new approval."
                )
            )
        for row in other_approved:
            if frappe.db.has_column("BOQ Cost Analysis", "pricing_rule_version"):
                if frappe.db.get_value("BOQ Cost Analysis", row.name, "pricing_rule_version") != PRICING_RULE:
                    frappe.throw(_("Previous legacy cost basis requires review before a new approval."))
        self.supersedes_analysis = other_approved[0].name if other_approved else None
        if not other_approved and (item.get("cost_basis") or "Manual") == "Manual" and not item.get("active_cost_analysis"):
            history = current_boq_sql(
                "SELECT name FROM `tabBOQ Cost Analysis` WHERE boq_item = %s AND docstatus > 0 LIMIT 1 FOR UPDATE NOWAIT",
                self.boq_item,
            )
            # Refresh a known manual basis after the owner edits it between
            # approval cycles. Never invent the pre-analysis basis of legacy data.
            if not history or item.get("manual_cost_snapshot"):
                snapshot = {
                    field: number(item.get(field), item.meta.get_label(field))
                    for field in ("est_unit_cost", *PERCENT_FIELDS)
                }
                snapshot.update(
                    schema="boq-manual-cost/v1",
                    captured_by=frappe.session.user,
                    captured_on=frappe.utils.now(),
                )
                if frappe.db.has_column("BOQ Item", "manual_cost_snapshot"):
                    item.db_set("manual_cost_snapshot", frappe.as_json(snapshot), update_modified=False)
        for row in other_approved:
            frappe.db.set_value(
                "BOQ Cost Analysis", row.name, "analysis_status", "Superseded", update_modified=False
            )

    def update_boq_item_estimated_cost(self):
        if not self.boq_item:
            return
        lock_boq_item_header(self.boq_item)
        item_doc = frappe.get_doc("BOQ Item", self.boq_item, for_update=True)
        if getattr(self, "pricing_rule_version", None) and self.pricing_rule_version != PRICING_RULE:
            frappe.throw(_("Legacy approved pricing requires reviewed conversion before restoration."))
        values = {field: self.get(field) for field in PERCENT_FIELDS}
        values.update(
            est_unit_cost=self.total_unit_cost, cost_basis="Approved Analysis", active_cost_analysis=self.name
        )
        item_doc.update(values)
        item_doc.calculate_cost_buildup()
        for field in (
            "overhead_amount",
            "profit_amount",
            "tender_tax_amount",
            "calculated_sell_price",
            "est_line_total",
        ):
            values[field] = item_doc.get(field)
        persisted_values = {f: v for f, v in values.items() if frappe.db.has_column("BOQ Item", f)}
        if persisted_values:
            item_doc.db_set(persisted_values, update_modified=False)
        self._refresh_boq_header_totals(item_doc.boq_header)

    def _refresh_boq_header_totals(self, boq_header):
        if not boq_header:
            return
        header = frappe.get_doc("BOQ Header", boq_header)
        header.recalculate_phase1_totals()

    def _restoration_target(self):
        if not self.boq_item:
            return None
        previous = self.get_doc_before_save()
        if previous and previous.analysis_status != "Approved":
            return None
        lock_boq_item_header(self.boq_item)
        active = current_boq_sql(
            "SELECT name FROM `tabBOQ Cost Analysis` WHERE boq_item = %s AND analysis_status = 'Approved' AND docstatus = 1 FOR UPDATE NOWAIT",
            self.boq_item,
        )
        if len(active) > 1:
            frappe.throw(_("Multiple approved analyses require reconciliation before cancellation."))
        if any(row[0] != self.name for row in active):
            return None  # cancelling superseded history must not replace the active basis
        target = self.get("supersedes_analysis")
        if not target and not frappe.db.has_column("BOQ Cost Analysis", "supersedes_analysis"):
            target = frappe.db.get_value(
                "BOQ Cost Analysis",
                {"boq_item": self.boq_item, "analysis_status": "Superseded", "docstatus": 1},
                "name",
                order_by="creation desc",
            )
        visited = {self.name}
        while target:
            if target in visited or len(visited) >= 1000:
                frappe.throw(_("Cost approval history requires reconciliation."))
            visited.add(target)
            prior = frappe.get_doc("BOQ Cost Analysis", target, for_update=True)
            if prior.boq_item != self.boq_item:
                frappe.throw(_("Previous cost analysis belongs to another BOQ Item."))
            if prior.docstatus == 1 and prior.analysis_status == "Superseded":
                if getattr(prior, "pricing_rule_version", None) and prior.pricing_rule_version != PRICING_RULE:
                    frappe.throw(_("Previous legacy cost basis requires review before cancellation."))
                return prior
            target = prior.get("supersedes_analysis")
        if not item.get("manual_cost_snapshot"):
            if not frappe.db.has_column("BOQ Item", "manual_cost_snapshot"):
                return None
            frappe.throw(
                _("Prior manual estimate is unavailable. Review the legacy cost basis before cancellation.")
            )
        try:
            snapshot = json.loads(item.get("manual_cost_snapshot"))
            if not isinstance(snapshot, dict) or snapshot.get("schema") != "boq-manual-cost/v1":
                raise ValueError
            for field in ("est_unit_cost", *PERCENT_FIELDS):
                number(snapshot[field], field, maximum=100 if field in PERCENT_FIELDS else None)
        except (ValueError, TypeError, KeyError):
            frappe.throw(_("Prior manual estimate evidence requires review before cancellation."))
        return snapshot

    def restore_prior_analysis_if_any(self):
        target = self._restoration_target()
        if target is None:
            return
        if not isinstance(target, dict):
            target.db_set("analysis_status", "Approved", update_modified=False)
            target.update_boq_item_estimated_cost()
            return
        item = frappe.get_doc("BOQ Item", self.boq_item, for_update=True)
        values = {field: target[field] for field in ("est_unit_cost", *PERCENT_FIELDS)}
        values.update(cost_basis="Manual", active_cost_analysis=None)
        item.update(values)
        item.calculate_cost_buildup()
        for field in (
            "overhead_amount",
            "profit_amount",
            "tender_tax_amount",
            "calculated_sell_price",
            "est_line_total",
        ):
            values[field] = item.get(field)
        persisted_values = {f: v for f, v in values.items() if frappe.db.has_column("BOQ Item", f)}
        if persisted_values:
            item.db_set(persisted_values, update_modified=False)
        self._refresh_boq_header_totals(item.boq_header)


def on_doctype_update():
    frappe.db.add_index("BOQ Cost Analysis", ["boq_item", "analysis_status"])
    frappe.db.add_index("BOQ Cost Analysis", ["boq_header", "analysis_status"])
