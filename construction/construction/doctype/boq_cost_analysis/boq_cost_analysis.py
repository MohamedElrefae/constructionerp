import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class BOQCostAnalysis(Document):
    def validate(self):
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

    def validate_scope_context(self):
        if not self.company:
            frappe.throw(_("Company is required."))
        if self.boq_header:
            header_project = frappe.db.get_value("BOQ Header", self.boq_header, "project")
            if header_project:
                if self.project and header_project != self.project:
                    frappe.throw(
                        _("Project mismatch: Analysis project '{0}' does not match BOQ Header project '{1}'.").format(
                            self.project, header_project
                        )
                    )
                header_company = frappe.db.get_value("Project", header_project, "company")
                if header_company and header_company != self.company:
                    frappe.throw(
                        _("Company mismatch: Analysis company '{0}' does not match Project company '{1}'.").format(
                            self.company, header_company
                        )
                    )

    def calculate_totals(self):
        total_direct = 0.0
        for row in self.get("details") or []:
            qty = flt(row.qty_per_boq_unit)
            rate = flt(row.cost_rate)
            wastage = flt(row.wastage_pct)
            row.amount = qty * rate * (1 + wastage / 100.0)
            total_direct += row.amount

        self.total_direct_cost = total_direct
        analysis_qty = flt(self.analysis_qty) or 1.0
        unit_direct = total_direct / analysis_qty if analysis_qty else 0

        overhead_pct = flt(self.overhead_pct)
        profit_pct = flt(self.profit_pct)
        overhead_amount = unit_direct * overhead_pct / 100.0
        profit_amount = (unit_direct + overhead_amount) * profit_pct / 100.0

        self.total_unit_cost = unit_direct + overhead_amount + profit_amount
        self.suggested_sell_rate = self.total_unit_cost

    def validate_approvable(self):
        if self.analysis_status != "Draft":
            frappe.throw(_("Only Draft analyses can be submitted."))
        if not self.get("details"):
            frappe.throw(_("At least one cost detail row is required."))

    def deactivate_other_approved_analyses(self):
        existing = frappe.db.get_value(
            "BOQ Cost Analysis",
            {
                "boq_item": self.boq_item,
                "analysis_status": "Approved",
                "docstatus": 1,
                "name": ["!=", self.name],
            },
            "name",
        )
        if existing:
            doc = frappe.get_doc("BOQ Cost Analysis", existing)
            doc.db_set("analysis_status", "Superseded", update_modified=False)

    def update_boq_item_estimated_cost(self):
        if not self.boq_item:
            return
        item_doc = frappe.get_doc("BOQ Item", self.boq_item)
        item_doc.db_set("est_unit_cost", self.total_unit_cost, update_modified=False)
        item_doc.calculate_cost_buildup()
        item_doc.db_set(
            {
                "overhead_amount": flt(item_doc.overhead_amount),
                "profit_amount": flt(item_doc.profit_amount),
                "calculated_sell_price": flt(item_doc.calculated_sell_price),
                "est_line_total": flt(item_doc.quantity) * flt(self.total_unit_cost) * (flt(item_doc.factor) or 1.0),
            },
            update_modified=False,
        )
        self._refresh_boq_header_totals(item_doc.boq_header)

    def _refresh_boq_header_totals(self, boq_header):
        if not boq_header:
            return
        header = frappe.get_doc("BOQ Header", boq_header)
        header.recalculate_phase1_totals()

    def restore_prior_analysis_if_any(self):
        prior = frappe.db.get_value(
            "BOQ Cost Analysis",
            {
                "boq_item": self.boq_item,
                "analysis_status": "Superseded",
                "docstatus": 1,
                "name": ["!=", self.name],
            },
            "name",
            order_by="modified desc",
        )
        if prior:
            prior_doc = frappe.get_doc("BOQ Cost Analysis", prior)
            prior_doc.db_set("analysis_status", "Approved", update_modified=False)
            prior_doc.update_boq_item_estimated_cost()


def on_doctype_update():
    frappe.db.add_index("BOQ Cost Analysis", ["boq_item", "analysis_status"])
    frappe.db.add_index("BOQ Cost Analysis", ["boq_header", "analysis_status"])
