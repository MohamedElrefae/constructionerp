"""Fresh-site registry requirements and non-destructive repeated provisioning."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.install import fix_system_manager_permissions
from construction.services.bilingual_service import get_mapping, get_registry
from construction.setup.bilingual_schema import ensure_bilingual_schema


class TestBilingualInstallSchema(FrappeTestCase):
    def test_permission_setup_repairs_invalid_import_without_committing(self):
        invalid = frappe.db.sql("""
            SELECT p.name FROM `tabDocPerm` p
            JOIN `tabDocType` d ON d.name = p.parent
            WHERE p.role = 'System Manager' AND p.`import` = 1
              AND (COALESCE(d.allow_import, 0) = 0 OR d.issingle = 1)
        """)
        self.assertEqual(invalid, ())
        permission = frappe.db.get_value(
            "DocPerm", {"parent": "UAE VAT Settings", "role": "System Manager"}, "name"
        )
        self.assertTrue(permission)
        frappe.db.savepoint("release_permission_setup")
        frappe.db.set_value("DocPerm", permission, "import", 1)
        fix_system_manager_permissions()
        self.assertEqual(frappe.db.get_value("DocPerm", permission, "import"), 0)
        # A hidden commit would discard this savepoint and make rollback fail.
        frappe.db.rollback(save_point="release_permission_setup")
        self.assertEqual(frappe.db.get_value("DocPerm", permission, "import"), 0)

    def test_installed_registry_adapters_have_physical_fields(self):
        for doctype, mapping in get_registry()["doctypes"].items():
            if mapping["state"] in ("active", "schema_installed") and frappe.db.exists("DocType", doctype):
                with self.subTest(doctype=doctype):
                    self.assertIsNotNone(get_mapping(doctype))

    def test_repeated_provisioning_does_not_change_existing_fields_or_values(self):
        before = frappe.get_all(
            "Custom Field", fields=["name", "modified", "fieldtype", "label"], order_by="name"
        )
        groups = frappe.get_all(
            "Item Group", fields=["name", "item_group_name_ar", "item_group_name_ar_norm"], order_by="name"
        )
        result = ensure_bilingual_schema()
        self.assertEqual(result["fields_created"], 0)
        self.assertEqual(
            frappe.get_all(
                "Custom Field", fields=["name", "modified", "fieldtype", "label"], order_by="name"
            ),
            before,
        )
        self.assertEqual(
            frappe.get_all(
                "Item Group",
                fields=["name", "item_group_name_ar", "item_group_name_ar_norm"],
                order_by="name",
            ),
            groups,
        )

    def test_missing_framework_identity_field_fails_without_inventing_it(self):
        registry = {
            "doctypes": {
                "Item Group": {
                    "state": "active",
                    "english_field": "missing_release_test_field",
                    "arabic_field": "item_group_name_ar",
                    "identity_field": "name",
                }
            }
        }
        with patch("construction.setup.bilingual_schema.get_registry", return_value=registry):
            with self.assertRaises(frappe.ValidationError):
                ensure_bilingual_schema()
        self.assertFalse(frappe.get_meta("Item Group").has_field("missing_release_test_field"))
