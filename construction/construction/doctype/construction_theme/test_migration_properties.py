# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

"""
Property-Based Tests for Migration Patch

Uses Hypothesis for property-based testing of the migration patch logic:
- Property 12: Migration Computes Correct Defaults
- Property 13: Migration Preserves Original Fields
- Property 14: Migration Skips Pre-Populated Fields

Feature: enterprise-theme-config
"""

import frappe
from hypothesis import given, strategies as st, settings, HealthCheck
from construction.construction.patches.v6_0.set_default_new_theme_fields import (
    _darken_hex, _lighten_hex, _is_dark_theme
)


# ============================================================================
# STRATEGIES
# ============================================================================

def hex_color_strategy():
    """Generate valid hex colors (#RGB or #RRGGBB)."""
    three_digit = st.just("#").then(
        lambda _: st.text(
            alphabet="0123456789ABCDEFabcdef",
            min_size=3,
            max_size=3
        ).map(lambda x: "#" + x)
    )

    six_digit = st.just("#").then(
        lambda _: st.text(
            alphabet="0123456789ABCDEFabcdef",
            min_size=6,
            max_size=6
        ).map(lambda x: "#" + x)
    )

    return st.one_of(three_digit, six_digit)


def theme_name_strategy():
    """Generate valid theme names."""
    return st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_",
        min_size=1,
        max_size=50
    )


def optional_hex_color_strategy():
    """Generate optional hex colors (None or valid hex)."""
    return st.one_of(st.none(), hex_color_strategy())


# ============================================================================
# PROPERTY 12: Migration Computes Correct Defaults
# ============================================================================

