"""Fresh-site registry requirements and non-destructive repeated provisioning."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.install import fix_select_permissions, fix_system_manager_permissions
from construction.services.bilingual_service import get_mapping, get_registry
from construction.setup.bilingual_schema import ensure_bilingual_schema


class TestBilingualInstallSchema(FrappeTestCase):
    def test_permission_setup_does_not_grant_vendor_roles_or_commit(self):
        frappe.db.savepoint("release_vendor_permissions")
        frappe.db.delete("DocPerm", {"parent": "Company", "role": "System Manager"})
        vendor = frappe.db.get_value("DocPerm", {"parent": "Project", "read": 1}, "name")
        self.assertTrue(vendor)
        frappe.db.set_value("DocPerm", vendor, "select", 0)
        fix_system_manager_permissions()
        fix_select_permissions()
        self.assertFalse(frappe.db.exists("DocPerm", {"parent": "Company", "role": "System Manager"}))
        self.assertEqual(frappe.db.get_value("DocPerm", vendor, "select"), 0)
        frappe.db.rollback(save_point="release_vendor_permissions")

    def test_permission_setup_repairs_invalid_import_without_committing(self):
        fix_system_manager_permissions()
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
        if not permission:
            # Clean vendor metadata has no such grant. Simulate only the old
            # app-created row needed to verify its impossible import flag.
            legacy = frappe.get_doc(
                {
                    "doctype": "DocPerm",
                    "parent": "UAE VAT Settings",
                    "parenttype": "DocType",
                    "parentfield": "permissions",
                    "role": "System Manager",
                    "permlevel": 0,
                    "read": 1,
                }
            )
            legacy.db_insert()
            permission = legacy.name
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

    def test_workspace_reconciliation_inserts_missing_page_before_sidebar(self):
        from construction.install import setup_construction_workspace_page

        self.assertTrue(frappe.conf.allow_tests)
        for field in frappe.get_meta("Workspace").get_table_fields():
            frappe.db.delete(field.options, {"parent": "Construction", "parenttype": "Workspace"})
        frappe.db.delete("Workspace", {"name": "Construction"})
        with patch.dict(frappe.conf, {"developer_mode": 0}):
            setup_construction_workspace_page()
            self.assertTrue(frappe.db.exists("Workspace", "Construction"))
            page = frappe.get_doc("Workspace", "Construction")
            self.assertTrue(page.public)
            sidebar = frappe.get_doc("Workspace Sidebar", "Construction")
            links = [(row.link_type, row.link_to) for row in sidebar.items if row.link_to]
            self.assertIn(("Workspace", "Construction"), links)
            setup_construction_workspace_page()
            repeated = frappe.get_doc("Workspace Sidebar", "Construction")
            self.assertEqual([(row.link_type, row.link_to) for row in repeated.items if row.link_to], links)
