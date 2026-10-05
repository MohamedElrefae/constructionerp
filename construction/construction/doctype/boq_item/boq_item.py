import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from construction.services.boq_operational import validate_boq_item_stage_distribution
from construction.services.boq_pricing import (
    PERCENT_FIELDS,
    PRICING_RULE,
    number,
    positive_factor,
    tender_amounts,
)
from construction.services.boq_transactions import current_boq_sql, lock_boq_header


class BOQItem(Document):
    PRICING_EDITABLE = frozenset(
        {
            "est_unit_price",
            "contract_unit_price",
            "factor",
            "cost_item",
            "item_type",
            "overhead_pct",
            "profit_pct",
            "tender_tax_pct",
            "est_unit_cost",
            "owner_page",
            "owner_ref_no",
            "owner_file_ref",
            "has_stages",
        }
    )

    PHASE1_STEPS = [
        "validate_leaf_only",
        "enforce_boq_status",
        "validate_input_guards",
        "validate_stage_distribution",
        "fetch_cost_data",
        "calculate_cost_buildup",
        "calculate_line_total",
        "validate_output_guards",
    ]

    def validate(self):
        previous = self.get_doc_before_save()
        headers = {self.boq_header}
        if previous:
            headers.add(previous.boq_header)
        for header in sorted(filter(None, headers)):
            lock_boq_header(header)
        self.validate_cost_provenance()
        for step in self.PHASE1_STEPS:
            getattr(self, step)()

    def on_update(self):
        self._trigger_header_rollup()

    def on_trash(self):
        # Frappe runs on_trash before link checks and SQL deletion.
        # Acquire header lock for concurrency protection (G05), but defer rollup to after_delete (G01).
        lock_boq_header(self.boq_header)

    def after_delete(self):
        # Frappe runs on_trash before link checks and SQL deletion. Aggregate
        # only after the row is removed, inside the same transaction.
        self._trigger_header_rollup()

    def _trigger_header_rollup(self):
        if getattr(frappe.flags, "defer_boq_rollups", False) or getattr(
            self.flags, "defer_boq_rollups", False
        ):
            return
        if not self.boq_header:
            return
        previous = self.get_doc_before_save()
        headers = {self.boq_header}
        if previous:
            headers.add(previous.boq_header)
        for header_name in sorted(filter(None, headers)):
            header = frappe.get_doc("BOQ Header", header_name)
            header.recalculate_phase1_totals()

    # --- Step 1: Leaf-only check ---
    def validate_leaf_only(self):
        """Verify the linked structure node is a leaf (is_group=0)."""
        if self.structure:
            is_group = frappe.db.get_value("BOQ Structure", self.structure, "is_group")
            if is_group:
                frappe.throw(_("BOQ Item can only be linked to leaf nodes (is_group=0)."))

    # --- Step 2: Status enforcement ---
    def enforce_boq_status(self):
        """Enforce field-level edit restrictions based on BOQ Header status.
        Reads status from DB at validation time for race-condition safety.
        """
        if not self.boq_header:
            return
        if self.flags.get("ignore_boq_status_for_variation") and self.is_variation_item:
            return
        status = lock_boq_header(self.boq_header).status
        if status == "Locked":
            frappe.throw(_("Cannot modify BOQ Item: BOQ is Locked."))
        if status == "Frozen":
            frappe.throw(_("Cannot modify BOQ Item: BOQ is Frozen."))
        if status == "Pricing":
            old_doc = self.get_doc_before_save()
            if not old_doc:
                return  # New doc in Pricing status — allow all fields
            for field in self.meta.get_valid_columns():
                if field in self.PRICING_EDITABLE:
                    continue
                if field in (
                    "name",
                    "modified",
                    "modified_by",
                    "creation",
                    "owner",
                    "docstatus",
                    "idx",
                    "_user_tags",
                    "_comments",
                    "_assign",
                    "_liked_by",
                ):
                    continue
                old_val = old_doc.get(field)
                new_val = self.get(field)
                if self._field_value_changed(field, old_val, new_val):
                    frappe.throw(
                        _(
                            "Cannot modify field '{0}': BOQ is in Pricing status. "
                            "Only pricing-related fields can be edited."
                        ).format(field)
                    )

    def _field_value_changed(self, fieldname, old_val, new_val):
        df = self.meta.get_field(fieldname)
        fieldtype = df.fieldtype if df else None

        if fieldtype in ("Float", "Currency", "Percent"):
            return abs(flt(old_val) - flt(new_val)) > 0.000001
        if fieldtype in ("Int", "Check"):
            return cint(old_val) != cint(new_val)

        return (old_val or "") != (new_val or "")

    # --- Step 3: Input guards ---
    def validate_input_guards(self):
        self.factor = positive_factor(self.factor)
        for field in ("quantity", "est_unit_cost", "est_unit_price", "contract_unit_price"):
            self.set(field, number(self.get(field), self.meta.get_label(field)))
        for field in PERCENT_FIELDS:
            self.set(field, number(self.get(field), self.meta.get_label(field), maximum=100))

    def validate_cost_provenance(self):
        if not frappe.db.has_column("BOQ Item", "cost_basis"):
            return
        previous = self.get_doc_before_save()
        if not previous and not self.get("cost_basis"):
            self.cost_basis = "Manual"
        if previous and getattr(previous, "cost_basis", None) == "Legacy Review":
            frappe.throw(_("Legacy cost basis requires a reviewed conversion before this item can be saved."))
        for field in ("cost_basis", "active_cost_analysis", "manual_cost_snapshot"):
            expected = previous.get(field) if previous else ("Manual" if field == "cost_basis" else None)
            if (self.get(field) or "") != (expected or ""):
                frappe.throw(_("Cost provenance is managed by cost approval and cancellation."))
        if previous and getattr(previous, "active_cost_analysis", None):
            for field in ("est_unit_cost", *PERCENT_FIELDS):
                if self._field_value_changed(field, previous.get(field), self.get(field)):
                    frappe.throw(_("Approved cost and pricing percentages require a new cost analysis."))

    def validate_stage_distribution(self):
        validate_boq_item_stage_distribution(self)

    # --- Step 4: Fetch approved cost data ---
    def fetch_cost_data(self):
        """Fetch est_unit_cost from approved BOQ Cost Analysis.

        If an approved BOQ Cost Analysis exists, use its total_unit_cost.
        If none exists, preserve the current est_unit_cost value during saves.
        """
        approved_cost = self._get_approved_analysis_unit_cost()
        if approved_cost is not None:
            self.est_unit_cost = approved_cost
            return

        if self.is_new():
            self.est_unit_cost = self.get("est_unit_cost") or 0

    def _get_approved_analysis_unit_cost(self):
        """Query approved BOQ Cost Analysis for total_unit_cost."""
        if not self.name or not frappe.db.exists("DocType", "BOQ Cost Analysis"):
            return None
        approved = current_boq_sql(
            """SELECT name FROM `tabBOQ Cost Analysis`
            WHERE boq_item = %s AND analysis_status = 'Approved' AND docstatus = 1
            ORDER BY name LIMIT 2 FOR UPDATE NOWAIT""",
            self.name,
        )
        if len(approved) > 1:
            frappe.throw(_("Multiple approved analyses require reconciliation before repricing this item."))
        if approved:
            analysis = frappe.get_doc("BOQ Cost Analysis", approved[0][0], for_update=True)
            if getattr(analysis, "pricing_rule_version", None) and analysis.pricing_rule_version != PRICING_RULE:
                frappe.throw(_("Legacy approved pricing requires review before repricing this item."))
            for field in PERCENT_FIELDS:
                self.set(field, analysis.get(field))
            return number(analysis.total_unit_cost, _("Approved direct unit cost"))
        return None

    # --- Step 5: Cost buildup ---
    def calculate_cost_buildup(self):
        """Compute overhead, profit, calculated sell price, and estimated line total."""
        factor = positive_factor(self.factor)
        (self.overhead_amount, self.profit_amount, self.tender_tax_amount, self.calculated_sell_price) = (
            tender_amounts(self.est_unit_cost, self.overhead_pct, self.profit_pct, self.tender_tax_pct)
        )
        self.est_line_total = (
            number(self.quantity, _("Quantity")) * number(self.est_unit_cost, _("Direct unit cost")) * factor
        )

    # --- Step 6: Line total ---
    def calculate_line_total(self):
        """Compute line_total = quantity × contract_unit_price × factor."""
        quantity = flt(self.quantity)
        price = flt(self.contract_unit_price)
        factor = positive_factor(self.factor)
        self.line_total = quantity * price * factor
        if (
            not self.last_quantity_revision
            and frappe.db.get_value("BOQ Header", self.boq_header, "status") != "Locked"
        ):
            # Before the first baseline there is no separate approved quantity.
            # Keep the current projection aligned with normal estimate edits.
            self.current_revised_qty = quantity
            self.current_revised_unit_price = price

    # --- Step 7: Output guards ---
    def validate_output_guards(self):
        """Defensively validate that all computed fields are non-negative."""
        output_fields = [
            "overhead_amount",
            "profit_amount",
            "tender_tax_amount",
            "calculated_sell_price",
            "est_line_total",
            "line_total",
        ]
        for field in output_fields:
            number(self.get(field), self.meta.get_label(field))


def on_doctype_update():
    frappe.db.add_index("BOQ Item", ["boq_header"])
