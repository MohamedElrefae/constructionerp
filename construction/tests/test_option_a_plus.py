# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""
Option A+ tests.

Targets:
  - The Property Setter helper that hides the `company` standard filter on
    7 ERPNext operational DocTypes.
  - The `construction.patches.v7_2.set_erpnext_standard_filters` patch
    entry point.
  - The `get_scope_dimension_permissions` whitelisted API used by the
    report filter hardening JS.
  - The `scope_report._enforce_scope_filters_strict` backend wrapper,
    including list-shaped filters (MultiSelectList), strict active-scope
    policy, allowlist behaviour, positional-args normalization, and
    duplicate-filter prevention (strict-signature tests).
  - Finance-role bypass.
"""

import unittest

import frappe

from construction.api.scope_context_api import (
    get_scope_dimension_permissions,
    set_scope_context,
)

# The 7 flagged ERPNext operational DocTypes.
FLAGGED_DOCTYPES = [
    "Sales Invoice",
    "Purchase Invoice",
    "Journal Entry",
    "Purchase Order",
    "Delivery Note",
    "Material Request",
    "Purchase Receipt",
]

# The 3 DocTypes whose `company.in_standard_filter` is already 0 natively.
NATIVE_SAFE_DOCTYPES = [
    "Payment Entry",
    "Stock Entry",
    "Timesheet",
]

_COST_CENTER = "Main - E"
_GROUP_CC = "Elrefae - E"


def _ensure_test_user():
    if not frappe.db.exists("User", "test_user2@example.com"):
        user = frappe.new_doc("User")
        user.email = "test_user2@example.com"
        user.first_name = "Test User 2"
        user.send_welcome_email = 0
        user.insert(ignore_permissions=True)
        frappe.db.commit()


def _enable_scope():
    frappe.db.set_single_value("Construction Settings", "enable_scope_context", 1)
    frappe.db.commit()


def _disable_scope():
    frappe.db.set_single_value("Construction Settings", "enable_scope_context", 0)
    frappe.db.commit()


# ─────────────────────────────────────────────────────────────────────
# Property Setter coverage
# ─────────────────────────────────────────────────────────────────────


class TestOptionAPlusPropertySetters(unittest.TestCase):
    """All 7 flagged DocTypes must have `company.in_standard_filter = 0`."""

    def test_helper_is_idempotent(self):
        from construction.patches.v7_2.set_erpnext_standard_filters import (
            setup_erpnext_standard_filters,
        )

        # Run twice — should not raise and should not duplicate.
        setup_erpnext_standard_filters()
        setup_erpnext_standard_filters()
        frappe.db.commit()

        for dt in FLAGGED_DOCTYPES:
            if not frappe.db.exists("DocType", dt):
                continue
            ps_count = frappe.db.count(
                "Property Setter",
                {
                    "doc_type": dt,
                    "field_name": "company",
                    "property": "in_standard_filter",
                },
            )
            self.assertEqual(
                ps_count,
                1,
                f"{dt}.company should have exactly one Property Setter, got {ps_count}",
            )

    def test_metadata_resolves_zero(self):
        from construction.patches.v7_2.set_erpnext_standard_filters import (
            setup_erpnext_standard_filters,
        )

        setup_erpnext_standard_filters()
        frappe.db.commit()

        for dt in FLAGGED_DOCTYPES:
            if not frappe.db.exists("DocType", dt):
                continue
            with self.subTest(doctype=dt):
                df = frappe.get_meta(dt).get_field("company")
                self.assertIsNotNone(df, f"{dt} should have a company field")
                self.assertEqual(
                    int(df.in_standard_filter or 0),
                    0,
                    f"{dt}.company.in_standard_filter should resolve to 0",
                )

    def test_native_safe_doctypes_remain_safe(self):
        """Payment Entry / Stock Entry / Timesheet ship with in_standard_filter=0."""
        for dt in NATIVE_SAFE_DOCTYPES:
            if not frappe.db.exists("DocType", dt):
                continue
            with self.subTest(doctype=dt):
                df = frappe.get_meta(dt).get_field("company")
                self.assertIsNotNone(df)
                self.assertEqual(
                    int(df.in_standard_filter or 0),
                    0,
                    f"{dt}.company should be 0 even without a Property Setter",
                )


# ─────────────────────────────────────────────────────────────────────
# Whitelisted permission probe API
# ─────────────────────────────────────────────────────────────────────


class TestScopeDimensionPermissionsAPI(unittest.TestCase):
    """The whitelisted endpoint must return a 4-key dict of booleans."""

    def test_returns_all_dimensions(self):
        result = get_scope_dimension_permissions()
        self.assertIsInstance(result, dict)
        for key in ("Company", "Project", "Cost Center", "Account"):
            self.assertIn(key, result, f"Missing key: {key}")
            self.assertIsInstance(result[key], bool, f"{key} should be a bool, got {type(result[key])}")

    def test_administrator_can_read_all(self):
        frappe.set_user("Administrator")
        try:
            result = get_scope_dimension_permissions()
            # Administrator has the all-powerful role — every dimension
            # must be readable.
            self.assertTrue(result["Company"])
            self.assertTrue(result["Project"])
            self.assertTrue(result["Cost Center"])
            self.assertTrue(result["Account"])
        finally:
            frappe.set_user("Administrator")


# ─────────────────────────────────────────────────────────────────────
# Backend report scope enforcement
# ─────────────────────────────────────────────────────────────────────


class TestScopeReportEnforcement(unittest.TestCase):
    """Verify _enforce_scope_filters_strict enforces active-scope strictly.

    Policy:
      - Company: scalar, always the active scope value.
      - Project: list, always `[scope.project]` (or `[]` if none).
      - Cost Center: list, always `[scope.cost_center, *descendants]`.
      - Department: list, always `[scope.department]` (or `[]` if none).
      - A restricted user cannot widen any filter beyond the top bar.
    """

    def setUp(self):
        _enable_scope()
        _ensure_test_user()
        frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
        frappe.db.commit()
        frappe.clear_cache(user="test_user2@example.com")

    def tearDown(self):
        _disable_scope()
        frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
        frappe.db.commit()
        frappe.clear_cache(user="test_user2@example.com")

    def _set_scope(self, project=None, department=None):
        # Always start from a clean state.
        frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
        for key in ("project", "department", "cost_center", "company"):
            frappe.defaults.clear_user_default(key, "test_user2@example.com")
        frappe.db.commit()
        frappe.clear_cache(user="test_user2@example.com")
        frappe.set_user("test_user2@example.com")
        try:
            set_scope_context(
                company="Elrefae",
                cost_center=_COST_CENTER,
                project=project,
                department=department,
                source="test",
            )
            frappe.db.commit()
            frappe.clear_cache(user="test_user2@example.com")
        finally:
            frappe.set_user("Administrator")

    def test_strict_company_is_scalar_and_equals_scope(self):
        from construction.overrides.scope_report import _enforce_scope_filters_strict

        self._set_scope()
        out = _enforce_scope_filters_strict({}, "test_user2@example.com")
        self.assertEqual(out["company"], "Elrefae")
        self.assertIsInstance(out["company"], str)

    def test_strict_project_is_list_with_scope_value(self):
        from construction.overrides.scope_report import _enforce_scope_filters_strict

        # Force-clear any prior scope state explicitly.
        frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
        frappe.db.commit()
        frappe.clear_cache(user="test_user2@example.com")

        self._set_scope(project=None)
        out = _enforce_scope_filters_strict({}, "test_user2@example.com")
        self.assertEqual(out["project"], [])

        # When the user has a project in scope:
        allowed_project = frappe.get_all("Project", pluck="name", limit=1)
        if not allowed_project:
            self.skipTest("No Project records in DB to test scope project")
        self._set_scope(project=allowed_project[0])
        out = _enforce_scope_filters_strict({}, "test_user2@example.com")
        self.assertEqual(out["project"], [allowed_project[0]])

    def test_strict_cost_center_is_list_with_descendants(self):
        from construction.overrides.scope_report import _enforce_scope_filters_strict

        # When scoped to the LEAF cost center, the result is the leaf alone.
        self._set_scope()
        out = _enforce_scope_filters_strict({}, "test_user2@example.com")
        self.assertIsInstance(out["cost_center"], list)
        self.assertIn(_COST_CENTER, out["cost_center"])
        # Leaf has no descendants; group ancestors are NOT included.
        self.assertNotIn(_GROUP_CC, out["cost_center"])

        # When scoped to the GROUP cost center, descendants are included
        # via lft/rgt expansion.
        frappe.set_user("test_user2@example.com")
        try:
            frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
            frappe.db.commit()
            frappe.clear_cache(user="test_user2@example.com")
            set_scope_context(
                company="Elrefae",
                cost_center=_GROUP_CC,
                project=None,
                department=None,
                source="test",
            )
            frappe.db.commit()
            frappe.clear_cache(user="test_user2@example.com")
        finally:
            frappe.set_user("Administrator")

        out = _enforce_scope_filters_strict({}, "test_user2@example.com")
        self.assertIsInstance(out["cost_center"], list)
        # The group itself is in the list.
        self.assertIn(_GROUP_CC, out["cost_center"])
        # And its descendant leaf.
        self.assertIn(_COST_CENTER, out["cost_center"])

    def test_strict_incoming_value_is_overwritten(self):
        """A restricted user attempting to widen the company is overridden."""
        from construction.overrides.scope_report import _enforce_scope_filters_strict

        self._set_scope()
        # The user submits a *different* company. Strict policy overrides.
        filters = {"company": "__OtherAllowedCo__", "project": ["__Any__"]}
        out = _enforce_scope_filters_strict(filters, "test_user2@example.com")
        self.assertEqual(out["company"], "Elrefae")
        self.assertEqual(out["project"], [])

    def test_unscoped_user_yields_empty_filters(self):
        from construction.overrides.scope_report import _enforce_scope_filters_strict

        # No scope set for this user.
        filters = {"company": "Elrefae"}
        out = _enforce_scope_filters_strict(filters, "test_user2@example.com")
        # Strict policy: no scope, no value injected. The dimension is None.
        self.assertIsNone(out.get("company"))
        self.assertEqual(out.get("project"), [])
        self.assertEqual(out.get("cost_center"), [])
        self.assertEqual(out.get("department"), [])


class TestScopeReportAllowlist(unittest.TestCase):
    """The wrapper must only rewrite filters for ALLOWED_REPORTS."""

    def setUp(self):
        _enable_scope()
        _ensure_test_user()

    def tearDown(self):
        _disable_scope()
        frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
        frappe.db.commit()
        frappe.clear_cache(user="test_user2@example.com")

    def test_allowed_reports_constant_contains_10(self):
        from construction.overrides.scope_report import ALLOWED_REPORTS

        for name in [
            "General Ledger",
            "Trial Balance",
            "Profit and Loss Statement",
            "Balance Sheet",
            "Accounts Payable",
            "Accounts Payable Summary",
            "Accounts Receivable",
            "Accounts Receivable Summary",
            "Budget Variance Report",
            "Cash Flow",
        ]:
            self.assertIn(name, ALLOWED_REPORTS)

    def test_non_allowlisted_report_passes_through(self):
        """For a non-allowlisted report, the wrapper must NOT rewrite filters."""
        from construction.overrides.scope_report import _ORIGINAL_RUN, _scope_aware_run

        # Set a scope.
        frappe.set_user("test_user2@example.com")
        try:
            set_scope_context(
                company="Elrefae",
                cost_center=_COST_CENTER,
                project=None,
                department=None,
                source="test",
            )
            frappe.db.commit()
            frappe.clear_cache(user="test_user2@example.com")

            # Mock the original run so we can inspect what was passed in.
            captured = {}

            def fake_run(*a, **kw):
                captured["args"] = a
                captured["kwargs"] = kw
                return {"result": []}

            import construction.overrides.scope_report as mod

            mod._ORIGINAL_RUN = fake_run
            try:
                _scope_aware_run(
                    "Sales Analytics",  # NOT in the allowlist
                    {"company": "Other Co"},
                )
            finally:
                mod._ORIGINAL_RUN = _ORIGINAL_RUN

            # Filters were not rewritten.
            self.assertEqual(captured["args"][0], "Sales Analytics")
            self.assertEqual(captured["args"][1], {"company": "Other Co"})
        finally:
            frappe.set_user("Administrator")

    def test_allowlisted_report_does_rewrite(self):
        from construction.overrides.scope_report import _ORIGINAL_RUN, _scope_aware_run

        frappe.set_user("test_user2@example.com")
        try:
            set_scope_context(
                company="Elrefae",
                cost_center=_COST_CENTER,
                project=None,
                department=None,
                source="test",
            )
            frappe.db.commit()
            frappe.clear_cache(user="test_user2@example.com")

            captured = {}

            def fake_run(*a, **kw):
                captured["args"] = a
                captured["kwargs"] = kw
                return {"result": []}

            import construction.overrides.scope_report as mod

            mod._ORIGINAL_RUN = fake_run
            try:
                _scope_aware_run(
                    "General Ledger",  # allowlisted
                    {"company": "__OtherCo__", "from_date": "2026-01-01"},
                )
            finally:
                mod._ORIGINAL_RUN = _ORIGINAL_RUN

            # Filters were rewritten: company is the scoped value.
            self.assertEqual(captured["args"][0], "General Ledger")
            filters_passed = captured["args"][1]
            self.assertEqual(filters_passed["company"], "Elrefae")
            # Non-scope dimensions are preserved.
            self.assertEqual(filters_passed["from_date"], "2026-01-01")
        finally:
            frappe.set_user("Administrator")


class TestScopeReportPositionalArgs(unittest.TestCase):
    """The wrapper must accept both positional and keyword filter args."""

    def setUp(self):
        _enable_scope()
        _ensure_test_user()

    def tearDown(self):
        _disable_scope()
        frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
        frappe.db.commit()
        frappe.clear_cache(user="test_user2@example.com")

    def test_positional_filters_are_normalized(self):
        from construction.overrides.scope_report import _ORIGINAL_RUN, _scope_aware_run

        frappe.set_user("test_user2@example.com")
        try:
            set_scope_context(
                company="Elrefae",
                cost_center=_COST_CENTER,
                project=None,
                department=None,
                source="test",
            )
            frappe.db.commit()
            frappe.clear_cache(user="test_user2@example.com")

            captured = {}

            def fake_run(*a, **kw):
                captured["args"] = a
                captured["kwargs"] = kw
                return {"result": []}

            import construction.overrides.scope_report as mod

            mod._ORIGINAL_RUN = fake_run
            try:
                # Call positionally: run(report_name, filters, user, ...)
                _scope_aware_run(
                    "General Ledger",
                    {"company": "__OtherCo__"},
                    "test_user2@example.com",
                )
            finally:
                mod._ORIGINAL_RUN = _ORIGINAL_RUN

            # The positional filters must have been rewritten.
            self.assertEqual(captured["args"][0], "General Ledger")
            self.assertEqual(captured["args"][1]["company"], "Elrefae")
        finally:
            frappe.set_user("Administrator")

    def test_filters_as_json_string_are_parsed(self):
        from construction.overrides.scope_report import _ORIGINAL_RUN, _scope_aware_run

        frappe.set_user("test_user2@example.com")
        try:
            set_scope_context(
                company="Elrefae",
                cost_center=_COST_CENTER,
                project=None,
                department=None,
                source="test",
            )
            frappe.db.commit()
            frappe.clear_cache(user="test_user2@example.com")

            captured = {}

            def fake_run(*a, **kw):
                captured["args"] = a
                captured["kwargs"] = kw
                return {"result": []}

            import construction.overrides.scope_report as mod

            mod._ORIGINAL_RUN = fake_run
            try:
                # Call with filters as a JSON-encoded string.
                _scope_aware_run(
                    "General Ledger",
                    '{"company": "__OtherCo__"}',
                )
            finally:
                mod._ORIGINAL_RUN = _ORIGINAL_RUN

            self.assertEqual(captured["args"][0], "General Ledger")
            self.assertEqual(captured["args"][1]["company"], "Elrefae")
        finally:
            frappe.set_user("Administrator")


class TestStrictSignature(unittest.TestCase):
    """
    The wrapper must NOT pass `filters` to the original `run()` twice.

    The real Frappe signature is::

        def run(report_name, filters=None, user=None, ...):

    If the wrapper passes `filters` both positionally and as a keyword,
    Python raises::

        TypeError: run() got multiple values for argument 'filters'

    These tests use a strict-signature fake that mirrors the real one,
    so the bug is caught even though the real `frappe.desk.query_report.run`
    is not invoked.
    """

    def setUp(self):
        _enable_scope()
        _ensure_test_user()
        # Clean state.
        frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
        for key in ("project", "department", "cost_center", "company"):
            frappe.defaults.clear_user_default(key, "test_user2@example.com")
        frappe.db.commit()
        frappe.clear_cache(user="test_user2@example.com")
        # Set up the scope for the test user.
        frappe.set_user("test_user2@example.com")
        try:
            set_scope_context(
                company="Elrefae",
                cost_center=_COST_CENTER,
                project=None,
                department=None,
                source="test",
            )
            frappe.db.commit()
            frappe.clear_cache(user="test_user2@example.com")
        finally:
            frappe.set_user("Administrator")

    def tearDown(self):
        _disable_scope()
        frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
        for key in ("project", "department", "cost_center", "company"):
            frappe.defaults.clear_user_default(key, "test_user2@example.com")
        frappe.db.commit()
        frappe.clear_cache(user="test_user2@example.com")

    def _make_strict_fake(self):
        """Return a fake `run` whose signature matches the real Frappe one."""
        captured = {"calls": 0, "last_error": None}

        def strict_fake_run(
            report_name,
            filters=None,
            user=None,
            ignore_prepared_report=False,
            custom_columns=None,
            is_tree=False,
            parent_field=None,
            are_default_filters=True,
            js_filters=None,
        ):
            captured["calls"] += 1
            return {"result": [], "report_name": report_name, "filters": filters}

        return strict_fake_run, captured

    def test_positional_filters_do_not_cause_duplicate_arg(self):
        """When caller passes filters positionally, the wrapper must NOT
        also pass filters as a keyword. Otherwise Python raises
        TypeError on the strict-signature call."""
        import construction.overrides.scope_report as mod
        from construction.overrides.scope_report import _scope_aware_run

        strict_fake, captured = self._make_strict_fake()
        mod._ORIGINAL_RUN = strict_fake
        try:
            _scope_aware_run(
                "General Ledger",
                {"company": "__OtherCo__"},
                "test_user2@example.com",
                False,
                None,
                False,
                None,
                True,
                None,
            )
        except TypeError as e:
            mod._ORIGINAL_RUN = mod.__dict__.get("_ORIGINAL_RUN", None)
            self.fail(f"Wrapper passed filters twice: {e}")

        self.assertEqual(captured["calls"], 1)

    def test_keyword_filters_do_not_cause_duplicate_arg(self):
        """When caller passes filters as keyword, the wrapper must NOT
        also pass filters positionally."""
        import construction.overrides.scope_report as mod
        from construction.overrides.scope_report import _scope_aware_run

        strict_fake, captured = self._make_strict_fake()
        mod._ORIGINAL_RUN = strict_fake
        try:
            _scope_aware_run(
                "General Ledger",
                filters={"company": "__OtherCo__"},
                user="test_user2@example.com",
            )
        except TypeError as e:
            mod._ORIGINAL_RUN = mod.__dict__.get("_ORIGINAL_RUN", None)
            self.fail(f"Wrapper passed filters twice: {e}")

        self.assertEqual(captured["calls"], 1)

    def test_filters_rewritten_with_positional_input(self):
        """The strict fake should see the rewritten (scope-strict) filters,
        proving the wrapper actually updated the positional arg."""
        import construction.overrides.scope_report as mod
        from construction.overrides.scope_report import _scope_aware_run

        strict_fake, captured = self._make_strict_fake()
        mod._ORIGINAL_RUN = strict_fake
        try:
            # Pass `user` as a kwarg so the wrapper can identify the
            # restricted user (the test runner's session user is
            # Administrator).
            result = _scope_aware_run(
                "General Ledger",
                {"company": "__OtherCo__", "cost_center": ["__OtherCC__"]},
                user="test_user2@example.com",
            )
        finally:
            mod._ORIGINAL_RUN = mod.__dict__.get("_ORIGINAL_RUN", None)

        self.assertEqual(captured["calls"], 1)
        self.assertEqual(result["report_name"], "General Ledger")
        # The wrapper should have replaced the user-supplied company with
        # the strict scope value.
        self.assertEqual(result["filters"]["company"], "Elrefae")

    def test_filters_rewritten_with_keyword_input(self):
        import construction.overrides.scope_report as mod
        from construction.overrides.scope_report import _scope_aware_run

        strict_fake, captured = self._make_strict_fake()
        mod._ORIGINAL_RUN = strict_fake
        try:
            result = _scope_aware_run(
                "General Ledger",
                filters={"company": "__OtherCo__"},
                user="test_user2@example.com",
            )
        finally:
            mod._ORIGINAL_RUN = mod.__dict__.get("_ORIGINAL_RUN", None)

        self.assertEqual(captured["calls"], 1)
        self.assertEqual(result["filters"]["company"], "Elrefae")

    def test_filters_as_json_string_with_keyword(self):
        """A JSON-string filter passed as keyword must be parsed and rewritten."""
        import construction.overrides.scope_report as mod
        from construction.overrides.scope_report import _scope_aware_run

        strict_fake, captured = self._make_strict_fake()
        mod._ORIGINAL_RUN = strict_fake
        try:
            result = _scope_aware_run(
                "General Ledger",
                filters='{"company": "__OtherCo__"}',
                user="test_user2@example.com",
            )
        finally:
            mod._ORIGINAL_RUN = mod.__dict__.get("_ORIGINAL_RUN", None)

        self.assertEqual(captured["calls"], 1)
        self.assertEqual(result["filters"]["company"], "Elrefae")

    def test_user_resolved_from_positional_arg(self):
        """A positional `user` argument must be honoured by the wrapper.

        Real Frappe callers may invoke ``run("General Ledger", filters,
        "some-user@example.com")``. The wrapper must read the user
        from the positional slot (not just kwargs) so the bypass /
        enforcement decision is correct.
        """
        import construction.overrides.scope_report as mod
        from construction.overrides.scope_report import _scope_aware_run

        strict_fake, captured = self._make_strict_fake()
        mod._ORIGINAL_RUN = strict_fake
        try:
            # Call exactly as Frappe's real signature would: report_name,
            # filters, user — all positional. No `user=` kwarg.
            result = _scope_aware_run(
                "General Ledger",
                {"company": "__OtherCo__", "cost_center": ["__OtherCC__"]},
                "test_user2@example.com",
            )
        finally:
            mod._ORIGINAL_RUN = mod.__dict__.get("_ORIGINAL_RUN", None)

        # The wrapper must have identified the restricted user from
        # the positional slot and rewritten the filters to the active
        # scope. If the wrapper fell back to frappe.session.user
        # (Administrator), it would bypass enforcement and the
        # original `__OtherCo__` would leak through.
        self.assertEqual(captured["calls"], 1)
        self.assertEqual(result["report_name"], "General Ledger")
        self.assertEqual(
            result["filters"]["company"],
            "Elrefae",
            "Positional user must be honoured so the restricted user "
            "is enforced, not bypassed as Administrator",
        )
        # Cost center should be the strict list (scoped + descendants).
        self.assertIsInstance(result["filters"]["cost_center"], list)
        self.assertIn("Main - E", result["filters"]["cost_center"])

    def test_unrestricted_user_in_positional_slot_bypasses(self):
        """If the positional `user` is an unrestricted role, the
        wrapper must bypass enforcement. This proves the wrapper
        actually uses the positional user (rather than ignoring it
        and falling back to frappe.session.user)."""
        import construction.overrides.scope_report as mod
        from construction.overrides.scope_report import _scope_aware_run

        captured = {}
        user_doc = None
        role_added = False

        def strict_fake(*a, **kw):
            captured["args"] = a
            captured["kwargs"] = kw
            return {"result": []}

        mod._ORIGINAL_RUN = strict_fake
        try:
            # Ensure the test user has the Accounts Manager role.
            if not frappe.db.exists("User", "accounts.manager@example.com"):
                u = frappe.new_doc("User")
                u.email = "accounts.manager@example.com"
                u.first_name = "Test Accounts Manager"
                u.send_welcome_email = 0
                u.enabled = 1
                u.insert(ignore_permissions=True)
                frappe.db.commit()
            user_doc = frappe.get_doc("User", "accounts.manager@example.com")
            if "Accounts Manager" not in frappe.get_roles("accounts.manager@example.com"):
                user_doc.add_roles("Accounts Manager")
                role_added = True
                frappe.db.commit()

            # The wrapper must bypass — filters should pass through
            # unchanged.
            result = _scope_aware_run(
                "General Ledger",
                {"company": "ACo", "cost_center": ["ACC"]},
                "accounts.manager@example.com",
            )
        finally:
            if role_added and user_doc is not None:
                try:
                    user_doc.remove_roles("Accounts Manager")
                    frappe.db.commit()
                except Exception:
                    pass
            mod._ORIGINAL_RUN = mod.__dict__.get("_ORIGINAL_RUN", None)

        # The wrapper bypassed. The fake saw the original filters.
        self.assertEqual(captured["args"][1], {"company": "ACo", "cost_center": ["ACC"]})


# ─────────────────────────────────────────────────────────────────────
# Finance role bypass
# ─────────────────────────────────────────────────────────────────────


class TestFinanceRoleBypass(unittest.TestCase):
    """Restricted users get scope enforcement; finance users bypass it."""

    def test_unrestricted_role_bypasses(self):
        from construction.overrides.scope_report import _has_unrestricted_report_role

        if not frappe.db.exists("Role", "Accounts User"):
            frappe.get_doc({"doctype": "Role", "role_name": "Accounts User"}).insert(ignore_permissions=True)

        user = "test_scope@example.com"
        user_doc = frappe.get_doc("User", user)
        try:
            user_doc.add_roles("Accounts User")
            self.assertTrue(_has_unrestricted_report_role(user))
        finally:
            user_doc.remove_roles("Accounts User")

    def test_non_finance_role_does_not_bypass(self):
        from construction.overrides.scope_report import _has_unrestricted_report_role

        user = "test_scope@example.com"
        user_doc = frappe.get_doc("User", user)
        for role in ("Accounts Manager", "Accounts User", "Finance Manager", "System Manager"):
            user_doc.remove_roles(role)

        self.assertFalse(_has_unrestricted_report_role(user))


# ─────────────────────────────────────────────────────────────────────
# Option B — Report access gate (Report.is_permitted + get_report_doc +
# has_permission + get_role_permissions + get_permitted_fields)
# ─────────────────────────────────────────────────────────────────────


class TestOptionBReportAccessGate(unittest.TestCase):
    """
    Verify the Option B report-access-gate bypass.

    The patch is gated on a STRUCTURED context
    (`frappe.flags.scope_report_bypass` is a dict with
    `report_name`, `user`) validated by `_bypass_should_apply`. The
    patch must:
    - Allow `Report.is_permitted()` to return True for allowlisted
      reports when the user has an active scope context.
    - Allow `get_report_doc()` to skip both 403 checks for allowlisted
      reports when the user has an active scope context.
    - Allow `frappe.has_permission` to return True for `report`,
      `select`, and `read` ptypes ONLY when the structured context
      is set AND the ptype is in the small allowlist.
    - Allow `frappe.permissions.get_role_permissions` to return
      permissive perms (for the allowlisted ptypes only) under the
      same condition.
    - Allow `frappe.model.get_permitted_fields` to return all valid
      columns under the same condition.
    - NOT bypass for:
        * non-allowlisted reports,
        * users without a scope context,
        * requests where the structured context is missing/empty,
        * requests where the user in the context differs from the
          session user (cross-user leak guard),
        * ptypes other than the small allowlist (report, select, read).

    The bypass is REPORT-scoped, not doctype-scoped: the report's
    SQL builder may query multiple secondary doctypes, and the
    data is constrained by the L1+L2 wrappers. The bypass only
    opens the perm gate for the report's own queries.
    """

    def setUp(self):
        _enable_scope()
        _ensure_test_user()
        # Clean state.
        frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
        for key in ("project", "department", "cost_center", "company"):
            frappe.defaults.clear_user_default(key, "test_user2@example.com")
        frappe.db.commit()
        frappe.clear_cache(user="test_user2@example.com")
        # Make sure apply_report_monkeypatch has been run.
        from construction.overrides import scope_report

        if not scope_report._ORIGINAL_RUN_SIG:
            scope_report.apply_report_monkeypatch()
        # Make sure no stale flag survives between tests.
        from construction.overrides import scope_report

        scope_report.clear_bypass_context()

    def tearDown(self):
        _disable_scope()
        frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
        for key in ("project", "department", "cost_center", "company"):
            frappe.defaults.clear_user_default(key, "test_user2@example.com")
        frappe.db.commit()
        frappe.clear_cache(user="test_user2@example.com")
        # Always clear the bypass context, even on test failure.
        from construction.overrides import scope_report

        scope_report.clear_bypass_context()

    def _set_scope(self):
        frappe.set_user("test_user2@example.com")
        try:
            set_scope_context(
                company="Elrefae",
                cost_center=_COST_CENTER,
                project=None,
                department=None,
                source="test_option_b",
            )
            frappe.db.commit()
            frappe.clear_cache(user="test_user2@example.com")
        finally:
            frappe.set_user("Administrator")

    def _set_bypass_context(self, scope_report, report_name="General Ledger", user="test_user2@example.com"):
        """Set a valid structured bypass context for the test user."""
        scope_report.frappe.flags.scope_report_bypass = {
            "report_name": report_name,
            "user": user,
        }

    def test_user_has_active_scope_context_returns_true_with_scope(self):
        from construction.overrides.scope_report import _user_has_active_scope_context

        self._set_scope()
        result = _user_has_active_scope_context("test_user2@example.com")
        self.assertTrue(result)

    def test_user_has_active_scope_context_returns_false_without_scope(self):
        from construction.overrides.scope_report import _user_has_active_scope_context

        # No scope set.
        result = _user_has_active_scope_context("test_user2@example.com")
        self.assertFalse(result)

    def test_user_has_active_scope_context_returns_false_for_admin(self):
        from construction.overrides.scope_report import _user_has_active_scope_context

        # Administrator is always bypassed.
        result = _user_has_active_scope_context("Administrator")
        self.assertFalse(result)

    def test_user_has_active_scope_context_returns_false_when_flag_off(self):
        from construction.overrides.scope_report import _user_has_active_scope_context

        self._set_scope()
        _disable_scope()
        try:
            result = _user_has_active_scope_context("test_user2@example.com")
            self.assertFalse(result, "Should be False when enable_scope_context is off")
        finally:
            _enable_scope()

    def test_report_is_permitted_bypassed_for_allowlisted_with_scope(self):
        from frappe.core.doctype.report.report import Report

        from construction.overrides import scope_report

        self._set_scope()
        # Check that is_permitted on a General Ledger doc returns True
        # for the scoped user (without them having any role on it).
        doc = frappe.get_doc("Report", "General Ledger")
        frappe.set_user("test_user2@example.com")
        try:
            self.assertTrue(doc.is_permitted())
        finally:
            frappe.set_user("Administrator")

    def test_report_is_permitted_not_bypassed_without_scope(self):
        from frappe.core.doctype.report.report import Report

        # No scope.
        doc = frappe.get_doc("Report", "General Ledger")
        frappe.set_user("test_user2@example.com")
        try:
            # The report has Has Role rows; site.engineer doesn't match.
            self.assertFalse(doc.is_permitted())
        finally:
            frappe.set_user("Administrator")

    def test_report_is_permitted_not_bypassed_for_non_allowlisted(self):
        from frappe.core.doctype.report.report import Report

        self._set_scope()
        # Find a non-allowlisted report. Use Sales Analytics if it
        # exists; otherwise create a dummy check.
        if frappe.db.exists("Report", "Sales Analytics"):
            doc = frappe.get_doc("Report", "Sales Analytics")
            frappe.set_user("test_user2@example.com")
            try:
                # Even with scope, Sales Analytics (not in allowlist) must
                # not be bypassed.
                self.assertFalse(doc.is_permitted())
            finally:
                frappe.set_user("Administrator")

    def test_get_report_doc_bypassed_for_allowlisted_with_scope(self):
        from frappe.desk.query_report import get_report_doc

        self._set_scope()
        # Should not raise.
        frappe.set_user("test_user2@example.com")
        try:
            doc = get_report_doc("General Ledger")
            self.assertEqual(doc.name, "General Ledger")
        finally:
            frappe.set_user("Administrator")

    def test_get_report_doc_not_bypassed_without_scope(self):
        import frappe.exceptions
        from frappe.desk.query_report import get_report_doc

        # No scope.
        frappe.set_user("test_user2@example.com")
        try:
            with self.assertRaises(frappe.exceptions.PermissionError):
                get_report_doc("General Ledger")
        finally:
            frappe.set_user("Administrator")

    def test_get_report_doc_not_bypassed_for_non_allowlisted_without_scope(self):
        import frappe.exceptions
        from frappe.desk.query_report import get_report_doc

        self._set_scope()
        # Sales Analytics (if exists) is not in the allowlist, so
        # the bypass should NOT fire even with scope.
        if frappe.db.exists("Report", "Sales Analytics"):
            frappe.set_user("test_user2@example.com")
            try:
                with self.assertRaises(frappe.exceptions.PermissionError):
                    get_report_doc("Sales Analytics")
            finally:
                frappe.set_user("Administrator")

    def test_has_permission_bypassed_for_report_perm(self):
        from construction.overrides import scope_report

        self._set_scope()
        # With scope + structured bypass context for GL Entry,
        # `report` perm must be granted.
        self._set_bypass_context(scope_report)
        try:
            frappe.set_user("test_user2@example.com")
            try:
                result = scope_report.frappe.has_permission("GL Entry", "report")
                self.assertTrue(result, "report perm should be granted with scope")
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_has_permission_bypassed_for_select_perm(self):
        from construction.overrides import scope_report

        self._set_scope()
        self._set_bypass_context(scope_report)
        try:
            frappe.set_user("test_user2@example.com")
            try:
                result = scope_report.frappe.has_permission("GL Entry", "select")
                self.assertTrue(result, "select perm should be granted with scope")
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_has_permission_bypassed_for_read_perm(self):
        from construction.overrides import scope_report

        self._set_scope()
        self._set_bypass_context(scope_report)
        try:
            frappe.set_user("test_user2@example.com")
            try:
                result = scope_report.frappe.has_permission("GL Entry", "read")
                self.assertTrue(result, "read perm should be granted with scope")
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_has_permission_not_bypassed_without_flag(self):
        from construction.overrides import scope_report

        self._set_scope()
        # No structured context set. The original check should run.
        result = scope_report.frappe.has_permission("GL Entry", "select", user="test_user2@example.com")
        self.assertFalse(result, "select perm should be denied without flag")

    def test_has_permission_bypassed_for_secondary_doctype_select(self):
        """The bypass is report-scoped: the report's SQL builder
        may query secondary doctypes (e.g. AP queries Purchase
        Invoice, GL Entry, Journal Entry). For SELECT/READ ptypes,
        the bypass MUST apply to those secondary doctypes. The
        data is constrained by the L1+L2 wrappers."""
        from construction.overrides import scope_report

        self._set_scope()
        self._set_bypass_context(scope_report)
        try:
            frappe.set_user("test_user2@example.com")
            try:
                # SELECT and READ on a secondary doctype must be
                # granted under the report-scoped bypass.
                for ptype in ("select", "read"):
                    result = scope_report.frappe.has_permission("Journal Entry", ptype)
                    self.assertTrue(
                        result,
                        f"Journal Entry.{ptype} must be granted by report-scoped bypass",
                    )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_has_permission_not_bypassed_for_unrelated_ptype_on_secondary_doctype(self):
        """Even for secondary doctypes, write/delete/create etc.
        must NOT be granted by the bypass. Only the small
        allowlist of ptypes (report, select, read) is allowed."""
        from construction.overrides import scope_report

        self._set_scope()
        self._set_bypass_context(scope_report)
        try:
            frappe.set_user("test_user2@example.com")
            try:
                for ptype in ("write", "delete", "create", "submit", "cancel", "amend"):
                    result = scope_report.frappe.has_permission("Journal Entry", ptype)
                    self.assertFalse(
                        result,
                        f"Journal Entry.{ptype} must NOT be granted by bypass",
                    )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_has_permission_not_bypassed_for_disallowed_ptype(self):
        """P0 narrowing: only the small allowlist of ptypes
        (report, select, read) may be granted. Other ptypes
        (write, delete, create, submit) must be denied."""
        from construction.overrides import scope_report

        self._set_scope()
        self._set_bypass_context(scope_report)
        try:
            frappe.set_user("test_user2@example.com")
            try:
                # Even for the report's own ref_doctype, write/delete
                # must be denied. The cache from a previous
                # bypass-ON call must NOT leak into a non-bypass
                # call.
                for ptype in ("write", "delete", "create", "submit", "cancel", "amend"):
                    result = scope_report.frappe.has_permission("GL Entry", ptype)
                    self.assertFalse(
                        result,
                        f"GL Entry.{ptype} must NOT be granted by bypass",
                    )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_has_permission_not_bypassed_for_cross_user_leak(self):
        """P0 narrowing: the structured context's user must match
        the session user. A scoped user A cannot grant perms for
        scoped user B's request by manipulating the flag."""
        from construction.overrides import scope_report

        self._set_scope()
        # Set the flag for a DIFFERENT user.
        scope_report.frappe.flags.scope_report_bypass = {
            "report_name": "General Ledger",
            "user": "other_user@example.com",
        }
        try:
            frappe.set_user("test_user2@example.com")
            try:
                result = scope_report.frappe.has_permission("GL Entry", "select")
                self.assertFalse(
                    result,
                    "Cross-user flag must not grant perm to a different session user",
                )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_has_permission_not_bypassed_with_bool_flag(self):
        """P0 narrowing: a boolean True (the old API) must NOT
        grant perm — the new gate requires a structured dict."""
        from construction.overrides import scope_report

        self._set_scope()
        # Set the old-style boolean flag. Must NOT grant perm.
        scope_report.frappe.flags.scope_report_bypass = True
        try:
            frappe.set_user("test_user2@example.com")
            try:
                result = scope_report.frappe.has_permission("GL Entry", "select")
                self.assertFalse(
                    result,
                    "Boolean flag must not grant perm — only structured dict does",
                )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_has_permission_not_bypassed_when_scope_cleared(self):
        """P0 narrowing: if the scope context is cleared after
        the flag is set, the bypass must be refused."""
        from construction.overrides import scope_report

        self._set_scope()
        self._set_bypass_context(scope_report)
        try:
            # Clear the scope doc. The structured-context validator
            # checks `_user_has_active_scope_context(user)` on every
            # call, so the bypass must refuse.
            frappe.db.delete("User Scope Context", {"user": "test_user2@example.com"})
            frappe.db.commit()
            frappe.clear_cache(user="test_user2@example.com")
            frappe.set_user("test_user2@example.com")
            try:
                result = scope_report.frappe.has_permission("GL Entry", "select")
                self.assertFalse(
                    result,
                    "Bypass must refuse when scope context is cleared",
                )
            finally:
                frappe.set_user("Administrator")
        finally:
            # Restore the scope so tearDown can clean up cleanly.
            self._set_scope()
            scope_report.clear_bypass_context()

    def test_has_permission_not_bypassed_for_non_allowlisted_report(self):
        """P0 narrowing: a non-allowlisted report in the flag must
        not grant perm. This catches an over-broad flag setter."""
        from construction.overrides import scope_report

        self._set_scope()
        scope_report.frappe.flags.scope_report_bypass = {
            "report_name": "Sales Analytics",  # NOT in allowlist
            "user": "test_user2@example.com",
        }
        try:
            frappe.set_user("test_user2@example.com")
            try:
                result = scope_report.frappe.has_permission("Sales Order", "select")
                self.assertFalse(
                    result,
                    "Non-allowlisted report must not grant perm",
                )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_get_role_permissions_bypassed_with_scope(self):
        from construction.overrides import scope_report

        self._set_scope()
        self._set_bypass_context(scope_report)
        try:
            # The cross-user check requires session.user == flag.user.
            frappe.set_user("test_user2@example.com")
            try:
                meta = frappe.get_meta("GL Entry")
                result = scope_report.frappe.permissions.get_role_permissions(
                    meta, user="test_user2@example.com"
                )
                # Should be permissive — read should be truthy.
                self.assertTrue(
                    result.get("read") or result.get("select"),
                    "get_role_permissions should be permissive with scope",
                )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_get_role_permissions_overrides_only_allowlisted_ptypes(self):
        """P0 narrowing: the bypass overrides ONLY the allowlisted
        ptypes (report, select, read) in the returned perms dict.
        write/delete/create remain 0 even with the bypass active."""
        from construction.overrides import scope_report

        self._set_scope()
        self._set_bypass_context(scope_report)
        try:
            frappe.set_user("test_user2@example.com")
            try:
                meta = frappe.get_meta("Project")
                result = scope_report.frappe.permissions.get_role_permissions(
                    meta, user="test_user2@example.com"
                )
                # report, select, read should be 1 (bypass).
                for ptype in ("report", "select", "read"):
                    self.assertEqual(
                        result.get(ptype),
                        1,
                        f"Project.{ptype} must be 1 (bypass active)",
                    )
                # write, delete, create should be 0 (not in
                # allowlist, original perms are 0 for test_user2).
                for ptype in ("write", "delete", "create", "submit", "cancel", "amend"):
                    self.assertNotEqual(
                        result.get(ptype),
                        1,
                        f"Project.{ptype} must NOT be 1 (bypass active)",
                    )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_get_permitted_fields_bypassed_with_scope(self):
        from construction.overrides import scope_report

        self._set_scope()
        self._set_bypass_context(scope_report)
        try:
            frappe.set_user("test_user2@example.com")
            try:
                result = scope_report.frappe.model.get_permitted_fields(
                    "GL Entry", user="test_user2@example.com"
                )
                # Should include all valid columns (including posting_date).
                self.assertIn("posting_date", result)
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_get_permitted_fields_bypassed_for_secondary_doctype(self):
        """The bypass is report-scoped: the report's SQL builder
        may query secondary doctypes, so get_permitted_fields
        must return all columns for those doctypes."""
        from construction.overrides import scope_report

        self._set_scope()
        self._set_bypass_context(scope_report)
        try:
            frappe.set_user("test_user2@example.com")
            try:
                result = scope_report.frappe.model.get_permitted_fields(
                    "Project", user="test_user2@example.com"
                )
                # All valid Project columns should be in the result.
                all_cols = set(frappe.get_meta("Project").get_valid_columns())
                self.assertTrue(
                    all_cols.issubset(set(result)),
                    "get_permitted_fields must return all columns for a secondary doctype under report-scoped bypass",
                )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    def test_get_report_doc_does_not_set_bypass_flag(self):
        """P0 regression: `get_report_doc()` must NOT set
        `frappe.flags.scope_report_bypass`. Only `_scope_aware_run`
        (which is wrapped in `try/finally`) is allowed to set the
        flag. Otherwise the `get_script` path would leave the
        flag active for the rest of the request, allowing
        `has_permission("Project", "read")` and similar to be
        wrongly granted via a stale flag."""
        from frappe.desk.query_report import get_report_doc

        from construction.overrides import scope_report

        self._set_scope()
        # Make sure no stale flag survives setUp.
        scope_report.clear_bypass_context()
        try:
            frappe.set_user("test_user2@example.com")
            try:
                # Call get_report_doc as the restricted user.
                # This is the entry point for `get_script`.
                doc = get_report_doc("General Ledger")
                self.assertEqual(doc.name, "General Ledger")
                # CRITICAL: the bypass flag MUST NOT be set.
                self.assertFalse(
                    hasattr(frappe.flags, "scope_report_bypass")
                    and getattr(frappe.flags, "scope_report_bypass", None) is not None,
                    "get_report_doc must NOT set scope_report_bypass",
                )
                # And the very next perm check on an unrelated
                # doctype must NOT be granted via a stale flag.
                result = scope_report.frappe.has_permission("Project", "read")
                self.assertFalse(
                    result,
                    "Project.read must NOT be granted after get_report_doc (no stale flag)",
                )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()

    # ── Option B admin toggle tests ──────────────────────────────

    def _disable_option_b_toggle(self):
        frappe.db.set_single_value(
            "Construction Settings", "enable_option_b_report_access_bypass", 0
        )
        frappe.db.commit()
        frappe.clear_cache()

    def _enable_option_b_toggle(self):
        frappe.db.set_single_value(
            "Construction Settings", "enable_option_b_report_access_bypass", 1
        )
        frappe.db.commit()
        frappe.clear_cache()

    def test_option_b_toggle_off_blocks_has_active_scope_context(self):
        from construction.overrides.scope_report import _user_has_active_scope_context

        self._set_scope()
        self._disable_option_b_toggle()
        try:
            result = _user_has_active_scope_context("test_user2@example.com")
            self.assertFalse(result, "Should be False when Option B toggle is off")
        finally:
            self._enable_option_b_toggle()

    def test_option_b_toggle_off_blocks_report_is_permitted(self):
        from frappe.core.doctype.report.report import Report

        self._set_scope()
        self._disable_option_b_toggle()
        try:
            doc = frappe.get_doc("Report", "General Ledger")
            frappe.set_user("test_user2@example.com")
            try:
                self.assertFalse(doc.is_permitted())
            finally:
                frappe.set_user("Administrator")
        finally:
            self._enable_option_b_toggle()

    def test_option_b_toggle_off_blocks_get_report_doc(self):
        import frappe.exceptions
        from frappe.desk.query_report import get_report_doc

        self._set_scope()
        self._disable_option_b_toggle()
        try:
            frappe.set_user("test_user2@example.com")
            try:
                with self.assertRaises(frappe.exceptions.PermissionError):
                    get_report_doc("General Ledger")
            finally:
                frappe.set_user("Administrator")
        finally:
            self._enable_option_b_toggle()


if __name__ == "__main__":
    import unittest as _unittest

    _unittest.main()
