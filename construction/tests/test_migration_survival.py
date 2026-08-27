import frappe
from frappe.tests.utils import FrappeTestCase

from construction.api.theme_api import whitelabel_patch
from construction.install import create_system_themes


class TestMigrationSurvival(FrappeTestCase):
    """Verifies after_migrate hooks survive updates without error."""

    EXPECTED_SYSTEM_THEME_COUNT = 4

    def test_whitelabel_patch_removes_welcome_page(self):
        frappe.db.delete("Page", {"name": "welcome-to-erpnext"})
        page = frappe.get_doc({
            "doctype": "Page",
            "name": "welcome-to-erpnext",
            "page_name": "welcome-to-erpnext",
            "title": "Welcome",
            "module": "Core",
        })
        page.db_insert()
        self.assertTrue(
            frappe.db.exists("Page", "welcome-to-erpnext"),
            "Precondition: welcome page must exist before patch",
        )
        whitelabel_patch()
        self.assertFalse(
            frappe.db.exists("Page", "welcome-to-erpnext"),
        )

    def test_whitelabel_patch_idempotent(self):
        whitelabel_patch()
        whitelabel_patch()
        self.assertFalse(
            frappe.db.exists("Page", "welcome-to-erpnext"),
        )

    def test_create_system_themes_runs_without_error(self):
        create_system_themes()

    def test_create_system_themes_creates_expected_themes(self):
        create_system_themes()
        themes = frappe.get_all(
            "Construction Theme",
            filters={"is_system_theme": 1},
        )
        self.assertGreaterEqual(
            len(themes),
            self.EXPECTED_SYSTEM_THEME_COUNT,
        )

    def test_create_system_themes_idempotent(self):
        create_system_themes()
        create_system_themes()
        themes = frappe.get_all(
            "Construction Theme",
            filters={"is_system_theme": 1},
        )
        self.assertGreaterEqual(
            len(themes),
            self.EXPECTED_SYSTEM_THEME_COUNT,
        )

    def test_hooks_have_required_entries(self):
        import construction.hooks as hooks
        self.assertTrue(hasattr(hooks, "email_css"))
        self.assertTrue(hasattr(hooks, "pdf_header_html"))

    def test_whitelabel_patch_clears_onboarding(self):
        whitelabel_patch()
        for module in frappe.get_all("Module Onboarding", fields=["name"]):
            doc = frappe.get_doc("Module Onboarding", module.name)
            self.assertEqual(
                doc.documentation_url or "",
                "",
                msg=f"Module Onboarding '{module.name}' should have empty documentation_url after whitelabel_patch",
            )

    # -------------------------------------------------------------------------
    # Eighth-pass QA: exact MR index-definition helper + commit-failure propagation
    # -------------------------------------------------------------------------
    def test_index_is_correct_accepts_exact_definition(self):
        from construction.install import _index_is_correct

        rows = [{
            "COLUMN_NAME": "custom_variation_order_active",
            "SEQ_IN_INDEX": "1",
            "NON_UNIQUE": "0",
            "INDEX_TYPE": "BTREE",
        }]
        self.assertTrue(
            _index_is_correct(rows, "custom_variation_order_active"),
            "Exact one-column unique BTREE index must be accepted",
        )

    def test_index_is_correct_rejects_wrong_column(self):
        from construction.install import _index_is_correct

        rows = [{
            "COLUMN_NAME": "custom_variation_order",  # wrong column
            "SEQ_IN_INDEX": "1",
            "NON_UNIQUE": "0",
            "INDEX_TYPE": "BTREE",
        }]
        self.assertFalse(
            _index_is_correct(rows, "custom_variation_order_active"),
            "Wrong-column index must be rejected",
        )

    def test_index_is_correct_rejects_non_unique(self):
        from construction.install import _index_is_correct

        rows = [{
            "COLUMN_NAME": "custom_variation_order_active",
            "SEQ_IN_INDEX": "1",
            "NON_UNIQUE": "1",  # non-unique
            "INDEX_TYPE": "BTREE",
        }]
        self.assertFalse(
            _index_is_correct(rows, "custom_variation_order_active"),
            "Non-unique index must be rejected",
        )

    def test_index_is_correct_rejects_multi_column(self):
        from construction.install import _index_is_correct

        rows = [
            {"COLUMN_NAME": "custom_variation_order_active", "SEQ_IN_INDEX": "1",
             "NON_UNIQUE": "0", "INDEX_TYPE": "BTREE"},
            {"COLUMN_NAME": "docstatus", "SEQ_IN_INDEX": "2",
             "NON_UNIQUE": "0", "INDEX_TYPE": "BTREE"},
        ]
        self.assertFalse(
            _index_is_correct(rows, "custom_variation_order_active"),
            "Multi-column index must be rejected",
        )

    def test_index_is_correct_handles_int_and_str_metadata(self):
        """Numeric metadata may arrive as int or string; both must be accepted."""
        from construction.install import _index_is_correct

        for seq, non_unique in [("1", "0"), (1, 0)]:
            rows = [{
                "COLUMN_NAME": "custom_variation_order_active",
                "SEQ_IN_INDEX": seq,
                "NON_UNIQUE": non_unique,
                "INDEX_TYPE": "BTREE",
            }]
            self.assertTrue(
                _index_is_correct(rows, "custom_variation_order_active"),
                f"Metadata seq={seq!r} non_unique={non_unique!r} must be accepted",
            )
        # Zero must not be swallowed by `or` defaulting (a 0 NON_UNIQUE means unique).
        rows = [{"COLUMN_NAME": "custom_variation_order_active", "SEQ_IN_INDEX": 1,
                 "NON_UNIQUE": 0, "INDEX_TYPE": "BTREE"}]
        self.assertTrue(_index_is_correct(rows, "custom_variation_order_active"))
        # For numerical zero the index should NOT be falsely treated as the default 1.
        self.assertFalse(
            _index_is_correct([{"COLUMN_NAME": "custom_variation_order_active",
                                "SEQ_IN_INDEX": 0, "NON_UNIQUE": 0, "INDEX_TYPE": "BTREE"}],
                              "custom_variation_order_active"),
            "Zero seq-in-index must not accidentally pass",
        )

    def test_ensure_unique_index_propagates_commit_failure(self):
        """Commit failure before DDL must propagate (abort migration), not be swallowed."""
        from unittest import mock

        import construction.install as inst

        real_commit = frappe.db.commit
        try:
            # Force frappe.db.commit to raise on the next call.
            def _boom(*a, **k):
                raise RuntimeError("simulated commit failure")
            frappe.db.commit = _boom
            # The reconcile's first commit (in _ensure_unique_index_or_fail) must fail.
            with self.assertRaises(RuntimeError):
                inst._ensure_unique_index_or_fail()
        finally:
            frappe.db.commit = real_commit
