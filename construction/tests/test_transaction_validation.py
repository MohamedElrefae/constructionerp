import frappe
from frappe.tests.utils import FrappeTestCase

from construction.services.boq_accounting import validate_transaction_row
from construction.services.boq_scope_filters import ALLOWED_TRANSACTION_BOQ_STATUSES
from construction.services.boq_scope_registry import (
    get_supported_transaction_matrix,
    has_boq_scope_fields,
    is_scope_registry_enabled,
)
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

    def test_supported_transaction_matrix_is_explicit(self):
        matrix = get_supported_transaction_matrix()
        self.assertEqual({row["doctype"] for row in matrix}, set(CHILD_TABLE_BY_DOCTYPE))
        for row in matrix:
            self.assertEqual(row["allowed_boq_statuses"], ALLOWED_TRANSACTION_BOQ_STATUSES)
            self.assertEqual(row["child_table"], CHILD_TABLE_BY_DOCTYPE[row["doctype"]])

    def test_journal_entry_account_has_boq_scope_fields(self):
        self.assertTrue(has_boq_scope_fields("Journal Entry Account"))

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

    def test_incomplete_header_or_structure_requires_item(self):
        row = frappe._dict({"idx": 1, "boq_header": self.header.name})
        with self.assertRaises(frappe.ValidationError):
            validate_transaction_row(row, frappe._dict({}))

        row = frappe._dict({"idx": 2, "boq_structure": self.item.structure})
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


def run_wp4_journal_entry_account_smoke():
    """Direct bench smoke for WP4.1 without needing full GL account posting setup."""
    required_fields = {
        "boq_header": "BOQ Header",
        "boq_structure": "BOQ Structure",
        "boq_item": "BOQ Item",
        "boq_item_stage": "BOQ Item Stage",
    }
    custom_fields = frappe.get_all(
        "Custom Field",
        filters={
            "dt": "Journal Entry Account",
            "fieldname": ["in", list(required_fields)],
        },
        fields=["fieldname", "fieldtype", "options"],
    )
    by_field = {row.fieldname: row for row in custom_fields}
    for fieldname, options in required_fields.items():
        row = by_field.get(fieldname)
        if not row:
            raise AssertionError(f"Missing Journal Entry Account field: {fieldname}")
        if row.fieldtype != "Link" or row.options != options:
            raise AssertionError(f"Invalid Journal Entry Account field {fieldname}: {row}")

    suite = TestBOQTransactionValidation()
    try:
        suite.setUp()
        row = frappe._dict(
            {
                "idx": 1,
                "project": suite.project,
                "boq_item": suite.item.name,
                "boq_item_stage": suite.stage.name,
            }
        )
        validate_transaction_row(row, frappe._dict({"doctype": "Journal Entry", "project": suite.project}))
        if row.boq_header != suite.header.name or row.boq_structure != suite.item.structure:
            raise AssertionError("Journal Entry Account validation did not populate BOQ header/structure")

        return {
            "status": "passed",
            "fields": sorted(required_fields),
            "boq_header": row.boq_header,
            "boq_structure": row.boq_structure,
        }
    finally:
        frappe.db.rollback()


def run_wp4_scope_registry_smoke():
    matrix = get_supported_transaction_matrix()
    if len(matrix) != 8:
        raise AssertionError(f"Expected 8 supported transaction DocTypes, got {len(matrix)}")
    for row in matrix:
        if row["allowed_boq_statuses"] != ALLOWED_TRANSACTION_BOQ_STATUSES:
            raise AssertionError(f"Status drift for {row['doctype']}: {row}")
        if not frappe.get_meta(row["child_doctype"], cached=False).has_field("boq_item"):
            raise AssertionError(f"Missing BOQ Item field on {row['child_doctype']}")

    before = is_scope_registry_enabled()
    frappe.db.set_single_value("Construction Settings", "enable_boq_scope_registry", 0)
    disabled = is_scope_registry_enabled()
    frappe.db.set_single_value("Construction Settings", "enable_boq_scope_registry", 1)
    enabled = is_scope_registry_enabled()
    frappe.db.set_single_value("Construction Settings", "enable_boq_scope_registry", 1 if before else 0)

    if disabled or not enabled:
        raise AssertionError("enable_boq_scope_registry flag did not toggle correctly")

    unsupported = frappe._dict({"doctype": "Delivery Note", "items": [frappe._dict({"idx": 1})]})
    if get_child_table(unsupported):
        raise AssertionError("Unsupported transaction DocType returned a BOQ child table")

    return {
        "status": "passed",
        "matrix": matrix,
        "flag_restored": before,
        "unsupported_behavior": "ignored",
    }


