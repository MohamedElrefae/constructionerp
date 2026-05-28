import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from construction.services.boq_operational import validate_stage_quantities


class BOQItemStage(Document):
    def validate(self):
        self.validate_selection_chain()
        self.fetch_parent_context()
        validate_stage_quantities(self)

    def before_insert(self):
        self.assign_stage_code_if_missing()
        if frappe.db.exists(
            "BOQ Item Stage",
            {"boq_item": self.boq_item, "stage_code": self.stage_code},
        ):
            frappe.throw(_("Stage code {0} already exists for this BOQ Item").format(self.stage_code))

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


def on_doctype_update():
    frappe.db.add_unique("BOQ Item Stage", ["boq_item", "stage_code"], "unique_stage_code_per_item")
    frappe.db.add_index("BOQ Item Stage", ["boq_item"])
    frappe.db.add_index("BOQ Item Stage", ["boq_item", "stage_code"], "idx_boq_item_stage_code")
