import frappe
from frappe.tests.utils import FrappeTestCase


class TestBOQHookRegression(FrappeTestCase):
    def test_scope_wildcard_hook_preserved(self):
        import construction.hooks as hooks

        self.assertIn("*", hooks.doc_events)
        self.assertEqual(
            hooks.doc_events["*"]["validate"],
            "construction.overrides.scope_enforcement.validate",
        )

    def test_boq_transaction_hooks_registered(self):
        """The single-handler DocTypes keep the EXACT shared BOQ validator."""
        import construction.hooks as hooks

        for doctype in (
            "Purchase Order",
            "Purchase Receipt",
            "Purchase Invoice",
            "Stock Entry",
            "Sales Invoice",
            "Material Request",
        ):
            with self.subTest(doctype=doctype):
                self.assertEqual(
                    hooks.doc_events[doctype]["validate"],
                    "construction.services.boq_transaction_validation.validate_document",
                )

    def test_timesheet_validate_hook_order(self):
        """The Timesheet validation order is the EXACT ordered list."""
        import construction.hooks as hooks

        self.assertEqual(
            hooks.doc_events["Timesheet"]["validate"],
            [
                "construction.services.timesheet_designation.derive_row_designations",
                "construction.services.boq_transaction_validation.validate_document",
            ],
        )

    def test_journal_entry_validate_hook_order(self):
        """The Journal Entry validation order is the EXACT ordered list.

        The shared BOQ validator normalizes the BOQ chain first; the Journal
        Entry helper then derives and validates the authoritative BOQ project,
        because the wildcard scope hook never sees a Journal Entry Account
        project (a Journal Entry has no parent ``project`` field).
        """
        import construction.hooks as hooks

        self.assertEqual(
            hooks.doc_events["Journal Entry"]["validate"],
            [
                "construction.services.boq_transaction_validation.validate_document",
                "construction.services.boq_journal_project.validate_document",
            ],
        )
