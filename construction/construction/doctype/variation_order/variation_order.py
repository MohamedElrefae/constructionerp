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

# Server-owned workflow audit identities. Clients can never set these;
# they are written exclusively by the transition that owns them.
_AUDIT_IDENTITY_FIELDS = (
    "submitted_by",
    "engineer_approved_by",
    "client_approved_by",
)
_AUDIT_FIELDS = (
    *_AUDIT_IDENTITY_FIELDS,
    "submitted_at",
    "engineer_approval_date",
    "client_approval_date",
)


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
        old_status = (
            old_doc.status
            if old_doc
            else (frappe.db.get_value("Variation Order", self.name, "status") if (self.name and frappe.db.exists("Variation Order", self.name)) else DRAFT_STATUS)
        )
        if self.status not in allowed.get(old_status, set()):
            frappe.throw(
                _("Invalid Variation Order status transition from {0} to {1}.").format(
                    old_status, self.status
                )
            )

        is_migration = bool(
            getattr(frappe.flags, "in_migrate", False)
            or getattr(frappe.flags, "in_install", False)
            or getattr(frappe.flags, "in_patch", False)
        )

        user_roles = set(frappe.get_roles(frappe.session.user)) if frappe.session.user else set()

        # Role-based workflow authorization (skip during install/migration)
        if not is_migration and frappe.session.user != "Administrator":
            if self.status == SUBMITTED_STATUS and old_status == DRAFT_STATUS:
                if not user_roles.intersection({"Project Manager", "Construction Owner", "System Manager"}):
                    frappe.throw(
                        _("Unauthorized: Only Project Manager or Construction Owner can submit Variation Orders."),
                        frappe.PermissionError,
                    )
            elif self.status == ENGINEER_APPROVED_STATUS and old_status == SUBMITTED_STATUS:
                if not user_roles.intersection({"Site Engineer", "Project Manager", "Construction Owner", "System Manager"}):
                    frappe.throw(
                        _("Unauthorized: Only Site Engineer or Project Manager can approve Variation Orders for Engineer stage."),
                        frappe.PermissionError,
                    )
            elif self.status == CLIENT_APPROVED_STATUS and old_status == ENGINEER_APPROVED_STATUS:
                if not user_roles.intersection({"Construction Owner", "System Manager"}):
                    frappe.throw(
                        _("Unauthorized: Only Construction Owner or System Manager can approve Variation Orders for Client stage."),
                        frappe.PermissionError,
                    )
            elif self.status == REJECTED_STATUS and old_status != REJECTED_STATUS:
                if not user_roles.intersection({"Site Engineer", "Project Manager", "Construction Owner", "System Manager"}):
                    frappe.throw(
                        _("Unauthorized: Role not permitted to reject Variation Orders."),
                        frappe.PermissionError,
                    )

        # ─────────────────────────────────────────────────────────
        # Audit trail & Segregation of Duties.
        # All workflow audit identities are SERVER-OWNED: they are read
        # from the persisted database record (never from incoming client
        # values) and overwritten exclusively by the transition that owns
        # them. Policy decision (documented): System Manager may bypass the
        # SOD *checks*, but even System Manager cannot inject forged actor
        # identities — actors are always assigned from frappe.session.user.
        # ─────────────────────────────────────────────────────────
        persisted = self._persisted_audit_fields()

        if self.status == SUBMITTED_STATUS and old_status == DRAFT_STATUS:
            # Server assigns the submitting identity unconditionally.
            self.submitted_by = frappe.session.user
            self.submitted_at = frappe.utils.now_datetime()

        elif self.status == ENGINEER_APPROVED_STATUS and old_status == SUBMITTED_STATUS:
            prev_submitter = persisted.get("submitted_by")
            if not is_migration and frappe.session.user != "Administrator":
                if prev_submitter and prev_submitter == frappe.session.user and "System Manager" not in user_roles:
                    frappe.throw(
                        _("Segregation of duties violation: The submitter cannot approve their own Variation Order."),
                        frappe.PermissionError,
                    )
            self.engineer_approved_by = frappe.session.user
            self.engineer_approval_date = nowdate()
            if not self.engineer_name and frappe.session.user:
                self.engineer_name = (
                    frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
                )

        elif self.status == CLIENT_APPROVED_STATUS and old_status == ENGINEER_APPROVED_STATUS:
            prev_submitter = persisted.get("submitted_by")
            prev_engineer = persisted.get("engineer_approved_by")
            if not is_migration and frappe.session.user != "Administrator":
                if (
                    (prev_submitter and prev_submitter == frappe.session.user)
                    or (prev_engineer and prev_engineer == frappe.session.user)
                ) and "System Manager" not in user_roles:
                    frappe.throw(
                        _("Segregation of duties violation: Submitter and Engineer approver cannot grant final Client approval."),
                        frappe.PermissionError,
                    )
            self.client_approved_by = frappe.session.user
            self.client_approval_date = nowdate()

        # Reject any client-supplied audit identity/timestamp outside its
        # owning transition (tamper reversion). Persisted values win.
        self._revert_audit_tampering(persisted, transitioned=bool(
            (self.status == SUBMITTED_STATUS and old_status == DRAFT_STATUS)
            or (self.status == ENGINEER_APPROVED_STATUS and old_status == SUBMITTED_STATUS)
            or (self.status == CLIENT_APPROVED_STATUS and old_status == ENGINEER_APPROVED_STATUS)
        ))

    def _persisted_audit_fields(self):
        """Return audit fields as currently persisted in the database.

        Reads straight from the DB so SOD comparisons can never be fooled
        by client-modified values on the in-memory document.
        """
        if self.is_new() or not self.name:
            return {}
        if not frappe.db.exists("Variation Order", self.name):
            return {}
        row = frappe.db.get_value("Variation Order", self.name, list(_AUDIT_FIELDS), as_dict=True)
        return dict(row) if row else {}

    def _revert_audit_tampering(self, persisted, transitioned):
        """Server-owned audit fields: incoming values that differ from the
        persisted record are reverted unless this save is exactly the
        transition that legitimately writes them."""
        is_migration = bool(
            getattr(frappe.flags, "in_migrate", False)
            or getattr(frappe.flags, "in_install", False)
            or getattr(frappe.flags, "in_patch", False)
        )
        if is_migration:
            return

        owned_now = set()
        if transitioned:
            if self.status == SUBMITTED_STATUS:
                owned_now = {"submitted_by", "submitted_at"}
            elif self.status == ENGINEER_APPROVED_STATUS:
                owned_now = {"engineer_approved_by", "engineer_approval_date"}
            elif self.status == CLIENT_APPROVED_STATUS:
                owned_now = {"client_approved_by", "client_approval_date"}

        for field in _AUDIT_FIELDS:
            if field in owned_now:
                continue
            persisted_val = persisted.get(field)
            if getattr(self, field, None) != persisted_val:
                setattr(self, field, persisted_val)

    def validate_client_approval_gate(self):
        import os

        if self.status != CLIENT_APPROVED_STATUS:
            return
        if not self.client_approval_document:
            frappe.throw(
                _("Signed client approval PDF is required before approving the Variation Order by Client.")
            )
        doc_str = str(self.client_approval_document).strip()

        # Require a real File record in the database
        file_name = None
        if frappe.db.exists(
            "File",
            {"name": doc_str, "attached_to_doctype": "Variation Order", "attached_to_name": self.name},
        ):
            file_name = doc_str
        elif frappe.db.exists(
            "File",
            {"file_url": doc_str, "attached_to_doctype": "Variation Order", "attached_to_name": self.name},
        ):
            file_name = frappe.db.get_value(
                "File",
                {"file_url": doc_str, "attached_to_doctype": "Variation Order", "attached_to_name": self.name},
                "name",
            )
        elif frappe.db.exists("File", doc_str):
            file_name = doc_str
        elif frappe.db.exists("File", {"file_url": doc_str}):
            file_name = frappe.db.get_value("File", {"file_url": doc_str}, "name")

        if not file_name:
            frappe.throw(
                _("Client approval document '{0}' is not a registered File attachment.").format(doc_str),
                frappe.ValidationError,
            )

        file_doc = frappe.get_doc("File", file_name)

        if not str(file_doc.file_name or "").lower().endswith(".pdf") and not doc_str.lower().endswith(".pdf"):
            frappe.throw(_("Client approval document must be a PDF file (.pdf)."), frappe.ValidationError)

        # Enforce attachment linkage to this Variation Order
        if file_doc.attached_to_doctype != "Variation Order" or file_doc.attached_to_name != self.name:
            frappe.throw(
                _("Client approval document '{0}' is not attached to this Variation Order.").format(doc_str),
                frappe.PermissionError,
            )

        # Enforce read permission on the File document
        frappe.has_permission("File", "read", doc=file_doc, throw=True)

        # Verify physical file existence, %PDF- magic bytes, and readable PDF structure
        file_path = file_doc.get_full_path()
        if not os.path.exists(file_path):
            frappe.throw(
                _("Approval PDF file content could not be found on the server."),
                frappe.ValidationError,
            )

        try:
            with open(file_path, "rb") as f:
                header = f.read(5)
                if not header.startswith(b"%PDF-"):
                    frappe.throw(
                        _("Invalid PDF file: Missing %PDF- file signature header."),
                        frappe.ValidationError,
                    )
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            if len(reader.pages) < 1:
                frappe.throw(_("Invalid PDF file: PDF document contains no pages."), frappe.ValidationError)
        except Exception as e:
            if isinstance(e, (frappe.ValidationError, frappe.PermissionError)):
                raise e
            frappe.throw(_("Failed to verify PDF attachment structure: {0}").format(str(e)), frappe.ValidationError)

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
