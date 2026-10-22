"""F44 TS2 — the Timesheet project references must obey the active scope.

A Timesheet stores its project on the parent under ``parent_project`` and on
every child row of ``time_logs``. The wildcard ``validate`` hook
(``construction/overrides/scope_enforcement.validate``) only ever sees the
parent document, so the generic ``doc.project`` rule never fired for a
Timesheet. An ordinary scoped user could therefore persist a Timesheet Detail
row that referenced a project outside the active scope.

This module is SITE LESS on purpose: the policy is a decision over the
document's own scope references, so it is exercised without a site, without a
database and without any fixture. The PRODUCTION file
``construction/overrides/scope_enforcement.py`` is loaded directly with the
minimal dependencies stubbed, so every assertion runs against the real
production source in every environment (plain CPython, a bench venv, a site).

The native document/lifecycle counterpart of this coverage (a real
``Timesheet`` save and submit through the server lifecycle) lives in
``construction/tests/test_timesheet_project_scope_native.py``.

Run it with:
    python construction/tests/test_timesheet_project_scope.py -v
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = APP_ROOT / "construction" / "overrides" / "scope_enforcement.py"

STUBBED_MODULE_NAMES = (
    "frappe",
    "construction",
    "construction.api",
    "construction.api.scope_context_api",
    "construction.overrides",
    "construction.overrides.scope_enforcement",
)


class StubPermissionError(Exception):
    """Stand-in for ``frappe.PermissionError``."""


class StubFlags:
    """Stand-in for ``frappe.flags`` (the server-controlled bypass flags)."""

    def __init__(self):
        self.in_migrate = False
        self.in_install = False
        self.in_patch = False
        self.construction_scope_bypass = False


class StubLogger:
    def __init__(self):
        self.errors = []

    def error(self, message):
        self.errors.append(message)


class StubDb:
    """Minimal ``frappe.db`` with only the reads the policy performs."""

    def __init__(self):
        self.enable_scope_context = 1
        self.single_value_error = None
        self.project_companies = {}
        self.cost_centers = {}

    def get_single_value(self, doctype, fieldname):
        if self.single_value_error is not None:
            raise self.single_value_error
        if doctype == "Construction Settings" and fieldname == "enable_scope_context":
            return self.enable_scope_context
        return None

    def get_value(self, doctype, name, fieldname):
        if doctype == "Project":
            return self.project_companies.get(name)
        if doctype == "Cost Center":
            return self.cost_centers.get(name)
        if doctype == "Branch":
            return None
        return None


class StubSession:
    def __init__(self):
        self.user = "ordinary@example.invalid"


def _stub_frappe():
    frappe = types.ModuleType("frappe")
    frappe.PermissionError = StubPermissionError
    frappe._ = lambda text, *args, **kwargs: text
    frappe.flags = StubFlags()
    frappe.session = StubSession()
    frappe.db = StubDb()
    frappe.logger = lambda name=None: StubLogger()
    frappe.get_roles = lambda user=None: []

    def throw(message, exc=Exception, title=None):
        raise exc(message)

    frappe.throw = throw
    return frappe


class StubRow:
    """A child row (``Timesheet Detail``) with Frappe's ``get`` semantics."""

    def __init__(self, **values):
        self.__dict__.update(values)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)


class StubDoc:
    """A document stub with Frappe's attribute semantics.

    Only the declared attributes exist, so ``hasattr(doc, "project")`` is
    False for a Timesheet exactly as it is on a real Frappe Timesheet (the
    field does not exist there) and True for a doctype that has it.
    """

    def __init__(self, doctype, flags=None):
        self.doctype = doctype
        self.flags = {} if flags is None else flags

    def get(self, key, default=None):
        return getattr(self, key, default)


def make_timesheet(company=None, parent_project=None, row_projects=(), department=None, flags=None):
    """A Timesheet stub: no ``project`` field, only ``parent_project``/rows."""
    doc = StubDoc("Timesheet", flags=flags)
    doc.company = company
    doc.department = department
    doc.parent_project = parent_project
    doc.time_logs = [StubRow(project=value) for value in row_projects]
    return doc


def make_material_request(company=None, project=None, flags=None):
    """An unrelated doctype that carries a plain ``project`` field."""
    doc = StubDoc("Material Request", flags=flags)
    doc.company = company
    doc.project = project
    return doc


