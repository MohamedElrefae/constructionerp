"""
Simple Phase 1 to Phase 2 Theme Migration - SQL Direct Insert
Creates Construction Theme records directly without Python controller dependency.

Run via: bench --site <site> execute construction.setup.migrate_phase1_themes_simple.run
"""

import json

import click
import frappe

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
		"description": "Standard Frappe Light theme with blue accents",
		"contrast_ratio": 4.5,
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
		"description": "Standard Frappe Dark theme with blue accents",
		"contrast_ratio": 4.5,
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
		"description": "Construction branded light theme with green accents",
		"contrast_ratio": 4.5,
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
		"description": "Construction branded dark theme with green accents",
		"contrast_ratio": 4.5,
	},
]


def run():
	"""
	Idempotent migration using direct SQL - safe to re-run.
	"""
	frappe.logger().info("[Theme Migration Simple] Starting Phase 1 to Phase 2 migration")

	created_count = 0
	updated_count = 0
	skipped_count = 0

	for theme_data in FIXTURE_THEMES:
		theme_name = theme_data["theme_name"]

		try:
			# Check if exists using SQL
			exists = frappe.db.sql(
				"SELECT name FROM `tabConstruction Theme` WHERE name = %s LIMIT 1",
				(theme_name,),
				as_dict=True,
			)

			if exists:
				# Update existing using SQL
				frappe.db.sql(
					"""
					UPDATE `tabConstruction Theme` SET
						emoji_icon = %s,
						is_active = %s,
						theme_type = %s,
						is_system_theme = %s,
						is_default_light = %s,
						is_default_dark = %s,
						accent_primary = %s,
						accent_primary_hover = %s,
						accent_secondary = %s,
						navbar_bg = %s,
						sidebar_bg = %s,
						surface_bg = %s,
						body_bg = %s,
						text_primary = %s,
						text_secondary = %s,
						border_color = %s,
						success_color = %s,
						warning_color = %s,
						error_color = %s,
						preview_colors = %s,
						description = %s,
						contrast_ratio = %s,
						modified = NOW()
					WHERE name = %s
				""",
					(
						theme_data["emoji_icon"],
						theme_data["is_active"],
						theme_data["theme_type"],
						theme_data["is_system_theme"],
						theme_data["is_default_light"],
						theme_data["is_default_dark"],
						theme_data["accent_primary"],
						theme_data["accent_primary_hover"],
						theme_data["accent_secondary"],
						theme_data["navbar_bg"],
						theme_data["sidebar_bg"],
						theme_data["surface_bg"],
						theme_data["body_bg"],
						theme_data["text_primary"],
						theme_data["text_secondary"],
						theme_data["border_color"],
						theme_data["success_color"],
						theme_data["warning_color"],
						theme_data["error_color"],
						theme_data["preview_colors"],
						theme_data["description"],
						theme_data["contrast_ratio"],
						theme_name,
					),
				)
				updated_count += 1
				click.echo(f"  Updated: {theme_name}")
			else:
				# Insert new using SQL
				frappe.db.sql(
					"""
					INSERT INTO `tabConstruction Theme` (
						name, theme_name, emoji_icon, is_active, theme_type,
						is_system_theme, is_default_light, is_default_dark,
						accent_primary, accent_primary_hover, accent_secondary,
						navbar_bg, sidebar_bg, surface_bg, body_bg,
						text_primary, text_secondary, border_color,
						success_color, warning_color, error_color,
						preview_colors, description, contrast_ratio,
						creation, modified, modified_by, owner, docstatus
					) VALUES (
						%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
						%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(),
						'Administrator', 'Administrator', 0
					)
				""",
					(
						theme_name,
						theme_name,
						theme_data["emoji_icon"],
						theme_data["is_active"],
						theme_data["theme_type"],
						theme_data["is_system_theme"],
						theme_data["is_default_light"],
						theme_data["is_default_dark"],
						theme_data["accent_primary"],
						theme_data["accent_primary_hover"],
						theme_data["accent_secondary"],
						theme_data["navbar_bg"],
						theme_data["sidebar_bg"],
						theme_data["surface_bg"],
						theme_data["body_bg"],
						theme_data["text_primary"],
						theme_data["text_secondary"],
						theme_data["border_color"],
						theme_data["success_color"],
						theme_data["warning_color"],
						theme_data["error_color"],
						theme_data["preview_colors"],
						theme_data["description"],
						theme_data["contrast_ratio"],
					),
				)
				created_count += 1
				click.echo(f"  Created: {theme_name}")

		except Exception as e:
			frappe.logger().error(f"[Theme Migration] Error migrating {theme_name}: {str(e)}")
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

	return {"created": created_count, "updated": updated_count, "skipped": skipped_count}
