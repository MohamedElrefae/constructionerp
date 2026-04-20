# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

"""
Unit tests for the v6.0 migration patch: set_default_new_theme_fields
"""

import unittest
import frappe
from .set_default_new_theme_fields import (
    _is_valid_hex_color,
    _darken_hex,
    _lighten_hex,
    _is_dark_theme,
    execute
)


class TestMigrationHelpers(unittest.TestCase):
    """Test helper functions for migration patch"""
    
    def test_is_valid_hex_color(self):
        """Test hex color validation"""
        # Valid colors
        self.assertTrue(_is_valid_hex_color("#FFF"))
        self.assertTrue(_is_valid_hex_color("#FFFFFF"))
        self.assertTrue(_is_valid_hex_color("#2076FF"))
        self.assertTrue(_is_valid_hex_color("#000000"))
        
        # Invalid colors
        self.assertFalse(_is_valid_hex_color(""))
        self.assertFalse(_is_valid_hex_color(None))
        self.assertFalse(_is_valid_hex_color("FFFFFF"))  # Missing #
        self.assertFalse(_is_valid_hex_color("#GGGGGG"))  # Invalid hex chars
        self.assertFalse(_is_valid_hex_color("#FF"))  # Too short
    
    def test_darken_hex(self):
        """Test darkening hex colors"""
        # Darken white by 10%
        result = _darken_hex("#FFFFFF", 0.1)
        self.assertEqual(result, "#e6e6e6")
        
        # Darken blue by 10%
        result = _darken_hex("#2076FF", 0.1)
        self.assertEqual(result, "#1a68e6")
        
        # Darken black by 10% (should stay black)
        result = _darken_hex("#000000", 0.1)
        self.assertEqual(result, "#000000")
    
    def test_lighten_hex(self):
        """Test lightening hex colors"""
        # Lighten black by 10%
        result = _lighten_hex("#000000", 0.1)
        self.assertEqual(result, "#191919")
        
        # Lighten dark blue by 10%
        result = _lighten_hex("#111827", 0.1)
        self.assertEqual(result, "#2a2f3d")
        
        # Lighten white by 10% (should stay white)
        result = _lighten_hex("#FFFFFF", 0.1)
        self.assertEqual(result, "#ffffff")
    
    def test_is_dark_theme(self):
        """Test dark theme detection"""
        # Dark themes start with #1
        self.assertTrue(_is_dark_theme("#111827"))
        self.assertTrue(_is_dark_theme("#1a1a1a"))
        self.assertTrue(_is_dark_theme("#1f2937"))
        
        # Light themes don't start with #1
        self.assertFalse(_is_dark_theme("#f8fafc"))
        self.assertFalse(_is_dark_theme("#ffffff"))
        self.assertFalse(_is_dark_theme("#2076FF"))
        
        # Edge cases
        self.assertFalse(_is_dark_theme(""))
        self.assertFalse(_is_dark_theme(None))


