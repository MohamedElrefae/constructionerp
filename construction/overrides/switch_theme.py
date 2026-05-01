"""
Override for Frappe's switch_theme function
Integrates custom Construction themes with Frappe's native theme system
"""

import frappe
from frappe import _


@frappe.whitelist()
def switch_theme(theme):
	"""
	Override Frappe's theme switcher to handle custom Construction themes.

	Args:
	    theme: Theme name (light, dark, automatic, construction_light, construction_dark)

	Returns:
	    dict: Success status and applied theme info
	"""
	user = frappe.session.user

	# Handle standard Frappe themes
	if theme in ["light", "dark", "automatic"]:
		# Call original Frappe function
		frappe.db.set_value("User", user, "desk_theme", theme, update_modified=False)

		# Also save in our custom system if user theme exists
		user_theme = frappe.db.get_value("User Desk Theme", {"user": user}, "name")
		if user_theme:
			frappe.db.set_value(
				"User Desk Theme",
				user_theme,
				{
					"light_theme": theme if theme != "dark" else "",
					"dark_theme": theme if theme == "dark" else "",
					"inherit_from_site": 0,
				},
			)

		return {
			"success": True,
			"theme": theme,
			"mode": _get_mode_from_theme(theme),
			"source": "frappe_native",
		}

	# Handle custom Construction themes
	if theme.startswith("construction_"):
		mode = "dark" if theme == "construction_dark" else "light"

		# Get the corresponding Modern Theme Settings
		theme_doc = frappe.db.get_value(
			"Modern Theme Settings",
			{"is_default_dark" if mode == "dark" else "is_default_light": 1, "is_active": 1},
			["name", "theme_name"],
			as_dict=True,
		)

		if not theme_doc:
			# Fallback to creating user theme preference
			theme_doc = {"name": theme, "theme_name": theme}

		# Save user theme preference
		user_theme_name = frappe.db.get_value("User Desk Theme", {"user": user}, "name")

		if user_theme_name:
			# Update existing
			frappe.db.set_value(
				"User Desk Theme",
				user_theme_name,
				{
					"light_theme": theme_doc.name if mode == "light" else None,
					"dark_theme": theme_doc.name if mode == "dark" else None,
					"inherit_from_site": 0,
				},
			)
		else:
			# Create new
			user_theme = frappe.new_doc("User Desk Theme")
			user_theme.user = user
			user_theme.inherit_from_site = 0
			user_theme.light_theme = theme_doc.name if mode == "light" else None
			user_theme.dark_theme = theme_doc.name if mode == "dark" else None
			user_theme.save(ignore_permissions=True)

		# Also update Frappe's native field for consistency
		frappe.db.set_value("User", user, "desk_theme", mode, update_modified=False)

		return {"success": True, "theme": theme_doc.theme_name, "mode": mode, "source": "construction_custom"}

	# Unknown theme
	return {"success": False, "error": f"Unknown theme: {theme}"}


def _get_mode_from_theme(theme):
	"""Get display mode from theme name"""
	if theme == "dark":
		return "dark"
	elif theme == "automatic":
		# Check system preference
		return "dark"  # Simplified - would need actual system check
	else:
		return "light"


@frappe.whitelist()
def get_user_theme_with_construction():
	"""
	Get user theme with Construction theme support.
	Combines Frappe native theme with Construction custom themes.

	Returns:
	    dict: Theme configuration
	"""
	user = frappe.session.user

	# Get Frappe native theme
	frappe_theme = frappe.db.get_value("User", user, "desk_theme") or "light"

	# Get Construction custom theme
	user_theme = frappe.db.get_value(
		"User Desk Theme", {"user": user}, ["light_theme", "dark_theme", "inherit_from_site"], as_dict=True
	)

	if not user_theme or user_theme.inherit_from_site:
		# Use site defaults
		site_settings = frappe.get_doc("Modern Theme Settings")

		mode = "light" if frappe_theme != "dark" else "dark"
		if frappe_theme == "automatic":
			mode = "light"  # Would check system preference

		return {
			"theme": site_settings.theme_name,
			"mode": mode,
			"frappe_theme": frappe_theme,
			"source": "site_default",
		}

	# Determine current mode and theme
	mode = "light" if frappe_theme != "dark" else "dark"
	theme_name = user_theme.light_theme if mode == "light" else user_theme.dark_theme

	if not theme_name:
		# Fallback to site default
		site_settings = frappe.get_doc("Modern Theme Settings")
		theme_name = site_settings.theme_name

	return {"theme": theme_name, "mode": mode, "frappe_theme": frappe_theme, "source": "user_preference"}
