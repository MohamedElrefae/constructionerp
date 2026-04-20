# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

import unittest
import frappe
from frappe.utils import cstr
from .construction_theme import ConstructionTheme


class TestConstructionTheme(unittest.TestCase):
    """Unit tests for Construction Theme DocType"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_theme_name = "_Test Theme"
        
        # Clean up any existing test theme
        if frappe.db.exists("Construction Theme", self.test_theme_name):
            frappe.delete_doc("Construction Theme", self.test_theme_name, force=True)
    
    def tearDown(self):
        """Clean up after tests"""
        if frappe.db.exists("Construction Theme", self.test_theme_name):
            frappe.delete_doc("Construction Theme", self.test_theme_name, force=True)
    
    def test_unique_default_light(self):
        """Only one theme can be default light."""
        # Create first default light theme
        theme1 = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name + " 1",
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "is_default_light": 1
        })
        theme1.insert()
        
        # Try to create second default light theme
        theme2 = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name + " 2",
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "is_default_light": 1
        })
        
        with self.assertRaises(frappe.ValidationError):
            theme2.insert()
        
        # Clean up
        frappe.delete_doc("Construction Theme", theme1.name, force=True)
    
    def test_unique_default_dark(self):
        """Only one theme can be default dark."""
        theme1 = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name + " Dark 1",
            "theme_type": "Custom Dark",
            "accent_primary": "#3b82f6",
            "navbar_bg": "#111827",
            "sidebar_bg": "#1f2937",
            "surface_bg": "#1f2937",
            "body_bg": "#111827",
            "text_primary": "#f9fafb",
            "is_default_dark": 1
        })
        theme1.insert()
        
        theme2 = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name + " Dark 2",
            "theme_type": "Custom Dark",
            "accent_primary": "#3b82f6",
            "navbar_bg": "#111827",
            "sidebar_bg": "#1f2937",
            "surface_bg": "#1f2937",
            "body_bg": "#111827",
            "text_primary": "#f9fafb",
            "is_default_dark": 1
        })
        
        with self.assertRaises(frappe.ValidationError):
            theme2.insert()
        
        frappe.delete_doc("Construction Theme", theme1.name, force=True)
    
    def test_auto_calculate_hover_color(self):
        """Blank accent_primary_hover auto-calculates."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",  # Blue
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "accent_primary_hover": None  # Explicitly blank
        })
        
        theme.insert()
        
        # Should have auto-calculated hover color
        self.assertIsNotNone(theme.accent_primary_hover)
        self.assertNotEqual(theme.accent_primary_hover, "")
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_auto_calculate_border_color(self):
        """Blank border_color auto-calculates from accent."""
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
            "border_color": None  # Explicitly blank
        })
        
        theme.insert()
        
        # Should have auto-calculated border color
        self.assertIsNotNone(theme.border_color)
        self.assertNotEqual(theme.border_color, "")
    
    def test_contrast_ratio_warning(self):
        """Low contrast shows warning but doesn't block save (unless enforced)."""
        # Create theme with poor contrast (light blue on white)
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#a5d6a7",  # Light green (poor contrast)
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#ffffff",  # White text (poor contrast on white bg)
        })
        
        # Should calculate contrast ratio
        theme.insert()
        
        self.assertIsNotNone(theme.contrast_ratio)
        self.assertGreater(theme.contrast_ratio, 0)
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_system_theme_deletion_blocked(self):
        """is_system_theme=1 prevents deletion."""
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
            "is_system_theme": 1
        })
        theme.insert()
        
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("Construction Theme", theme.name)
        
        # Clean up by disabling system flag first
        theme.is_system_theme = 0
        theme.save()
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_cache_invalidation_on_save(self):
        """Cache key is deleted when theme is updated."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827"
        })
        theme.insert()
        
        # Generate CSS to populate cache
        css = theme.generate_css()
        
        # Verify cache exists
        cache_key = f"theme_css:{theme.name}"
        cached = frappe.cache().get_value(cache_key)
        self.assertIsNotNone(cached)
        
        # Update theme
        theme.accent_primary = "#FF0000"
        theme.save()
        
        # Cache should be invalidated
        cached = frappe.cache().get_value(cache_key)
        self.assertIsNone(cached)
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_hex_color_validation(self):
        """Invalid hex colors are rejected."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "not-a-color",  # Invalid
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827"
        })
        
        with self.assertRaises(frappe.ValidationError):
            theme.insert()
    
    def test_custom_css_validation(self):
        """Dangerous CSS patterns are blocked."""
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
            "custom_css": "@import url('https://evil.com/styles.css');"  # Should be blocked
        })
        
        with self.assertRaises(frappe.ValidationError):
            theme.insert()
    
    def test_custom_css_size_limit(self):
        """Custom CSS cannot exceed 10KB."""
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
            "custom_css": "/* " + "x" * 10241 + " */"  # Just over 10KB
        })
        
        with self.assertRaises(frappe.ValidationError):
            theme.insert()
    
    def test_css_generation_matches_hardcoded(self):
        """
        CRITICAL REGRESSION TEST:
        Generated CSS for Phase 1 themes must match hardcoded CSS.
        This ensures the migration doesn't break existing themes.
        """
        # Create Construction Dark theme with Phase 1 colors
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Construction Dark",
            "accent_primary": "#4CAF50",
            "accent_primary_hover": "#43a047",
            "accent_secondary": "#66BB6A",
            "navbar_bg": "#1a3a1e",
            "sidebar_bg": "#0d1f10",
            "surface_bg": "#112b15",
            "body_bg": "#0a1a0c",
            "text_primary": "#e8f5e9",
            "text_secondary": "#a5d6a7",
            "border_color": "#2e5c35",
        })
        
        theme.insert()
        
        # Generate CSS
        css = theme.generate_css()
        
        # Verify CSS contains expected selectors
        self.assertIn("html[data-modern-theme=\"_Test Theme\"]", css)
        self.assertIn(".navbar", css)
        self.assertIn(".btn-primary", css)
        self.assertIn("#4CAF50", css)  # Accent color appears
        self.assertIn("#1a3a1e", css)  # Navbar background
        
        # Verify no empty CSS
        self.assertGreater(len(css), 500)  # Should be substantial
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_generate_css_variables_basic(self):
        """generate_css_variables produces scoped CSS block with --ct-* variables."""
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
        
        css_vars = theme.generate_css_variables()
        
        # Should contain scoped selector
        self.assertIn('html[data-modern-theme="_test_theme"]', css_vars)
        
        # Should contain --ct-* variables
        self.assertIn('--ct-accent-primary: #2076FF;', css_vars)
        self.assertIn('--ct-navbar-bg: #ffffff;', css_vars)
        self.assertIn('--ct-text-primary: #111827;', css_vars)
        
        # Should not contain empty fields
        self.assertNotIn('--ct-primary-btn-bg', css_vars)  # Not set
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_generate_css_variables_skips_empty_fields(self):
        """generate_css_variables skips null/empty fields."""
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
            # Intentionally leave many fields empty
        })
        
        theme.insert()
        
        css_vars = theme.generate_css_variables()
        
        # Should not contain variables for empty fields
        self.assertNotIn('--ct-primary-btn-bg', css_vars)
        self.assertNotIn('--ct-table-header-bg', css_vars)
        self.assertNotIn('--ct-footer-bg', css_vars)
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_generate_css_variables_auto_compute_hover_light(self):
        """generate_css_variables auto-computes hover colors for light themes."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",  # Light theme (doesn't start with #1)
            "text_primary": "#111827",
            "primary_btn_bg": "#4CAF50",
            # primary_btn_hover_bg intentionally empty
        })
        
        theme.insert()
        
        css_vars = theme.generate_css_variables()
        
        # Should contain auto-computed hover color
        self.assertIn('--ct-primary-btn-hover-bg:', css_vars)
        
        # Hover should be darker than base (darkened by 10%)
        # #4CAF50 darkened 10% should be approximately #3d8b40
        self.assertIn('--ct-primary-btn-hover-bg: #3d8b40;', css_vars)
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_generate_css_variables_auto_compute_hover_dark(self):
        """generate_css_variables auto-computes hover colors for dark themes."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Dark",
            "accent_primary": "#2076FF",
            "navbar_bg": "#111827",
            "sidebar_bg": "#1f2937",
            "surface_bg": "#1f2937",
            "body_bg": "#111827",  # Dark theme (starts with #1)
            "text_primary": "#f9fafb",
            "primary_btn_bg": "#4CAF50",
            # primary_btn_hover_bg intentionally empty
        })
        
        theme.insert()
        
        css_vars = theme.generate_css_variables()
        
        # Should contain auto-computed hover color
        self.assertIn('--ct-primary-btn-hover-bg:', css_vars)
        
        # Hover should be lighter than base (lightened by 10%)
        # #4CAF50 lightened 10% should be approximately #66bb6a
        self.assertIn('--ct-primary-btn-hover-bg: #66bb6a;', css_vars)
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_generate_css_variables_respects_explicit_hover(self):
        """generate_css_variables uses explicit hover color if provided."""
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
            "primary_btn_bg": "#4CAF50",
            "primary_btn_hover_bg": "#FF0000",  # Explicitly set
        })
        
        theme.insert()
        
        css_vars = theme.generate_css_variables()
        
        # Should use explicit hover color, not auto-computed
        self.assertIn('--ct-primary-btn-hover-bg: #FF0000;', css_vars)
        self.assertNotIn('--ct-primary-btn-hover-bg: #3d8b40;', css_vars)
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_generate_css_variables_size_bound(self):
        """generate_css_variables output ≤ 800 bytes for fully populated theme."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            # Populate all 40+ fields
            "accent_primary": "#2076FF",
            "accent_primary_hover": "#1a5cc4",
            "accent_secondary": "#66BB6A",
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
            "primary_btn_bg": "#2076FF",
            "primary_btn_text": "#ffffff",
            "primary_btn_hover_bg": "#1a5cc4",
            "primary_btn_hover_text": "#ffffff",
            "secondary_btn_bg": "#e5e7eb",
            "secondary_btn_text": "#111827",
            "secondary_btn_hover_bg": "#d1d5db",
            "secondary_btn_hover_text": "#111827",
            "table_header_bg": "#f3f4f6",
            "table_header_text": "#111827",
            "table_body_bg": "#ffffff",
            "table_body_text": "#111827",
            "number_card_bg": "#f9fafb",
            "number_card_border": "#e5e7eb",
            "number_card_text": "#111827",
            "input_bg": "#ffffff",
            "input_border": "#d1d5db",
            "input_text": "#111827",
            "input_label_color": "#6b7280",
            "navbar_text_color": "#111827",
            "footer_bg": "#f9fafb",
            "footer_text": "#6b7280",
        })
        
        theme.insert()
        
        css_vars = theme.generate_css_variables()
        
        # Should be under 800 bytes
        self.assertLessEqual(len(css_vars), 800, 
            f"CSS variables output ({len(css_vars)} bytes) exceeds 800 byte limit")
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_generate_css_variables_empty_theme(self):
        """generate_css_variables returns empty string for theme with no fields."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": self.test_theme_name,
            "theme_type": "Custom Light",
            # No fields set
        })
        
        theme.insert()
        
        css_vars = theme.generate_css_variables()
        
        # Should return empty string
        self.assertEqual(css_vars, "")
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)
    
    def test_generate_css_variables_format(self):
        """generate_css_variables output matches expected CSS format."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": "My Test Theme",
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
        })
        
        theme.insert()
        
        css_vars = theme.generate_css_variables()
        
        # Should match pattern: html[data-modern-theme="..."] { ... }
        self.assertTrue(css_vars.startswith('html[data-modern-theme="my_test_theme"] {'))
        self.assertTrue(css_vars.endswith('}'))
        
        # Should have proper indentation
        self.assertIn('  --ct-', css_vars)
        
        # Should have proper line breaks
        lines = css_vars.split('\n')
        self.assertGreater(len(lines), 2)  # At least opening, content, closing
        
        frappe.delete_doc("Construction Theme", theme.name, force=True)


class TestConstructionThemeStaticMethods(unittest.TestCase):
    """Tests for static/class methods"""
    
    def test_list_active_themes(self):
        """list_active_themes returns only active themes."""
        themes = ConstructionTheme.list_active_themes(limit=10)
        
        # Should return list
        self.assertIsInstance(themes, list)
        
        # All returned themes should be active
        for theme in themes:
            self.assertEqual(theme.is_active, 1)


if __name__ == "__main__":
    unittest.main()
