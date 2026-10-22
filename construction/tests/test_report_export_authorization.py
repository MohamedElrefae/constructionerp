"""Native regression coverage for standalone report files and stored parents.

Self-contained fixtures
-----------------------
This module provisions everything it asserts on and removes it again, so it
behaves identically on the disposable CI site (which seeds a single
``_Test Company`` and no custom permissions) and on a developer site:

* two Companies (the CI fixture company plus a second, test-owned one);
* a Project owned by the second Company (used by the stored-parent case);
* the documented narrow ``Company`` read grant for the estimation audience
  (F21-D001, ``scripts/apply_report_audience_company_read.py``) applied through
  Frappe's native ``add_permission`` API, which copies the standard rows before
  adding the read-only row so the rest of the Company permission table is
  preserved;
* per-user native ``Company`` User Permissions and an active ``User Scope
  Context``; and
* a private generated export file.

The denial assertions are kept exactly as written: the reader must natively be
allowed to read the company, so every refusal below is attributable to the
selected scope (or ownership), never to a missing role permission. Production
permission code is not touched.
"""

import json
import unittest
import uuid
from pathlib import Path

import frappe

from construction.api.construction_reports import report_view
from construction.overrides.file_download import download_file
from construction.overrides.file_permissions import has_file_parent_permission

# Canonical CI fixture company (see .github/ci/business_fixtures.py).
COMPANY = "_Test Company"
COMPANY_ABBR = "_TC"
# Test-owned second company, created only if absent.
OTHER_COMPANY = "F31 Other Company"
OTHER_COMPANY_ABBR = "F31OC"
# The estimation audience role that report_view's Company gate is designed for.
READER_ROLE = "Project Manager"


