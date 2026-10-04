import frappe
from frappe.tests.utils import FrappeTestCase

from construction.services.boq_rollup_audit import audit_boq_rollups
from construction.tests.test_boq_helpers import get_or_create_test_project


class TestBOQRollupAudit(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.delete("User Scope Context", {"user": "Administrator"})
        self.header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": "Rollup audit fixture",
                "project": get_or_create_test_project(),
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        self.group = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.header.name,
                "title": "Audit group",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)

        unit = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
        self.items = []
        self.structures = []
        for index, (quantity, contract_rate, unit_cost, factor) in enumerate(
            ((2, 50, 20, 1.5), (4, 30, 10, 2)), start=1
        ):
            structure = frappe.get_doc(
                {
                    "doctype": "BOQ Structure",
                    "boq_header": self.header.name,
                    "parent_structure": self.group.name,
                    "title": f"Audit line {index}",
                    "is_group": 0,
                }
            ).insert(ignore_permissions=True)
            item = frappe.get_doc("BOQ Item", {"structure": structure.name})
            item.quantity = quantity
            item.unit = unit
            item.contract_unit_price = contract_rate
            item.est_unit_cost = unit_cost
            item.factor = factor
            item.save(ignore_permissions=True)
            frappe.db.set_value(
                "BOQ Item",
                item.name,
                {"current_revised_qty": quantity, "current_revised_unit_price": contract_rate},
                update_modified=False,
            )
            self.structures.append(structure)
            self.items.append(item)

        # These fixtures model a BOQ with an initialized current projection;
        # new items otherwise retain the DocType's zero defaults for revisions.
        self.header.recalculate_phase1_totals()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def _stored_snapshot(self):
        header = frappe.db.sql(
            """
            SELECT total_contract_value, total_estimated_value,
                   total_budgeted_cost, total_revised_value
            FROM `tabBOQ Header` WHERE name = %s
            """,
            (self.header.name,),
        )[0]
        structures = frappe.db.sql(
            """
            SELECT name, item_count, total_contract_value, total_budgeted_cost
            FROM `tabBOQ Structure`
            WHERE boq_header = %s AND docstatus < 2
            ORDER BY lft, name
            """,
            (self.header.name,),
        )
        return header, structures

    def test_consistent_two_line_rollups_have_no_mismatches(self):
        result = audit_boq_rollups(self.header.name)

        self.assertEqual(
            result["header"]["computed"],
            {
                "total_contract_value": 390,
                "total_estimated_value": 140,
                "total_budgeted_cost": 140,
                "total_revised_value": 390,
            },
        )
        self.assertEqual(result["header"]["mismatched_fields"], [])
        group_result = next(row for row in result["structures"] if row["name"] == self.group.name)
        self.assertEqual(
            group_result["computed"],
            {
                "item_count": 2,
                "total_contract_value": 390,
                "total_budgeted_cost": 140,
            },
        )
        self.assertEqual(group_result["mismatched_fields"], [])
        self.assertIn("do not filter item docstatus", result["aggregation_limit"])
        self.assertIn("include variation items", result["aggregation_limit"])

    def test_audit_detects_legacy_drift_and_does_not_repair_it(self):
        first, second = self.items
        frappe.db.set_value(
            "BOQ Item",
            first.name,
            {"current_revised_qty": 3, "current_revised_unit_price": 60},
            update_modified=False,
        )
        frappe.db.set_value(
            "BOQ Item",
            second.name,
            {
                "is_variation_item": 1,
                "current_revised_qty": 5,
                "current_revised_unit_price": 40,
                "factor": 3,
            },
            update_modified=False,
        )
        before = self._stored_snapshot()

        result = audit_boq_rollups(self.header.name)

        self.assertEqual(
            result["header"]["computed"],
            {
                "total_contract_value": 150,
                "total_estimated_value": 60,
                "total_budgeted_cost": 60,
                "total_revised_value": 870,
            },
        )
        self.assertEqual(
            result["header"]["mismatched_fields"],
            [
                "total_contract_value",
                "total_estimated_value",
                "total_budgeted_cost",
                "total_revised_value",
            ],
        )

        group_result = next(row for row in result["structures"] if row["name"] == self.group.name)
        self.assertEqual(
            group_result["computed"],
            {
                "item_count": 2,
                "total_contract_value": 390,
                "total_budgeted_cost": 180,
            },
        )
        self.assertEqual(group_result["mismatched_fields"], ["total_budgeted_cost"])

        leaf_result = next(row for row in result["structures"] if row["name"] == self.structures[1].name)
        self.assertEqual(leaf_result["computed"]["total_budgeted_cost"], 120)
        self.assertEqual(leaf_result["mismatched_fields"], ["total_budgeted_cost"])
        self.assertEqual(self._stored_snapshot(), before)

    def test_header_docstatus_and_structure_docstatus_policy_is_reported(self):
        frappe.db.set_value("BOQ Item", self.items[1].name, "docstatus", 2, update_modified=False)

        result = audit_boq_rollups(self.header.name)

        self.assertEqual(result["header"]["computed"]["total_contract_value"], 390)
        group_result = next(row for row in result["structures"] if row["name"] == self.group.name)
        self.assertEqual(
            group_result["computed"],
            {
                "item_count": 1,
                "total_contract_value": 150,
                "total_budgeted_cost": 60,
            },
        )
        self.assertEqual(
            group_result["mismatched_fields"], ["item_count", "total_contract_value", "total_budgeted_cost"]
        )

    def test_non_administrator_is_denied(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            audit_boq_rollups(self.header.name)

    def test_missing_header_is_rejected(self):
        with self.assertRaises(frappe.DoesNotExistError):
            audit_boq_rollups("BOQ-ROLLUP-AUDIT-MISSING")
