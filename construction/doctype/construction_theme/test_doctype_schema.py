# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

"""
Unit Tests: DocType Schema Verification

Tests for Task 4.9: Verify all 11 tabs, all field names, correct types

Feature: enterprise-theme-config
"""

import unittest
import frappe
from frappe.model.meta import get_meta


class TestConstructionThemeSchema(unittest.TestCase):
    """Unit tests for Construction Theme DocType schema"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.meta = get_meta("Construction Theme")
        self.fields = {f.fieldname: f for f in self.meta.fields}
    
    def test_all_11_tabs_exist(self):
        """Verify all 11 tabs are present in the DocType."""
        expected_tabs = [
            "General",
            "Login Page",
            "Buttons",
            "Tables",
            "Widgets",
            "Input Fields",
            "Navbar",
            "Footer",
            "Semantic Colors",
            "Preview",
            "Advanced"
        ]
        
        tab_fields = [f for f in self.meta.fields if f.fieldtype == "Tab Break"]
        tab_labels = [f.label for f in tab_fields]
        
        for expected_tab in expected_tabs:
            self.assertIn(expected_tab, tab_labels,
                f"Tab '{expected_tab}' not found in DocType")
    
    def test_general_tab_fields(self):
        """Verify General tab contains required fields."""
        required_fields = [
            "theme_name",
            "emoji_icon",
            "is_active",
            "theme_type",
            "is_system_theme",
            "is_default_light",
            "is_default_dark",
            "description",
            "accent_primary",
            "accent_primary_hover",
            "accent_secondary",
            "sidebar_bg",
            "surface_bg",
            "body_bg",
            "text_primary",
            "text_secondary",
            "border_color",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in General tab")
    
    def test_login_page_tab_fields(self):
        """Verify Login Page tab contains all required fields."""
        required_fields = [
            "login_btn_bg",
            "login_btn_text",
            "login_btn_hover_bg",
            "login_btn_hover_text",
            "login_page_bg_type",
            "login_page_bg_color",
            "login_page_bg_image",
            "login_box_position",
            "login_logo_inside_box",
            "login_page_title",
            "login_heading_text_color",
            "login_tab_bg_color",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in Login Page tab")
    
    def test_buttons_tab_fields(self):
        """Verify Buttons tab contains all required fields."""
        required_fields = [
            "primary_btn_bg",
            "primary_btn_text",
            "primary_btn_hover_bg",
            "primary_btn_hover_text",
            "secondary_btn_bg",
            "secondary_btn_text",
            "secondary_btn_hover_bg",
            "secondary_btn_hover_text",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in Buttons tab")
    
    def test_tables_tab_fields(self):
        """Verify Tables tab contains all required fields."""
        required_fields = [
            "table_header_bg",
            "table_header_text",
            "table_body_bg",
            "table_body_text",
            "hide_like_comment",
            "mobile_card_view",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in Tables tab")
    
    def test_widgets_tab_fields(self):
        """Verify Widgets tab contains all required fields."""
        required_fields = [
            "number_card_bg",
            "number_card_border",
            "number_card_text",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in Widgets tab")
    
    def test_input_fields_tab_fields(self):
        """Verify Input Fields tab contains all required fields."""
        required_fields = [
            "input_bg",
            "input_border",
            "input_text",
            "input_label_color",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in Input Fields tab")
    
    def test_navbar_tab_fields(self):
        """Verify Navbar tab contains all required fields."""
        required_fields = [
            "navbar_bg",
            "navbar_text_color",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in Navbar tab")
    
    def test_footer_tab_fields(self):
        """Verify Footer tab contains all required fields."""
        required_fields = [
            "footer_bg",
            "footer_text",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in Footer tab")
    
    def test_semantic_colors_tab_fields(self):
        """Verify Semantic Colors tab contains all required fields."""
        required_fields = [
            "success_color",
            "warning_color",
            "error_color",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in Semantic Colors tab")
    
    def test_preview_tab_fields(self):
        """Verify Preview tab contains all required fields."""
        required_fields = [
            "preview_colors",
            "contrast_ratio",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in Preview tab")
    
    def test_advanced_tab_fields(self):
        """Verify Advanced tab contains all required fields."""
        required_fields = [
            "hide_help_button",
            "hide_search_bar",
            "hide_sidebar",
            "custom_css",
        ]
        
        for field_name in required_fields:
            self.assertIn(field_name, self.fields,
                f"Field '{field_name}' not found in Advanced tab")
    
    def test_color_field_types(self):
        """Verify all color fields have correct fieldtype."""
        color_fields = [
            "accent_primary",
            "accent_primary_hover",
            "accent_secondary",
            "navbar_bg",
            "sidebar_bg",
            "surface_bg",
            "body_bg",
            "text_primary",
            "text_secondary",
            "border_color",
            "success_color",
            "warning_color",
            "error_color",
            "primary_btn_bg",
            "primary_btn_text",
            "primary_btn_hover_bg",
            "primary_btn_hover_text",
            "secondary_btn_bg",
            "secondary_btn_text",
            "secondary_btn_hover_bg",
            "secondary_btn_hover_text",
            "table_header_bg",
            "table_header_text",
            "table_body_bg",
            "table_body_text",
            "number_card_bg",
            "number_card_border",
            "number_card_text",
            "input_bg",
            "input_border",
            "input_text",
            "input_label_color",
            "navbar_text_color",
            "footer_bg",
            "footer_text",
            "login_btn_bg",
            "login_btn_text",
            "login_btn_hover_bg",
            "login_btn_hover_text",
            "login_page_bg_color",
            "login_heading_text_color",
            "login_tab_bg_color",
        ]
        
        for field_name in color_fields:
            self.assertIn(field_name, self.fields,
                f"Color field '{field_name}' not found")
            field = self.fields[field_name]
            self.assertEqual(field.fieldtype, "Color",
                f"Field '{field_name}' should be Color type, got {field.fieldtype}")
    
    def test_check_field_types(self):
        """Verify all check fields have correct fieldtype."""
        check_fields = [
            "is_active",
            "is_system_theme",
            "is_default_light",
            "is_default_dark",
            "login_logo_inside_box",
            "hide_like_comment",
            "mobile_card_view",
            "hide_help_button",
            "hide_search_bar",
            "hide_sidebar",
        ]
        
        for field_name in check_fields:
            self.assertIn(field_name, self.fields,
                f"Check field '{field_name}' not found")
            field = self.fields[field_name]
            self.assertEqual(field.fieldtype, "Check",
                f"Field '{field_name}' should be Check type, got {field.fieldtype}")
    
    def test_data_field_types(self):
        """Verify all data fields have correct fieldtype."""
        data_fields = [
            "theme_name",
            "emoji_icon",
            "login_page_title",
        ]
        
        for field_name in data_fields:
            self.assertIn(field_name, self.fields,
                f"Data field '{field_name}' not found")
            field = self.fields[field_name]
            self.assertEqual(field.fieldtype, "Data",
                f"Field '{field_name}' should be Data type, got {field.fieldtype}")
    
    def test_select_field_types(self):
        """Verify all select fields have correct fieldtype."""
        select_fields = [
            "theme_type",
            "login_page_bg_type",
            "login_box_position",
        ]
        
        for field_name in select_fields:
            self.assertIn(field_name, self.fields,
                f"Select field '{field_name}' not found")
            field = self.fields[field_name]
            self.assertEqual(field.fieldtype, "Select",
                f"Field '{field_name}' should be Select type, got {field.fieldtype}")
    
    def test_theme_name_is_unique(self):
        """Verify theme_name field is marked as unique."""
        field = self.fields.get("theme_name")
        self.assertIsNotNone(field, "theme_name field not found")
        self.assertEqual(field.unique, 1,
            "theme_name should be marked as unique")
    
    def test_theme_name_is_required(self):
        """Verify theme_name field is required."""
        field = self.fields.get("theme_name")
        self.assertIsNotNone(field, "theme_name field not found")
        self.assertEqual(field.reqd, 1,
            "theme_name should be required")
    
    def test_theme_type_is_required(self):
        """Verify theme_type field is required."""
        field = self.fields.get("theme_type")
        self.assertIsNotNone(field, "theme_type field not found")
        self.assertEqual(field.reqd, 1,
            "theme_type should be required")
    
    def test_navbar_bg_is_required(self):
        """Verify navbar_bg field is required."""
        field = self.fields.get("navbar_bg")
        self.assertIsNotNone(field, "navbar_bg field not found")
        self.assertEqual(field.reqd, 1,
            "navbar_bg should be required")
    
    def test_custom_css_field_type(self):
        """Verify custom_css field has correct fieldtype."""
        field = self.fields.get("custom_css")
        self.assertIsNotNone(field, "custom_css field not found")
        self.assertEqual(field.fieldtype, "Code",
            f"custom_css should be Code type, got {field.fieldtype}")
    
    def test_preview_colors_field_type(self):
        """Verify preview_colors field has correct fieldtype."""
        field = self.fields.get("preview_colors")
        self.assertIsNotNone(field, "preview_colors field not found")
        self.assertEqual(field.fieldtype, "JSON",
            f"preview_colors should be JSON type, got {field.fieldtype}")
    
    def test_contrast_ratio_field_type(self):
        """Verify contrast_ratio field has correct fieldtype."""
        field = self.fields.get("contrast_ratio")
        self.assertIsNotNone(field, "contrast_ratio field not found")
        self.assertEqual(field.fieldtype, "Float",
            f"contrast_ratio should be Float type, got {field.fieldtype}")
    
    def test_login_page_bg_image_field_type(self):
        """Verify login_page_bg_image field has correct fieldtype."""
        field = self.fields.get("login_page_bg_image")
        self.assertIsNotNone(field, "login_page_bg_image field not found")
        self.assertEqual(field.fieldtype, "Attach Image",
            f"login_page_bg_image should be Attach Image type, got {field.fieldtype}")
    
    def test_description_field_type(self):
        """Verify description field has correct fieldtype."""
        field = self.fields.get("description")
        self.assertIsNotNone(field, "description field not found")
        self.assertEqual(field.fieldtype, "Small Text",
            f"description should be Small Text type, got {field.fieldtype}")
    
    def test_all_original_15_fields_preserved(self):
        """Verify all 15 original fields are preserved with original names."""
        original_fields = [
            "accent_primary",
            "accent_primary_hover",
            "accent_secondary",
            "navbar_bg",
            "sidebar_bg",
            "surface_bg",
            "body_bg",
            "text_primary",
            "text_secondary",
            "border_color",
            "success_color",
            "warning_color",
            "error_color",
            "preview_colors",
            "contrast_ratio",
        ]
        
        for field_name in original_fields:
            self.assertIn(field_name, self.fields,
                f"Original field '{field_name}' not found or was renamed")
    
    def test_no_field_type_changes(self):
        """Verify original fields have not changed fieldtype."""
        expected_types = {
            "accent_primary": "Color",
            "accent_primary_hover": "Color",
            "accent_secondary": "Color",
            "navbar_bg": "Color",
            "sidebar_bg": "Color",
            "surface_bg": "Color",
            "body_bg": "Color",
            "text_primary": "Color",
            "text_secondary": "Color",
            "border_color": "Color",
            "success_color": "Color",
            "warning_color": "Color",
            "error_color": "Color",
            "preview_colors": "JSON",
            "contrast_ratio": "Float",
        }
        
        for field_name, expected_type in expected_types.items():
            field = self.fields.get(field_name)
            self.assertIsNotNone(field, f"Field '{field_name}' not found")
            self.assertEqual(field.fieldtype, expected_type,
                f"Field '{field_name}' type changed from {expected_type} to {field.fieldtype}")
    
    def test_login_page_bg_type_has_options(self):
        """Verify login_page_bg_type has correct options."""
        field = self.fields.get("login_page_bg_type")
        self.assertIsNotNone(field, "login_page_bg_type field not found")
        
        # Options should include "Solid Color" and "Background Image"
        options = field.options.split('\n') if field.options else []
        self.assertIn("Solid Color", options,
            "login_page_bg_type should have 'Solid Color' option")
        self.assertIn("Background Image", options,
            "login_page_bg_type should have 'Background Image' option")
    
    def test_login_box_position_has_options(self):
        """Verify login_box_position has correct options."""
        field = self.fields.get("login_box_position")
        self.assertIsNotNone(field, "login_box_position field not found")
        
        # Options should include "Default", "Left", "Right"
        options = field.options.split('\n') if field.options else []
        self.assertIn("Default", options,
            "login_box_position should have 'Default' option")
        self.assertIn("Left", options,
            "login_box_position should have 'Left' option")
        self.assertIn("Right", options,
            "login_box_position should have 'Right' option")
    
    def test_theme_type_has_options(self):
        """Verify theme_type has correct options."""
        field = self.fields.get("theme_type")
        self.assertIsNotNone(field, "theme_type field not found")
        
        # Options should include theme types
        options = field.options.split('\n') if field.options else []
        self.assertGreater(len(options), 0,
            "theme_type should have options defined")


if __name__ == "__main__":
    unittest.main()
