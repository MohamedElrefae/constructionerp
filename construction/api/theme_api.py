"""
Theme API for Modern UI Theme
Handles per-user theme resolution and persistence
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_effective_desk_theme(current_mode=None):
	"""
	Returns the effective Desk Theme for current user based on:
	- User's Light/Dark/Automatic preference
	- User Desk Theme override (if enabled and allowed) - Phase 2: Server-side persistence
	- Construction Theme site defaults
	- OS preference (if Automatic)

	Phase 2 Update: Now reads from Construction Theme DocType and User Desk Theme
	to eliminate localStorage dependency.

	Args:
	    current_mode: Optional mode passed from frontend to avoid race condition

	Returns:
	    dict: {
	        "theme_name": str,           # Display name
	        "mode": "light" | "dark",
	        "source": "user_override" | "site_default" | "frappe_default",
	        "theme_doc": str,            # Construction Theme record name
	        "is_construction": bool,     # Whether it's a construction theme
	        "needs_css_injection": bool  # Whether to fetch custom CSS
	    }
	"""
	try:
		user = frappe.session.user
		user_doc = frappe.get_doc("User", user)

		# Debug logging
		frappe.logger().info(
			f"[Modern Theme v2] API called - current_mode: {current_mode}, "
			f"user desk_theme: {user_doc.desk_theme}"
		)

		# Determine light/dark mode
		if current_mode and current_mode in ["light", "dark"]:
			mode = current_mode
		else:
			mode = resolve_mode(user_doc.desk_theme)

		# Phase 2: Check for per-user Construction Theme preference first
		try:
			# Check if user has custom Construction Theme
			user_theme_pref = frappe.db.get_value(
				"User Desk Theme",
				{"user": user},
				["light_theme", "dark_theme", "inherit_from_site"],
				as_dict=True,
			)

			if user_theme_pref and not user_theme_pref.inherit_from_site:
				# User has custom theme preference
				construction_theme_name = (
					user_theme_pref.dark_theme if mode == "dark" else user_theme_pref.light_theme
				)

				if construction_theme_name:
					# Verify it's a valid Construction Theme
					theme_exists = frappe.db.exists(
						"Construction Theme", {"name": construction_theme_name, "is_active": 1}
					)

					if theme_exists:
						# Fetch feature toggles from theme
						toggles = (
							frappe.db.get_value(
								"Construction Theme",
								construction_theme_name,
								[
									"hide_help_button",
									"hide_search_bar",
									"hide_sidebar",
									"hide_like_comment",
									"mobile_card_view",
								],
								as_dict=True,
							)
							or {}
						)

						result = {
							"theme_name": construction_theme_name,
							"mode": mode,
							"source": "user_override",
							"theme_doc": construction_theme_name,
							"is_construction": True,
							"needs_css_injection": True,
							"feature_toggles": {
								"hide_help_button": toggles.get("hide_help_button", 0),
								"hide_search_bar": toggles.get("hide_search_bar", 0),
								"hide_sidebar": toggles.get("hide_sidebar", 0),
								"hide_like_comment": toggles.get("hide_like_comment", 0),
								"mobile_card_view": toggles.get("mobile_card_view", 0),
							},
						}
						frappe.logger().info(f"[Modern Theme v2] User construction theme: {result}")
						return result
		except Exception as e:
			frappe.logger().warning(f"[Modern Theme v2] Error reading user theme: {e}")

		# Check Construction Theme site defaults
		try:
			# Look for default theme for this mode
			default_theme = frappe.db.get_value(
				"Construction Theme",
				{"is_active": 1, "is_default_light" if mode == "light" else "is_default_dark": 1},
				"name",
			)

			if default_theme:
				# Fetch feature toggles from theme
				toggles = (
					frappe.db.get_value(
						"Construction Theme",
						default_theme,
						[
							"hide_help_button",
							"hide_search_bar",
							"hide_sidebar",
							"hide_like_comment",
							"mobile_card_view",
						],
						as_dict=True,
					)
					or {}
				)

				result = {
					"theme_name": default_theme,
					"mode": mode,
					"source": "site_default",
					"theme_doc": default_theme,
					"is_construction": True,
					"needs_css_injection": True,
					"feature_toggles": {
						"hide_help_button": toggles.get("hide_help_button", 0),
						"hide_search_bar": toggles.get("hide_search_bar", 0),
						"hide_sidebar": toggles.get("hide_sidebar", 0),
						"hide_like_comment": toggles.get("hide_like_comment", 0),
						"mobile_card_view": toggles.get("mobile_card_view", 0),
					},
				}
				frappe.logger().info(f"[Modern Theme v2] Site default construction theme: {result}")
				return result
		except Exception as e:
			frappe.logger().warning(f"[Modern Theme v2] Error reading site defaults: {e}")

		# Check Modern Theme Settings for configured defaults
		try:
			site_settings = frappe.get_doc("Modern Theme Settings")
			default_theme_name = (
				site_settings.default_dark_theme if mode == "dark" else site_settings.default_light_theme
			)
			if default_theme_name:
				theme_exists = frappe.db.exists(
					"Construction Theme", {"name": default_theme_name, "is_active": 1}
				)

				if theme_exists:
					toggles = (
						frappe.db.get_value(
							"Construction Theme",
							default_theme_name,
							[
								"hide_help_button",
								"hide_search_bar",
								"hide_sidebar",
								"hide_like_comment",
								"mobile_card_view",
							],
							as_dict=True,
						)
						or {}
					)

					result = {
						"theme_name": default_theme_name,
						"mode": mode,
						"source": "modern_theme_settings",
						"theme_doc": default_theme_name,
						"is_construction": True,
						"needs_css_injection": True,
						"feature_toggles": {
							"hide_help_button": toggles.get("hide_help_button", 0),
							"hide_search_bar": toggles.get("hide_search_bar", 0),
							"hide_sidebar": toggles.get("hide_sidebar", 0),
							"hide_like_comment": toggles.get("hide_like_comment", 0),
							"mobile_card_view": toggles.get("mobile_card_view", 0),
						},
					}
					return result
		except frappe.DoesNotExistError:
			pass

		# Ultimate fallback to Frappe default (Light/Dark only, no construction)
		result = {
			"theme_name": "Standard",
			"mode": mode,
			"source": "frappe_default",
			"theme_doc": None,
			"is_construction": False,
			"needs_css_injection": False,
			"feature_toggles": {},
		}
		frappe.logger().info(f"[Modern Theme v2] Returning Frappe default: {result}")
		return result

	except Exception as e:
		frappe.logger().error(f"[Modern Theme v2] Error in get_effective_desk_theme: {str(e)}")
		frappe.log_error(f"Error getting effective desk theme: {str(e)}")
		return {
			"theme_name": "Standard",
			"mode": current_mode or "light",
			"source": "error_fallback",
			"theme_doc": None,
			"is_construction": False,
			"needs_css_injection": False,
			"feature_toggles": {},
		}


@frappe.whitelist()
def get_available_themes():
	"""
	Get list of available Desk Themes from frappe_desk_theme

	Returns:
	    list: [{"name": str, "label": str, "is_standard": bool}]
	"""
	try:
		themes = frappe.get_all(
			"Desk Theme",
			fields=["name", "theme_name", "is_standard"],
			filters={"enabled": 1},
			order_by="is_standard desc, theme_name asc",
		)

		return [
			{"name": t.name, "label": t.theme_name or t.name, "is_standard": t.is_standard} for t in themes
		]
	except Exception as e:
		frappe.log_error(f"Error getting available themes: {str(e)}")
		return []


@frappe.whitelist()
def get_user_theme_settings():
	"""
	Get current user's theme settings

	Returns:
	    dict: User's theme preferences or None
	"""
	try:
		user = frappe.session.user

		# Check if user has custom theme settings
		try:
			user_theme = frappe.get_doc("User Desk Theme", {"user": user})
			return {
				"exists": True,
				"inherit_from_site": user_theme.inherit_from_site,
				"light_theme": user_theme.light_theme,
				"dark_theme": user_theme.dark_theme,
			}
		except frappe.DoesNotExistError:
			return {"exists": False}

	except Exception as e:
		frappe.log_error(f"Error getting user theme settings: {str(e)}")
		return None


@frappe.whitelist()
def save_user_theme_settings(inherit_from_site, light_theme=None, dark_theme=None):
	"""
	Save user's theme settings

	Args:
	    inherit_from_site: bool
	    light_theme: str (optional)
	    dark_theme: str (optional)

	Returns:
	    dict: {"success": bool, "message": str}
	"""
	try:
		user = frappe.session.user

		# Check if site allows user overrides
		try:
			site_settings = frappe.get_doc("Modern Theme Settings")
			if not site_settings.allow_user_override and not inherit_from_site:
				return {
					"success": False,
					"message": _("User theme overrides are not allowed by administrator"),
				}
		except frappe.DoesNotExistError:
			pass  # Settings don't exist yet, proceed with caution

		# Get or create user theme doc
		try:
			user_theme = frappe.get_doc("User Desk Theme", {"user": user})
		except frappe.DoesNotExistError:
			user_theme = frappe.new_doc("User Desk Theme")
			user_theme.user = user

		# Update settings
		user_theme.inherit_from_site = inherit_from_site
		if not inherit_from_site:
			user_theme.light_theme = light_theme
			user_theme.dark_theme = dark_theme

		user_theme.save(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True, "message": _("Theme settings saved successfully")}

	except Exception as e:
		frappe.log_error(f"Error saving user theme settings: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_modern_theme_settings():
	"""
	Get site-wide Modern Theme Settings (admin only)

	Returns:
	    dict: Site theme configuration
	"""
	if not frappe.has_permission("Modern Theme Settings", "read"):
		frappe.throw(_("Not permitted"))

	try:
		settings = frappe.get_doc("Modern Theme Settings")
		return {
			"exists": True,
			"default_light_theme": settings.default_light_theme,
			"default_dark_theme": settings.default_dark_theme,
			"allow_user_override": settings.allow_user_override,
			"enforce_contrast_check": settings.enforce_contrast_check,
			"theme_switcher_limit": settings.theme_switcher_limit,
			"css_cache_ttl": settings.css_cache_ttl,
		}
	except frappe.DoesNotExistError:
		return {"exists": False}


@frappe.whitelist()
def save_modern_theme_settings(
	default_light_theme=None,
	default_dark_theme=None,
	allow_user_override=True,
	enforce_contrast_check=False,
	theme_switcher_limit=12,
	css_cache_ttl=3600,
):
	"""
	Save site-wide Modern Theme Settings (admin only)

	Returns:
	    dict: {"success": bool, "message": str}
	"""
	if not frappe.has_permission("Modern Theme Settings", "write"):
		frappe.throw(_("Not permitted"))

	try:
		settings = frappe.get_doc("Modern Theme Settings")
		settings.default_light_theme = default_light_theme
		settings.default_dark_theme = default_dark_theme
		settings.allow_user_override = allow_user_override
		settings.enforce_contrast_check = enforce_contrast_check
		settings.theme_switcher_limit = theme_switcher_limit
		settings.css_cache_ttl = css_cache_ttl
		settings.save()
		frappe.db.commit()

		return {"success": True, "message": _("Modern Theme Settings saved successfully")}

	except Exception as e:
		frappe.log_error(f"Error saving modern theme settings: {str(e)}")
		return {"success": False, "message": str(e)}


def resolve_mode(desk_theme_pref):
	"""
	Resolve user's desk_theme preference to actual light/dark mode

	Args:
	    desk_theme_pref: str - "Light", "Dark", or "Automatic"

	Returns:
	    str: "light" or "dark"
	"""
	if desk_theme_pref == "Dark":
		return "dark"
	elif desk_theme_pref == "Light":
		return "light"
	elif desk_theme_pref == "Automatic":
		# Detect OS preference
		# Note: This would need client-side detection for accuracy
		# Server-side fallback to light
		return "light"
	else:
		return "light"


@frappe.whitelist()
def get_theme_css_variables(theme_name):
	"""
	Get CSS variables for a specific Construction Theme

	Args:
	    theme_name: str - Name of the Construction Theme record

	Returns:
	    dict: {
	        "css_variables": str,
	        "theme_data": dict
	    }
	"""
	try:
		theme = frappe.get_doc("Construction Theme", theme_name)

		return {
			"css_variables": theme.generate_css_variables(),
			"theme_data": {
				"theme_name": theme.theme_name,
				"theme_type": theme.theme_type,
				"is_default_light": theme.is_default_light,
				"is_default_dark": theme.is_default_dark,
				"is_system_theme": theme.is_system_theme,
			},
		}

	except frappe.DoesNotExistError:
		return {"css_variables": "", "theme_data": None}
	except Exception as e:
		frappe.log_error(f"Error getting theme CSS variables: {str(e)}")
		return {"css_variables": "", "theme_data": None, "error": str(e)}


@frappe.whitelist()
def save_user_mode(mode):
	"""
	Persist user's light/dark mode preference without triggering
	TimestampMismatchError. Uses frappe.db.set_value with
	update_modified=False so it never conflicts with concurrent
	User document writes.

	Args:
	    mode: str - "light" or "dark"

	Returns:
	    dict: {"success": bool}
	"""
	try:
		if mode not in ("light", "dark"):
			return {"success": False, "message": "Invalid mode"}

		user = frappe.session.user
		desk_theme_value = "Dark" if mode == "dark" else "Light"

		# Direct DB update — skips ORM validation & modified timestamp check
		frappe.db.set_value("User", user, "desk_theme", desk_theme_value, update_modified=False)
		frappe.db.commit()

		return {"success": True, "mode": mode}
	except Exception as e:
		frappe.log_error(f"Error saving user mode: {str(e)}")
		return {"success": False, "message": str(e)}


def _get_theme_css_template(theme_name, normalized_key):
	"""
	Generate comprehensive CSS template that applies Construction theme variables.
	This CSS uses the CSS variables defined in generate_css_variables() to override Frappe styles.
	"""
	is_dark = 'dark' in normalized_key
	
	# Base template with CSS that actually applies the variables
	template = f"""
