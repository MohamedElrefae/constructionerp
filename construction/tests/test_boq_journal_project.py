"""F44 — Journal Entry BOQ project propagation (site-less policy coverage).

A Journal Entry Account row that carries a BOQ attribution (``boq_item``)
belongs to the project of the selected BOQ Header, but the native ERPNext
controller copies the ROW's ``project`` into the General Ledger entry. A BOQ
expense row saved with a blank row project therefore produced a posted GL
entry with ``project = NULL``: the cost was invisible in the project-scoped
General Ledger while the voucher itself stayed balanced.

This module is SITE LESS on purpose: the policy is a decision over the
document's own BOQ chain, the authoritative project authorities, the PERSISTED
row state and the active scope context, so it is exercised without a site,
without a database and without any fixture. The PRODUCTION files are loaded
directly with the minimal dependencies stubbed, so every assertion runs against
the real production source in every environment (plain CPython, a bench venv, a
site):

* ``construction/services/boq_journal_project.py`` (the bounded correction),
* ``construction/services/boq_transaction_validation.py`` and
  ``construction/services/boq_accounting.py`` (the EXISTING shared path, whose
  behaviour must stay unchanged, including the parent-bound historical
  predicate ``is_new_or_changed_attribution``),
* ``construction/services/scope_resolution.py`` and
  ``construction/overrides/scope_enforcement.py`` (the EXISTING scope
  semantics and the fail-closed scope configuration),
* ``construction/services/boq_scope_registry.py`` (the EXISTING transaction
  registry that names the child table of every registered DocType).

The Journal Entry ``validate`` chain is read from the REAL ``hooks.py``
binding, so the bound-order test proves the shipped wiring and not a copy of
it.

The native document/lifecycle counterpart of this coverage (a real Journal
Entry save, submit and cancel with the persisted row and GL project) lives in
``construction/tests/test_boq_journal_project_native.py``.

Run it with:
    python construction/tests/test_boq_journal_project.py -v
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
HOOKS_PATH = APP_ROOT / "construction" / "hooks.py"
JOURNAL_MODULE_PATH = APP_ROOT / "construction" / "services" / "boq_journal_project.py"

STUBBED_MODULE_NAMES = (
    "frappe",
    "frappe.utils",
    "construction",
    "construction.api",
    "construction.api.scope_context_api",
    "construction.construction",
    "construction.construction.utils",
    "construction.overrides",
    "construction.overrides.scope_enforcement",
    "construction.services",
    "construction.services.boq_accounting",
    "construction.services.boq_journal_project",
    "construction.services.boq_lookups",
    "construction.services.boq_scope_filters",
    "construction.services.boq_scope_registry",
    "construction.services.boq_transaction_validation",
    "construction.services.feature_flags",
    "construction.services.scope_resolution",
)


# --------------------------------------------------------------------------
# Frappe stubs
# --------------------------------------------------------------------------


class StubValidationError(Exception):
    """Stand-in for ``frappe.ValidationError``."""


class StubPermissionError(Exception):
    """Stand-in for ``frappe.PermissionError``, separate from ValidationError."""


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


class StubSession:
    def __init__(self):
        self.user = "ordinary@example.invalid"


class AttrDict(dict):
    """A ``as_dict=True`` result with attribute access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise AttributeError(name) from exc


class StubDB:
    """Minimal ``frappe.db`` with only the reads the production policy performs.

    The fixture data is a plain in-memory table, so the production lookups
    (``frappe.db.get_value`` / ``frappe.db.exists``) are exercised for real
    against the data the test sets up.
    """

    def __init__(self):
        self.rows = {}
        self.singles = {}
        self.single_value_error = None

    # -- fixture helpers ---------------------------------------------------

    def add(self, doctype, name, **fields):
        self.rows[(doctype, name)] = dict(fields)
        return name

    def set_single(self, doctype, fieldname, value):
        self.singles[(doctype, fieldname)] = value

    def reset(self):
        self.rows = {}
        self.singles = {}
        self.single_value_error = None

    # -- frappe.db API -----------------------------------------------------

    def exists(self, doctype, name=None, filters=None):
        if isinstance(name, dict):
            filters = name
            name = None
        if name is not None:
            return (doctype, name) in self.rows
        if filters:
            return any(
                self._matches(fields, filters)
                for (row_doctype, _row_name), fields in self.rows.items()
                if row_doctype == doctype
            )
        return False

    def get_value(self, doctype, name=None, fieldname=None, as_dict=False, filters=None, **kwargs):
        if isinstance(name, dict):
            filters = name
            name = None
        fields = self._find(doctype, name, filters)
        if fields is None:
            return None
        if isinstance(fieldname, list | tuple):
            if as_dict:
                return AttrDict({field: fields.get(field) for field in fieldname})
            return [fields.get(field) for field in fieldname]
        return fields.get(fieldname)

    def get_single_value(self, doctype, fieldname):
        if self.single_value_error is not None:
            raise self.single_value_error
        return self.singles.get((doctype, fieldname))

    def set_single_value(self, doctype, fieldname, value):
        self.set_single(doctype, fieldname, value)

    # -- internals ---------------------------------------------------------

    def _find(self, doctype, name, filters):
        if name is not None:
            return self.rows.get((doctype, name))
        if filters:
            for (row_doctype, _row_name), fields in self.rows.items():
                if row_doctype == doctype and self._matches(fields, filters):
                    return fields
        return None

    @staticmethod
    def _matches(fields, filters):
        return all(fields.get(key) == value for key, value in filters.items())


