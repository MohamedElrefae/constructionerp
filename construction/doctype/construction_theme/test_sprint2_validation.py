# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

"""
Sprint 2 Validation Tests for Enterprise Theme Configuration

Property-based tests for hex color validation, WCAG contrast ratio, and login title length.
Unit tests for component stylesheet structure and login validation edge cases.

Feature: enterprise-theme-config
"""

import re
import unittest
import frappe
from hypothesis import given, strategies as st, settings, HealthCheck
from .construction_theme import ConstructionTheme


# ============================================================================
# STRATEGIES
# ============================================================================

def hex_color_strategy():
    """Generate valid hex colors (#RGB or #RRGGBB)."""
    three_digit = st.text(
        alphabet="0123456789ABCDEFabcdef",
        min_size=3,
        max_size=3
    ).map(lambda x: "#" + x)

    six_digit = st.text(
        alphabet="0123456789ABCDEFabcdef",
        min_size=6,
        max_size=6
    ).map(lambda x: "#" + x)

    return st.one_of(three_digit, six_digit)


def invalid_hex_color_strategy():
    """Generate invalid hex color strings."""
    return st.one_of(
        st.text(min_size=1, max_size=20).filter(lambda x: not re.match(r'^#[0-9A-Fa-f]{3}$|^#[0-9A-Fa-f]{6}$', x)),
        st.just(""),
        st.just(None),
        st.just("#"),
        st.just("#12"),
        st.just("#1234"),
        st.just("#12345"),
        st.just("#1234567"),
        st.just("#GGGGGG"),
        st.just("red"),
        st.just("rgb(255,0,0)"),
    )


def login_title_strategy():
    """Generate strings for login_page_title testing."""
    return st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_",
        min_size=0,
        max_size=100
    )


# ============================================================================
# PROPERTY 6: Hex Color Validation
# ============================================================================

@given(test_string=st.one_of(hex_color_strategy(), invalid_hex_color_strategy()))
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_hex_color_validation_property(test_string):
    """
    Property 6: Hex Color Validation

    For any string, _is_valid_hex_color() SHALL return True if and only if
    the string matches the pattern #[0-9A-Fa-f]{3} or #[0-9A-Fa-f]{6},
    and return False for all other strings (including empty/null).

    **Validates: Requirements 13.1**
    """
    theme = frappe.get_doc({
        "doctype": "Construction Theme",
        "theme_name": "Test Theme",
        "theme_type": "Custom Light",
        "accent_primary": "#4CAF50",
        "navbar_bg": "#2196F3",
        "sidebar_bg": "#F5F5F5",
        "surface_bg": "#FFFFFF",
        "body_bg": "#FAFAFA",
        "text_primary": "#212121",
    })

    result = theme._is_valid_hex_color(test_string)

    # Check if string matches valid hex pattern
    is_valid_hex = bool(re.match(r'^#[0-9A-Fa-f]{3}$|^#[0-9A-Fa-f]{6}$', str(test_string or "")))

    # Result should match the pattern check
    assert result == is_valid_hex, \
        f"_is_valid_hex_color('{test_string}') returned {result}, expected {is_valid_hex}"


# ============================================================================
# PROPERTY 7: WCAG Contrast Ratio Correctness
# ============================================================================

