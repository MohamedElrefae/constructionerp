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
        import construction.hooks as hooks

        for doctype in (
            "Purchase Order",
            "Purchase Receipt",
            "Purchase Invoice",
            "Stock Entry",
            "Timesheet",
            "Journal Entry",
            "Sales Invoice",
            "Material Request",
        ):
            self.assertEqual(
                hooks.doc_events[doctype]["validate"],
                "construction.services.boq_transaction_validation.validate_document",
            )
