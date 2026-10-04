from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from construction.services.boq_pricing import number
from construction.services.boq_transactions import current_boq_sql, lock_boq_header


class BOQQuantityRevision(Document):
    # Approval freezes the commercial evidence, including derived amounts and
    # approval attribution. Form read_only properties do not enforce this.
    APPROVAL_FROZEN_FIELDS = (
        "boq_header",
        "boq_structure",
        "boq_item",
        "variation_order",
        "revision_date",
        "revision_type",
        "previous_qty",
        "revised_qty",
        "delta_qty",
        "delta_from_contract_qty",
        "change_pct",
        "change_pct_from_contract",
        "rate_change_triggered",
        "contract_unit_price",
        "revised_unit_price",
        "previous_value",
        "revised_value",
        "delta_value",
        "rate_change_justification",
        "reason",
        "owner_page",
        "owner_ref_no",
        "owner_file_ref",
        "status",
        "approved_by",
        "approved_on",
    )

    def validate(self):
        self.validate_approval_integrity()
        if self._previously_approved():
            # Re-saving unchanged history must not recompute it from a BOQ
            # Item whose baseline or current quantities may since have changed.
            return
        self.validate_new_revision_context()
        self.validate_computed_fields()
        self.validate_revision_rules()
        self.compute_values()

    def before_insert(self):
        if self.revision_type == "Original Lock":
            from construction.services.quantity_revisions import _is_baseline_creation

            if not _is_baseline_creation(self.boq_header):
                frappe.throw(_("Original Lock revisions are created only by the baseline service."))
        self.compute_values()
        self.compute_revision_type()

    def validate_new_revision_context(self):
        from construction.services.boq_transactions import lock_boq_item_header

        actual_header = lock_boq_item_header(self.boq_item)
        item = frappe.get_doc("BOQ Item", self.boq_item, for_update=True)
        if self.boq_header != actual_header or self.boq_structure != item.structure:
            frappe.throw(_("Revision header and structure must match the BOQ Item."))
        for field in ("previous_qty", "revised_qty", "contract_unit_price", "revised_unit_price"):
            self.set(field, number(self.get(field), self.meta.get_label(field)))
        if self.status != "Approved":
            if self.approved_by or self.approved_on:
                frappe.throw(_("Approval attribution is managed by the approval service."))
            return
        if frappe.session.user != "Administrator":
            if not set(frappe.get_roles()).intersection(
                {"Project Manager", "Construction Owner", "System Manager"}
            ):
                frappe.throw(_("You cannot approve BOQ revisions."), frappe.PermissionError)
            frappe.has_permission("BOQ Quantity Revision", "write", doc=self, throw=True)
            frappe.has_permission("BOQ Item", "read", doc=item, throw=True)
        if self.revision_type not in ("Original Lock", "New Variation Item"):
            current_qty = item.current_revised_qty if item.current_revised_qty is not None else item.quantity
            if flt(self.previous_qty) != flt(current_qty):
                frappe.throw(
                    _(
                        "Previous quantity has changed. Create or update the correction from current quantities."
                    )
                )
        elif self.revision_type == "New Variation Item" and not item.is_variation_item:
            frappe.throw(_("New Variation Item revisions require a variation BOQ Item."))
        self.approved_by = frappe.session.user
        self.approved_on = frappe.utils.now()

    def before_save(self):
        if self._previously_approved():
            return
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
            item = frappe.db.get_value(
                "BOQ Item", self.boq_item, ["is_variation_item", "original_qty"], as_dict=True
            )
            if item and item.is_variation_item and flt(item.original_qty) == 0:
                self.revision_type = "New Variation Item"
            else:
                self.revision_type = (
                    "Increase Above 25%" if self.change_pct_from_contract > 25 else "Increase Within 25%"
                )
        elif flt(self.revised_qty) == 0:
            self.revision_type = "Omission"
        elif flt(self.revised_qty) > flt(self.previous_qty):
            self.revision_type = (
                "Increase Above 25%" if self.change_pct_from_contract > 25 else "Increase Within 25%"
            )
        elif flt(self.revised_qty) < flt(self.previous_qty):
            self.revision_type = (
                "Decrease Above 25%" if self.change_pct_from_contract > 25 else "Decrease Within 25%"
            )
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
                frappe.throw(
                    _("Rate change justification is required when change exceeds 25% from contract.")
                )

    def validate_approval_integrity(self):
        previous = self._previously_approved()
        if not previous:
            return
        for fieldname in self.APPROVAL_FROZEN_FIELDS:
            field = self.meta.get_field(fieldname)
            before, after = previous.get(fieldname), self.get(fieldname)
            if field.fieldtype in ("Float", "Currency", "Percent", "Check"):
                # Display precision is not storage precision: rounding a
                # currency to two digits would permit persisted sub-cent
                # edits which become material at large quantities.
                try:
                    original_number = Decimal(str(before or 0))
                    candidate_number = Decimal(str(after or 0))
                    if not original_number.is_finite() or not candidate_number.is_finite():
                        raise InvalidOperation
                    # Match database storage scale, never UI currency precision.
                    # Otherwise an unchanged in-memory 1/3 percentage differs
                    # from its persisted decimal(21,9) approval evidence.
                    sql_type, sql_size = frappe.db.type_map[field.fieldtype]
                    if sql_type == "decimal" and "," in str(sql_size):
                        scale = int(str(sql_size).split(",")[1])
                        quantum = Decimal(1).scaleb(-scale)
                        original_number = original_number.quantize(quantum)
                        candidate_number = candidate_number.quantize(quantum)
                    changed = original_number != candidate_number
                except (InvalidOperation, ValueError):
                    frappe.throw(_("Approved revision values must remain valid numbers."))
            else:
                changed = str(before or "") != str(after or "")
            if changed:
                frappe.throw(
                    _(
                        "Approved revision field {0} cannot be changed. Create a new revision for a correction."
                    ).format(field.label)
                )

    def _previously_approved(self):
        previous = self.get_doc_before_save()
        return previous if previous and self._has_approval_evidence(previous) else None

    @staticmethod
    def _has_approval_evidence(revision):
        return (
            revision.get("status") == "Approved"
            or bool(revision.get("approved_by"))
            or bool(revision.get("approved_on"))
        )

    def on_trash(self):
        if self.boq_header:
            lock_boq_header(self.boq_header)

        item_rows = current_boq_sql(
            "SELECT name, boq_header FROM `tabBOQ Item` WHERE name = %s FOR UPDATE NOWAIT",
            self.boq_item,
            as_dict=True,
        )
        if not item_rows:
            frappe.throw(_("The BOQ Item for this revision no longer exists."))

        rows = current_boq_sql(
            """
            SELECT status, approved_by, approved_on, boq_item, boq_header
            FROM `tabBOQ Quantity Revision`
            WHERE name = %s
            FOR UPDATE NOWAIT
            """,
            self.name,
            as_dict=True,
        )
        if not rows:
            return

        current = rows[0]
        if (
            current.boq_item != item_rows[0].name
            or current.boq_header != item_rows[0].boq_header
            or current.boq_header != self.boq_header
        ):
            frappe.throw(_("The revision BOQ changed concurrently. Reload and retry the deletion."))
        if not self._has_approval_evidence(current):
            return

        frappe.throw(
            _(
                "Approved or previously approved revisions cannot be deleted. Create a new revision for corrections."
            )
        )

    def on_update(self):
        if self.status == "Approved" and not self._previously_approved():
            from construction.services.quantity_revisions import _project_new_approval

            _project_new_approval(self)


def on_doctype_update():
    frappe.db.add_index("BOQ Quantity Revision", ["boq_item", "revision_date"])
    frappe.db.add_index("BOQ Quantity Revision", ["boq_header", "status"])
    frappe.db.add_index("BOQ Quantity Revision", ["variation_order", "status"])