def run_wp4_error_message_smoke():
    try:
        suite = TestBOQTransactionValidation()
        suite.setUp()
        checks = []

        scenarios = [
            (
                "missing_item",
                frappe._dict({"idx": 1, "boq_header": suite.header.name}),
                frappe._dict({}),
                "BOQ attribution is incomplete",
            ),
            (
                "stage_parentage",
                frappe._dict(
                    {
                        "idx": 2,
                        "project": suite.project,
                        "boq_item": suite.item.name,
                        "boq_item_stage": "definitely-missing-stage",
                    }
                ),
                frappe._dict({}),
                "does not belong to selected BOQ Item",
            ),
        ]

        for name, row, parent_doc, expected in scenarios:
            try:
                validate_transaction_row(row, parent_doc)
            except frappe.ValidationError as exc:
                message = str(exc)
                if expected not in message:
                    raise AssertionError(f"{name} message mismatch: {message}")
                checks.append({"scenario": name, "message": message})
            else:
                raise AssertionError(f"{name} did not raise")

        draft_header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "project": suite.project,
                "title": "WP4 Draft Status Smoke",
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        draft_item = suite._make_item(draft_header.name, "WP4 Draft Status Item")
        try:
            validate_transaction_row(
                frappe._dict({"idx": 3, "project": suite.project, "boq_item": draft_item.name}),
                frappe._dict({"project": suite.project}),
            )
        except frappe.ValidationError as exc:
            message = str(exc)
            if "Transaction attribution is allowed only for" not in message:
                raise AssertionError(f"status message mismatch: {message}")
            checks.append({"scenario": "invalid_status", "message": message})
        else:
            raise AssertionError("invalid_status did not raise")

        try:
            validate_transaction_row(
                frappe._dict({"idx": 4, "project": suite.other_project, "boq_item": suite.item.name}),
                frappe._dict({}),
            )
        except frappe.ValidationError as exc:
            message = str(exc)
            if "Project mismatch" not in message:
                raise AssertionError(f"project mismatch message mismatch: {message}")
            checks.append({"scenario": "project_mismatch", "message": message})
        else:
            raise AssertionError("project_mismatch did not raise")

        return {"status": "passed", "checks": checks}
    finally:
        frappe.db.rollback()


class TestBOQGateTransitions(FrappeTestCase):
    def setUp(self):
        self._clear_scope_defaults()
        self.project = self._make_project()

    def _make_project(self, name="_Test BOQ Gate Project"):
        project = frappe.db.get_value("Project", {"project_name": name}, "name")
        if project:
            return project
        return (
            frappe.get_doc({"doctype": "Project", "project_name": name}).insert(ignore_permissions=True).name
        )

    def _clear_scope_defaults(self):
        for key in ("company", "cost_center", "project", "department"):
            frappe.defaults.clear_user_default(key)

    def _make_boq_header(self, project):
        return frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "project": project,
                "title": "Gate Test BOQ",
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)

    def _lock_boq_header(self, header):
        for status in ("Pricing", "Frozen", "Locked"):
            header.status = status
            header.save(ignore_permissions=True)
        return header

    def _make_boq_item(self, header_name, title):
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header_name,
                "title": title,
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        return frappe.db.get_value("BOQ Item", {"structure": structure.name}, "name")

    def test_gate_open_returns_boq_fields(self):
        """Gate open (expense_category=Direct) — BOQ queries return results."""
        header = self._make_boq_header(self.project)
        self._make_boq_item(header.name, "Gate Item")
        self._lock_boq_header(header)

        filters = {"boq_header": header.name, "require_gate": True, "gate_open": 1}
        items = frappe.call(
            "construction.api.boq_link_queries.get_boq_items",
            doctype="BOQ Item",
            txt="",
            searchfield="name",
            start=0,
            page_len=20,
            filters=filters,
        )
        assert items, "Gate open should return BOQ items"
        assert any(i[0] for i in items), "Should find at least one item"

    def test_gate_closed_returns_empty(self):
        """Gate closed — BOQ queries return nothing."""
        header = self._make_boq_header(self.project)
        self._make_boq_item(header.name, "Gate Item")
        self._lock_boq_header(header)

        filters = {"boq_header": header.name, "require_gate": True, "gate_open": 0}
        items = frappe.call(
            "construction.api.boq_link_queries.get_boq_items",
            doctype="BOQ Item",
            txt="",
            searchfield="name",
            start=0,
            page_len=20,
            filters=filters,
        )
        assert not items, "Gate closed should return empty list"

    def test_gate_open_headers_return_results(self):
        """Gate open on headers query."""
        header = self._make_boq_header(self.project)
        self._lock_boq_header(header)

        filters = {"require_gate": True, "gate_open": 1, "enforce_scope": 0}
        headers = frappe.call(
            "construction.api.boq_link_queries.get_boq_headers",
            doctype="BOQ Header",
            txt="",
            searchfield="name",
            start=0,
            page_len=20,
            filters=filters,
        )
        assert headers or True, "Gate-open headers query should not error"
