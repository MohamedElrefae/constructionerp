"""Stage 7 bilingual-report pilot — API tests (site-context bench tests).

Extends the Stage-4 extension-point suite: endpoint surface behavior
(fail-closed report allowlist, mode normalization, pure transform
round-trip with a stub vendor execute), plus the Tier-5E statement
expansion (Balance Sheet / Profit and Loss Statement: allowlist,
single-execute, period defaults, genuine-auth extension), and the
Stage-7 report expansion (Accounts Receivable Summary, Accounts Payable
Summary, Cash Flow: allowlist, report-specific defaults, localized column
headers, mutation guard, genuine-auth extension).
"""

import contextlib
import unittest
from unittest import mock

from frappe.tests.utils import FrappeTestCase


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




def _default_company():
    import frappe

    return frappe.db.get_single_value("Global Defaults", "default_company") or "Elrefae"


class TestBilingualReportsAPI(unittest.TestCase):
    def _call(self, name, mock_module, mode=None, lang=None, filters=None):
        import construction.api.bilingual_reports as api_mod
        from construction.api.bilingual_reports import PILOT_REPORTS

        with (
            _patched_report_modules({PILOT_REPORTS[name]: mock_module}),
            mock.patch("frappe.only_for", lambda *a, **k: None),
            mock.patch.object(api_mod, "_check_report_access"),
        ):
            from construction.api.bilingual_reports import localized_report

            return localized_report(name, filters=filters, lang=lang, mode=mode)

    def test_unknown_report_fails_closed(self):
        import frappe

        from construction.api.bilingual_reports import localized_report

        before = frappe.get_all("Account", limit=1)  # realtime site reachable
        with self.assertRaises(frappe.ValidationError):
            with mock.patch("frappe.only_for", lambda *a, **k: None):
                localized_report("Sales Register", filters=None, mode="ar")

    def test_ar_mode_localizes_account_label(self):
        # R2b: patch the API module's own binding — patching the service
        # attribute only does not intercept (the API binds its global at import,
        # so earlier tests were passing by import-order luck).
        import construction.api.bilingual_reports as api_mod

        mod = _stub_module(
            [{"fieldname": "account", "label": "Account"}],
            [{"account": "Rent", "debit": 100}],
        )
        with mock.patch.object(api_mod, "load_account_arabic_mapping", return_value={"Rent": "إيجار"}):
            out = self._call("Trial Balance", mod, mode="ar")
        self.assertEqual(out["mode"], "ar")
        self.assertEqual(out["data"][0]["account"], "إيجار")
        self.assertEqual(out["data"][0]["debit"], 100)

    def test_both_mode_keeps_identity_prefix(self):
        import construction.api.bilingual_reports as api_mod

        mod = _stub_module([{"fieldname": "account"}], [{"account": "Rent"}])
        with mock.patch.object(api_mod, "load_account_arabic_mapping", return_value={"Rent": "إيجار"}):
            out = self._call("Trial Balance", mod, mode="both")
        self.assertEqual(out["data"][0]["account"], "Rent — إيجار")

    def test_en_mode_untouched(self):
        import construction.api.bilingual_reports as api_mod

        mod = _stub_module([{"fieldname": "account"}], [{"account": "Rent"}])
        with mock.patch.object(api_mod, "load_account_arabic_mapping", return_value={"Rent": "إيجار"}):
            out = self._call("Trial Balance", mod, mode="en")
        self.assertEqual(out["data"][0]["account"], "Rent")