/* ===== CONSTRUCTION THEME CSS TEMPLATE ===== */
/* Theme: {theme_name} | Key: {normalized_key} */

/* --- Root scope with data attribute --- */
[data-modern-theme="{normalized_key}"] {{
  /* Apply body background */
  background-color: var(--ct-body-bg) !important;
}}

/* --- Navbar styling --- */
[data-modern-theme="{normalized_key}"] .navbar,
[data-modern-theme="{normalized_key}"] .navbar.navbar-expand,
[data-modern-theme="{normalized_key}"] header.navbar {{
  background: var(--ct-navbar-bg) !important;
  border-bottom: 1px solid var(--ct-border-color) !important;
}}

[data-modern-theme="{normalized_key}"] .navbar .nav-link,
[data-modern-theme="{normalized_key}"] .navbar .navbar-brand {{
  color: var(--ct-text-primary) !important;
}}

/* --- Sidebar styling --- */
[data-modern-theme="{normalized_key}"] .layout-side-section,
[data-modern-theme="{normalized_key}"] .sidebar,
[data-modern-theme="{normalized_key}"] .desk-sidebar,
[data-modern-theme="{normalized_key}"] .form-sidebar {{
  background: var(--ct-sidebar-bg) !important;
  border-right: 1px solid var(--ct-border-color) !important;
}}

/* --- Sidebar items (comprehensive Frappe v16 selectors) --- */
[data-modern-theme="{normalized_key}"] .layout-side-section .sidebar-item,
[data-modern-theme="{normalized_key}"] .desk-sidebar .sidebar-item,
[data-modern-theme="{normalized_key}"] .standard-sidebar-item a,
[data-modern-theme="{normalized_key}"] .sidebar-item-container a,
[data-modern-theme="{normalized_key}"] .desk-sidebar .standard-sidebar-item a,
[data-modern-theme="{normalized_key}"] .layout-side-section .item-anchor,
[data-modern-theme="{normalized_key}"] .desk-sidebar .item-anchor,
[data-modern-theme="{normalized_key}"] .sidebar .item-anchor {{
  color: var(--ct-text-primary) !important;
  text-decoration: none !important;
}}

