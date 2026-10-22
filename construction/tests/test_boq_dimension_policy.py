"""F44 round 2 — the native ERPNext accounting dimension policy of the BOQ Item query.

The BOQ cascade query replaces the native ERPNext query of the "boq_item"
field. The native query
(`erpnext.controllers.queries.get_filtered_dimensions`) applies the Accounting
Dimension Filter of the row's account, so the app must apply the same policy
itself; otherwise the correction would silently DROP the per-account dimension
restriction (for example on Journal Entry expense rows).

This module is SITE LESS on purpose: the policy resolution is a pure decision
over the native filter map, so it is exercised without a site, without a
database and without any fixture. The production file
`construction/api/boq_link_queries.py` is loaded directly with the minimal
dependencies stubbed, so the assertions run against the real production
source in every environment (plain CPython, a bench venv, a site).

Run it with:
    python construction/tests/test_boq_dimension_policy.py -v
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = APP_ROOT / "construction" / "api" / "boq_link_queries.py"

STUBBED_MODULE_NAMES = (
    "frappe",
    "construction",
    "construction.api",
    "construction.services",
    "construction.services.bilingual_service",
    "construction.services.boq_scope_filters",
    "construction.services.scope_resolution",
    "construction.api.boq_link_queries",
)


def _stub_frappe():
    """A minimal frappe stub: decorators pass through, db.sql is captured."""

    frappe = types.ModuleType("frappe")
    frappe.executed = []

    def whitelist(*args, **kwargs):
        def decorator(fn):
            return fn

        return decorator

    def validate_and_sanitize_search_inputs(fn):
        return fn

    class _Session:
        user = "offline@example.invalid"

    class _Db:
        @staticmethod
        def sql(query, values=None, **kwargs):
            frappe.executed.append((query, values))
            return []

        @staticmethod
        def get_value(*args, **kwargs):
            return None

        @staticmethod
        def exists(*args, **kwargs):
            return None

        @staticmethod
        def get_single_value(*args, **kwargs):
            return None

    frappe.whitelist = whitelist
    frappe.validate_and_sanitize_search_inputs = validate_and_sanitize_search_inputs
    frappe._ = lambda text: text
    frappe.parse_json = lambda value: value
    frappe.session = _Session()
    frappe.db = _Db()
    frappe.local = types.SimpleNamespace(response={})
    frappe.get_all = lambda *args, **kwargs: []
    frappe.log_error = lambda *args, **kwargs: None
    return frappe


def _stub_service_modules():
    """Stub the app services the module under test imports."""

    bilingual = types.ModuleType("construction.services.bilingual_service")
    bilingual.normalize_arabic = lambda value: value

    scope_filters = types.ModuleType("construction.services.boq_scope_filters")
    scope_filters.ALLOWED_TRANSACTION_BOQ_STATUSES = ["Locked", "Frozen"]
    scope_filters.scope_calls = []

    def append_allowed_status_filter(conditions, values, header_alias="h"):
        conditions.append(f"{header_alias}.status IN %(allowed_statuses)s")
        values["allowed_statuses"] = ("Locked", "Frozen")

    def apply_header_filters(conditions, values, filters, header_alias="h"):
        return False

    def apply_header_scope(conditions, values, scope, header_alias="h"):
        # A scoped user only sees the BOQ Headers of the scope project.
        conditions.append(f"{header_alias}.project = %(scope_project)s")
        values["scope_project"] = scope.project
        return True

    def get_scope_payload(*args, **kwargs):
        return {}

    def resolve_query_scope(enforce_scope=None):
        scope_filters.scope_calls.append(enforce_scope)
        if getattr(scope_filters, "scope", None) is None:
            return None
        return scope_filters.scope

    scope_filters.append_allowed_status_filter = append_allowed_status_filter
    scope_filters.apply_header_filters = apply_header_filters
    scope_filters.apply_header_scope = apply_header_scope
    scope_filters.get_scope_payload = get_scope_payload
    scope_filters.resolve_query_scope = resolve_query_scope
    scope_filters.scope = None

    scope_resolution = types.ModuleType("construction.services.scope_resolution")
    scope_resolution.get_scope_token = lambda *args, **kwargs: None

    return {
        "construction.services.bilingual_service": bilingual,
        "construction.services.boq_scope_filters": scope_filters,
        "construction.services.scope_resolution": scope_resolution,
    }


def load_boq_link_queries():
    """Load the production module with stubbed dependencies.

    The stubbed dependencies are removed from sys.modules again afterwards; the
    loaded module keeps its own references to them, so the loaded production
    source stays deterministic in every environment.
    """
    saved = {name: sys.modules.get(name) for name in STUBBED_MODULE_NAMES}

    construction = types.ModuleType("construction")
    construction.__path__ = []
    api = types.ModuleType("construction.api")
    api.__path__ = []
    services = types.ModuleType("construction.services")
    services.__path__ = []

    sys.modules["frappe"] = _stub_frappe()
    sys.modules["construction"] = construction
    sys.modules["construction.api"] = api
    sys.modules["construction.services"] = services
    sys.modules.update(_stub_service_modules())

    try:
        spec = importlib.util.spec_from_file_location("construction.api.boq_link_queries", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules["construction.api.boq_link_queries"] = module
        spec.loader.exec_module(module)
        return module, sys.modules["construction.services.boq_scope_filters"]
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def native_map(entries):
    """Build a map shaped exactly like the native ERPNext dimension filter map.

    The native map is keyed by (dimension, account) and holds
    {"allowed_dimensions": [...], "is_mandatory": int, "allow_or_restrict": str}.
    """
    return dict(entries)


def allows(policy, name):
    """The effective predicate of a resolved policy for one BOQ Item name."""
    if policy["mode"] is None:
        return True
    if policy["mode"] == "allow":
        return name in policy["values"]
    return name not in policy["values"]


class NativeDimensionPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.scope_filters = load_boq_link_queries()

    def setUp(self):
        self.module.frappe.executed.clear()

    # -- the decision -------------------------------------------------------

    def test_no_account_on_the_row_means_no_native_policy(self):
        policy = self.module.resolve_native_dimension_policy({}, dimension_filter_map={})
        self.assertIsNone(policy["mode"])
        self.assertEqual(policy["values"], ())

    def test_an_account_without_a_filter_entry_means_no_native_policy(self):
        policy = self.module.resolve_native_dimension_policy(
            {"account": "Expense - A - B"}, dimension_filter_map={}
        )
        self.assertIsNone(policy["mode"])

    def test_an_account_of_another_dimension_is_not_applied(self):
        entries = native_map(
            {
                ("cost_center", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-1"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        policy = self.module.resolve_native_dimension_policy(
            {"account": "Expense - A - B"}, dimension_filter_map=entries
        )
        self.assertIsNone(policy["mode"], "only the boq_item dimension may be applied")

    def test_allow_lists_exactly_the_allowed_dimensions(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-ALLOWED-1", "BOQI-ALLOWED-2"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        policy = self.module.resolve_native_dimension_policy(
            {"account": "Expense - A - B"}, dimension_filter_map=entries
        )
        self.assertEqual(policy["mode"], "allow")
        self.assertEqual(policy["values"], ("BOQI-ALLOWED-1", "BOQI-ALLOWED-2"))
        self.assertTrue(allows(policy, "BOQI-ALLOWED-1"))
        self.assertTrue(allows(policy, "BOQI-ALLOWED-2"))
        self.assertFalse(allows(policy, "BOQI-DENIED"), "an item outside the allowed set must not be offered")

    def test_restrict_excludes_exactly_the_restricted_dimensions(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-DENIED"],
                    "allow_or_restrict": "Restrict",
                    "is_mandatory": 0,
                }
            }
        )
        policy = self.module.resolve_native_dimension_policy(
            {"account": "Expense - A - B"}, dimension_filter_map=entries
        )
        self.assertEqual(policy["mode"], "restrict")
        self.assertEqual(policy["values"], ("BOQI-DENIED",))
        self.assertFalse(allows(policy, "BOQI-DENIED"))
        self.assertTrue(allows(policy, "BOQI-OTHER"))

    def test_an_empty_allowed_list_matches_the_native_edge_case(self):
        allow_entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": [],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        allow_policy = self.module.resolve_native_dimension_policy(
            {"account": "Expense - A - B"}, dimension_filter_map=allow_entries
        )
        self.assertEqual(allow_policy["mode"], "allow")
        self.assertEqual(allow_policy["values"], ())
        self.assertFalse(
            allows(allow_policy, "BOQI-ANY"),
            "the native edge case of an empty allow list offers no item",
        )

        restrict_entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": [],
                    "allow_or_restrict": "Restrict",
                    "is_mandatory": 0,
                }
            }
        )
        restrict_policy = self.module.resolve_native_dimension_policy(
            {"account": "Expense - A - B"}, dimension_filter_map=restrict_entries
        )
        self.assertEqual(restrict_policy["mode"], "restrict")
        self.assertTrue(
            allows(restrict_policy, "BOQI-ANY"),
            "the native edge case of an empty restrict list offers every item",
        )

    def test_an_unusable_account_value_is_ignored(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-ALLOWED-1"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        for value in ("", "   ", "x" * 200, "bad\nvalue", None, 42, ["a"]):
            policy = self.module.resolve_native_dimension_policy(
                {"account": value}, dimension_filter_map=entries
            )
            self.assertIsNone(policy["mode"], "an unusable account must not raise or apply a policy")

    # -- the SQL ------------------------------------------------------------

    def test_the_allow_policy_is_rendered_as_a_parameterised_in_condition(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-ALLOWED-1", "BOQI-ALLOWED-2"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        conditions: list[str] = []
        values: dict = {}
        policy = self.module.apply_native_dimension_policy(
            conditions, values, {"account": "Expense - A - B"}, dimension_filter_map=entries
        )
        self.assertEqual(policy["mode"], "allow")
        self.assertEqual(len(conditions), 1)
        self.assertIn("i.name IN %(native_dimension_allowed)s", conditions[0])
        self.assertEqual(values["native_dimension_allowed"], ("BOQI-ALLOWED-1", "BOQI-ALLOWED-2"))

    def test_the_restrict_policy_is_rendered_as_a_parameterised_not_in_condition(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-DENIED"],
                    "allow_or_restrict": "Restrict",
                    "is_mandatory": 0,
                }
            }
        )
        conditions: list[str] = []
        values: dict = {}
        self.module.apply_native_dimension_policy(
            conditions, values, {"account": "Expense - A - B"}, dimension_filter_map=entries
        )
        self.assertEqual(len(conditions), 1)
        self.assertIn("i.name NOT IN %(native_dimension_allowed)s", conditions[0])
        self.assertEqual(values["native_dimension_allowed"], ("BOQI-DENIED",))

    def test_the_empty_allowed_list_is_bound_like_the_native_predicate(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": [],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        conditions: list[str] = []
        values: dict = {}
        self.module.apply_native_dimension_policy(
            conditions, values, {"account": "Expense - A - B"}, dimension_filter_map=entries
        )
        self.assertEqual(values["native_dimension_allowed"], ("",))

    def test_without_an_account_no_extra_condition_is_added(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-ALLOWED-1"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        conditions: list[str] = []
        values: dict = {}
        policy = self.module.apply_native_dimension_policy(
            conditions, values, {}, dimension_filter_map=entries
        )
        self.assertIsNone(policy["mode"])
        self.assertEqual(conditions, [])
        self.assertEqual(values, {})

    def test_the_policy_is_added_next_to_the_boq_gates(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-ALLOWED-1"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        conditions = ["i.docstatus < 2", "i.boq_header = %(boq_header)s"]
        values = {"boq_header": "BOQ-2026-9705"}
        self.module.apply_native_dimension_policy(
            conditions, values, {"account": "Expense - A - B"}, dimension_filter_map=entries
        )
        self.assertEqual(len(conditions), 3)
        self.assertEqual(conditions[0], "i.docstatus < 2")
        self.assertEqual(conditions[1], "i.boq_header = %(boq_header)s")
        self.assertEqual(values["boq_header"], "BOQ-2026-9705")

    # -- the production wiring ---------------------------------------------

    def test_the_resolver_uses_the_native_map_by_default(self):
        sentinel = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-ALLOWED-1"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        original = self.module._native_dimension_filter_map
        self.module._native_dimension_filter_map = lambda: sentinel
        try:
            policy = self.module.resolve_native_dimension_policy({"account": "Expense - A - B"})
        finally:
            self.module._native_dimension_filter_map = original
        self.assertEqual(policy["mode"], "allow")
        self.assertEqual(policy["values"], ("BOQI-ALLOWED-1",))

    def test_the_native_map_helper_is_the_pinned_erpnext_helper(self):
        dotted = "erpnext.accounts.doctype.accounting_dimension_filter" ".accounting_dimension_filter"
        sentinel = {("boq_item", "Expense - A - B"): {"allowed_dimensions": []}}
        fake = types.ModuleType(dotted)
        fake.get_dimension_filter_map = lambda: sentinel

        saved = {name: sys.modules.get(name) for name in (dotted, "erpnext", "erpnext.accounts")}
        sys.modules[dotted] = fake
        sys.modules.setdefault("erpnext", types.ModuleType("erpnext"))
        sys.modules.setdefault("erpnext.accounts", types.ModuleType("erpnext.accounts"))
        try:
            self.assertEqual(self.module._native_dimension_filter_map(), sentinel)
        finally:
            for name, previous in saved.items():
                if previous is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous

    # -- the BOQ Item query -------------------------------------------------

    def _run_boq_items(self, filters):
        self.module.get_boq_items(
            doctype="BOQ Item",
            txt="",
            searchfield="name",
            start=0,
            page_len=20,
            filters=filters,
        )
        self.assertEqual(len(self.module.frappe.executed), 1)
        return self.module.frappe.executed[0]

    def test_the_boq_item_query_applies_the_native_allow_policy(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-ALLOWED-1", "BOQI-ALLOWED-2"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        original = self.module._native_dimension_filter_map
        self.module._native_dimension_filter_map = lambda: entries
        try:
            query, values = self._run_boq_items(
                {
                    "boq_header": "BOQ-2026-9705",
                    "structure": "gu7goanfvi",
                    "require_boq_header": True,
                    "require_structure": True,
                    "exclude_zero_revised": True,
                    "allowed_statuses": ["Frozen", "Locked"],
                    "account": "Expense - A - B",
                }
            )
        finally:
            self.module._native_dimension_filter_map = original

        # The native dimension restriction is applied ...
        self.assertIn("i.name IN %(native_dimension_allowed)s", query)
        self.assertEqual(values["native_dimension_allowed"], ("BOQI-ALLOWED-1", "BOQI-ALLOWED-2"))
        # ... next to the BOQ omission / header / structure / status gates.
        self.assertIn("COALESCE(i.current_revised_qty, i.quantity) > 0", query)
        self.assertIn("i.boq_header = %(boq_header)s", query)
        self.assertIn("i.structure = %(structure)s", query)
        self.assertIn("h.status IN %(allowed_statuses)s", query)
        self.assertEqual(values["boq_header"], "BOQ-2026-9705")
        self.assertEqual(values["structure"], "gu7goanfvi")
        self.assertEqual(values["allowed_statuses"], ("Frozen", "Locked"))

    def test_the_boq_item_query_applies_the_native_restrict_policy(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-DENIED"],
                    "allow_or_restrict": "Restrict",
                    "is_mandatory": 0,
                }
            }
        )
        original = self.module._native_dimension_filter_map
        self.module._native_dimension_filter_map = lambda: entries
        try:
            query, values = self._run_boq_items(
                {
                    "boq_header": "BOQ-2026-9705",
                    "structure": "gu7goanfvi",
                    "require_boq_header": True,
                    "require_structure": True,
                    "exclude_zero_revised": True,
                    "account": "Expense - A - B",
                }
            )
        finally:
            self.module._native_dimension_filter_map = original

        self.assertIn("i.name NOT IN %(native_dimension_allowed)s", query)
        self.assertEqual(values["native_dimension_allowed"], ("BOQI-DENIED",))
        self.assertIn("i.structure = %(structure)s", query)

    def test_the_boq_item_query_without_an_account_keeps_the_boq_gates_only(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-ALLOWED-1"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        original = self.module._native_dimension_filter_map
        self.module._native_dimension_filter_map = lambda: entries
        try:
            query, values = self._run_boq_items(
                {
                    "boq_header": "BOQ-2026-9705",
                    "structure": "gu7goanfvi",
                    "require_boq_header": True,
                    "require_structure": True,
                    "exclude_zero_revised": True,
                }
            )
        finally:
            self.module._native_dimension_filter_map = original

        self.assertNotIn("native_dimension_allowed", query)
        self.assertNotIn("native_dimension_allowed", values)
        self.assertIn("i.boq_header = %(boq_header)s", query)
        self.assertIn("i.structure = %(structure)s", query)

    def test_the_closed_gate_still_denies_every_item(self):
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-ALLOWED-1"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        original = self.module._native_dimension_filter_map
        self.module._native_dimension_filter_map = lambda: entries
        try:
            result = self.module.get_boq_items(
                doctype="BOQ Item",
                txt="",
                searchfield="name",
                start=0,
                page_len=20,
                filters={
                    "boq_header": "BOQ-2026-9705",
                    "structure": "gu7goanfvi",
                    "require_boq_header": True,
                    "require_structure": True,
                    "require_gate": True,
                    "gate_open": 0,
                    "account": "Expense - A - B",
                },
            )
        finally:
            self.module._native_dimension_filter_map = original

        self.assertEqual(result, [])
        self.assertEqual(self.module.frappe.executed, [], "a closed gate must not query the items")

    def test_the_scope_boundary_is_still_applied_next_to_the_native_policy(self):
        """A scoped user must not see the BOQ Items of another project."""
        entries = native_map(
            {
                ("boq_item", "Expense - A - B"): {
                    "allowed_dimensions": ["BOQI-ALLOWED-1"],
                    "allow_or_restrict": "Allow",
                    "is_mandatory": 0,
                }
            }
        )
        scope_filters = self.scope_filters
        scope_filters.scope = types.SimpleNamespace(project="PROJ-0115", scope_type="Project-Scoped")
        scope_filters.scope_calls.clear()
        original = self.module._native_dimension_filter_map
        self.module._native_dimension_filter_map = lambda: entries
        try:
            query, values = self._run_boq_items(
                {
                    "boq_header": "BOQ-2026-9705",
                    "structure": "gu7goanfvi",
                    "require_boq_header": True,
                    "require_structure": True,
                    "exclude_zero_revised": True,
                    "account": "Expense - A - B",
                }
            )
        finally:
            self.module._native_dimension_filter_map = original
            scope_filters.scope = None

        # The scope is still resolved server side (the client cannot switch it off).
        self.assertTrue(scope_filters.scope_calls, "the query scope must still be resolved")
        # The scope condition is applied ...
        self.assertIn("h.project = %(scope_project)s", query)
        self.assertEqual(values["scope_project"], "PROJ-0115")
        # ... next to the native dimension restriction and the BOQ gates.
        self.assertIn("i.name IN %(native_dimension_allowed)s", query)
        self.assertEqual(values["native_dimension_allowed"], ("BOQI-ALLOWED-1",))
        self.assertIn("i.boq_header = %(boq_header)s", query)
        self.assertIn("i.structure = %(structure)s", query)


if __name__ == "__main__":
    unittest.main()
