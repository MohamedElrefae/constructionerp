"""Regression coverage for ownership-aware performance-harness cleanup."""

import unittest

import frappe

from construction import perf_boq_capture


class TestPerfBOQCaptureCleanup(unittest.TestCase):
    def setUp(self):
        self.original_user = frappe.session.user
        frappe.set_user("Administrator")
        self.created_projects = []
        self.created_headers = []
        self.created_structures = []
        self.addCleanup(self._cleanup_fixtures)

    def _cleanup_fixtures(self):
        try:
            frappe.set_user("Administrator")
            for doctype, names in (
                ("BOQ Structure", self.created_structures),
                ("BOQ Header", self.created_headers),
                ("Project", self.created_projects),
            ):
                for name in names:
                    if frappe.db.exists(doctype, name):
                        frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
            frappe.db.commit()
        finally:
            frappe.set_user(self.original_user)

    def test_capture_preserves_a_preexisting_reused_project(self):
        headers_before = set(
            frappe.get_all(
                "BOQ Header",
                filters={"title": ["like", "_Perf Harness BOQ %"]},
                pluck="name",
                limit_page_length=0,
            )
        )
        project = frappe.db.get_value("Project", {"project_name": "_Perf Harness Project"}, "name")
        if not project:
            company = frappe.db.get_value("Company", {}, "name")
            self.assertTrue(company, "the test site must contain its normal setup Company")
            project = (
                frappe.get_doc(
                    {"doctype": "Project", "project_name": "_Perf Harness Project", "company": company}
                )
                .insert(ignore_permissions=True)
                .name
            )
            self.created_projects.append(project)
            frappe.db.commit()

        perf_boq_capture._capture(0, cleanup=True)

        self.assertTrue(frappe.db.exists("Project", project), "cleanup must preserve the reused Project")
        headers_after = set(
            frappe.get_all(
                "BOQ Header",
                filters={"title": ["like", "_Perf Harness BOQ %"]},
                pluck="name",
                limit_page_length=0,
            )
        )
        self.assertEqual(headers_after, headers_before, "capture cleanup must remove only its own BOQ Header")

    def test_cleanup_deletes_a_project_only_when_capture_created_it(self):
        company = frappe.db.get_value("Company", {}, "name")
        self.assertTrue(company, "the test site must contain its normal setup Company")
        project = (
            frappe.get_doc(
                {
                    "doctype": "Project",
                    "project_name": f"_Perf Harness Owned {frappe.generate_hash(length=8)}",
                    "company": company,
                }
            )
            .insert(ignore_permissions=True)
            .name
        )
        self.created_projects.append(project)
        header = frappe.get_doc(
            {"doctype": "BOQ Header", "title": "_Perf Harness Owned Header", "project": project}
        ).insert(ignore_permissions=True)
        self.created_headers.append(header.name)
        section = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Perf Section",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        self.created_structures.append(section.name)
        frappe.db.commit()

        perf_boq_capture._cleanup(header.name, section.name, project, project_created=True)

        self.assertFalse(frappe.db.exists("Project", project))
        self.assertFalse(frappe.db.exists("BOQ Header", header.name))
        self.assertFalse(frappe.db.exists("BOQ Structure", section.name))