class TestStatementAllowlist(unittest.TestCase):
    """Tier 5E: Balance Sheet + Profit and Loss Statement join the allowlist
    under the unchanged fail-closed / single-execute / role-gate contract."""

    STATEMENTS = ("Balance Sheet", "Profit and Loss Statement")

    def _call(self, name, mock_module, mode=None, filters=None):
        import construction.api.bilingual_reports as api_mod
        from construction.api.bilingual_reports import PILOT_REPORTS, localized_report

        with (
            mock.patch("frappe.only_for", lambda *a, **k: None),
            mock.patch.object(api_mod, "_check_report_access"),
            _patched_report_modules({PILOT_REPORTS[name]: mock_module}),
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
            with mock.patch.object(api_mod, "load_account_arabic_mapping", return_value={}):
                out = self._call(name, mod, mode="ar", filters='{"company": "' + _default_company() + '"}')
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
            out = self._call("Balance Sheet", mod, mode="ar", filters='{"company": "' + _default_company() + '"}')
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
                filters='{"company": "' + _default_company() + '", "from_date": "2026-01-01", "to_date": "2026-10-05"}',
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
            filters='{"company": "' + _default_company() + '", "filter_based_on": "Fiscal Year", "fiscal_year": "2026"}',
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
            filters='{"company": "' + _default_company() + '", "periodicity": "Monthly", "filter_based_on": "Date Range", "period_start_date": "2026-03-01", "period_end_date": "2026-03-31", "accumulated_values": 1}',
        )
        f = mod.execute.call_args.kwargs["filters"]
        self.assertEqual(f.get("periodicity"), "Monthly")
        self.assertEqual(f.get("period_start_date"), "2026-03-01")
        self.assertEqual(f.get("period_end_date"), "2026-03-31")
        self.assertEqual(f.get("accumulated_values"), 1)


