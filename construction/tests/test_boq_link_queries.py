import frappe
from frappe.tests.utils import FrappeTestCase

from construction.api.boq_link_queries import (
    get_boq_headers,
    get_boq_item_stages,
    get_boq_items,
    get_boq_scope_token,
    get_boq_structures,
)
from construction.services.scope_resolution import get_scope_token


class TestBOQLinkQueries(FrappeTestCase):
    def setUp(self):
        self._clear_scope_defaults()
        self.company = frappe.db.get_value("Company", {}, "name") or self._make_company()
        self.previous_mode = frappe.db.get_single_value(
            "Construction Settings", "enable_boq_cascade_filtering"
        )
        frappe.db.set_single_value("Construction Settings", "enable_boq_cascade_filtering", "On")
        frappe.db.delete("User Scope Context", {"user": "Administrator"})

        self.project_a = self._make_project("_Test BOQ Scope A")
        self.project_b = self._make_project("_Test BOQ Scope B")
        self.header_a = self._make_header(self.project_a, "_Test Scoped BOQ A", "Draft")
        self.header_b = self._make_header(self.project_b, "_Test Scoped BOQ B", "Draft")
        self.draft_header = self._make_header(self.project_a, "_Test Draft BOQ", "Draft")
        self.structure_a, self.item_a = self._make_leaf_item(self.header_a.name, "_Test Leaf A")
        self.structure_b, self.item_b = self._make_leaf_item(self.header_b.name, "_Test Leaf B")
        self._set_header_status(self.header_a, "Frozen")
        self._set_header_status(self.header_b, "Frozen")

        self._set_scope(project=self.project_a)

    def tearDown(self):
        frappe.db.rollback()
        frappe.db.set_single_value(
            "Construction Settings", "enable_boq_cascade_filtering", self.previous_mode or "Off"
        )

    def _make_company(self):
        return (
            frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": "_Test BOQ Scope Company",
                    "abbr": "TBSC",
                    "default_currency": "USD",
                    "country": "United States",
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _clear_scope_defaults(self):
        for key in ("branch", "company", "cost_center", "project", "department"):
            frappe.defaults.clear_user_default(key, "Administrator")

    def _make_project(self, project_name):
        name = frappe.db.get_value("Project", {"project_name": project_name}, "name")
        if name:
            return name
        return (
            frappe.get_doc(
                {
                    "doctype": "Project",
                    "project_name": project_name,
                    "company": self.company,
                    "naming_series": "PROJ-.####",
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _make_header(self, project, title, status):
        return frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "project": project,
                "title": title,
                "status": status,
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)

    def _set_header_status(self, header, status):
        if status == "Frozen":
            header.status = "Pricing"
            header.save(ignore_permissions=True)
        header.status = status
        header.save(ignore_permissions=True)

    def _make_leaf_item(self, header, title):
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header,
                "title": title,
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        item_name = frappe.db.get_value("BOQ Item", {"structure": structure.name}, "name")
        return structure, frappe.get_doc("BOQ Item", item_name)

    def _set_scope(self, project=None, cost_center=None):
        frappe.get_doc(
            {
                "doctype": "User Scope Context",
                "user": "Administrator",
                "company": self.company,
                "cost_center": cost_center,
                "project": project,
            }
        ).insert(ignore_permissions=True)

    def test_scope_token_endpoint_matches_service_token(self):
        payload = get_boq_scope_token()
        self.assertEqual(payload["scope_token"], get_scope_token("Administrator"))
        self.assertEqual(payload["scope"]["project"], self.project_a)
        self.assertEqual(payload["scope"]["scope_type"], "Project-Scoped")

    def test_boq_header_query_enforces_project_scope_and_allowed_status(self):
        rows = get_boq_headers("BOQ Header", "_Test", "name", 0, 20, {}, enforce_scope=True)
        names = {row[0] for row in rows}
        self.assertIn(self.header_a.name, names)
        self.assertNotIn(self.header_b.name, names)
        self.assertNotIn(self.draft_header.name, names)

    def test_boq_structure_and_item_queries_follow_scope_chain(self):
        structures = get_boq_structures("BOQ Structure", "_Test", "name", 0, 20, {}, enforce_scope=True)
        structure_names = {row[0] for row in structures}
        self.assertIn(self.structure_a.name, structure_names)
        self.assertNotIn(self.structure_b.name, structure_names)

        items = get_boq_items("BOQ Item", "", "name", 0, 20, {}, enforce_scope=True)
        item_names = {row[0] for row in items}
        self.assertIn(self.item_a.name, item_names)
        self.assertNotIn(self.item_b.name, item_names)

    def test_closed_row_gate_returns_no_boq_dropdown_options(self):
        closed_gate = {"require_gate": 1, "gate_open": 0}

        self.assertEqual(
            get_boq_headers("BOQ Header", "_Test", "name", 0, 20, closed_gate, enforce_scope=True),
            [],
        )
        self.assertEqual(
            get_boq_structures("BOQ Structure", "_Test", "name", 0, 20, closed_gate, enforce_scope=True),
            [],
        )
        self.assertEqual(
            get_boq_items("BOQ Item", "", "name", 0, 20, closed_gate, enforce_scope=True),
            [],
        )
        self.assertEqual(
            get_boq_item_stages("BOQ Item Stage", "", "name", 0, 20, closed_gate, enforce_scope=True),
            [],
        )