def _stub_frappe():
    frappe = types.ModuleType("frappe")
    frappe.ValidationError = StubValidationError
    frappe.PermissionError = StubPermissionError
    frappe._ = lambda text, *args, **kwargs: text
    frappe.flags = StubFlags()
    frappe.session = StubSession()
    frappe.db = StubDB()
    frappe.logger = lambda name=None: StubLogger()
    frappe.get_roles = lambda user=None: []
    frappe.get_all = lambda *args, **kwargs: []
    frappe.get_cached_value = lambda doctype, name, fieldname, as_dict=False: frappe.db.get_value(
        doctype, name, fieldname, as_dict=as_dict
    )

    def throw(message, exc=None, title=None):
        raise (exc or frappe.ValidationError)(message)

    frappe.throw = throw

    frappe.utils = types.ModuleType("frappe.utils")
    frappe.utils.flt = lambda value, precision=None: float(value or 0)
    return frappe


class StubRow:
    """A child row (``Journal Entry Account``) with Frappe's ``get`` semantics."""

    def __init__(self, **values):
        self.__dict__.update(values)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)


class StubField:
    def __init__(self, options):
        self.options = options


class StubMeta:
    """The child-doctype metadata the historical predicate reads."""

    def __init__(self, table_field="accounts", child_doctype="Journal Entry Account"):
        self.table_field = table_field
        self.child_doctype = child_doctype

    def get_field(self, fieldname):
        if fieldname == self.table_field:
            return StubField(self.child_doctype)
        return None


class StubDoc:
    """A document stub with Frappe's attribute semantics.

    Only the declared attributes exist, so ``hasattr(doc, "project")`` is False
    for a Journal Entry exactly as it is on a real Frappe Journal Entry (the
    field does not exist there).
    """

    def __init__(self, doctype, **values):
        self.doctype = doctype
        self.__dict__.update(values)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)


# --------------------------------------------------------------------------
# Production module loading
# --------------------------------------------------------------------------


class LoadedModules:
    """The loaded production modules and the stubbed ``frappe``."""

    def __init__(self, frappe, **modules):
        self.frappe = frappe
        self.__dict__.update(modules)

    @property
    def journal_project(self):
        return self.__dict__.get("boq_journal_project")

    @property
    def journal_project_error(self):
        return self.__dict__.get("boq_journal_project_error")


