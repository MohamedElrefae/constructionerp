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
def get_theme_css_variables(theme_name, version=None):
    """
    Get CSS variables for a specific Construction Theme

    Args:
        theme_name: str - Name of the Construction Theme record (or frontend key like 'construction_light')
        version: str - Optional version flag (e.g. "v16") to include v16-specific dynamic selectors

    Returns:
        dict: {
            "css_variables": str,
            "theme_data": dict
        }
    """
    try:
        # Map frontend keys to actual theme names
        frontend_key_map = {
            "construction_light": "Construction Light",
            "construction_dark": "Construction Dark",
            "light": "Construction Light",
            "dark": "Construction Dark",
        }

        # Resolve frontend key to actual theme name
        actual_theme_name = frontend_key_map.get(theme_name.lower(), theme_name)

        # Try to get by name first, then by theme_name field
        if frappe.db.exists("Construction Theme", actual_theme_name):
            theme = frappe.get_doc("Construction Theme", actual_theme_name)
        else:
            # Try looking up by theme_name field
            theme_name_from_db = frappe.db.get_value(
                "Construction Theme", {"theme_name": actual_theme_name, "is_active": 1}, "name"
            )
            if theme_name_from_db:
                theme = frappe.get_doc("Construction Theme", theme_name_from_db)
            else:
                # Ultimate fallback - create on the fly if system theme
                if actual_theme_name in ("Construction Light", "Construction Dark"):
                    theme = _create_system_theme_on_fly(actual_theme_name)
                else:
                    raise frappe.DoesNotExistError(f"Construction Theme {theme_name} not found")

        css_variables = theme.generate_css_variables()

        # Append v16-specific dynamic selectors when version flag is present
        if version == "v16":
            v16_css = _get_v16_dynamic_css(theme)
            if v16_css:
                css_variables = css_variables + "\n" + v16_css

        return {
            "css_variables": css_variables,
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


def _create_system_theme_on_fly(theme_name):
    """
    Create a system theme on the fly if it doesn't exist in the database.
    This is a fallback for when theme records haven't been created yet.
    """
    is_dark = theme_name == "Construction Dark"

    theme = frappe.new_doc("Construction Theme")
    theme.name = theme_name
    theme.theme_name = theme_name
    theme.theme_type = "Dark" if is_dark else "Light"
    theme.is_system_theme = 1
    theme.is_active = 1

    if is_dark:
        theme.is_default_dark = 1
    else:
        theme.is_default_light = 1

    # Set default colors
    theme.primary_color = "#0ea5e9"
    theme.accent_color = "#f59e0b"
    theme.danger_color = "#dc2626"
    theme.success_color = "#16a34a"

    # Set background colors
    theme.background_color = "#0b1020" if is_dark else "#f8fafc"
    theme.surface_color = "#1e293b" if is_dark else "#ffffff"

    # Set text colors
    theme.text_color = "#f8fafc" if is_dark else "#1e293b"
    theme.secondary_text_color = "#94a3b8" if is_dark else "#64748b"

    # Set border and shadow
    theme.border_color = "rgba(148,163,184,0.18)" if is_dark else "#e5e7eb"

    theme.insert(ignore_if_duplicate=True)
    frappe.db.commit()

    frappe.logger().info(f"[Theme API] Created system theme on the fly: {theme_name}")

    return theme


def _get_v16_dynamic_css(theme):
    """Generate v16-specific dynamic CSS selectors for a Construction Theme.

    These selectors target v16 DOM structures (sidebar-container, form-sidebar,
    dt-scrollable, etc.) and use the theme's --ct-* variables so dynamic
    theme switching works correctly on v16 cloud deployments.

    Returns an empty string if theme has no variables to apply.
    """
    is_dark = "dark" in (theme.theme_type or "").lower() or (theme.body_bg and theme.body_bg.startswith("#1"))
    mode = "dark" if is_dark else "light"
    selector = f'html[data-theme="{mode}"]'

    # Use --ct-* variables that the theme's generate_css_variables() defines
    # These complement the static modern_theme_v16_adapter.css which uses --* tokens
    css_parts = []

    # v16 sidebar container
    css_parts.append(f"""{selector} .sidebar-container {{
  background: var(--ct-sidebar-bg) !important;
  border-right-color: var(--ct-border-color) !important;
}}""")

    # v16 form sidebar (right-aligned)
    css_parts.append(f"""{selector} .form-sidebar {{
  background: var(--ct-sidebar-bg) !important;
  border-left-color: var(--ct-border-color) !important;
}}""")

    # v16 list header
    css_parts.append(f"""{selector} .list-header {{
  color: #fff !important;
}}""")

    # v16 dt-scrollable scrollbar theming
    css_parts.append(f"""{selector} .dt-scrollable {{
  background: var(--ct-body-bg) !important;
}}""")

    # v16 app drawer
    css_parts.append(f"""{selector} .apps-menu {{
  background: var(--ct-sidebar-bg) !important;
  border-color: var(--ct-border-color) !important;
  color: var(--ct-text-primary) !important;
}}""")

    css_parts.append(f"""{selector} .app-icon {{
  color: var(--ct-text-secondary) !important;
}}""")

    css_parts.append(f"""{selector} .app-icon:hover {{
  color: var(--ct-text-primary) !important;
}}""")

    # v16 mask field
    css_parts.append(f"""{selector} .masked-field {{
  background: var(--ct-body-bg) !important;
  border-color: var(--ct-border-color) !important;
  color: var(--ct-text-secondary) !important;
}}""")

    # v16 tag item
    css_parts.append(f"""{selector} .tag-item {{
  background: var(--ct-body-bg) !important;
  border-color: var(--ct-border-color) !important;
  color: var(--ct-text-secondary) !important;
}}""")

    # v16 attachment item
    css_parts.append(f"""{selector} .attachment-item {{
  background: var(--ct-body-bg) !important;
  border-color: var(--ct-border-color) !important;
  color: var(--ct-text-secondary) !important;
}}""")

    # v16 print format container
    css_parts.append(f"""{selector} .print-format-container {{
  background: var(--ct-sidebar-bg) !important;
  border-color: var(--ct-border-color) !important;
  color: var(--ct-text-primary) !important;
}}""")

    return "\n".join(css_parts)


def _get_theme_css_template(theme_name, normalized_key):
    """
    FROZEN - Do not add new logic here.
    This template is being migrated to Jinja2 templates in theme_templates/.
    New styling work should go into Jinja2 templates and/or static CSS bundles.
    Phase A: Missing sections added as new Jinja2 files.
    Phase B: Existing hardcoded blocks migrated from this function.

    Generate comprehensive CSS template that applies Construction theme variables.
    This CSS uses the CSS variables defined in generate_css_variables() to override Frappe styles.
    """
    is_dark = "dark" in normalized_key

    # Base template with CSS that actually applies the variables
    template = f"""
/* ===== CONSTRUCTION THEME CSS TEMPLATE ===== */
/* Theme: {theme_name} | Key: {normalized_key} */

/* --- Root scope with data attribute --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] {{
  /* Apply body background */
  background-color: var(--ct-body-bg) !important;
}}

/* --- Navbar styling --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .navbar,
[data-theme="{ 'dark' if is_dark else 'light' }"] .navbar.navbar-expand,
[data-theme="{ 'dark' if is_dark else 'light' }"] header.navbar {{
  background: var(--ct-navbar-bg) !important;
  border-bottom: 1px solid var(--ct-border-color) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .navbar .nav-link,
[data-theme="{ 'dark' if is_dark else 'light' }"] .navbar .navbar-brand {{
  color: var(--ct-text-primary) !important;
}}

/* --- Sidebar styling --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section,
[data-theme="{ 'dark' if is_dark else 'light' }"] .sidebar,
[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar,
[data-theme="{ 'dark' if is_dark else 'light' }"] .form-sidebar {{
  background: var(--ct-sidebar-bg) !important;
  border-right: 1px solid var(--ct-border-color) !important;
}}

/* --- Sidebar items (comprehensive Frappe v16 selectors) --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section .sidebar-item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar .sidebar-item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .standard-sidebar-item a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .sidebar-item-container a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar .standard-sidebar-item a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section .item-anchor,
[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar .item-anchor,
[data-theme="{ 'dark' if is_dark else 'light' }"] .sidebar .item-anchor {{
  color: var(--ct-text-primary) !important;
  text-decoration: none !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section .sidebar-item:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar .sidebar-item:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .standard-sidebar-item:hover a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .sidebar-item-container:hover a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar .standard-sidebar-item:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section .item-anchor:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar .item-anchor:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .sidebar .item-anchor:hover {{
  background: var(--ct-accent-hover) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Active/selected sidebar item --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .standard-sidebar-item.selected a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .sidebar-item-container.selected a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .standard-sidebar-item.selected .item-anchor,
[data-theme="{ 'dark' if is_dark else 'light' }"] .sidebar-item.selected .item-anchor,
[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section .selected .item-anchor {{
  color: var(--ct-text-primary) !important;
  font-weight: 600 !important;
}}

/* --- Force sidebar background for Frappe v16 --- */
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar,
html[data-theme="{ 'dark' if is_dark else 'light' }"] [data-theme="light"] .layout-side-section,
html[data-theme="{ 'dark' if is_dark else 'light' }"] [data-theme="light"] .desk-sidebar {{
  background: var(--ct-sidebar-bg) !important;
}}

/* AGGRESSIVE: Force ALL text in sidebar to be light */
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section *,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar *,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section .sidebar-item *,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar .sidebar-item * {{
  color: var(--ct-text-primary) !important;
}}

/* AGGRESSIVE: Force all links in sidebar */
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section a,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar a,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section a:link,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar a:link,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section a:visited,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar a:visited {{
  color: var(--ct-text-primary) !important;
}}

/* --- Main content area (comprehensive Frappe v16 selectors) --- */
html[data-theme="{ 'dark' if is_dark else 'light' }"] body,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-main-section,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .content,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .page-wrapper,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .page-container,
html[data-theme="{ 'dark' if is_dark else 'light' }"] #page-container,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-main,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .content.page-container {{
  background: var(--ct-body-bg) !important;
}}

/* --- Cards, widgets, and tree views --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .card,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget,
[data-theme="{ 'dark' if is_dark else 'light' }"] .section-head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .form-section,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dialog,
[data-theme="{ 'dark' if is_dark else 'light' }"] .tree-node,
[data-theme="{ 'dark' if is_dark else 'light' }"] .tree-children,
[data-theme="{ 'dark' if is_dark else 'light' }"] .tree-node-content,
[data-theme="{ 'dark' if is_dark else 'light' }"] .treemap-node,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row,
[data-theme="{ 'dark' if is_dark else 'light' }"] .grid-row {{
  background: var(--ct-surface-bg) !important;
  border-color: var(--ct-border-color) !important;
}}

/* --- Widget headers and shortcut pills --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .ellipsis,
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box,
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box .widget-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box .link-text,
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box .badge,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-label,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-subtitle,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-control {{
  color: var(--ct-text-primary) !important;
}}

/* --- Sidebar icons and emojis --- */
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section .sidebar-item-icon,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar .sidebar-item-icon,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section .icon,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar .icon,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section svg,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar svg,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .layout-side-section use,
html[data-theme="{ 'dark' if is_dark else 'light' }"] .desk-sidebar use {{
  fill: var(--ct-text-primary) !important;
  color: var(--ct-text-primary) !important;
  stroke: var(--ct-text-primary) !important;
}}

/* --- Charts and graph labels --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .chart-container text,
[data-theme="{ 'dark' if is_dark else 'light' }"] .chart-label,
[data-theme="{ 'dark' if is_dark else 'light' }"] .axis-label,
[data-theme="{ 'dark' if is_dark else 'light' }"] .chart-legend,
[data-theme="{ 'dark' if is_dark else 'light' }"] .graph-svg-tip,
[data-theme="{ 'dark' if is_dark else 'light' }"] .bar-chart text,
[data-theme="{ 'dark' if is_dark else 'light' }"] .bar-chart .chart-label,
[data-theme="{ 'dark' if is_dark else 'light' }"] .chart-container .dataset-label {{
  fill: var(--ct-text-primary) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Shortcut pills background fix --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box,
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box .widget-body,
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box .pill {{
  background: var(--ct-surface) !important;
}}
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box .pill {{
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

/* --- Shortcut Widget Box Hover Effects --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box:hover {{
  border-color: var(--ct-accent) !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
  transform: translateY(-1px) !important;
}}

/* --- Number Cards / KPI Widgets --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .number-card,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget.number-widget-box,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-body .number-card-wrapper {{
  background: var(--ct-surface-bg) !important;
  border: 1.5px solid var(--ct-border-color) !important;
  border-radius: 10px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
  transition: all 0.2s ease !important;
  padding: 16px 20px !important;
  box-sizing: border-box !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .number-card:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget.number-widget-box:hover {{
  border-color: var(--ct-accent) !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
  transform: translateY(-1px) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .number-card .number-card-label,
[data-theme="{ 'dark' if is_dark else 'light' }"] .number-card .widget-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget.number-widget-box .widget-title {{
  color: var(--ct-text-secondary) !important;
  font-size: 0.7rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .number-card .number-card-number,
[data-theme="{ 'dark' if is_dark else 'light' }"] .number-card .number,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget.number-widget-box .number {{
  color: var(--ct-text-primary) !important;
  font-size: 1.5rem !important;
  font-weight: 700 !important;
}}

/* --- Chart Cards / Dashboard Charts --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .chart-card,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget.chart-widget-box,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dashboard-chart-wrapper,
[data-theme="{ 'dark' if is_dark else 'light' }"] .chart-container {{
  background: var(--ct-surface-bg) !important;
  border: 1.5px solid var(--ct-border-color) !important;
  border-radius: 16px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
  transition: all 0.2s ease !important;
  padding: 20px !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .chart-card:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget.chart-widget-box:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dashboard-chart-wrapper:hover {{
  border-color: var(--ct-accent) !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
  transform: translateY(-1px) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .chart-card .card-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dashboard-chart-wrapper .chart-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget.chart-widget-box .widget-title {{
  color: var(--ct-text-primary) !important;
  font-weight: 600 !important;
}}

/* --- ApexCharts Tooltip Fix --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-series-group {{
  background: var(--ct-surface-bg) !important;
  border-color: var(--ct-border-color) !important;
  color: var(--ct-text-primary) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-title {{
  background: var(--ct-navbar-bg) !important;
  border-bottom-color: var(--ct-border-color) !important;
  color: var(--ct-text-primary) !important;
  font-weight: 600 !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-series-group {{
  background: var(--ct-surface-bg) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-text-goals-value,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-text-y-value,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-text-z-value {{
  color: var(--ct-text-primary) !important;
}}

/* --- Widget Group / Reports & Masters Cards --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .modules-card-container,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget.onboarding-widget {{
  background: var(--ct-surface-bg) !important;
  border: 1.5px solid var(--ct-border-color) !important;
  border-radius: 10px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
  transition: all 0.2s ease !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .modules-card-container:hover {{
  border-color: var(--ct-accent) !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
  transform: translateY(-1px) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .widget-group-head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .widget-group-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group h3,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group h4,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .modules-card-container .module-title {{
  color: var(--ct-text-primary) !important;
  font-weight: 700 !important;
  font-size: 1rem !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .modules-card-container a {{
  color: var(--ct-text-secondary) !important;
  transition: color 0.15s ease !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group a:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .modules-card-container a:hover {{
  color: var(--ct-accent) !important;
}}

/* --- Kanban Cards --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .kanban-column {{
  background: var(--ct-surface-bg) !important;
  border: 1px solid var(--ct-border-color) !important;
  border-radius: 16px !important;
  padding: 20px !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .kanban-card.content {{
  background: var(--ct-navbar-bg) !important;
  border: 1.5px solid var(--ct-border-color) !important;
  border-radius: 10px !important;
  transition: all 0.2s ease !important;
  margin-bottom: 12px !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .kanban-card-wrapper:hover .kanban-card.content {{
  border-color: var(--ct-accent) !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
  transform: translateY(-1px) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .kanban-column-header,
[data-theme="{ 'dark' if is_dark else 'light' }"] .kanban-column-title {{
  color: var(--ct-text-primary) !important;
  font-weight: 700 !important;
  border-bottom: 2px solid var(--ct-border-color) !important;
  padding-bottom: 12px !important;
  margin-bottom: 16px !important;
}}

/* --- Top-Right Action Buttons: Primary + Secondary/Ghost --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .primary-action,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-head-actions .primary-action,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn-primary {{
  background: var(--ct-accent) !important;
  border: 2px solid var(--ct-accent) !important;
  color: #ffffff !important;
  transition: all 0.2s ease !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
  font-weight: 600 !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .primary-action:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-head-actions .primary-action:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn-primary:hover {{
  background: var(--ct-accent-hover) !important;
  border-color: var(--ct-accent-hover) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
  transform: translateY(-1px) !important;
}}

/* Secondary/Ghost buttons in page actions */
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn-secondary,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn-default,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-head-actions .btn-secondary,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-head-actions .btn-default,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn:not(.btn-primary):not(.primary-action),
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-head-actions .btn:not(.btn-primary):not(.primary-action) {{
  background: var(--ct-surface-bg) !important;
  border: 2px solid var(--ct-border-color) !important;
  color: var(--ct-text-primary) !important;
  font-weight: 600 !important;
  transition: all 0.2s ease !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn-secondary:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn-default:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-head-actions .btn-secondary:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-head-actions .btn-default:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn:not(.btn-primary):not(.primary-action):hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-head-actions .btn:not(.btn-primary):not(.primary-action):hover {{
  background: var(--ct-accent-hover) !important;
  border-color: var(--ct-accent) !important;
  color: #ffffff !important;
  transform: translateY(-1px) !important;
}}

/* Button icons/text visibility */
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn svg,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-head-actions .btn svg,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn .icon,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-head-actions .btn .icon {{
  fill: currentColor !important;
  stroke: currentColor !important;
}}

/* --- Chart Tooltip: Force Readable Contrast --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-series-group,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-xaxistooltip,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-yaxistooltip {{
  background: var(--ct-surface-bg) !important;
  background-color: var(--ct-surface-bg) !important;
  border: 2px solid var(--ct-border-color) !important;
  color: var(--ct-text-primary) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-title {{
  background: var(--ct-navbar-bg) !important;
  border-bottom: 2px solid var(--ct-border-color) !important;
  color: var(--ct-text-primary) !important;
  font-weight: 700 !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-series-group {{
  background: var(--ct-surface-bg) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-text-goals-value,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-text-y-value,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-text-z-value,
[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-text {{
  color: var(--ct-text-primary) !important;
  font-weight: 600 !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .apexcharts-tooltip-marker {{
  border: 2px solid var(--ct-border-color) !important;
}}

/* Frappe chart tooltips */
[data-theme="{ 'dark' if is_dark else 'light' }"] .chart-tooltip,
[data-theme="{ 'dark' if is_dark else 'light' }"] .graph-svg-tip,
[data-theme="{ 'dark' if is_dark else 'light' }"] .tooltip-inner {{
  background: var(--ct-surface-bg) !important;
  border: 2px solid var(--ct-border-color) !important;
  color: var(--ct-text-primary) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
}}

/* Generic tooltip fallback */
[data-theme="{ 'dark' if is_dark else 'light' }"] .tooltip,
[data-theme="{ 'dark' if is_dark else 'light' }"] .popover {{
  background: var(--ct-surface-bg) !important;
  border: 2px solid var(--ct-border-color) !important;
  color: var(--ct-text-primary) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .tooltip .arrow::before,
[data-theme="{ 'dark' if is_dark else 'light' }"] .popover .arrow::before {{
  border-top-color: var(--ct-surface-bg) !important;
}}

/* --- Shortcut pills and badges - force dark background --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box .pill,
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box .badge,
[data-theme="{ 'dark' if is_dark else 'light' }"] .badge,
[data-theme="{ 'dark' if is_dark else 'light' }"] .pill,
[data-theme="{ 'dark' if is_dark else 'light' }"] .pill-badge,
[data-theme="{ 'dark' if is_dark else 'light' }"] .count-badge,
[data-theme="{ 'dark' if is_dark else 'light' }"] [class*="badge"],
[data-theme="{ 'dark' if is_dark else 'light' }"] [class*="pill"] {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

/* --- Force all white backgrounds to dark in widgets --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .pill[style*="background"],
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .badge[style*="background"],
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box span[class*="pill"],
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box span[class*="badge"] {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Section headers --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .section-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .section-head {{
  color: var(--ct-text-primary) !important;
}}

/* --- Text colors --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] body,
[data-theme="{ 'dark' if is_dark else 'light' }"] .text-color,
[data-theme="{ 'dark' if is_dark else 'light' }"] .text-muted,
[data-theme="{ 'dark' if is_dark else 'light' }"] h1, [data-theme="{ 'dark' if is_dark else 'light' }"] h2,
[data-theme="{ 'dark' if is_dark else 'light' }"] h3, [data-theme="{ 'dark' if is_dark else 'light' }"] h4,
[data-theme="{ 'dark' if is_dark else 'light' }"] h5, [data-theme="{ 'dark' if is_dark else 'light' }"] h6 {{
  color: var(--ct-text-primary) !important;
}}

/* --- Buttons --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary {{
  background: var(--ct-primary-btn-bg) !important;
  border-color: var(--ct-primary-btn-bg) !important;
  color: var(--ct-primary-btn-text) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary:hover {{
  background: var(--ct-accent-hover) !important;
  border-color: var(--ct-accent-hover) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-secondary {{
  background: var(--ct-secondary-btn-bg) !important;
  border-color: var(--ct-secondary-btn-bg) !important;
  color: var(--ct-secondary-btn-text) !important;
}}

/* --- Links --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .link-primary {{
  color: var(--ct-accent-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] a:hover {{
  color: var(--ct-accent-hover) !important;
}}

/* --- Buttons - comprehensive styling --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn:hover {{
  background: var(--ct-accent-hover) !important;
  border-color: var(--ct-accent) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary {{
  background: var(--ct-accent) !important;
  border-color: var(--ct-accent) !important;
  color: #ffffff !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary:hover {{
  background: var(--ct-accent-hover) !important;
  border-color: var(--ct-accent-hover) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-secondary,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-default {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-danger {{
  background: #dc3545 !important;
  border-color: #dc3545 !important;
  color: #ffffff !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-success {{
  background: var(--ct-success) !important;
  border-color: var(--ct-success) !important;
  color: #ffffff !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-warning {{
  background: #ffc107 !important;
  border-color: #ffc107 !important;
  color: #212529 !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn:disabled,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn.disabled {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-muted) !important;
  opacity: 0.6 !important;
}}

/* --- Form elements - comprehensive --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] input,
[data-theme="{ 'dark' if is_dark else 'light' }"] select,
[data-theme="{ 'dark' if is_dark else 'light' }"] textarea,
[data-theme="{ 'dark' if is_dark else 'light' }"] .form-control {{
  background: var(--ct-surface) !important;
  border-color: var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] input:focus,
[data-theme="{ 'dark' if is_dark else 'light' }"] select:focus,
[data-theme="{ 'dark' if is_dark else 'light' }"] textarea:focus,
[data-theme="{ 'dark' if is_dark else 'light' }"] .form-control:focus {{
  border-color: var(--ct-accent) !important;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] input::placeholder,
[data-theme="{ 'dark' if is_dark else 'light' }"] textarea::placeholder {{
  color: var(--ct-text-muted) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .input-group-text {{
  background: var(--ct-surface) !important;
  border-color: var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .form-label,
[data-theme="{ 'dark' if is_dark else 'light' }"] label {{
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .form-text,
[data-theme="{ 'dark' if is_dark else 'light' }"] .help-text {{
  color: var(--ct-text-muted) !important;
}}

/* --- Tables - comprehensive --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .table,
[data-theme="{ 'dark' if is_dark else 'light' }"] .datatable,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row,
[data-theme="{ 'dark' if is_dark else 'light' }"] .data-row {{
  background: var(--ct-surface-bg) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .table thead th,
[data-theme="{ 'dark' if is_dark else 'light' }"] .datatable-header,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row-head {{
  background: var(--ct-navbar-bg) !important;
  color: var(--ct-text-primary) !important;
  border-color: var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .table td,
[data-theme="{ 'dark' if is_dark else 'light' }"] .table th {{
  border-color: var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .table-hover tbody tr:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .data-row:hover {{
  background: var(--ct-accent-hover) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .table-striped tbody tr:nth-of-type(odd) {{
  background: rgba(255,255,255,0.03) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row.active,
[data-theme="{ 'dark' if is_dark else 'light' }"] .data-row.active {{
  background: var(--ct-accent-hover) !important;
}}

/* --- Dropdown menus - comprehensive --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item {{
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item:focus,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item.active {{
  background: var(--ct-accent-hover) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-header {{
  color: var(--ct-text-muted) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-divider {{
  border-top: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-toggle {{
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-toggle:hover {{
  background: var(--ct-accent-hover) !important;
}}

/* --- Dropdown Menu Visibility Fix (Issue #1) --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu.show,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-list,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-help {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item span,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-list li a {{
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li a:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-list li a:hover {{
  background: var(--ct-accent-hover) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Menu Toggle Switches Fix --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-btn-group .toggle-switch,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu .toggle-switch,
[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-switch,
[data-theme="{ 'dark' if is_dark else 'light' }"] .toggle-btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-toggle {{
  background: var(--ct-surface) !important;
  border: 2px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-btn-group .toggle-switch.active,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu .toggle-switch.active,
[data-theme="{ 'dark' if is_dark else 'light' }"] .toggle-switch:checked,
[data-theme="{ 'dark' if is_dark else 'light' }"] .toggle-btn.active {{
  background: var(--ct-accent) !important;
  border-color: var(--ct-accent) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .toggle-switch .toggle-slider,
[data-theme="{ 'dark' if is_dark else 'light' }"] .toggle-btn .slider {{
  background: var(--ct-text-muted) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .toggle-switch.active .toggle-slider,
[data-theme="{ 'dark' if is_dark else 'light' }"] .toggle-switch:checked .toggle-slider {{
  background: #ffffff !important;
}}

/* --- Menu Items Better Styling --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-btn-group .menu-item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu .menu-item {{
  color: var(--ct-text-primary) !important;
  background: transparent !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-item:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-item.active {{
  background: var(--ct-accent-hover) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Form Inputs Dark Theme --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .form-control,
[data-theme="{ 'dark' if is_dark else 'light' }"] input.form-control,
[data-theme="{ 'dark' if is_dark else 'light' }"] textarea.form-control,
[data-theme="{ 'dark' if is_dark else 'light' }"] select.form-control {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .form-control:focus {{
  border-color: var(--ct-accent) !important;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.3) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .form-control::placeholder {{
  color: var(--ct-text-muted) !important;
}}

/* --- AGGRESSIVE Dropdown Menu Solid Background --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu.show,
[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-dropdown,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-list,
[data-theme="{ 'dark' if is_dark else 'light' }"] ul.dropdown-menu,
[data-theme="{ 'dark' if is_dark else 'light' }"] div.dropdown-menu {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.8) !important;
  z-index: 99999 !important;
  opacity: 1 !important;
  visibility: visible !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu > li,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu > li > a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu span,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li span {{
  background: transparent !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu > li > a:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li:hover {{
  background: var(--ct-accent-hover) !important;
  color: #ffffff !important;
}}

/* --- AGGRESSIVE Button Visibility Fix --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] button.btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] a.btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .actions-btn-group .btn {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 2px solid var(--ct-border) !important;
  border-radius: 6px !important;
  padding: 8px 16px !important;
  font-weight: 500 !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
  transition: all 0.2s ease !important;
  cursor: pointer !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn.btn-primary {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border: 2px solid var(--ct-accent) !important;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.5) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-secondary:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-default:hover {{
  background: var(--ct-accent-hover) !important;
  color: #ffffff !important;
  border-color: var(--ct-accent) !important;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.4) !important;
  transform: translateY(-2px) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary:hover {{
  background: var(--ct-accent-hover) !important;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.6) !important;
  transform: translateY(-2px) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn:disabled,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn.disabled {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-muted) !important;
  border-color: var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-backdrop {{
  background: rgba(0,0,0,0.5) !important;
  z-index: 9990 !important;
}}

/* --- ULTRA AGGRESSIVE Filter Area Fix (White Background Issue) --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-area,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-box,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-section,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-filter,
[data-theme="{ 'dark' if is_dark else 'light' }"] .form-group.frappe-control,
[data-theme="{ 'dark' if is_dark else 'light' }"] .frappe-control[data-fieldtype="Filter"] {{
  background: var(--ct-navbar-bg) !important;
  background-color: var(--ct-navbar-bg) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-area input,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-box input,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-section input,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-area select,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-box select {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-area label,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-box label,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-section label,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-label {{
  color: var(--ct-text-primary) !important;
}}

/* --- ULTRA AGGRESSIVE Dropdown Fix --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu.show,
[data-theme="{ 'dark' if is_dark else 'light' }"] ul.dropdown-menu,
[data-theme="{ 'dark' if is_dark else 'light' }"] div.dropdown-menu,
[data-theme="{ 'dark' if is_dark else 'light' }"] .navbar .dropdown-menu,
[data-theme="{ 'dark' if is_dark else 'light' }"] .nav .dropdown-menu {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.8) !important;
  z-index: 99999 !important;
  opacity: 1 !important;
  visibility: visible !important;
  position: absolute !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item span,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu a {{
  background: transparent !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li a:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item:hover {{
  background: var(--ct-accent-hover) !important;
  color: #ffffff !important;
}}

/* --- ULTRA AGGRESSIVE Button Fix --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] button.btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] a.btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .actions-btn-group .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .navbar .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .nav .btn {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 2px solid var(--ct-border) !important;
  border-radius: 6px !important;
  padding: 8px 16px !important;
  font-weight: 500 !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
  transition: all 0.2s ease !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn.btn-primary {{
  background: var(--ct-accent) !important;
  background-color: var(--ct-accent) !important;
  color: #ffffff !important;
  border: 2px solid var(--ct-accent) !important;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.5) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] button.btn:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] a.btn:hover {{
  background: var(--ct-accent-hover) !important;
  color: #ffffff !important;
  border-color: var(--ct-accent) !important;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.4) !important;
  transform: translateY(-2px) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary:hover {{
  background: var(--ct-accent-hover) !important;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.6) !important;
  transform: translateY(-2px) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn .icon,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn svg {{
  fill: currentColor !important;
  stroke: currentColor !important;
}}

/* --- Action Buttons Fix (Issue #1) - More aggressive with proper colors --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn-action,
[data-theme="{ 'dark' if is_dark else 'light' }"] .actions-btn-group,
[data-theme="{ 'dark' if is_dark else 'light' }"] .actions-btn-group .btn {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .actions-btn-group .btn:hover {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border-color: var(--ct-accent) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn svg,
[data-theme="{ 'dark' if is_dark else 'light' }"] .actions-btn-group .btn svg {{
  fill: var(--ct-text-primary) !important;
  stroke: var(--ct-text-primary) !important;
}}

/* --- Widget/Card Headers Fix (Issue #3) --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .widget-head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-head .widget-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .section-head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .widget-group-head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .widget-group-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .head {{
  color: var(--ct-text-primary) !important;
  background: transparent !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .widget-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .section-head h4,
[data-theme="{ 'dark' if is_dark else 'light' }"] .section-head h5 {{
  color: var(--ct-text-primary) !important;
  font-weight: 600 !important;
}}

/* --- Card Items/Links with Hover (Issue #4) --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .widget-item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .widget-link,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-content a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-body a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-list a {{
  color: var(--ct-accent) !important;
  transition: all 0.2s ease !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget a:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .widget-item:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .item:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .widget-link:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-content a:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .shortcut-widget-box a:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-body a:hover {{
  color: var(--ct-accent-hover) !important;
  background: rgba(37, 99, 235, 0.1) !important;
  padding-left: 4px !important;
  border-radius: 4px !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .ellipsis,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-item .ellipsis,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-body .ellipsis {{
  color: var(--ct-accent) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .ellipsis:hover {{
  color: var(--ct-accent-hover) !important;
}}

/* --- Table Hover Text Readability Fix --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .table tbody tr:hover td,
[data-theme="{ 'dark' if is_dark else 'light' }"] .datatable .data-row:hover .data-row-col,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row:hover .list-row-col,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row:hover .level-item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .table-hover tbody tr:hover td * {{
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .table tbody tr:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .datatable .data-row:hover {{
  background: var(--ct-accent-hover) !important;
}}

/* --- Header Filter Fix (White background issue) --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row-head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-filter,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-box,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-section,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-area {{
  background: var(--ct-navbar-bg) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-box input,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-area input,
[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-section input {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .filter-label,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row-head .list-check-all,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row-head .list-row-checkbox {{
  color: var(--ct-text-primary) !important;
}}

/* --- Dropdown Menu Solid Background Fix --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu.show,
[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-dropdown,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-list {{
  background: var(--ct-surface) !important;
  background-color: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
  z-index: 9999 !important;
  opacity: 1 !important;
  visibility: visible !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item span {{
  background: transparent !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-menu li a:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-item:hover {{
  background: var(--ct-accent-hover) !important;
  color: var(--ct-text-primary) !important;
}}

/* --- Action Buttons with better visibility --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .actions-btn-group .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-btn-group .btn {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 2px solid var(--ct-border) !important;
  border-radius: 6px !important;
  font-weight: 500 !important;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .page-actions .btn:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .actions-btn-group .btn:hover {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border-color: var(--ct-accent) !important;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
  transform: translateY(-2px) !important;
}}

/* --- Widget Headers Forced White --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .widget-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .widget-group-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-shortcut-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .section-head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-head h4,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-head h5,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group-head h4,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group-head h5 {{
  color: #ffffff !important;
  text-shadow: none !important;
}}


[data-theme="{ 'dark' if is_dark else 'light' }"] .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-secondary,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-default {{
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

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border: 2px solid var(--ct-accent) !important;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-secondary:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-default:hover {{
  background: var(--ct-accent-hover) !important;
  border-color: var(--ct-accent) !important;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
  transform: translateY(-1px) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary:hover {{
  background: var(--ct-accent-hover) !important;
  color: #ffffff !important;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.6) !important;
  transform: translateY(-1px) !important;
}}

/* --- Widget Headers Forced White (Issue #2) --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget .widget-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .widget-group-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-shortcut-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .section-head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-head h4,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-head h5,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group-head h4,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group-head h5 {{
  color: #ffffff !important;
  text-shadow: none !important;
}}

/* --- Group Titles Fix (Issue #4) --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .section-head,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group-title,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .head,
[data-theme="{ 'dark' if is_dark else 'light' }"] [class*="group-title"],
[data-theme="{ 'dark' if is_dark else 'light' }"] .reports-section,
[data-theme="{ 'dark' if is_dark else 'light' }"] .section-title {{
  color: #ffffff !important;
  font-weight: 600 !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .text-muted,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .text-dark,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .text-secondary {{
  color: var(--ct-text-muted) !important;
}}

/* --- Card Hover Effects --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget.shortcut-widget-box,
[data-theme="{ 'dark' if is_dark else 'light' }"] .card.widget {{
  transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget.shortcut-widget-box:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .card.widget:hover {{
  transform: translateY(-4px) !important;
  border-color: var(--ct-accent) !important;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.2) !important;
  background: var(--ct-surface) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget-group .widget:hover {{
  border-left: 3px solid var(--ct-accent) !important;
}}

/* --- Modals - comprehensive --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .modal-content {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .modal-header {{
  background: var(--ct-surface) !important;
  border-bottom: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .modal-footer {{
  background: var(--ct-surface) !important;
  border-top: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .modal-body {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .modal-title {{
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .close,
[data-theme="{ 'dark' if is_dark else 'light' }"] .modal-header .close {{
  color: var(--ct-text-muted) !important;
  text-shadow: none !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .close:hover {{
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .modal-backdrop {{
  background: rgba(0,0,0,0.8) !important;
}}

/* --- Tooltips & Popovers --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .tooltip-inner {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .popover {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .popover-header {{
  background: var(--ct-surface) !important;
  border-bottom: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .popover-body {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .bs-popover-auto[data-popper-placement^="top"] > .popover-arrow::after,
[data-theme="{ 'dark' if is_dark else 'light' }"] .bs-popover-top > .popover-arrow::after {{
  border-top-color: var(--ct-surface) !important;
}}

/* --- Kanban & Calendar Views --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .kanban-board {{
  background: var(--ct-body-bg) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .kanban-column {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .kanban-card {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .kanban-card:hover {{
  background: var(--ct-accent-hover) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .fc-day {{
  background: var(--ct-surface) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .fc-day-today {{
  background: var(--ct-accent-hover) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .fc-event {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border: none !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .fc-toolbar-title {{
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .fc-button {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .fc-button:hover {{
  background: var(--ct-accent-hover) !important;
}}

/* --- Animations & Transitions --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn-primary,
[data-theme="{ 'dark' if is_dark else 'light' }"] .form-control,
[data-theme="{ 'dark' if is_dark else 'light' }"] .card,
[data-theme="{ 'dark' if is_dark else 'light' }"] .widget,
[data-theme="{ 'dark' if is_dark else 'light' }"] .kanban-card,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row {{
  transition: all 0.2s ease-in-out !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .widget:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .card:hover {{
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn:hover {{
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .btn:active {{
  transform: translateY(0) !important;
  box-shadow: none !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .sidebar-item,
[data-theme="{ 'dark' if is_dark else 'light' }"] .standard-sidebar-item {{
  transition: background 0.15s ease !important;
}}

/* --- Toast & Notification --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .toast {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .toast-header {{
  background: var(--ct-surface) !important;
  border-bottom: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .alert {{
  background: var(--ct-surface) !important;
  border: 1px solid var(--ct-border) !important;
  color: var(--ct-text-primary) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .alert-primary {{
  border-left: 4px solid var(--ct-accent) !important;
}}

/* --- Tabs & Navigation --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .nav-tabs {{
  border-bottom: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .nav-tabs .nav-link {{
  color: var(--ct-text-muted) !important;
  border: none !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .nav-tabs .nav-link:hover {{
  color: var(--ct-text-primary) !important;
  background: var(--ct-accent-hover) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .nav-tabs .nav-link.active {{
  color: var(--ct-text-primary) !important;
  background: var(--ct-surface) !important;
  border-bottom: 2px solid var(--ct-accent) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .nav-pills .nav-link {{
  color: var(--ct-text-muted) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .nav-pills .nav-link.active {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
}}

/* --- Pagination --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .pagination .page-link {{
  background: var(--ct-surface) !important;
  color: var(--ct-text-primary) !important;
  border: 1px solid var(--ct-border) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .pagination .page-link:hover {{
  background: var(--ct-accent-hover) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .pagination .page-item.active .page-link {{
  background: var(--ct-accent) !important;
  border-color: var(--ct-accent) !important;
  color: #ffffff !important;
}}

/* --- AGGRESSIVE Table Row Hover Fix --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .table tbody tr:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .data-row:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .grid-row:hover {{
  background: var(--ct-accent-hover) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .table tbody tr:hover td,
[data-theme="{ 'dark' if is_dark else 'light' }"] .table tbody tr:hover a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .table tbody tr:hover span,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row:hover .list-row-col,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row:hover a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .list-row:hover span,
[data-theme="{ 'dark' if is_dark else 'light' }"] .data-row:hover .data-row-col,
[data-theme="{ 'dark' if is_dark else 'light' }"] .data-row:hover a,
[data-theme="{ 'dark' if is_dark else 'light' }"] .grid-row:hover td,
[data-theme="{ 'dark' if is_dark else 'light' }"] .grid-row:hover a {{
  color: #ffffff !important;
}}

/* --- AGGRESSIVE Dropdown Backdrop --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-backdrop,
[data-theme="{ 'dark' if is_dark else 'light' }"] .modal-backdrop.show,
[data-theme="{ 'dark' if is_dark else 'light' }"] .open > .dropdown-backdrop {{
  background: rgba(0,0,0,0.7) !important;
  z-index: 9990 !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
}}

/* --- AGGRESSIVE Menu Button Fix (Three dots menu) --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-btn-group > .btn,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-toggle,
[data-theme="{ 'dark' if is_dark else 'light' }"] .btn.menu-btn {{
  background: var(--ct-accent) !important;
  color: #ffffff !important;
  border: none !important;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .menu-btn:hover,
[data-theme="{ 'dark' if is_dark else 'light' }"] .dropdown-toggle:hover {{
  background: var(--ct-accent-hover) !important;
  color: #ffffff !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 8px rgba(0,0,0,0.4) !important;
}}

/* --- Progress & Loading --- */
[data-theme="{ 'dark' if is_dark else 'light' }"] .progress {{
  background: var(--ct-surface) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .progress-bar {{
  background: var(--ct-accent) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .spinner-border {{
  color: var(--ct-accent) !important;
}}

[data-theme="{ 'dark' if is_dark else 'light' }"] .loading-spinner {{
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

    # PRIORITY 1: Check if current user has a specific theme set for this mode in User Desk Theme
    if frappe.session.user != "Guest":
        user_theme = frappe.db.get_value(
            "User Desk Theme",
            {"user": frappe.session.user},
            ["light_theme", "dark_theme", "inherit_from_site"],
            as_dict=True,
        )
        if user_theme and not user_theme.inherit_from_site:
            user_pref = user_theme.dark_theme if mode == "dark" else user_theme.light_theme
            if user_pref:
                return user_pref

    # PRIORITY 2: Check site defaults in Modern Theme Settings
    site_settings = frappe.db.get_value(
        "Modern Theme Settings",
        {"name": "Modern Theme Settings"},
        ["default_light_theme", "default_dark_theme"],
        as_dict=True,
    )
    if site_settings:
        site_pref = site_settings.default_dark_theme if mode == "dark" else site_settings.default_light_theme
        if site_pref:
            return site_pref

    # PRIORITY 3: Hardcoded system defaults
    if key_lower in ("light", "construction_light"):
        return (
            frappe.db.get_value("Construction Theme", {"is_system_theme": 1, "is_default_light": 1}, "name")
            or "Construction Light"
        )

    if key_lower in ("dark", "construction_dark"):
        return (
            frappe.db.get_value("Construction Theme", {"is_system_theme": 1, "is_default_dark": 1}, "name")
            or "Construction Dark"
        )

    # Custom themes: exact name match (case-insensitive)
    existing = frappe.db.get_value("Construction Theme", {"name": theme_key, "is_active": 1}, "name")
    if existing:
        return existing

    # Try case-insensitive match for custom themes
    all_active = frappe.get_all("Construction Theme", filters={"is_active": 1}, fields=["name"])
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
        # Set theme based on mode (using actual DocType name)
        if mode == "light":
            user_theme.light_theme = theme_doc
        else:
            user_theme.dark_theme = theme_doc

        user_theme.inherit_from_site = 0  # User has custom theme, don't inherit
        user_theme.save(ignore_permissions=True)

        # Also update User doc desk_theme for mode consistency
        desk_theme_value = "Dark" if mode == "dark" else "Light"
        frappe.db.set_value("User", user, "desk_theme", desk_theme_value, update_modified=False)

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
                "label": f"{t.emoji_icon or '🎨'} {t.theme_name}",
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

        # Phase 2: CSS variable definitions + Jinja2 template-based CSS
        css = theme_doc.generate_css_variables()
        css += theme_doc.generate_css()

        # Append custom_css if present (from the DocType's custom_css field)
        if hasattr(theme_doc, "custom_css") and theme_doc.custom_css:
            css += "\n/* ===== CUSTOM CSS ===== */\n" + theme_doc.custom_css

        # Build feature toggles dict
        feature_toggles = {}
        for field in [
            "hide_help_button",
            "hide_search_bar",
            "hide_sidebar",
            "hide_like_comment",
            "mobile_card_view",
        ]:
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
    theme_mode = "dark" if "dark" in theme.theme_name.lower() else "light"
    css_parts.append(f"""/* ===== BASE: {theme.theme_name} ===== */
html[data-theme="{theme_mode}"] {{
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
html[data-theme="{theme_mode}"] .navbar {{
	background: {navbar} !important;
	border-bottom: 2px solid {accent} !important;
	{"box-shadow: 0 2px 8px rgba(0,0,0,.3) !important;" if is_dark else "box-shadow: 0 2px 4px rgba(0,0,0,.1) !important;"}
}}

html[data-theme="{theme_mode}"] .navbar .nav-link {{
	color: {text} !important;
}}

html[data-theme="{theme_mode}"] .navbar .nav-link:hover {{
	color: {accent} !important;
	background: {accent}19 !important;
	border-radius: 8px !important;
}}""")

    # Sidebar
    css_parts.append(f"""/* ===== SIDEBAR ===== */
html[data-theme="{theme_mode}"] .layout-side-section {{
	background: {sidebar} !important;
	border-right: 1px solid {border} !important;
}}

html[data-theme="{theme_mode}"] .desk-sidebar .standard-sidebar-item a {{
	color: {text} !important;
}}

html[data-theme="{theme_mode}"] .desk-sidebar .standard-sidebar-item.selected a {{
	background: {accent}33 !important;
	color: {accent} !important;
	box-shadow: inset 3px 0 0 {accent} !important;
}}

html[data-theme="{theme_mode}"] .desk-sidebar .standard-sidebar-item a:hover {{
	color: {accent} !important;
	background: {accent}19 !important;
}}""")

    # Buttons
    css_parts.append(f"""/* ===== BUTTONS ===== */
html[data-theme="{theme_mode}"] .btn-primary {{
	background: {accent} !important;
	border-color: {accent} !important;
	color: #fff !important;
	border-radius: 10px !important;
}}

html[data-theme="{theme_mode}"] .btn-primary:hover {{
	background: {accent_hover} !important;
	border-color: {accent_hover} !important;
	transform: translateY(-1px) !important;
}}

html[data-theme="{theme_mode}"] .btn-default {{
	background: {surface} !important;
	border: 1px solid {border} !important;
	color: {text} !important;
	border-radius: 10px !important;
}}

html[data-theme="{theme_mode}"] .btn-default:hover {{
	background: {accent}19 !important;
	border-color: {accent} !important;
	color: {accent} !important;
}}""")

    # Forms
    css_parts.append(f"""/* ===== FORMS ===== */
html[data-theme="{theme_mode}"] .form-control {{
	background: {surface} !important;
	border-color: {border} !important;
	color: {text} !important;
	border-radius: 8px !important;
}}

html[data-theme="{theme_mode}"] .form-control:focus {{
	border-color: {accent} !important;
	box-shadow: 0 0 0 3px {accent}26 !important;
}}

html[data-theme="{theme_mode}"] a {{
	color: {accent} !important;
}}

html[data-theme="{theme_mode}"] h1,
html[data-theme="{theme_mode}"] h2,
html[data-theme="{theme_mode}"] h3 {{
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

            return {"theme": "construction_light", "mode": "light", "source": "hardcoded_guest"}

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
                site_settings.default_dark_theme if mode == "dark" else site_settings.default_light_theme
            )
            if theme_doc:
                frontend_key = _get_frontend_theme_key(theme_doc, mode)
                return {"theme": frontend_key, "mode": mode, "source": "site_default", "doc_name": theme_doc}

        # Fall back to construction theme based on mode (not plain light/dark)
        # This ensures the JS loads the correct CSS on initial page load
        construction_key = f"construction_{mode}"
        return {"theme": construction_key, "mode": mode, "source": "mode_fallback"}

    except Exception as e:
        frappe.log_error(f"Error getting theme for boot: {str(e)}")
        return {"theme": "light", "mode": "light", "source": "error_fallback"}


def add_theme_to_boot(bootinfo):
    """
    Inject theme configuration into frappe.boot for JS access.
    This runs on every desk page load.
    """
    if frappe.session.user == "Guest":
        return

    # Cache theme config for 1 hour to avoid repeated DB hits
    cache_key = f"construction_theme:{frappe.local.site}"
    theme_config = frappe.cache().get_value(cache_key)

    if not theme_config:
        theme_config = get_theme_config()
        frappe.cache().set_value(cache_key, theme_config, expires_in_sec=3600)

    bootinfo.construction_theme = theme_config
    bootinfo.construction_typography = get_user_typography_settings()
    # Also set the standard frappe.boot.theme for compatibility
    bootinfo.theme = theme_config.get("color_scheme", "dark")


def _default_typography_settings():
    return {
        "desk_font_family": "System Default",
        "desk_font_size": 14,
        "desk_font_weight": "400",
        "sidebar_font_family": "Inherit",
        "sidebar_font_size": 13,
        "sidebar_font_weight": "500",
        "navbar_font_family": "Inherit",
        "navbar_font_size": 14,
        "navbar_font_weight": "500",
        "form_font_family": "Inherit",
        "form_font_size": 14,
        "form_font_weight": "400",
        "list_font_family": "Inherit",
        "list_font_size": 13,
        "list_font_weight": "400",
        "menu_font_family": "Inherit",
        "menu_font_size": 13,
        "menu_font_weight": "400",
    }


def _normalize_typography_settings(values):
    settings = _default_typography_settings()
    if values:
        settings.update({key: values.get(key) for key in settings if values.get(key) is not None})

    allowed_fonts = {
        "Inherit",
        "System Default",
        "Inter",
        "Arial",
        "Helvetica",
        "Tahoma",
        "Verdana",
        "Trebuchet MS",
        "Georgia",
        "Times New Roman",
        "Courier New",
        "Roboto",
        "Open Sans",
        "Lato",
        "Montserrat",
        "Poppins",
        "Noto Sans",
        "Noto Sans Arabic",
        "Cairo",
        "Tajawal",
        "Almarai",
    }
    for fieldname in (
        "desk_font_family",
        "sidebar_font_family",
        "navbar_font_family",
        "form_font_family",
        "list_font_family",
        "menu_font_family",
    ):
        if settings[fieldname] not in allowed_fonts:
            settings[fieldname] = "System Default" if fieldname == "desk_font_family" else "Inherit"
    if settings["desk_font_family"] == "Inherit":
        settings["desk_font_family"] = "System Default"

    size_defaults = (
        ("desk_font_size", 14),
        ("sidebar_font_size", 13),
        ("navbar_font_size", 14),
        ("form_font_size", 14),
        ("list_font_size", 13),
        ("menu_font_size", 13),
    )
    for fieldname, default_value in size_defaults:
        try:
            value = int(settings[fieldname])
        except (TypeError, ValueError):
            value = default_value
        settings[fieldname] = max(11, min(20, value))

    weight_defaults = (
        ("desk_font_weight", "400"),
        ("sidebar_font_weight", "500"),
        ("navbar_font_weight", "500"),
        ("form_font_weight", "400"),
        ("list_font_weight", "400"),
        ("menu_font_weight", "400"),
    )
    for fieldname, default_value in weight_defaults:
        value = str(settings.get(fieldname) or default_value)
        if value not in {"300", "400", "500", "600", "700"}:
            value = default_value
        settings[fieldname] = value

    return settings


@frappe.whitelist()
def get_user_typography_settings():
    """Return current user's Desk typography preferences."""
    if frappe.session.user == "Guest":
        return _default_typography_settings()

    try:
        if not frappe.db.table_exists("User Desk Theme"):
            return _default_typography_settings()

        values = frappe.db.get_value(
            "User Desk Theme",
            {"user": frappe.session.user},
            [
                "desk_font_family",
                "desk_font_size",
                "desk_font_weight",
                "sidebar_font_family",
                "sidebar_font_size",
                "sidebar_font_weight",
                "navbar_font_family",
                "navbar_font_size",
                "navbar_font_weight",
                "form_font_family",
                "form_font_size",
                "form_font_weight",
                "list_font_family",
                "list_font_size",
                "list_font_weight",
                "menu_font_family",
                "menu_font_size",
                "menu_font_weight",
            ],
            as_dict=True,
        )
        return _normalize_typography_settings(values)
    except Exception:
        return _default_typography_settings()


@frappe.whitelist()
def save_user_typography_settings(
    desk_font_family=None,
    desk_font_size=None,
    desk_font_weight=None,
    sidebar_font_family=None,
    sidebar_font_size=None,
    sidebar_font_weight=None,
    navbar_font_family=None,
    navbar_font_size=None,
    navbar_font_weight=None,
    form_font_family=None,
    form_font_size=None,
    form_font_weight=None,
    list_font_family=None,
    list_font_size=None,
    list_font_weight=None,
    menu_font_family=None,
    menu_font_size=None,
    menu_font_weight=None,
):
    """Persist current user's Desk typography preferences."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"))

    settings = _normalize_typography_settings(
        {
            "desk_font_family": desk_font_family,
            "desk_font_size": desk_font_size,
            "desk_font_weight": desk_font_weight,
            "sidebar_font_family": sidebar_font_family,
            "sidebar_font_size": sidebar_font_size,
            "sidebar_font_weight": sidebar_font_weight,
            "navbar_font_family": navbar_font_family,
            "navbar_font_size": navbar_font_size,
            "navbar_font_weight": navbar_font_weight,
            "form_font_family": form_font_family,
            "form_font_size": form_font_size,
            "form_font_weight": form_font_weight,
            "list_font_family": list_font_family,
            "list_font_size": list_font_size,
            "list_font_weight": list_font_weight,
            "menu_font_family": menu_font_family,
            "menu_font_size": menu_font_size,
            "menu_font_weight": menu_font_weight,
        }
    )

    existing = frappe.db.get_value("User Desk Theme", {"user": frappe.session.user}, "name")
    if existing:
        doc = frappe.get_doc("User Desk Theme", existing)
    else:
        doc = frappe.new_doc("User Desk Theme")
        doc.user = frappe.session.user
        doc.inherit_from_site = 1

    doc.update(settings)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.cache().delete_key(f"user_desk_theme:{frappe.session.user}")
    frappe.cache().hdel("bootinfo", frappe.session.user)

    return settings


def get_theme_config():
    """Fetch from Construction Theme DocType with safe defaults.
    Fallback to defaults if DocType/controller is missing."""
    try:
        # Check if table exists and has records (avoid controller import)
        if not frappe.db.table_exists("Construction Theme"):
            return get_default_theme_vals()

        default_theme = frappe.db.get_value(
            "Construction Theme", {"is_active": 1, "is_system_theme": 1}, "name"
        )
        if not default_theme:
            default_theme = frappe.db.get_value("Construction Theme", {"is_active": 1}, "name")

        if not default_theme:
            return get_default_theme_vals()

        # Use get_values to avoid controller import
        vals = frappe.db.get_values(
            "Construction Theme",
            default_theme,
            ["primary_color", "accent_color", "danger_color", "success_color", "theme_type", "custom_css"],
            as_dict=True,
        )
        if not vals:
            return get_default_theme_vals()
        doc = vals[0]
    except Exception:
        # Any error (ImportError, DoesNotExistError, etc.) → return defaults
        return get_default_theme_vals()

    return {
        "app_title": "Construction ERP",
        "logo_url": "/assets/construction/images/construction_logo.svg",
        "favicon": "/assets/construction/images/construction_logo.svg",
        "primary_color": doc.get("primary_color") or "#0ea5e9",
        "accent_color": doc.get("accent_color") or "#f59e0b",
        "danger_color": doc.get("danger_color") or "#dc2626",
        "success_color": doc.get("success_color") or "#16a34a",
        "color_scheme": "dark" if (doc.get("theme_type") or "Light") == "Dark" else "light",
        "custom_css": doc.get("custom_css") or "",
        "custom_js": "",
        "hide_help_menu": 1,
        "disable_update_popup": 1,
        "navbar_title": "",
    }


def get_default_theme_vals():
    """Fallback if DocType not yet configured."""
    return {
        "app_title": "Construction ERP",
        "logo_url": "/assets/construction/images/construction_logo.svg",
        "favicon": "/assets/construction/images/construction_logo.svg",
        "primary_color": "#0ea5e9",
        "accent_color": "#f59e0b",
        "danger_color": "#dc2626",
        "success_color": "#16a34a",
        "color_scheme": "dark",
        "custom_css": "",
        "custom_js": "",
        "hide_help_menu": 1,
        "disable_update_popup": 1,
        "navbar_title": "",
    }


def whitelabel_patch():
    """
    Post-migration cleanup. Removes Frappe branding that reappears on updates.
    """
    # Remove welcome page
    frappe.delete_doc_if_exists("Page", "welcome-to-erpnext", force=1)

    # Clear onboarding content
    if frappe.db.exists("Blog Post", "Welcome"):
        frappe.db.set_value("Blog Post", "Welcome", "content", "")

    # Clear module onboarding docs
    for module in frappe.get_all("Module Onboarding", fields=["name"]):
        doc = frappe.get_doc("Module Onboarding", module.name)
        doc.documentation_url = ""
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)

    # Clear onboarding steps
    for step in frappe.get_all("Onboarding Step", fields=["name"]):
        doc = frappe.get_doc("Onboarding Step", step.name)
        doc.intro_video_url = ""
        doc.description = ""
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        # Sanitize legacy onboarding actions for v16 compatibility
        if doc.get("action"):
            doc.action = _sanitize_onboarding_action(doc.action)
        doc.save(ignore_permissions=True)


# ── Onboarding Action Sanitizer ──
# v16 removed "Watch Video" from the Onboarding Step action options.
# This helper remaps legacy values to valid v16 alternatives.
_VALID_ONBOARDING_ACTIONS = {
    "Create Entry",
    "Update Settings",
    "Show Form Tour",
    "View Report",
    "Go to Page",
    "View Docs",
}

_LEGACY_ACTION_MAP = {
    "Watch Video": "View Docs",
}


def _sanitize_onboarding_action(action):
    """Return a valid v16 onboarding action. Falls back to 'View Docs'."""
    if not action:
        return action
    if action in _VALID_ONBOARDING_ACTIONS:
        return action
    return _LEGACY_ACTION_MAP.get(action, "View Docs")


@frappe.whitelist()
def ignore_update_popup():
    """
    Override for frappe.utils.change_log.show_update_popup.
    """
    # Just return, effectively disabling it
    return


def get_pdf_header():
    """Returns branded PDF header HTML."""
    return frappe.get_template("construction/templates/includes/pdf_header.html").render()


def get_pdf_footer():
    """Returns branded PDF footer HTML."""
    return frappe.get_template("construction/templates/includes/pdf_footer.html").render()