class TestMigrationExecution(unittest.TestCase):
    """Test the migration patch execution"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_theme_name = "_Test Migration Theme"
        
        # Clean up any existing test theme
        if frappe.db.exists("Construction Theme", self.test_theme_name):
            frappe.delete_doc("Construction Theme", self.test_theme_name, force=True)
    
    def tearDown(self):
        """Clean up after tests"""
        if frappe.db.exists("Construction Theme", self.test_theme_name):
            frappe.delete_doc("Construction Theme", self.test_theme_name, force=True)
    
    def test_migration_populates_button_fields(self):
        """Migration populates button fields from accent_primary"""
        # Create theme with only 15 original fields
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "accent_primary_hover": "#1a5ce6",
            "accent_secondary": "#4CAF50",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "text_secondary": "#6b7280",
            "border_color": "#e5e7eb",
            "success_color": "#10b981",
            "warning_color": "#f59e0b",
            "error_color": "#ef4444",
            # New fields are empty
            "primary_btn_bg": None,
            "primary_btn_text": None,
            "primary_btn_hover_bg": None,
            "primary_btn_hover_text": None,
        })
        theme.insert()
        
        # Execute migration
        execute()
        
        # Reload theme
        theme.reload()
        
        # Verify button fields were populated
        self.assertEqual(theme.primary_btn_bg, "#2076FF")  # From accent_primary
        self.assertEqual(theme.primary_btn_text, "#FFFFFF")  # Hardcoded white
        self.assertIsNotNone(theme.primary_btn_hover_bg)  # Should be darkened
        self.assertEqual(theme.primary_btn_hover_text, "#FFFFFF")
    
    def test_migration_populates_table_fields(self):
        """Migration populates table fields from existing fields"""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "accent_primary_hover": "#1a5ce6",
            "accent_secondary": "#4CAF50",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "text_secondary": "#6b7280",
            "border_color": "#e5e7eb",
            "success_color": "#10b981",
            "warning_color": "#f59e0b",
            "error_color": "#ef4444",
            # Table fields empty
            "table_header_bg": None,
            "table_header_text": None,
            "table_body_bg": None,
            "table_body_text": None,
        })
        theme.insert()
        
        execute()
        theme.reload()
        
        # Verify table fields
        self.assertEqual(theme.table_header_bg, "#f1f5f9")  # From sidebar_bg
        self.assertEqual(theme.table_header_text, "#111827")  # From text_primary
        self.assertEqual(theme.table_body_bg, "#f8fafc")  # From body_bg
        self.assertEqual(theme.table_body_text, "#111827")  # From text_primary
    
    def test_migration_populates_input_fields(self):
        """Migration populates input fields from existing fields"""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "accent_primary_hover": "#1a5ce6",
            "accent_secondary": "#4CAF50",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "text_secondary": "#6b7280",
            "border_color": "#e5e7eb",
            "success_color": "#10b981",
            "warning_color": "#f59e0b",
            "error_color": "#ef4444",
            # Input fields empty
            "input_bg": None,
            "input_border": None,
            "input_text": None,
            "input_label_color": None,
        })
        theme.insert()
        
        execute()
        theme.reload()
        
        # Verify input fields
        self.assertEqual(theme.input_bg, "#ffffff")  # From surface_bg
        self.assertEqual(theme.input_border, "#e5e7eb")  # From border_color
        self.assertEqual(theme.input_text, "#111827")  # From text_primary
        self.assertEqual(theme.input_label_color, "#6b7280")  # From text_secondary
    
    def test_migration_skips_populated_fields(self):
        """Migration skips fields that already have values"""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "accent_primary_hover": "#1a5ce6",
            "accent_secondary": "#4CAF50",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "text_secondary": "#6b7280",
            "border_color": "#e5e7eb",
            "success_color": "#10b981",
            "warning_color": "#f59e0b",
            "error_color": "#ef4444",
            # Pre-populate one field with custom value
            "primary_btn_bg": "#FF0000",  # Custom red
            "primary_btn_text": None,
        })
        theme.insert()
        
        execute()
        theme.reload()
        
        # Verify pre-populated field was not changed
        self.assertEqual(theme.primary_btn_bg, "#FF0000")
        # But other fields were populated
        self.assertEqual(theme.primary_btn_text, "#FFFFFF")
    
    def test_migration_uses_fallback_accent(self):
        """Migration uses #2076FF fallback when accent_primary is empty"""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": None,  # Empty!
            "accent_primary_hover": None,
            "accent_secondary": "#4CAF50",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "text_secondary": "#6b7280",
            "border_color": "#e5e7eb",
            "success_color": "#10b981",
            "warning_color": "#f59e0b",
            "error_color": "#ef4444",
            "primary_btn_bg": None,
        })
        theme.insert()
        
        execute()
        theme.reload()
        
        # Verify fallback accent was used
        self.assertEqual(theme.primary_btn_bg, "#2076FF")
    
    def test_migration_dark_theme_hover_computation(self):
        """Migration lightens hover colors for dark themes"""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Dark",
            "accent_primary": "#3b82f6",
            "accent_primary_hover": "#2563eb",
            "accent_secondary": "#60a5fa",
            "navbar_bg": "#111827",
            "sidebar_bg": "#1f2937",
            "surface_bg": "#1f2937",
            "body_bg": "#111827",  # Starts with #1 = dark theme
            "text_primary": "#f9fafb",
            "text_secondary": "#d1d5db",
            "border_color": "#374151",
            "success_color": "#10b981",
            "warning_color": "#f59e0b",
            "error_color": "#ef4444",
            "primary_btn_hover_bg": None,
        })
        theme.insert()
        
        execute()
        theme.reload()
        
        # For dark theme, hover should be lightened (not darkened)
        # Lighten #3b82f6 by 10%
        expected_hover = _lighten_hex("#3b82f6", 0.1)
        self.assertEqual(theme.primary_btn_hover_bg, expected_hover)
    
    def test_migration_light_theme_hover_computation(self):
        """Migration darkens hover colors for light themes"""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "accent_primary_hover": "#1a5ce6",
            "accent_secondary": "#4CAF50",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",  # Does NOT start with #1 = light theme
            "text_primary": "#111827",
            "text_secondary": "#6b7280",
            "border_color": "#e5e7eb",
            "success_color": "#10b981",
            "warning_color": "#f59e0b",
            "error_color": "#ef4444",
            "primary_btn_hover_bg": None,
        })
        theme.insert()
        
        execute()
        theme.reload()
        
        # For light theme, hover should be darkened
        # Darken #2076FF by 10%
        expected_hover = _darken_hex("#2076FF", 0.1)
        self.assertEqual(theme.primary_btn_hover_bg, expected_hover)
    
    def test_migration_preserves_original_fields(self):
        """Migration does not modify the original 15 fields"""
        original_values = {
            "accent_primary": "#2076FF",
            "accent_primary_hover": "#1a5ce6",
            "accent_secondary": "#4CAF50",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "text_secondary": "#6b7280",
            "border_color": "#e5e7eb",
            "success_color": "#10b981",
            "warning_color": "#f59e0b",
            "error_color": "#ef4444",
        }
        
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            **original_values
        })
        theme.insert()
        
        execute()
        theme.reload()
        
        # Verify all original fields are unchanged
        for field, value in original_values.items():
            self.assertEqual(getattr(theme, field), value, f"Field {field} was modified")
    
    def test_migration_populates_navbar_text_color(self):
        """Migration populates navbar_text_color from text_primary"""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "accent_primary_hover": "#1a5ce6",
            "accent_secondary": "#4CAF50",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "text_secondary": "#6b7280",
            "border_color": "#e5e7eb",
            "success_color": "#10b981",
            "warning_color": "#f59e0b",
            "error_color": "#ef4444",
            "navbar_text_color": None,
        })
        theme.insert()
        
        execute()
        theme.reload()
        
        # Verify navbar_text_color was populated
        self.assertEqual(theme.navbar_text_color, "#111827")  # From text_primary


if __name__ == "__main__":
    unittest.main()
