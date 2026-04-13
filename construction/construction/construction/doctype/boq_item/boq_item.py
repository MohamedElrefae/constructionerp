import frappe
from frappe.model.document import Document


class BOQItem(Document):
    def validate(self):
        self.validate_leaf_only()
        self.enforce_boq_status()
        self.fetch_cost_item_rate()
        self.calculate_line_total()

    def on_update(self):
        self.update_header_total()

    def on_trash(self):
        self.update_header_total()

    def validate_leaf_only(self):
        if self.structure:
            is_group = frappe.db.get_value("BOQ Structure", self.structure, "is_group")
            if is_group:
                frappe.throw("BOQ Item can only be linked to leaf nodes (is_group=0).")

    def enforce_boq_status(self):
        if not self.boq_header:
            return
        status = frappe.db.get_value("BOQ Header", self.boq_header, "status")
        if status == "Locked":
            frappe.throw("Cannot modify BOQ Item: BOQ is Locked.")
        elif status == "Frozen":
            frappe.throw("Cannot modify BOQ Item: BOQ is Frozen.")

    def fetch_cost_item_rate(self):
        # Cost Item reference removed - est_unit_cost can be set manually
        pass

    def calculate_line_total(self):
        qty = self.quantity or 0
        price = self.contract_unit_price or 0
        factor = self.factor or 1.0
        self.line_total = qty * price * factor

    def update_header_total(self):
        if not self.boq_header:
            return
        total = frappe.db.sql(
            "SELECT COALESCE(SUM(line_total), 0) FROM `tabBOQ Item` WHERE boq_header = %s",
            self.boq_header
        )
        val = total[0][0] if total and total[0][0] else 0
        frappe.db.set_value("BOQ Header", self.boq_header, "total_contract_value", val)
        frappe.db.set_value("BOQ Header", self.boq_header, "total_budgeted_cost", val)
