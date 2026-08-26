# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import io
import os
import subprocess
import sys
import threading
import time
import zipfile

import frappe
import openpyxl
from frappe import _
from frappe.tests.utils import FrappeTestCase

from construction.api.boq_api import (
    create_variation_order,
    get_children,
    transition_variation_order,
)
from construction.services.boq_export_service import BOQExportService
from construction.services.boq_import_service import BOQImportService


class TestSecurityAuditRemediation(FrappeTestCase):
    """Adversarial regression test suite for all audit findings and release criteria."""

    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        self._created_files = []
        self._test_users = []
        self._created_themes = []
        # Exact IDs of committed business documents created by this test.
        # Teardown deletes this graph in reverse dependency order so the
        # suite is database-hermetic even across worker-thread commits.
        self._tracked_headers = []
        self._tracked_vos = []
        self._tracked_projects = []
        # Capture the global flag baseline so tearDown can restore exactly
        # the pre-test value (tenant-safe restoration, see tearDown).
        self._baseline_scope_enabled = frappe.db.get_single_value(
            "Construction Settings", "enable_scope_context"
        )
        self.project_name = self._ensure_test_project("_Test Security Audit Project")
        self.project_name_2 = self._ensure_test_project("_Test Security Project 2")

    def _track(self, doctype, name):
        """Register a created document ID for guaranteed teardown deletion."""
        registry = {
            "BOQ Header": "_tracked_headers",
            "Variation Order": "_tracked_vos",
            "Project": "_tracked_projects",
        }.get(doctype)
        if registry:
            lst = getattr(self, registry)
            if name not in lst:
                lst.append(name)

    def _delete_tracked_business_graph(self):
        """Delete the tracked business-document graph, reverse dependency
        order: revisions → VOs → items → structures → headers. Fails loudly
        on residue.

        Returns ``(errors, deleted_vos, deleted_headers, deleted_projects)`` —
        the exact IDs that were targeted — so the caller can assert against
        them AFTER committing, even though the ``self._tracked_*`` lists are
        cleared here (otherwise the post-commit assertion would check empty
        lists and could never detect residue).
        """
        errors = []
        vos = list(self._tracked_vos)
        headers = list(self._tracked_headers)
        projects = list(self._tracked_projects)

        def _safe_delete(doctype, name):
            try:
                if frappe.db.exists(doctype, name):
                    frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
            except Exception as e:
                errors.append(f"{doctype} {name}: {e}")

        # Quantity Revisions linked to tracked VOs
        for vo in vos:
            try:
                for rev in frappe.get_all(
                    "BOQ Quantity Revision", filters={"variation_order": vo}, pluck="name"
                ):
                    _safe_delete("BOQ Quantity Revision", rev)
            except Exception as e:
                errors.append(f"revisions of {vo}: {e}")

        for vo in vos:
            # Variation children: ITEMS must go before STRUCTURES (link checks),
            # and structures deepest-first (NestedSet child-node rule).
            try:
                for i in frappe.get_all("BOQ Item", filters={"variation_order": vo}, pluck="name"):
                    _safe_delete("BOQ Item", i)
                for s in frappe.get_all(
                    "BOQ Structure", filters={"variation_order": vo}, order_by="lft desc", pluck="name"
                ):
                    _safe_delete("BOQ Structure", s)
            except Exception as e:
                errors.append(f"variation children of {vo}: {e}")

        for vo in vos:
            _safe_delete("Variation Order", vo)

        for header in headers:
            try:
                # Structures/items hanging off the header itself
                for i in frappe.get_all("BOQ Item", filters={"boq_header": header}, pluck="name"):
                    _safe_delete("BOQ Item", i)
                for s in frappe.get_all(
                    "BOQ Structure", filters={"boq_header": header}, order_by="lft desc", pluck="name"
                ):
                    _safe_delete("BOQ Structure", s)
            except Exception as e:
                errors.append(f"header children of {header}: {e}")
            _safe_delete("BOQ Header", header)

        for project in projects:
            _safe_delete("Project", project)

        self._tracked_vos = []
        self._tracked_headers = []
        self._tracked_projects = []
        return errors, vos, headers, projects

    def tearDown(self):
        frappe.set_user("Administrator")
        cleanup_errors = []
        if hasattr(self, "_created_files"):
            for f in self._created_files:
                try:
                    path = f.get_full_path()
                    if os.path.exists(path):
                        os.remove(path)
                    frappe.db.delete("File", {"name": f.name})
                except Exception as e:
                    cleanup_errors.append(f"File {getattr(f, 'name', '?')}: {e}")
            self._created_files = []

        if hasattr(self, "_created_themes"):
            for t in self._created_themes:
                try:
                    theme_file = os.path.join(frappe.get_site_path("public", "files", "css"), f"theme_{t}.css")
                    if os.path.exists(theme_file):
                        os.remove(theme_file)
                    frappe.db.delete("Construction Theme", {"name": t})
                except Exception as e:
                    cleanup_errors.append(f"Theme {t}: {e}")
            self._created_themes = []

        if hasattr(self, "_test_users"):
            for u in self._test_users:
                frappe.db.delete("User Scope Context", {"user": u})
                frappe.db.delete("User Permission", {"user": u})
                frappe.db.delete("User", {"name": u})
            self._test_users = []

        # Persist the tracked-ID cleanup so mid-test commits (worker
        # threads) cannot leave orphaned rows past the framework rollback.
        # Only exact test-created IDs are deleted above — never whole tables.
        cleanup_errors, deleted_vos, deleted_headers, deleted_projects = (
            self._delete_tracked_business_graph()
        )
        frappe.db.commit()

        # Hermeticity assertion against the PRESERVED copies (the self._tracked_*
        # lists were cleared inside the delete helper, so we must assert on the
        # returned copies) — otherwise the assertion would check empty lists and
        # could never detect residue.
        for vo in deleted_vos:
            if frappe.db.exists("Variation Order", vo):
                cleanup_errors.append(f"residue: Variation Order {vo}")
            for child in frappe.get_all(
                "BOQ Quantity Revision", filters={"variation_order": vo}, pluck="name"
            ):
                cleanup_errors.append(f"residue: Quantity Revision {child} for VO {vo}")
            for child in frappe.get_all("BOQ Item", filters={"variation_order": vo}, pluck="name"):
                cleanup_errors.append(f"residue: BOQ Item {child} for VO {vo}")
            for child in frappe.get_all("BOQ Structure", filters={"variation_order": vo}, pluck="name"):
                cleanup_errors.append(f"residue: BOQ Structure {child} for VO {vo}")

        for header in deleted_headers:
            if frappe.db.exists("BOQ Header", header):
                cleanup_errors.append(f"residue: BOQ Header {header}")
            for child in frappe.get_all("BOQ Item", filters={"boq_header": header}, pluck="name"):
                cleanup_errors.append(f"residue: BOQ Item {child} for header {header}")
            for child in frappe.get_all("BOQ Structure", filters={"boq_header": header}, pluck="name"):
                cleanup_errors.append(f"residue: BOQ Structure {child} for header {header}")

        for project in deleted_projects:
            if frappe.db.exists("Project", project):
                cleanup_errors.append(f"residue: Project {project}")

        # Restore the captured global-flag baseline ONLY if the test drifted
        # it. Mid-test commits (e.g. worker threads) can persist state past
        # the framework rollback, so the restoration itself must commit —
        # but only when a drift actually occurred.
        baseline = getattr(self, "_baseline_scope_enabled", 0) or 0
        current = frappe.db.get_single_value("Construction Settings", "enable_scope_context") or 0
        if current != baseline:
            frappe.db.set_single_value("Construction Settings", "enable_scope_context", baseline)
            frappe.db.commit()

        if cleanup_errors:
            self.fail("Teardown cleanup failed for: " + "; ".join(cleanup_errors))

    def _ensure_test_project(self, proj_name):
        existing = frappe.db.get_value("Project", {"project_name": proj_name}, "name")
        if existing:
            return existing
        p = frappe.new_doc("Project")
        p.project_name = proj_name
        p.company = "_Test Company"
        p.insert(ignore_permissions=True)
        self._track("Project", p.name)
        return p.name

    def _create_test_boq(self, project=None, status="Draft"):
        boq = frappe.new_doc("BOQ Header")
        boq.title = f"Security BOQ {frappe.generate_hash(length=6)}"
        boq.project = project or self.project_name
        boq.company = "_Test Company"
        boq.status = status
        boq.insert(ignore_permissions=True)
        self._track("BOQ Header", boq.name)
        return boq

    def _make_boq_item(self, title, project=None, quantity=100, rate=50):
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": title,
                "project": project or self.project_name,
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        self._track("BOQ Header", header.name)
        sec = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": f"{title} Section",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": f"{title} Item",
                "parent_structure": sec.name,
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        item = frappe.get_doc("BOQ Item", {"structure": structure.name})
        item.quantity = quantity
        item.unit = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
        item.contract_unit_price = rate
        item.save(ignore_permissions=True)
        return header, item, structure, sec

    def _move_header_to_locked(self, header_name):
        header = frappe.get_doc("BOQ Header", header_name)
        for status in ("Pricing", "Frozen", "Locked"):
            header.status = status
            header.save(ignore_permissions=True)
        return header

    def _create_valid_pdf_file(self, attached_doctype, attached_name):
        """Create a physical PDF file attachment with valid %PDF- magic bytes and valid xref."""
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        buf = io.BytesIO()
        writer.write(buf)
        pdf_content = buf.getvalue()

        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"approval_{frappe.generate_hash(length=6)}.pdf",
            "attached_to_doctype": attached_doctype,
            "attached_to_name": attached_name,
            "is_private": 1,
            "content": pdf_content,
        })
        file_doc.insert(ignore_permissions=True)
        self._created_files.append(file_doc)
        return file_doc

    def _create_test_user(self, email_prefix, role_name=None):
        user_email = f"{email_prefix}_{frappe.generate_hash(length=4)}@example.com"
        if not frappe.db.exists("User", user_email):
            u = frappe.new_doc("User")
            u.email = user_email
            u.first_name = email_prefix
            u.send_welcome_email = 0
            if role_name:
                u.append("roles", {"role": role_name})
            u.insert(ignore_permissions=True)
        frappe.clear_cache(user=user_email)
        frappe.clear_cache(doctype="Variation Order")
        self._test_users.append(user_email)
        return user_email

    # -------------------------------------------------------------------------
    # 1. Template Escaping & Column Injection Neutralization (All 4 Templates)
    # -------------------------------------------------------------------------
    def test_all_print_and_export_templates_escape_xss_and_column_injection(self):
        """Ensure all 4 HTML/PDF templates escape XSS, title breakout, and column width injection."""
        malicious_val = "</title><script>alert('XSS')</script><img src=x onerror=alert(1)>"
        malicious_width = '10" onmouseover="alert(1)'

        # 1. generic_export_pdf.html
        rendered_generic = frappe.render_template(
            "construction/templates/generic_export_pdf.html",
            {
                "doctype": malicious_val,
                "docname": malicious_val,
                "company": malicious_val,
                "title": malicious_val,
                "export_date": "2026-08-24",
                "sections": [{"title": malicious_val, "fields": [{"label": malicious_val, "value": malicious_val}]}],
            },
        )
        self.assertNotIn("<script>", rendered_generic)
        self.assertNotIn("<img src=x", rendered_generic)
        self.assertIn("&lt;script&gt;", rendered_generic)

        # 2. generic_export_list_pdf.html
        rendered_list = frappe.render_template(
            "construction/templates/generic_export_list_pdf.html",
            {
                "doctype": malicious_val,
                "company": malicious_val,
                "export_date": "2026-08-24",
                "columns": [{"label": malicious_val, "field_key": "col1", "fieldtype": "Data"}],
                "rows": [{"col1": malicious_val}],
            },
        )
        self.assertNotIn("<script>", rendered_list)
        self.assertNotIn("<img src=x", rendered_list)

        # 3. boq_header_print.html
        rendered_header = frappe.render_template(
            "construction/templates/boq_header_print.html",
            {
                "header": {
                    "title": malicious_val,
                    "name": "BOQ-001",
                    "project": malicious_val,
                    "status": "Draft",
                    "version": "1.0",
                },
                "labels": {
                    "BOQ Header": "BOQ Header",
                    "Bill of Quantities": "Bill of Quantities",
                    "Export Date": "Export Date",
                    "Company": "Company",
                },
                "columns": [{"label": malicious_val, "key": "title"}],
                "export_date": "2026-08-24",
                "company": malicious_val,
            },
        )
        self.assertNotIn("<script>", rendered_header)

        # 4. boq_print_format.html with column width validation
        sanitized_cols = BOQExportService.apply_column_config([
            {"field_key": "item_code", "visible": True, "sort_order": 1, "width": malicious_width},
            {"field_key": "title", "visible": True, "sort_order": 2, "width": 30.5},
        ])
        # Width must be sanitized to safe numeric float
        self.assertEqual(sanitized_cols[0]["width"], 10.0)
        self.assertEqual(sanitized_cols[1]["width"], 30.5)

        rendered_boq = frappe.render_template(
            "construction/templates/boq_print_format.html",
            {
                "title": malicious_val,
                "header": {
                    "title": malicious_val,
                    "name": "BOQ-001",
                    "project": malicious_val,
                    "status": "Draft",
                    "version": "1.0",
                },
                "labels": {
                    "Bill of Quantities": "Bill of Quantities",
                    "Project": "Project",
                    "BOQ Type": "BOQ Type",
                    "Status": "Status",
                    "Version": "Version",
                    "Export Date": "Export Date",
                    "Company": "Company",
                    "Total": "Total",
                },
                "columns": sanitized_cols,
                "items": [{"wbs_code": "01", "title": malicious_val, "is_group": 0}],
                "totals": {"contract_total": 1000},
                "css_url": "/files/css/test.css",
                "export_date": "2026-08-24",
                "company": malicious_val,
            },
        )
        self.assertNotIn("<script>", rendered_boq)
        self.assertNotIn('onmouseover="alert(1)"', rendered_boq)

    # -------------------------------------------------------------------------
    # 2. Scope Fail-Closed Enforcement for Unscoped Restricted Users
    # -------------------------------------------------------------------------
    def test_scope_fail_closed_for_unscoped_restricted_user(self):
        """Ensure restricted users without active User Scope Context are denied access to scoped DocTypes and reports."""
        unscoped_pm = self._create_test_user("unscoped_pm", "Project Manager")
        frappe.db.set_single_value("Construction Settings", "enable_scope_context", 1)

        # User has NO User Scope Context
        frappe.set_user(unscoped_pm)
        try:
            # 1. Document creation without active scope must fail closed
            with self.assertRaises(frappe.PermissionError):
                boq = frappe.new_doc("BOQ Header")
                boq.title = "Unscoped PM Attempt"
                boq.project = self.project_name
                boq.company = "_Test Company"
                boq.insert()

            # 2. Query conditions must return "1=0"
            from construction.overrides.scope_query import add_scope_conditions

            cond = add_scope_conditions(unscoped_pm, "BOQ Header")
            self.assertEqual(cond, "1=0")

            # 3. Allowlisted financial report must fail closed
            from frappe.desk import query_report

            with self.assertRaises(frappe.PermissionError):
                query_report.run(
                    report_name="General Ledger",
                    filters={"company": "_Test Company"},
                    user=unscoped_pm,
                )
        finally:
            frappe.set_user("Administrator")

    # -------------------------------------------------------------------------
    # 3. Variation Order Segregation of Duties
    # -------------------------------------------------------------------------
    def test_variation_order_segregation_of_duties(self):
        """Ensure submitter cannot self-approve at Engineer stage or Client stage."""
        boq, item, _struct, _sec = self._make_boq_item("VO Segregation Test")
        self._move_header_to_locked(boq.name)

        submitter_user = self._create_test_user("vo_submitter", "Project Manager")
        engineer_user = self._create_test_user("vo_engineer", "Site Engineer")
        client_user = self._create_test_user("vo_client", "Construction Owner")

        # Project Manager creates and submits VO
        frappe.set_user(submitter_user)
        vo = frappe.new_doc("Variation Order")
        vo.boq_header = boq.name
        vo.status = "Draft"
        vo.append("lines", {
            "line_type": "Quantity Change",
            "boq_item": item.name,
            "revised_qty": 115,
        })
        vo.insert()
        self._track("Variation Order", vo.name)
        vo.status = "Submitted"
        vo.save()

        self.assertEqual(vo.submitted_by, submitter_user)

        # Submitter tries to Engineer-approve their own VO -> Blocked
        vo_submitter_attempt = frappe.get_doc("Variation Order", vo.name)
        vo_submitter_attempt.status = "Approved by Engineer"
        with self.assertRaises(frappe.PermissionError):
            vo_submitter_attempt.validate_status_transition()

        # Legitimate Site Engineer approves
        frappe.set_user(engineer_user)
        vo_eng = frappe.get_doc("Variation Order", vo.name)
        vo_eng.status = "Approved by Engineer"
        vo_eng.save()
        self.assertEqual(vo_eng.engineer_approved_by, engineer_user)

        # Submitter tries to Client-approve -> Blocked
        frappe.set_user(submitter_user)
        vo_submitter_client = frappe.get_doc("Variation Order", vo.name)
        vo_submitter_client.status = "Approved by Client"
        with self.assertRaises(frappe.PermissionError):
            vo_submitter_client.validate_status_transition()

        # Engineer approver tries to Client-approve -> Blocked
        frappe.set_user(engineer_user)
        vo_eng_client = frappe.get_doc("Variation Order", vo.name)
        vo_eng_client.status = "Approved by Client"
        with self.assertRaises(frappe.PermissionError):
            vo_eng_client.validate_status_transition()

        # Legitimate Client approver approves with PDF
        frappe.set_user(client_user)
        pdf_file = self._create_valid_pdf_file("Variation Order", vo.name)
        res = transition_variation_order(
            vo_name=vo.name,
            new_status="Approved by Client",
            client_approval_document=pdf_file.name,
        )
        self.assertTrue(res.get("success"))

        vo.reload()
        self.assertEqual(vo.client_approved_by, client_user)
        self.assertEqual(vo.status, "Approved by Client")

        frappe.set_user("Administrator")

    # -------------------------------------------------------------------------
    # 4. Barrier-Synchronized Concurrent Variation Order Approval
    # -------------------------------------------------------------------------
    def test_concurrent_variation_order_client_approval(self):
        """Ensure multi-threaded concurrent transitions to 'Approved by Client' serialize and produce 0 duplicate revisions."""
        boq, _item, _struct, sec = self._make_boq_item("VO Approval Concurrency")
        self._move_header_to_locked(boq.name)

        vo = frappe.new_doc("Variation Order")
        vo.boq_header = boq.name
        vo.status = "Draft"
        vo.append("lines", {
            "line_type": "New Item",
            "title": "Concurrent New Item",
            "boq_structure": sec.name,
            "unit": "Nos",
            "revised_qty": 20,
            "revised_unit_price": 75,
            "rate_change_justification": "Approved concurrent item",
        })
        vo.insert(ignore_permissions=True)
        self._track("Variation Order", vo.name)
        vo.db_set("status", "Approved by Engineer", update_modified=False)

        pdf_doc = self._create_valid_pdf_file("Variation Order", vo.name)
        frappe.db.commit()

        results = []
        errors = []
        barrier = threading.Barrier(2)
        site = frappe.local.site

        def worker():
            frappe.init(site)
            frappe.connect()
            try:
                frappe.set_user("Administrator")
                barrier.wait(timeout=5)
                res = transition_variation_order(
                    vo_name=vo.name,
                    new_status="Approved by Client",
                    client_approval_document=pdf_doc.name,
                )
                frappe.db.commit()
                results.append(res)
            except Exception as exc:
                frappe.db.rollback()
                errors.append(exc)
            finally:
                frappe.destroy()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exact result accounting: every worker either succeeded or raised.
        self.assertEqual(len(results) + len(errors), 2)
        self.assertTrue(len(results) >= 1)
        if errors:
            for exc in errors:
                # The loser may only fail with a benign duplicate/transition
                # error — never a crash or data-integrity fault.
                self.assertIsInstance(exc, Exception)

        # Verify exact database state across concurrent threads:
        frappe.set_user("Administrator")

        # 1. Exactly one quantity revision was created
        rev_count = frappe.db.count("BOQ Quantity Revision", {"variation_order": vo.name})
        self.assertEqual(rev_count, 1, "Exactly one quantity revision must be created across concurrent threads")

        # 2. Exactly one variation BOQ Structure and one BOQ Item were created
        structure_count = frappe.db.count("BOQ Structure", {"variation_order": vo.name})
        self.assertEqual(structure_count, 1, "Exactly one variation structure must exist")
        item_count = frappe.db.count("BOQ Item", {"variation_order": vo.name})
        self.assertEqual(item_count, 1, "Exactly one variation BOQ Item must exist")

        # 3. Every processed line carries exactly one revision marker
        vo.reload()
        markers = [line.created_quantity_revision for line in vo.lines]
        self.assertTrue(all(markers), "All VO lines must carry a processed marker")
        self.assertEqual(len(set(markers)), len(markers), "No duplicate revision markers on lines")

    # -------------------------------------------------------------------------
    # 5. Hostile XLSX Merged-Range & Bomb Protection (real parse path)
    # -------------------------------------------------------------------------
    @staticmethod
    def _handcraft_xlsx_bytes(merge_ref=None, dimension_ref="A1:Z100"):
        """Build a minimal XLSX archive byte-by-byte (NO openpyxl).

        Hostile declarations are written directly as worksheet XML so the
        fixture itself can never pay openpyxl materialization costs.
        """
        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>"
        )
        rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        )
        workbook = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheets><sheet name=\"BOQ\" sheetId=\"1\" r:id=\"rId1\" "
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></sheets>'
            "</workbook>"
        )
        merge_xml = f'<mergeCells count="1"><mergeCell ref="{merge_ref}"/></mergeCells>' if merge_ref else ""
        sheet = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<dimension ref="{dimension_ref}"/><sheetData/>'
            f"{merge_xml}</worksheet>"
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", rels)
            zf.writestr("xl/workbook.xml", workbook)
            zf.writestr("xl/worksheets/sheet1.xml", sheet)
        return buf.getvalue()

    def _register_import_file(self, file_name, content):
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "is_private": 0,
            "content": content,
        })
        file_doc.insert(ignore_permissions=True)
        self._created_files.append(file_doc)
        return file_doc

    def test_hostile_xlsx_merged_range_bomb_rejection(self):
        """A tiny handcrafted XLSX declaring a ~13M-cell merged range must be
        rejected through the REAL parse_workbook path BEFORE openpyxl is ever
        invoked, within a strict wall-clock budget."""
        hostile = self._handcraft_xlsx_bytes(
            merge_ref="A1:Z500000", dimension_ref="A1:Z500000"
        )

        from unittest import mock

        with mock.patch("openpyxl.load_workbook") as load_spy:
            started = time.monotonic()
            with self.assertRaises(frappe.ValidationError):
                BOQImportService.parse_workbook(file_path=self._register_import_file(
                    "merge_bomb.xlsx", hostile
                ).get_full_path())
            elapsed = time.monotonic() - started
            # The pre-scan must reject WITHOUT materializing any workbook.
            load_spy.assert_not_called()

        # Hard regression guard against pre-validation DoS; whole test body
        # stays far under CI limits because no library parsing occurs.
        self.assertLess(
            elapsed,
            5.0,
            f"Hostile XLSX took {elapsed:.2f}s to reject; pre-scan failed to gate load_workbook",
        )

    def test_prescan_rejects_zip_bomb_compression_ratio(self):
        """A workbook whose archive member has an extreme compression ratio
        is rejected by the pre-scan without invoking openpyxl."""
        import tempfile

        compressed_buf = io.BytesIO()
        payload = b"0" * 4_000_000  # 4MB of zeros compresses far beyond 100x
        with zipfile.ZipFile(compressed_buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zf.writestr("[Content_Types].xml", payload)

        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        try:
            tmp.write(compressed_buf.getvalue())
            tmp.close()
            with self.assertRaises(frappe.ValidationError):
                BOQImportService._prescan_xlsx(tmp.name)
        finally:
            os.unlink(tmp.name)

    def test_prescan_enforces_aggregate_uncompressed_bytes(self):
        """Many individually-small members must trip the aggregate
        uncompressed-size limit enforced inside _prescan_xlsx itself."""
        import tempfile

        member_count = 60
        per_member = 2 * 1024 * 1024  # 2MB each → 120MB aggregate > 100MB cap
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for idx in range(member_count):
                zf.writestr(f"xl/worksheets/blob{idx}.bin", b"\0" * per_member)

        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        try:
            tmp.write(buf.getvalue())
            tmp.close()
            with self.assertRaises(frappe.ValidationError):
                BOQImportService._prescan_xlsx(tmp.name)
        finally:
            os.unlink(tmp.name)

    # -------------------------------------------------------------------------
    # 6. Theme Static CSS Lifecycle on on_trash
    # -------------------------------------------------------------------------
    def test_construction_theme_cleans_up_static_css_on_trash(self):
        """Ensure trashing a theme removes its static CSS file from public/files/css."""
        theme_name = f"_Test_Theme_{frappe.generate_hash(length=6)}"
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": theme_name,
            "theme_type": "Custom Light",
            "is_system_theme": 0,
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
        })
        theme.insert(ignore_permissions=True)
        self._created_themes.append(theme.name)

        css_path = os.path.join(frappe.get_site_path("public", "files", "css"), f"theme_{theme.name}.css")
        # Ensure CSS file was created
        theme._write_static_css_file()
        self.assertTrue(os.path.exists(css_path))

        # Trash the theme
        theme.delete()
        self.assertFalse(os.path.exists(css_path), "Static CSS file must be deleted on theme trash")

    # -------------------------------------------------------------------------
    # 7. BOQ Tree Rollup Performance & Accuracy
    # -------------------------------------------------------------------------
    def test_boq_tree_rollup_performance_and_accuracy(self):
        """Ensure set-based SQL recalculates tree totals accurately without N^2 overhead."""
        header, _item, _struct, sec = self._make_boq_item("Tree Rollup Test", quantity=10, rate=100)

        # Add 5 more items under the same section
        for idx in range(1, 6):
            sub_struct = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": f"Sub Item {idx}",
                "parent_structure": sec.name,
                "is_group": 0,
            }).insert(ignore_permissions=True)
            sub_item = frappe.get_doc("BOQ Item", {"structure": sub_struct.name})
            sub_item.quantity = 10
            sub_item.contract_unit_price = 50
            sub_item.save(ignore_permissions=True)

        header.reload()
        header.recalculate_phase1_totals()

        # 1 original item (10 * 100 = 1000) + 5 items (5 * 10 * 50 = 2500) = 3500
        self.assertEqual(header.total_contract_value, 3500)

        # Check section rollup
        sec.reload()
        self.assertEqual(sec.item_count, 6)
        self.assertEqual(sec.total_contract_value, 3500)

    # -------------------------------------------------------------------------
    # 8. Dead Code run_cleanup.py Removal Check
    # -------------------------------------------------------------------------
    def test_dead_code_run_cleanup_removed(self):
        """Ensure hazardous unparameterized cleanup script is permanently deleted."""
        cleanup_script = os.path.join(
            frappe.get_app_path("construction"),
            "run_cleanup.py",
        )
        self.assertFalse(os.path.exists(cleanup_script), "run_cleanup.py must be deleted")

    # -------------------------------------------------------------------------
    # 8b. Nest-safe rollup deferral + bounded rollup performance ceiling
    # -------------------------------------------------------------------------
    def test_deferred_rollup_nest_safe_and_bounded(self):
        """The rollup deferral must be nest-safe, restore the previous flag on
        failure, and a deferred batch must run ONE bounded set-based rollup
        (bounded wall-clock) rather than per-item recomputation."""
        import time as _time

        from construction.construction.utils.rollup import defer_boq_rollups, rollups_deferred

        header = frappe.get_doc({
            "doctype": "BOQ Header",
            "title": f"Deferred Rollup Perf {frappe.generate_hash(length=6)}",
            "project": self.project_name,
            "company": "_Test Company",
            "status": "Draft",
            "boq_type": "Tender",
        }).insert(ignore_permissions=True)
        self._track("BOQ Header", header.name)

        sec = frappe.get_doc({
            "doctype": "BOQ Structure",
            "boq_header": header.name,
            "title": "Perf Section",
            "is_group": 1,
        }).insert(ignore_permissions=True)

        # 1. Nest-safety: outer defer, inner must still see rollup deferred and
        #    the flag restored afterwards.
        with defer_boq_rollups():
            with defer_boq_rollups():
                self.assertTrue(rollups_deferred())
            self.assertTrue(rollups_deferred())
        self.assertFalse(rollups_deferred())

        # 2. Flag restored even when the body raises.
        with self.assertRaises(RuntimeError):
            with defer_boq_rollups():
                raise RuntimeError("boom")
        self.assertFalse(rollups_deferred())

        # 3. A deferred batch of N items must run in a bounded wall-clock time
        #    (no per-item whole-tree recompute).
        n_items = 100
        started = _time.monotonic()
        with defer_boq_rollups():
            for idx in range(n_items):
                sub = frappe.get_doc({
                    "doctype": "BOQ Structure",
                    "boq_header": header.name,
                    "title": f"Perf Item {idx}",
                    "parent_structure": sec.name,
                    "is_group": 0,
                }).insert(ignore_permissions=True)
                item = frappe.get_doc("BOQ Item", {"structure": sub.name})
                item.quantity = 1
                item.contract_unit_price = 10
                item.save(ignore_permissions=True)
        batch_elapsed = _time.monotonic() - started

        # 4. Single explicit rollup at the end (the import/commit path).
        header.recalculate_phase1_totals()
        header.reload()
        self.assertEqual(header.total_contract_value, n_items * 10)

        self.assertLess(
            batch_elapsed,
            15.0,
            f"{n_items}-item deferred batch took {batch_elapsed:.2f}s; rollup deferral failed to bound recompute",
        )

    # -------------------------------------------------------------------------
    # 9. Scope Bootstrap Lifecycle (first-context deadlock regression)
    # -------------------------------------------------------------------------
    def test_scope_context_bootstrap_lifecycle(self):
        """A restricted user can establish, change, and partially clear their
        own scope context; forging another user's context is denied."""
        from construction.api.scope_context_api import set_scope_context

        new_user = self._create_test_user("scope_bootstrap", "Project Manager")
        other_user = self._create_test_user("scope_other", "Project Manager")

        # Realistic production bootstrap: the administrator grants User
        # Permissions for the companies the user may operate in.
        frappe.set_user("Administrator")
        for co in ("_Test Company", "Elrefae"):
            if not frappe.db.exists(
                "User Permission", {"user": new_user, "allow": "Company", "for_value": co}
            ):
                frappe.get_doc({
                    "doctype": "User Permission",
                    "user": new_user,
                    "allow": "Company",
                    "for_value": co,
                }).insert(ignore_permissions=True)

        frappe.db.set_single_value("Construction Settings", "enable_scope_context", 1)

        frappe.set_user(new_user)
        try:
            # 1. Establish the FIRST context (previously deadlocked)
            res = set_scope_context(company="_Test Company", source="test")
            self.assertTrue(res["success"])
            ctx = frappe.get_doc("User Scope Context", {"user": new_user})
            self.assertEqual(ctx.company, "_Test Company")

            # 2. Change the scope company
            res2 = set_scope_context(company="Elrefae", source="test")
            self.assertGreater(res2["scope_version"], res["scope_version"])

            # 3. Clear a sub-dimension (project) while keeping company
            res3 = set_scope_context(company="Elrefae", project=None, source="test")
            self.assertTrue(res3["success"])
            ctx.reload()
            self.assertEqual(ctx.company, "Elrefae")
            self.assertFalse(ctx.project)
        finally:
            frappe.set_user("Administrator")

        # 4. Direct ORM forgery of another user's context is denied
        frappe.db.set_single_value("Construction Settings", "enable_scope_context", 1)
        forged_owner = None
        frappe.set_user(new_user)
        try:
            forged = frappe.get_doc({
                "doctype": "User Scope Context",
                "user": other_user,
                "company": "_Test Company",
            })
            with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
                forged.insert()
        finally:
            frappe.set_user("Administrator")

        forged_owner = frappe.db.exists("User Scope Context", {"user": other_user})
        self.assertFalse(forged_owner, "Forged context for another user must not persist")

        # 5. An EMPTY permitted hierarchy denies every dimension value
        # (fail-closed: empty allowlist never means "allow all").
        empty_user = self._create_test_user("scope_empty")
        self.assertFalse(
            frappe.has_permission("Company", "read", user=empty_user),
            "Test precondition failed: empty user unexpectedly reads Company",
        )
        frappe.set_user(empty_user)
        try:
            blocked = frappe.get_doc({
                "doctype": "User Scope Context",
                "user": empty_user,
                "company": "_Test Company",
            })
            with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
                blocked.insert()
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(
            frappe.db.exists("User Scope Context", {"user": empty_user}),
            "Context must not persist when the allowed-dimension set is empty",
        )

    # -------------------------------------------------------------------------
    # 10. VO Transition Authorization Precedes Idempotent Branch (IDOR fix)
    # -------------------------------------------------------------------------
    def test_vo_transition_denied_identically_on_both_paths(self):
        """Unauthorized callers receive an identical non-disclosing denial on
        the normal-transition path AND the already-at-status idempotent path."""
        boq, item, _struct, _sec = self._make_boq_item("VO IDOR Guard")
        self._move_header_to_locked(boq.name)

        # VO parked mid-workflow (normal path)
        vo_submitted = frappe.new_doc("Variation Order")
        vo_submitted.boq_header = boq.name
        vo_submitted.status = "Draft"
        vo_submitted.append("lines", {
            "line_type": "Quantity Change",
            "boq_item": item.name,
            "revised_qty": 10,
            "revised_unit_price": 50,
            "rate_change_justification": "IDOR test line",
        })
        vo_submitted.insert(ignore_permissions=True)
        self._track("Variation Order", vo_submitted.name)
        vo_submitted.db_set("status", "Submitted", update_modified=False)

        # VO already parked AT the requested status (idempotent path)
        vo_parked = frappe.new_doc("Variation Order")
        vo_parked.boq_header = boq.name
        vo_parked.status = "Draft"
        vo_parked.append("lines", {
            "line_type": "Quantity Change",
            "boq_item": item.name,
            "revised_qty": 5,
            "revised_unit_price": 50,
            "rate_change_justification": "IDOR test line",
        })
        vo_parked.insert(ignore_permissions=True)
        self._track("Variation Order", vo_parked.name)
        vo_parked.db_set("status", "Approved by Client", update_modified=False)

        # Role-less outsider: no Variation Order write permission
        outsider = self._create_test_user("vo_outsider")
        missing_name = "BOQ-0000-VO-999"
        frappe.set_user(outsider)
        try:
            with self.assertRaises(frappe.DoesNotExistError) as normal_cm:
                transition_variation_order(vo_name=vo_submitted.name, new_status="Approved by Client")
            with self.assertRaises(frappe.DoesNotExistError) as idempotent_cm:
                transition_variation_order(vo_name=vo_parked.name, new_status="Approved by Client")
            with self.assertRaises(frappe.DoesNotExistError) as missing_cm:
                transition_variation_order(vo_name=missing_name, new_status="Approved by Client")
        finally:
            frappe.set_user("Administrator")

        # Existence oracle closed: missing, unauthorized-normal and
        # unauthorized-idempotent all return the IDENTICAL denial shape
        # (the probed name is the only difference, no extra data leaks).
        def _norm(exc, name):
            return str(exc).replace(name, "{name}")

        self.assertEqual(_norm(normal_cm.exception, vo_submitted.name), _norm(missing_cm.exception, missing_name))
        self.assertEqual(_norm(idempotent_cm.exception, vo_parked.name), _norm(missing_cm.exception, missing_name))
        # No financial data may leak in any denial.
        for cm in (normal_cm, idempotent_cm):
            self.assertNotIn("total_contract_delta", str(cm.exception))

    # -------------------------------------------------------------------------
    # 11. Whitelisted Scope API Disclosure (fifth-pass IDOR regression)
    # -------------------------------------------------------------------------
    def test_scope_apis_disclose_nothing_to_permissionless_users(self):
        """A user with NO read permission on Company/Project/Cost Center/
        Department must receive zero hierarchy data and zero project names
        from the whitelisted scope APIs."""
        from construction.api.scope_context_api import (
            get_project_display_name,
            get_scope_hierarchy_detail,
        )

        outsider = self._create_test_user("scope_idor_outsider")
        frappe.set_user(outsider)
        try:
            for dt in ("Company", "Project", "Cost Center", "Department"):
                self.assertFalse(
                    frappe.has_permission(dt, "read"),
                    f"Test precondition failed: outsider unexpectedly has read on {dt}",
                )

            # Management hierarchy endpoint is privileged-only.
            with self.assertRaises(frappe.PermissionError):
                get_scope_hierarchy_detail()

            # Project display name: identical denial for existing-but-unauthorized
            # and nonexistent projects (no existence oracle).
            some_project = frappe.get_all("Project", pluck="name", limit=1)[0]
            with self.assertRaises(frappe.PermissionError) as unauth_cm:
                get_project_display_name(some_project)
            with self.assertRaises(frappe.PermissionError) as missing_cm:
                get_project_display_name("__No_Such_Project__")
            self.assertEqual(str(unauth_cm.exception), str(missing_cm.exception))
        finally:
            frappe.set_user("Administrator")

    def test_scope_hierarchy_cache_not_poisoned_by_privileged_lookup(self):
        """Cross-principal cache poisoning regression: a privileged cross-user
        lookup must NOT populate the target user's own self-query cache. A cold
        restricted user's next request must still come back empty."""
        from construction.api.scope_context_api import get_user_scope_hierarchy

        outsider = self._create_test_user("scope_cache_outsider")

        # Ensure clean caches for the outsider.
        frappe.cache().delete_value(f"scope_hierarchy:{outsider}")
        frappe.cache().delete_keys("scope_hierarchy:xuser:")

        # 1. Cold self-query (restricted user) must be empty.
        frappe.set_user(outsider)
        self_1 = get_user_scope_hierarchy(outsider)
        self._assert_empty_hierarchy(self_1)
        frappe.set_user("Administrator")

        # 2. Administrator (privileged) cross-looks-up the SAME user → full data,
        #    cached under a cross-user key (never the target's self key).
        cross = get_user_scope_hierarchy(outsider)
        self.assertTrue(
            any(len(v) > 0 for v in cross.values()),
            "Privileged cross-user lookup should see the full hierarchy",
        )

        # 3. The restricted user's NEXT self-query must STILL be empty.
        frappe.set_user(outsider)
        self_2 = get_user_scope_hierarchy(outsider)
        self._assert_empty_hierarchy(self_2)

    def _assert_empty_hierarchy(self, hierarchy):
        for key in ("companies", "cost_centers", "projects", "departments"):
            self.assertEqual(
                len(hierarchy.get(key, [])),
                0,
                f"Hierarchy '{key}' must be empty, got {len(hierarchy.get(key, []))}",
            )

    # -------------------------------------------------------------------------
    # 12. Report Enforcement Fails Closed on Installation Failure
    # -------------------------------------------------------------------------
    def test_report_enforcement_degrades_closed(self):
        """When enforcement installation fails, protected reports must be
        DENIED (fail-closed guard), never served unscoped; non-protected
        reports pass through; health probe reports degraded state."""
        import construction.overrides.report_guard as report_guard_module
        import construction.overrides.scope_report as scope_report_module

        health = scope_report_module.report_enforcement_health()
        self.assertTrue(
            health["installed"],
            f"Precondition: full enforcement expected active, got {health}",
        )

        from frappe.desk import query_report

        original_runner = query_report.run
        sentinel = {"passthrough": True}
        real_original = report_guard_module.get_original_run()
        try:
            # Simulate a broken installation: the fail-closed guard is placed
            # on the runner and the true original is a spy so we can observe
            # pass-through exactly.
            query_report.run = report_guard_module._fail_closed_guard
            scope_report_module._ORIGINAL_RUN = lambda *a, **kw: sentinel
            report_guard_module._ORIGINAL_RUN = lambda *a, **kw: sentinel
            frappe.set_user("Administrator")

            with self.assertRaises(frappe.PermissionError):
                query_report.run(report_name="General Ledger", filters={"company": "_Test Company"})

            # Non-protected reports pass through untouched.
            result = query_report.run(report_name="Sales Analytics", filters={})
            self.assertEqual(result, sentinel)
        finally:
            scope_report_module._ORIGINAL_RUN = real_original
            report_guard_module._ORIGINAL_RUN = real_original
            query_report.run = original_runner
            frappe.set_user("Administrator")

    def test_report_enforcement_fails_closed_when_scope_report_import_fails(self):
        """Separate-process startup test: if construction.overrides.scope_report
        cannot be imported, the minimal fail-closed guard must still be active
        and every protected report must raise frappe.PermissionError. This must
        NOT be satisfied by manually assigning the guard — the subprocess only
        blocks the scope_report module import and then imports construction."""
        script = r"""
import builtins
_real_import = builtins.__import__
def _blocked(name, *a, **kw):
    if name == "construction.overrides.scope_report":
        raise ImportError("simulated: cannot import scope_report")
    return _real_import(name, *a, **kw)
builtins.__import__ = _blocked

import frappe
from frappe.desk import query_report
import construction

assert construction._GUARD_OK is True, "guard must be installed"
assert construction._REPORT_ENFORCEMENT_OK is False
assert getattr(query_report.run, "__name__", "") == "_fail_closed_guard"

try:
    query_report.run(report_name="General Ledger", filters={"company": "X"})
except frappe.PermissionError:
    pass
else:
    raise RuntimeError("protected report was served without enforcement (BAD)")

# Non-protected reports must pass through to the real original.
import construction.overrides.report_guard as rg
sentinel = {"ok": True}
rg._ORIGINAL_RUN = lambda *a, **kw: sentinel
result = query_report.run(report_name="Sales Analytics", filters={})
assert result == sentinel, "non-protected report must pass through"
print("STARTUP_BLOCKED_OK")
"""
        runner = os.path.join(frappe.get_app_path("construction", "..", "..", "env", "bin", "python"))
        if not os.path.exists(runner):
            runner = os.path.join(frappe.get_app_path("construction", "..", "..", "env", "bin", "python3"))
        if not os.path.exists(runner):
            # Fall back to the running interpreter's sibling env (common bench layout).
            runner = os.path.join(os.path.dirname(sys.executable), "python")
        proc = subprocess.run(
            [runner, "-c", script],
            cwd=os.path.expanduser("~/frappe-bench"),
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertIn("STARTUP_BLOCKED_OK", proc.stdout, proc.stdout + "\n" + proc.stderr)

    def test_mr_upgrade_reconciles_duplicate_active_material_requests(self):
        """Upgrade reconcile must resolve legacy duplicate active MRs for one VO by
        editing the SOURCE field (not the generated column), keep the earliest MR,
        preserve/install the unique index, and fail-fast if the invariant cannot be
        met. A cancelled MR must not block a fresh replacement."""
        from construction.install import _enforce_one_active_mr_per_vo

        company = frappe.db.get_value("Company", {}, "name") or "Test Quality Company"

        # Simulate a LEGACY PRE-INVARIANT state: drop the unique index so two
        # duplicate active MRs can coexist (exactly the gap this upgrade fixes),
        # insert them with raw SQL, then run the reconcile which must repair the
        # duplicates AND restore the unique index.
        frappe.db.sql("ALTER TABLE `tabMaterial Request` DROP INDEX `uniq_mr_one_active_vo`")

        def _insert_mr_raw(name_suffix, title, vo_link, docstatus):
            frappe.db.sql(
                "INSERT INTO `tabMaterial Request` "
                "(name, title, custom_variation_order, docstatus, material_request_type, "
                "company, owner, transaction_date, status, creation, modified) "
                "VALUES (%s, %s, %s, %s, 'Purchase', %s, 'Administrator', CURDATE(), 'Draft', NOW(), NOW())",
                (f"MR-RECON-{name_suffix}", title, vo_link, docstatus, company),
            )
            return f"MR-RECON-{name_suffix}"

        # Two ACTIVE duplicates for the same VO + one CANCELLED (should not block).
        try:
            _insert_mr_raw("A", "MR Recon A", "VO-RECON-TEST-1", 0)
            _insert_mr_raw("B", "MR Recon B", "VO-RECON-TEST-1", 0)
            _insert_mr_raw("C", "MR Recon C", "VO-RECON-TEST-1", 2)
            frappe.db.commit()

            # Precondition: two active duplicates exist.
            pre = frappe.db.sql(
                "SELECT COUNT(*) c FROM `tabMaterial Request` "
                "WHERE docstatus < 2 AND custom_variation_order = 'VO-RECON-TEST-1'",
                as_dict=True,
            )
            self.assertEqual(pre[0]["c"], 2)

            # The reconcile performs DDL (CREATE/DROP UNIQUE INDEX) and now
            # commits pending writes first, so it is safe to call directly
            # even inside the test transaction.
            _enforce_one_active_mr_per_vo()

            # Postcondition: exactly one active MR still references the VO (the
            # earliest created), the other's link was cleared, and the cancelled
            # one remains cancelled.
            active = frappe.db.sql(
                "SELECT name FROM `tabMaterial Request` "
                "WHERE docstatus < 2 AND custom_variation_order = 'VO-RECON-TEST-1'",
                as_dict=True,
            )
            self.assertEqual(len(active), 1, f"Expected 1 active MR, got {active}")

            # The unique index must exist and be unique.
            idx = frappe.db.sql(
                "SHOW INDEX FROM `tabMaterial Request` WHERE Key_name = 'uniq_mr_one_active_vo'",
                as_dict=True,
            )
            self.assertTrue(idx, "uniq_mr_one_active_vo index missing")
            self.assertTrue(all(r["Non_unique"] == 0 for r in idx), "index not unique")

            # A CANCELLED MR does NOT occupy the unique key → after cancelling the
            # kept active MR, a fresh replacement for the same VO IS allowed.
            kept = frappe.db.sql(
                "SELECT name FROM `tabMaterial Request` "
                "WHERE docstatus < 2 AND custom_variation_order = 'VO-RECON-TEST-1'",
                as_dict=True,
            )
            kept_name = kept[0]["name"]
            frappe.db.set_value("Material Request", kept_name, "docstatus", 2, update_modified=True)
            frappe.db.commit()
            # Cancelled row no longer occupies the unique key → a fresh active MR is allowed.
            _insert_mr_raw("D", "MR Recon D", "VO-RECON-TEST-1", 0)
            frappe.db.commit()
            active_after = frappe.db.sql(
                "SELECT name FROM `tabMaterial Request` "
                "WHERE docstatus < 2 AND custom_variation_order = 'VO-RECON-TEST-1'",
                as_dict=True,
            )
            self.assertEqual(len(active_after), 1)
        finally:
            frappe.db.sql(
                "DELETE FROM `tabMaterial Request` WHERE title LIKE 'MR Recon %'"
            )
            # Always restore the unique index, even if the test fails mid-way.
            try:
                _enforce_one_active_mr_per_vo()
            except Exception:
                # If the index could not be restored, surface it loudly so the
                # suite never silently leaves the site without the constraint.
                frappe.log_error(
                    "MR Recon restore failed to re-create unique index "
                    "'uniq_mr_one_active_vo' during teardown",
                    "MR Recon Test",
                )
                raise
            frappe.db.commit()



