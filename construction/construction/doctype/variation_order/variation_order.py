import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from construction.api.scope_context_api import get_user_scope_context

CLIENT_APPROVED_STATUS = "Approved by Client"
ENGINEER_APPROVED_STATUS = "Approved by Engineer"
SUBMITTED_STATUS = "Submitted"
DRAFT_STATUS = "Draft"
REJECTED_STATUS = "Rejected"


class VariationOrder(Document):
    def autoname(self):
        self.validate_boq_header()
        self.vo_number = self.vo_number or get_next_vo_number(self.boq_header)
        self.name = f"{self.boq_header}-{self.vo_number}"

    def validate(self):
        self.enforce_scope_context_project()
        self.validate_boq_header()
        self.fetch_header_context()
        self.validate_status_transition()
        self.validate_client_approval_gate()
        self.validate_lines()
        self.calculate_total_contract_delta()

    def enforce_scope_context_project(self):
        if not self.is_new():
            return
        if frappe.session.user == "Administrator":
            return
        try:
            enabled = bool(
                frappe.db.get_single_value("Construction Settings", "enable_scope_context") or False
            )
        except Exception:
            enabled = False
        if not enabled:
            return
        scope = get_user_scope_context(frappe.session.user)
        if not scope or not scope.project:
            return
        doc_project = (
            self.project or frappe.db.get_value("BOQ Header", self.boq_header, "project")
            if self.boq_header
            else None
        )
        if doc_project and doc_project != scope.project:
            frappe.throw(
                _(
                    "Project {0} does not match your active scope project {1}. Switch your scope in the top bar and try again."
                ).format(doc_project, scope.project)
            )

    def on_update(self):
        if self.status == CLIENT_APPROVED_STATUS:
            self.process_approved_vo_lines()

    def validate_boq_header(self):
        if not self.boq_header:
            frappe.throw(_("BOQ Header is required."))
        header_status = frappe.db.get_value("BOQ Header", self.boq_header, "status")
        if header_status != "Locked":
            frappe.throw(_("Variation Orders can only be raised against Locked BOQ Headers."))

    def fetch_header_context(self):
        self.project = frappe.db.get_value("BOQ Header", self.boq_header, "project")
        if not self.vo_date:
            self.vo_date = nowdate()

    def validate_status_transition(self):
        allowed = {
            DRAFT_STATUS: {DRAFT_STATUS, SUBMITTED_STATUS, REJECTED_STATUS},
            SUBMITTED_STATUS: {SUBMITTED_STATUS, ENGINEER_APPROVED_STATUS, REJECTED_STATUS},
            ENGINEER_APPROVED_STATUS: {ENGINEER_APPROVED_STATUS, CLIENT_APPROVED_STATUS, REJECTED_STATUS},
            CLIENT_APPROVED_STATUS: {CLIENT_APPROVED_STATUS},
            REJECTED_STATUS: {REJECTED_STATUS},
        }
        old_doc = None if self.is_new() else self.get_doc_before_save()
        old_status = old_doc.status if old_doc else DRAFT_STATUS
        if self.status not in allowed.get(old_status, set()):
            frappe.throw(
                _("Invalid Variation Order status transition from {0} to {1}.").format(
                    old_status, self.status
                )
            )

        if self.status == ENGINEER_APPROVED_STATUS:
            self.engineer_approval_date = self.engineer_approval_date or nowdate()
        if self.status == CLIENT_APPROVED_STATUS:
            self.client_approval_date = self.client_approval_date or nowdate()

    def validate_client_approval_gate(self):
        if self.status != CLIENT_APPROVED_STATUS:
            return
        if not self.client_approval_document:
            frappe.throw(
                _("Signed client approval PDF is required before approving the Variation Order by Client.")
            )
        if not str(self.client_approval_document).lower().endswith(".pdf"):
            frappe.throw(_("Client approval document must be a PDF."))

    def validate_lines(self):
        if not self.lines:
            # An empty Draft VO is allowed so users can launch a new VO and
            # fill in lines afterwards. All non-Draft statuses must have at
            # least one line so the VO is a meaningful artefact.
            if (self.status or DRAFT_STATUS) != DRAFT_STATUS:
                frappe.throw(_("At least one VO Line is required."))
            return
        for line in self.lines:
            line.validate_against_parent(self)

        # P0-1: Block line edits after Engineer Approval
        if self.status in (ENGINEER_APPROVED_STATUS, CLIENT_APPROVED_STATUS, REJECTED_STATUS):
            self._validate_no_line_changes_after_approval()

    def _validate_no_line_changes_after_approval(self):
        """Ensure VO lines are not modified after Engineer Approval."""
        if self.is_new():
            return

        old_doc = self.get_doc_before_save()
        if not old_doc:
            return

        # Check if any line was modified
        if len(old_doc.lines) != len(self.lines):
            frappe.throw(
                _(
                    "Cannot add or remove VO lines after Engineer Approval. Return to Submitted status to edit."
                )
            )

        for old_line, new_line in zip(old_doc.lines, self.lines, strict=True):
            if old_line.name != new_line.name:
                frappe.throw(
                    _("Cannot modify VO lines after Engineer Approval. Return to Submitted status to edit.")
                )

            # Check key fields for changes
            if (
                flt(old_line.revised_qty) != flt(new_line.revised_qty)
                or flt(old_line.revised_unit_price) != flt(new_line.revised_unit_price)
                or old_line.line_type != new_line.line_type
                or old_line.boq_item != new_line.boq_item
            ):
                frappe.throw(
                    _("Cannot modify VO lines after Engineer Approval. Return to Submitted status to edit.")
                )

    def calculate_total_contract_delta(self):
        self.total_contract_delta = sum(flt(line.line_delta_value) for line in self.lines)

    def process_approved_vo_lines(self):
        """Process all VO lines atomically on Client Approval.

        Idempotent: skips lines that already have created_quantity_revision.
        """
        from construction.services.quantity_revisions import process_approved_vo_lines as service_process

        service_process(self)


