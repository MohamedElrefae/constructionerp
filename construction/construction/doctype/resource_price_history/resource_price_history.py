import frappe
from frappe.model.document import Document


class ResourcePriceHistory(Document):
    def validate(self):
        self.validate_rates()

    def validate_rates(self):
        if self.rate < 0:
            frappe.throw("Rate cannot be negative.")
        if self.exchange_rate and self.exchange_rate <= 0:
            frappe.throw("Exchange rate must be positive.")


def on_doctype_update():
    frappe.db.add_index("Resource Price History", ["item_code", "price_date"])
    frappe.db.add_index("Resource Price History", ["item_code", "supplier"])
    frappe.db.add_index("Resource Price History", ["source_doctype", "source_name"])
