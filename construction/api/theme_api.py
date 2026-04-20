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


@frappe.whitelist()
def set_user_theme(theme, mode):
	"""
	Set user theme preference

	Args:
	    theme: str - Theme name
	    mode: str - "light" or "dark"

	Returns:
	    dict: Success status
	"""
	try:
		user = frappe.session.user

		# Get or create User Desk Theme
		user_theme_name = frappe.db.get_value("User Desk Theme", {"user": user}, "name")

		if user_theme_name:
			user_theme = frappe.get_doc("User Desk Theme", user_theme_name)
		else:
			user_theme = frappe.new_doc("User Desk Theme")
			user_theme.user = user

		# Set theme based on mode
		if mode == "light":
			user_theme.light_theme = theme
		else:
			user_theme.dark_theme = theme

		user_theme.inherit_from_site = 0
		user_theme.save(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True, "message": "Theme preference saved"}

	except Exception as e:
		frappe.log_error(f"Error setting user theme: {str(e)}")
		return {"success": False, "message": str(e)}


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
	    theme_name: str - Name of the Construction Theme

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

		# Check cache first
		cache_key = f"construction_theme_css:{theme_name}"
		cached_css = frappe.cache().get_value(cache_key)

		if cached_css:
			return {
				"css": cached_css,
				"theme_name": theme_name,
				"cached": True,
				"version": "2",
				"generated_at": None,
			}

		# Get theme document
		theme_doc = frappe.get_doc("Construction Theme", theme_name)

		# Generate CSS using generate_css_variables()
		css = theme_doc.generate_css_variables()

		# Cache the result
		frappe.cache().set_value(cache_key, css, expires_in_sec=3600)

		return {
			"css": css,
			"theme_name": theme_name,
			"cached": False,
			"version": "2",
			"generated_at": frappe.utils.now(),
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
