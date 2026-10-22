"""Native Frappe REST coverage for owner-scoped and guest-readable surfaces."""

import json
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote
from uuid import uuid4

import frappe
from frappe.auth import CookieManager, LoginManager
from frappe.tests.test_api import FrappeAPITestCase
from frappe.utils import get_test_client, set_request


class TestNativeSecurityRestAuthorization(FrappeAPITestCase):
    """Exercise resource and whitelisted-method routes through Frappe WSGI."""

    # Isolate identities explicitly in each request. A cookie retained from a
    # prior owner request must never turn a later Guest request into an
    # authenticated one.
    TEST_CLIENT = get_test_client(use_cookies=False)

    def setUp(self):
        super().setUp()
        self.original_user = frappe.session.user
        frappe.set_user("Administrator")
        self.users = []
        self.user_permissions = []
        self.user_desk_themes = []
        self.user_scope_contexts = []
        self.profiles = []
        self.projects = []
        self.boq_headers = []
        self.files = []
        self.file_paths = []
        self.session_sids = {}
        self.addCleanup(self._cleanup_fixtures)

        suffix = frappe.generate_hash(length=8)
        self.owner = self._create_user(f"native_security_owner_{suffix}@example.com")
        self.observer = self._create_user(f"native_security_observer_{suffix}@example.com")
        self.company = frappe.db.get_value("Company", {}, "name")
        self.assertTrue(self.company, "the test site must contain its normal setup Company")
        self.shared_profile_doctype = "Task"

        self.owner_theme = self._create_user_theme(self.owner)
        self.observer_theme = self._create_user_theme(self.observer)
        self._grant_company_scope(self.owner)
        self._grant_company_scope(self.observer)
        self.owner_scope = self._create_scope(self.owner)
        self.observer_scope = self._create_scope(self.observer)
        self.owner_profile = self._create_profile("owner", for_user=self.owner, priority=100)
        self.observer_profile = self._create_profile("observer", for_user=self.observer, priority=100)
        self.shared_profile = self._create_profile("shared", for_role="Accounts User", priority=10)
        self.theme_for_guest_check = frappe.db.get_value("Construction Theme", {}, "name")
        self.assertTrue(self.theme_for_guest_check, "site must contain its normal seeded Construction Theme")

        # The FrappeAPITestCase request helper runs WSGI in a separate thread
        # and database connection. Commit only these disposable fixtures so
        # the HTTP requests can see them; cleanup below removes and commits them.
        frappe.db.commit()

    def _create_user(self, email):
        # Record the deterministic name before insertion so cleanup remains
        # available if User validation fails after the row is written.
        self.users.append(email)
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Native security REST test",
                "enabled": 1,
                "user_type": "System User",
                "send_welcome_email": 0,
                "roles": [{"role": "Accounts User"}],
            }
        ).insert(ignore_permissions=True)
        return user.name

    def _grant_company_scope(self, user):
        """Grant only this test user the existing Company used by its scope."""
        permission = frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user,
                "allow": "Company",
                "for_value": self.company,
            }
        ).insert(ignore_permissions=True)
        self.user_permissions.append(permission.name)
        return permission.name

    def _create_project_manager(self, email):
        self.users.append(email)
        return (
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": "Native download test",
                    "enabled": 1,
                    "user_type": "System User",
                    "send_welcome_email": 0,
                    "roles": [{"role": "Project Manager"}],
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _create_project(self, suffix):
        project = frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": f"_Native download {suffix}",
                "company": self.company,
            }
        ).insert(ignore_permissions=True)
        self.projects.append(project.name)
        return project.name

    def _create_scoped_user(self, project, suffix):
        user = self._create_project_manager(f"native_download_{suffix}@example.com")
        self.user_scope_contexts.append(user)
        frappe.get_doc(
            {
                "doctype": "User Scope Context",
                "user": user,
                "company": self.company,
                "project": project,
            }
        ).insert(ignore_permissions=True)
        return user

    def _create_user_theme(self, user):
        frappe.set_user(user)
        try:
            doc = frappe.get_doc({"doctype": "User Desk Theme", "user": user, "inherit_from_site": 1})
            doc.insert(ignore_permissions=True)
            self.user_desk_themes.append(doc.name)
            return doc.name
        finally:
            frappe.set_user("Administrator")

    def _create_scope(self, user):
        frappe.set_user(user)
        try:
            doc = frappe.get_doc({"doctype": "User Scope Context", "user": user, "company": self.company})
            doc.insert(ignore_permissions=True)
            self.user_scope_contexts.append(doc.name)
            return doc.name
        finally:
            frappe.set_user("Administrator")

    def _create_profile(self, label, *, for_user=None, for_role=None, priority=10):
        # Form Layout Profile creation is an administrator-managed operation;
        # the ownership boundary under test is its `for_user` selector.
        frappe.set_user("Administrator")
        try:
            doc = frappe.get_doc(
                {
                    "doctype": "Form Layout Profile",
                    "reference_doctype": self.shared_profile_doctype,
                    "profile_name": f"_native_rest_{frappe.generate_hash(length=8)}_{label}",
                    "for_user": for_user,
                    "for_role": for_role,
                    "is_default": 0,
                    "is_system": 0,
                    "enabled": 1,
                    "priority": priority,
                    "layout_version": 1,
                    "sections_json": json.dumps({"version": 1, "sections": [{"label": label, "fields": []}]}),
                }
            )
            doc.insert(ignore_permissions=True)
            self.profiles.append(doc.name)
            return doc.name
        finally:
            frappe.set_user("Administrator")

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

    def _resource_path(self, doctype, name=None):
        parts = ["resource", quote(doctype, safe="")]
        if name is not None:
            parts.append(quote(name, safe=""))
        return self.get_path(*parts)

    def _resource_get(self, doctype, *, user=None, name=None, params=None):
        request_params = dict(params or {})
        if user:
            request_params["sid"] = self._login_sid(user)
        return self.get(self._resource_path(doctype, name), request_params)

    def _resource_put(self, doctype, name, *, user, data):
        request_data = {**data, "sid": self._login_sid(user)}
        return self.put(self._resource_path(doctype, name), request_data)

    def _method_get(self, method, *, user=None, params=None):
        request_params = dict(params or {})
        if user:
            request_params["sid"] = self._login_sid(user)
        return self.get(self.method(method), request_params)

    def _download_get(self, file_url, *, user=None):
        params = {"file_url": file_url}
        if user:
            params["sid"] = self._login_sid(user)
        return self.get(self.method("frappe.handler.download_file"), params)

    def _create_test_file(self, *, name, content, is_private, owner, attached_to=None):
        directory = Path(frappe.get_site_path("private" if is_private else "public", "files"))
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_bytes(content)
        self.file_paths.append(path)
        doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": name,
                "file_url": ("/private/files/" if is_private else "/files/") + name,
                "is_private": int(is_private),
                "owner": owner,
                "attached_to_doctype": attached_to[0] if attached_to else None,
                "attached_to_name": attached_to[1] if attached_to else None,
            }
        ).insert(ignore_permissions=True)
        self.files.append(doc.name)
        return doc

    def _cleanup_fixtures(self):
        try:
            frappe.set_user("Administrator")
            for name in self.files:
                if frappe.db.exists("File", name):
                    frappe.delete_doc("File", name, ignore_permissions=True, force=True)
            for name in self.boq_headers:
                if frappe.db.exists("BOQ Header", name):
                    frappe.delete_doc("BOQ Header", name, ignore_permissions=True, force=True)
            for name in self.projects:
                if frappe.db.exists("Project", name):
                    frappe.delete_doc("Project", name, ignore_permissions=True, force=True)
            for doctype, names in (
                ("Form Layout Profile", self.profiles),
                ("User Desk Theme", self.user_desk_themes),
            ):
                for name in names:
                    if frappe.db.exists(doctype, name):
                        frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
            for name in self.user_scope_contexts:
                if frappe.db.exists("User Scope Context", name):
                    frappe.db.delete("User Scope Context", {"name": name})
            for name in self.user_permissions:
                if frappe.db.exists("User Permission", name):
                    frappe.db.delete("User Permission", {"name": name})
            for user in self.users:
                if frappe.db.exists("User", user):
                    frappe.delete_doc("User", user, ignore_permissions=True, force=True)
            frappe.db.commit()
        finally:
            frappe.set_user(self.original_user)
            for path in self.file_paths:
                path.unlink(missing_ok=True)

    def test_user_desk_theme_item_and_list_are_owner_scoped_over_rest(self):
        owner_item = self._resource_get("User Desk Theme", user=self.owner, name=self.owner_theme)
        self.assertEqual(owner_item.status_code, 200, owner_item.get_data(as_text=True))
        self.assertEqual(owner_item.get_json()["data"]["user"], self.owner)

        foreign_item = self._resource_get("User Desk Theme", user=self.observer, name=self.owner_theme)
        self.assertEqual(foreign_item.status_code, 403, foreign_item.get_data(as_text=True))
        observer_item = self._resource_get("User Desk Theme", user=self.observer, name=self.observer_theme)
        self.assertEqual(observer_item.status_code, 200, observer_item.get_data(as_text=True))
        self.assertEqual(observer_item.get_json()["data"]["user"], self.observer)

        owner_list = self._resource_get("User Desk Theme", user=self.owner)
        observer_list = self._resource_get("User Desk Theme", user=self.observer)
        self.assertEqual(owner_list.status_code, 200, owner_list.get_data(as_text=True))
        self.assertEqual(observer_list.status_code, 200, observer_list.get_data(as_text=True))
        owner_names = {row["name"] for row in owner_list.get_json()["data"]}
        observer_names = {row["name"] for row in observer_list.get_json()["data"]}
        self.assertIn(self.owner_theme, owner_names)
        self.assertNotIn(self.owner_theme, observer_names)

        guest_item = self._resource_get("User Desk Theme", name=self.owner_theme)
        guest_list = self._resource_get("User Desk Theme")
        self.assertEqual(guest_item.status_code, 403, guest_item.get_data(as_text=True))
        self.assertEqual(guest_list.status_code, 403, guest_list.get_data(as_text=True))

    def test_user_scope_context_item_and_list_are_owner_scoped_over_rest(self):
        owner_item = self._resource_get("User Scope Context", user=self.owner, name=self.owner_scope)
        self.assertEqual(owner_item.status_code, 200, owner_item.get_data(as_text=True))
        self.assertEqual(owner_item.get_json()["data"]["user"], self.owner)

        foreign_item = self._resource_get("User Scope Context", user=self.observer, name=self.owner_scope)
        self.assertEqual(foreign_item.status_code, 403, foreign_item.get_data(as_text=True))
        observer_item = self._resource_get("User Scope Context", user=self.observer, name=self.observer_scope)
        self.assertEqual(observer_item.status_code, 200, observer_item.get_data(as_text=True))
        self.assertEqual(observer_item.get_json()["data"]["user"], self.observer)

        owner_list = self._resource_get("User Scope Context", user=self.owner)
        observer_list = self._resource_get("User Scope Context", user=self.observer)
        self.assertEqual(owner_list.status_code, 200, owner_list.get_data(as_text=True))
        self.assertEqual(observer_list.status_code, 200, observer_list.get_data(as_text=True))
        owner_names = {row["name"] for row in owner_list.get_json()["data"]}
        observer_names = {row["name"] for row in observer_list.get_json()["data"]}
        self.assertIn(self.owner_scope, owner_names)
        self.assertNotIn(self.owner_scope, observer_names)

        guest_item = self._resource_get("User Scope Context", name=self.owner_scope)
        guest_list = self._resource_get("User Scope Context")
        self.assertEqual(guest_item.status_code, 403, guest_item.get_data(as_text=True))
        self.assertEqual(guest_list.status_code, 403, guest_list.get_data(as_text=True))

    def test_user_scope_context_owner_write_cannot_reassign_record(self):
        own_update = self._resource_put(
            "User Scope Context",
            self.owner_scope,
            user=self.owner,
            data={"user": self.owner, "company": self.company},
        )
        self.assertEqual(own_update.status_code, 200, own_update.get_data(as_text=True))
        self.assertEqual(own_update.get_json()["data"]["user"], self.owner)

        reassignment = self._resource_put(
            "User Scope Context",
            self.owner_scope,
            user=self.owner,
            data={"user": self.observer, "company": self.company},
        )
        self.assertNotEqual(reassignment.status_code, 200, reassignment.get_data(as_text=True))

        persisted = self._resource_get("User Scope Context", user=self.owner, name=self.owner_scope)
        self.assertEqual(persisted.status_code, 200, persisted.get_data(as_text=True))
        self.assertEqual(persisted.get_json()["data"]["user"], self.owner)

        guest_write = self.put(
            self._resource_path("User Scope Context", self.owner_scope),
            {"user": self.observer, "company": self.company},
        )
        self.assertEqual(guest_write.status_code, 403, guest_write.get_data(as_text=True))

    def test_guest_theme_rest_and_settings_methods_are_denied_but_boot_is_minimal(self):
        authenticated_theme_item = self._resource_get(
            "Construction Theme", user=self.owner, name=self.theme_for_guest_check
        )
        authenticated_theme_list = self._resource_get("Construction Theme", user=self.owner)
        authenticated_settings_item = self._resource_get(
            "Modern Theme Settings", user=self.owner, name="Modern Theme Settings"
        )
        theme_item = self._resource_get("Construction Theme", name=self.theme_for_guest_check)
        theme_list = self._resource_get("Construction Theme")
        settings_item = self._resource_get("Modern Theme Settings", name="Modern Theme Settings")
        self.assertEqual(
            authenticated_theme_item.status_code, 200, authenticated_theme_item.get_data(as_text=True)
        )
        self.assertEqual(
            authenticated_theme_list.status_code, 200, authenticated_theme_list.get_data(as_text=True)
        )
        self.assertEqual(
            authenticated_settings_item.status_code, 200, authenticated_settings_item.get_data(as_text=True)
        )
        self.assertEqual(theme_item.status_code, 403, theme_item.get_data(as_text=True))
        self.assertEqual(theme_list.status_code, 403, theme_list.get_data(as_text=True))
        self.assertEqual(settings_item.status_code, 403, settings_item.get_data(as_text=True))
        # Modern Theme Settings is a Single DocType. The generic resource-list
        # route returned a stock SQL ProgrammingError here and for the native
        # System Settings Single, so it is unsupported and is not asserted as
        # an authorization denial. Keep supported item/API reads covered.

        boot = self._method_get("construction.api.theme_api.get_user_theme_for_boot")
        self.assertEqual(boot.status_code, 200, boot.get_data(as_text=True))
        boot_payload = boot.get_json()["message"]
        self.assertEqual(set(boot_payload), {"theme", "mode", "source"})
        self.assertEqual(boot_payload["mode"], "light")

        css = self._method_get("construction.api.theme_api.get_theme_css", params={"theme_name": "light"})
        settings = self._method_get("construction.api.theme_api.get_modern_theme_settings")
        self.assertEqual(css.status_code, 403, css.get_data(as_text=True))
        self.assertEqual(settings.status_code, 403, settings.get_data(as_text=True))

    def test_guest_theme_boot_read_and_logger_failures_return_minimal_fallback(self):
        from construction.api import theme_api

        original_user = frappe.session.user
        frappe.set_user("Guest")
        try:
            with (
                patch.object(
                    frappe.db,
                    "get_single_value",
                    side_effect=RuntimeError("simulated Singleton settings read failure"),
                ),
                patch.object(theme_api.frappe, "logger", side_effect=RuntimeError("logger unavailable")),
            ):
                result = theme_api.get_user_theme_for_boot()
        finally:
            frappe.set_user(original_user)

        self.assertEqual(result, {"theme": "light", "mode": "light", "source": "error_fallback"})

    def test_form_layout_native_and_api_routes_filter_personal_profiles(self):
        owner_item = self._resource_get("Form Layout Profile", user=self.owner, name=self.owner_profile)
        foreign_item = self._resource_get("Form Layout Profile", user=self.owner, name=self.observer_profile)
        shared_item = self._resource_get("Form Layout Profile", user=self.owner, name=self.shared_profile)
        self.assertEqual(owner_item.status_code, 200, owner_item.get_data(as_text=True))
        self.assertEqual(foreign_item.status_code, 403, foreign_item.get_data(as_text=True))
        self.assertEqual(shared_item.status_code, 200, shared_item.get_data(as_text=True))

        native_list = self._resource_get(
            "Form Layout Profile",
            user=self.owner,
            params={"filters": json.dumps([["reference_doctype", "=", self.shared_profile_doctype]])},
        )
        self.assertEqual(native_list.status_code, 200, native_list.get_data(as_text=True))
        native_names = {row["name"] for row in native_list.get_json()["data"]}
        self.assertIn(self.owner_profile, native_names)
        self.assertIn(self.shared_profile, native_names)
        self.assertNotIn(self.observer_profile, native_names)

        api_list = self._method_get(
            "construction.construction.api.layout_api.list_layouts",
            user=self.owner,
            params={"doctype": self.shared_profile_doctype},
        )
        self.assertEqual(api_list.status_code, 200, api_list.get_data(as_text=True))
        api_names = {row["name"] for row in api_list.get_json()["message"]}
        self.assertIn(self.owner_profile, api_names)
        self.assertIn(self.shared_profile, api_names)
        self.assertNotIn(self.observer_profile, api_names)

        observer_native = self._resource_get(
            "Form Layout Profile", user=self.observer, name=self.observer_profile
        )
        owner_cross_read = self._resource_get(
            "Form Layout Profile", user=self.observer, name=self.owner_profile
        )
        self.assertEqual(observer_native.status_code, 200, observer_native.get_data(as_text=True))
        self.assertEqual(owner_cross_read.status_code, 403, owner_cross_read.get_data(as_text=True))

        observer_api_list = self._method_get(
            "construction.construction.api.layout_api.list_layouts",
            user=self.observer,
            params={"doctype": self.shared_profile_doctype},
        )
        self.assertEqual(observer_api_list.status_code, 200, observer_api_list.get_data(as_text=True))
        observer_api_names = {row["name"] for row in observer_api_list.get_json()["message"]}
        self.assertIn(self.observer_profile, observer_api_names)
        self.assertIn(self.shared_profile, observer_api_names)
        self.assertNotIn(self.owner_profile, observer_api_names)

        active = self._method_get(
            "construction.construction.api.layout_api.get_active_layout",
            user=self.owner,
            params={"doctype": self.shared_profile_doctype},
        )
        self.assertEqual(active.status_code, 200, active.get_data(as_text=True))
        self.assertEqual(active.get_json()["message"]["name"], self.owner_profile)

        guest_shared = self._resource_get("Form Layout Profile", name=self.shared_profile)
        guest_personal = self._resource_get("Form Layout Profile", name=self.owner_profile)
        guest_foreign = self._resource_get("Form Layout Profile", name=self.observer_profile)
        guest_list = self._method_get(
            "construction.construction.api.layout_api.list_layouts",
            params={"doctype": self.shared_profile_doctype},
        )
        guest_active = self._method_get(
            "construction.construction.api.layout_api.get_active_layout",
            params={"doctype": self.shared_profile_doctype},
        )
        self.assertEqual(guest_shared.status_code, 403, guest_shared.get_data(as_text=True))
        self.assertEqual(guest_personal.status_code, 403, guest_personal.get_data(as_text=True))
        self.assertEqual(guest_foreign.status_code, 403, guest_foreign.get_data(as_text=True))
        self.assertEqual(guest_list.status_code, 403, guest_list.get_data(as_text=True))
        self.assertEqual(guest_active.status_code, 403, guest_active.get_data(as_text=True))

    def test_native_download_denies_guest_and_unrelated_user_but_keeps_public_files(self):
        suffix = uuid4().hex[:10]
        project = self._create_project(suffix)
        self.owner = self._create_scoped_user(project, f"owner_{suffix}")
        header = frappe.get_doc(
            {"doctype": "BOQ Header", "project": project, "title": f"_Native download {suffix}"}
        ).insert(ignore_permissions=True)
        self.boq_headers.append(header.name)
        restricted = self._create_test_file(
            name=f"native_download_{suffix}.txt",
            content=b"restricted test attachment",
            is_private=True,
            owner=self.owner,
            attached_to=("BOQ Header", header.name),
        )
        public = self._create_test_file(
            name=f"native_public_{suffix}.txt",
            content=b"public test attachment",
            is_private=False,
            owner="Administrator",
        )
        frappe.db.commit()

        owner_response = self._download_get(restricted.file_url, user=self.owner)
        guest_response = self._download_get(restricted.file_url)
        unrelated_response = self._download_get(restricted.file_url, user=self.observer)
        public_response = self._download_get(public.file_url)

        self.assertEqual(owner_response.status_code, 200, owner_response.get_data(as_text=True))
        self.assertEqual(owner_response.get_data(), b"restricted test attachment")
        self.assertEqual(guest_response.status_code, 403, guest_response.get_data(as_text=True))
        self.assertEqual(unrelated_response.status_code, 403, unrelated_response.get_data(as_text=True))
        self.assertEqual(public_response.status_code, 200, public_response.get_data(as_text=True))
        self.assertEqual(public_response.get_data(), b"public test attachment")
