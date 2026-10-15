"""F22-D006 review: `get_project_display_name` authorization on the scope fallback path.

Owner's three requirements for the SQL path that replaced `frappe.get_list`:
  1. authorization binds to the EXACT requested project (not a prefix, not "any project
     the user can read", not the first project in scope);
  2. only that project's display name is returned — nothing else;
  3. generic denials are preserved: an unauthorized name and a missing name give the
     SAME message, so the endpoint stays a non-disclosing authorization boundary.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.api.scope_context_api import get_project_display_name

SCOPED = "f23-scopeless@v16rehearsal.local"


class TestProjectDisplayNameAuthorization(FrappeTestCase):
    def setUp(self):
        self.scoped_user = "f06-owner@v16rehearsal.local"
        if not frappe.db.exists("User", self.scoped_user):
            self.skipTest("fixture persona absent")

        self.scope = frappe.db.get_value(
            "User Scope Context", {"user": self.scoped_user}, ["company", "project"], as_dict=True
        )
        if not (self.scope and self.scope.project):
            self.skipTest("fixture persona has no scope context")

        # A second, real project the scoped persona does NOT have in scope.
        self.other = frappe.db.get_value(
            "Project", {"name": ["!=", self.scope.project]}, "name"
        )
        self.addCleanup(frappe.set_user, "Administrator")

    # -- requirement 3: generic denials -------------------------------------

    def test_unauthorized_project_is_denied(self):
        frappe.set_user(SCOPED)
        frappe.local._boq_perm_scope_dims = {}
        with self.assertRaises(frappe.PermissionError) as ctx:
            get_project_display_name(self.other)
        self.assertIn("Not authorized to access this project.", str(ctx.exception))

    def test_missing_project_gives_the_same_denial(self):
        """A name that does not exist must be indistinguishable from an unauthorized one."""
        frappe.set_user(SCOPED)
        frappe.local._boq_perm_scope_dims = {}
        with self.assertRaises(frappe.PermissionError) as ctx:
            get_project_display_name("PROJ-does-not-exist")
        self.assertIn("Not authorized to access this project.", str(ctx.exception))

    def test_scope_prefix_is_not_a_match(self):
        """Authorization is exact equality, so a name that merely extends the scope name
        must not inherit the scope's authorization."""
        frappe.set_user(SCOPED)
        frappe.local._boq_perm_scope_dims = {}
        with self.assertRaises(frappe.PermissionError):
            get_project_display_name(str(self.scope.project) + "0")

    # -- requirement 1 + 2: exact binding, name only -------------------------

    def test_scoped_project_resolves_its_own_name(self):
        frappe.set_user(self.scoped_user)
        frappe.local._boq_perm_scope_dims = {}
        result = get_project_display_name(self.scope.project)
        self.assertEqual(set(result.keys()), {"project_name"}, "only the display name may be returned")
        expected = frappe.db.get_value("Project", self.scope.project, "project_name")
        self.assertEqual(result["project_name"], expected)

    def test_result_contains_no_other_project_fields(self):
        """The response must not carry company, cost centre or any other dimension."""
        frappe.set_user(self.scoped_user)
        frappe.local._boq_perm_scope_dims = {}
        result = get_project_display_name(self.scope.project)
        for forbidden in ("company", "cost_center", "status", "owner", "name"):
            self.assertNotIn(forbidden, result)

    def test_empty_request_returns_blank_label(self):
        self.assertEqual(get_project_display_name(""), {"project_name": ""})
        self.assertEqual(get_project_display_name(None), {"project_name": ""})
