import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from construction.services.boq_operational import validate_stage_quantities


class BOQItemStage(Document):
    CERTIFIER_ROLES = frozenset({"System Manager", "Construction Owner", "Project Manager"})
    FROZEN_LOCKED_IMMUTABLE_FIELDS = frozenset(
        {
            "project",
            "boq_header",
            "boq_structure",
            "boq_item",
            "stage_code",
            "stage_name",
            "planned_qty",
        }
    )
    CERTIFIED_IMMUTABLE_FIELDS = frozenset(
        {
            "project",
            "boq_header",
            "boq_structure",
            "boq_item",
            "stage_code",
            "stage_name",
            "stage_status",
            "planned_qty",
            "measured_executed_qty",
            "certified_qty",
            "percent_complete",
            "description",
        }
    )

    def validate(self):
        self.validate_selection_chain()
        self.fetch_parent_context()
        self.enforce_certification_role()
        self.enforce_stage_edit_policy()
        validate_stage_quantities(self)

    def before_insert(self):
        self.assign_stage_code_if_missing()
        if frappe.db.exists(
            "BOQ Item Stage",
            {"boq_item": self.boq_item, "stage_code": self.stage_code},
        ):
            frappe.throw(_("Stage code {0} already exists for this BOQ Item").format(self.stage_code))

    def on_trash(self):
        from construction.services.boq_lifecycle import before_delete_boq_item_stage

        before_delete_boq_item_stage(self)

    def assign_stage_code_if_missing(self):
        if (self.stage_code or "").strip():
            return
        # Suggest next code from existing records for this BOQ Item.
        rows = frappe.get_all(
            "BOQ Item Stage",
            filters={"boq_item": self.boq_item},
            fields=["stage_code"],
        )
        max_seq = 0
        for row in rows:
            code = (row.stage_code or "").strip().upper()
            if not code.startswith("STG-"):
                continue
            part = code[4:]
            if part.isdigit():
                max_seq = max(max_seq, cint(part))
        self.stage_code = f"STG-{max_seq + 1:03d}"

    def fetch_parent_context(self):
        if not self.boq_item:
            frappe.throw(_("BOQ Item is required"))

        parent = frappe.db.get_value("BOQ Item", self.boq_item, ["boq_header", "structure"], as_dict=True)
        if not parent:
            frappe.throw(_("BOQ Item {0} does not exist").format(self.boq_item))

        if self.boq_header and self.boq_header != parent.boq_header:
            frappe.throw(_("BOQ Item does not belong to selected BOQ Header."))
        if self.boq_structure and self.boq_structure != parent.structure:
            frappe.throw(_("BOQ Item does not belong to selected BOQ Structure."))

        self.boq_header = parent.boq_header
        self.boq_structure = parent.structure
        self.project = frappe.db.get_value("BOQ Header", self.boq_header, "project")

    def validate_selection_chain(self):
        if self.boq_header and self.project:
            header_project = frappe.db.get_value("BOQ Header", self.boq_header, "project")
            if header_project and header_project != self.project:
                frappe.throw(_("Selected BOQ Header does not belong to selected Project."))

        if self.boq_structure and self.boq_header:
            structure_header = frappe.db.get_value("BOQ Structure", self.boq_structure, "boq_header")
            if structure_header and structure_header != self.boq_header:
                frappe.throw(_("Selected BOQ Structure does not belong to selected BOQ Header."))

    def enforce_stage_edit_policy(self):
        if self.is_new():
            return

        old_doc = self.get_doc_before_save()
        if not old_doc:
            return

        if self._is_certified_state(old_doc):
            changed = self._changed_fields(old_doc, self.CERTIFIED_IMMUTABLE_FIELDS)
            if changed:
                frappe.throw(
                    _("Cannot modify certified BOQ Item Stage fields: {0}. Create an adjustment stage instead.").format(
                        ", ".join(changed)
                    )
                )
            return

        header_status = frappe.db.get_value("BOQ Header", self.boq_header, "status")
        if header_status in ("Frozen", "Locked"):
            changed = self._changed_fields(old_doc, self.FROZEN_LOCKED_IMMUTABLE_FIELDS)
            if changed:
                frappe.throw(
                    _("Cannot modify planning fields on BOQ Item Stage when BOQ is {0}: {1}.").format(
                        header_status, ", ".join(changed)
                    )
                )

    def enforce_certification_role(self):
        if self._user_can_certify():
            return

        old_doc = None if self.is_new() else self.get_doc_before_save()
        old_certified_qty = flt(old_doc.certified_qty) if old_doc else 0
        certified_qty_changed = abs(flt(self.certified_qty) - old_certified_qty) > 0.000001
        setting_certified_status = self.stage_status == "Certified" and (not old_doc or old_doc.stage_status != "Certified")

        if certified_qty_changed or setting_certified_status:
            frappe.throw(_("Only Project Manager, Construction Owner, or System Manager can certify BOQ Item Stages."))

    def _user_can_certify(self):
        roles = set(frappe.get_roles(frappe.session.user))
        return bool(roles.intersection(self.CERTIFIER_ROLES))

    def _is_certified_state(self, doc):
        return doc.stage_status == "Certified" or flt(doc.certified_qty) > 0

    def _changed_fields(self, old_doc, fieldnames):
        changed = []
        for fieldname in sorted(fieldnames):
            if self._field_changed(old_doc, fieldname):
                changed.append(self.meta.get_label(fieldname) or fieldname)
        return changed

    def _field_changed(self, old_doc, fieldname):
        df = self.meta.get_field(fieldname)
        fieldtype = df.fieldtype if df else None
        old_value = old_doc.get(fieldname)
        new_value = self.get(fieldname)
        if fieldtype in ("Float", "Currency", "Percent"):
            return abs(flt(old_value) - flt(new_value)) > 0.000001
        if fieldtype in ("Int", "Check"):
            return cint(old_value) != cint(new_value)
        return (old_value or "") != (new_value or "")


def on_doctype_update():
    frappe.db.add_unique("BOQ Item Stage", ["boq_item", "stage_code"], "unique_stage_code_per_item")
    frappe.db.add_index("BOQ Item Stage", ["boq_item"])
    frappe.db.add_index("BOQ Item Stage", ["boq_item", "stage_code"], "idx_boq_item_stage_code")