def get_next_vo_number(boq_header):
    frappe.db.sql("select name from `tabBOQ Header` where name = %s for update", boq_header)
    existing = frappe.get_all(
        "Variation Order",
        filters={"boq_header": boq_header},
        pluck="vo_number",
    )
    max_seq = 0
    for number in existing:
        suffix = str(number or "").replace("VO-", "")
        if suffix.isdigit():
            max_seq = max(max_seq, int(suffix))
    return f"VO-{max_seq + 1:03d}"


def create_variation_structure_and_item(vo, line):
    from frappe.utils.nestedset import rebuild_tree

    structure = frappe.new_doc("BOQ Structure")
    structure.flags.ignore_boq_status_for_variation = True
    structure.flags.ignore_wbs_generation = True
    structure.boq_header = vo.boq_header
    structure.project = vo.project
    structure.title = line.title
    structure.wbs_code = line.wbs_code
    structure.is_group = 0
    structure.is_variation_item = 1
    if line.boq_structure:
        structure.parent_structure = line.boq_structure
    structure.variation_order = vo.name
    structure.import_mode = "Variation"
    structure.insert(ignore_permissions=True)

    item = frappe.get_doc("BOQ Item", {"structure": structure.name})
    item.flags.ignore_boq_status_for_variation = True
    item.is_variation_item = 1
    item.variation_order = vo.name
    item.quantity = flt(line.revised_qty)
    item.unit = line.unit
    item.contract_unit_price = flt(line.revised_unit_price)
    item.import_mode = "Variation"

    item.owner_page = line.owner_page
    item.owner_ref_no = line.owner_ref_no
    item.owner_file_ref = line.owner_file_ref

    item.save(ignore_permissions=True)

    rebuild_tree("BOQ Structure")
    return structure


def on_doctype_update():
    frappe.db.add_index("Variation Order", ["boq_header", "vo_number"], "idx_vo_boq_number")
