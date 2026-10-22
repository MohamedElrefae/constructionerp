"""Timesheet direct-labor designation derivation (bounded TS correction).

The Timesheet Detail row field ``designation`` is the input the direct-labor BOQ
gate depends on (``depends_on: frappe.boot.direct_labor_designations.includes(doc.designation)``).
It is defined as a hidden, read-only field, so it can only be populated by a
trusted path.

Two paths exist, with different authorization:

* **Internal derivation** (:func:`derive_row_designations`) runs inside the
  already-authorized Timesheet save lifecycle. It reads the authoritative
  Employee designation on the server, so employee changes, employee clearing and
  stale/spoofed client values can never survive a save.
* **The public helper** (:func:`get_timesheet_employee_designation`) is used by
  the native employee-selection flow so the gate fields can appear before the
  first save. It is NOT a general Employee oracle: the caller must be permitted
  to use the Timesheet operation, must hold the native Employee ``select``
  permission for the specific record (the same policy ERPNext's
  ``get_activity_cost`` applies), and the record must sit inside the acting
  user's active scope under the application's own scope-enforcement policy
  (deny when scope is active and the caller has no scope context). Only the
  single designation string is returned.
"""

import frappe
from frappe import _

from construction.api.scope_context_api import get_user_scope_context
from construction.overrides.scope_enforcement import _scope_enabled_or_fail_closed


def get_employee_company(employee):
    """Company of an Employee (used by the scope boundary)."""
    if not employee:
        return None
    return frappe.db.get_value("Employee", employee, "company")


def get_employee_designation(employee):
    """Return the designation of an Employee (authoritative server-side read)."""
    if not employee:
        return None
    return frappe.db.get_value("Employee", employee, "designation")


def _privileged_bypass(user=None):
    """Documented privileged bypass, mirroring the document scope policy.

    Administrator, a System Manager and an explicit service-only bypass token
    (``frappe.flags.construction_scope_bypass``) may cross the scope boundary,
    exactly as the scoped-document enforcement allows.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    if "System Manager" in frappe.get_roles(user):
        return True
    return bool(getattr(frappe.flags, "construction_scope_bypass", False))


def assert_timesheet_operator():
    """The caller must be allowed to work on Timesheet documents."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted to use Timesheet."), frappe.PermissionError)
    if not (frappe.has_permission("Timesheet", "create") or frappe.has_permission("Timesheet", "read")):
        frappe.throw(_("Not permitted to use Timesheet."), frappe.PermissionError)


def assert_employee_selectable(employee):
    """Native Employee select policy for the specific record (ERPNext parity)."""
    if not frappe.has_permission("Employee", "select", doc=employee):
        frappe.throw(
            _("Not permitted to select Employee {0}.").format(employee),
            frappe.PermissionError,
        )


def assert_employee_in_scope(employee):
    """Apply the application's scope boundary to the selected Employee.

    Mirrors ``construction.overrides.scope_enforcement.validate``: a configuration
    read failure fails closed, a Guest or an ordinary user without an active
    scope context is denied while scope enforcement is active, and the employee's
    company must match the active scope company. Documented privileged bypasses
    (Administrator / System Manager / the service-only bypass token) are allowed.
    """
    if _privileged_bypass():
        return

    # Fail closed when the configuration cannot be read.
    enabled = _scope_enabled_or_fail_closed()
    if not enabled:
        # Scope enforcement is off: the native Employee select policy is the boundary.
        return

    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted to use Timesheet."), frappe.PermissionError)

    scope = get_user_scope_context(frappe.session.user)
    if not scope or not scope.company:
        frappe.throw(
            _("An active User Scope Context is required to select Employee {0}.").format(employee),
            frappe.PermissionError,
        )

    employee_company = get_employee_company(employee)
    if not employee_company:
        frappe.throw(
            _("Employee {0} has no company and cannot be used for BOQ attribution.").format(employee),
            frappe.PermissionError,
        )
    if employee_company != scope.company:
        frappe.throw(
            _("Scope boundary violation: Employee {0} does not match active user scope '{1}'.").format(
                employee, scope.company
            ),
            frappe.PermissionError,
        )


@frappe.whitelist()
def get_timesheet_employee_designation(employee):
    """Whitelisted helper for the native employee-selection flow.

    Authorization: Timesheet operation permission + native Employee ``select`` for
    that record + the active scope/company boundary. The response carries the
    designation string only.
    """
    assert_timesheet_operator()
    if not employee:
        return {"designation": None}
    assert_employee_selectable(employee)
    assert_employee_in_scope(employee)
    return {"designation": get_employee_designation(employee)}


def derive_row_designations(doc):
    """Re-derive ``designation`` on every Timesheet Detail row of a Timesheet.

    Called from the Timesheet validate hook (inside the authorized save
    lifecycle). The stored value is never trusted: it is always replaced by the
    designation of the currently selected employee, or cleared when there is no
    employee or no designation.
    """
    if not doc or doc.doctype != "Timesheet":
        return
    rows = doc.get("time_logs") or []
    if not rows:
        return

    employee = doc.get("employee")
    designation = get_employee_designation(employee) if employee else None
    for row in rows:
        if row.get("designation") != designation:
            row.designation = designation


def row_designation_mismatches(doc):
    """Rows whose stored designation does not match the selected employee.

    Used by the regression tests to prove that a stale or spoofed client value is
    never accepted (the derivation replaces it before the document is saved).
    """
    if not doc or doc.doctype != "Timesheet":
        return []
    employee = doc.get("employee")
    expected = get_employee_designation(employee) if employee else None
    return [
        row.idx
        for row in (doc.get("time_logs") or [])
        if frappe.utils.cstr(row.get("designation") or "") != frappe.utils.cstr(expected or "")
    ]
