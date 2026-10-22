"""Portable regression coverage for the resource_requirements adapter.

Authorization must be resolved BEFORE aggregation because the service groups
by stream/item_code/uom and has no single boq_item identity. Fixtures are
created in setUp and removed in tearDown; an ordinary (non-Administrator)
caller exercises the adapter; cleanup is ordered and reports failures.
"""

import json
import unittest
import uuid
from pathlib import Path
from unittest import mock

import frappe

from construction.api.construction_reports import report_export, report_view
from construction.services import boq_report_service as svc


class TestResourceRequirementAuthorization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._class_previous_user = frappe.session.user
        frappe.set_user("Administrator")
        frappe.local._boq_perm_scope_dims = {}
        frappe.local.request_cache.clear()
        cls._class_owned = []
        cls._created_company = None

        if not frappe.db.exists("UOM", "Nos"):
            frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert()
            cls._class_owned.append(("UOM", "Nos"))
            frappe.db.commit()

        item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        if not item_group:
            ig = frappe.get_doc(
                {"doctype": "Item Group", "item_group_name": "RR Auth Group", "is_group": 0}
            ).insert()
            cls._class_owned.append(("Item Group", ig.name))
            item_group = ig.name
            frappe.db.commit()
        cls._item_group = item_group

        companies = frappe.get_all("Company", pluck="name")
        if len(companies) < 2:
            from erpnext.accounts.test.accounts_mixin import AccountsMixin

            mixin = AccountsMixin()
            mixin.create_company(company_name="_RR Auth Co 2", abbr="_R2")
            frappe.db.commit()
            cls._created_company = "_RR Auth Co 2"
            companies = frappe.get_all("Company", pluck="name")
        cls._companies = companies

        items = frappe.get_all("Item", pluck="name")
        if not items:
            it = frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": "RR Auth Item " + uuid.uuid4().hex[:6],
                    "item_name": "RR Auth Item",
                    "item_group": cls._item_group,
                    "stock_uom": "Nos",
                }
            ).insert()
            cls._class_owned.append(("Item", it.name))
            items = [it.name]
            frappe.db.commit()
        cls._resource_item = items[0]

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        errors = []
        for dt, name in reversed(cls._class_owned):
            try:
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
            except Exception as e:
                errors.append((dt, name, "delete", str(e)))
        if cls._created_company and frappe.db.exists("Company", cls._created_company):
            try:
                frappe.delete_doc("Company", cls._created_company, force=True, ignore_permissions=True)
            except Exception as e:
                errors.append(("Company", cls._created_company, "delete", str(e)))
        try:
            frappe.db.commit()
        except Exception as e:
            errors.append(("db", "commit", "commit", str(e)))
        try:
            frappe.set_user(cls._class_previous_user)
        except Exception as e:
            errors.append(("session", "restore", "set_user", str(e)))
        frappe.local.request_cache.clear()
        frappe.local._boq_perm_scope_dims = {}
        if errors:
            raise AssertionError("class teardown failures: " + repr(errors))

    def setUp(self):
        # Guarded initialized state so cleanup never raises AttributeError.
        self.previous_user = frappe.session.user
        self.paths = []
        self.owned = []  # list of (doctype, name) in creation order
        self.reader = None
        self.cleanup_errors = []
        self.addCleanup(self.cleanup)

        frappe.set_user("Administrator")
        frappe.local._boq_perm_scope_dims = {}
        frappe.local.request_cache.clear()

        companies = self.__class__._companies
        self.assertGreaterEqual(len(companies), 2, "need at least two companies")
        self.company = companies[0]
        self.other_company = companies[1]
        self.resource_item = self.__class__._resource_item

        # ordinary caller
        self.reader = "rr-auth-reader-" + uuid.uuid4().hex[:8] + "@qualification.invalid"
        u = frappe.get_doc(
            {
                "doctype": "User",
                "email": self.reader,
                "first_name": "RR Auth Reader",
                "send_welcome_email": 0,
                "roles": [{"role": "Site Engineer"}, {"role": "Projects User"}],
            }
        ).insert()
        self.owned.append(("User", u.name))
        up = frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": self.reader,
                "allow": "Company",
                "for_value": self.company,
                "apply_to_all_doctypes": 1,
            }
        ).insert()
        self.owned.append(("User Permission", up.name))
        sc = frappe.get_doc(
            {"doctype": "User Scope Context", "user": self.reader, "company": self.company}
        ).insert()
        self.owned.append(("User Scope Context", sc.name))

        # project + boq header under self.company
        self.project = frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": "RR Auth Project " + uuid.uuid4().hex[:6],
                "company": self.company,
                "naming_series": "PROJ-.YYYY.-",
            }
        ).insert()
        self.owned.append(("Project", self.project.name))

        self.header = frappe.get_doc(
            {"doctype": "BOQ Header", "project": self.project.name, "status": "Draft"}
        ).insert()
        self.owned.append(("BOQ Header", self.header.name))
        frappe.db.set_value("BOQ Header", self.header.name, "project", self.project.name)

        # foreign header under other_company
        self.other_project = frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": "RR Auth Other " + uuid.uuid4().hex[:6],
                "company": self.other_company,
                "naming_series": "PROJ-.YYYY.-",
            }
        ).insert()
        self.owned.append(("Project", self.other_project.name))
        self.other_header = frappe.get_doc(
            {"doctype": "BOQ Header", "project": self.other_project.name, "status": "Draft"}
        ).insert()
        self.owned.append(("BOQ Header", self.other_header.name))
        frappe.db.set_value("BOQ Header", self.other_header.name, "project", self.other_project.name)

        # structure group + two leaves
        self.group = frappe.get_doc(
            {"doctype": "BOQ Structure", "boq_header": self.header.name, "title": "G", "is_group": 1}
        ).insert()
        self.owned.append(("BOQ Structure", self.group.name))
        self.leaf_a = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.header.name,
                "title": "L1",
                "is_group": 0,
                "parent_structure": self.group.name,
            }
        ).insert()
        self.owned.append(("BOQ Structure", self.leaf_a.name))
        self.leaf_b = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.header.name,
                "title": "L2",
                "is_group": 0,
                "parent_structure": self.group.name,
            }
        ).insert()
        self.owned.append(("BOQ Structure", self.leaf_b.name))

        self.item_a = frappe.get_all("BOQ Item", filters={"structure": self.leaf_a.name}, pluck="name")[0]
        self.item_b = frappe.get_all("BOQ Item", filters={"structure": self.leaf_b.name}, pluck="name")[0]
        for it in (self.item_a, self.item_b):
            frappe.db.set_value("BOQ Item", it, {"quantity": 1, "factor": 1, "contract_unit_price": 100})

        def make_analysis(boq_item, qty, detail_qty, rate):
            a = frappe.get_doc(
                {
                    "doctype": "BOQ Cost Analysis",
                    "title": "RR Auth " + boq_item,
                    "boq_item": boq_item,
                    "company": self.company,
                    "analysis_status": "Draft",
                    "analysis_uom": "Nos",
                    "analysis_qty": qty,
                    "currency": frappe.db.get_value("Company", self.company, "default_currency") or "USD",
                    "overhead_pct": 0,
                    "profit_pct": 0,
                    "details": [
                        {
                            "cost_stream": "M",
                            "item_code": self.resource_item,
                            "resource_uom": "Nos",
                            "qty_per_boq_unit": detail_qty,
                            "cost_rate": rate,
                            "wastage_pct": 0,
                        }
                    ],
                }
            )
            a.insert()
            self.owned.append(("BOQ Cost Analysis", a.name))
            a.submit()
            a.reload()
            return a

        self.analysis_a = make_analysis(self.item_a, 1, 10, 5)
        self.analysis_b = make_analysis(self.item_b, 1, 20, 5)
        frappe.db.commit()
        self._setup_ok = True

    def cleanup(self):
        frappe.set_user("Administrator")
        errors = []
        # cancel analyses first
        for dt, name in reversed(self.owned):
            if dt == "BOQ Cost Analysis" and name:
                try:
                    doc = frappe.get_doc(dt, name)
                    if doc.docstatus == 1:
                        doc.cancel()
                except Exception as e:
                    errors.append((dt, name, "cancel", str(e)))
        for dt, name in reversed(self.owned):
            if name is None:
                continue
            try:
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
            except Exception as e:
                errors.append((dt, name, "delete", str(e)))
        # user (tracked in owned already as User)
        try:
            frappe.db.commit()
        except Exception as e:
            errors.append(("db", "commit", "commit", str(e)))
        frappe.local.request_cache.clear()
        frappe.local._boq_perm_scope_dims = {}
        try:
            frappe.set_user(self.previous_user)
        except Exception as e:
            errors.append(("session", "restore", "set_user", str(e)))
        for path in getattr(self, "paths", []):
            try:
                path.unlink(missing_ok=True)
            except Exception as e:
                errors.append(("File", str(path), "unlink", str(e)))
        # track File docs created by export (best-effort, recorded not ignored)
        if errors:
            raise AssertionError("cleanup failures: " + repr(errors))

    # --- service level ---

    def test_populated_authorized_totals(self):
        rows = svc.get_resource_requirement_summary(
            self.header.name, authorized_items=[self.item_a, self.item_b]
        )
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["total_resource_qty"], 30.0)
        self.assertAlmostEqual(rows[0]["total_resource_cost"], 150.0)
        self.assertAlmostEqual(rows[0]["avg_cost_rate"], 150.0 / 30.0, places=6)

    def test_partial_authorization_excludes_hidden_contribution(self):
        rows = svc.get_resource_requirement_summary(self.header.name, authorized_items=[self.item_a])
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["total_resource_qty"], 10.0)
        self.assertAlmostEqual(rows[0]["total_resource_cost"], 50.0)

    def test_all_denied_returns_no_data(self):
        rows = svc.get_resource_requirement_summary(self.header.name, authorized_items=[])
        self.assertEqual(rows, [])

    def test_trusted_internal_caller_preserves_legacy_behaviour(self):
        rows = svc.get_resource_requirement_summary(self.header.name, authorized_items=None)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["total_resource_qty"], 30.0)

    def test_hidden_invalid_analysis_qty_does_not_break_visible_aggregate(self):
        frappe.set_user("Administrator")
        frappe.db.set_value("BOQ Cost Analysis", self.analysis_b.name, "analysis_qty", 0)
        frappe.db.commit()
        try:
            rows = svc.get_resource_requirement_summary(self.header.name, authorized_items=[self.item_a])
            self.assertEqual(len(rows), 1)
            self.assertAlmostEqual(rows[0]["total_resource_qty"], 10.0)
        finally:
            frappe.db.set_value("BOQ Cost Analysis", self.analysis_b.name, "analysis_qty", 1)
            frappe.db.commit()

    def test_hidden_invalid_factor_does_not_break_visible_aggregate(self):
        frappe.set_user("Administrator")
        orig = frappe.db.get_value("BOQ Item", self.item_b, "factor")
        frappe.db.set_value("BOQ Item", self.item_b, "factor", 0)
        frappe.db.commit()
        try:
            rows = svc.get_resource_requirement_summary(self.header.name, authorized_items=[self.item_a])
            self.assertEqual(len(rows), 1)
            self.assertAlmostEqual(rows[0]["total_resource_qty"], 10.0)
        finally:
            frappe.db.set_value("BOQ Item", self.item_b, "factor", orig)
            frappe.db.commit()

    def test_visible_invalid_factor_is_refused(self):
        frappe.set_user("Administrator")
        orig = frappe.db.get_value("BOQ Item", self.item_a, "factor")
        frappe.db.set_value("BOQ Item", self.item_a, "factor", 0)
        frappe.db.commit()
        try:
            with self.assertRaises(frappe.ValidationError):
                svc.get_resource_requirement_summary(self.header.name, authorized_items=[self.item_a])
        finally:
            frappe.db.set_value("BOQ Item", self.item_a, "factor", orig)
            frappe.db.commit()

    # --- adapter level (ordinary caller) ---

    def test_fixture_native_company_read(self):
        frappe.set_user(self.reader)
        frappe.local._boq_perm_scope_dims = {}
        frappe.local.request_cache.clear()
        self.assertTrue(
            frappe.has_permission("Company", "read", doc=self.company),
            "ordinary reader must have native Company read on the allowed company",
        )
        self.assertTrue(
            frappe.has_permission("BOQ Header", "read", doc=self.header.name),
            "ordinary reader must read the in-scope header",
        )
        for it in (self.item_a, self.item_b):
            self.assertTrue(
                frappe.has_permission("BOQ Item", "read", doc=it),
                "ordinary reader must read in-scope BOQ items",
            )

    def test_adapter_positive_control_ordinary_user(self):
        frappe.set_user(self.reader)
        frappe.local._boq_perm_scope_dims = {}
        frappe.local.request_cache.clear()
        data = report_view("resource_requirements", company=self.company, boq_header=self.header.name)
        self.assertEqual(data["row_count"], 1)
        self.assertAlmostEqual(data["rows"][0]["total_resource_qty"], 30.0)

    def test_adapter_passes_empty_list_not_none_for_missing_header(self):
        import construction.api.construction_reports as adapter

        captured = {}

        def fake_summary(boq_header, authorized_items=None):
            captured["authorized_items"] = authorized_items
            return []

        with mock.patch(
            "construction.services.boq_report_service.get_resource_requirement_summary",
            fake_summary,
        ):
            frappe.set_user(self.reader)
            frappe.local._boq_perm_scope_dims = {}
            frappe.local.request_cache.clear()
            data = report_view("resource_requirements", company=self.company)
        self.assertEqual(data["row_count"], 0)
        self.assertIn("authorized_items", captured)
        self.assertEqual(captured["authorized_items"], [])

    def test_foreign_company_denied(self):
        frappe.set_user(self.reader)
        with self.assertRaises(frappe.PermissionError):
            report_view(
                "resource_requirements",
                company=self.other_company,
                boq_header=self.header.name,
            )

    def test_foreign_header_denied(self):
        frappe.set_user(self.reader)
        with self.assertRaises(frappe.PermissionError):
            report_view(
                "resource_requirements",
                company=self.company,
                boq_header=self.other_header.name,
            )

    def test_missing_header_returns_no_rows_without_unrestricted_mode(self):
        frappe.set_user(self.reader)
        frappe.local._boq_perm_scope_dims = {}
        frappe.local.request_cache.clear()
        data = report_view("resource_requirements", company=self.company)
        self.assertEqual(data["row_count"], 0)
        self.assertEqual(data["rows"], [])

    def test_adapter_partial_denial_ordinary_user(self):
        import construction.api.construction_reports as adapter

        orig = adapter._readable_item

        def readable_only_a(name):
            return name == self.item_a

        adapter._readable_item = readable_only_a
        try:
            frappe.set_user(self.reader)
            frappe.local._boq_perm_scope_dims = {}
            frappe.local.request_cache.clear()
            data = report_view("resource_requirements", company=self.company, boq_header=self.header.name)
            self.assertEqual(data["row_count"], 1)
            self.assertAlmostEqual(data["rows"][0]["total_resource_qty"], 10.0)
            self.assertAlmostEqual(data["rows"][0]["total_resource_cost"], 50.0)
        finally:
            adapter._readable_item = orig

    # --- export parity (ordinary permitted caller) ---

    def test_export_parity_ordinary_user(self):
        frappe.set_user(self.reader)
        frappe.local._boq_perm_scope_dims = {}
        frappe.local.request_cache.clear()
        result = report_export("resource_requirements", company=self.company, boq_header=self.header.name)
        self.assertEqual(result["row_count"], 1)
        name = result["file_name"]
        path = Path(frappe.get_site_path("private", "files", name))
        self.paths.append(path)
        # Track the File doc for explicit cleanup.
        file_doc_name = frappe.db.get_value("File", {"file_name": name}, "name")
        if file_doc_name:
            self.owned.append(("File", file_doc_name))
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["report"], "resource_requirements")
        self.assertEqual(len(payload["rows"]), 1)
        self.assertAlmostEqual(payload["rows"][0]["total_resource_qty"], 30.0)
        self.assertAlmostEqual(payload["rows"][0]["total_resource_cost"], 150.0)


if __name__ == "__main__":
    unittest.main()