def _stub_package(name):
    package = types.ModuleType(name)
    package.__path__ = []
    return package


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_production_modules():
    """Load the REAL production modules with a stubbed ``frappe``."""
    saved = {name: sys.modules.get(name) for name in STUBBED_MODULE_NAMES}

    frappe = _stub_frappe()
    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = frappe.utils

    for name in (
        "construction",
        "construction.api",
        "construction.construction",
        "construction.construction.utils",
        "construction.overrides",
        "construction.services",
    ):
        sys.modules[name] = _stub_package(name)

    scope_api = types.ModuleType("construction.api.scope_context_api")
    scope_api.get_user_scope_context = lambda user=None: None
    scope_api.get_allowed_scope_dimensions = lambda user=None: {}
    sys.modules["construction.api.scope_context_api"] = scope_api

    services = APP_ROOT / "construction" / "services"
    overrides = APP_ROOT / "construction" / "overrides"

    try:
        _load_module("construction.services.scope_resolution", services / "scope_resolution.py")
        _load_module("construction.services.boq_scope_filters", services / "boq_scope_filters.py")
        _load_module("construction.services.feature_flags", services / "feature_flags.py")
        _load_module("construction.services.boq_scope_registry", services / "boq_scope_registry.py")
        _load_module("construction.services.boq_lookups", services / "boq_lookups.py")
        _load_module("construction.services.boq_accounting", services / "boq_accounting.py")
        _load_module(
            "construction.services.boq_transaction_validation",
            services / "boq_transaction_validation.py",
        )
        _load_module("construction.overrides.scope_enforcement", overrides / "scope_enforcement.py")

        journal_project = None
        journal_project_error = None
        if JOURNAL_MODULE_PATH.is_file():
            journal_project = _load_module("construction.services.boq_journal_project", JOURNAL_MODULE_PATH)
        else:
            journal_project_error = (
                "construction/services/boq_journal_project.py is absent: this tree has no "
                "Journal Entry BOQ project helper (the baseline source)."
            )

        return LoadedModules(
            frappe=frappe,
            boq_accounting=sys.modules["construction.services.boq_accounting"],
            boq_lookups=sys.modules["construction.services.boq_lookups"],
            boq_scope_registry=sys.modules["construction.services.boq_scope_registry"],
            boq_transaction_validation=sys.modules["construction.services.boq_transaction_validation"],
            scope_enforcement=sys.modules["construction.overrides.scope_enforcement"],
            scope_resolution=sys.modules["construction.services.scope_resolution"],
            boq_journal_project=journal_project,
            boq_journal_project_error=journal_project_error,
        )
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


_LOADED = None


def load_production_modules():
    """Load (once) and return the production modules under test."""
    global _LOADED
    if _LOADED is None:
        _LOADED = _load_production_modules()
    return _LOADED


# --------------------------------------------------------------------------
# The real Journal Entry validate binding (construction/hooks.py)
# --------------------------------------------------------------------------


def journal_entry_validate_handlers(hooks_path=HOOKS_PATH):
    """The Journal Entry ``validate`` handlers, in the real bound order."""
    tree = ast.parse(hooks_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "doc_events" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values, strict=True):
            if getattr(key, "value", None) != "Journal Entry" or not isinstance(value, ast.Dict):
                continue
            for event_key, event_value in zip(value.keys, value.values, strict=True):
                if getattr(event_key, "value", None) != "validate":
                    continue
                if isinstance(event_value, ast.Constant):
                    return [event_value.value]
                if isinstance(event_value, ast.List | ast.Tuple):
                    return [element.value for element in event_value.elts]
    raise AssertionError("construction/hooks.py has no Journal Entry validate binding")


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

# The production modules a bound Journal Entry validate handler may live in.
HANDLER_MODULES = {
    "construction.services.boq_transaction_validation": "boq_transaction_validation",
    "construction.services.boq_journal_project": "boq_journal_project",
}

BOQ_PROJECT = "PROJ-A"
SAME_COMPANY_OTHER_PROJECT = "PROJ-A2"
OTHER_COMPANY_PROJECT = "PROJ-B"
THIRD_COMPANY_PROJECT = "PROJ-C"
COMPANY = "Company-A"
OTHER_COMPANY = "Company-B"
THIRD_COMPANY = "Company-C"


def seed_world(db):
    """The authoritative BOQ chain, project authorities and scope context."""
    db.add("DocType", "User Scope Context")
    db.add("Project", BOQ_PROJECT, company=COMPANY)
    db.add("Project", SAME_COMPANY_OTHER_PROJECT, company=COMPANY)
    db.add("Project", OTHER_COMPANY_PROJECT, company=OTHER_COMPANY)
    db.add("Project", THIRD_COMPANY_PROJECT, company=THIRD_COMPANY)
    db.add("BOQ Header", "HDR-1", project=BOQ_PROJECT, status="Frozen")
    db.add("BOQ Header", "HDR-2", project=OTHER_COMPANY_PROJECT, status="Frozen")
    db.add("BOQ Header", "HDR-3", project=SAME_COMPANY_OTHER_PROJECT, status="Frozen")
    db.add("BOQ Header", "HDR-4", project=THIRD_COMPANY_PROJECT, status="Frozen")
    db.add("BOQ Header", "HDR-0", project=None, status="Frozen")
    db.add("BOQ Item", "ITEM-1", boq_header="HDR-1", structure="STR-1", quantity=10)
    db.add("BOQ Item", "ITEM-2", boq_header="HDR-2", structure="STR-2", quantity=10)
    db.add("BOQ Item", "ITEM-3", boq_header="HDR-3", structure="STR-3", quantity=10)
    db.add("BOQ Item", "ITEM-4", boq_header="HDR-4", structure="STR-4", quantity=10)
    db.add("BOQ Item", "ITEM-0", boq_header="HDR-0", structure="STR-0", quantity=10)
    db.add("BOQ Item", "ITEM-NH", boq_header=None, structure="STR-NH", quantity=10)
    db.add(
        "User Scope Context",
        "SC-1",
        user="ordinary@example.invalid",
        company=COMPANY,
        cost_center=None,
        project=BOQ_PROJECT,
        modified=None,
    )
    db.set_single("Construction Settings", "enable_scope_context", 1)
    db.set_single("Construction Settings", "enable_boq_scope_registry", 1)


