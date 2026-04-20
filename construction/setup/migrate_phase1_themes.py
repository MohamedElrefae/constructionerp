"""
Phase 1 to Phase 2 Theme Migration Script
Creates Construction Theme records from the 4 hardcoded Phase 1 themes.

Run via: bench --site <site> execute construction.setup.migrate_phase1_themes.run
"""

import json
import frappe
import click


FIXTURE_THEMES = [
    {
        "theme_name": "Light",
        "emoji_icon": "☀️",
        "is_active": 1,
        "theme_type": "Construction Light",
        "is_system_theme": 1,
        "is_default_light": 1,
        "accent_primary": "#2076FF",
        "accent_primary_hover": "#4A90FF",
        "accent_secondary": "#3b82f6",
        "navbar_bg": "#f8fafc",
        "sidebar_bg": "#f1f5f9",
        "surface_bg": "#ffffff",
        "body_bg": "#f8fafc",
        "text_primary": "#111827",
        "text_secondary": "#6b7280",
        "border_color": "#e2e8f0",
        "success_color": "#28a745",
        "warning_color": "#ffc107",
        "error_color": "#dc3545",
        "preview_colors": json.dumps(["#f8fafc", "#2076FF", "#ffffff", "#111827", "#e2e8f0"]),
        "description": "Standard Frappe Light theme with blue accents"
    },
    {
        "theme_name": "Dark",
        "emoji_icon": "🌙",
        "is_active": 1,
        "theme_type": "Construction Dark",
        "is_system_theme": 1,
        "is_default_dark": 1,
        "accent_primary": "#3b82f6",
        "accent_primary_hover": "#60a5fa",
        "accent_secondary": "#4A90FF",
        "navbar_bg": "#111827",
        "sidebar_bg": "#1f2937",
        "surface_bg": "#1f2937",
        "body_bg": "#111827",
        "text_primary": "#f9fafb",
        "text_secondary": "#9ca3af",
        "border_color": "#374151",
        "success_color": "#28a745",
        "warning_color": "#ffc107",
        "error_color": "#dc3545",
        "preview_colors": json.dumps(["#111827", "#3b82f6", "#1f2937", "#f9fafb", "#374151"]),
        "description": "Standard Frappe Dark theme with blue accents"
    },
    {
        "theme_name": "Construction Light",
        "emoji_icon": "🏗️",
        "is_active": 1,
        "theme_type": "Construction Light",
        "is_system_theme": 1,
        "accent_primary": "#2E7D32",
        "accent_primary_hover": "#388E3C",
        "accent_secondary": "#4CAF50",
        "navbar_bg": "#e8f5e9",
        "sidebar_bg": "#f1f8e9",
        "surface_bg": "#ffffff",
        "body_bg": "#f1f8e9",
        "text_primary": "#1b5e20",
        "text_secondary": "#558b2f",
        "border_color": "#c8e6c9",
        "success_color": "#28a745",
        "warning_color": "#ffc107",
        "error_color": "#dc3545",
        "preview_colors": json.dumps(["#e8f5e9", "#2E7D32", "#ffffff", "#1b5e20", "#c8e6c9"]),
        "description": "Construction branded light theme with green accents"
    },
    {
        "theme_name": "Construction Dark",
        "emoji_icon": "🏗️",
        "is_active": 1,
        "theme_type": "Construction Dark",
        "is_system_theme": 1,
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
        "success_color": "#28a745",
        "warning_color": "#ffc107",
        "error_color": "#dc3545",
        "preview_colors": json.dumps(["#1a3a1e", "#4CAF50", "#0d1f10", "#e8f5e9", "#2e5c35"]),
        "description": "Construction branded dark theme with green accents"
    }
]


def run():
    """
    Idempotent migration - safe to re-run.
    Creates or updates the 4 Phase 1 themes in Construction Theme DocType.
    """
    frappe.logger().info("[Theme Migration] Starting Phase 1 to Phase 2 migration")

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for theme_data in FIXTURE_THEMES:
        theme_name = theme_data["theme_name"]

        try:
            if frappe.db.exists("Construction Theme", theme_name):
                # Update existing
                doc = frappe.get_doc("Construction Theme", theme_name)

                # Only update if it's a system theme (protect user customizations)
                if doc.is_system_theme:
                    for key, value in theme_data.items():
                        if key != "theme_name":  # Don't overwrite the name
                            setattr(doc, key, value)
                    doc.save(ignore_permissions=True)
                    updated_count += 1
                    click.echo(f"  Updated: {theme_name}")
                else:
                    skipped_count += 1
                    click.echo(f"  Skipped (user theme): {theme_name}")
            else:
                # Create new
                doc = frappe.get_doc({
                    "doctype": "Construction Theme",
                    **theme_data
                })
                doc.insert(ignore_permissions=True)
                created_count += 1
                click.echo(f"  Created: {theme_name}")

        except Exception as e:
            frappe.log_error(f"Error migrating theme {theme_name}: {str(e)}")
            click.echo(f"  Error: {theme_name} - {str(e)}")

    frappe.db.commit()

    # Log results
    summary = f"""
[Theme Migration] Complete:
  Created: {created_count}
  Updated: {updated_count}
  Skipped: {skipped_count}
  Total: {created_count + updated_count + skipped_count}
"""
    frappe.logger().info(summary)
    click.echo(summary)

    return {
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count
    }


def rollback():
    """
    Emergency rollback to Phase 1 state.
    Clears caches and resets to Frappe defaults.
    """
    click.echo("Starting rollback...")

    # 1. Clear all server-side CSS caches
    frappe.cache().delete_keys("theme_css:*")
    click.echo("  Cleared CSS caches")

    # 2. Reset active users to Frappe default theme
    try:
        frappe.db.sql("""
            UPDATE `tabUser`
            SET desk_theme = 'Light'
            WHERE desk_theme IN ('construction_light', 'construction_dark')
        """)
        click.echo("  Reset user themes to Light")
    except Exception as e:
        click.echo(f"  Warning: Could not reset user themes: {e}")

    # 3. Clear data-modern-theme from User Desk Theme records
    try:
        frappe.db.sql("""
            UPDATE `tabUser Desk Theme`
            SET light_theme = NULL, dark_theme = NULL
            WHERE light_theme LIKE 'construction_%' OR dark_theme LIKE 'construction_%'
        """)
        click.echo("  Cleared User Desk Theme custom themes")
    except Exception as e:
        click.echo(f"  Warning: Could not clear User Desk Theme: {e}")

    frappe.db.commit()

    click.echo("Rollback complete. Clear browser cache and refresh.")
    click.echo("The v2 JS loader should take over if v3 is disabled.")


def verify():
    """
    Verify that all 4 Phase 1 themes exist and have correct values.
    """
    click.echo("Verifying Phase 1 theme migration...")

    all_valid = True

    for theme_data in FIXTURE_THEMES:
        theme_name = theme_data["theme_name"]

        if not frappe.db.exists("Construction Theme", theme_name):
            click.echo(f"  MISSING: {theme_name}")
            all_valid = False
            continue

        doc = frappe.get_doc("Construction Theme", theme_name)

        # Check critical fields
        checks = [
            ("is_system_theme", 1),
            ("is_active", 1),
            ("theme_type", theme_data["theme_type"]),
        ]

        for field, expected in checks:
            actual = getattr(doc, field)
            if actual != expected:
                click.echo(f"  MISMATCH {theme_name}.{field}: expected {expected}, got {actual}")
                all_valid = False

    if all_valid:
        click.echo("  All themes verified successfully!")
    else:
        click.echo("  Verification FAILED - run migration again")

    return all_valid
