# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

import frappe

SYSTEM_THEMES = [
	{
		"theme_name": "Light",
		"theme_type": "Custom Light",
		"is_system_theme": 1,
		"is_active": 1,
		"accent_primary": "#2076FF",
		"emoji_icon": "☀️",
		"navbar_bg": "#FFFFFF",
		"sidebar_bg": "#F8FAFC",
		"surface_bg": "#FFFFFF",
		"body_bg": "#F5F6FA",
		"text_primary": "#2C3E50",
		"text_secondary": "#7F8C8D",
		"border_color": "#D5DADF",
		"success_color": "#28a745",
		"warning_color": "#ffc107",
		"error_color": "#dc3545",
	},
	{
		"theme_name": "Dark",
		"theme_type": "Custom Dark",
		"is_system_theme": 1,
		"is_active": 1,
		"accent_primary": "#2076FF",
		"emoji_icon": "🌙",
		"navbar_bg": "#1E1E1E",
		"sidebar_bg": "#2D2D2D",
		"surface_bg": "#3A3A3A",
		"body_bg": "#1A1A1A",
		"text_primary": "#E8E8E8",
		"text_secondary": "#A8A8A8",
		"border_color": "#4A4A4A",
		"success_color": "#28a745",
		"warning_color": "#ffc107",
		"error_color": "#dc3545",
	},
	{
		"theme_name": "Construction Light",
		"theme_type": "Construction Light",
		"is_system_theme": 1,
		"is_active": 1,
		"accent_primary": "#2E7D32",
		"emoji_icon": "🏗️",
		"navbar_bg": "#F0FDF4",
		"sidebar_bg": "#F0FDF4",
		"surface_bg": "#FFFFFF",
		"body_bg": "#F0FDF4",
		"text_primary": "#181C23",
		"text_secondary": "#6B7280",
		"border_color": "#E2E6ED",
		"success_color": "#28a745",
		"warning_color": "#ffc107",
		"error_color": "#dc3545",
	},
	{
		"theme_name": "Construction Dark",
		"theme_type": "Construction Dark",
		"is_system_theme": 1,
		"is_active": 1,
		"accent_primary": "#4CAF50",
		"emoji_icon": "🏗️",
		"navbar_bg": "#1A3A1E",
		"sidebar_bg": "#0D1F12",
		"surface_bg": "#1f2937",
		"body_bg": "#111A13",
		"text_primary": "#EDEDED",
		"text_secondary": "#9CA3AF",
		"border_color": "#393C43",
		"success_color": "#28a745",
		"warning_color": "#ffc107",
		"error_color": "#dc3545",
	},
]


def create_system_themes():
	"""Idempotent creation of the 4 system themes.

	Called by after_install and after_migrate hooks.
	Does NOT call frappe.db.commit() — Frappe manages the transaction.
	"""
	for theme_data in SYSTEM_THEMES:
		if not frappe.db.exists("Construction Theme", theme_data["theme_name"]):
			doc = frappe.get_doc({"doctype": "Construction Theme", **theme_data})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
