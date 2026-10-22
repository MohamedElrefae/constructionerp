"""F22-D006: exercise Project display-name authorization with test-owned fixtures.

The HTTP path matters here: the fallback persona must genuinely lack Project
read permission, and the scope comparison must still authorize only its exact
active project name.
"""

import json

import frappe
from frappe.auth import CookieManager, LoginManager
from frappe.tests.test_api import FrappeAPITestCase
from frappe.utils import set_request


class TestProjectDisplayNameAuthorization(FrappeAPITestCase):
    def setUp(self):
        super().setUp()
        self.original_user = frappe.session.user
        frappe.set_user("Administrator")
        self.users = []
        self.projects = []
        self.scope_name = None
        self.session_sids = {}
        self.addCleanup(self._cleanup_fixtures)
        suffix = frappe.generate_hash(length=8)
        self.scoped_user = self._create_user(f"project_scope_{suffix}@example.com")
        self.company = frappe.db.get_value("Company", {}, "name")
        self.assertTrue(self.company, "the test site must contain its normal setup Company")

        self.scoped_project = self._create_project(f"_Scope Project {suffix}")
        self.other_project = self._create_project(f"_Other Project {suffix}")
        self.scope_name = self.scoped_user
        frappe.get_doc(
            {
                "doctype": "User Scope Context",
                "user": self.scoped_user,
                "company": self.company,
                "project": self.scoped_project.name,
            }
        ).insert(ignore_permissions=True)
        # Native REST requests run in FrappeAPITestCase's separate thread and
        # database connection, so the test-owned rows must be visible there.
        frappe.db.commit()

    def _create_user(self, email):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Project display authorization test",
                "enabled": 1,
                "user_type": "System User",
                "send_welcome_email": 0,
                "roles": [{"role": "Accounts User"}],
            }
        ).insert(ignore_permissions=True)
        self.users.append(user.name)
        self.assertFalse(
            frappe.has_permission("Project", "read", user=user.name),
            "fixture user must exercise the scope fallback without Project read permission",
        )
        return user.name

    def _create_project(self, project_name):
        project = frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": project_name,
                "company": self.company,
                "status": "Open",
            }
        ).insert(ignore_permissions=True)
        self.projects.append(project.name)
        return project

    def _login_sid(self, user):
        if user in self.session_sids:
            return self.session_sids[user]
        try:
            set_request(path="/")
            frappe.local.cookie_manager = CookieManager()
            frappe.local.login_manager = LoginManager()
            frappe.local.login_manager.login_as(user)
            sid = frappe.session.sid
            frappe.db.commit()
            self.session_sids[user] = sid
            return sid
        finally:
            frappe.set_user(self.original_user)

    def _project_name_request(self, project):
        return self.get(
            self.method("construction.api.scope_context_api.get_project_display_name"),
            {"sid": self._login_sid(self.scoped_user), "project": project},
        )

    def _cleanup_fixtures(self):
        try:
            frappe.set_user("Administrator")
            if self.scope_name and frappe.db.exists("User Scope Context", self.scope_name):
                frappe.db.delete("User Scope Context", {"name": self.scope_name})
            for project in self.projects:
                if frappe.db.exists("Project", project):
                    frappe.delete_doc("Project", project, ignore_permissions=True, force=True)
            for user in self.users:
                if frappe.db.exists("User", user):
                    frappe.delete_doc("User", user, ignore_permissions=True, force=True)
            frappe.db.commit()
        finally:
            frappe.set_user(self.original_user)

    @staticmethod
    def _server_messages(response):
        payload = response.get_json() or {}
        messages = json.loads(payload.get("_server_messages") or "[]")
        return [
            json.loads(message).get("message", "") if isinstance(message, str) else message.get("message", "")
            for message in messages
        ]

    def test_scope_fallback_requires_a_genuinely_unprivileged_user(self):
        self.assertFalse(frappe.has_permission("Project", "read", user=self.scoped_user))
        self.assertNotIn("Projects User", frappe.get_roles(self.scoped_user))
        self.assertNotIn("Projects Manager", frappe.get_roles(self.scoped_user))

    def test_scoped_project_returns_only_its_display_name_over_native_rest(self):
        response = self._project_name_request(self.scoped_project.name)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        message = response.get_json()["message"]
        self.assertEqual(set(message), {"project_name"})
        self.assertEqual(message["project_name"], self.scoped_project.project_name)

    def test_other_project_and_missing_name_have_same_generic_denial(self):
        other = self._project_name_request(self.other_project.name)
        missing = self._project_name_request("_Project Does Not Exist")
        self.assertEqual(other.status_code, 403, other.get_data(as_text=True))
        self.assertEqual(missing.status_code, 403, missing.get_data(as_text=True))
        other_messages = self._server_messages(other)
        missing_messages = self._server_messages(missing)
        self.assertEqual(other_messages, missing_messages)
        self.assertIn("Not authorized to access this project.", other_messages)
        self.assertNotIn(self.other_project.name, " ".join(other_messages))
        self.assertNotIn("_Project Does Not Exist", " ".join(missing_messages))

    def test_scope_prefix_is_not_a_match(self):
        response = self._project_name_request(self.scoped_project.name + "0")
        self.assertEqual(response.status_code, 403, response.get_data(as_text=True))
        messages = self._server_messages(response)
        self.assertIn("Not authorized to access this project.", messages)
        self.assertNotIn(self.scoped_project.name + "0", " ".join(messages))

    def test_empty_project_returns_blank_label(self):
        response = self._project_name_request("")
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.get_json()["message"], {"project_name": ""})
