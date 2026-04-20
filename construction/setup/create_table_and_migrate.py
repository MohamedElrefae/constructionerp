"""
Create Construction Theme table and migrate Phase 1 themes.
Run via: bench --site <site> execute construction.setup.create_table_and_migrate.run
"""

import frappe
import json


def run():
    """Create table and migrate themes in one command."""

    # Create table if not exists
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS `tabConstruction Theme` (
        `name` VARCHAR(255) NOT NULL PRIMARY KEY,
        `theme_name` VARCHAR(255) NOT NULL,
        `emoji_icon` VARCHAR(10) DEFAULT "🎨",
        `is_active` TINYINT(1) DEFAULT 1,
        `theme_type` VARCHAR(50) NOT NULL,
        `is_system_theme` TINYINT(1) DEFAULT 0,
        `is_default_light` TINYINT(1) DEFAULT 0,
        `is_default_dark` TINYINT(1) DEFAULT 0,
        `accent_primary` VARCHAR(7),
        `accent_primary_hover` VARCHAR(7),
        `accent_secondary` VARCHAR(7),
        `navbar_bg` VARCHAR(7),
        `sidebar_bg` VARCHAR(7),
        `surface_bg` VARCHAR(7),
        `body_bg` VARCHAR(7),
        `text_primary` VARCHAR(7),
        `text_secondary` VARCHAR(7),
        `border_color` VARCHAR(7),
        `success_color` VARCHAR(7) DEFAULT "#28a745",
        `warning_color` VARCHAR(7) DEFAULT "#ffc107",
        `error_color` VARCHAR(7) DEFAULT "#dc3545",
        `preview_colors` TEXT,
        `contrast_ratio` FLOAT,
        `description` TEXT,
        `custom_css` LONGTEXT,
        `creation` DATETIME DEFAULT NOW(),
        `modified` DATETIME DEFAULT NOW(),
        `modified_by` VARCHAR(255) DEFAULT "Administrator",
        `owner` VARCHAR(255) DEFAULT "Administrator",
        `docstatus` TINYINT(1) DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """

    try:
        frappe.db.sql(create_table_sql)
        print("✓ Table 'tabConstruction Theme' created or already exists")
    except Exception as e:
        print(f"Table creation note: {e}")

    # Check if table exists
    table_exists = frappe.db.sql("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'tabConstruction Theme'
    """)[0][0]

    if not table_exists:
        print("✗ Failed to create table. Aborting.")
        return

    # Migration data
    themes = [
        {
            "name": "Light",
            "theme_name": "Light",
            "emoji_icon": "☀️",
            "theme_type": "Construction Light",
            "is_system_theme": 1,
            "is_default_light": 1,
            "accent_primary": "#2076FF",
            "navbar_bg": "#f8fafc",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "description": "Standard Frappe Light theme"
        },
        {
            "name": "Dark",
            "theme_name": "Dark",
            "emoji_icon": "🌙",
            "theme_type": "Construction Dark",
            "is_system_theme": 1,
            "is_default_dark": 1,
            "accent_primary": "#3b82f6",
            "navbar_bg": "#111827",
            "sidebar_bg": "#1f2937",
            "surface_bg": "#1f2937",
            "body_bg": "#111827",
            "text_primary": "#f9fafb",
            "description": "Standard Frappe Dark theme"
        },
        {
            "name": "Construction Light",
            "theme_name": "Construction Light",
            "emoji_icon": "🏗️",
            "theme_type": "Construction Light",
            "is_system_theme": 1,
            "accent_primary": "#2E7D32",
            "navbar_bg": "#e8f5e9",
            "sidebar_bg": "#f1f8e9",
            "surface_bg": "#ffffff",
            "body_bg": "#f1f8e9",
            "text_primary": "#1b5e20",
            "description": "Construction branded light theme"
        },
        {
            "name": "Construction Dark",
            "theme_name": "Construction Dark",
            "emoji_icon": "🏗️",
            "theme_type": "Construction Dark",
            "is_system_theme": 1,
            "accent_primary": "#4CAF50",
            "navbar_bg": "#1a3a1e",
            "sidebar_bg": "#0d1f10",
            "surface_bg": "#112b15",
            "body_bg": "#0a1a0c",
            "text_primary": "#e8f5e9",
            "description": "Construction branded dark theme"
        }
    ]

    created = 0
    updated = 0

    for theme in themes:
        # Check if exists
        exists = frappe.db.sql(
            "SELECT name FROM `tabConstruction Theme` WHERE name = %s LIMIT 1",
            (theme["name"],)
        )

        if exists:
            # Update
            frappe.db.sql("""
                UPDATE `tabConstruction Theme` SET
                    theme_name = %s,
                    emoji_icon = %s,
                    theme_type = %s,
                    is_system_theme = %s,
                    is_default_light = %s,
                    is_default_dark = %s,
                    accent_primary = %s,
                    navbar_bg = %s,
                    sidebar_bg = %s,
                    surface_bg = %s,
                    body_bg = %s,
                    text_primary = %s,
                    description = %s,
                    modified = NOW()
                WHERE name = %s
            """, (
                theme["theme_name"], theme["emoji_icon"], theme["theme_type"],
                theme["is_system_theme"], theme.get("is_default_light", 0),
                theme.get("is_default_dark", 0), theme["accent_primary"],
                theme["navbar_bg"], theme["sidebar_bg"], theme["surface_bg"],
                theme["body_bg"], theme["text_primary"], theme["description"],
                theme["name"]
            ))
            updated += 1
            print(f"  Updated: {theme['name']}")
        else:
            # Insert
            frappe.db.sql("""
                INSERT INTO `tabConstruction Theme` (
                    name, theme_name, emoji_icon, is_active, theme_type,
                    is_system_theme, is_default_light, is_default_dark,
                    accent_primary, navbar_bg, sidebar_bg, surface_bg, body_bg,
                    text_primary, description, creation, modified, owner, modified_by
                ) VALUES (
                    %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    NOW(), NOW(), 'Administrator', 'Administrator'
                )
            """, (
                theme["name"], theme["theme_name"], theme["emoji_icon"],
                theme["theme_type"], theme["is_system_theme"],
                theme.get("is_default_light", 0), theme.get("is_default_dark", 0),
                theme["accent_primary"], theme["navbar_bg"], theme["sidebar_bg"],
                theme["surface_bg"], theme["body_bg"], theme["text_primary"],
                theme["description"]
            ))
            created += 1
            print(f"  Created: {theme['name']}")

    frappe.db.commit()

    print(f"\n✓ Migration Complete:")
    print(f"  Created: {created}")
    print(f"  Updated: {updated}")
    print(f"  Total: {created + updated}")

    return {"created": created, "updated": updated}
