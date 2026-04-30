# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


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
			"owner_page",
			"owner_ref_no",
			"owner_file_ref",
		}
	)

	PHASE1_STEPS = [
		"validate_leaf_only",
		"enforce_boq_status",
		"validate_input_guards",
		"fetch_cost_item_data",
		"calculate_cost_buildup",
		"calculate_line_total",
		"validate_output_guards",
	]

	def validate(self):
		for step in self.PHASE1_STEPS:
			getattr(self, step)()

	def on_update(self):
		self._trigger_header_rollup()

	def on_trash(self):
		self._trigger_header_rollup()

	def _trigger_header_rollup(self):
		if not self.boq_header:
			return
		header = frappe.get_doc("BOQ Header", self.boq_header)
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
		status = frappe.db.get_value("BOQ Header", self.boq_header, "status")
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
				if str(old_val or "") != str(new_val or ""):
					frappe.throw(
						_(
							"Cannot modify field '{0}': BOQ is in Pricing status. "
							"Only pricing-related fields can be edited."
						).format(field)
					)

	# --- Step 3: Input guards ---
	def validate_input_guards(self):
		"""Enforce non-negative guards on user-editable inputs and range guards on percentages."""
		non_negative_fields = [
			"quantity",
			"factor",
			"est_unit_cost",
			"est_unit_price",
			"contract_unit_price",
		]
		for field in non_negative_fields:
			val = self.get(field) or 0
			if val < 0:
				frappe.throw(_("Field '{0}' must be non-negative. Got: {1}").format(field, val))
		pct_fields = ["overhead_pct", "profit_pct"]
		for field in pct_fields:
			val = self.get(field) or 0
			if val < 0 or val > 100:
				frappe.throw(_("Field '{0}' must be between 0 and 100. Got: {1}").format(field, val))

	# --- Step 4: Fetch CostItem data ---
	def fetch_cost_item_data(self):
		"""Fetch est_unit_cost from CostItem. Set to zero if no cost_item linked.
		Gracefully handles the case where CostItem DocType is not yet deployed.
		"""
		if self.cost_item:
			try:
				if frappe.db.exists("DocType", "CostItem"):
					cost = frappe.db.get_value("CostItem", self.cost_item, "total_direct_cost")
					self.est_unit_cost = cost or 0
				else:
					self.est_unit_cost = 0
			except Exception:
				self.est_unit_cost = 0
		else:
			self.est_unit_cost = 0

	# --- Step 5: Cost buildup ---
	def calculate_cost_buildup(self):
		"""Compute overhead, profit, calculated sell price, and estimated line total."""
		est_unit_cost = self.est_unit_cost or 0
		overhead_pct = self.overhead_pct or 0
		profit_pct = self.profit_pct or 0
		quantity = self.quantity or 0
		factor = self.factor or 1.0

		self.overhead_amount = est_unit_cost * overhead_pct / 100
		self.profit_amount = (est_unit_cost + self.overhead_amount) * profit_pct / 100
		self.calculated_sell_price = est_unit_cost + self.overhead_amount + self.profit_amount
		self.est_line_total = quantity * est_unit_cost * factor

	# --- Step 6: Line total ---
	def calculate_line_total(self):
		"""Compute line_total = quantity × contract_unit_price × factor."""
		quantity = self.quantity or 0
		price = self.contract_unit_price or 0
		factor = self.factor or 1.0
		self.line_total = quantity * price * factor

	# --- Step 7: Output guards ---
	def validate_output_guards(self):
		"""Defensively validate that all computed fields are non-negative."""
		output_fields = [
			"overhead_amount",
			"profit_amount",
			"calculated_sell_price",
			"est_line_total",
			"line_total",
		]
		for field in output_fields:
			val = self.get(field) or 0
			if val < 0:
				frappe.throw(_("Computed field '{0}' must be non-negative. Got: {1}").format(field, val))


def on_doctype_update():
	frappe.db.add_index("BOQ Item", ["boq_header"])
