"""
User Scope Context DocType Controller
DEL-001: Real implementation with automated hooks
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from construction.construction.utils.scope_validation import validate_scope_dimensions


class UserScopeContext(Document):
    """
    User Scope Context stores per-user active company, branch,
    project, and department for multi-company ERPNext environments.
    """

    def before_save(self):
        """
        Auto-increment scope_version and update last_active_at on every save.
        """
        # Increment scope version
        if not self.scope_version:
            self.scope_version = 0
        self.scope_version += 1
        
        # Update last active timestamp
        self.last_active_at = now_datetime()

    def validate(self):
        """
        Validate user-specific record modifications and cross-dimension alignment.
        """
        # Check if user is modifying their own record (if not System Manager)
        if not frappe.has_permission(self.doctype, "write", self, user=frappe.session.user):
            if self.user != frappe.session.user:
                frappe.throw(
                    f"You can only modify your own User Scope Context. "
                    f"Current user: {frappe.session.user}, Record owner: {self.user}"
                )
        
        # Cross-dimension validation
        if self.company and self.branch:
            validate_scope_dimensions(
                company=self.company,
                branch=self.branch,
                project=self.project,
                department=self.department,
                throw=True
            )
        
        # Validate user exists
        if self.user and not frappe.db.exists("User", self.user):
            frappe.throw(f"User '{self.user}' does not exist")
        
        # Validate company exists
        if self.company and not frappe.db.exists("Company", self.company):
            frappe.throw(f"Company '{self.company}' does not exist")

    def on_trash(self):
        """
        Prevent deletion of User Scope Context records.
        Records should be updated, not deleted.
        """
        # Allow System Manager to delete for testing purposes
        if not frappe.has_permission(self.doctype, "delete", self, user=frappe.session.user):
            frappe.throw("User Scope Context records cannot be deleted. Update the record instead.")