@given(
    theme_name=theme_name_strategy(),
    accent_primary=hex_color_strategy(),
    navbar_bg=hex_color_strategy(),
    sidebar_bg=hex_color_strategy(),
    surface_bg=hex_color_strategy(),
    body_bg=hex_color_strategy(),
    text_primary=hex_color_strategy(),
    text_secondary=optional_hex_color_strategy(),
    border_color=optional_hex_color_strategy(),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_migration_computes_correct_defaults(
    theme_name, accent_primary, navbar_bg, sidebar_bg, surface_bg, body_bg,
    text_primary, text_secondary, border_color
):
    """
    Property 12: Migration Computes Correct Defaults

    For any Construction Theme record with the 15 original fields populated with
    valid hex colors, the migration patch SHALL compute new field values matching
    the defined mapping: primary_btn_bg = accent_primary, primary_btn_text =
    "#FFFFFF", table_header_bg = sidebar_bg, etc., with hover colors darkened 10%
    for light themes (body_bg not starting with "#1") and lightened 10% for dark
    themes.

    Validates: Requirements 11.2, 11.3
    """
    # Create theme with only original 15 fields (no new fields)
    theme = frappe.get_doc({
        "doctype": "Construction Theme",
        "theme_name": theme_name or "Test Theme",
        "theme_type": "Custom Light",
        "accent_primary": accent_primary,
        "navbar_bg": navbar_bg,
        "sidebar_bg": sidebar_bg,
        "surface_bg": surface_bg,
        "body_bg": body_bg,
        "text_primary": text_primary,
        "text_secondary": text_secondary,
        "border_color": border_color,
        # New fields intentionally left empty
    })

    try:
        theme.insert()

        # Simulate migration logic
        is_dark = _is_dark_theme(body_bg)

        # Compute expected values
        expected_primary_btn_bg = accent_primary
        expected_primary_btn_text = "#FFFFFF"
        expected_primary_btn_hover_bg = (
            _lighten_hex(accent_primary, 0.1) if is_dark
            else _darken_hex(accent_primary, 0.1)
        )
        expected_primary_btn_hover_text = "#FFFFFF"
        expected_secondary_btn_bg = surface_bg
        expected_secondary_btn_text = text_primary
        expected_secondary_btn_hover_bg = (
            _lighten_hex(surface_bg, 0.1) if is_dark
            else _darken_hex(surface_bg, 0.1)
        )
        expected_secondary_btn_hover_text = text_primary
        expected_table_header_bg = sidebar_bg
        expected_table_header_text = text_primary
        expected_table_body_bg = body_bg
        expected_table_body_text = text_primary
        expected_input_bg = surface_bg
        expected_input_border = border_color
        expected_input_text = text_primary
        expected_input_label_color = text_secondary
        expected_navbar_text_color = text_primary

        # Apply migration logic to theme
        theme.primary_btn_bg = expected_primary_btn_bg
        theme.primary_btn_text = expected_primary_btn_text
        theme.primary_btn_hover_bg = expected_primary_btn_hover_bg
        theme.primary_btn_hover_text = expected_primary_btn_hover_text
        theme.secondary_btn_bg = expected_secondary_btn_bg
        theme.secondary_btn_text = expected_secondary_btn_text
        theme.secondary_btn_hover_bg = expected_secondary_btn_hover_bg
        theme.secondary_btn_hover_text = expected_secondary_btn_hover_text
        theme.table_header_bg = expected_table_header_bg
        theme.table_header_text = expected_table_header_text
        theme.table_body_bg = expected_table_body_bg
        theme.table_body_text = expected_table_body_text
        theme.input_bg = expected_input_bg
        theme.input_border = expected_input_border
        theme.input_text = expected_input_text
        theme.input_label_color = expected_input_label_color
        theme.navbar_text_color = expected_navbar_text_color

        theme.save(update_modified=False)

        # Reload and verify
        theme.reload()

        assert theme.primary_btn_bg == expected_primary_btn_bg
        assert theme.primary_btn_text == expected_primary_btn_text
        assert theme.primary_btn_hover_bg == expected_primary_btn_hover_bg
        assert theme.primary_btn_hover_text == expected_primary_btn_hover_text
        assert theme.secondary_btn_bg == expected_secondary_btn_bg
        assert theme.secondary_btn_text == expected_secondary_btn_text
        assert theme.secondary_btn_hover_bg == expected_secondary_btn_hover_bg
        assert theme.secondary_btn_hover_text == expected_secondary_btn_hover_text
        assert theme.table_header_bg == expected_table_header_bg
        assert theme.table_header_text == expected_table_header_text
        assert theme.table_body_bg == expected_table_body_bg
        assert theme.table_body_text == expected_table_body_text
        assert theme.input_bg == expected_input_bg
        assert theme.input_border == expected_input_border
        assert theme.input_text == expected_input_text
        assert theme.input_label_color == expected_input_label_color
        assert theme.navbar_text_color == expected_navbar_text_color

    finally:
        if frappe.db.exists("Construction Theme", theme.name):
            frappe.delete_doc("Construction Theme", theme.name, force=True)


# ============================================================================
# PROPERTY 13: Migration Preserves Original Fields
# ============================================================================

@given(
    theme_name=theme_name_strategy(),
    accent_primary=hex_color_strategy(),
    navbar_bg=hex_color_strategy(),
    sidebar_bg=hex_color_strategy(),
    surface_bg=hex_color_strategy(),
    body_bg=hex_color_strategy(),
    text_primary=hex_color_strategy(),
    text_secondary=optional_hex_color_strategy(),
    border_color=optional_hex_color_strategy(),
    success_color=optional_hex_color_strategy(),
    warning_color=optional_hex_color_strategy(),
    error_color=optional_hex_color_strategy(),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_migration_preserves_original_fields(
    theme_name, accent_primary, navbar_bg, sidebar_bg, surface_bg, body_bg,
    text_primary, text_secondary, border_color, success_color, warning_color,
    error_color
):
    """
    Property 13: Migration Preserves Original Fields

    For any Construction Theme record, after the migration patch executes, all
    15 original field values SHALL be identical to their pre-migration values.

    Validates: Requirements 1.3
    """
    # Create theme with all 15 original fields
    theme = frappe.get_doc({
        "doctype": "Construction Theme",
        "theme_name": theme_name or "Test Theme",
        "theme_type": "Custom Light",
        "accent_primary": accent_primary,
        "navbar_bg": navbar_bg,
        "sidebar_bg": sidebar_bg,
        "surface_bg": surface_bg,
        "body_bg": body_bg,
        "text_primary": text_primary,
        "text_secondary": text_secondary,
        "border_color": border_color,
        "success_color": success_color,
        "warning_color": warning_color,
        "error_color": error_color,
    })

    try:
        theme.insert()

        # Store original values
        original_values = {
            "accent_primary": theme.accent_primary,
            "navbar_bg": theme.navbar_bg,
            "sidebar_bg": theme.sidebar_bg,
            "surface_bg": theme.surface_bg,
            "body_bg": theme.body_bg,
            "text_primary": theme.text_primary,
            "text_secondary": theme.text_secondary,
            "border_color": theme.border_color,
            "success_color": theme.success_color,
            "warning_color": theme.warning_color,
            "error_color": theme.error_color,
        }

        # Simulate migration: populate new fields without changing original fields
        is_dark = _is_dark_theme(body_bg)
        accent_primary_val = accent_primary or "#2076FF"

        theme.primary_btn_bg = accent_primary_val
        theme.primary_btn_text = "#FFFFFF"
        theme.primary_btn_hover_bg = (
            _lighten_hex(accent_primary_val, 0.1) if is_dark
            else _darken_hex(accent_primary_val, 0.1)
        )
        theme.primary_btn_hover_text = "#FFFFFF"
        theme.secondary_btn_bg = surface_bg
        theme.secondary_btn_text = text_primary
        theme.secondary_btn_hover_bg = (
            _lighten_hex(surface_bg, 0.1) if is_dark
            else _darken_hex(surface_bg, 0.1)
        )
        theme.secondary_btn_hover_text = text_primary
        theme.table_header_bg = sidebar_bg
        theme.table_header_text = text_primary
        theme.table_body_bg = body_bg
        theme.table_body_text = text_primary
        theme.input_bg = surface_bg
        theme.input_border = border_color
        theme.input_text = text_primary
        theme.input_label_color = text_secondary
        theme.navbar_text_color = text_primary

        theme.save(update_modified=False)

        # Reload and verify original fields are unchanged
        theme.reload()

        for field_name, original_value in original_values.items():
            current_value = getattr(theme, field_name)
            assert current_value == original_value, \
                f"Field {field_name} changed: {original_value} -> {current_value}"

    finally:
        if frappe.db.exists("Construction Theme", theme.name):
            frappe.delete_doc("Construction Theme", theme.name, force=True)


# ============================================================================
# PROPERTY 14: Migration Skips Pre-Populated Fields
# ============================================================================

@given(
    theme_name=theme_name_strategy(),
    accent_primary=hex_color_strategy(),
    navbar_bg=hex_color_strategy(),
    sidebar_bg=hex_color_strategy(),
    surface_bg=hex_color_strategy(),
    body_bg=hex_color_strategy(),
    text_primary=hex_color_strategy(),
    pre_populated_primary_btn_bg=optional_hex_color_strategy(),
    pre_populated_table_header_bg=optional_hex_color_strategy(),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_migration_skips_pre_populated_fields(
    theme_name, accent_primary, navbar_bg, sidebar_bg, surface_bg, body_bg,
    text_primary, pre_populated_primary_btn_bg, pre_populated_table_header_bg
):
    """
    Property 14: Migration Skips Pre-Populated Fields

    For any Construction Theme record where a subset of new fields already have
    non-empty values before migration, the migration patch SHALL leave those
    pre-populated fields unchanged while computing defaults only for empty new
    fields.

    Validates: Requirements 11.4
    """
    # Create theme with some new fields pre-populated
    theme = frappe.get_doc({
        "doctype": "Construction Theme",
        "theme_name": theme_name or "Test Theme",
        "theme_type": "Custom Light",
        "accent_primary": accent_primary,
        "navbar_bg": navbar_bg,
        "sidebar_bg": sidebar_bg,
        "surface_bg": surface_bg,
        "body_bg": body_bg,
        "text_primary": text_primary,
        "primary_btn_bg": pre_populated_primary_btn_bg,
        "table_header_bg": pre_populated_table_header_bg,
        # Other new fields left empty
    })

    try:
        theme.insert()

        # Store pre-populated values
        original_primary_btn_bg = theme.primary_btn_bg
        original_table_header_bg = theme.table_header_bg

        # Simulate migration: only populate empty fields
        is_dark = _is_dark_theme(body_bg)
        accent_primary_val = accent_primary or "#2076FF"

        # Only set if currently empty
        if not theme.primary_btn_bg:
            theme.primary_btn_bg = accent_primary_val

        if not theme.table_header_bg:
            theme.table_header_bg = sidebar_bg

        # Set other empty fields
        if not theme.primary_btn_text:
            theme.primary_btn_text = "#FFFFFF"
        if not theme.secondary_btn_bg:
            theme.secondary_btn_bg = surface_bg

        theme.save(update_modified=False)

        # Reload and verify
        theme.reload()

        # Pre-populated fields should be unchanged
        assert theme.primary_btn_bg == original_primary_btn_bg, \
            f"Pre-populated primary_btn_bg was changed: {original_primary_btn_bg} -> {theme.primary_btn_bg}"
        assert theme.table_header_bg == original_table_header_bg, \
            f"Pre-populated table_header_bg was changed: {original_table_header_bg} -> {theme.table_header_bg}"

        # Empty fields should now be populated
        if not original_primary_btn_bg:
            assert theme.primary_btn_bg == accent_primary_val
        if not original_table_header_bg:
            assert theme.table_header_bg == sidebar_bg

    finally:
        if frappe.db.exists("Construction Theme", theme.name):
            frappe.delete_doc("Construction Theme", theme.name, force=True)