def make_journal_entry(rows, company=COMPANY, name=None, doctype="Journal Entry"):
    """A Journal Entry stub: a company, no parent ``project`` field."""
    doc = StubDoc(doctype, meta=StubMeta(), name=name, company=company)
    doc.accounts = list(rows)
    return doc


def make_row(**values):
    """A Journal Entry Account row stub."""
    values.setdefault("idx", 1)
    values.setdefault("doctype", "Journal Entry Account")
    # A real Journal Entry Account always carries the ``project`` field; its
    # value may be empty, the field itself is never missing.
    values.setdefault("project", None)
    return StubRow(**values)


def make_registry_doc(rule, row, project=None, name=None):
    """A document of a registered transaction DocType with one child row."""
    doc = StubDoc(
        rule.doctype,
        meta=StubMeta(rule.child_table, rule.child_doctype),
        name=name or f"{rule.doctype}-1",
        company=COMPANY,
    )
    if project:
        # A Journal Entry has NO parent ``project`` field; every other
        # registered transaction DocType carries one.
        doc.project = project
    setattr(doc, rule.child_table, [row])
    return doc


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


class BoqJournalProjectTestCase(unittest.TestCase):
    """Shared fixture state for the site-less coverage."""

    @classmethod
    def setUpClass(cls):
        cls.modules = load_production_modules()
        cls.frappe = cls.modules.frappe

    def setUp(self):
        self.db = self.frappe.db
        self.db.reset()
        seed_world(self.db)
        self.frappe.session.user = "ordinary@example.invalid"
        self.frappe.get_roles = lambda user=None: []
        self.frappe.flags = StubFlags()

    # -- helpers -----------------------------------------------------------

    def _journal_helper(self):
        module = self.modules.journal_project
        if module is None:
            self.fail(self.modules.journal_project_error)
        return module

    def _run_chain(self, doc):
        """Run the REAL bound Journal Entry validate chain."""
        for handler in journal_entry_validate_handlers():
            module_name, _, function_name = handler.rpartition(".")
            attribute = HANDLER_MODULES.get(module_name)
            if attribute is None:
                self.fail(f"the bound handler {handler} is not loadable in this harness")
            module = self.modules.__dict__.get(attribute)
            if module is None:
                self.fail(f"the bound handler {handler} is not loadable in this harness")
            getattr(module, function_name)(doc)

    def _assert_denied(self, doc, expected=None, permission=False):
        with self.assertRaises(StubPermissionError if permission else StubValidationError) as ctx:
            self._journal_helper().validate_document(doc)
        message = str(ctx.exception)
        if expected:
            self.assertIn(expected, message)
        if not permission:
            self.assertNotIn("Scope boundary violation", message)
        return message

    def _store_row(self, name="ROW-1", boq_item="ITEM-1", project=None, parent="JE-1"):
        """A PERSISTED Journal Entry Account row of the parent ``JE-1``."""
        self.db.add(
            "Journal Entry Account",
            name,
            boq_item=boq_item,
            project=project,
            parent=parent,
            parenttype="Journal Entry",
            parentfield="accounts",
        )
        return name


