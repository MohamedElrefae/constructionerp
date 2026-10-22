"""Two real MariaDB transactions, including stale snapshots and overlapping locks.

Like framework concurrency tests, these deliberately commit synthetic fixtures
on the allow_tests site so a second connection can see them. Cleanup deletes
only this test's BOQ records. Never run business suites on a customer site.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.construction.utils.rollup import defer_boq_rollups
from construction.services.boq_rollup_audit import audit_boq_rollups
from construction.services.boq_transactions import lock_boq_header
from construction.services.quantity_revisions import (
    approve_quantity_revision,
    create_lock_baseline,
    create_quantity_revision,
)
from construction.tests import test_cost_analysis_engine as costing_fixtures
from construction.tests import test_customer_release_financial_guards as financial_fixtures


class TestBOQTransactions(FrappeTestCase):
    def setUp(self):
        self.assertTrue(frappe.conf.allow_tests)
        financial_fixtures.TestCustomerReleaseFinancialGuards.setUp(self)
        self.company = frappe.db.get_value("Project", self.header.project, "company")
        self.structure_names = [self.group.name, *(item.structure for item in self.items)]
        self.item_names = [item.name for item in self.items]
        frappe.db.commit()
        self.assertEqual(frappe.db.sql("SELECT @@tx_isolation")[0][0], "REPEATABLE-READ")
        connection_id = frappe.db.sql("SELECT CONNECTION_ID()")[0][0]
        with self.secondary_connection():
            frappe.db.rollback()
            self.assertNotEqual(connection_id, frappe.db.sql("SELECT CONNECTION_ID()")[0][0])
        # The legacy Frappe helper initializes its first secondary connection
        # before capturing the old local connection. Restore explicitly.
        frappe.local.db = self._primary_connection
        self.assertIsNot(self._primary_connection, self._secondary_connection)

    def tearDown(self):
        # Roll back both open transactions before targeted fixture cleanup;
        # otherwise another connection's locks could block the cleanup itself.
        self._primary_connection.rollback()
        self._secondary_connection.rollback()
        with self.primary_connection():
            analyses = frappe.get_all(
                "BOQ Cost Analysis", filters={"boq_item": ["in", self.item_names]}, pluck="name"
            )
            if analyses:
                child_doctype = frappe.get_meta("BOQ Cost Analysis").get_field("details").options
                frappe.db.delete(child_doctype, {"parent": ["in", analyses]})
                frappe.db.delete("BOQ Cost Analysis", {"name": ["in", analyses]})
            frappe.db.delete("BOQ Quantity Revision", {"boq_header": self.header.name})
            frappe.db.delete("BOQ Item", {"boq_header": self.header.name})
            frappe.db.delete("BOQ Structure", {"boq_header": self.header.name})
            frappe.db.delete("BOQ Header", {"name": self.header.name})
            frappe.db.commit()

    def _assert_current_totals(self, contract=None, budget=None, revised=None):
        # Start a fresh reader, independently of the writers' old snapshots.
        frappe.db.rollback()
        audit = audit_boq_rollups(self.header.name)
        self.assertFalse(audit["header"]["mismatched_fields"], audit)
        for structure in audit["structures"]:
            self.assertFalse(structure["mismatched_fields"], structure)
        actual = audit["header"]["stored"]
        for field, expected in (
            ("total_contract_value", contract),
            ("total_budgeted_cost", budget),
            ("total_revised_value", revised),
        ):
            if expected is not None:
                self.assertAlmostEqual(float(actual[field]), expected, places=6)

    def _save_other_item(self, quantity=8):
        with self.secondary_connection():
            item = frappe.get_doc("BOQ Item", self.items[1].name)
            item.quantity = quantity
            item.save(ignore_permissions=True)
            frappe.db.commit()

    def test_different_item_save_uses_current_aggregate_after_stale_snapshot(self):
        item = frappe.get_doc("BOQ Item", self.items[0].name)
        self._save_other_item()
        item.quantity = 4
        item.save(ignore_permissions=True)
        frappe.db.commit()
        self._assert_current_totals(contract=120, budget=48)

    def test_delete_after_other_item_commit_uses_current_remaining_rows(self):
        frappe.get_doc("BOQ Item", self.items[0].name)  # establish old snapshot
        self._save_other_item()
        frappe.delete_doc("BOQ Item", self.items[0].name)
        frappe.db.commit()
        self._assert_current_totals(contract=80, budget=32)

    def test_deferred_batch_flush_uses_current_aggregate(self):
        item = frappe.get_doc("BOQ Item", self.items[0].name)
        self._save_other_item()
        with defer_boq_rollups():
            item.quantity = 4
            item.save(ignore_permissions=True)
        self.header.recalculate_phase1_totals()
        frappe.db.commit()
        self._assert_current_totals(contract=120, budget=48)

    def test_two_different_item_approvals_and_repeat_approval(self):
        create_lock_baseline(self.header.name)
        revisions = [
            create_quantity_revision(
                item.name,
                previous_qty=item.quantity,
                revised_qty=quantity,
                contract_unit_price=10,
                revised_unit_price=10,
                rate_change_justification="Synthetic concurrency test",
            ).name
            for item, quantity in zip(self.items, (4, 8), strict=True)
        ]
        frappe.db.commit()
        frappe.get_doc("BOQ Quantity Revision", revisions[0])  # establish old snapshot
        with self.secondary_connection():
            approve_quantity_revision(revisions[1])
            frappe.db.commit()
        approve_quantity_revision(revisions[0])
        frappe.db.commit()
        self._assert_current_totals(contract=100, budget=40, revised=120)
        before = frappe.db.count("BOQ Quantity Revision", {"boq_header": self.header.name})
        approve_quantity_revision(revisions[0])
        frappe.db.commit()
        self._assert_current_totals(revised=120)
        self.assertEqual(before, frappe.db.count("BOQ Quantity Revision", {"boq_header": self.header.name}))

    def test_header_contention_fails_closed_then_whole_operation_retry_succeeds(self):
        lock_boq_header(self.header.name)
        with self.secondary_connection():
            item = frappe.get_doc("BOQ Item", self.items[1].name)
            item.quantity = 8
            with self.assertRaises(frappe.QueryTimeoutError):
                item.save(ignore_permissions=True)
            # Even callers that swallow the error cannot commit this transaction.
            for _ in range(2):
                with self.assertRaises(frappe.QueryTimeoutError):
                    frappe.db.commit()
            frappe.db.rollback()
        item = frappe.get_doc("BOQ Item", self.items[0].name)
        item.quantity = 4
        item.save(ignore_permissions=True)
        frappe.db.commit()
        self._save_other_item()  # one explicit fresh-transaction retry, no retry loop
        self._assert_current_totals(contract=120, budget=48)

    def test_partial_write_and_savepoint_recovery_cannot_commit_after_lock_failure(self):
        lock_boq_header(self.header.name)
        with self.secondary_connection():
            # Model a legacy service that writes first, then catches a lock error.
            frappe.db.set_value("BOQ Item", self.items[1].name, "quantity", 777)
            frappe.db.savepoint("release_concurrency_probe")
            with self.assertRaises(frappe.QueryTimeoutError):
                lock_boq_header(self.header.name)
            frappe.db.rollback(save_point="release_concurrency_probe")
            with self.assertRaises(frappe.QueryTimeoutError):
                frappe.db.commit()
            frappe.db.rollback()
        frappe.db.rollback()
        self.assertEqual(frappe.db.get_value("BOQ Item", self.items[1].name, "quantity"), 7)
        self._assert_current_totals(contract=100, budget=40)

    def test_header_save_cannot_overwrite_newer_item_totals_from_old_snapshot(self):
        header = frappe.get_doc("BOQ Header", self.header.name)
        self._save_other_item()
        header.title = "Synthetic title edit after another transaction"
        header.save(ignore_permissions=True)
        frappe.db.commit()
        self._assert_current_totals(contract=110, budget=44)

    def test_frozen_status_is_checked_against_current_header(self):
        item = frappe.get_doc("BOQ Item", self.items[0].name)
        with self.secondary_connection():
            header = frappe.get_doc("BOQ Header", self.header.name)
            for status in ("Pricing", "Frozen"):
                header.status = status
                header.save(ignore_permissions=True)
            frappe.db.commit()
        item.quantity = 4
        with self.assertRaisesRegex(frappe.ValidationError, "Frozen"):
            item.save(ignore_permissions=True)
        frappe.db.rollback()
        self._assert_current_totals(contract=100, budget=40)

    def _analysis(self, item, rate):
        item_code = costing_fixtures.TestCostAnalysisEngine._make_item_doctype(
            self, "_Test Release Concurrency Material", "Release Concurrency Material"
        )
        return costing_fixtures.TestCostAnalysisEngine._make_cost_analysis(
            self,
            item.name,
            details=[
                {
                    "cost_stream": "M",
                    "item_code": item_code,
                    "resource_uom": "Nos",
                    "qty_per_boq_unit": 1,
                    "cost_rate": rate,
                }
            ],
        )

    def test_cost_approvals_on_different_items_use_current_budget_rows(self):
        analyses = [self._analysis(item, rate).name for item, rate in zip(self.items, (6, 9), strict=True)]
        frappe.db.commit()
        first = frappe.get_doc("BOQ Cost Analysis", analyses[0])  # old snapshot
        with self.secondary_connection():
            frappe.get_doc("BOQ Cost Analysis", analyses[1]).submit()
            frappe.db.commit()
        first.submit()
        frappe.db.commit()
        self._assert_current_totals(contract=100, budget=81)

    def test_cost_cancellation_restoration_uses_current_item_quantity(self):
        prior = self._analysis(self.items[0], 6)
        prior.submit()
        current = self._analysis(self.items[0], 9)
        current.submit()
        frappe.db.commit()
        current = frappe.get_doc("BOQ Cost Analysis", current.name)  # old snapshot
        with self.secondary_connection():
            item = frappe.get_doc("BOQ Item", self.items[0].name)
            item.quantity = 4
            item.save(ignore_permissions=True)
            frappe.db.commit()
        current.cancel()
        frappe.db.commit()
        self._assert_current_totals(contract=110, budget=52)

    def test_rollup_failure_rolls_back_item_header_and_structure_together(self):
        item = frappe.get_doc("BOQ Item", self.items[0].name)
        item.quantity = 4
        with patch.object(
            type(self.header), "recalculate_structure_rollups", side_effect=RuntimeError("probe")
        ):
            with self.assertRaisesRegex(RuntimeError, "probe"):
                item.save(ignore_permissions=True)
        frappe.db.rollback()
        self._assert_current_totals(contract=100, budget=40)
        self.assertEqual(frappe.db.get_value("BOQ Item", item.name, "quantity"), 3)

    def test_injected_deadlock_also_requires_full_rollback(self):
        with patch.object(frappe.db, "sql", side_effect=frappe.QueryDeadlockError("probe")):
            with self.assertRaises(frappe.QueryTimeoutError):
                lock_boq_header(self.header.name)
        with self.assertRaises(frappe.QueryTimeoutError):
            frappe.db.commit()
        frappe.db.rollback()
        self._assert_current_totals(contract=100, budget=40)
