import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class BOQQuantityRevision(Document):
    def validate(self):
        self.validate_computed_fields()
        self.validate_revision_rules()
        self.validate_approval_integrity()
        self.compute_values()
    
    def before_insert(self):
        self.compute_values()
        self.compute_revision_type()
    
    def before_save(self):
        self.compute_values()
        self.compute_revision_type()
    
    def validate_computed_fields(self):
        # Ensure computed fields are correct
        expected_delta = flt(self.revised_qty) - flt(self.previous_qty)
        if abs(flt(self.delta_qty) - expected_delta) > 0.0001:
            self.delta_qty = expected_delta
        
        # Get original_qty from BOQ Item
        original_qty = frappe.db.get_value("BOQ Item", self.boq_item, "original_qty") or 0
        expected_delta_contract = flt(self.revised_qty) - flt(original_qty)
        if abs(flt(self.delta_from_contract_qty) - expected_delta_contract) > 0.0001:
            self.delta_from_contract_qty = expected_delta_contract
    
    def compute_values(self):
        # Delta qty
        self.delta_qty = flt(self.revised_qty) - flt(self.previous_qty)
        
        # Delta from contract
        original_qty = frappe.db.get_value("BOQ Item", self.boq_item, "original_qty") or 0
        self.delta_from_contract_qty = flt(self.revised_qty) - flt(original_qty)
        
        # Change pct from previous
        if flt(self.previous_qty) > 0:
            self.change_pct = abs(flt(self.delta_qty)) / flt(self.previous_qty) * 100
        else:
            self.change_pct = 100 if self.revised_qty > 0 else 0
        
        # Change pct from contract (FIDIC rule)
        if flt(original_qty) > 0:
            self.change_pct_from_contract = abs(flt(self.delta_from_contract_qty)) / flt(original_qty) * 100
        else:
            # For new variation items with original_qty = 0
            self.change_pct_from_contract = 100 if self.revised_qty > 0 else 0
        
        # Rate change triggered (FIDIC: > 25% from contract)
        self.rate_change_triggered = 1 if self.change_pct_from_contract > 25 else 0
        
        # Values
        self.previous_value = flt(self.previous_qty) * flt(self.contract_unit_price)
        self.revised_value = flt(self.revised_qty) * flt(self.revised_unit_price)
        self.delta_value = self.revised_value - self.previous_value
    
    def compute_revision_type(self):
        # Auto-compute revision type based on quantities
        # Skip if explicitly set to Original Lock (system-generated baseline)
        if self.revision_type == "Original Lock":
            return
        if flt(self.previous_qty) == 0 and flt(self.revised_qty) > 0:
            self.revision_type = "New Variation Item"
        elif flt(self.revised_qty) == 0:
            self.revision_type = "Omission"
        elif flt(self.revised_qty) > flt(self.previous_qty):
            self.revision_type = "Increase Above 25%" if self.change_pct_from_contract > 25 else "Increase Within 25%"
        elif flt(self.revised_qty) < flt(self.previous_qty):
            self.revision_type = "Decrease Above 25%" if self.change_pct_from_contract > 25 else "Decrease Within 25%"
        else:
            # Quantity unchanged - this is rare but possible
            self.revision_type = "Increase Within 25%"
    
    def validate_revision_rules(self):
        # Revised qty must be non-negative
        if flt(self.revised_qty) < 0:
            frappe.throw(_("Revised quantity cannot be negative."))
        
        # Omission requires revised_qty = 0
        if self.revision_type == "Omission" and flt(self.revised_qty) != 0:
            frappe.throw(_("Omission requires revised quantity to be zero."))
        
        # New variation item requires previous_qty = 0
        if self.revision_type == "New Variation Item" and flt(self.previous_qty) != 0:
            frappe.throw(_("New Variation Item requires previous quantity to be zero."))
        
        # Original Lock must be system-generated
        if self.revision_type == "Original Lock" and self.status != "Approved":
            frappe.throw(_("Original Lock revisions must be system-generated and approved."))
        
        # Rate change justification required when triggered
        if self.rate_change_triggered and not self.rate_change_justification:
            # Only require for non-omission
            if self.revision_type != "Omission":
                frappe.throw(_("Rate change justification is required when change exceeds 25% from contract."))
    
    def validate_approval_integrity(self):
        # Check if document is being edited after approval
        if self.name and frappe.db.exists("BOQ Quantity Revision", self.name):
            old_status = frappe.db.get_value("BOQ Quantity Revision", self.name, "status")
            if old_status == "Approved" and self.status != "Approved":
                # Allow changing from Approved to Rejected only
                if self.status != "Rejected":
                    frappe.throw(_("Approved revisions cannot be casually edited."))
            if old_status == "Approved" and self.status == "Approved":
                # Re-saving approved record - allow but warn
                pass
    
    def on_update(self):
        if self.status == "Approved" and not self.approved_by:
            self.approved_by = frappe.session.user
            self.approved_on = frappe.utils.now()
            self.db_set("approved_by", self.approved_by, update_modified=False)
            self.db_set("approved_on", self.approved_on, update_modified=False)


def on_doctype_update():
    frappe.db.add_index("BOQ Quantity Revision", ["boq_item", "revision_date"])
    frappe.db.add_index("BOQ Quantity Revision", ["boq_header", "status"])
    frappe.db.add_index("BOQ Quantity Revision", ["variation_order", "status"])