class TestReportExportAuthorization(unittest.TestCase):
    def setUp(self):
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        frappe.local._boq_perm_scope_dims = {}
        frappe.local.request_cache.clear()
        self.paths = []
        self._created_companies = []
        self._created_projects = []
        self._created_custom_perms = []
        self.addCleanup(self.cleanup)

        self.company = self._ensure_company(COMPANY, COMPANY_ABBR)
        self.other_company = self._ensure_company(OTHER_COMPANY, OTHER_COMPANY_ABBR)
        self.assertNotEqual(self.company, self.other_company)

        self._grant_company_read(READER_ROLE)
        self._refresh_company_authorization_cache()

        self.other_project = self._ensure_project("F31 Other Company Project", self.other_company)

        self.reader = "f31-export-reader@qualification.invalid"
        self.other_reader = "f31-export-other@qualification.invalid"
        for user in (self.reader, self.other_reader):
            if not frappe.db.exists("User", user):
                frappe.get_doc(
                    {
                        "doctype": "User",
                        "email": user,
                        "first_name": "F31 Reader",
                        "send_welcome_email": 0,
                        "roles": [{"role": READER_ROLE}],
                    }
                ).insert()
            for company in (self.company, self.other_company):
                if not frappe.db.exists(
                    "User Permission", {"user": user, "allow": "Company", "for_value": company}
                ):
                    frappe.get_doc(
                        {
                            "doctype": "User Permission",
                            "user": user,
                            "allow": "Company",
                            "for_value": company,
                            "apply_to_all_doctypes": 1,
                        }
                    ).insert()
            if not frappe.db.exists("User Scope Context", {"user": user}):
                frappe.get_doc(
                    {"doctype": "User Scope Context", "user": user, "company": self.company}
                ).insert()
        name = "F19_price_history_" + uuid.uuid4().hex + ".json"
        path = Path(frappe.get_site_path("private", "files", name))
        path.write_text(
            json.dumps({"report": "price_history", "filters": {"company": self.company}, "rows": []})
        )
        self.paths.append(path)
        frappe.set_user(self.reader)
        self.file = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": name,
                "file_url": "/private/files/" + name,
                "is_private": 1,
                "owner": self.reader,
            }
        ).insert(ignore_permissions=True)
        frappe.set_user("Administrator")

    # fixtures ---------------------------------------------------------------

    def _ensure_company(self, name, abbr):
        if frappe.db.exists("Company", name):
            return name
        # A bare CI site has no Warehouse Type "Transit"; ERPNext's Company
        # controller expects it (mirrors .github/ci/business_fixtures.py).
        if not frappe.db.exists("Warehouse Type", "Transit"):
            frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)
        company = frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": name,
                "abbr": abbr,
                "default_currency": "INR",
                "country": "India",
                "create_chart_of_accounts_based_on": "Standard Template",
                "chart_of_accounts": "Standard",
                "enable_perpetual_inventory": 0,
            }
        ).insert(ignore_permissions=True)
        self._created_companies.append(company.name)
        return company.name

    def _ensure_project(self, project_name, company):
        existing = frappe.db.get_value("Project", {"project_name": project_name, "company": company}, "name")
        if existing:
            return existing
        project = (
            frappe.get_doc(
                {
                    "doctype": "Project",
                    "project_name": project_name,
                    "company": company,
                    "naming_series": "PROJ-.####",
                }
            )
            .insert(ignore_permissions=True)
            .name
        )
        self._created_projects.append(project)
        return project

    def _grant_company_read(self, role):
        """Apply the F21-D001 read-only Company grant for ``role`` (native route)."""
        before = set(frappe.get_all("Custom DocPerm", filters={"parent": "Company"}, pluck="name"))
        frappe.permissions.add_permission("Company", role, 0, "read")
        after = set(frappe.get_all("Custom DocPerm", filters={"parent": "Company"}, pluck="name"))
        self._created_custom_perms = sorted(after - before)

    def _refresh_company_authorization_cache(self):
        """Drop cached Company meta and evaluated role permissions."""
        frappe.clear_cache(doctype="Company")
        role_cache = getattr(frappe.local, "role_permissions", None)
        if role_cache is not None:
            role_cache.clear()
        frappe.local.request_cache.clear()

    def cleanup(self):
        # Discard uncommitted fixture writes first; then remove anything that a
        # stray interior commit could have made durable. Nothing in the exercised
        # export/report path commits, so the rollback normally owns cleanup.
        frappe.db.rollback()
        frappe.set_user("Administrator")
        removed = False
        for name in self._created_custom_perms:
            if frappe.db.exists("Custom DocPerm", name):
                frappe.delete_doc("Custom DocPerm", name, ignore_permissions=True, force=True)
                removed = True
        for name in self._created_projects:
            if frappe.db.exists("Project", name):
                frappe.delete_doc("Project", name, ignore_permissions=True, force=True)
                removed = True
        for name in self._created_companies:
            if frappe.db.exists("Company", name):
                frappe.delete_doc("Company", name, ignore_permissions=True, force=True)
                removed = True
        if removed:
            frappe.db.commit()
        frappe.clear_cache(doctype="Company")
        frappe.set_user(self.previous_user)
        for path in self.paths:
            path.unlink(missing_ok=True)
        frappe.local.request_cache.clear()
        frappe.local._boq_perm_scope_dims = {}
        role_cache = getattr(frappe.local, "role_permissions", None)
        if role_cache is not None:
            role_cache.clear()

    # tests ------------------------------------------------------------------

    def test_guest_cannot_download_unattached_export(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            download_file(self.file.file_url)

    def test_other_user_cannot_download_owned_export(self):
        frappe.set_user(self.other_reader)
        with self.assertRaises(frappe.PermissionError):
            download_file(self.file.file_url)

    def test_owner_can_download_authorized_export(self):
        frappe.set_user(self.reader)
        self.assertTrue(frappe.has_permission("Company", "read", doc=self.company))
        download_file(self.file.file_url)
        self.assertIn(
            self.company.encode(),
            frappe.local.response.filecontent.encode()
            if isinstance(frappe.local.response.filecontent, str)
            else frappe.local.response.filecontent,
        )

    def test_selected_company_blocks_other_natively_allowed_company(self):
        frappe.set_user(self.reader)
        self.assertTrue(frappe.has_permission("Company", "read", doc=self.other_company))
        with self.assertRaises(frappe.PermissionError):
            report_view("price_history", company=self.other_company)

    def test_owner_export_denied_after_selected_company_switch(self):
        scope_name = frappe.db.get_value("User Scope Context", {"user": self.reader}, "name")
        scope = frappe.get_doc("User Scope Context", scope_name)
        scope.company = self.other_company
        scope.save()
        # A subsequent HTTP request has a fresh request-local scope cache.
        frappe.local._boq_perm_scope_dims = {}
        frappe.local.request_cache.clear()
        frappe.set_user(self.reader)
        self.assertTrue(frappe.has_permission("Company", "read", doc=self.company))
        with self.assertRaises(frappe.PermissionError):
            download_file(self.file.file_url)

    def test_export_protection_cannot_be_renamed_away(self):
        doc = frappe.get_doc("File", self.file.name)
        doc.file_name = "ordinary.json"
        doc.file_url = "/private/files/ordinary.json"
        self.assertFalse(has_file_parent_permission(doc, "write", user=self.reader))

    def test_stored_foreign_boq_parent_blocks_detachment(self):
        project = frappe.db.get_value("Project", {"company": self.other_company}, "name")
        self.assertTrue(project)
        header = frappe.get_doc({"doctype": "BOQ Header", "project": project, "status": "Draft"}).insert()
        name = "F31_parent_" + uuid.uuid4().hex + ".json"
        path = Path(frappe.get_site_path("private", "files", name))
        path.write_text("{}")
        self.paths.append(path)
        file = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": name,
                "file_url": "/private/files/" + name,
                "is_private": 1,
                "attached_to_doctype": "BOQ Header",
                "attached_to_name": header.name,
            }
        ).insert()
        doc = frappe.get_doc("File", file.name)
        doc.attached_to_doctype = None
        doc.attached_to_name = None
        self.assertFalse(has_file_parent_permission(doc, "write", user=self.reader))
