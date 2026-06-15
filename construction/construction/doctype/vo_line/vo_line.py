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
            # Auto-fill boq_item from boq_structure if boq_structure is set but boq_item is not
            if self.boq_structure and not self.boq_item:
                self.boq_item = frappe.db.get_value("BOQ Item", {"structure": self.boq_structure}, "name")

            if not self.boq_item:
                frappe.throw(_("BOQ Item is required for VO line type {0}.").format(self.line_type))
            item = frappe.db.get_value(
                "BOQ Item",
                self.boq_item,
                ["boq_header", "structure", "quantity", "current_revised_qty", "unit", "contract_unit_price"],
                as_dict=True,
            )
            if not item:
                frappe.throw(_("BOQ Item {0} does not exist.").format(self.boq_item))
            if item.boq_header != parent.boq_header:
                frappe.throw(_("VO Line BOQ Item must belong to the selected BOQ Header."))

            structure = frappe.db.get_value(
                "BOQ Structure", item.structure, ["name", "title", "wbs_code", "is_group"], as_dict=True
            )
            if not structure:
                frappe.throw(_("Structure linked to BOQ Item {0} does not exist.").format(self.boq_item))
            if structure.is_group:
                frappe.throw(_("VO Line leaf structure cannot be a group node."))

            self.boq_structure = structure.name
            self.wbs_code = structure.wbs_code
            self.title = structure.title
            self.unit = item.unit
            self.contract_qty = flt(item.quantity)
            self.previous_qty = flt(item.current_revised_qty)  # Reference: current revised qty
            self.contract_unit_price = flt(item.contract_unit_price)
            if self.line_type == "Omission":
                self.revised_qty = 0

        elif self.line_type == "New Item":
            if self.boq_item:
                frappe.throw(_("BOQ Item must be empty for New Item VO lines."))
            if self.boq_structure:
                struct = frappe.db.get_value(
                    "BOQ Structure", self.boq_structure, ["boq_header", "is_group"], as_dict=True
                )
                if not struct:
                    frappe.throw(_("Parent Structure {0} does not exist.").format(self.boq_structure))
                if struct.boq_header != parent.boq_header:
                    frappe.throw(_("Parent Structure must belong to the selected BOQ Header."))
                if not struct.is_group:
                    frappe.throw(_("Parent Structure must be a group node for New Items."))
            else:
                frappe.throw(_("Parent Structure is required for New Item VO lines."))

            # item_code removed - not required
            if not self.title:
                frappe.throw(_("Title is required for New Item VO lines."))
            if not self.unit:
                frappe.throw(_("Unit is required for New Item VO lines."))
            if flt(self.revised_qty) <= 0:
                frappe.throw(_("New Item VO lines require a positive quantity."))
            if flt(self.revised_unit_price) <= 0:
                frappe.throw(_("New Item VO lines require an agreed unit price."))
            self.contract_qty = 0
            self.previous_qty = 0
            self.contract_unit_price = 0
            self.rate_change_triggered = 1
            self.wbs_code = self.wbs_code or self.get_next_new_item_wbs(parent)
        else:
            frappe.throw(_("Invalid VO line type: {0}.").format(self.line_type))

    def calculate_quantities_and_values(self):
        # Primary input is revised_qty
        # Compute delta_qty from revised_qty

        if self.line_type in ("Quantity Change", "Omission"):
            # Compute delta from previous_qty (reference)
            self.delta_qty = flt(self.revised_qty) - flt(self.previous_qty)
            # Compute delta from contract
            self.delta_from_contract_qty = flt(self.revised_qty) - flt(self.contract_qty)

            # FIDIC rule: change % from original contract quantity
            if flt(self.contract_qty) > 0:
                self.change_pct_from_contract = (
                    abs(flt(self.delta_from_contract_qty)) / flt(self.contract_qty) * 100
                )
            else:
                # For variation items or zero contract qty
                self.change_pct_from_contract = 100 if self.revised_qty > 0 else 0

            # Rate change triggered based on FIDIC (> 25% from contract)
            self.rate_change_triggered = 1 if self.change_pct_from_contract > 25 else 0

            # If not triggered, use contract price
            if not self.rate_change_triggered and self.line_type != "Omission":
                self.revised_unit_price = self.contract_unit_price

        elif self.line_type == "New Item":
            self.delta_qty = flt(self.revised_qty)  # From 0 to revised_qty
            self.delta_from_contract_qty = flt(self.revised_qty)  # From 0 to revised_qty
            self.change_pct_from_contract = 100  # Always 100% for new items
            self.rate_change_triggered = 1

        if flt(self.revised_qty) < 0:
            frappe.throw(_("Revised quantity cannot be negative."))

        self.contract_line_value = flt(self.contract_qty) * flt(self.contract_unit_price)
        self.revised_line_value = flt(self.revised_qty) * flt(self.revised_unit_price)
        self.line_delta_value = self.revised_line_value - self.contract_line_value

        # Legacy field for compatibility
        self.abs_change_pct = self.change_pct_from_contract

    def validate_rate_change_rule(self):
        if self.rate_change_triggered:
            if flt(self.revised_unit_price) <= 0 and self.line_type != "Omission":
                frappe.throw(_("Revised unit price is required when the VO rate change rule is triggered."))
            if not self.rate_change_justification and self.line_type != "Omission":
                frappe.throw(
                    _(
                        "Rate change justification is required when quantity changes by more than 25 percent from contract."
                    )
                )

        if self.line_type == "Omission":
            self.revised_unit_price = 0
            self.revised_line_value = 0
            self.line_delta_value = -1 * flt(self.contract_line_value)

    def get_next_new_item_wbs(self, parent):
        vo_prefix = parent.vo_number or "VO-000"
        if self.boq_structure:
            parent_wbs = frappe.db.get_value("BOQ Structure", self.boq_structure, "wbs_code")
            if not parent_wbs:
                parent_wbs = "00"
            prefix = f"{parent_wbs}.{vo_prefix}"
        else:
            prefix = vo_prefix

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