@given(
    color1=hex_color_strategy(),
    color2=hex_color_strategy(),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_wcag_contrast_ratio_property(color1, color2):
    """
    Property 7: WCAG Contrast Ratio Correctness

    For any two valid hex colors, _get_contrast_ratio(color1, color2) SHALL return
    a value equal to (L_lighter + 0.05) / (L_darker + 0.05) where L is the relative
    luminance computed per WCAG 2.1 specification, and the result SHALL always be ≥ 1.0.

    **Validates: Requirements 13.2**
    """
    theme = frappe.get_doc({
        "doctype": "Construction Theme",
        "theme_name": "Test Theme",
        "theme_type": "Custom Light",
        "accent_primary": "#4CAF50",
        "navbar_bg": "#2196F3",
        "sidebar_bg": "#F5F5F5",
        "surface_bg": "#FFFFFF",
        "body_bg": "#FAFAFA",
        "text_primary": "#212121",
    })

    ratio = theme._get_contrast_ratio(color1, color2)

    # Verify ratio is >= 1.0
    assert ratio >= 1.0, f"Contrast ratio {ratio} is less than 1.0"

    # Manually compute expected ratio using WCAG formula
    def luminance(hex_color):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])

        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255

        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4

        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    l1 = luminance(color1)
    l2 = luminance(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    expected_ratio = (lighter + 0.05) / (darker + 0.05)

    # Allow small floating point differences
    assert abs(ratio - expected_ratio) < 0.0001, \
        f"Contrast ratio {ratio} does not match expected {expected_ratio}"


# ============================================================================
# PROPERTY 8: Login Title Length Validation
# ============================================================================

@given(title=login_title_strategy())
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_login_title_length_validation_property(title):
    """
    Property 8: Login Title Length Validation

    For any string assigned to login_page_title, the validation SHALL reject
    the save if len(string) > 30 and accept it if len(string) <= 30.

    **Validates: Requirements 2.4**
    """
    theme = frappe.get_doc({
        "doctype": "Construction Theme",
        "theme_name": f"Test Theme {len(title)}",
        "theme_type": "Custom Light",
        "accent_primary": "#4CAF50",
        "navbar_bg": "#2196F3",
        "sidebar_bg": "#F5F5F5",
        "surface_bg": "#FFFFFF",
        "body_bg": "#FAFAFA",
        "text_primary": "#212121",
        "login_page_title": title,
    })

    try:
        if len(title) > 30:
            # Should raise validation error
            try:
                theme.insert()
                assert False, f"Expected validation error for title length {len(title)}, but insert succeeded"
            except frappe.ValidationError:
                # Expected behavior
                pass
        else:
            # Should succeed
            theme.insert()
            assert frappe.db.exists("Construction Theme", theme.name), \
                f"Theme with title length {len(title)} should have been inserted"
    finally:
        if frappe.db.exists("Construction Theme", theme.name):
            frappe.delete_doc("Construction Theme", theme.name, force=True)


# ============================================================================
# UNIT TESTS: Component Stylesheet Structure
# ============================================================================

class TestComponentStylesheetStructure(unittest.TestCase):
    """Unit tests for component stylesheet structure.

    Tests for Task 8.4: Component stylesheet structure verification
    """

    def setUp(self):
        """Setup test fixtures."""
        self.stylesheet_path = "construction/construction/public/css/construction_theme_components.css"

    def test_component_stylesheet_exists(self):
        """Verify component stylesheet file exists."""
        import os
        self.assertTrue(
            os.path.exists(self.stylesheet_path),
            f"Component stylesheet not found at {self.stylesheet_path}"
        )

    def test_ct_theme_rules_exist(self):
        """Verify ct-theme-* CSS rules exist in stylesheet."""
        with open(self.stylesheet_path, 'r') as f:
            content = f.read()

        required_classes = [
            'ct-theme-hide-help',
            'ct-theme-hide-search',
            'ct-theme-hide-sidebar',
            'ct-theme-hide-like-comment',
            'ct-theme-mobile-card',
        ]

        for css_class in required_classes:
            self.assertIn(
                f'.{css_class}',
                content,
                f"CSS class .{css_class} not found in component stylesheet"
            )

    def test_display_none_used_for_hiding(self):
        """Verify display:none is used for hiding elements."""
        with open(self.stylesheet_path, 'r') as f:
            content = f.read()

        # Find all ct-theme-hide-* rules
        hide_rules = re.findall(r'\.ct-theme-hide-[a-z-]+ \{[^}]*\}', content)

        for rule in hide_rules:
            self.assertTrue(
                'display: none' in rule or 'display:none' in rule,
                f"Rule {rule} does not use display:none"
            )

    def test_important_documented(self):
        """Verify all !important usages are documented with comments."""
        with open(self.stylesheet_path, 'r') as f:
            content = f.read()

        # Find all !important declarations
        important_lines = re.findall(r'.*!important.*', content)

        for line in important_lines:
            # Check if there's a comment nearby (within 2 lines before)
            lines = content.split('\n')
            for i, l in enumerate(lines):
                if '!important' in l:
                    # Check if there's a comment on this line or previous line
                    has_comment = '/*' in l or (i > 0 and '*/' in lines[i-1])
                    self.assertTrue(
                        has_comment,
                        f"!important usage not documented: {l}"
                    )

    def test_no_hardcoded_hex_colors(self):
        """Verify no hardcoded hex color values in stylesheet."""
        with open(self.stylesheet_path, 'r') as f:
            content = f.read()

        # Remove comments from content
        content_no_comments = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Look for hex color patterns (but not in variable names like --ct-*)
        hex_pattern = r'(?<!--ct-[a-z0-9-]*)[:#]([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})(?![0-9A-Fa-f])'
        hex_matches = re.findall(hex_pattern, content_no_comments)

        # Filter out false positives (like #media, #keyframes, etc.)
        false_positives = ['media', 'keyframes', 'supports', 'document']
        hex_matches = [m for m in hex_matches if m not in false_positives]

        self.assertEqual(
            len(hex_matches),
            0,
            f"Found hardcoded hex colors in stylesheet: {hex_matches}"
        )

    def test_css_variables_referenced(self):
        """Verify CSS variables (--ct-*) are referenced in stylesheet."""
        with open(self.stylesheet_path, 'r') as f:
            content = f.read()

        # Find all --ct-* variable references
        var_pattern = r'var\(--ct-[a-z0-9-]+\)'
        var_matches = re.findall(var_pattern, content)

        self.assertGreater(
            len(var_matches),
            0,
            "No CSS variables (--ct-*) found in component stylesheet"
        )


# ============================================================================
# UNIT TESTS: Login Validation Edge Cases
# ============================================================================

class TestLoginValidationEdgeCases(unittest.TestCase):
    """Unit tests for login page validation edge cases.

    Tests for Task 8.5: Login validation edge cases
    """

    def setUp(self):
        """Setup test fixtures."""
        pass

    def tearDown(self):
        """Cleanup after tests."""
        # Clean up any test themes
        test_themes = frappe.db.get_list(
            "Construction Theme",
            filters={"theme_name": ["like", "Test Login%"]}
        )
        for theme in test_themes:
            frappe.delete_doc("Construction Theme", theme.name, force=True)

    def test_login_bg_type_mismatch_solid_color_no_color(self):
        """Verify validation rejects Solid Color without bg_color."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": "Test Login BG Type Mismatch 1",
            "theme_type": "Custom Light",
            "accent_primary": "#4CAF50",
            "navbar_bg": "#2196F3",
            "sidebar_bg": "#F5F5F5",
            "surface_bg": "#FFFFFF",
            "body_bg": "#FAFAFA",
            "text_primary": "#212121",
            "login_page_bg_type": "Solid Color",
            "login_page_bg_color": "",  # Empty - should fail
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        error_msg = str(context.exception).lower()
        self.assertTrue(
            "background" in error_msg or "color" in error_msg,
            f"Error message should mention background or color: {context.exception}"
        )

    def test_login_bg_type_mismatch_image_no_image(self):
        """Verify validation rejects Background Image without bg_image."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": "Test Login BG Type Mismatch 2",
            "theme_type": "Custom Light",
            "accent_primary": "#4CAF50",
            "navbar_bg": "#2196F3",
            "sidebar_bg": "#F5F5F5",
            "surface_bg": "#FFFFFF",
            "body_bg": "#FAFAFA",
            "text_primary": "#212121",
            "login_page_bg_type": "Background Image",
            "login_page_bg_image": "",  # Empty - should fail
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        error_msg = str(context.exception).lower()
        self.assertIn(
            "image",
            error_msg,
            f"Error message should mention image: {context.exception}"
        )

    def test_login_bg_type_solid_color_with_color_succeeds(self):
        """Verify validation accepts Solid Color with bg_color."""
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": "Test Login BG Type Solid Success",
            "theme_type": "Custom Light",
            "accent_primary": "#4CAF50",
            "navbar_bg": "#2196F3",
            "sidebar_bg": "#F5F5F5",
            "surface_bg": "#FFFFFF",
            "body_bg": "#FAFAFA",
            "text_primary": "#212121",
            "login_page_bg_type": "Solid Color",
            "login_page_bg_color": "#FFFFFF",
        })

        try:
            theme.insert()
            self.assertTrue(
                frappe.db.exists("Construction Theme", theme.name),
                "Theme with Solid Color and bg_color should be inserted"
            )
        finally:
            if frappe.db.exists("Construction Theme", theme.name):
                frappe.delete_doc("Construction Theme", theme.name, force=True)

    def test_login_page_title_exactly_30_chars_succeeds(self):
        """Verify validation accepts login_page_title with exactly 30 characters."""
        title = "a" * 30
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": "Test Login Title 30 Chars",
            "theme_type": "Custom Light",
            "accent_primary": "#4CAF50",
            "navbar_bg": "#2196F3",
            "sidebar_bg": "#F5F5F5",
            "surface_bg": "#FFFFFF",
            "body_bg": "#FAFAFA",
            "text_primary": "#212121",
            "login_page_title": title,
        })

        try:
            theme.insert()
            self.assertTrue(
                frappe.db.exists("Construction Theme", theme.name),
                "Theme with 30-char title should be inserted"
            )
        finally:
            if frappe.db.exists("Construction Theme", theme.name):
                frappe.delete_doc("Construction Theme", theme.name, force=True)

    def test_login_page_title_31_chars_fails(self):
        """Verify validation rejects login_page_title with 31 characters."""
        title = "a" * 31
        theme = frappe.get_doc({
            "doctype": "Construction Theme",
            "theme_name": "Test Login Title 31 Chars",
            "theme_type": "Custom Light",
            "accent_primary": "#4CAF50",
            "navbar_bg": "#2196F3",
            "sidebar_bg": "#F5F5F5",
            "surface_bg": "#FFFFFF",
            "body_bg": "#FAFAFA",
            "text_primary": "#212121",
            "login_page_title": title,
        })

        with self.assertRaises(frappe.ValidationError) as context:
            theme.insert()

        error_msg = str(context.exception)
        self.assertTrue(
            "30" in error_msg or "length" in error_msg.lower(),
            f"Error message should mention 30 char limit: {context.exception}"
        )
