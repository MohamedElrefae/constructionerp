import frappe
from frappe.model.document import Document


class BOQHeader(Document):
	VALID_TRANSITIONS = {"Draft": "Pricing", "Pricing": "Frozen", "Frozen": "Locked"}

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
				frappe.throw("Status can only move forward: Draft → Pricing → Frozen → Locked.")

	def calculate_total_value(self):
		if self.is_new():
			self.total_contract_value = 0
			self.total_budgeted_cost = 0
			return
		total = frappe.db.sql(
			"SELECT COALESCE(SUM(line_total), 0) FROM `tabBOQ Item` WHERE boq_header = %s", self.name
		)
		val = total[0][0] if total and total[0][0] else 0
		self.total_contract_value = val
		self.total_budgeted_cost = val
