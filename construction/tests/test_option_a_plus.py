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
            self.assertIsInstance(
                result[key], bool, f"{key} should be a bool, got {type(result[key])}"
            )

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
            frappe.db.delete(
                "User Scope Context", {"user": "test_user2@example.com"}
            )
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
            frappe.get_doc(
                {"doctype": "Role", "role_name": "Accounts User"}
            ).insert(ignore_permissions=True)

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


if __name__ == "__main__":
    import unittest as _unittest
    _unittest.main()
