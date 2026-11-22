"""Controller for Execution Breakdown Node.

Ordinary DocPerms are intentionally absent. Every mutation must occur inside
the private service guard; the controller never derives authorization from a
caller-provided flag.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from construction.services import execution_tree_access as access
from construction.services import execution_tree_rules as rules

IMMUTABLE_FIELDS = ("project", "company", "ebs_code")


class ExecutionBreakdownNode(Document):
    def before_insert(self):
        guard = self._require_guard("create")
        self.company = self._derived_company()
        self.disabled = 1 if self.disabled else 0
        self.is_group = 1 if self.is_group else 0
        access.require_guard_transition(guard, document=self, field="company", value=self.company)
        access.require_guard_transition(guard, document=self, field="ebs_code", value=self.ebs_code)

    def validate(self):
        operation = access.current_operation()
        if operation not in ("create", "update", "move", "set_disabled"):
            frappe.throw(_("Not permitted."), frappe.PermissionError)
        guard = self._require_guard(operation)
        self.title = rules.validate_title(self.title)
        self.is_group = 1 if rules.validate_boolean(self.is_group, field="is_group") else 0
        self.disabled = 1 if rules.validate_boolean(self.disabled, field="disabled") else 0
        if self.company != self._derived_company():
            frappe.throw(_("The Company is derived from the Project."), frappe.ValidationError)
        for field in ("title", "is_group", "disabled", "parent_node", "company", "ebs_code"):
            access.require_guard_transition(guard, document=self, field=field, value=self.get(field))
        if not self.is_new():
            before = self.get_doc_before_save()
            if before is not None:
                for field in IMMUTABLE_FIELDS:
                    if (self.get(field) or None) != (before.get(field) or None):
                        frappe.throw(
                            _("Execution tree identity fields cannot be changed."),
                            frappe.ValidationError,
                        )
        self._validate_parent()

    def _derived_company(self):
        rows = frappe.db.sql(
            "SELECT company FROM tabProject WHERE name=%s FOR UPDATE",
            (self.project,),
            as_dict=True,
        )
        company = rows[0].get("company") if rows else None
        if not company:
            frappe.throw(_("A valid Project is required."), frappe.ValidationError)
        return company

    def _locked_parent(self, name):
        rows = frappe.db.sql(
            "SELECT name, project, is_group, parent_node FROM `tabExecution Breakdown Node` "
            "WHERE name=%s FOR UPDATE",
            (name,),
            as_dict=True,
        )
        return rows[0] if rows else None

    def _validate_parent(self):
        if not self.parent_node:
            return
        if self.parent_node == self.name:
            frappe.throw(_("A node cannot be its own parent."), frappe.ValidationError)
        parent = self._locked_parent(self.parent_node)
        if not parent or parent.get("project") != self.project:
            frappe.throw(_("A valid same-Project parent is required."), frappe.ValidationError)
        if not int(parent.get("is_group") or 0):
            frappe.throw(_("The parent must be a group."), frappe.ValidationError)
        if not self.is_new() and self.parent_node != (self.get_doc_before_save() or self).parent_node:
            cursor = self.parent_node
            seen = {self.name}
            while cursor:
                if cursor in seen:
                    frappe.throw(_("A node cannot move below its own subtree."), frappe.ValidationError)
                seen.add(cursor)
                row = self._locked_parent(cursor)
                cursor = row.get("parent_node") if row else None

    def before_rename(self, old, new, merge=False):
        frappe.throw(_("Execution tree nodes cannot be renamed."), frappe.PermissionError)

    def on_trash(self):
        self._require_guard("delete")
        # Current locking read: the child check must not rely on an older
        # consistent snapshot of the main transaction.
        children = frappe.db.sql(
            "SELECT name FROM `tabExecution Breakdown Node` "
            "WHERE parent_node=%s ORDER BY name LIMIT 1 FOR UPDATE",
            (self.name,),
            as_dict=True,
        )
        if children:
            frappe.throw(_("A node with children cannot be deleted."), frappe.ValidationError)

    def _require_guard(self, operation):
        return access.require_guard(rules.NODE_DOCTYPE, operation, self.project, self.name, document=self)
