"""Controller for Execution Code Counter.

The counter is internal. It is written only by the authorized creation service
under a narrowly bound counter guard, and it is never exposed through an RPC
or ordinary DocPerm.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from construction.services import execution_tree_access as access
from construction.services import execution_tree_rules as rules


class ExecutionCodeCounter(Document):
    def before_insert(self):
        guard = self._require_guard()
        self.last_issued = rules.validate_counter_value(self.last_issued)
        if guard.get("from_value") is not None:
            frappe.throw(_("A new counter cannot continue an existing transition."), frappe.ValidationError)
        if guard.get("to_value") != self.last_issued:
            frappe.throw(
                _("The counter transition is not the authorized transition."), frappe.PermissionError
            )

    def validate(self):
        guard = self._require_guard()
        self.last_issued = rules.validate_counter_value(self.last_issued)
        if not self.is_new():
            before = self.get_doc_before_save()
            if before is not None:
                if before.project != self.project:
                    frappe.throw(_("The counter Project cannot be changed."), frappe.ValidationError)
                previous = rules.validate_counter_value(before.last_issued)
                if guard.get("from_value") != previous:
                    frappe.throw(
                        _("The counter transition is not the authorized transition."), frappe.PermissionError
                    )
                if guard.get("to_value") != self.last_issued:
                    frappe.throw(
                        _("The counter transition is not the authorized transition."), frappe.PermissionError
                    )
                if self.last_issued != previous + 1:
                    frappe.throw(_("The counter must advance by exactly one."), frappe.ValidationError)
        elif guard.get("to_value") != self.last_issued:
            frappe.throw(
                _("The counter transition is not the authorized transition."), frappe.PermissionError
            )

    def before_rename(self, old, new, merge=False):
        frappe.throw(_("Execution code counters cannot be renamed."), frappe.PermissionError)

    def on_trash(self):
        frappe.throw(_("Execution code counters cannot be deleted."), frappe.PermissionError)

    def _require_guard(self):
        guard = access.current_guard()
        if not access.has_counter_guard(self.project, document=self) or guard is None:
            frappe.throw(_("Not permitted."), frappe.PermissionError)
        if guard.get("actor") != frappe.session.user:
            frappe.throw(_("Not permitted."), frappe.PermissionError)
        return guard
