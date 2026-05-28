import frappe
from frappe.tests.utils import FrappeTestCase

from construction.services.boq_accounting import validate_transaction_row
from construction.services.boq_transaction_validation import CHILD_TABLE_BY_DOCTYPE, get_child_table


class TestBOQTransactionValidation(FrappeTestCase):
    def setUp(self):
        self._clear_scope_defaults()
        self.project = self._make_project()
        self.other_project = self._make_project("_Test BOQ Other Project")
        self.header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "project": self.project,
                "title": "Test Transaction BOQ",
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        self.item = self._make_item(self.header.name, "Transaction Item")
        self.item.quantity = 10
        self.item.has_stages = 1
        self.item.save(ignore_permissions=True)

        self.header.status = "Pricing"
        self.header.save(ignore_permissions=True)
        self.header.status = "Frozen"
        self.header.save(ignore_permissions=True)

        self.stage = frappe.get_doc(
            {
                "doctype": "BOQ Item Stage",
                "boq_item": self.item.name,
                "stage_code": "TXN",
                "stage_name": "Transaction Stage",
                "planned_qty": 10,
                "measured_executed_qty": 0,
                "certified_qty": 0,
                "percent_complete": 0,
                "stage_status": "Not Started",
            }
        ).insert(ignore_permissions=True)

    def _clear_scope_defaults(self):
        for key in ("branch", "company", "cost_center", "project", "department"):
            frappe.defaults.clear_user_default(key, "Administrator")

    def _make_project(self, project_name="_Test BOQ Transaction Project"):
        company = frappe.db.get_value("Company", {}, "name")
        if not company:
            company = (
                frappe.get_doc(
                    {
                        "doctype": "Company",
                        "company_name": "_Test BOQ Transaction Company",
                        "default_currency": "USD",
                        "country": "United States",
                    }
                )
                .insert(ignore_permissions=True)
                .name
            )

        project = frappe.db.get_value("Project", {"project_name": project_name}, "name")
        if project:
            return project

        return (
            frappe.get_doc(
                {
                    "doctype": "Project",
                    "project_name": project_name,
                    "company": company,
                    "naming_series": "PROJ-.####",
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _make_item(self, header_name, title):
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header_name,
                "title": title,
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        return frappe.get_doc(
            "BOQ Item",
            frappe.db.get_value("BOQ Item", {"structure": structure.name}, "name"),
        )

    def test_child_table_mapping_covers_all_approved_doctypes(self):
        self.assertEqual(
            set(CHILD_TABLE_BY_DOCTYPE),
            {
                "Purchase Order",
                "Purchase Receipt",
                "Purchase Invoice",
                "Sales Invoice",
                "Stock Entry",
                "Timesheet",
                "Journal Entry",
                "Material Request",
            },
        )
        for doctype, table_field in CHILD_TABLE_BY_DOCTYPE.items():
            doc = frappe._dict({"doctype": doctype, table_field: [frappe._dict({"idx": 1})]})
            self.assertEqual(get_child_table(doc), doc[table_field])

    def test_valid_row_passes(self):
        row = frappe._dict(
            {
                "idx": 1,
                "project": self.project,
                "boq_item": self.item.name,
                "boq_item_stage": self.stage.name,
            }
        )
        validate_transaction_row(row, frappe._dict({"project": self.project}))

    def test_no_boq_fields_are_allowed(self):
        validate_transaction_row(frappe._dict({"idx": 1}), frappe._dict({}))

    def test_stage_requires_item(self):
        row = frappe._dict({"idx": 1, "boq_item_stage": self.stage.name})
        with self.assertRaises(frappe.ValidationError):
            validate_transaction_row(row, frappe._dict({}))

    def test_draft_and_pricing_headers_block_attribution(self):
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "project": self.project,
                "title": "Blocked BOQ",
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        item = self._make_item(header.name, "Blocked Item")

        row = frappe._dict({"idx": 1, "project": self.project, "boq_item": item.name})
        with self.assertRaises(frappe.ValidationError):
            validate_transaction_row(row, frappe._dict({"project": self.project}))

        header.status = "Pricing"
        header.save(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            validate_transaction_row(row, frappe._dict({"project": self.project}))

    def test_project_mismatch_rejected(self):
        row = frappe._dict({"idx": 1, "project": self.other_project, "boq_item": self.item.name})
        with self.assertRaises(frappe.ValidationError):
            validate_transaction_row(row, frappe._dict({}))

    def test_stage_from_other_item_rejected(self):
        other_header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "project": self.project,
                "title": "Other Stage BOQ",
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        other_item = self._make_item(other_header.name, "Other Stage Item")
        other_header.status = "Pricing"
        other_header.save(ignore_permissions=True)
        other_header.status = "Frozen"
        other_header.save(ignore_permissions=True)

        row = frappe._dict(
            {
                "idx": 1,
                "project": self.project,
                "boq_item": other_item.name,
                "boq_item_stage": self.stage.name,
            }
        )
        with self.assertRaises(frappe.ValidationError):
            validate_transaction_row(row, frappe._dict({}))
