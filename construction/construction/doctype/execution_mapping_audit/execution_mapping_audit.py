"""Immutable controller for Execution Mapping Audit.

Ordinary DocPerms are intentionally absent. Inserts are permitted only inside
the private request-local audit guard in ``construction.services.execution_mapping``.
All post-insert updates, renames and deletions are unconditionally refused.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from construction.services import execution_mapping as mapping


class ExecutionMappingAudit(Document):
    def before_insert(self):
        mapping.require_audit_insert_guard(self)

    def validate(self):
        if not self.is_new():
            frappe.throw(_("Execution Mapping Audit records are immutable."), frappe.PermissionError)
        mapping.require_audit_insert_guard(self)

    def on_update(self):
        # Frappe fires on_update during initial insert too; permit ONLY the
        # exact newly-inserted document bound to the active audit insert guard.
        if not mapping.is_guarded_audit_insert(self):
            frappe.throw(_("Execution Mapping Audit records are immutable."), frappe.PermissionError)

    def before_rename(self, old, new, merge=False):
        frappe.throw(_("Execution Mapping Audit records cannot be renamed."), frappe.PermissionError)

    def on_trash(self):
        frappe.throw(_("Execution Mapping Audit records cannot be deleted."), frappe.PermissionError)


def on_doctype_update():
    mapping.reconcile_audit_series_counter()
