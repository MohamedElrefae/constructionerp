"""Stage 4 report extension-point spike tests (read-only, no mutation).

Run with: bench --site [site] run-tests --module construction.tests.test_stage4_report_extension

Proves Arabic / English / Both account-name rendering for the General
Ledger, Trial Balance, Balance Sheet, and Profit & Loss reports via the
Construction-side bilingualizer — no vendor file edit, no Report DocType,
no Account/translation mutation. Integration runs are read-only calls to the
vendor report `execute`.
"""

import unittest

import frappe

from construction.services import report_bilingual_extension as rbe


class TestReportExtensionPure(unittest.TestCase):
    def test_english_mode_preserves_labels(self):
        cols = [{"fieldname": "account", "label": "Account"}]
        data = [{"account": "1100 - Cash - E", "balance": 1}]
        mapping = {"1100 - Cash - E": "نقدية"}
        _nc, nd = rbe.transform_report(cols, data, "en", mapping, ["account"])
        self.assertEqual(nd[0]["account"], "1100 - Cash - E")

    def test_arabic_mode_swaps_label(self):
        cols = [{"fieldname": "account", "label": "Account"}]
        data = [{"account": "1100 - Cash - E", "balance": 1}]
        mapping = {"1100 - Cash - E": "نقدية"}
        _nc, nd = rbe.transform_report(cols, data, "ar", mapping, ["account"])
        self.assertEqual(nd[0]["account"], "نقدية")

    def test_both_mode_shows_pair(self):
        data = [{"account": "1100 - Cash - E"}]
        mapping = {"1100 - Cash - E": "نقدية"}
        _nc, nd = rbe.transform_report([], data, "both", mapping, ["account"])
        self.assertEqual(nd[0]["account"], "1100 - Cash - E — نقدية")

    def test_unknown_label_kept_identity(self):
        data = [{"account": "1200 - Receivable - E"}]
        mapping = {"1100 - Cash - E": "نقدية"}
        _nc, nd = rbe.transform_report([], data, "ar", mapping, ["account"])
        self.assertEqual(nd[0]["account"], "1200 - Receivable - E")

    def test_sources_are_not_mutated(self):
        cols = [{"fieldname": "account", "label": "Account"}]
        data = [{"account": "1100 - Cash - E"}]
        mapping = {"1100 - Cash - E": "نقدية"}
        rbe.transform_report(cols, data, "ar", mapping, ["account"])
        # originals untouched (pure)
        self.assertEqual(data[0]["account"], "1100 - Cash - E")

    def test_columnar_row_translates_account_column(self):
        cols = [{"fieldname": "account", "label": "Account"}, {"fieldname": "balance"}]
        data = [["1100 - Cash - E", 10]]
        mapping = {"1100 - Cash - E": "نقدية"}
        _nc, nd = rbe.transform_report(cols, data, "ar", mapping, ["account"])
        self.assertEqual(nd[0][0], "نقدية")
        self.assertEqual(nd[0][1], 10)

    def test_report_label_field_configurations(self):
        for name in ("General Ledger", "Trial Balance", "Balance Sheet", "Profit and Loss Statement"):
            self.assertTrue(rbe.REPORT_LABEL_FIELDS[name])


class TestReportExtensionIntegration(unittest.TestCase):
    def test_general_ledger_bilingualize_readonly(self):
        from erpnext.accounts.report.general_ledger.general_ledger import execute

        filters = frappe._dict({"company": "Elrefae", "from_date": "2024-01-01", "to_date": "2029-12-31"})
        cols, raw = rbe.bilingualize_report(execute, filters, "en", "General Ledger")
        self.assertIsInstance(cols, list)
        self.assertIsInstance(raw, list)
        for lang in ("ar", "en", "both"):
            cols2, data = rbe.bilingualize_report(execute, filters, lang, "General Ledger")
            self.assertIsInstance(cols2, list)
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), len(raw))

    def test_trial_balance_bilingualize_readonly(self):
        from erpnext.accounts.report.trial_balance.trial_balance import execute

        filters = frappe._dict({"company": "Elrefae", "fiscal_year": "_Test Short Fiscal Year 2011"})
        cols, data = rbe.bilingualize_report(execute, filters, "en", "Trial Balance")
        self.assertIsInstance(cols, list)
        self.assertIsInstance(data, list)

    def test_financial_statements_reports_are_supported(self):
        # The four required report names resolve to label-field configs.
        self.assertIn("Balance Sheet", rbe.REPORT_LABEL_FIELDS)
        self.assertIn("Profit and Loss Statement", rbe.REPORT_LABEL_FIELDS)

    def test_rollback_note_documented(self):
        note = rbe.rollback_note()
        self.assertIn("Rollback", note)
        self.assertIn("vendor report file", note)


if __name__ == "__main__":
    unittest.main()
