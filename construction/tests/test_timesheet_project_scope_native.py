"""Native regression for the Timesheet project scope (F44 TS2 correction).

A Timesheet stores its project on the parent under ``parent_project`` and on
every child row of ``time_logs``. The wildcard ``validate`` hook
(``construction/overrides/scope_enforcement.validate``) only sees the parent
document, so an ordinary scoped user could persist a Timesheet Detail row
that referenced a project outside the active scope.

This module exercises the REAL server save/submit lifecycle on a native
``Timesheet`` document: the assertions are about persisted rows and refused
operations, not about a model of the policy. The site-less policy coverage of
the same rule lives in ``construction/tests/test_timesheet_project_scope.py``.

Fixture setup and cleanup are owned by the suite.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from construction.tests.test_boq_helpers import get_or_create_test_project


class TimesheetProjectScopeNativeTests(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.scope_project = get_or_create_test_project()
        self.company = frappe.db.get_value("Project", self.scope_project, "company")
        self.other_project = self._make_project("_Test Construction Other Scope Project")
        self.employee = self._make_employee()
        self.activity_type = self._make_activity_type()
        self.user = self._make_user()
        self._set_scope_enforcement(True)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    # ---------------------------------------------------------------- fixtures

    def _make_project(self, label):
        existing = frappe.db.get_value("Project", {"project_name": label}, "name")
        if existing:
            return existing
        return (
            frappe.get_doc(
                {
                    "doctype": "Project",
                    "project_name": label,
                    "company": self.company,
                    "naming_series": "PROJ-.####",
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _make_employee(self):
        return (
            frappe.get_doc(
                {
                    "doctype": "Employee",
                    "employee_name": f"TS Scope Employee {frappe.generate_hash(length=5)}",
                    "first_name": "TS",
                    "last_name": "Scope",
                    "company": self.company,
                    "gender": "Other",
                    "date_of_joining": nowdate(),
                    "date_of_birth": nowdate(),
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _make_activity_type(self):
        existing = frappe.db.get_value("Activity Type", {"activity_type": "_Test TS Scope Activity"}, "name")
        if existing:
            return existing
        return (
            frappe.get_doc({"doctype": "Activity Type", "activity_type": "_Test TS Scope Activity"})
            .insert(ignore_permissions=True)
            .name
        )

    def _make_user(self):
        """An ordinary representative: Accounts User + Projects User.

        Fixture creation may use permission overrides; the tested save path
        always runs as this real user with real roles and a real scope context.
        """
        email = f"ts-scope-ctl-{frappe.generate_hash(length=8)}@example.invalid"
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "TS Scope Control",
                "send_welcome_email": 0,
                "roles": [{"role": "Accounts User"}, {"role": "Projects User"}],
            }
        ).insert(ignore_permissions=True)
        frappe.get_doc(
            {
                "doctype": "User Scope Context",
                "user": email,
                "company": self.company,
                "project": self.scope_project,
            }
        ).insert(ignore_permissions=True)
        return email

    @staticmethod
    def _set_scope_enforcement(enabled):
        frappe.db.set_single_value("Construction Settings", "enable_scope_context", 1 if enabled else 0)

    def _new_timesheet(self, rows, parent_project=None, company=None):
        """A native Timesheet with the given ``(project, from_time, hours)`` rows."""
        return frappe.get_doc(
            {
                "doctype": "Timesheet",
                "employee": self.employee,
                "company": company,
                "parent_project": parent_project,
                "time_logs": [
                    {
                        "doctype": "Timesheet Detail",
                        "activity_type": self.activity_type,
                        "from_time": from_time,
                        "hours": hours,
                        "project": project,
                    }
                    for project, from_time, hours in rows
                ],
            }
        )

    def _timesheet_count(self):
        return frappe.db.count("Timesheet")

    # ---------------------------------------------------- the reproduced defect

    def test_child_row_outside_the_active_project_is_refused(self):
        """The reproduced TS2 failure: blank parent, out-of-scope row project.

        This is the exact shape the qualified site persisted: company NULL,
        parent_project NULL, no BOQ attribution, one row pointing at a
        same-company project outside the active project scope.
        """
        frappe.set_user(self.user)
        before = self._timesheet_count()
        doc = self._new_timesheet([(self.other_project, "2026-01-05 09:00:00", 4)])
        with self.assertRaises(frappe.PermissionError) as ctx:
            doc.insert()
        self.assertIn("Scope boundary violation", str(ctx.exception))
        self.assertEqual(self._timesheet_count(), before, "a refused save must not persist a document")

    def test_child_row_outside_the_active_project_is_refused_on_update(self):
        """An existing draft may not be moved out of the active scope."""
        frappe.set_user(self.user)
        doc = self._new_timesheet([(self.scope_project, "2026-01-05 09:00:00", 4)])
        doc.insert()
        row_name = doc.time_logs[0].name
        doc.reload()
        doc.time_logs[0].project = self.other_project
        with self.assertRaises(frappe.PermissionError):
            doc.save()
        self.assertEqual(
            frappe.db.get_value("Timesheet Detail", row_name, "project"),
            self.scope_project,
            "a refused update must not change the stored row project",
        )

    def test_child_row_outside_the_active_project_is_refused_on_submit(self):
        """Submission is refused exactly like a draft save."""
        frappe.set_user(self.user)
        doc = self._new_timesheet([(self.scope_project, "2026-01-05 09:00:00", 4)])
        doc.insert()
        doc.reload()
        doc.time_logs[0].project = self.other_project
        with self.assertRaises(frappe.PermissionError):
            doc.submit()
        self.assertEqual(frappe.db.get_value("Timesheet", doc.name, "docstatus"), 0)

    def test_mixed_rows_refuse_the_whole_document(self):
        """One out-of-scope row refuses the whole document."""
        frappe.set_user(self.user)
        before = self._timesheet_count()
        doc = self._new_timesheet(
            [
                (self.scope_project, "2026-01-05 09:00:00", 4),
                (self.other_project, "2026-01-05 15:00:00", 4),
            ]
        )
        with self.assertRaises(frappe.PermissionError):
            doc.insert()
        self.assertEqual(self._timesheet_count(), before)

    def test_parent_project_alias_outside_the_active_project_is_refused(self):
        """The parent's ``parent_project`` alias carries the same boundary."""
        frappe.set_user(self.user)
        before = self._timesheet_count()
        doc = self._new_timesheet(
            [(self.other_project, "2026-01-05 09:00:00", 4)], parent_project=self.other_project
        )
        with self.assertRaises(frappe.PermissionError) as ctx:
            doc.insert()
        self.assertIn("Scope boundary violation", str(ctx.exception))
        self.assertEqual(self._timesheet_count(), before)

    # --------------------------------------------------------- same-scope pass

    def test_same_scope_child_row_is_saved_and_persisted(self):
        frappe.set_user(self.user)
        doc = self._new_timesheet([(self.scope_project, "2026-01-05 09:00:00", 4)])
        doc.insert()
        self.assertEqual(doc.docstatus, 0)
        self.assertEqual(
            frappe.db.get_value("Timesheet Detail", doc.time_logs[0].name, "project"), self.scope_project
        )

    def test_same_scope_timesheet_submits(self):
        frappe.set_user(self.user)
        doc = self._new_timesheet([(self.scope_project, "2026-01-05 09:00:00", 4)])
        doc.insert()
        doc.submit()
        self.assertEqual(doc.docstatus, 1)

    def test_a_timesheet_without_any_project_reference_is_unaffected(self):
        """A Timesheet that references no project keeps the previous behavior."""
        frappe.set_user(self.user)
        doc = self._new_timesheet([(None, "2026-01-05 09:00:00", 4)])
        doc.insert()
        self.assertEqual(doc.docstatus, 0)

    # ---------------------------------------------------------- bypass controls

    def test_ignore_permissions_is_not_a_scope_bypass(self):
        """``ignore_permissions`` never widens the active scope."""
        frappe.set_user(self.user)
        before = self._timesheet_count()
        doc = self._new_timesheet([(self.other_project, "2026-01-05 09:00:00", 4)])
        with self.assertRaises(frappe.PermissionError):
            doc.insert(ignore_permissions=True)
        self.assertEqual(self._timesheet_count(), before)

    def test_administrator_may_still_write_an_out_of_scope_timesheet(self):
        before = self._timesheet_count()
        doc = self._new_timesheet([(self.other_project, "2026-01-05 09:00:00", 4)])
        doc.insert(ignore_permissions=True)
        self.assertEqual(self._timesheet_count(), before + 1)

    def test_disabled_scope_context_is_preserved(self):
        self._set_scope_enforcement(False)
        frappe.set_user(self.user)
        doc = self._new_timesheet([(self.other_project, "2026-01-05 09:00:00", 4)])
        doc.insert()
        self.assertEqual(doc.docstatus, 0)

    def test_missing_active_context_refuses_a_child_only_timesheet(self):
        """A child-only Timesheet may not evade the active-context rule."""
        frappe.set_user(self.user)
        frappe.db.delete("User Scope Context", {"user": self.user})
        before = self._timesheet_count()
        doc = self._new_timesheet([(self.scope_project, "2026-01-05 09:00:00", 4)])
        with self.assertRaises(frappe.PermissionError) as ctx:
            doc.insert()
        self.assertIn("active User Scope Context is required", str(ctx.exception))
        self.assertEqual(self._timesheet_count(), before)