class BoundJournalEntryHookChainTests(BoqJournalProjectTestCase):
    """The chain that is actually BOUND in ``construction/hooks.py``.

    These tests run the real handlers in the real order, so they work on a tree
    that has the bounded correction AND on a tree that does not (the baseline),
    which is what makes the fail-before / pass-after control meaningful.
    """

    def test_the_bound_chain_derives_the_authoritative_boq_project(self):
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row])
        self._run_chain(doc)
        self.assertEqual(
            row.project,
            BOQ_PROJECT,
            "the bound Journal Entry validate chain must derive the authoritative BOQ project",
        )

    def test_the_bound_chain_keeps_the_unattributed_row_unattributed(self):
        boq_row = make_row(idx=1, boq_item="ITEM-1")
        cash_row = make_row(idx=2, account="Cash - ACC")
        doc = make_journal_entry([boq_row, cash_row])
        self._run_chain(doc)
        self.assertEqual(boq_row.project, BOQ_PROJECT)
        self.assertIsNone(cash_row.project, "a row without a BOQ attribution keeps the native project")

    def test_the_bound_chain_refuses_an_explicit_project_mismatch(self):
        row = make_row(boq_item="ITEM-1", project=SAME_COMPANY_OTHER_PROJECT)
        doc = make_journal_entry([row])
        with self.assertRaises(StubValidationError) as ctx:
            self._run_chain(doc)
        self.assertIn("Project mismatch", str(ctx.exception))

    def test_the_bound_chain_keeps_an_assigned_project_that_a_later_save_arrives_without(self):
        """C1 regression, executed through the REAL bound chain.

        The persisted row of THIS parent carries the authoritative project; a
        later draft save arrives with a blank row project. The assigned project
        must not be lost.
        """
        self._store_row(project=BOQ_PROJECT)
        row = make_row(name="ROW-1", boq_item="ITEM-1")
        doc = make_journal_entry([row], name="JE-1")
        self._run_chain(doc)
        self.assertEqual(
            row.project,
            BOQ_PROJECT,
            "a later save must not clear an already assigned project",
        )


class SharedBoqValidatorRegressionTests(BoqJournalProjectTestCase):
    """The EXISTING shared BOQ path must stay byte-for-byte equivalent.

    The shared validator is used by eight registered transaction DocTypes. It
    normalizes the BOQ chain and refuses a project mismatch, but it never
    DERIVES a row project: that is the defect this bounded correction fixes for
    the Journal Entry only. These tests pin the shared behaviour, so a change
    to the shared path (which would change the other seven DocTypes) fails
    here.
    """

    def test_the_shared_validator_does_not_derive_a_row_project(self):
        """The reproduced defect: the existing path leaves the row project NULL."""
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row])
        self.modules.boq_transaction_validation.validate_document(doc)
        self.assertIsNone(
            row.project,
            "the shared validator must keep deriving nothing: the derivation is Journal Entry only",
        )
        self.assertEqual(row.boq_header, "HDR-1")
        self.assertEqual(row.boq_structure, "STR-1")

    def test_the_shared_validator_still_refuses_a_project_mismatch(self):
        row = make_row(boq_item="ITEM-1", project=SAME_COMPANY_OTHER_PROJECT)
        doc = make_journal_entry([row])
        with self.assertRaises(StubValidationError) as ctx:
            self.modules.boq_transaction_validation.validate_document(doc)
        self.assertIn("Project mismatch", str(ctx.exception))

    def test_the_shared_validator_derives_nothing_for_every_registered_doctype(self):
        """Policy-level regression over the REAL transaction registry.

        This is a POLICY check on the shared validator: it never writes a row
        project for any registered transaction DocType. It is NOT a stored-row
        or persistence proof for the other seven DocTypes: this site-less suite
        never writes a database row for them.
        """
        rules = self.modules.boq_scope_registry.SUPPORTED_TRANSACTION_RULES
        self.assertGreaterEqual(len(rules), 8, "the registry must name every transaction DocType")
        for rule in rules:
            with self.subTest(doctype=rule.doctype):
                row = make_row(boq_item="ITEM-1", doctype=rule.child_doctype)
                # A Journal Entry carries no parent project field.
                project = None if rule.doctype == "Journal Entry" else BOQ_PROJECT
                doc = make_registry_doc(rule, row, project=project)
                self.modules.boq_transaction_validation.validate_document(doc)
                self.assertIsNone(
                    row.project,
                    "the shared path must not write a row project for any registered DocType",
                )

    def test_the_journal_entry_helper_leaves_every_other_registered_doctype_untouched(self):
        """The correction is Journal Entry only, across the REAL registry."""
        for rule in self.modules.boq_scope_registry.SUPPORTED_TRANSACTION_RULES:
            if rule.doctype == "Journal Entry":
                continue
            with self.subTest(doctype=rule.doctype):
                row = make_row(boq_item="ITEM-1", doctype=rule.child_doctype)
                doc = make_registry_doc(rule, row, project=BOQ_PROJECT)
                self._journal_helper().validate_document(doc)
                self.assertIsNone(row.project, "the correction is Journal Entry only")