[data-modern-theme="{normalized_key}"] .layout-side-section .sidebar-item:hover,
[data-modern-theme="{normalized_key}"] .desk-sidebar .sidebar-item:hover,
[data-modern-theme="{normalized_key}"] .standard-sidebar-item:hover a,
[data-modern-theme="{normalized_key}"] .sidebar-item-container:hover a,
[data-modern-theme="{normalized_key}"] .desk-sidebar .standard-sidebar-item:hover,
[data-modern-theme="{normalized_key}"] .layout-side-section .item-anchor:hover,
[data-modern-theme="{normalized_key}"] .desk-sidebar .item-anchor:hover,
[data-modern-theme="{normalized_key}"] .sidebar .item-anchor:hover {{
  background: var(--ct-accent-hover) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Active/selected sidebar item --- */
[data-modern-theme="{normalized_key}"] .standard-sidebar-item.selected a,
[data-modern-theme="{normalized_key}"] .sidebar-item-container.selected a,
[data-modern-theme="{normalized_key}"] .standard-sidebar-item.selected .item-anchor,
[data-modern-theme="{normalized_key}"] .sidebar-item.selected .item-anchor,
[data-modern-theme="{normalized_key}"] .layout-side-section .selected .item-anchor {{
  color: var(--ct-text-primary) !important;
  font-weight: 600 !important;
}}

/* --- Force sidebar background for Frappe v16 --- */
html[data-modern-theme="{normalized_key}"] .layout-side-section,
html[data-modern-theme="{normalized_key}"] .desk-sidebar,
html[data-modern-theme="{normalized_key}"] [data-theme="light"] .layout-side-section,
html[data-modern-theme="{normalized_key}"] [data-theme="light"] .desk-sidebar {{
  background: var(--ct-sidebar-bg) !important;
}}

/* AGGRESSIVE: Force ALL text in sidebar to be light */
html[data-modern-theme="{normalized_key}"] .layout-side-section *,
html[data-modern-theme="{normalized_key}"] .desk-sidebar *,
html[data-modern-theme="{normalized_key}"] .layout-side-section .sidebar-item *,
html[data-modern-theme="{normalized_key}"] .desk-sidebar .sidebar-item * {{
  color: var(--ct-text-primary) !important;
}}

/* AGGRESSIVE: Force all links in sidebar */
html[data-modern-theme="{normalized_key}"] .layout-side-section a,
html[data-modern-theme="{normalized_key}"] .desk-sidebar a,
html[data-modern-theme="{normalized_key}"] .layout-side-section a:link,
html[data-modern-theme="{normalized_key}"] .desk-sidebar a:link,
html[data-modern-theme="{normalized_key}"] .layout-side-section a:visited,
html[data-modern-theme="{normalized_key}"] .desk-sidebar a:visited {{
  color: var(--ct-text-primary) !important;
}}

/* --- Main content area (comprehensive Frappe v16 selectors) --- */
html[data-modern-theme="{normalized_key}"] body,
html[data-modern-theme="{normalized_key}"] .layout-main-section,
html[data-modern-theme="{normalized_key}"] .content,
html[data-modern-theme="{normalized_key}"] .page-wrapper,
html[data-modern-theme="{normalized_key}"] .page-container,
html[data-modern-theme="{normalized_key}"] #page-container,
html[data-modern-theme="{normalized_key}"] .layout-main,
html[data-modern-theme="{normalized_key}"] .content.page-container {{
  background: var(--ct-body-bg) !important;
}}

/* --- Cards, widgets, and tree views --- */
[data-modern-theme="{normalized_key}"] .card,
[data-modern-theme="{normalized_key}"] .widget,
[data-modern-theme="{normalized_key}"] .section-head,
[data-modern-theme="{normalized_key}"] .form-section,
[data-modern-theme="{normalized_key}"] .dialog,
[data-modern-theme="{normalized_key}"] .tree-node,
[data-modern-theme="{normalized_key}"] .tree-children,
[data-modern-theme="{normalized_key}"] .tree-node-content,
[data-modern-theme="{normalized_key}"] .treemap-node,
[data-modern-theme="{normalized_key}"] .list-row,
[data-modern-theme="{normalized_key}"] .grid-row {{
  background: var(--ct-surface-bg) !important;
  border-color: var(--ct-border-color) !important;
}}

/* --- Widget headers and shortcut pills --- */
[data-modern-theme="{normalized_key}"] .widget-head,
[data-modern-theme="{normalized_key}"] .widget-title,
[data-modern-theme="{normalized_key}"] .widget .ellipsis,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box .widget-title,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box a,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box .link-text,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box .badge,
[data-modern-theme="{normalized_key}"] .widget-label,
[data-modern-theme="{normalized_key}"] .widget-subtitle,
[data-modern-theme="{normalized_key}"] .widget-control {{
  color: var(--ct-text-primary) !important;
}}

/* --- Sidebar icons and emojis --- */
html[data-modern-theme="{normalized_key}"] .layout-side-section .sidebar-item-icon,
html[data-modern-theme="{normalized_key}"] .desk-sidebar .sidebar-item-icon,
html[data-modern-theme="{normalized_key}"] .layout-side-section .icon,
html[data-modern-theme="{normalized_key}"] .desk-sidebar .icon,
html[data-modern-theme="{normalized_key}"] .layout-side-section svg,
html[data-modern-theme="{normalized_key}"] .desk-sidebar svg,
html[data-modern-theme="{normalized_key}"] .layout-side-section use,
html[data-modern-theme="{normalized_key}"] .desk-sidebar use {{
  fill: var(--ct-text-primary) !important;
  color: var(--ct-text-primary) !important;
  stroke: var(--ct-text-primary) !important;
}}

/* --- Charts and graph labels --- */
[data-modern-theme="{normalized_key}"] .chart-container text,
[data-modern-theme="{normalized_key}"] .chart-label,
[data-modern-theme="{normalized_key}"] .axis-label,
[data-modern-theme="{normalized_key}"] .chart-legend,
[data-modern-theme="{normalized_key}"] .graph-svg-tip,
[data-modern-theme="{normalized_key}"] .bar-chart text,
[data-modern-theme="{normalized_key}"] .bar-chart .chart-label,
[data-modern-theme="{normalized_key}"] .chart-container .dataset-label {{
  fill: var(--ct-text-primary) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Shortcut pills background fix --- */
[data-modern-theme="{normalized_key}"] .shortcut-widget-box,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box .widget-body,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box .pill {{
  background: var(--ct-surface) !important;
}}
[data-modern-theme="{normalized_key}"] .shortcut-widget-box .pill {{
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

/* --- Shortcut pills and badges - force dark background --- */
[data-modern-theme="{normalized_key}"] .shortcut-widget-box .pill,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box .badge,
[data-modern-theme="{normalized_key}"] .badge,
[data-modern-theme="{normalized_key}"] .pill,
[data-modern-theme="{normalized_key}"] .pill-badge,
[data-modern-theme="{normalized_key}"] .count-badge,
[data-modern-theme="{normalized_key}"] [class*="badge"],
[data-modern-theme="{normalized_key}"] [class*="pill"] {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

/* --- Force all white backgrounds to dark in widgets --- */
[data-modern-theme="{normalized_key}"] .widget .pill[style*="background"],
[data-modern-theme="{normalized_key}"] .widget .badge[style*="background"],
[data-modern-theme="{normalized_key}"] .shortcut-widget-box span[class*="pill"],
[data-modern-theme="{normalized_key}"] .shortcut-widget-box span[class*="badge"] {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Section headers --- */
[data-modern-theme="{normalized_key}"] .section-title,
[data-modern-theme="{normalized_key}"] .section-head {{
  color: var(--ct-text-primary) !important;
}}

/* --- Text colors --- */
[data-modern-theme="{normalized_key}"] body,
[data-modern-theme="{normalized_key}"] .text-color,
[data-modern-theme="{normalized_key}"] .text-muted,
[data-modern-theme="{normalized_key}"] h1, [data-modern-theme="{normalized_key}"] h2, 
[data-modern-theme="{normalized_key}"] h3, [data-modern-theme="{normalized_key}"] h4,
[data-modern-theme="{normalized_key}"] h5, [data-modern-theme="{normalized_key}"] h6 {{
  color: var(--ct-text-primary) !important;
}}

/* --- Buttons --- */
[data-modern-theme="{normalized_key}"] .btn-primary {{
  background: var(--ct-primary-btn-bg) !important;
  border-color: var(--ct-primary-btn-bg) !important;
  color: var(--ct-primary-btn-text) !important;
}}

[data-modern-theme="{normalized_key}"] .btn-primary:hover {{
  background: var(--ct-primary-btn-hover-bg) !important;
  border-color: var(--ct-primary-btn-hover-bg) !important;
}}

[data-modern-theme="{normalized_key}"] .btn-secondary {{
  background: var(--ct-secondary-btn-bg) !important;
  border-color: var(--ct-secondary-btn-bg) !important;
  color: var(--ct-secondary-btn-text) !important;
}}

/* --- Links --- */
[data-modern-theme="{normalized_key}"] a,
[data-modern-theme="{normalized_key}"] .link-primary {{
  color: var(--ct-accent-primary) !important;
}}

[data-modern-theme="{normalized_key}"] a:hover {{
  color: var(--ct-accent-hover) !important;
}}

/* --- Buttons - comprehensive styling --- */
[data-modern-theme="{normalized_key}"] .btn {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .btn:hover {{
  background: var(--ct-accent-hover) !important;
  border-color: var(--ct-accent) !important;
}}

[data-modern-theme="{normalized_key}"] .btn-primary {{
  background: var(--ct-accent) !important;
  border-color: var(--ct-accent) !important;
  color: #ffffff !important;
}}

[data-modern-theme="{normalized_key}"] .btn-primary:hover {{
  background: #45a049 !important;
  border-color: #45a049 !important;
}}

[data-modern-theme="{normalized_key}"] .btn-secondary,
[data-modern-theme="{normalized_key}"] .btn-default {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .btn-danger {{
  background: #dc3545 !important;
  border-color: #dc3545 !important;
  color: #ffffff !important;
}}

[data-modern-theme="{normalized_key}"] .btn-success {{
  background: #28a745 !important;
  border-color: #28a745 !important;
  color: #ffffff !important;
}}

[data-modern-theme="{normalized_key}"] .btn-warning {{
  background: #ffc107 !important;
  border-color: #ffc107 !important;
  color: #212529 !important;
}}

[data-modern-theme="{normalized_key}"] .btn:disabled,
[data-modern-theme="{normalized_key}"] .btn.disabled {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-muted) !important;
  opacity: 0.6 !important;
}}

/* --- Form elements - comprehensive --- */
[data-modern-theme="{normalized_key}"] input,
[data-modern-theme="{normalized_key}"] select,
[data-modern-theme="{normalized_key}"] textarea,
[data-modern-theme="{normalized_key}"] .form-control {{
  background: var(--ct-surface) !important;
  border-color: var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] input:focus,
[data-modern-theme="{normalized_key}"] select:focus,
[data-modern-theme="{normalized_key}"] textarea:focus,
[data-modern-theme="{normalized_key}"] .form-control:focus {{
  border-color: var(--ct-accent) !important;
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2) !important;
}}

[data-modern-theme="{normalized_key}"] input::placeholder,
[data-modern-theme="{normalized_key}"] textarea::placeholder {{
  color: var(--ct-text-muted) !important;
}}

[data-modern-theme="{normalized_key}"] .input-group-text {{
  background: var(--ct-surface) !important;
  border-color: var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .form-label,
[data-modern-theme="{normalized_key}"] label {{
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .form-text,
[data-modern-theme="{normalized_key}"] .help-text {{
  color: var(--ct-text-muted) !important;
}}

/* --- Tables - comprehensive --- */
[data-modern-theme="{normalized_key}"] .table,
[data-modern-theme="{normalized_key}"] .datatable,
[data-modern-theme="{normalized_key}"] .list-row,
[data-modern-theme="{normalized_key}"] .data-row {{
  background: var(--ct-surface-bg) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .table thead th,
[data-modern-theme="{normalized_key}"] .datatable-header,
[data-modern-theme="{normalized_key}"] .list-row-head {{
  background: var(--ct-navbar-bg) !important;
  color: var(--ct-text-primary) !important;
  border-color: var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .table td,
[data-modern-theme="{normalized_key}"] .table th {{
  border-color: var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .table-hover tbody tr:hover,
[data-modern-theme="{normalized_key}"] .list-row:hover,
[data-modern-theme="{normalized_key}"] .data-row:hover {{
  background: var(--ct-accent-hover) !important;
}}

[data-modern-theme="{normalized_key}"] .table-striped tbody tr:nth-of-type(odd) {{
  background: rgba(255,255,255,0.03) !important;
}}

[data-modern-theme="{normalized_key}"] .list-row.active,
[data-modern-theme="{normalized_key}"] .data-row.active {{
  background: var(--ct-accent-hover) !important;
}}

/* --- Dropdown menus - comprehensive --- */
[data-modern-theme="{normalized_key}"] .dropdown-menu {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-item {{
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-item:hover,
[data-modern-theme="{normalized_key}"] .dropdown-item:focus,
[data-modern-theme="{normalized_key}"] .dropdown-item.active {{
  background: var(--ct-accent-hover) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-header {{
  color: var(--ct-text-muted) !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-divider {{
  border-top: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-toggle {{
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-toggle:hover {{
  background: var(--ct-accent-hover) !important;
}}

/* --- Dropdown Menu Visibility Fix (Issue #1) --- */
[data-modern-theme="{normalized_key}"] .dropdown-menu,
[data-modern-theme="{normalized_key}"] .dropdown-menu.show,
[data-modern-theme="{normalized_key}"] .dropdown-list,
[data-modern-theme="{normalized_key}"] .dropdown-help {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-menu li,
[data-modern-theme="{normalized_key}"] .dropdown-menu li a,
[data-modern-theme="{normalized_key}"] .dropdown-item span,
[data-modern-theme="{normalized_key}"] .dropdown-list li a {{
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-menu li a:hover,
[data-modern-theme="{normalized_key}"] .dropdown-list li a:hover {{
  background: var(--ct-accent-hover) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Menu Toggle Switches Fix --- */
[data-modern-theme="{normalized_key}"] .menu-btn-group .toggle-switch,
[data-modern-theme="{normalized_key}"] .dropdown-menu .toggle-switch,
[data-modern-theme="{normalized_key}"] .menu-switch,
[data-modern-theme="{normalized_key}"] .toggle-btn,
[data-modern-theme="{normalized_key}"] .btn-toggle {{
  background: var(--ct-surface) !important;
  border: 2px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .menu-btn-group .toggle-switch.active,
[data-modern-theme="{normalized_key}"] .dropdown-menu .toggle-switch.active,
[data-modern-theme="{normalized_key}"] .toggle-switch:checked,
[data-modern-theme="{normalized_key}"] .toggle-btn.active {{
  background: var(--ct-accent) !important;
  border-color: var(--ct-accent) !important;
}}

[data-modern-theme="{normalized_key}"] .toggle-switch .toggle-slider,
[data-modern-theme="{normalized_key}"] .toggle-btn .slider {{
  background: var(--ct-text-muted) !important;
}}

[data-modern-theme="{normalized_key}"] .toggle-switch.active .toggle-slider,
[data-modern-theme="{normalized_key}"] .toggle-switch:checked .toggle-slider {{
  background: #ffffff !important;
}}

/* --- Menu Items Better Styling --- */
[data-modern-theme="{normalized_key}"] .menu-item,
[data-modern-theme="{normalized_key}"] .menu-btn-group .menu-item,
[data-modern-theme="{normalized_key}"] .dropdown-menu .menu-item {{
  color: var(--ct-text-primary) !important;
  background: transparent !important;
}}

[data-modern-theme="{normalized_key}"] .menu-item:hover,
[data-modern-theme="{normalized_key}"] .menu-item.active {{
  background: var(--ct-accent-hover) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Form Inputs Dark Theme --- */
[data-modern-theme="{normalized_key}"] .form-control,
[data-modern-theme="{normalized_key}"] input.form-control,
[data-modern-theme="{normalized_key}"] textarea.form-control,
[data-modern-theme="{normalized_key}"] select.form-control {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .form-control:focus {{
  border-color: var(--ct-accent) !important;
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.3) !important;
}}

[data-modern-theme="{normalized_key}"] .form-control::placeholder {{
  color: var(--ct-text-muted) !important;
}}

/* --- AGGRESSIVE Dropdown Menu Solid Background --- */
[data-modern-theme="{normalized_key}"] .dropdown-menu,
[data-modern-theme="{normalized_key}"] .dropdown-menu.show,
[data-modern-theme="{normalized_key}"] .menu-dropdown,
[data-modern-theme="{normalized_key}"] .dropdown-list,
[data-modern-theme="{normalized_key}"] ul.dropdown-menu,
[data-modern-theme="{normalized_key}"] div.dropdown-menu {{
  background: #1a2e1f !important;
  background-color: #1a2e1f !important;
  border: 1px solid #2f4a36 !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.8) !important;
  z-index: 99999 !important;
  opacity: 1 !important;
  visibility: visible !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-menu > li,
[data-modern-theme="{normalized_key}"] .dropdown-menu > li > a,
[data-modern-theme="{normalized_key}"] .dropdown-item,
[data-modern-theme="{normalized_key}"] .dropdown-menu span,
[data-modern-theme="{normalized_key}"] .dropdown-menu li span {{
  background: transparent !important;
  color: #f9fafb !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-menu > li > a:hover,
[data-modern-theme="{normalized_key}"] .dropdown-item:hover,
[data-modern-theme="{normalized_key}"] .dropdown-menu li:hover {{
  background: #45a049 !important;
  color: #ffffff !important;
}}

/* --- AGGRESSIVE Button Visibility Fix --- */
[data-modern-theme="{normalized_key}"] .btn,
[data-modern-theme="{normalized_key}"] button.btn,
[data-modern-theme="{normalized_key}"] a.btn,
[data-modern-theme="{normalized_key}"] .page-actions .btn,
[data-modern-theme="{normalized_key}"] .actions-btn-group .btn {{
  background: #1a2e1f !important;
  color: #f9fafb !important;
  border: 2px solid #4CAF50 !important;
  border-radius: 6px !important;
  padding: 8px 16px !important;
  font-weight: 500 !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
  transition: all 0.2s ease !important;
  cursor: pointer !important;
}}

[data-modern-theme="{normalized_key}"] .btn-primary,
[data-modern-theme="{normalized_key}"] .btn.btn-primary {{
  background: #4CAF50 !important;
  color: #ffffff !important;
  border: 2px solid #4CAF50 !important;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.5) !important;
}}

[data-modern-theme="{normalized_key}"] .btn:hover,
[data-modern-theme="{normalized_key}"] .btn-secondary:hover,
[data-modern-theme="{normalized_key}"] .btn-default:hover {{
  background: #45a049 !important;
  color: #ffffff !important;
  border-color: #4CAF50 !important;
  box-shadow: 0 4px 16px rgba(76, 175, 80, 0.4) !important;
  transform: translateY(-2px) !important;
}}

[data-modern-theme="{normalized_key}"] .btn-primary:hover {{
  background: #45a049 !important;
  box-shadow: 0 4px 16px rgba(76, 175, 80, 0.6) !important;
  transform: translateY(-2px) !important;
}}

[data-modern-theme="{normalized_key}"] .btn:disabled,
[data-modern-theme="{normalized_key}"] .btn.disabled {{
  background: #2a3a2f !important;
  color: #6b7280 !important;
  border-color: #4a5a4f !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-backdrop {{
  background: rgba(0,0,0,0.5) !important;
  z-index: 9990 !important;
}}

/* --- ULTRA AGGRESSIVE Filter Area Fix (White Background Issue) --- */
[data-modern-theme="{normalized_key}"] .filter-area,
[data-modern-theme="{normalized_key}"] .filter-box,
[data-modern-theme="{normalized_key}"] .filter-section,
[data-modern-theme="{normalized_key}"] .list-filter,
[data-modern-theme="{normalized_key}"] .form-group.frappe-control,
[data-modern-theme="{normalized_key}"] .frappe-control[data-fieldtype="Filter"] {{
  background: var(--ct-navbar-bg) !important;
  background-color: var(--ct-navbar-bg) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .filter-area input,
[data-modern-theme="{normalized_key}"] .filter-box input,
[data-modern-theme="{normalized_key}"] .filter-section input,
[data-modern-theme="{normalized_key}"] .filter-area select,
[data-modern-theme="{normalized_key}"] .filter-box select {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .filter-area label,
[data-modern-theme="{normalized_key}"] .filter-box label,
[data-modern-theme="{normalized_key}"] .filter-section label,
[data-modern-theme="{normalized_key}"] .filter-label {{
  color: var(--ct-text-primary) !important;
}}

/* --- ULTRA AGGRESSIVE Dropdown Fix --- */
[data-modern-theme="{normalized_key}"] .dropdown-menu,
[data-modern-theme="{normalized_key}"] .dropdown-menu.show,
[data-modern-theme="{normalized_key}"] ul.dropdown-menu,
[data-modern-theme="{normalized_key}"] div.dropdown-menu,
[data-modern-theme="{normalized_key}"] .navbar .dropdown-menu,
[data-modern-theme="{normalized_key}"] .nav .dropdown-menu {{
  background: #1a2e1f !important;
  background-color: #1a2e1f !important;
  border: 1px solid #2f4a36 !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.8) !important;
  z-index: 99999 !important;
  opacity: 1 !important;
  visibility: visible !important;
  position: absolute !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-menu li,
[data-modern-theme="{normalized_key}"] .dropdown-menu li a,
[data-modern-theme="{normalized_key}"] .dropdown-item,
[data-modern-theme="{normalized_key}"] .dropdown-item span,
[data-modern-theme="{normalized_key}"] .dropdown-menu a {{
  background: transparent !important;
  color: #f9fafb !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-menu li:hover,
[data-modern-theme="{normalized_key}"] .dropdown-menu li a:hover,
[data-modern-theme="{normalized_key}"] .dropdown-item:hover {{
  background: #45a049 !important;
  color: #ffffff !important;
}}

/* --- ULTRA AGGRESSIVE Button Fix --- */
[data-modern-theme="{normalized_key}"] .btn,
[data-modern-theme="{normalized_key}"] button.btn,
[data-modern-theme="{normalized_key}"] a.btn,
[data-modern-theme="{normalized_key}"] .page-actions .btn,
[data-modern-theme="{normalized_key}"] .actions-btn-group .btn,
[data-modern-theme="{normalized_key}"] .navbar .btn,
[data-modern-theme="{normalized_key}"] .nav .btn {{
  background: #1a2e1f !important;
  background-color: #1a2e1f !important;
  color: #f9fafb !important;
  border: 2px solid #4CAF50 !important;
  border-radius: 6px !important;
  padding: 8px 16px !important;
  font-weight: 500 !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
  transition: all 0.2s ease !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
}}

[data-modern-theme="{normalized_key}"] .btn-primary,
[data-modern-theme="{normalized_key}"] .btn.btn-primary {{
  background: #4CAF50 !important;
  background-color: #4CAF50 !important;
  color: #ffffff !important;
  border: 2px solid #4CAF50 !important;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.5) !important;
}}

[data-modern-theme="{normalized_key}"] .btn:hover,
[data-modern-theme="{normalized_key}"] button.btn:hover,
[data-modern-theme="{normalized_key}"] a.btn:hover {{
  background: #45a049 !important;
  color: #ffffff !important;
  border-color: #4CAF50 !important;
  box-shadow: 0 4px 16px rgba(76, 175, 80, 0.4) !important;
  transform: translateY(-2px) !important;
}}

[data-modern-theme="{normalized_key}"] .btn-primary:hover {{
  background: #45a049 !important;
  box-shadow: 0 4px 16px rgba(76, 175, 80, 0.6) !important;
  transform: translateY(-2px) !important;
}}

[data-modern-theme="{normalized_key}"] .btn .icon,
[data-modern-theme="{normalized_key}"] .btn svg {{
  fill: currentColor !important;
  stroke: currentColor !important;
}}

/* --- Action Buttons Fix (Issue #1) - More aggressive with proper colors --- */
[data-modern-theme="{normalized_key}"] .page-actions,
[data-modern-theme="{normalized_key}"] .page-actions .btn,
[data-modern-theme="{normalized_key}"] .page-actions .btn-action,
[data-modern-theme="{normalized_key}"] .actions-btn-group,
[data-modern-theme="{normalized_key}"] .actions-btn-group .btn {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .page-actions .btn:hover,
[data-modern-theme="{normalized_key}"] .actions-btn-group .btn:hover {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border-color: var(--ct-accent) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}}

[data-modern-theme="{normalized_key}"] .page-actions .btn svg,
[data-modern-theme="{normalized_key}"] .actions-btn-group .btn svg {{
  fill: var(--ct-text-primary) !important;
  stroke: var(--ct-text-primary) !important;
}}

/* --- Widget/Card Headers Fix (Issue #3) --- */
[data-modern-theme="{normalized_key}"] .widget .widget-head,
[data-modern-theme="{normalized_key}"] .widget-head .widget-title,
[data-modern-theme="{normalized_key}"] .section-head,
[data-modern-theme="{normalized_key}"] .widget-group .widget-group-head,
[data-modern-theme="{normalized_key}"] .widget-group .widget-group-title,
[data-modern-theme="{normalized_key}"] .widget .head {{
  color: var(--ct-text-primary) !important;
  background: transparent !important;
}}

[data-modern-theme="{normalized_key}"] .widget .widget-title,
[data-modern-theme="{normalized_key}"] .widget-group-title,
[data-modern-theme="{normalized_key}"] .section-head h4,
[data-modern-theme="{normalized_key}"] .section-head h5 {{
  color: var(--ct-text-primary) !important;
  font-weight: 600 !important;
}}

/* --- Card Items/Links with Hover (Issue #4) --- */
[data-modern-theme="{normalized_key}"] .widget a,
[data-modern-theme="{normalized_key}"] .widget .widget-item,
[data-modern-theme="{normalized_key}"] .widget .item,
[data-modern-theme="{normalized_key}"] .widget .widget-link,
[data-modern-theme="{normalized_key}"] .widget-content a,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box a,
[data-modern-theme="{normalized_key}"] .widget-body a,
[data-modern-theme="{normalized_key}"] .widget-list a {{
  color: var(--ct-accent) !important;
  transition: all 0.2s ease !important;
}}

[data-modern-theme="{normalized_key}"] .widget a:hover,
[data-modern-theme="{normalized_key}"] .widget .widget-item:hover,
[data-modern-theme="{normalized_key}"] .widget .item:hover,
[data-modern-theme="{normalized_key}"] .widget .widget-link:hover,
[data-modern-theme="{normalized_key}"] .widget-content a:hover,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box a:hover,
[data-modern-theme="{normalized_key}"] .widget-body a:hover {{
  color: var(--ct-accent-hover) !important;
  background: rgba(76, 175, 80, 0.1) !important;
  padding-left: 4px !important;
  border-radius: 4px !important;
}}

[data-modern-theme="{normalized_key}"] .widget .ellipsis,
[data-modern-theme="{normalized_key}"] .widget-item .ellipsis,
[data-modern-theme="{normalized_key}"] .widget-body .ellipsis {{
  color: var(--ct-accent) !important;
}}

[data-modern-theme="{normalized_key}"] .widget .ellipsis:hover {{
  color: var(--ct-accent-hover) !important;
}}

/* --- Table Hover Text Readability Fix --- */
[data-modern-theme="{normalized_key}"] .table tbody tr:hover td,
[data-modern-theme="{normalized_key}"] .datatable .data-row:hover .data-row-col,
[data-modern-theme="{normalized_key}"] .list-row:hover .list-row-col,
[data-modern-theme="{normalized_key}"] .list-row:hover .level-item,
[data-modern-theme="{normalized_key}"] .table-hover tbody tr:hover td * {{
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .table tbody tr:hover,
[data-modern-theme="{normalized_key}"] .list-row:hover,
[data-modern-theme="{normalized_key}"] .datatable .data-row:hover {{
  background: var(--ct-accent-hover) !important;
}}

/* --- Header Filter Fix (White background issue) --- */
[data-modern-theme="{normalized_key}"] .list-row-head,
[data-modern-theme="{normalized_key}"] .list-filter,
[data-modern-theme="{normalized_key}"] .filter-box,
[data-modern-theme="{normalized_key}"] .filter-section,
[data-modern-theme="{normalized_key}"] .filter-area {{
  background: var(--ct-navbar-bg) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .filter-box input,
[data-modern-theme="{normalized_key}"] .filter-area input,
[data-modern-theme="{normalized_key}"] .filter-section input {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .filter-label,
[data-modern-theme="{normalized_key}"] .list-row-head .list-check-all,
[data-modern-theme="{normalized_key}"] .list-row-head .list-row-checkbox {{
  color: var(--ct-text-primary) !important;
}}

/* --- Dropdown Menu Solid Background Fix --- */
[data-modern-theme="{normalized_key}"] .dropdown-menu,
[data-modern-theme="{normalized_key}"] .dropdown-menu.show,
[data-modern-theme="{normalized_key}"] .menu-dropdown,
[data-modern-theme="{normalized_key}"] .dropdown-list {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
  z-index: 9999 !important;
  opacity: 1 !important;
  visibility: visible !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-menu li,
[data-modern-theme="{normalized_key}"] .dropdown-menu li a,
[data-modern-theme="{normalized_key}"] .dropdown-item,
[data-modern-theme="{normalized_key}"] .dropdown-item span {{
  background: transparent !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .dropdown-menu li a:hover,
[data-modern-theme="{normalized_key}"] .dropdown-item:hover {{
  background: var(--ct-accent-hover) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Action Buttons with better visibility --- */
[data-modern-theme="{normalized_key}"] .page-actions .btn,
[data-modern-theme="{normalized_key}"] .actions-btn-group .btn,
[data-modern-theme="{normalized_key}"] .menu-btn-group .btn {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 2px solid var(--ct-border) !important;
  border-radius: 6px !important;
  font-weight: 500 !important;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
}}

[data-modern-theme="{normalized_key}"] .page-actions .btn:hover,
[data-modern-theme="{normalized_key}"] .actions-btn-group .btn:hover {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border-color: var(--ct-accent) !important;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4) !important;
  transform: translateY(-2px) !important;
}}

/* --- Widget Headers Forced White --- */
[data-modern-theme="{normalized_key}"] .widget .widget-title,
[data-modern-theme="{normalized_key}"] .widget-group .widget-group-title,
[data-modern-theme="{normalized_key}"] .widget-shortcut-title,
[data-modern-theme="{normalized_key}"] .section-head,
[data-modern-theme="{normalized_key}"] .widget-head h4,
[data-modern-theme="{normalized_key}"] .widget-head h5,
[data-modern-theme="{normalized_key}"] .widget-group-head h4,
[data-modern-theme="{normalized_key}"] .widget-group-head h5 {{
  color: #ffffff !important;
  text-shadow: none !important;
}}

/* --- Card Border Effect (Reverted to simple but visible) --- */
[data-modern-theme="{normalized_key}"] .widget,
[data-modern-theme="{normalized_key}"] .card.widget,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box {{
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
  transition: all 0.3s ease !important;
}}

[data-modern-theme="{normalized_key}"] .widget:hover,
[data-modern-theme="{normalized_key}"] .card.widget:hover,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box:hover {{
  border-color: var(--ct-accent) !important;
  border-width: 2px !important;
  box-shadow: 0 8px 24px rgba(76, 175, 80, 0.3) !important;
  transform: translateY(-4px) !important;
}}
[data-modern-theme="{normalized_key}"] .btn,
[data-modern-theme="{normalized_key}"] .btn-primary,
[data-modern-theme="{normalized_key}"] .btn-secondary,
[data-modern-theme="{normalized_key}"] .btn-default {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 2px solid var(--ct-border) !important;
  border-radius: 6px !important;
  padding: 8px 16px !important;
  font-weight: 500 !important;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
  transition: all 0.2s ease !important;
  cursor: pointer !important;
}}

[data-modern-theme="{normalized_key}"] .btn-primary {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border: 2px solid var(--ct-accent) !important;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.4) !important;
}}

[data-modern-theme="{normalized_key}"] .btn:hover,
[data-modern-theme="{normalized_key}"] .btn-secondary:hover,
[data-modern-theme="{normalized_key}"] .btn-default:hover {{
  background: var(--ct-accent-hover) !important;
  border-color: var(--ct-accent) !important;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3) !important;
  transform: translateY(-1px) !important;
}}

[data-modern-theme="{normalized_key}"] .btn-primary:hover {{
  background: var(--ct-accent-hover) !important;
  color: #ffffff !important;
  box-shadow: 0 4px 16px rgba(76, 175, 80, 0.6) !important;
  transform: translateY(-1px) !important;
}}

/* --- Widget Headers Forced White (Issue #2) --- */
[data-modern-theme="{normalized_key}"] .widget .widget-title,
[data-modern-theme="{normalized_key}"] .widget-group .widget-group-title,
[data-modern-theme="{normalized_key}"] .widget-shortcut-title,
[data-modern-theme="{normalized_key}"] .section-head,
[data-modern-theme="{normalized_key}"] .widget-head h4,
[data-modern-theme="{normalized_key}"] .widget-head h5,
[data-modern-theme="{normalized_key}"] .widget-group-head h4,
[data-modern-theme="{normalized_key}"] .widget-group-head h5 {{
  color: #ffffff !important;
  text-shadow: none !important;
}}

/* --- Group Titles Fix (Issue #4) --- */
[data-modern-theme="{normalized_key}"] .widget-group,
[data-modern-theme="{normalized_key}"] .widget-group .section-head,
[data-modern-theme="{normalized_key}"] .widget-group-title,
[data-modern-theme="{normalized_key}"] .widget-group .head,
[data-modern-theme="{normalized_key}"] [class*="group-title"],
[data-modern-theme="{normalized_key}"] .reports-section,
[data-modern-theme="{normalized_key}"] .section-title {{
  color: #ffffff !important;
  font-weight: 600 !important;
}}

[data-modern-theme="{normalized_key}"] .widget-group .text-muted,
[data-modern-theme="{normalized_key}"] .widget-group .text-dark,
[data-modern-theme="{normalized_key}"] .widget-group .text-secondary {{
  color: var(--ct-text-muted) !important;
}}

/* --- Animated Gradient Border (Issue #3) --- */
[data-modern-theme="{normalized_key}"] .widget,
[data-modern-theme="{normalized_key}"] .card.widget,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box {{
  position: relative !important;
  border: 2px solid transparent !important;
  background: var(--ct-surface) !important;
  background-clip: padding-box !important;
  transition: transform 0.3s ease, box-shadow 0.3s ease !important;
}}

[data-modern-theme="{normalized_key}"] .widget::before,
[data-modern-theme="{normalized_key}"] .card.widget::before,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box::before {{
  content: "" !important;
  position: absolute !important;
  top: -2px !important;
  left: -2px !important;
  right: -2px !important;
  bottom: -2px !important;
  background: linear-gradient(45deg, var(--ct-accent), var(--ct-accent-hover), var(--ct-accent)) !important;
  background-size: 200% 200% !important;
  border-radius: 6px !important;
  z-index: -1 !important;
  opacity: 0 !important;
  transition: opacity 0.3s ease !important;
  animation: none !important;
}}

[data-modern-theme="{normalized_key}"] .widget:hover::before,
[data-modern-theme="{normalized_key}"] .card.widget:hover::before,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box:hover::before {{
  opacity: 1 !important;
  animation: gradientRotate 3s linear infinite !important;
}}

[data-modern-theme="{normalized_key}"] .widget:hover,
[data-modern-theme="{normalized_key}"] .card.widget:hover,
[data-modern-theme="{normalized_key}"] .shortcut-widget-box:hover {{
  transform: translateY(-4px) !important;
  box-shadow: 0 12px 24px rgba(76, 175, 80, 0.3) !important;
}}

@keyframes gradientRotate {{
  0% {{ background-position: 0% 50%; }}
  50% {{ background-position: 100% 50%; }}
  100% {{ background-position: 0% 50%; }}
}}

/* --- Card Hover Effects with Border (Issue #5) --- */
[data-modern-theme="{normalized_key}"] .widget,
[data-modern-theme="{normalized_key}"] .widget.shortcut-widget-box,
[data-modern-theme="{normalized_key}"] .card.widget {{
  transition: all 0.3s ease !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .widget:hover,
[data-modern-theme="{normalized_key}"] .widget.shortcut-widget-box:hover,
[data-modern-theme="{normalized_key}"] .card.widget:hover {{
  transform: translateY(-4px) !important;
  border-color: var(--ct-accent) !important;
  box-shadow: 0 8px 24px rgba(76, 175, 80, 0.2) !important;
  background: var(--ct-surface) !important;
}}

[data-modern-theme="{normalized_key}"] .widget-group .widget:hover {{
  border-left: 3px solid var(--ct-accent) !important;
}}

/* --- Modals - comprehensive --- */
[data-modern-theme="{normalized_key}"] .modal-content {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
}}

[data-modern-theme="{normalized_key}"] .modal-header {{
  background: var(--ct-surface) !important;
  border-bottom: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .modal-footer {{
  background: var(--ct-surface) !important;
  border-top: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .modal-body {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .modal-title {{
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .close,
[data-modern-theme="{normalized_key}"] .modal-header .close {{
  color: var(--ct-text-muted) !important;
  text-shadow: none !important;
}}

[data-modern-theme="{normalized_key}"] .close:hover {{
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .modal-backdrop {{
  background: rgba(0,0,0,0.8) !important;
}}

/* --- Tooltips & Popovers --- */
[data-modern-theme="{normalized_key}"] .tooltip-inner {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}}

[data-modern-theme="{normalized_key}"] .popover {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
}}

[data-modern-theme="{normalized_key}"] .popover-header {{
  background: var(--ct-surface) !important;
  border-bottom: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .popover-body {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .bs-popover-auto[data-popper-placement^="top"] > .popover-arrow::after,
[data-modern-theme="{normalized_key}"] .bs-popover-top > .popover-arrow::after {{
  border-top-color: var(--ct-surface) !important;
}}

/* --- Kanban & Calendar Views --- */
[data-modern-theme="{normalized_key}"] .kanban-board {{
  background: var(--ct-body-bg) !important;
}}

[data-modern-theme="{normalized_key}"] .kanban-column {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .kanban-card {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .kanban-card:hover {{
  background: var(--ct-accent-hover) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}}

[data-modern-theme="{normalized_key}"] .fc-day {{
  background: var(--ct-surface) !important;
}}

[data-modern-theme="{normalized_key}"] .fc-day-today {{
  background: var(--ct-accent-hover) !important;
}}

[data-modern-theme="{normalized_key}"] .fc-event {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border: none !important;
}}

[data-modern-theme="{normalized_key}"] .fc-toolbar-title {{
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .fc-button {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .fc-button:hover {{
  background: var(--ct-accent-hover) !important;
}}

/* --- Animations & Transitions --- */
[data-modern-theme="{normalized_key}"] .btn,
[data-modern-theme="{normalized_key}"] .btn-primary,
[data-modern-theme="{normalized_key}"] .form-control,
[data-modern-theme="{normalized_key}"] .card,
[data-modern-theme="{normalized_key}"] .widget,
[data-modern-theme="{normalized_key}"] .kanban-card,
[data-modern-theme="{normalized_key}"] .list-row {{
  transition: all 0.2s ease-in-out !important;
}}

[data-modern-theme="{normalized_key}"] .widget:hover,
[data-modern-theme="{normalized_key}"] .card:hover {{
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3) !important;
}}

[data-modern-theme="{normalized_key}"] .btn:hover {{
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
}}

[data-modern-theme="{normalized_key}"] .btn:active {{
  transform: translateY(0) !important;
  box-shadow: none !important;
}}

[data-modern-theme="{normalized_key}"] .sidebar-item,
[data-modern-theme="{normalized_key}"] .standard-sidebar-item {{
  transition: background 0.15s ease !important;
}}

/* --- Toast & Notification --- */
[data-modern-theme="{normalized_key}"] .toast {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}}

[data-modern-theme="{normalized_key}"] .toast-header {{
  background: var(--ct-surface) !important;
  border-bottom: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .alert {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-modern-theme="{normalized_key}"] .alert-primary {{
  border-left: 4px solid var(--ct-accent) !important;
}}

/* --- Tabs & Navigation --- */
[data-modern-theme="{normalized_key}"] .nav-tabs {{
  border-bottom: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .nav-tabs .nav-link {{
  color: var(--ct-text-muted) !important;
  border: none !important;
}}

[data-modern-theme="{normalized_key}"] .nav-tabs .nav-link:hover {{
  color: var(--ct-text-primary) !important;
  background: var(--ct-accent-hover) !important;
}}

[data-modern-theme="{normalized_key}"] .nav-tabs .nav-link.active {{
  color: var(--ct-text-primary) !important;
  background: var(--ct-surface) !important;
  border-bottom: 2px solid var(--ct-accent) !important;
}}

[data-modern-theme="{normalized_key}"] .nav-pills .nav-link {{
  color: var(--ct-text-muted) !important;
}}

[data-modern-theme="{normalized_key}"] .nav-pills .nav-link.active {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
}}

/* --- Pagination --- */
[data-modern-theme="{normalized_key}"] .pagination .page-link {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-modern-theme="{normalized_key}"] .pagination .page-link:hover {{
  background: var(--ct-accent-hover) !important;
}}

[data-modern-theme="{normalized_key}"] .pagination .page-item.active .page-link {{
  background: var(--ct-accent) !important;
  border-color: var(--ct-accent) !important;
  color: #ffffff !important;
}}

/* --- AGGRESSIVE Table Row Hover Fix --- */
[data-modern-theme="{normalized_key}"] .table tbody tr:hover,
[data-modern-theme="{normalized_key}"] .list-row:hover,
[data-modern-theme="{normalized_key}"] .data-row:hover,
[data-modern-theme="{normalized_key}"] .grid-row:hover {{
  background: var(--ct-accent-hover) !important;
}}

[data-modern-theme="{normalized_key}"] .table tbody tr:hover td,
[data-modern-theme="{normalized_key}"] .table tbody tr:hover a,
[data-modern-theme="{normalized_key}"] .table tbody tr:hover span,
[data-modern-theme="{normalized_key}"] .list-row:hover .list-row-col,
[data-modern-theme="{normalized_key}"] .list-row:hover a,
[data-modern-theme="{normalized_key}"] .list-row:hover span,
[data-modern-theme="{normalized_key}"] .data-row:hover .data-row-col,
[data-modern-theme="{normalized_key}"] .data-row:hover a,
[data-modern-theme="{normalized_key}"] .grid-row:hover td,
[data-modern-theme="{normalized_key}"] .grid-row:hover a {{
  color: #ffffff !important;
}}

/* --- AGGRESSIVE Dropdown Backdrop --- */
[data-modern-theme="{normalized_key}"] .dropdown-backdrop,
[data-modern-theme="{normalized_key}"] .modal-backdrop.show,
[data-modern-theme="{normalized_key}"] .open > .dropdown-backdrop {{
  background: rgba(0,0,0,0.7) !important;
  z-index: 9990 !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
}}

/* --- AGGRESSIVE Menu Button Fix (Three dots menu) --- */
[data-modern-theme="{normalized_key}"] .menu-btn,
[data-modern-theme="{normalized_key}"] .menu-btn-group > .btn,
[data-modern-theme="{normalized_key}"] .dropdown-toggle,
[data-modern-theme="{normalized_key}"] .btn.menu-btn {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border: none !important;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
}}

[data-modern-theme="{normalized_key}"] .menu-btn:hover,
[data-modern-theme="{normalized_key}"] .dropdown-toggle:hover {{
  background: var(--ct-accent-hover) !important;
  color: #ffffff !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 8px rgba(0,0,0,0.4) !important;
}}

/* --- Progress & Loading --- */
[data-modern-theme="{normalized_key}"] .progress {{
  background: var(--ct-surface) !important;
}}

[data-modern-theme="{normalized_key}"] .progress-bar {{
  background: var(--ct-accent) !important;
}}

[data-modern-theme="{normalized_key}"] .spinner-border {{
  color: var(--ct-accent) !important;
}}

[data-modern-theme="{normalized_key}"] .loading-spinner {{
  color: var(--ct-accent) !important;
}}
"""
	
	return template


def _resolve_frontend_theme_to_doc(theme_key, mode):
	"""
	Resolve frontend theme key to Construction Theme DocType name.
	
	Resolution priority:
	1. 'light' / 'construction_light' -> Construction Light (is_default_light=1)
	2. 'dark' / 'construction_dark'    -> Construction Dark (is_default_dark=1)
	3. Custom theme name               -> exact name match (is_active=1)
	4. No match                        -> None (fallback to Frappe native)
	"""
	if not theme_key:
		return None
	
	key_lower = theme_key.lower().replace(" ", "_")
	
	# Map all light variants to the default light Construction theme
	if key_lower in ("light", "construction_light"):
		default_light = frappe.db.get_value(
			"Construction Theme",
			{"is_system_theme": 1, "is_default_light": 1, "is_active": 1},
			"name"
		)
		if default_light:
			return default_light
		# Fallback: find any active Construction Light
		return frappe.db.get_value(
			"Construction Theme",
			{"name": "Construction Light", "is_active": 1},
			"name"
		)
	
	# Map all dark variants to the default dark Construction theme
	if key_lower in ("dark", "construction_dark"):
		default_dark = frappe.db.get_value(
			"Construction Theme",
			{"is_system_theme": 1, "is_default_dark": 1, "is_active": 1},
			"name"
		)
		if default_dark:
			return default_dark
		# Fallback: find any active Construction Dark
		return frappe.db.get_value(
			"Construction Theme",
			{"name": "Construction Dark", "is_active": 1},
			"name"
		)
	
	# Custom themes: exact name match (case-insensitive)
	existing = frappe.db.get_value(
		"Construction Theme",
		{"name": theme_key, "is_active": 1},
		"name"
	)
	if existing:
		return existing
	
	# Try case-insensitive match for custom themes
	all_active = frappe.get_all(
		"Construction Theme",
		filters={"is_active": 1},
		fields=["name"]
	)
	for t in all_active:
		if t.name.lower() == key_lower:
			return t.name
	
	return None


@frappe.whitelist()
def set_user_theme(theme, mode):
	"""
	Set user theme preference

	Args:
	    theme: str - Theme name (frontend key or DocType name)
	    mode: str - "light" or "dark"

	Returns:
	    dict: Success status
	"""
	try:
		user = frappe.session.user

		# Resolve frontend key to DocType name
		theme_doc = _resolve_frontend_theme_to_doc(theme, mode)
		
		# If no theme_doc, it's a basic theme (light/dark) - just save mode
		if not theme_doc:
			# Update User.desk_theme for mode
			desk_theme_value = "Dark" if mode == "dark" else "Light"
			frappe.db.set_value("User", user, "desk_theme", desk_theme_value, update_modified=False)
			
			# CRITICAL: Set User Desk Theme to inherit from site so it doesn't override
			# When user selects basic theme, we don't want User Desk Theme to provide construction themes
			user_theme_name = frappe.db.get_value("User Desk Theme", {"user": user}, "name")
			if user_theme_name:
				frappe.db.set_value("User Desk Theme", user_theme_name, "inherit_from_site", 1)
				frappe.db.set_value("User Desk Theme", user_theme_name, "light_theme", None)
				frappe.db.set_value("User Desk Theme", user_theme_name, "dark_theme", None)
			
			frappe.db.commit()
			return {"success": True, "message": f"Mode saved: {mode}", "basic_theme": True}

		# Get or create User Desk Theme
		user_theme_name = frappe.db.get_value("User Desk Theme", {"user": user}, "name")

		if user_theme_name:
			user_theme = frappe.get_doc("User Desk Theme", user_theme_name)
		else:
			user_theme = frappe.new_doc("User Desk Theme")
			user_theme.user = user

		# Set theme based on mode (using actual DocType name)
		if mode == "light":
			user_theme.light_theme = theme_doc
			user_theme.dark_theme = None  # Clear opposite mode
		else:
			user_theme.dark_theme = theme_doc
			user_theme.light_theme = None  # Clear opposite mode

		user_theme.inherit_from_site = 0  # User has custom theme, don't inherit
		user_theme.save(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True, "message": "Theme preference saved", "theme_doc": theme_doc}

	except Exception as e:
		# Log short error message to avoid truncation
		error_msg = str(e)[:100] if len(str(e)) > 100 else str(e)
		frappe.log_error(f"Theme save error: {error_msg}")
		return {"success": False, "message": error_msg}


@frappe.whitelist()
def list_available_themes():
	"""
	List all available Construction Themes for the ThemeSwitcher dropdown.
	Uses SQL to bypass Python controller import issues.

	Returns:
	    dict: { success: bool, themes: list }
	"""
	try:
		# Get limit from settings (default 12)
		limit = 12
		try:
			# Check if Modern Theme Settings table exists
			table_exists = frappe.db.sql("""
				SELECT COUNT(*) FROM information_schema.tables
				WHERE table_schema = DATABASE()
				AND table_name = 'tabModern Theme Settings'
			""")[0][0]

			if table_exists:
				limit_result = frappe.db.sql("""
					SELECT theme_switcher_limit FROM `tabModern Theme Settings`
					LIMIT 1
				""")
				if limit_result and limit_result[0][0]:
					limit = limit_result[0][0]
		except Exception as e:
			frappe.logger().debug(f"Could not get theme_switcher_limit: {e}")
			limit = 12

		# Query themes via SQL
		themes_data = frappe.db.sql(
			"""
			SELECT
				name, theme_name, emoji_icon, theme_type,
				is_system_theme, preview_colors,
				is_default_light, is_default_dark, description
			FROM `tabConstruction Theme`
			WHERE is_active = 1
			ORDER BY is_system_theme DESC, theme_name ASC
			LIMIT %s
		""",
			(limit,),
			as_dict=True,
		)

		# Format themes for ThemeSwitcher
		import json

		themes = []
		for t in themes_data:
			theme = {
				"name": t.theme_name,
				"label": f"{t.emoji_icon or "🎨"} {t.theme_name}",
				"info": t.description or t.theme_type,
				"is_construction": True,
				"theme_doc": t.name,
				"is_system": t.is_system_theme,
				"is_default_light": t.is_default_light,
				"is_default_dark": t.is_default_dark,
				"preview_colors": [],
			}

			# Parse preview_colors JSON
			if t.preview_colors:
				try:
					theme["preview_colors"] = json.loads(t.preview_colors)
				except:
					theme["preview_colors"] = []

			themes.append(theme)

		return {"success": True, "themes": themes}

	except Exception as e:
		frappe.logger().error(f"Error listing themes: {str(e)}")
		return {"success": False, "themes": [], "message": str(e)}


@frappe.whitelist()
def get_theme_css(theme_name):
	"""
	Returns generated CSS for a theme (server-side cached).
	Uses generate_css_variables() method to produce CSS variable block.

	Args:
	    theme_name: str - Name of the Construction Theme (or frontend key like 'construction_light')

	Returns:
	    dict: { css: str, theme_name: str, cached: bool, version: str }
	"""
	try:
		if not theme_name:
			return {
				"css": "",
				"theme_name": "",
				"cached": False,
				"version": "2",
				"error": "Theme name is required",
			}

		# Resolve frontend theme keys to actual Construction Theme DocType names
		# This handles 'light', 'dark', 'construction_light', 'construction_dark' and custom names
		theme_name_normalized = theme_name.lower().replace(" ", "_")
		actual_theme_name = theme_name

		if theme_name_normalized in ("light", "dark", "construction_light", "construction_dark"):
			# Use _resolve_frontend_theme_to_doc for consistent resolution
			mode = "dark" if theme_name_normalized in ("dark", "construction_dark") else "light"
			resolved = _resolve_frontend_theme_to_doc(theme_name, mode)
			if resolved:
				actual_theme_name = resolved
			else:
				# Theme DocType doesn't exist - generate hardcoded CSS with full template
				css = _get_theme_css_template(theme_name, theme_name_normalized)
				return {
					"css": css,
					"theme_name": theme_name,
					"cached": False,
					"version": "2",
					"hardcoded": True,
					"message": f"Theme {theme_name} uses hardcoded CSS ({len(css)} bytes)",
				}

		# Check cache first
		cache_key = f"construction_theme_css:{actual_theme_name}"
		cached_css = frappe.cache().get_value(cache_key)

		if cached_css:
			return {
				"css": cached_css,
				"theme_name": actual_theme_name,
				"cached": True,
				"version": "2",
				"generated_at": None,
			}

		# Get theme document
		theme_doc = frappe.get_doc("Construction Theme", actual_theme_name)

		# Generate CSS using generate_css_variables()
		css = theme_doc.generate_css_variables()

		# Add comprehensive CSS template that applies the variables to override Frappe styles
		css += _get_theme_css_template(actual_theme_name, theme_name_normalized)

		# Append custom_css if present (from the DocType's custom_css field)
		if hasattr(theme_doc, 'custom_css') and theme_doc.custom_css:
			css += "\n/* ===== CUSTOM CSS ===== */\n" + theme_doc.custom_css

		# Build feature toggles dict
		feature_toggles = {}
		for field in ["hide_help_button", "hide_search_bar", "hide_sidebar", "hide_like_comment", "mobile_card_view"]:
			if hasattr(theme_doc, field):
				feature_toggles[field] = theme_doc.get(field, 0)

		# Cache the result
		frappe.cache().set_value(cache_key, css, expires_in_sec=3600)

		return {
			"css": css,
			"theme_name": actual_theme_name,
			"cached": False,
			"version": "2",
			"generated_at": frappe.utils.now(),
			"feature_toggles": feature_toggles,
		}

	except Exception as e:
		frappe.logger().error(f"Error getting theme CSS for {theme_name}: {str(e)}")
		return {"css": "", "theme_name": theme_name, "cached": False, "version": "2", "error": str(e)}


def generate_css_sql(theme):
	"""Generate CSS directly without using Python controller."""
	is_dark = "Dark" in (theme.theme_type or "")

	# Helper: darken hex color
	def darken_hex(hex_color, factor=0.1):
		if not hex_color or not hex_color.startswith("#"):
			return hex_color
		hex_color = hex_color.lstrip("#")
		if len(hex_color) == 3:
			hex_color = "".join([c * 2 for c in hex_color])
		r = int(hex_color[0:2], 16)
		g = int(hex_color[2:4], 16)
		b = int(hex_color[4:6], 16)
		r = int(r * (1 - factor))
		g = int(g * (1 - factor))
		b = int(b * (1 - factor))
		return f"#{r:02x}{g:02x}{b:02x}"

	# Get values with defaults
	accent = theme.accent_primary or "#2076FF"
	accent_hover = theme.accent_primary_hover or darken_hex(accent, 0.1)
	navbar = theme.navbar_bg or ("#111827" if is_dark else "#f8fafc")
	sidebar = theme.sidebar_bg or ("#1f2937" if is_dark else "#f1f5f9")
	surface = theme.surface_bg or ("#1f2937" if is_dark else "#ffffff")
	body = theme.body_bg or ("#111827" if is_dark else "#f8fafc")
	text = theme.text_primary or ("#f9fafb" if is_dark else "#111827")
	text_secondary = theme.text_secondary or ("#9ca3af" if is_dark else "#6b7280")
	border = theme.border_color or (accent + "33")

	css_parts = []

	# Base CSS variables
	css_parts.append(f"""/* ===== BASE: {theme.theme_name} ===== */
html[data-modern-theme="{theme.theme_name}"] {{
  --navbar-bg: {navbar};
  --sidebar-bg: {sidebar};
  --surface-bg: {surface};
  --body-bg: {body};
  --text-primary: {text};
  --text-secondary: {text_secondary};
  --accent-primary: {accent};
  --accent-primary-hover: {accent_hover};
  --border-color: {border};
}}""")

	# Navbar
	css_parts.append(f"""/* ===== NAVBAR ===== */
html[data-modern-theme="{theme.theme_name}"] .navbar {{
	background: {navbar} !important;
	border-bottom: 2px solid {accent} !important;
	{"box-shadow: 0 2px 8px rgba(0,0,0,.3) !important;" if is_dark else "box-shadow: 0 2px 4px rgba(0,0,0,.1) !important;"}
}}

html[data-modern-theme="{theme.theme_name}"] .navbar .nav-link {{
	color: {text} !important;
}}

html[data-modern-theme="{theme.theme_name}"] .navbar .nav-link:hover {{
	color: {accent} !important;
	background: {accent}19 !important;
	border-radius: 8px !important;
}}""")

	# Sidebar
	css_parts.append(f"""/* ===== SIDEBAR ===== */
html[data-modern-theme="{theme.theme_name}"] .layout-side-section {{
	background: {sidebar} !important;
	border-right: 1px solid {border} !important;
}}

html[data-modern-theme="{theme.theme_name}"] .desk-sidebar .standard-sidebar-item a {{
	color: {text} !important;
}}

html[data-modern-theme="{theme.theme_name}"] .desk-sidebar .standard-sidebar-item.selected a {{
	background: {accent}33 !important;
	color: {accent} !important;
	box-shadow: inset 3px 0 0 {accent} !important;
}}

html[data-modern-theme="{theme.theme_name}"] .desk-sidebar .standard-sidebar-item a:hover {{
	color: {accent} !important;
	background: {accent}19 !important;
}}""")

	# Buttons
	css_parts.append(f"""/* ===== BUTTONS ===== */
html[data-modern-theme="{theme.theme_name}"] .btn-primary {{
	background: {accent} !important;
	border-color: {accent} !important;
	color: #fff !important;
	border-radius: 10px !important;
}}

html[data-modern-theme="{theme.theme_name}"] .btn-primary:hover {{
	background: {accent_hover} !important;
	border-color: {accent_hover} !important;
	transform: translateY(-1px) !important;
}}

html[data-modern-theme="{theme.theme_name}"] .btn-default {{
	background: {surface} !important;
	border: 1px solid {border} !important;
	color: {text} !important;
	border-radius: 10px !important;
}}

html[data-modern-theme="{theme.theme_name}"] .btn-default:hover {{
	background: {accent}19 !important;
	border-color: {accent} !important;
	color: {accent} !important;
}}""")

	# Forms
	css_parts.append(f"""/* ===== FORMS ===== */
html[data-modern-theme="{theme.theme_name}"] .form-control {{
	background: {surface} !important;
	border-color: {border} !important;
	color: {text} !important;
	border-radius: 8px !important;
}}

html[data-modern-theme="{theme.theme_name}"] .form-control:focus {{
	border-color: {accent} !important;
	box-shadow: 0 0 0 3px {accent}26 !important;
}}

html[data-modern-theme="{theme.theme_name}"] a {{
	color: {accent} !important;
}}

html[data-modern-theme="{theme.theme_name}"] h1,
html[data-modern-theme="{theme.theme_name}"] h2,
html[data-modern-theme="{theme.theme_name}"] h3 {{
	color: {text} !important;
}}""")

	# Add custom CSS if present
	if theme.custom_css:
		css_parts.append(f"/* ===== CUSTOM CSS ===== */\n{theme.custom_css}")

	return "\n".join(css_parts)


@frappe.whitelist()
def preview_theme(theme_name=None, temporary=False, **color_fields):
	"""
	Generates CSS for preview without saving to user profile.
	Used by the "Preview" button on theme settings form.

	Args:
	    theme_name: str - Existing theme to preview (optional if temporary)
	    temporary: bool - If True, use color_fields instead of DB
	    **color_fields: dict - Color values for temporary preview

	Returns:
	    dict: Same as get_theme_css()
	"""
	try:
		if temporary and color_fields:
			# Create temporary theme document (don't save)
			theme_doc = frappe.new_doc("Construction Theme")
			for key, value in color_fields.items():
				if hasattr(theme_doc, key):
					setattr(theme_doc, key, value)

			# Set defaults for required fields
			theme_doc.theme_name = "_Preview"
			theme_doc.theme_type = "Custom Light"

			# Auto-calculate derived colors
			theme_doc._auto_calculate_derived_colors()

			css = theme_doc.generate_css()

			return {"css": css, "theme_name": "_Preview", "cached": False, "version": "1", "temporary": True}

		elif theme_name:
			# Use existing theme
			return get_theme_css(theme_name)

		else:
			return {"css": "", "error": "Either theme_name or temporary=True with color_fields required"}

	except Exception as e:
		frappe.log_error(f"Error previewing theme: {str(e)}")
		return {"css": "", "error": str(e)}


@frappe.whitelist()
def get_user_construction_theme():
	"""
	Get the user's saved construction theme preference (for server-side persistence).
	Replaces localStorage dependency.

	Returns:
	    dict: { theme_name: str, mode: str, source: str } or None
	"""
	try:
		user = frappe.session.user

		# Check User Desk Theme
		user_theme = frappe.db.get_value(
			"User Desk Theme",
			{"user": user},
			["light_theme", "dark_theme", "inherit_from_site"],
			as_dict=True,
		)

		if not user_theme or user_theme.inherit_from_site:
			return None

		# Get current mode from User doc
		desk_theme = frappe.db.get_value("User", user, "desk_theme") or "Light"
		mode = "dark" if desk_theme == "Dark" else "light"

		# Get theme for current mode
		theme_name = user_theme.dark_theme if mode == "dark" else user_theme.light_theme

		if theme_name:
			return {"theme_name": theme_name, "mode": mode, "source": "user_desk_theme"}

		return None

	except Exception as e:
		frappe.log_error(f"Error getting user construction theme: {str(e)}")
		return None


def _get_frontend_theme_key(theme_doc_name, mode):
	"""
	Convert a Construction Theme DocType name to a frontend theme key.
	
	Args:
	    theme_doc_name: Name of the Construction Theme DocType
	    mode: 'light' or 'dark'
	
	Returns:
	    Frontend key like 'light', 'dark', 'construction_light', 'construction_dark'
	"""
	if not theme_doc_name:
		return mode

	# Check if it's a system/hardcoded theme
	is_system = frappe.db.get_value("Construction Theme", theme_doc_name, "is_system_theme")

	if is_system:
		# System themes map to construction_light/construction_dark
		return f"construction_{mode}"

	# For custom themes, return the actual DocType name
	# The frontend will handle it as a custom construction theme
	return theme_doc_name


@frappe.whitelist(allow_guest=True)
def get_user_theme_for_boot():
	"""
	Get the user's theme for boot injection.
	Called during frappe.boot to determine the initial theme for the user.

	Single Source of Truth: For logged-in users, master is User Desk Theme + User.desk_theme
	For guests, master is Modern Theme Settings (site default).

	Returns:
	    dict: {
	        theme: str,        # Frontend key (light/dark/construction_light/construction_dark/custom_name)
	        mode: str,         # 'light' or 'dark'
	        source: str,       # Where the value came from
	        css_url: str       # Optional CSS URL for dynamic themes
	    }
	"""
	try:
		user = frappe.session.user

		# Guest user - use site defaults
		if user == "Guest":
			site_settings = frappe.db.get_value(
				"Modern Theme Settings",
				{"name": "Modern Theme Settings"},
				["default_light_theme", "default_dark_theme", "allow_user_override"],
				as_dict=True,
			)

			if site_settings:
				# Check if default is a system theme or custom
				theme_doc = site_settings.default_light_theme or "light"
				if theme_doc and frappe.db.exists("Construction Theme", theme_doc):
					theme = _get_frontend_theme_key(theme_doc, "light")
				else:
					theme = "light"
				mode = "light"
				return {
					"theme": theme,
					"mode": mode,
					"source": "site_default_guest",
				}

			return {"theme": "light", "mode": "light", "source": "hardcoded_guest"}

		# Logged-in user - check User Desk Theme first (master source)
		user_theme = frappe.db.get_value(
			"User Desk Theme",
			{"user": user},
			["light_theme", "dark_theme", "inherit_from_site"],
			as_dict=True,
		)

		# Get user's mode preference from User.desk_theme
		desk_theme = frappe.db.get_value("User", user, "desk_theme") or "Light"
		mode = "dark" if desk_theme == "Dark" else "light"

		# If user has custom theme settings and not inheriting from site
		if user_theme and not user_theme.inherit_from_site:
			theme_doc = user_theme.dark_theme if mode == "dark" else user_theme.light_theme
			if theme_doc:
				# Convert DocType name to frontend key
				frontend_key = _get_frontend_theme_key(theme_doc, mode)
				return {
					"theme": frontend_key,
					"mode": mode,
					"source": "user_desk_theme",
					"doc_name": theme_doc,  # Original DocType name for reference
				}

		# User inherits from site or no custom theme set - check site defaults
		site_settings = frappe.db.get_value(
			"Modern Theme Settings",
			{"name": "Modern Theme Settings"},
			["default_light_theme", "default_dark_theme"],
			as_dict=True,
		)

		if site_settings:
			theme_doc = (
				site_settings.default_dark_theme
				if mode == "dark"
				else site_settings.default_light_theme
			)
			if theme_doc:
				frontend_key = _get_frontend_theme_key(theme_doc, mode)
				return {"theme": frontend_key, "mode": mode, "source": "site_default", "doc_name": theme_doc}

		# Fall back to basic light/dark based on mode
		return {"theme": mode, "mode": mode, "source": "mode_fallback"}

	except Exception as e:
		frappe.log_error(f"Error getting theme for boot: {str(e)}")
		return {"theme": "light", "mode": "light", "source": "error_fallback"}


def add_theme_to_boot(bootinfo):
	"""
	Hook function called during frappe.boot to inject theme into bootinfo.
	Added to hooks.py as boot_session = 'construction.api.theme_api.add_theme_to_boot'

	This ensures the theme is available immediately on page load without extra API calls.
	"""
	try:
		theme_data = get_user_theme_for_boot()
		bootinfo.construction_theme = theme_data

		# Also set the standard frappe.boot.theme for compatibility
		bootinfo.theme = theme_data.get("mode", "light")

		frappe.logger().debug(f"[Theme Boot] Injected theme for {frappe.session.user}: {theme_data}")

	except Exception as e:
		frappe.log_error(f"Error adding theme to boot: {str(e)}")
		# Ensure we always have a fallback
		bootinfo.construction_theme = {"theme": "light", "mode": "light", "source": "boot_error"}
		bootinfo.theme = "light"
