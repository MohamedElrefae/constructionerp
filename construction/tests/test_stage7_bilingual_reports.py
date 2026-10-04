"""Stage 7 bilingual-report pilot — API tests (site-context bench tests).

Extends the Stage-4 extension-point suite: endpoint surface behavior
(fail-closed report allowlist, mode normalization, pure transform
round-trip with a stub vendor execute), plus the Tier-5E statement
expansion (Balance Sheet / Profit and Loss Statement: allowlist,
single-execute, period defaults, genuine-auth extension).
"""

import contextlib
import unittest
from unittest import mock


def _stub_module(columns, data):
    import types

    mod = types.ModuleType("vendor.stub")
    mod.execute = mock.Mock(return_value=(columns, data))
    return mod


@contextlib.contextmanager
def _patched_report_modules(mapping):
    """Intercept frappe.get_module for report module paths only.

    Tier-5E hardening (the blanket patch breaks frappe internals): DocType
    controller imports and hook attr resolution (`frappe.get_attr`) must
    keep the real importer, because `_ensure_required` touches DB/meta
    paths (Fiscal Year bounds) while the patch is active. Yields the list
    of vendor report paths actually resolved during the block.
    """
    import frappe

    from construction.api.bilingual_reports import PILOT_REPORTS

    real = frappe.get_module
    vendor_paths = set(PILOT_REPORTS.values()) | set(mapping)
    resolved = []

    def _dispatch(name, *args, **kwargs):
        if name in vendor_paths:
            resolved.append(name)
            if name in mapping:
                return mapping[name]
            return mock.Mock(name=f"unexpected_vendor_resolution:{name}")
        return real(name, *args, **kwargs)

    with mock.patch("frappe.get_module", side_effect=_dispatch):
        yield resolved


class TestBilingualReportsAPI(unittest.TestCase):
    def _call(self, name, mock_module, mode=None, lang=None, filters=None):
        with mock.patch("frappe.get_module", return_value=mock_module), mock.patch(
            "frappe.only_for", lambda *a, **k: None
        ):
            from construction.api.bilingual_reports import localized_report

            return localized_report(name, filters=filters, lang=lang, mode=mode)

    def test_unknown_report_fails_closed(self):
        import frappe

        before = frappe.get_all("Account", limit=1)  # realtime site reachable
        with self.assertRaises(frappe.ValidationError):
            self._call("Sales Register", _stub_module([], []))

    def test_ar_mode_localizes_account_label(self):
        # R2b: patch the API module's own binding — patching the service
        # attribute only does not intercept (the API binds its global at import,
        # so earlier tests were passing by import-order luck).
        import construction.api.bilingual_reports as api_mod

        mod = _stub_module(
            [{"fieldname": "account", "label": "Account"}],
            [{"account": "Rent", "debit": 100}],
        )
        with mock.patch.object(
            api_mod, "load_account_arabic_mapping", return_value={"Rent": "إيجار"}
        ):
            out = self._call("Trial Balance", mod, mode="ar")
        self.assertEqual(out["mode"], "ar")
        self.assertEqual(out["data"][0]["account"], "إيجار")
        self.assertEqual(out["data"][0]["debit"], 100)

    def test_both_mode_keeps_identity_prefix(self):
        import construction.api.bilingual_reports as api_mod

        mod = _stub_module([{"fieldname": "account"}], [{"account": "Rent"}])
        with mock.patch.object(
            api_mod, "load_account_arabic_mapping", return_value={"Rent": "إيجار"}
        ):
            out = self._call("Trial Balance", mod, mode="both")
        self.assertEqual(out["data"][0]["account"], "Rent — إيجار")

    def test_en_mode_untouched(self):
        import construction.api.bilingual_reports as api_mod

        mod = _stub_module([{"fieldname": "account"}], [{"account": "Rent"}])
        with mock.patch.object(
            api_mod, "load_account_arabic_mapping", return_value={"Rent": "إيجار"}
        ):
            out = self._call("Trial Balance", mod, mode="en")
        self.assertEqual(out["data"][0]["account"], "Rent")