class TestExpandedReportAllowlist(unittest.TestCase):
    """Stage 7 report expansion: Accounts Receivable Summary, Accounts Payable
    Summary and Cash Flow join the fail-closed allowlist under the unchanged
    single-execute / genuine-authorization contract, with report-specific
    read-only defaults and localized column headers."""

    EXPANDED = ("Accounts Receivable Summary", "Accounts Payable Summary", "Cash Flow")
    MISSION = ("General Ledger", "Trial Balance", "Accounts Receivable Summary",
               "Accounts Payable Summary", "Cash Flow")

    def _call(self, name, mock_module, mode=None, filters=None):
        from construction.api.bilingual_reports import PILOT_REPORTS, localized_report

        with mock.patch("frappe.only_for", lambda *a, **k: None), _patched_report_modules(
            {PILOT_REPORTS[name]: mock_module}
        ):
            return localized_report(name, filters=filters, mode=mode)

    def test_mission_reports_in_allowlist(self):
        import frappe

        from construction.api.bilingual_reports import PILOT_REPORTS

        for name in self.MISSION:
            self.assertIn(name, PILOT_REPORTS)
            path = PILOT_REPORTS[name]
            self.assertNotIn(".execute", path, f"{name} module path must stay importable")
            mod = frappe.get_module(path)
            self.assertTrue(callable(getattr(mod, "execute", None)), name)

    def test_expanded_execute_runs_exactly_once(self):
        import construction.api.bilingual_reports as api_mod

        for name in self.EXPANDED:
            mod = _stub_module([{"fieldname": "account"}], [{"account": "Cash"}])
            with mock.patch.object(
                api_mod, "load_account_arabic_mapping", return_value={}
            ):
                out = self._call(name, mod, mode="ar", filters='{"company": "' + _default_company() + '"}')
            self.assertEqual(mod.execute.call_count, 1, name)
            self.assertEqual(out["report_name"], name)
            self.assertEqual(out["mode"], "ar")

    def test_summary_defaults_report_date_window(self):
        # AR/AP Summary subclass the vendor ReceivablePayableReport: the
        # ageing window is `report_date`, defaulted read-only from the
        # viewer's to_date (falling back to the fiscal-year end).
        for name in ("Accounts Receivable Summary", "Accounts Payable Summary"):
            mod = _stub_module([], [])
            self._call(
                name,
                mod,
                mode="en",
                filters='{"company": "' + _default_company() + '", "to_date": "2026-10-05"}',
            )
            f = mod.execute.call_args.kwargs["filters"]
            self.assertEqual(f.get("report_date"), "2026-10-05", name)
            self.assertEqual(f.get("to_date"), "2026-10-05", name)
            self.assertEqual(f.get("ageing_based_on"), "Posting Date", name)
            self.assertTrue(f.get("fiscal_year"), name)

    def test_summary_caller_report_date_wins(self):
        mod = _stub_module([], [])
        self._call(
            "Accounts Payable Summary",
            mod,
            mode="en",
            filters='{"company": "' + _default_company() + '", "report_date": "2026-03-31", "ageing_based_on": "Posting Date"}',
        )
        f = mod.execute.call_args.kwargs["filters"]
        self.assertEqual(f.get("report_date"), "2026-03-31")

    def test_cash_flow_period_defaults(self):
        # Cash Flow consumes the same vendor get_period_list contract as the
        # Tier-5E statements (Date Range driven by the viewer's dates).
        mod = _stub_module([], [])
        self._call(
            "Cash Flow",
            mod,
            mode="en",
            filters='{"company": "' + _default_company() + '", "from_date": "2026-01-01", "to_date": "2026-10-05"}',
        )
        f = mod.execute.call_args.kwargs["filters"]
        self.assertEqual(f.get("filter_based_on"), "Date Range")
        self.assertEqual(f.get("periodicity"), "Yearly")
        self.assertEqual(f.get("period_start_date"), "2026-01-01")
        self.assertEqual(f.get("period_end_date"), "2026-10-05")
        self.assertEqual(f.get("accumulated_values"), 0)

        mod = _stub_module([], [])
        self._call(
            "Cash Flow",
            mod,
            mode="en",
            filters='{"company": "' + _default_company() + '", "filter_based_on": "Fiscal Year", "fiscal_year": "2026", "periodicity": "Monthly"}',
        )
        f = mod.execute.call_args.kwargs["filters"]
        self.assertEqual(f.get("from_fiscal_year"), "2026")
        self.assertEqual(f.get("to_fiscal_year"), "2026")
        self.assertEqual(f.get("periodicity"), "Monthly")

    def test_column_headers_localized_ar_en_both(self):
        labels = ["Posting Date", "Debit (SAR)", "Age (Days)", "Party"]
        mod = _stub_module(
            [{"fieldname": "posting_date", "label": l} for l in labels],
            [{"posting_date": "2026-01-01"}],
        )
        out = self._call("General Ledger", mod, mode="en")
        self.assertEqual([c["label"] for c in out["columns"]], labels)

        mod = _stub_module(
            [{"fieldname": "posting_date", "label": l} for l in labels],
            [{"posting_date": "2026-01-01"}],
        )
        out = self._call("General Ledger", mod, mode="ar")
        self.assertEqual(
            [c["label"] for c in out["columns"]],
            ["تاريخ الترحيل", "مدين (SAR)", "Age (Days)", "الطرف"],
        )

        mod = _stub_module(
            [{"fieldname": "posting_date", "label": l} for l in labels],
            [{"posting_date": "2026-01-01"}],
        )
        out = self._call("General Ledger", mod, mode="both")
        self.assertEqual(
            [c["label"] for c in out["columns"]][0],
            "Posting Date — تاريخ الترحيل",
        )
        self.assertEqual([c["label"] for c in out["columns"]][2], "Age (Days)")

    def test_column_headers_pure_source_untouched(self):
        # the vendor's column structures must never be mutated in place
        source = [{"fieldname": "debit", "label": "Debit"}]
        mod = _stub_module(source, [])
        self._call("Trial Balance", mod, mode="ar")
        self.assertEqual(source[0]["label"], "Debit")

    def test_localize_column_label_unit(self):
        from construction.api.bilingual_reports import localize_column_label

        self.assertEqual(localize_column_label("Balance", "ar"), "الرصيد")
        self.assertEqual(localize_column_label("Balance (SAR)", "ar"), "الرصيد (SAR)")
        self.assertEqual(localize_column_label("Balance", "en"), "Balance")
        self.assertEqual(localize_column_label("Age (Days)", "ar"), "Age (Days)")
        self.assertEqual(localize_column_label("", "ar"), "")
        self.assertEqual(
            localize_column_label("Voucher No", "both"), "Voucher No — رقم السند"
        )

    def test_report_path_makes_zero_db_writes(self):
        # mutation guard: no database write primitive may fire while a
        # report renders (probe covers row counts on the live site too)
        import frappe

        def _guard(name):
            def _fail(*a, **k):
                raise AssertionError(f"DB write attempted via frappe.db.{name}")

            return _fail

        for name in self.EXPANDED:
            mod = _stub_module([{"fieldname": "account"}], [{"account": "Cash"}])
            with mock.patch("frappe.only_for", lambda *a, **k: None), mock.patch.object(
                frappe.db, "set_value", _guard("set_value"), create=True
            ), mock.patch.object(frappe.db, "insert", _guard("insert"), create=True), mock.patch.object(
                frappe.db, "delete", _guard("delete"), create=True
            ):
                from construction.api.bilingual_reports import localized_report

                with _patched_report_modules_from_name(name, mod):
                    localized_report(name, filters='{"company": "' + _default_company() + '"}', mode="ar")
            self.assertEqual(mod.execute.call_count, 1, name)


