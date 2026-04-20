# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

import unittest
import frappe
from .construction_theme import ConstructionTheme


class TestExtendedValidation(unittest.TestCase):
    """Tests for Task 7: Extended Validation in construction_theme.py

    Tests for:
    - 7.1 Extended hex color validation for all new color fields
    - 7.2 Login page field validation (bg_type ↔ bg_color/bg_image, title max 30 chars)
    - 7.3 Login page bg_image publicity check
    - 7.4 Extended WCAG contrast calculation
    """

    def setUp(self):
        """Set up test fixtures"""
        self.test_theme_name = "_Test Extended Validation"

        # Clean up any existing test theme
        if frappe.db.exists("Construction Theme", self.test_theme_name):
            frappe.delete_doc("Construction Theme", self.test_theme_name, force=True)

    def tearDown(self):
        """Clean up after tests"""
        if frappe.db.exists("Construction Theme", self.test_theme_name):
            frappe.delete_doc("Construction Theme", self.test_theme_name, force=True)

    # ===== Task 7.1: Extended Hex Color Validation =====

    def test_validate_hex_colors_button_fields(self):
        """7.1: Hex validation covers button color fields."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "primary_btn_bg": "invalid-color",  # Invalid
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        self.assertIn("primary_btn_bg", str(context.exception))

    def test_validate_hex_colors_table_fields(self):
        """7.1: Hex validation covers table color fields."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "table_header_bg": "not-hex",  # Invalid
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        self.assertIn("table_header_bg", str(context.exception))

    def test_validate_hex_colors_widget_fields(self):
        """7.1: Hex validation covers widget color fields."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "number_card_bg": "#gggggg",  # Invalid hex
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        self.assertIn("number_card_bg", str(context.exception))

    def test_validate_hex_colors_input_fields(self):
        """7.1: Hex validation covers input field color fields."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "input_label_color": "#xyz",  # Invalid
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        self.assertIn("input_label_color", str(context.exception))

    def test_validate_hex_colors_navbar_text(self):
        """7.1: Hex validation covers navbar_text_color."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "navbar_text_color": "red",  # Invalid hex
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        self.assertIn("navbar_text_color", str(context.exception))

    def test_validate_hex_colors_footer_fields(self):
        """7.1: Hex validation covers footer color fields."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "footer_bg": "#12345",  # Invalid (5 chars)
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        self.assertIn("footer_bg", str(context.exception))

    def test_validate_hex_colors_login_page_fields(self):
        """7.1: Hex validation covers login page color fields."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "login_btn_bg": "badcolor",  # Invalid
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        self.assertIn("login_btn_bg", str(context.exception))

    def test_validate_hex_colors_all_valid(self):
        """7.1: All new color fields accept valid hex colors."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            # All new fields with valid hex
            "primary_btn_bg": "#2076FF",
            "primary_btn_text": "#ffffff",
            "secondary_btn_bg": "#e5e7eb",
            "table_header_bg": "#f3f4f6",
            "table_header_text": "#111827",
            "number_card_bg": "#f9fafb",
            "number_card_border": "#e5e7eb",
            "input_bg": "#ffffff",
            "input_border": "#d1d5db",
            "navbar_text_color": "#111827",
            "footer_bg": "#f9fafb",
            "footer_text": "#6b7280",
            "login_btn_bg": "#2076FF",
            "login_page_bg_color": "#ffffff",
            "login_heading_text_color": "#111827",
        })

        # Should insert without validation errors
        theme.insert()
        self.assertIsNotNone(theme.name)

        frappe.delete_doc("Construction Theme", theme.name, force=True)

    # ===== Task 7.2: Login Page Field Validation =====

    def test_login_page_bg_type_solid_color_requires_color(self):
        """7.2: bg_type='Solid Color' requires login_page_bg_color."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "login_page_bg_type": "Solid Color",
            "login_page_bg_color": None,  # Missing
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        self.assertIn("Login Page Background Color is required", str(context.exception))

    def test_login_page_bg_type_image_requires_image(self):
        """7.2: bg_type='Background Image' requires login_page_bg_image."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "login_page_bg_type": "Background Image",
            "login_page_bg_image": None,  # Missing
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        self.assertIn("Login Page Background Image is required", str(context.exception))

    def test_login_page_title_max_30_chars(self):
        """7.2: login_page_title must not exceed 30 characters."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "login_page_title": "This is a very long title that exceeds thirty characters",  # 56 chars
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        self.assertIn("must not exceed 30 characters", str(context.exception))

    def test_login_page_title_exactly_30_chars(self):
        """7.2: login_page_title exactly 30 chars is accepted."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "login_page_title": "123456789012345678901234567890",  # Exactly 30 chars
        })

        # Should insert without error
        theme.insert()
        self.assertIsNotNone(theme.name)

        frappe.delete_doc("Construction Theme", theme.name, force=True)

    def test_login_page_title_under_30_chars(self):
        """7.2: login_page_title under 30 chars is accepted."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "login_page_title": "Welcome",  # 7 chars
        })

        # Should insert without error
        theme.insert()
        self.assertIsNotNone(theme.name)

        frappe.delete_doc("Construction Theme", theme.name, force=True)

    def test_login_page_title_empty_is_allowed(self):
        """7.2: login_page_title can be empty."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "login_page_title": "",  # Empty
        })

        # Should insert without error
        theme.insert()
        self.assertIsNotNone(theme.name)

        frappe.delete_doc("Construction Theme", theme.name, force=True)

    # ===== Task 7.3: Login Page BG Image Publicity Check =====

    def test_login_page_bg_image_publicity_check_public_file(self):
        """7.3: Public login_page_bg_image is accepted without warning."""
        # Create a public file
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": "test_login_bg.jpg",
            "file_url": "/files/test_login_bg.jpg",
            "is_private": 0,  # Public
        })
        file_doc.insert()

        try:
            theme = frappe.get_doc({
                "doctype": "Construction Theme",
                "theme_name": self.test_theme_name,
                "theme_type": "Custom Light",
                "accent_primary": "#2076FF",
                "navbar_bg": "#ffffff",
                "sidebar_bg": "#f1f5f9",
                "surface_bg": "#ffffff",
                "body_bg": "#f8fafc",
                "text_primary": "#111827",
                "login_page_bg_type": "Background Image",
                "login_page_bg_image": file_doc.file_url,
            })

            # Should insert without error
            theme.insert()
            self.assertIsNotNone(theme.name)

            frappe.delete_doc("Construction Theme", theme.name, force=True)
        finally:
            frappe.delete_doc("File", file_doc.name, force=True)

    def test_login_page_bg_image_publicity_check_private_file_auto_set_public(self):
        """7.3: Private login_page_bg_image is auto-set to public with warning."""
        # Create a private file
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": "test_login_bg_private.jpg",
            "file_url": "/files/test_login_bg_private.jpg",
            "is_private": 1,  # Private
        })
        file_doc.insert()

        try:
            theme = frappe.get_doc({
                "doctype": "Construction Theme",
                "theme_name": self.test_theme_name,
                "theme_type": "Custom Light",
                "accent_primary": "#2076FF",
                "navbar_bg": "#ffffff",
                "sidebar_bg": "#f1f5f9",
                "surface_bg": "#ffffff",
                "body_bg": "#f8fafc",
                "text_primary": "#111827",
                "login_page_bg_type": "Background Image",
                "login_page_bg_image": file_doc.file_url,
            })

            # Should insert (with warning)
            theme.insert()
            self.assertIsNotNone(theme.name)

            # Verify file was set to public
            updated_file = frappe.get_doc("File", file_doc.name)
            self.assertEqual(updated_file.is_private, 0)

            frappe.delete_doc("Construction Theme", theme.name, force=True)
        finally:
            frappe.delete_doc("File", file_doc.name, force=True)

    def test_login_page_bg_image_no_image_no_check(self):
        """7.3: No publicity check if login_page_bg_image is empty."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "login_page_bg_image": None,  # Empty
        })

        # Should insert without error
        theme.insert()
        self.assertIsNotNone(theme.name)

        frappe.delete_doc("Construction Theme", theme.name, force=True)

    # ===== Task 7.4: Extended WCAG Contrast Calculation =====

    def test_contrast_ratio_text_primary_vs_body_bg(self):
        """7.4: Contrast calculated for text_primary vs body_bg."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",  # Dark text on light bg = good contrast
        })

        theme.insert()

        # Should have calculated contrast ratio
        self.assertIsNotNone(theme.contrast_ratio)
        self.assertGreater(theme.contrast_ratio, 4.5)  # Should be good

        frappe.delete_doc("Construction Theme", theme.name, force=True)

    def test_contrast_ratio_text_secondary_vs_surface_bg(self):
        """7.4: Contrast calculated for text_secondary vs surface_bg."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "text_secondary": "#6b7280",  # Medium gray
        })

        theme.insert()

        # Should have calculated contrast ratio
        self.assertIsNotNone(theme.contrast_ratio)

        frappe.delete_doc("Construction Theme", theme.name, force=True)

    def test_contrast_ratio_primary_btn_text_vs_bg(self):
        """7.4: Contrast calculated for primary_btn_text vs primary_btn_bg."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "primary_btn_bg": "#2076FF",
            "primary_btn_text": "#ffffff",  # White text on blue bg = good contrast
        })

        theme.insert()

        # Should have calculated contrast ratio
        self.assertIsNotNone(theme.contrast_ratio)
        self.assertGreater(theme.contrast_ratio, 4.5)

        frappe.delete_doc("Construction Theme", theme.name, force=True)

    def test_contrast_ratio_accent_vs_surface_bg(self):
        """7.4: Contrast calculated for accent_primary vs surface_bg."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
        })

        theme.insert()

        # Should have calculated contrast ratio
        self.assertIsNotNone(theme.contrast_ratio)

        frappe.delete_doc("Construction Theme", theme.name, force=True)

    def test_contrast_ratio_low_contrast_warning(self):
        """7.4: Low contrast pairs generate warning."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#f0f0f0",  # Very light text on light bg = poor contrast
        })

        # Should insert (with warning, not error)
        theme.insert()
        self.assertIsNotNone(theme.name)

        frappe.delete_doc("Construction Theme", theme.name, force=True)


if __name__ == "__main__":
    unittest.main()