class TestStatementAllowlist(unittest.TestCase):
    """Tier 5E: Balance Sheet + Profit and Loss Statement join the allowlist
    under the unchanged fail-closed / single-execute / role-gate contract."""

    STATEMENTS = ("Balance Sheet", "Profit and Loss Statement")

    def _call(self, name, mock_module, mode=None, filters=None):
        from construction.api.bilingual_reports import PILOT_REPORTS, localized_report

        with mock.patch("frappe.only_for", lambda *a, **k: None), _patched_report_modules(
            {PILOT_REPORTS[name]: mock_module}
        ):
            return localized_report(name, filters=filters, mode=mode)

    def test_statement_reports_in_allowlist(self):
        import frappe

        from construction.api.bilingual_reports import PILOT_REPORTS

        for name in self.STATEMENTS:
            self.assertIn(name, PILOT_REPORTS)
            path = PILOT_REPORTS[name]
            self.assertNotIn(".execute", path, f"{name} module path must stay importable")
            mod = frappe.get_module(path)
            self.assertTrue(callable(getattr(mod, "execute", None)), name)

    def test_statement_execute_runs_exactly_once(self):
        import construction.api.bilingual_reports as api_mod

        for name in self.STATEMENTS:
            mod = _stub_module([{"fieldname": "account"}], [{"account": "Cash"}])
            with mock.patch.object(
                api_mod, "load_account_arabic_mapping", return_value={}
            ):
                out = self._call(name, mod, mode="ar", filters='{"company": "Elrefae"}')
            self.assertEqual(mod.execute.call_count, 1, name)
            self.assertEqual(out["report_name"], name)
            self.assertEqual(out["mode"], "ar")

    def test_statement_ar_mode_localizes_account_name(self):
        import construction.api.bilingual_reports as api_mod

        mod = _stub_module(
            [
                {"fieldname": "account", "label": "Account"},
                {"fieldname": "account_name", "label": "Account Name"},
            ],
            [{"account": "Cash", "account_name": "Cash in Hand"}],
        )
        with mock.patch.object(
            api_mod,
            "load_account_arabic_mapping",
            return_value={"Cash in Hand": "النقدية"},
        ):
            out = self._call(
                "Balance Sheet", mod, mode="ar", filters='{"company": "Elrefae"}'
            )
        self.assertEqual(out["data"][0]["account_name"], "النقدية")
        self.assertEqual(out["data"][0]["account"], "Cash")

    def test_statement_period_defaults_date_range(self):
        # viewer from_date/to_date drive the Date Range window; R4 defaults
        # fill only what the caller omitted.
        for name in self.STATEMENTS:
            mod = _stub_module([], [])
            self._call(
                name,
                mod,
                mode="en",
                filters='{"company": "Elrefae", "from_date": "2026-01-01", "to_date": "2026-10-05"}',
            )
            f = mod.execute.call_args.kwargs["filters"]
            self.assertEqual(f.get("filter_based_on"), "Date Range", name)
            self.assertEqual(f.get("periodicity"), "Yearly", name)
            self.assertEqual(f.get("period_start_date"), "2026-01-01", name)
            self.assertEqual(f.get("period_end_date"), "2026-10-05", name)
            self.assertEqual(f.get("accumulated_values"), 0, name)

    def test_statement_period_defaults_fiscal_year_and_fallback(self):
        # explicit Fiscal Year mode resolves the fiscal years; omitted dates
        # fall back to the company fiscal-year bounds (both stay read-only).
        mod = _stub_module([], [])
        self._call(
            "Balance Sheet",
            mod,
            mode="en",
            filters='{"company": "Elrefae", "filter_based_on": "Fiscal Year", "fiscal_year": "2026"}',
        )
        f = mod.execute.call_args.kwargs["filters"]
        self.assertEqual(f.get("from_fiscal_year"), "2026")
        self.assertEqual(f.get("to_fiscal_year"), "2026")

        mod = _stub_module([], [])
        self._call("Profit and Loss Statement", mod, mode="en", filters=None)
        f = mod.execute.call_args.kwargs["filters"]
        self.assertTrue(f.get("period_start_date"))
        self.assertTrue(f.get("period_end_date"))
        self.assertLessEqual(f["period_start_date"], f["period_end_date"])

    def test_statement_caller_values_win(self):
        mod = _stub_module([], [])
        self._call(
            "Balance Sheet",
            mod,
            mode="en",
            filters='{"company": "Elrefae", "periodicity": "Monthly", "filter_based_on": "Date Range", "period_start_date": "2026-03-01", "period_end_date": "2026-03-31", "accumulated_values": 1}',
        )
        f = mod.execute.call_args.kwargs["filters"]
        self.assertEqual(f.get("periodicity"), "Monthly")
        self.assertEqual(f.get("period_start_date"), "2026-03-01")
        self.assertEqual(f.get("period_end_date"), "2026-03-31")
        self.assertEqual(f.get("accumulated_values"), 1)


