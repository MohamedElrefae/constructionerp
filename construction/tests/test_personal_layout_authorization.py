"""Native and API authorization tests for personal Form Layout Profiles."""

import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

import construction.construction.api.layout_api as layout_api_module
from construction.construction.api.layout_api import (
    delete_layout,
    delete_my_personal_layout,
    get_active_layout,
    list_layouts,
    save_layout,
    validate_layout,
)
from construction.overrides.layout_permissions import has_form_layout_profile_permission


class TestPersonalLayoutAuthorization(FrappeTestCase):
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        self.users = []
        self.profiles = []
        suffix = frappe.generate_hash(length=8)
        self.owner = self._create_user(f"layout_owner_{suffix}@example.com", "Accounts User")
        self.observer = self._create_user(f"layout_observer_{suffix}@example.com", "Accounts User")
        self.foreign_owner = self._create_user(f"layout_foreign_{suffix}@example.com", "Accounts User")
        self.manager = self._create_user(f"layout_manager_{suffix}@example.com", "System Manager")
        self.suffix = suffix

    def tearDown(self):
        frappe.set_user("Administrator")
        for profile in self.profiles:
            if frappe.db.exists("Form Layout Profile", profile):
                frappe.delete_doc("Form Layout Profile", profile, ignore_permissions=True, force=True)
        for user in self.users:
            if frappe.db.exists("User", user):
                frappe.delete_doc("User", user, ignore_permissions=True, force=True)
        super().tearDown()

    def _create_user(self, email, role):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Personal layout authorization test",
                "enabled": 1,
                "user_type": "System User",
                "send_welcome_email": 0,
                "roles": [{"role": role}],
            }
        )
        user.insert(ignore_permissions=True)
        self.users.append(email)
        return email

    def _create_profile(
        self,
        label,
        *,
        doctype="Task",
        for_user=None,
        for_role=None,
        is_default=0,
        priority=10,
    ):
        profile = frappe.get_doc(
            {
                "doctype": "Form Layout Profile",
                "reference_doctype": doctype,
                "profile_name": f"_privacy_{self.suffix}_{label}",
                "for_user": for_user,
                "for_role": for_role,
                "is_default": is_default,
                "is_system": 0,
                "enabled": 1,
                "priority": priority,
                "layout_version": 1,
                "sections_json": json.dumps({"version": 1, "sections": [{"label": label, "fields": []}]}),
            }
        )
        profile.insert(ignore_permissions=True)
        self.profiles.append(profile.name)
        return profile

    def _doctype_without_profiles(self, exclude=()):
        candidates = (
            "User Permission",
            "Workflow",
            "Page",
            "Note",
            "Contact",
            "Communication",
            "Assignment Rule",
            "Calendar View",
            "Dashboard",
        )
        for doctype in candidates:
            if doctype in exclude:
                continue
            if not frappe.db.exists("Form Layout Profile", {"reference_doctype": doctype}):
                return doctype
        self.fail("No existing DocType without a layout was found for this isolated test")

    def _seed_layouts(self):
        self.personal = self._create_profile("owner", for_user=self.owner, priority=0)
        self.foreign = self._create_profile(
            "foreign_role_candidate",
            for_user=self.foreign_owner,
            for_role="Accounts User",
            priority=1000,
        )
        self.shared_role = self._create_profile("shared_role", for_role="Accounts User", priority=20)
        self.task_default = self._create_profile("task_default", is_default=1, priority=1)
        self.shared_default_doctype = self._doctype_without_profiles()
        self.shared_default = self._create_profile(
            "shared_default", doctype=self.shared_default_doctype, is_default=1, priority=1
        )
        self.foreign_role_doctype = self._doctype_without_profiles(exclude=(self.shared_default_doctype,))
        self.foreign_role_only = self._create_profile(
            "foreign_role_only",
            doctype=self.foreign_role_doctype,
            for_user=self.foreign_owner,
            for_role="Accounts User",
            priority=1000,
        )
        self.foreign_default_doctype = self._doctype_without_profiles(
            exclude=(self.shared_default_doctype, self.foreign_role_doctype)
        )
        self.foreign_default = self._create_profile(
            "foreign_default",
            doctype=self.foreign_default_doctype,
            for_user=self.foreign_owner,
            is_default=1,
            priority=1000,
        )

    def test_ordinary_native_list_and_api_exclude_foreign_personal_profiles(self):
        self._seed_layouts()
        frappe.set_user(self.owner)

        # The DocType's existing All read permission allows this native list;
        # the row-level hook still hides foreign personal configurations.
        native_rows = frappe.get_list(
            "Form Layout Profile",
            filters={"reference_doctype": "Task", "enabled": 1},
            fields=["name"],
        )
        native_names = {row.name for row in native_rows}
        self.assertIn(self.personal.name, native_names)
        self.assertIn(self.shared_role.name, native_names)
        self.assertIn(self.task_default.name, native_names)
        self.assertNotIn(self.foreign.name, native_names)

        api_names = {row.name for row in list_layouts("Task")}
        self.assertEqual(api_names, native_names)

    def test_resolver_excludes_foreign_personal_role_and_default_candidates(self):
        self._seed_layouts()
        frappe.set_user(self.owner)
        self.assertEqual(get_active_layout("Task")["profile_name"], self.personal.profile_name)
        self.assertEqual(
            get_active_layout(self.shared_default_doctype)["profile_name"],
            self.shared_default.profile_name,
        )
        self.assertIsNone(get_active_layout(self.foreign_role_doctype))
        self.assertIsNone(get_active_layout(self.foreign_default_doctype))

    def test_direct_permission_hook_denies_foreign_and_defers_to_docperms(self):
        self._seed_layouts()
        self.assertIs(has_form_layout_profile_permission(self.foreign, "read", user=self.owner), False)
        self.assertIs(has_form_layout_profile_permission(self.personal, "read", user=self.owner), True)
        self.assertIs(has_form_layout_profile_permission(self.shared_role, "read", user=self.owner), True)
        self.assertIs(has_form_layout_profile_permission(self.foreign, "read", user=self.manager), True)
        self.assertFalse(
            frappe.has_permission("Form Layout Profile", "read", doc=self.foreign, user=self.owner)
        )

    def test_ordinary_user_cannot_write_even_own_personal_profile(self):
        self._seed_layouts()
        self.assertTrue(has_form_layout_profile_permission(self.personal, "write", user=self.owner))
        self.assertFalse(
            frappe.has_permission("Form Layout Profile", "write", doc=self.personal, user=self.owner)
        )
        self.assertFalse(
            frappe.has_permission("Form Layout Profile", "write", doc=self.foreign, user=self.owner)
        )

    def test_shared_role_and_default_selection_remain_available(self):
        self._seed_layouts()
        frappe.set_user(self.observer)
        self.assertEqual(get_active_layout("Task")["profile_name"], self.shared_role.profile_name)
        self.assertEqual(
            get_active_layout(self.shared_default_doctype)["profile_name"],
            self.shared_default.profile_name,
        )

    def test_administrator_can_inspect_all_but_resolver_still_filters(self):
        self._seed_layouts()
        frappe.set_user("Administrator")
        names = {row.name for row in list_layouts("Task")}
        self.assertIn(self.foreign.name, names)
        self.assertTrue(frappe.has_permission("Form Layout Profile", "read", doc=self.foreign))
        self.assertNotEqual(get_active_layout("Task")["name"], self.foreign.name)
        self.assertIsNone(get_active_layout(self.foreign_role_doctype))
        self.assertIsNone(get_active_layout(self.foreign_default_doctype))

    def test_system_manager_can_inspect_all_but_resolver_still_filters(self):
        self._seed_layouts()
        frappe.set_user(self.manager)
        names = {row.name for row in list_layouts("Task")}
        self.assertIn(self.foreign.name, names)
        self.assertTrue(
            frappe.has_permission("Form Layout Profile", "read", doc=self.foreign),
            f"{self.manager} roles: {frappe.get_roles(self.manager)}",
        )
        self.assertNotEqual(get_active_layout("Task")["name"], self.foreign.name)
        self.assertIsNone(get_active_layout(self.foreign_role_doctype))
        self.assertIsNone(get_active_layout(self.foreign_default_doctype))

    def test_mutations_are_post_only_and_read_apis_keep_get(self):
        from frappe import allowed_http_methods_for_whitelisted_func

        for method in (save_layout, delete_layout, delete_my_personal_layout):
            self.assertEqual(allowed_http_methods_for_whitelisted_func[method], ["POST"])
        for method in (get_active_layout, list_layouts, validate_layout):
            self.assertIn("GET", allowed_http_methods_for_whitelisted_func[method])

    def test_tests_import_the_candidate_layout_api(self):
        candidate_root = Path(__file__).resolve().parents[2]
        self.assertTrue(Path(layout_api_module.__file__).resolve().is_relative_to(candidate_root))