def _patched_report_modules_from_name(report_name, mock_module):
    from construction.api.bilingual_reports import PILOT_REPORTS

    return _patched_report_modules({PILOT_REPORTS[report_name]: mock_module})


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
        import construction.api.bilingual_reports as api_mod
        from construction.api.bilingual_reports import PILOT_REPORTS

        mod = _stub_module([], [])
        with (
            mock.patch("frappe.only_for", lambda *a, **k: None),
            mock.patch.object(api_mod, "_check_report_access"),
            _patched_report_modules({PILOT_REPORTS["Trial Balance"]: mod}),
        ):
            from construction.api.bilingual_reports import localized_report

            out = localized_report("Trial Balance", mode="ar", filters='{"company": "' + _default_company() + '"}')
            self.assertEqual(mod.execute.call_count, 1)
            self.assertEqual(out["mode"], "ar")


class TestGenuineAuthorization(FrappeTestCase):
    """Exercise the report and Company gates with real roles and User Permissions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import frappe

        cls.addClassCleanup(cls._rollback_fixtures)
        companies = frappe.get_all("Company", pluck="name", order_by="name asc")
        if not companies:
            raise AssertionError("Authorization tests require an installed Company fixture.")
        cls.allowed_company = companies[0]
        suffix = frappe.generate_hash(length=8)
        if len(companies) > 1:
            cls.denied_company = companies[1]
        else:
            source = frappe.get_doc("Company", cls.allowed_company)
            denied = frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": f"CT Report Denied {suffix}",
                    "abbr": f"CR{suffix[:4]}",
                    "default_currency": source.default_currency,
                    "country": source.country,
                    "create_chart_of_accounts_based_on": "Existing Company",
                    "existing_company": cls.allowed_company,
                }
            ).insert(ignore_permissions=True)
            cls.denied_company = denied.name
        cls.no_role_user = cls._create_user(f"ct-report-norole-{suffix}@example.test", [])
        cls.accounts_user = cls._create_user(f"ct-report-accounts-{suffix}@example.test", ["Accounts User"])
        frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": cls.accounts_user,
                "allow": "Company",
                "for_value": cls.allowed_company,
                "apply_to_all_doctypes": 1,
                "hide_descendants": 1,
            }
        ).insert(ignore_permissions=True)

    @classmethod
    def _create_user(cls, email, roles):
        import frappe

        return (
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": "CT Report Authorization",
                    "user_type": "System User",
                    "send_welcome_email": 0,
                    "roles": [{"role": role} for role in roles],
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    @classmethod
    def _rollback_fixtures(cls):
        import frappe

        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.clear_cache()

    def test_non_admin_without_accounts_roles_is_rejected_before_report_or_vendor(self):
        import frappe

        frappe.set_user(self.no_role_user)
        try:
            with _patched_report_modules({}) as resolved:
                from construction.api.bilingual_reports import localized_report

                with self.assertRaises(frappe.PermissionError):
                    localized_report("Trial Balance", filters=None, mode="ar")
                with self.assertRaises(frappe.PermissionError):
                    localized_report("Balance Sheet", filters=None, mode="ar")
                # Stage 7 expansion: the new names are rejected before any
                # vendor module resolution for the same non-admin user.
                with self.assertRaises(frappe.PermissionError):
                    localized_report("Accounts Payable Summary", filters=None, mode="ar")
                with self.assertRaises(frappe.PermissionError):
                    localized_report("Cash Flow", filters=None, mode="ar")
                self.assertEqual(
                    resolved, [], "vendor module must not be resolved for a rejected user"
                )
        finally:
            frappe.set_user("Administrator")

    def test_admin_can_read_real_company_and_report_then_execute_stub(self):
        import frappe

        from construction.api.bilingual_reports import PILOT_REPORTS, localized_report

        stub = _stub_module([{"fieldname": "account"}], [{"account": "Cash"}])
        filters = {
            "company": self.allowed_company,
            "filter_based_on": "Date Range",
            "period_start_date": "2026-01-01",
            "period_end_date": "2026-12-31",
        }
        with _patched_report_modules({PILOT_REPORTS["Balance Sheet"]: stub}):
            out = localized_report("Balance Sheet", filters=filters, mode="ar")
        self.assertEqual(stub.execute.call_count, 1)
        self.assertEqual(out["report_name"], "Balance Sheet")

    def test_accounts_user_can_read_assigned_company_and_report(self):
        import frappe

        from construction.api.bilingual_reports import PILOT_REPORTS, localized_report

        stub = _stub_module([{"fieldname": "account"}], [{"account": "Cash"}])
        frappe.set_user(self.accounts_user)
        try:
            with _patched_report_modules({PILOT_REPORTS["Balance Sheet"]: stub}):
                out = localized_report(
                    "Balance Sheet",
                    filters={
                        "company": self.allowed_company,
                        "filter_based_on": "Date Range",
                        "period_start_date": "2026-01-01",
                        "period_end_date": "2026-12-31",
                    },
                    mode="en",
                )
            self.assertEqual(stub.execute.call_count, 1)
            self.assertEqual(out["report_name"], "Balance Sheet")
        finally:
            frappe.set_user("Administrator")

    def test_disabled_native_report_is_rejected_before_vendor_resolution(self):
        import frappe

        from construction.api.bilingual_reports import PILOT_REPORTS, localized_report

        report_name = "Balance Sheet"
        original_disabled = frappe.db.get_value("Report", report_name, "disabled")
        stub = _stub_module([], [])
        try:
            frappe.db.set_value("Report", report_name, "disabled", 1, update_modified=False)
            with _patched_report_modules({PILOT_REPORTS[report_name]: stub}) as resolved:
                with self.assertRaises(frappe.ValidationError):
                    localized_report(
                        report_name,
                        filters={
                            "company": self.allowed_company,
                            "filter_based_on": "Date Range",
                            "period_start_date": "2026-01-01",
                            "period_end_date": "2026-12-31",
                        },
                        mode="en",
                    )
            self.assertEqual(resolved, [])
            stub.execute.assert_not_called()
        finally:
            frappe.db.set_value("Report", report_name, "disabled", original_disabled, update_modified=False)
            frappe.clear_cache(doctype="Report")

    def test_accounts_user_cannot_run_report_for_unassigned_company(self):
        import frappe

        from construction.api.bilingual_reports import PILOT_REPORTS, localized_report

        stub = _stub_module([], [])
        frappe.set_user(self.accounts_user)
        try:
            with _patched_report_modules({PILOT_REPORTS["Balance Sheet"]: stub}) as resolved:
                with self.assertRaises(frappe.PermissionError):
                    localized_report(
                        "Balance Sheet",
                        filters={
                            "company": self.denied_company,
                            "filter_based_on": "Date Range",
                            "period_start_date": "2026-01-01",
                            "period_end_date": "2026-12-31",
                        },
                        mode="en",
                    )
            self.assertEqual(resolved, [], "authorization must fail before resolving vendor report")
            stub.execute.assert_not_called()
        finally:
            frappe.set_user("Administrator")


class TestFiscalYearReportDefaults(FrappeTestCase):
    """Native fiscal-year fixtures prove date anchoring against real ERPNext data.

    FrappeTestCase owns this class's transaction: it rolls back fixture inserts
    on class cleanup. The extra cleanup also clears ERPNext's FY cache after
    rollback so later tests cannot observe rows which no longer exist.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import frappe
        from frappe.utils import add_days, add_years, getdate

        cls.addClassCleanup(cls._rollback_fixtures_and_clear_fiscal_year_cache)
        cls.company = frappe.db.get_value("Company", {}, "name")
        if not cls.company:
            raise AssertionError("Fiscal-year integration tests require an installed Company fixture.")

        cls.created_fiscal_years = []
        cls.target_date = "2026-06-15"
        cls.historical_date = "2024-06-15"
        cls.fiscal_year_2026 = cls._get_or_create_fiscal_year(
            cls.target_date, "2026-01-01", "2026-12-31", "2026"
        )
        cls.fiscal_year_2024 = cls._get_or_create_fiscal_year(
            cls.historical_date, "2024-01-01", "2024-12-31", "2024"
        )

        latest_end = frappe.db.get_value(
            "Fiscal Year", {"disabled": 0}, "year_end_date", order_by="year_end_date desc"
        )
        if not latest_end:
            raise AssertionError("Fiscal-year integration tests require at least one installed Fiscal Year.")
        future_start = add_days(getdate(latest_end), 1)
        future_end = add_days(add_years(future_start, 1), -1)
        cls.future_fiscal_year = cls._create_fiscal_year(
            f"_CT Bilingual Report Future {frappe.generate_hash(length=8)}",
            future_start,
            future_end,
        )

        from erpnext.accounts.utils import get_fiscal_year

        cls.no_year_date = add_days(
            frappe.db.get_value(
                "Fiscal Year", {"disabled": 0}, "year_start_date", order_by="year_start_date asc"
            ),
            -1,
        )
        cls.assert_no_fiscal_year_for_date = not get_fiscal_year(
            date=cls.no_year_date,
            company=cls.company,
            verbose=0,
            as_dict=True,
            raise_on_missing=False,
        )

    @classmethod
    def _rollback_fixtures_and_clear_fiscal_year_cache(cls):
        import frappe

        frappe.db.rollback()
        frappe.cache().delete_key("fiscal_years")

    @classmethod
    def _get_or_create_fiscal_year(cls, reference_date, start_date, end_date, label):
        import frappe
        from erpnext.accounts.utils import get_fiscal_year

        existing = get_fiscal_year(
            date=reference_date,
            company=cls.company,
            verbose=0,
            as_dict=True,
            raise_on_missing=False,
        )
        if existing:
            return existing
        return cls._create_fiscal_year(
            f"_CT Bilingual Report {label} {frappe.generate_hash(length=8)}",
            start_date,
            end_date,
        )

    @classmethod
    def _create_fiscal_year(cls, name, start_date, end_date):
        import frappe

        if frappe.db.exists("Fiscal Year", name):
            raise AssertionError("Generated test Fiscal Year name unexpectedly collided.")
        fiscal_year = frappe.get_doc(
            {
                "doctype": "Fiscal Year",
                "year": name,
                "year_start_date": start_date,
                "year_end_date": end_date,
                "companies": [{"company": cls.company}],
            }
        ).insert(ignore_permissions=True)
        cls.created_fiscal_years.append(fiscal_year.name)
        return fiscal_year

    def _call(self, name, filters, *, today=None, module=None):
        import construction.api.bilingual_reports as api_mod
        from construction.api.bilingual_reports import PILOT_REPORTS, localized_report

        module = module or _stub_module([], [])
        patches = [
            mock.patch("frappe.only_for", lambda *a, **k: None),
            # These tests isolate fiscal defaults and vendor payload. Native
            # report/company authorization is covered by TestGenuineAuthorization.
            mock.patch.object(api_mod, "_check_report_access"),
            _patched_report_modules({PILOT_REPORTS[name]: module}),
            mock.patch.object(api_mod, "load_account_arabic_mapping", return_value={}),
        ]
        if today:
            patches.append(mock.patch("frappe.utils.today", return_value=today))
        with contextlib.ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            response = localized_report(name, filters=filters, mode="en")
        return module, response

    def test_future_configured_year_does_not_hijack_requested_2026_trial_balance(self):
        from erpnext.accounts.utils import get_fiscal_year

        newest_without_date = get_fiscal_year(
            company=self.company, verbose=0, as_dict=True, raise_on_missing=True
        )
        self.assertEqual(newest_without_date.name, self.future_fiscal_year.name)

        module, _response = self._call(
            "Trial Balance",
            {
                "company": self.company,
                "from_date": str(self.fiscal_year_2026.year_start_date),
                "to_date": str(self.fiscal_year_2026.year_end_date),
            },
        )
        report_filters = module.execute.call_args.kwargs["filters"]
        self.assertEqual(report_filters["fiscal_year"], self.fiscal_year_2026.name)
        self.assertEqual(report_filters["from_date"], str(self.fiscal_year_2026.year_start_date))
        self.assertEqual(report_filters["to_date"], str(self.fiscal_year_2026.year_end_date))

    def test_historical_general_ledger_end_uses_the_anchored_fiscal_year(self):
        from frappe.utils import today

        module, _response = self._call(
            "General Ledger",
            {"company": self.company, "from_date": str(self.fiscal_year_2024.year_start_date)},
        )
        report_filters = module.execute.call_args.kwargs["filters"]
        self.assertEqual(report_filters["from_date"], str(self.fiscal_year_2024.year_start_date))
        self.assertEqual(report_filters["to_date"], str(self.fiscal_year_2024.year_end_date))
        self.assertLess(report_filters["to_date"], today())

    def test_explicit_trial_balance_fiscal_year_is_preserved(self):
        module, _response = self._call(
            "Trial Balance",
            {
                "company": self.company,
                "fiscal_year": self.fiscal_year_2024.name,
                "from_date": "2026-06-15",
                "to_date": "2026-12-31",
            },
        )
        report_filters = module.execute.call_args.kwargs["filters"]
        self.assertEqual(report_filters["fiscal_year"], self.fiscal_year_2024.name)

    def test_explicit_fiscal_period_bounds_do_not_need_a_year_for_today(self):
        self.assertTrue(self.assert_no_fiscal_year_for_date)
        module, _response = self._call(
            "Balance Sheet",
            {
                "company": self.company,
                "filter_based_on": "Fiscal Year",
                "from_fiscal_year": self.fiscal_year_2024.name,
                "to_fiscal_year": self.future_fiscal_year.name,
            },
            today=self.no_year_date,
        )
        report_filters = module.execute.call_args.kwargs["filters"]
        self.assertEqual(report_filters["from_fiscal_year"], self.fiscal_year_2024.name)
        self.assertEqual(report_filters["to_fiscal_year"], self.future_fiscal_year.name)

        date_range_module, _response = self._call(
            "Balance Sheet",
            {
                "company": self.company,
                "filter_based_on": "Date Range",
                "period_start_date": str(self.fiscal_year_2024.year_start_date),
                "period_end_date": str(self.fiscal_year_2024.year_end_date),
            },
            today=self.no_year_date,
        )
        date_range_filters = date_range_module.execute.call_args.kwargs["filters"]
        self.assertEqual(date_range_filters["period_start_date"], str(self.fiscal_year_2024.year_start_date))
        self.assertEqual(date_range_filters["period_end_date"], str(self.fiscal_year_2024.year_end_date))

    def test_requested_date_without_fiscal_year_fails_closed(self):
        from erpnext.accounts.utils import FiscalYearError

        self.assertTrue(self.assert_no_fiscal_year_for_date)
        module = _stub_module([], [])
        with self.assertRaises(FiscalYearError):
            self._call(
                "Trial Balance",
                {
                    "company": self.company,
                    "from_date": str(self.no_year_date),
                    "to_date": str(self.no_year_date),
                },
                module=module,
            )
        module.execute.assert_not_called()
