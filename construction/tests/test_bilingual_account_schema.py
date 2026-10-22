"""
Stage 1B tests: `Account.account_name_ar` schema foundation.
Run with: bench --site [site] run-tests --module construction.tests.test_bilingual_account_schema
"""

import unittest

import frappe


class TestAccountArabicNameSchema(unittest.TestCase):
    """Schema, idempotency, and metadata-cache verification."""

    def test_custom_field_registered(self):
        """Custom Field record exists on Account with correct definition."""
        name = frappe.db.get_value(
            "Custom Field",
            {"dt": "Account", "fieldname": "account_name_ar"},
            "name",
        )
        self.assertIsNotNone(name, "account_name_ar Custom Field missing on Account")
        doc = frappe.get_doc("Custom Field", name)
        self.assertEqual(doc.fieldtype, "Data")
        self.assertEqual(doc.insert_after, "account_name")
        self.assertEqual(doc.translatable, 0)
        self.assertEqual(doc.hidden, 0)
        # Stage 3 P0: the field is read-only in the form; writes are
        # confined to the governed bilingual API (server-enforced).
        self.assertEqual(doc.read_only, 1)

    def test_db_column_exists(self):
        """Physical column exists on tabAccount."""
        self.assertIn("account_name_ar", frappe.db.get_table_columns("Account"))

    def test_meta_exposes_field_after_cache_refresh(self):
        """DocType meta serves the field after clear_cache (no stale metadata)."""
        frappe.clear_cache(doctype="Account")
        self.assertTrue(frappe.get_meta("Account").has_field("account_name_ar"))

    def test_patch_is_idempotent(self):
        """Re-running the patch changes nothing (no duplicate Custom Field)."""
        from construction.patches.v8_8.add_account_arabic_name_field import execute

        before = frappe.db.count("Custom Field", {"dt": "Account", "fieldname": "account_name_ar"})
        execute()
        execute()
        after = frappe.db.count("Custom Field", {"dt": "Account", "fieldname": "account_name_ar"})
        self.assertEqual(before, 1)
        self.assertEqual(after, 1)

    def test_arabic_only_write_does_not_rename(self):
        """Setting account_name_ar leaves document name and English name intact.

        Uses a disposable CT- fixture account. Never pick an arbitrary real
        account: get_value() returns the most recently modified row, and an
        earlier run cleared the live Arabic value on GST - E this way.
        """
        parent = frappe.db.get_value(
            "Account",
            {"company": "Elrefae", "is_group": 1, "parent_account": ("is", "set")},
            "name",
        )
        self.assertIsNotNone(parent, "No Elrefae group parent available for fixture")
        parent_meta = frappe.db.get_value("Account", parent, ["root_type", "report_type"], as_dict=True)
        doc = frappe.get_doc(
            {
                "doctype": "Account",
                "company": "Elrefae",
                "account_name": "CT Schema Arabic Check",
                "account_number": "CT-SCHEMA-" + frappe.generate_hash(length=6),
                "parent_account": parent,
                "is_group": 0,
                "root_type": parent_meta.root_type,
                "report_type": parent_meta.report_type,
            }
        )
        doc.insert(ignore_permissions=True)
        name = doc.name
        try:
            before = frappe.db.get_value("Account", name, ["name", "account_name"], as_dict=True)
            frappe.db.set_value("Account", name, "account_name_ar", "حساب اختبار")
            after = frappe.db.get_value("Account", name, ["name", "account_name"], as_dict=True)
            self.assertEqual(after.name, before.name)
            self.assertEqual(after.account_name, before.account_name)
        finally:
            if frappe.db.exists("Account", name):
                frappe.delete_doc("Account", name, force=True, ignore_permissions=True)
