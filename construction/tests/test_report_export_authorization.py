"""Native regression coverage for standalone report files and stored parents."""

import json
import unittest
import uuid
from pathlib import Path

import frappe

from construction.api.construction_reports import report_view
from construction.overrides.file_download import download_file
from construction.overrides.file_permissions import has_file_parent_permission


class TestReportExportAuthorization(unittest.TestCase):
    def setUp(self):
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        frappe.local._boq_perm_scope_dims = {}
        frappe.local.request_cache.clear()
        self.paths = []
        self.addCleanup(self.cleanup)
        companies = frappe.get_all("Company", pluck="name")
        self.assertGreaterEqual(len(companies), 2)
        self.company, self.other_company = companies[:2]
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
                        "roles": [{"role": "Project Manager"}],
                    }
                ).insert()
            for company in companies[:2]:
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

    def cleanup(self):
        frappe.db.rollback()
        frappe.set_user(self.previous_user)
        for path in self.paths:
            path.unlink(missing_ok=True)
        frappe.local.request_cache.clear()
        frappe.local._boq_perm_scope_dims = {}

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
