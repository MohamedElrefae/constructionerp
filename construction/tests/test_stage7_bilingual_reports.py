"""Stage 7 bilingual-report pilot — API tests (site-context bench tests).

Extends the Stage-4 extension-point suite: endpoint surface behavior
(fail-closed report allowlist, mode normalization, pure transform
round-trip with a stub vendor execute).
"""

import unittest
from unittest import mock


def _stub_module(columns, data):
    import types

    mod = types.ModuleType("vendor.stub")
    mod.execute = mock.Mock(return_value=(columns, data))
    return mod


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
            with mock.patch("frappe.get_module") as gm:
                from construction.api.bilingual_reports import localized_report

                with self.assertRaises(frappe.PermissionError):
                    localized_report("Trial Balance", filters=None, mode="ar")
                self.assertEqual(
                    gm.call_count, 0, "vendor module must not be resolved for a rejected user"
                )
        finally:
            frappe.set_user("Administrator")
            if frappe.db.exists("User", self.USER):
                frappe.delete_doc("User", self.USER, force=True, ignore_permissions=True)
            frappe.db.commit()

        with mock.patch("frappe.get_module") as gm:
            gm.return_value.execute = mock.Mock(
                return_value=([{"fieldname": "account"}], [{"account": "Cash"}])
            )
            from construction.api.bilingual_reports import localized_report

            out = localized_report("Trial Balance", filters='{"company": "Elrefae"}', mode="ar")
        self.assertEqual(out["report_name"], "Trial Balance")
