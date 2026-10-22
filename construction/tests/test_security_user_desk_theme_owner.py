"""Authorization regression tests for per-user Desk Theme records."""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestUserDeskThemeOwnership(FrappeTestCase):
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        self.users = []
        suffix = frappe.generate_hash(length=8)
        self.attacker = self._create_user(f"udt_owner_{suffix}_attacker@example.com", "Accounts User")
        self.victim = self._create_user(f"udt_owner_{suffix}_victim@example.com", "Accounts User")
        self.manager = self._create_user(f"udt_owner_{suffix}_manager@example.com", "System Manager")

    def tearDown(self):
        frappe.set_user("Administrator")
        for user in self.users:
            for name in frappe.get_all("User Desk Theme", filters={"user": user}, pluck="name"):
                frappe.delete_doc("User Desk Theme", name, ignore_permissions=True, force=True)
            if frappe.db.exists("User", user):
                frappe.delete_doc("User", user, ignore_permissions=True, force=True)
        frappe.set_user("Administrator")
        super().tearDown()

    def _create_user(self, email, role):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "User Desk Theme ownership test",
                "enabled": 1,
                "user_type": "System User",
                "send_welcome_email": 0,
                "roles": [{"role": role}],
            }
        )
        user.insert(ignore_permissions=True)
        self.users.append(email)
        return email

    def _new_theme(self, user):
        theme = frappe.new_doc("User Desk Theme")
        theme.user = user
        theme.inherit_from_site = 1
        return theme

    def test_ordinary_user_cannot_create_theme_for_another_user(self):
        frappe.set_user(self.attacker)
        self.assertTrue(frappe.has_permission("User Desk Theme", "create"))

        theme = self._new_theme(self.victim)
        with self.assertRaises(frappe.PermissionError):
            theme.insert()

        self.assertFalse(frappe.db.exists("User Desk Theme", {"user": self.victim}))

    def test_ordinary_user_cannot_reassign_own_theme_to_another_user(self):
        frappe.set_user(self.attacker)
        theme = self._new_theme(self.attacker)
        theme.insert()

        theme.user = self.victim
        with self.assertRaises(frappe.PermissionError):
            theme.save()

        self.assertEqual(frappe.db.get_value("User Desk Theme", theme.name, "user"), self.attacker)

    def test_ordinary_user_can_create_and_update_own_theme(self):
        frappe.set_user(self.attacker)
        theme = self._new_theme(self.attacker)
        theme.insert()

        theme.desk_font_size = 15
        theme.save()

        self.assertEqual(frappe.db.get_value("User Desk Theme", theme.name, "user"), self.attacker)
        self.assertEqual(frappe.db.get_value("User Desk Theme", theme.name, "desk_font_size"), 15)

    def test_system_manager_and_administrator_can_manage_another_users_theme(self):
        frappe.set_user(self.manager)
        theme = self._new_theme(self.victim)
        theme.insert()

        theme.desk_font_size = 15
        theme.save()

        frappe.set_user("Administrator")
        theme = frappe.get_doc("User Desk Theme", theme.name)
        theme.desk_font_size = 16
        theme.save()

        self.assertEqual(frappe.db.get_value("User Desk Theme", theme.name, "user"), self.victim)
        self.assertEqual(frappe.db.get_value("User Desk Theme", theme.name, "desk_font_size"), 16)
