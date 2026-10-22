"""Regression tests for the bounded Timesheet designation correction.

The direct-labor BOQ gate reads the Timesheet Detail ``designation`` field.
These tests cover the authorized native derivation path (employee -> row
designation), the handling of employee changes, employee clearing and stale or
spoofed row values, and the authorization boundary of the public lookup helper
(denied user, forbidden employee, foreign company, Guest, authorized flow).
Fixture setup and cleanup are owned by the suite.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from construction.services.timesheet_designation import (
    derive_row_designations,
    get_employee_designation,
    get_timesheet_employee_designation,
    row_designation_mismatches,
)


class TestTimesheetDesignation(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name")
        self.other_company = self._make_other_company()
        self.designation = self._make_designation("_Test Omission Direct Labor")
        self.employee = self._make_employee(self.designation, self.company)
        self.other_designation = self._make_designation("_Test Omission Other Labor")
        self.other_employee = self._make_employee(self.other_designation, self.company)
        self.foreign_employee = self._make_employee(self.other_designation, self.other_company)
        self.activity_type = frappe.db.get_value("Activity Type", {}, "name") or self._make_activity_type()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    # ---------------------------------------------------------------- fixtures

    def _make_other_company(self):
        existing = frappe.db.get_value("Company", {"company_name": "_Test Omission Other Co"}, "name")
        if existing:
            return existing
        return (
            frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": "_Test Omission Other Co",
                    "abbr": "_TOOC",
                    "default_currency": "USD",
                    "country": "United States",
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _make_designation(self, label):
        existing = frappe.db.get_value("Designation", {"designation_name": label}, "name")
        if existing:
            return existing
        return (
            frappe.get_doc({"doctype": "Designation", "designation_name": label})
            .insert(ignore_permissions=True)
            .name
        )

    def _make_employee(self, designation, company):
        return (
            frappe.get_doc(
                {
                    "doctype": "Employee",
                    "employee_name": f"Omission Employee {frappe.generate_hash(length=5)}",
                    "first_name": "Omission",
                    "last_name": "Employee",
                    "company": company,
                    "designation": designation,
                    "gender": "Other",
                    "date_of_joining": nowdate(),
                    "date_of_birth": nowdate(),
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _make_activity_type(self):
        return (
            frappe.get_doc(
                {"doctype": "Activity Type", "name": f"Omission Activity {frappe.generate_hash(length=5)}"}
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _new_timesheet(self, employee=None, designation=None):
        return frappe.get_doc(
            {
                "doctype": "Timesheet",
                "employee": employee,
                "company": self.company,
                "time_logs": [
                    {
                        "doctype": "Timesheet Detail",
                        "activity_type": self.activity_type,
                        "from_time": nowdate() + " 09:00:00",
                        "hours": 4,
                        "designation": designation,
                    }
                ],
            }
        )

    def _make_user(self, roles, scope_company=None, scope_project=None):
        """Create a test user.

        Fixture creation may use permission overrides; the *tested* authorization
        path below always runs as a real user with real roles.
        """
        from construction.tests.test_boq_helpers import get_or_create_test_project

        email = f"omission-ts-ctl-{frappe.generate_hash(length=8)}@example.invalid"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Omission Timesheet Control",
                "send_welcome_email": 0,
            }
        )
        user.set("roles", [])
        for role in roles:
            user.append("roles", {"role": role})
        user.insert(ignore_permissions=True)
        frappe.get_doc(
            {
                "doctype": "User Scope Context",
                "user": email,
                "company": scope_company or self.company,
                "project": scope_project or get_or_create_test_project(),
            }
        ).insert(ignore_permissions=True)
        return user.name

    # ------------------------------------------------- derivation (save path)

    def test_designation_derived_from_selected_employee(self):
        """Normal flow: selecting an employee derives the row designation."""
        doc = self._new_timesheet(employee=self.employee)
        doc.insert(ignore_permissions=True)
        self.assertEqual(doc.time_logs[0].designation, self.designation)
        self.assertEqual(row_designation_mismatches(doc), [])

    def test_employee_change_rederives_designation(self):
        doc = self._new_timesheet(employee=self.employee)
        doc.insert(ignore_permissions=True)
        self.assertEqual(doc.time_logs[0].designation, self.designation)

        doc.reload()
        doc.employee = self.other_employee
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.time_logs[0].designation, self.other_designation)

    def test_clearing_employee_clears_designation(self):
        doc = self._new_timesheet(employee=self.employee)
        doc.insert(ignore_permissions=True)
        self.assertEqual(doc.time_logs[0].designation, self.designation)

        doc.reload()
        doc.employee = None
        doc.save(ignore_permissions=True)
        self.assertFalse(doc.time_logs[0].designation)

    def test_spoofed_row_designation_is_corrected(self):
        """A client-supplied designation never survives a save."""
        doc = self._new_timesheet(employee=self.employee, designation=self.other_designation)
        doc.insert(ignore_permissions=True)
        self.assertEqual(doc.time_logs[0].designation, self.designation)
        self.assertEqual(row_designation_mismatches(doc), [])

    def test_optional_attribution_is_preserved(self):
        """Deriving the designation does not make BOQ attribution compulsory."""
        doc = self._new_timesheet(employee=self.employee)
        doc.insert(ignore_permissions=True)
        row = doc.time_logs[0]
        self.assertFalse(row.get("boq_item"))
        self.assertFalse(row.get("boq_header"))
        self.assertEqual(row.designation, self.designation)

    def test_derivation_is_a_noop_for_other_doctypes(self):
        other = frappe._dict({"doctype": "Material Request", "time_logs": []})
        derive_row_designations(other)
        self.assertEqual(other.get("time_logs"), [])

    def test_designation_lookup_helper(self):
        self.assertEqual(get_employee_designation(self.employee), self.designation)
        self.assertIsNone(get_employee_designation(None))

    # ------------------------------------------- public helper authorization

    def test_authorized_native_flow_returns_the_designation(self):
        """An ordinary user with the native Employee select policy may use it."""
        user = self._make_user(("Accounts User",))
        try:
            frappe.set_user(user)
            self.assertTrue(frappe.has_permission("Employee", "select"))
            result = get_timesheet_employee_designation(self.employee)
            self.assertEqual(set(result.keys()), {"designation"})
            self.assertEqual(result["designation"], self.designation)
        finally:
            frappe.set_user("Administrator")

    def test_denied_user_cannot_use_the_public_helper(self):
        """A user without the native Employee select policy is refused."""
        user = self._make_user(("Purchase User",))
        try:
            frappe.set_user(user)
            self.assertFalse(frappe.has_permission("Employee", "select"))
            with self.assertRaises(frappe.PermissionError):
                get_timesheet_employee_designation(self.employee)
        finally:
            frappe.set_user("Administrator")

    def test_guest_cannot_use_the_public_helper(self):
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                get_timesheet_employee_designation(self.employee)
        finally:
            frappe.set_user("Administrator")

    def test_employee_outside_the_active_scope_is_refused(self):
        """Foreign company employees are refused for a scoped caller."""
        user = self._make_user(("Accounts User",), scope_company=self.company)
        try:
            frappe.set_user(user)
            with self.assertRaises(frappe.PermissionError):
                get_timesheet_employee_designation(self.foreign_employee)
        finally:
            frappe.set_user("Administrator")

    def test_ordinary_user_save_without_ignore_permissions(self):
        """An ordinary user saves a Timesheet and the designation is derived."""
        user = self._make_user(("Accounts User",))
        try:
            frappe.set_user(user)
            doc = self._new_timesheet(employee=self.employee)
            doc.insert()
            self.assertEqual(doc.time_logs[0].designation, self.designation)
        finally:
            frappe.set_user("Administrator")

    def test_whitelisted_helper_reports_no_employee_as_empty(self):
        result = get_timesheet_employee_designation(None)
        self.assertIsNone(result["designation"])

    # ---------------------------------------------------- scope policy (A)

    def _set_scope_enforcement(self, enabled):
        frappe.db.set_single_value("Construction Settings", "enable_scope_context", 1 if enabled else 0)

    def test_scope_active_without_context_is_refused(self):
        """An ordinary user with Employee select but no scope context is denied."""
        self._set_scope_enforcement(True)
        user = self._make_user(("Accounts User",), scope_company=self.company)
        try:
            frappe.set_user(user)
            frappe.db.delete("User Scope Context", {"user": user})
            with self.assertRaises(frappe.PermissionError):
                get_timesheet_employee_designation(self.employee)
        finally:
            frappe.set_user("Administrator")

    def test_scope_active_with_empty_company_is_refused(self):
        self._set_scope_enforcement(True)
        user = self._make_user(("Accounts User",), scope_company=self.company)
        try:
            frappe.set_user(user)
            from construction.services import timesheet_designation as module

            original = module.get_user_scope_context
            module.get_user_scope_context = lambda user=None: frappe._dict(company=None, project=None)
            with self.assertRaises(frappe.PermissionError):
                get_timesheet_employee_designation(self.employee)
            module.get_user_scope_context = original
        finally:
            frappe.set_user("Administrator")

    def test_permitted_scoped_user_is_allowed(self):
        self._set_scope_enforcement(True)
        user = self._make_user(("Accounts User",), scope_company=self.company)
        try:
            frappe.set_user(user)
            result = get_timesheet_employee_designation(self.employee)
            self.assertEqual(result["designation"], self.designation)
        finally:
            frappe.set_user("Administrator")

    def test_employee_without_company_is_refused_under_scope(self):
        self._set_scope_enforcement(True)
        from construction.services import timesheet_designation as module

        original = module.get_employee_company
        module.get_employee_company = lambda employee: None
        user = self._make_user(("Accounts User",), scope_company=self.company)
        try:
            frappe.set_user(user)
            with self.assertRaises(frappe.PermissionError):
                get_timesheet_employee_designation(self.employee)
        finally:
            module.get_employee_company = original
            frappe.set_user("Administrator")

    def test_missing_employee_is_refused(self):
        self._set_scope_enforcement(True)
        user = self._make_user(("Accounts User",), scope_company=self.company)
        try:
            frappe.set_user(user)
            with self.assertRaises((frappe.PermissionError, frappe.DoesNotExistError)):
                get_timesheet_employee_designation("HR-EMP-DOES-NOT-EXIST")
        finally:
            frappe.set_user("Administrator")

    def test_scope_disabled_falls_back_to_native_select_policy(self):
        self._set_scope_enforcement(False)
        user = self._make_user(("Accounts User",), scope_company=self.company)
        try:
            frappe.set_user(user)
            result = get_timesheet_employee_designation(self.employee)
            self.assertEqual(result["designation"], self.designation)
        finally:
            frappe.set_user("Administrator")

    def test_privileged_bypass_is_allowed(self):
        self._set_scope_enforcement(True)
        user = self._make_user(("Accounts User",), scope_company=self.company)
        try:
            frappe.set_user(user)
            frappe.db.delete("User Scope Context", {"user": user})
            with self.assertRaises(frappe.PermissionError):
                get_timesheet_employee_designation(self.employee)
        finally:
            frappe.set_user("Administrator")
            # The documented Administrator bypass still applies.
            result = get_timesheet_employee_designation(self.employee)
            self.assertEqual(result["designation"], self.designation)

    def test_scope_setting_read_failure_fails_closed(self):
        self._set_scope_enforcement(True)
        from construction.services import timesheet_designation as module

        original = module._scope_enabled_or_fail_closed

        def failing():
            raise frappe.PermissionError(
                "Security Error: Scope enforcement configuration could not be loaded."
            )

        module._scope_enabled_or_fail_closed = failing
        try:
            user = self._make_user(("Accounts User",), scope_company=self.company)
            frappe.set_user(user)
            with self.assertRaises(frappe.PermissionError):
                get_timesheet_employee_designation(self.employee)
        finally:
            module._scope_enabled_or_fail_closed = original
            frappe.set_user("Administrator")

    def test_employee_query_error_is_not_silently_allowed(self):
        self._set_scope_enforcement(True)
        user = self._make_user(("Accounts User",), scope_company=self.company)
        from construction.services import timesheet_designation as module

        original = module.get_employee_company

        def failing(employee):
            raise RuntimeError("employee lookup failed")

        module.get_employee_company = failing
        try:
            frappe.set_user(user)
            with self.assertRaises(RuntimeError):
                get_timesheet_employee_designation(self.employee)
        finally:
            module.get_employee_company = original
            frappe.set_user("Administrator")
