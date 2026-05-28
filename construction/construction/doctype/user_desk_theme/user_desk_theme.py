# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class UserDeskTheme(Document):
    """Per-user theme preferences"""

    def validate(self):
        """Validate user theme settings"""
        # Check if user override is allowed
        try:
            site_settings = frappe.get_doc("Modern Theme Settings")
            if not site_settings.allow_user_override and not self.inherit_from_site:
                frappe.throw("User theme overrides are not allowed by administrator")
        except frappe.DoesNotExistError:
            pass  # No site settings yet, allow override

        # Validate theme references
        if not self.inherit_from_site:
            if self.light_theme and not frappe.db.exists("Construction Theme", self.light_theme):
                frappe.throw(f"Light theme '{self.light_theme}' does not exist")

            if self.dark_theme and not frappe.db.exists("Construction Theme", self.dark_theme):
                frappe.throw(f"Dark theme '{self.dark_theme}' does not exist")

        # Ensure user is valid
        if not frappe.db.exists("User", self.user):
            frappe.throw(f"User '{self.user}' does not exist")

        self.validate_typography()

    def validate_typography(self):
        """Keep typography values in a small, safe range."""
        allowed_fonts = {
            "Inherit",
            "System Default",
            "Inter",
            "Arial",
            "Helvetica",
            "Tahoma",
            "Verdana",
            "Trebuchet MS",
            "Georgia",
            "Times New Roman",
            "Courier New",
            "Roboto",
            "Open Sans",
            "Lato",
            "Montserrat",
            "Poppins",
            "Noto Sans",
            "Noto Sans Arabic",
            "Cairo",
            "Tajawal",
            "Almarai",
        }
        if self.desk_font_family and self.desk_font_family not in allowed_fonts:
            frappe.throw("Invalid desk font family")
        if self.desk_font_family == "Inherit":
            self.desk_font_family = "System Default"
        for fieldname in (
            "sidebar_font_family",
            "navbar_font_family",
            "form_font_family",
            "list_font_family",
            "menu_font_family",
        ):
            if self.get(fieldname) and self.get(fieldname) not in allowed_fonts:
                frappe.throw(f"Invalid {frappe.unscrub(fieldname)}")

        size_defaults = (
            ("desk_font_size", 14),
            ("sidebar_font_size", 13),
            ("navbar_font_size", 14),
            ("form_font_size", 14),
            ("list_font_size", 13),
            ("menu_font_size", 13),
        )
        for fieldname, default_value in size_defaults:
            value = self.get(fieldname)
            if value is None:
                self.set(fieldname, default_value)
                continue
            try:
                value = int(value)
            except (TypeError, ValueError):
                frappe.throw(f"{frappe.unscrub(fieldname)} must be a number")
            self.set(fieldname, value)
            if value < 11 or value > 20:
                frappe.throw(f"{frappe.unscrub(fieldname)} must be between 11 and 20 px")

        allowed_weights = {"300", "400", "500", "600", "700", 300, 400, 500, 600, 700}
        weight_defaults = (
            ("desk_font_weight", "400"),
            ("sidebar_font_weight", "500"),
            ("navbar_font_weight", "500"),
            ("form_font_weight", "400"),
            ("list_font_weight", "400"),
            ("menu_font_weight", "400"),
        )
        for fieldname, default_value in weight_defaults:
            value = self.get(fieldname)
            if not value:
                self.set(fieldname, default_value)
            elif str(value) not in allowed_weights:
                frappe.throw(f"Invalid {frappe.unscrub(fieldname)}")
            else:
                self.set(fieldname, str(value))

    def before_insert(self):
        """Ensure unique user constraint"""
        if frappe.db.exists("User Desk Theme", {"user": self.user}):
            frappe.throw(f"Theme settings already exist for user '{self.user}'")

    def on_update(self):
        """Clear cache when user theme is updated"""
        frappe.cache().delete_key(f"user_desk_theme:{self.user}")
        frappe.cache().hdel("bootinfo", self.user)

    @staticmethod
    def get_user_theme(user=None):
        """Get theme settings for a user"""
        if not user:
            user = frappe.session.user

        try:
            return frappe.get_doc("User Desk Theme", {"user": user})
        except frappe.DoesNotExistError:
            return None

    @staticmethod
    def get_or_create_user_theme(user=None):
        """Get or create theme settings for a user"""
        if not user:
            user = frappe.session.user

        theme = UserDeskTheme.get_user_theme(user)
        if theme:
            return theme

        # Create default settings
        theme = frappe.new_doc("User Desk Theme")
        theme.user = user
        theme.inherit_from_site = 1
        theme.desk_font_family = "System Default"
        theme.desk_font_size = 14
        theme.desk_font_weight = "400"
        theme.sidebar_font_family = "Inherit"
        theme.sidebar_font_size = 13
        theme.sidebar_font_weight = "500"
        theme.navbar_font_family = "Inherit"
        theme.navbar_font_size = 14
        theme.navbar_font_weight = "500"
        theme.form_font_family = "Inherit"
        theme.form_font_size = 14
        theme.form_font_weight = "400"
        theme.list_font_family = "Inherit"
        theme.list_font_size = 13
        theme.list_font_weight = "400"
        theme.menu_font_family = "Inherit"
        theme.menu_font_size = 13
        theme.menu_font_weight = "400"
        theme.insert(ignore_permissions=True)
        return theme
