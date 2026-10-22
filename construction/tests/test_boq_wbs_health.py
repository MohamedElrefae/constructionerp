import frappe
from frappe.tests.utils import FrappeTestCase

from construction.services.boq_wbs_health import run_wbs_health_check
from construction.tests.test_boq_helpers import get_or_create_test_project


class TestBOQWBSHealth(FrappeTestCase):
    def setUp(self):
        self.header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": "Test WBS Health",
                "project": get_or_create_test_project(),
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)

        self.root = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.header.name,
                "title": "Root",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)

        self.leaf = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.header.name,
                "title": "Leaf",
                "parent_structure": self.root.name,
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)

        self.item_name = frappe.db.get_value("BOQ Item", {"structure": self.leaf.name}, "name")

    def tearDown(self):
        frappe.db.rollback()

    def _issue_types(self):
        report = run_wbs_health_check(self.header.name)
        return {issue["issue_type"] for issue in report["issues"]}

    def test_valid_tree_is_healthy(self):
        report = run_wbs_health_check(self.header.name)

        self.assertTrue(report["healthy"])
        self.assertEqual(report["summary"]["issue_count"], 0)
        self.assertEqual(report["summary"]["structures_checked"], 2)
        self.assertEqual(report["summary"]["items_checked"], 1)

    def test_blank_wbs_is_reported(self):
        other = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.header.name,
                "title": "Other Root",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)

        frappe.db.set_value("BOQ Structure", self.leaf.name, "wbs_code", "")

        issue_types = self._issue_types()

        self.assertIn("blank_wbs_code", issue_types)

    def test_broken_parent_and_nested_set_bounds_are_reported(self):
        frappe.db.set_value("BOQ Structure", self.leaf.name, "parent_structure", "missing-parent")
        frappe.db.set_value("BOQ Structure", self.root.name, {"lft": 10, "rgt": 9})

        issue_types = self._issue_types()

        self.assertIn("missing_parent_structure", issue_types)
        self.assertIn("invalid_nested_set_bounds", issue_types)

    def test_leaf_parent_and_parent_bounds_mismatch_are_reported(self):
        child = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.header.name,
                "title": "Child Under Leaf",
                "parent_structure": self.root.name,
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)

        frappe.db.set_value("BOQ Structure", child.name, "parent_structure", self.leaf.name)
        frappe.db.set_value("BOQ Structure", child.name, {"lft": 100, "rgt": 101})

        issue_types = self._issue_types()

        self.assertIn("leaf_used_as_parent", issue_types)
        self.assertIn("nested_set_parent_bounds_mismatch", issue_types)

    def test_boq_item_structure_issues_are_reported(self):
        frappe.db.set_value("BOQ Item", self.item_name, "structure", "missing-structure")

        issue_types = self._issue_types()

        self.assertIn("boq_item_missing_structure", issue_types)
        self.assertIn("leaf_structure_missing_boq_item", issue_types)

    def test_boq_item_header_mismatch_and_group_link_are_reported(self):
        other_header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": "Other WBS Health",
                "project": get_or_create_test_project("_Test Construction BOQ Other Project"),
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)

        frappe.db.set_value(
            "BOQ Item",
            self.item_name,
            {
                "boq_header": other_header.name,
                "structure": self.root.name,
            },
        )

        report = run_wbs_health_check()
        issue_types = {issue["issue_type"] for issue in report["issues"]}

        self.assertIn("boq_item_header_mismatch", issue_types)
        self.assertIn("boq_item_linked_to_group_structure", issue_types)