class JournalEntryBoqProjectPolicyTests(BoqJournalProjectTestCase):
    """The bounded Journal Entry correction itself."""

    # -- derivation --------------------------------------------------------

    def test_new_row_with_a_blank_project_derives_the_authoritative_boq_project(self):
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row])
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, BOQ_PROJECT)

    def test_an_explicit_matching_project_is_preserved(self):
        row = make_row(boq_item="ITEM-1", project=BOQ_PROJECT)
        doc = make_journal_entry([row])
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, BOQ_PROJECT)

    def test_an_explicit_mismatched_project_is_refused(self):
        row = make_row(boq_item="ITEM-1", project=SAME_COMPANY_OTHER_PROJECT)
        doc = make_journal_entry([row])
        message = self._assert_denied(doc, "Project mismatch")
        self.assertIn(SAME_COMPANY_OTHER_PROJECT, message)

    def test_a_crafted_indirect_row_with_a_boq_item_is_attributed(self):
        """The attribution predicate is a non-empty ``boq_item``.

        The Journal Entry Direct/Indirect gate is NOT enforced server-side
        today; this correction does not add it, so a crafted row labelled
        ``Indirect`` that carries a BOQ item is attributed like any other
        BOQ-bearing row.
        """
        row = make_row(boq_item="ITEM-1", expense_category="Indirect")
        doc = make_journal_entry([row])
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, BOQ_PROJECT)

    def test_a_row_without_a_boq_attribution_keeps_the_native_project(self):
        row = make_row(account="Cash - ACC")
        doc = make_journal_entry([row])
        self._journal_helper().validate_document(doc)
        self.assertIsNone(row.project)

    def test_a_document_without_rows_is_untouched(self):
        doc = make_journal_entry([])
        self._journal_helper().validate_document(doc)
        self.assertEqual(doc.accounts, [])

    def test_another_doctype_is_not_touched(self):
        rule = next(
            rule
            for rule in self.modules.boq_scope_registry.SUPPORTED_TRANSACTION_RULES
            if rule.doctype == "Purchase Order"
        )
        row = make_row(boq_item="ITEM-1", doctype=rule.child_doctype)
        doc = make_registry_doc(rule, row, project=BOQ_PROJECT)
        self._journal_helper().validate_document(doc)
        self.assertIsNone(row.project, "the correction is Journal Entry only")

    # -- authoritative authorities -----------------------------------------

    def test_a_boq_header_without_a_project_is_refused(self):
        row = make_row(boq_item="ITEM-0")
        doc = make_journal_entry([row])
        self._assert_denied(doc, "BOQ attribution is incomplete")

    def test_a_boq_item_without_a_header_is_refused(self):
        row = make_row(boq_item="ITEM-NH")
        doc = make_journal_entry([row])
        self._assert_denied(doc, "BOQ attribution is incomplete")

    def test_an_unreadable_project_company_is_refused(self):
        del self.db.rows[("Project", BOQ_PROJECT)]
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row])
        self._assert_denied(doc, "does not belong to Company")

    def test_a_missing_document_company_is_refused(self):
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row], company=None)
        self._assert_denied(doc, "Company is required")

    def test_a_cross_company_boq_project_is_refused_on_the_first_save(self):
        row = make_row(boq_item="ITEM-2")
        doc = make_journal_entry([row])
        message = self._assert_denied(doc, "does not belong to Company")
        self.assertIn(OTHER_COMPANY_PROJECT, message)
        self.assertIn(COMPANY, message)

    # -- the active scope boundary ----------------------------------------

    def test_an_out_of_scope_project_is_refused(self):
        row = make_row(boq_item="ITEM-3")
        doc = make_journal_entry([row])
        message = self._assert_denied(doc, "Scope boundary violation", permission=True)
        self.assertIn(SAME_COMPANY_OTHER_PROJECT, message)

    def test_the_active_scope_project_is_accepted(self):
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row])
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, BOQ_PROJECT)

    def test_a_company_only_scope_accepts_a_same_company_project(self):
        self.db.add(
            "User Scope Context",
            "SC-1",
            user="ordinary@example.invalid",
            company=COMPANY,
            cost_center=None,
            project=None,
            modified=None,
        )
        row = make_row(boq_item="ITEM-3")
        doc = make_journal_entry([row])
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, SAME_COMPANY_OTHER_PROJECT)

    def test_a_company_only_scope_refuses_a_project_outside_the_scope_company(self):
        """Company-only scope: the Project's own company must match the scope company.

        The document company matches the Project company here, so the refusal
        comes from the active scope comparison and not from the document
        company integrity rule.
        """
        self.db.add(
            "User Scope Context",
            "SC-1",
            user="ordinary@example.invalid",
            company=COMPANY,
            cost_center=None,
            project=None,
            modified=None,
        )
        row = make_row(boq_item="ITEM-4")
        doc = make_journal_entry([row], company=THIRD_COMPANY)
        self._assert_denied(doc, "Scope boundary violation", permission=True)

    def test_an_unreadable_project_company_fails_closed_under_a_company_only_scope(self):
        """An unverifiable authority fails closed, whatever the active scope is."""
        self.db.add(
            "User Scope Context",
            "SC-1",
            user="ordinary@example.invalid",
            company=COMPANY,
            cost_center=None,
            project=None,
            modified=None,
        )
        del self.db.rows[("Project", BOQ_PROJECT)]
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row])
        self._assert_denied(doc, "does not belong to Company")

    def test_a_missing_active_scope_context_is_refused(self):
        del self.db.rows[("User Scope Context", "SC-1")]
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row])
        self._assert_denied(doc, "active User Scope Context is required", permission=True)

    def test_an_active_scope_context_without_a_company_is_refused(self):
        self.db.add(
            "User Scope Context",
            "SC-1",
            user="ordinary@example.invalid",
            company=None,
            cost_center=None,
            project=BOQ_PROJECT,
            modified=None,
        )
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row])
        self._assert_denied(doc, "active User Scope Context is required", permission=True)

    # -- privileged and server-lifecycle semantics -------------------------

    def test_a_disabled_scope_context_keeps_the_company_integrity_rule(self):
        self.db.set_single("Construction Settings", "enable_scope_context", 0)
        row = make_row(boq_item="ITEM-3")
        doc = make_journal_entry([row])
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, SAME_COMPANY_OTHER_PROJECT, "the scope comparison is skipped")

        cross = make_row(idx=2, boq_item="ITEM-2")
        cross_doc = make_journal_entry([cross])
        self._assert_denied(cross_doc, "does not belong to Company")

    def test_administrator_keeps_the_company_integrity_rule(self):
        self.frappe.session.user = "Administrator"
        row = make_row(boq_item="ITEM-3")
        doc = make_journal_entry([row])
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, SAME_COMPANY_OTHER_PROJECT, "the scope comparison is skipped")

        cross = make_row(idx=2, boq_item="ITEM-2")
        cross_doc = make_journal_entry([cross])
        self._assert_denied(cross_doc, "does not belong to Company")

    def test_a_system_manager_skips_the_scope_comparison(self):
        self.frappe.get_roles = lambda user=None: ["System Manager"]
        row = make_row(boq_item="ITEM-3")
        doc = make_journal_entry([row])
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, SAME_COMPANY_OTHER_PROJECT)

    def test_a_guest_session_is_refused(self):
        self.frappe.session.user = "Guest"
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row])
        self._assert_denied(doc, "Guest sessions cannot modify scoped documents", permission=True)

    def test_a_scope_configuration_read_failure_fails_closed(self):
        self.db.single_value_error = RuntimeError("settings unreadable")
        row = make_row(boq_item="ITEM-1")
        doc = make_journal_entry([row])
        self._assert_denied(doc, "Scope enforcement configuration could not be loaded", permission=True)

    def test_ignore_permissions_is_not_a_scope_bypass(self):
        doc = make_journal_entry([make_row(boq_item="ITEM-3")])
        doc.flags = {"ignore_permissions": True}
        self._assert_denied(doc, "Scope boundary violation", permission=True)

    def test_the_service_only_bypass_token_is_preserved(self):
        self.frappe.flags.construction_scope_bypass = True
        row = make_row(boq_item="ITEM-3")
        doc = make_journal_entry([row])
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, SAME_COMPANY_OTHER_PROJECT)

    def test_the_install_migrate_and_patch_exemptions_are_preserved(self):
        for flag in ("in_install", "in_migrate", "in_patch"):
            with self.subTest(flag=flag):
                flags = StubFlags()
                setattr(flags, flag, True)
                self.frappe.flags = flags
                row = make_row(boq_item="ITEM-3")
                doc = make_journal_entry([row])
                self._journal_helper().validate_document(doc)
                self.assertEqual(row.project, SAME_COMPANY_OTHER_PROJECT)

    # -- the historical identity -------------------------------------------

    def test_an_unchanged_historical_row_keeps_its_null_project(self):
        self._store_row(project=None)
        row = make_row(name="ROW-1", boq_item="ITEM-1")
        doc = make_journal_entry([row], name="JE-1")
        self._journal_helper().validate_document(doc)
        self.assertIsNone(
            row.project,
            "an unchanged historical row keeps its stored project: no backfill, no history rewrite",
        )

    def test_an_unchanged_historical_row_keeps_its_stored_project(self):
        self._store_row(project=BOQ_PROJECT)
        row = make_row(name="ROW-1", boq_item="ITEM-1", project=BOQ_PROJECT)
        doc = make_journal_entry([row], name="JE-1")
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, BOQ_PROJECT)

    def test_a_persisted_project_is_not_lost_when_a_later_save_arrives_blank(self):
        """C1 regression: the assigned project survives a later blank save.

        The persisted row of THIS parent carries the authoritative project and
        the attribution is unchanged, so the row is historical. The incoming
        blank value must not clear the assigned project.
        """
        self._store_row(project=BOQ_PROJECT)
        row = make_row(name="ROW-1", boq_item="ITEM-1")
        doc = make_journal_entry([row], name="JE-1")
        self._journal_helper().validate_document(doc)
        self.assertEqual(
            row.project,
            BOQ_PROJECT,
            "the persisted project is restored instead of being cleared",
        )

    def test_a_persisted_project_of_another_parent_is_not_restored(self):
        """A foreign child identity never reaches the historical branch."""
        self._store_row(name="ROW-FOREIGN", project=BOQ_PROJECT, parent="JE-OTHER")
        row = make_row(name="ROW-FOREIGN", boq_item="ITEM-1")
        doc = make_journal_entry([row], name="JE-1")
        self._journal_helper().validate_document(doc)
        self.assertEqual(
            row.project,
            BOQ_PROJECT,
            "a foreign child identity is attributed like a new row",
        )

    def test_a_persisted_project_that_contradicts_the_boq_project_is_refused(self):
        """A stale stored project is never silently cleared nor silently replaced."""
        self._store_row(project=SAME_COMPANY_OTHER_PROJECT)
        row = make_row(name="ROW-1", boq_item="ITEM-1")
        doc = make_journal_entry([row], name="JE-1")
        message = self._assert_denied(doc, "Project mismatch")
        self.assertIn(SAME_COMPANY_OTHER_PROJECT, message)
        self.assertIn(BOQ_PROJECT, message)

    def test_an_explicit_authoritative_project_repairs_a_stale_persisted_project(self):
        """An explicit client value that equals the authoritative project is kept."""
        self._store_row(project=SAME_COMPANY_OTHER_PROJECT)
        row = make_row(name="ROW-1", boq_item="ITEM-1", project=BOQ_PROJECT)
        doc = make_journal_entry([row], name="JE-1")
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, BOQ_PROJECT)

    def test_a_re_attributed_historical_row_receives_the_derived_project(self):
        self._store_row(boq_item="ITEM-OTHER", project=None)
        row = make_row(name="ROW-1", boq_item="ITEM-1")
        doc = make_journal_entry([row], name="JE-1")
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, BOQ_PROJECT)

    def test_a_copied_child_identity_cannot_obtain_the_historical_exception(self):
        """A copied row identity is not persisted yet, so it is a new row."""
        row = make_row(name="ROW-COPIED", boq_item="ITEM-1")
        doc = make_journal_entry([row], name="JE-1")
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, BOQ_PROJECT)

    def test_a_foreign_child_identity_cannot_obtain_the_historical_exception(self):
        self._store_row(name="ROW-FOREIGN", project=None, parent="JE-OTHER")
        row = make_row(name="ROW-FOREIGN", boq_item="ITEM-1")
        doc = make_journal_entry([row], name="JE-1")
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, BOQ_PROJECT)

    def test_a_new_child_row_identity_receives_the_derived_project(self):
        row = make_row(name="ROW-NEW", boq_item="ITEM-1")
        doc = make_journal_entry([row], name="JE-1")
        self._journal_helper().validate_document(doc)
        self.assertEqual(row.project, BOQ_PROJECT)

    # -- atomicity --------------------------------------------------------

    def test_one_refused_row_refuses_the_whole_document(self):
        good = make_row(idx=1, boq_item="ITEM-1")
        bad = make_row(idx=2, boq_item="ITEM-2")
        doc = make_journal_entry([good, bad])
        self._assert_denied(doc, "does not belong to Company")


if __name__ == "__main__":
    unittest.main(verbosity=2)