def load_scope_enforcement():
    """Load the PRODUCTION module with stubbed dependencies."""
    saved = {name: sys.modules.get(name) for name in STUBBED_MODULE_NAMES}

    construction = types.ModuleType("construction")
    construction.__path__ = []
    api = types.ModuleType("construction.api")
    api.__path__ = []
    overrides = types.ModuleType("construction.overrides")
    overrides.__path__ = []

    scope_api = types.ModuleType("construction.api.scope_context_api")
    scope_api.get_user_scope_context = lambda user=None: scope_api.scope
    scope_api.get_allowed_scope_dimensions = lambda user=None: {}
    scope_api.scope = None

    sys.modules["frappe"] = _stub_frappe()
    sys.modules["construction"] = construction
    sys.modules["construction.api"] = api
    sys.modules["construction.api.scope_context_api"] = scope_api
    sys.modules["construction.overrides"] = overrides

    try:
        spec = importlib.util.spec_from_file_location("construction.overrides.scope_enforcement", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules["construction.overrides.scope_enforcement"] = module
        spec.loader.exec_module(module)
        return module, scope_api
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


class TimesheetProjectScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.scope_api = load_scope_enforcement()

    def setUp(self):
        self.frappe = self.module.frappe
        self.frappe.session.user = "ordinary@example.invalid"
        self.frappe.get_roles = lambda user=None: []
        self.frappe.flags = StubFlags()
        self.frappe.db.enable_scope_context = 1
        self.frappe.db.single_value_error = None
        self.frappe.db.project_companies = {
            "PROJ-A": "Company-A",
            "PROJ-A2": "Company-A",
            "PROJ-B": "Company-B",
        }
        self.scope_api.scope = self._scope("Company-A", "PROJ-A")

    @staticmethod
    def _scope(company=None, project=None):
        return types.SimpleNamespace(company=company, project=project, cost_center=None, department=None)

    def _validate(self, doc):
        return self.module.validate(doc, "validate")

    def _assert_denied(self, doc):
        with self.assertRaises(StubPermissionError) as ctx:
            self._validate(doc)
        return str(ctx.exception)

    def _assert_allowed(self, doc):
        self._validate(doc)  # raises on refusal

    # ---------------------------------------------------- the failing case

    def test_child_only_row_outside_the_active_project_is_denied(self):
        """The reproduced TS2 failure: blank parent, out-of-scope row project.

        This is the exact shape the qualified site persisted: company NULL,
        parent_project NULL, no BOQ attribution, one row pointing at a
        same-company project outside the active project scope.
        """
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2"])
        message = self._assert_denied(doc)
        self.assertIn("PROJ-A2", message)
        self.assertIn("PROJ-A", message)

    def test_child_only_row_outside_the_active_project_is_not_silently_allowed(self):
        """The refusal must be a scope refusal, not an unrelated error."""
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2"])
        with self.assertRaises(StubPermissionError):
            self._validate(doc)

    # ------------------------------------------------------- same-scope pass

    def test_same_scope_child_row_is_allowed(self):
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A"])
        self._assert_allowed(doc)

    def test_same_scope_header_and_row_are_allowed(self):
        doc = make_timesheet(company="Company-A", parent_project="PROJ-A", row_projects=["PROJ-A", "PROJ-A"])
        self._assert_allowed(doc)

    def test_timesheet_without_any_project_reference_is_unchanged(self):
        """A Timesheet that references no project keeps the previous behavior."""
        doc = make_timesheet(company="Company-A", parent_project=None, row_projects=[])
        self._assert_allowed(doc)

    # ------------------------------------------------------ mixed / atomic

    def test_mixed_rows_fail_atomically(self):
        """One out-of-scope row refuses the whole document."""
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A", "PROJ-A2", "PROJ-A"])
        message = self._assert_denied(doc)
        self.assertIn("PROJ-A2", message)

    def test_mixed_rows_refuse_before_the_in_scope_rows_are_trusted(self):
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2", "PROJ-A"])
        self._assert_denied(doc)

    # ------------------------------------------------- parent_project alias

    def test_parent_project_alias_outside_the_active_project_is_denied(self):
        doc = make_timesheet(company=None, parent_project="PROJ-A2", row_projects=[])
        message = self._assert_denied(doc)
        self.assertIn("PROJ-A2", message)

    def test_parent_project_alias_inside_the_active_project_is_allowed(self):
        doc = make_timesheet(company=None, parent_project="PROJ-A", row_projects=[])
        self._assert_allowed(doc)

    def test_parent_project_alias_is_denied_even_with_a_matching_row(self):
        doc = make_timesheet(company=None, parent_project="PROJ-A2", row_projects=["PROJ-A"])
        self._assert_denied(doc)

    # ------------------------------------------------ active context needed

    def test_missing_active_context_with_child_only_fields_is_denied(self):
        """A child-only Timesheet must not evade the active-context rule."""
        self.scope_api.scope = None
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A"])
        message = self._assert_denied(doc)
        self.assertIn("active User Scope Context is required", message)

    def test_missing_active_context_with_parent_project_alias_is_denied(self):
        self.scope_api.scope = None
        doc = make_timesheet(company=None, parent_project="PROJ-A", row_projects=[])
        self._assert_denied(doc)

    def test_active_context_without_company_is_denied(self):
        self.scope_api.scope = self._scope(company=None, project="PROJ-A")
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A"])
        self._assert_denied(doc)

    # ----------------------------------------------- company-only active scope

    def test_company_only_scope_allows_a_project_of_the_active_company(self):
        self.scope_api.scope = self._scope(company="Company-A", project=None)
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2"])
        self._assert_allowed(doc)

    def test_company_only_scope_denies_a_cross_company_project(self):
        """A blank document company must not carry a cross-company project."""
        self.scope_api.scope = self._scope(company="Company-A", project=None)
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-B"])
        message = self._assert_denied(doc)
        self.assertIn("Company-B", message)
        self.assertIn("Company-A", message)

    def test_company_only_scope_denies_a_cross_company_header_alias(self):
        self.scope_api.scope = self._scope(company="Company-A", project=None)
        doc = make_timesheet(company=None, parent_project="PROJ-B", row_projects=[])
        self._assert_denied(doc)

    def test_company_only_scope_denies_an_unreadable_project_company(self):
        """An unverifiable reference fails closed."""
        self.scope_api.scope = self._scope(company="Company-A", project=None)
        self.frappe.db.project_companies = {}
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2"])
        self._assert_denied(doc)

    # -------------------------------------------------------- bypass controls

    def test_ignore_permissions_is_not_a_bypass(self):
        """``doc.flags.ignore_permissions`` must never widen the scope."""
        doc = make_timesheet(
            company=None, parent_project=None, row_projects=["PROJ-A2"], flags={"ignore_permissions": True}
        )
        self._assert_denied(doc)

    def test_administrator_is_allowed(self):
        self.frappe.session.user = "Administrator"
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2"])
        self._assert_allowed(doc)

    def test_system_manager_is_allowed(self):
        self.frappe.get_roles = lambda user=None: ["System Manager"]
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2"])
        self._assert_allowed(doc)

    def test_explicit_server_only_bypass_is_allowed(self):
        self.frappe.flags.construction_scope_bypass = True
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2"])
        self._assert_allowed(doc)

    def test_install_migrate_and_patch_exemptions_are_preserved(self):
        for flag in ("in_install", "in_migrate", "in_patch"):
            with self.subTest(flag=flag):
                flags = StubFlags()
                setattr(flags, flag, True)
                self.frappe.flags = flags
                doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2"])
                self._assert_allowed(doc)

    def test_disabled_scope_context_is_preserved(self):
        self.frappe.db.enable_scope_context = 0
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2"])
        self._assert_allowed(doc)

    def test_configuration_read_failure_fails_closed(self):
        self.frappe.db.single_value_error = RuntimeError("settings unreadable")
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A2"])
        message = self._assert_denied(doc)
        self.assertIn("Scope enforcement configuration could not be loaded", message)

    def test_guest_cannot_write_a_scoped_timesheet(self):
        self.frappe.session.user = "Guest"
        doc = make_timesheet(company=None, parent_project=None, row_projects=["PROJ-A"])
        self._assert_denied(doc)

    # ------------------------------------------------- unrelated doctypes

    def test_unrelated_doctype_project_boundary_is_unchanged(self):
        doc = make_material_request(company="Company-A", project="PROJ-A")
        self._assert_allowed(doc)

    def test_unrelated_doctype_out_of_scope_project_is_still_denied(self):
        doc = make_material_request(company="Company-A", project="PROJ-A2")
        message = self._assert_denied(doc)
        self.assertIn("PROJ-A2", message)

    def test_unrelated_doctype_company_boundary_is_unchanged(self):
        doc = make_material_request(company="Company-B", project="PROJ-A")
        self._assert_denied(doc)

    def test_unrelated_doctype_without_scope_fields_is_unchanged(self):
        self.scope_api.scope = None
        doc = make_material_request(company=None, project=None)
        self._assert_allowed(doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