class TestRealModuleSmoke(unittest.TestCase):
    """Unmocked smoke: every pilot path is a real importable module exposing a
    callable execute (P1 review note: function paths cannot be imported)."""

    def test_pilot_modules_import_and_expose_execute(self):
        import frappe

        from construction.api.bilingual_reports import PILOT_REPORTS

        for name, path in PILOT_REPORTS.items():
            self.assertNotIn(".execute", path, f"{name} module path must stay importable")
            mod = frappe.get_module(path)
            self.assertTrue(callable(getattr(mod, "execute", None)), name)

    def test_malformed_filters_fail_closed(self):
        import frappe

        with mock.patch("frappe.only_for", lambda *a, **k: None):
            from construction.api.bilingual_reports import localized_report

            with self.assertRaises(frappe.ValidationError):
                localized_report("Trial Balance", filters="{not-json", mode="ar")

    def test_non_object_filters_fail_closed(self):
        # P2 review note: valid JSON that is not an object must be rejected
        import frappe

        with mock.patch("frappe.only_for", lambda *a, **k: None):
            from construction.api.bilingual_reports import localized_report

            for bad in ("[]", "null", "42", '"str"', "7.5"):
                with self.assertRaises(frappe.ValidationError, msg=bad):
                    localized_report("Trial Balance", filters=bad, mode="ar")

    def test_non_object_native_filters_fail_closed(self):
        import frappe

        with mock.patch("frappe.only_for", lambda *a, **k: None):
            from construction.api.bilingual_reports import localized_report

            for native in ([], 42, "x"):
                with self.assertRaises(frappe.ValidationError, msg=str(native)):
                    localized_report("Trial Balance", filters=native, mode="ar")

    def test_object_filters_accepted(self):
        with mock.patch("frappe.only_for", lambda *a, **k: None), mock.patch(
            "frappe.get_module"
        ) as gm:
            gm.return_value.execute = mock.Mock(return_value=([], []))
            from construction.api.bilingual_reports import localized_report

            out = localized_report("Trial Balance", mode="ar", filters='{"company": "Elrefae"}')
            self.assertEqual(gm.return_value.execute.call_count, 1)
            self.assertEqual(out["mode"], "ar")


class TestGenuineAuthorization(unittest.TestCase):
    """AGENTS.md §4.7: the role gate must hold for a real user, unmocked."""

    USER = "ct-finance-noperm@example.com"

    def test_non_admin_without_accounts_roles_is_rejected_before_execute(self):
        import frappe

        if not frappe.db.exists("User", self.USER):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": self.USER,
                    "first_name": "CT",
                    "new_password": "ct-test-pw-123",
                    "user_type": "System User",
                    "send_welcome_email": 0,
                    "roles": [],
                }
            ).insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.set_user(self.USER)
        try:
            with _patched_report_modules({}) as resolved:
                from construction.api.bilingual_reports import localized_report

                with self.assertRaises(frappe.PermissionError):
                    localized_report("Trial Balance", filters=None, mode="ar")
                # Tier 5E: the same gate holds for the statement names.
                with self.assertRaises(frappe.PermissionError):
                    localized_report("Balance Sheet", filters=None, mode="ar")
                self.assertEqual(
                    resolved, [], "vendor module must not be resolved for a rejected user"
                )
        finally:
            frappe.set_user("Administrator")
            if frappe.db.exists("User", self.USER):
                frappe.delete_doc("User", self.USER, force=True, ignore_permissions=True)
            frappe.db.commit()

        from construction.api.bilingual_reports import PILOT_REPORTS

        stub = _stub_module([{"fieldname": "account"}], [{"account": "Cash"}])
        with _patched_report_modules({PILOT_REPORTS["Trial Balance"]: stub}):
            from construction.api.bilingual_reports import localized_report

            out = localized_report("Trial Balance", filters='{"company": "Elrefae"}', mode="ar")
        self.assertEqual(stub.execute.call_count, 1)
        self.assertEqual(out["report_name"], "Trial Balance")
