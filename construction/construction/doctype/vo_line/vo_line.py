import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class VOLine(Document):
    def validate_against_parent(self, parent):
        self.fetch_and_validate_scope(parent)
        self.calculate_quantities_and_values()
        self.validate_rate_change_rule()

    def fetch_and_validate_scope(self, parent):
        if self.line_type in ("Quantity Change", "Omission"):
            if not self.boq_item:
                frappe.throw(_("BOQ Item is required for VO line type {0}.").format(self.line_type))
            item = frappe.db.get_value(
                "BOQ Item",
                self.boq_item,
                ["boq_header", "structure", "quantity", "unit", "contract_unit_price"],
                as_dict=True,
            )
            if not item:
                frappe.throw(_("BOQ Item {0} does not exist.").format(self.boq_item))
            if item.boq_header != parent.boq_header:
                frappe.throw(_("VO Line BOQ Item must belong to the selected BOQ Header."))

            structure = frappe.db.get_value("BOQ Structure", item.structure, ["title", "wbs_code"], as_dict=True)
            self.wbs_code = structure.wbs_code
            self.title = structure.title
            self.unit = item.unit
            self.contract_qty = flt(item.quantity)
            self.contract_unit_price = flt(item.contract_unit_price)
            if self.line_type == "Omission":
                self.delta_qty = -1 * self.contract_qty

        elif self.line_type == "New Item":
            if self.boq_item:
                frappe.throw(_("BOQ Item must be empty for New Item VO lines."))
            if not self.title:
                frappe.throw(_("Title is required for New Item VO lines."))
            if not self.unit:
                frappe.throw(_("Unit is required for New Item VO lines."))
            if flt(self.delta_qty) <= 0:
                frappe.throw(_("New Item VO lines require a positive quantity."))
            if flt(self.revised_unit_price) <= 0:
                frappe.throw(_("New Item VO lines require an agreed unit price."))
            self.contract_qty = 0
            self.contract_unit_price = 0
            self.rate_change_triggered = 1
            self.wbs_code = self.wbs_code or self.get_next_new_item_wbs(parent)
        else:
            frappe.throw(_("Invalid VO line type: {0}.").format(self.line_type))

    def calculate_quantities_and_values(self):
        self.revised_qty = flt(self.contract_qty) + flt(self.delta_qty)
        if self.revised_qty < 0:
            frappe.throw(_("Revised quantity cannot be negative."))

        if flt(self.contract_qty):
            self.abs_change_pct = abs(flt(self.delta_qty)) / flt(self.contract_qty) * 100
        else:
            self.abs_change_pct = 100 if self.line_type == "New Item" else 0

        if self.line_type != "New Item":
            self.rate_change_triggered = 1 if self.abs_change_pct > 25 else 0
            if not self.rate_change_triggered:
                self.revised_unit_price = self.contract_unit_price

        self.contract_line_value = flt(self.contract_qty) * flt(self.contract_unit_price)
        self.revised_line_value = flt(self.revised_qty) * flt(self.revised_unit_price)
        self.line_delta_value = self.revised_line_value - self.contract_line_value

    def validate_rate_change_rule(self):
        if self.rate_change_triggered:
            if flt(self.revised_unit_price) <= 0 and self.line_type != "Omission":
                frappe.throw(_("Revised unit price is required when the VO rate change rule is triggered."))
            if not self.rate_change_justification and self.line_type != "Omission":
                frappe.throw(_("Rate change justification is required when quantity changes by more than 25 percent."))

        if self.line_type == "Omission":
            self.revised_unit_price = 0
            self.revised_line_value = 0
            self.line_delta_value = -1 * flt(self.contract_line_value)

    def get_next_new_item_wbs(self, parent):
        prefix = parent.vo_number or "VO-000"
        max_seq = 0
        for line in parent.lines:
            if line.name == self.name:
                continue
            code = str(line.wbs_code or "")
            if not code.startswith(f"{prefix}-"):
                continue
            suffix = code.rsplit("-", 1)[-1]
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))
        return f"{prefix}-{max_seq + 1:02d}"
