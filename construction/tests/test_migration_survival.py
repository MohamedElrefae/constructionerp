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
