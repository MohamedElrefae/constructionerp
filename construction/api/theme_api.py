"""
Theme API for Modern UI Theme
Handles per-user theme resolution and persistence
"""
import frappe
from frappe import _


@frappe.whitelist()
def get_effective_desk_theme():
    """
    Returns the effective Desk Theme for current user based on:
    - User's Light/Dark/Automatic preference
    - User Desk Theme override (if enabled and allowed)
    - Site defaults from Modern Theme Settings
    - OS preference (if Automatic)
    
    Returns:
        dict: {
            "theme_name": str,
            "mode": "light" | "dark",
            "source": "user_override" | "site_default" | "frappe_default"
        }
    """
    try:
        user = frappe.session.user
        user_doc = frappe.get_doc("User", user)
        
        # Determine light/dark mode
        mode = resolve_mode(user_doc.desk_theme)
        
        # Get site settings
        try:
            site_settings = frappe.get_doc("Modern Theme Settings")
            allow_user_override = site_settings.allow_user_override
        except frappe.DoesNotExistError:
            # Modern Theme Settings not created yet, use defaults
            return {
                "theme_name": "Standard",
                "mode": mode,
                "source": "frappe_default"
            }
        
        # Check for per-user override (if enabled)
        if allow_user_override:
            try:
                user_theme = frappe.get_doc("User Desk Theme", {"user": user})
                if user_theme and not user_theme.inherit_from_site:
                    # User has custom theme preference
                    theme_name = (
                        user_theme.light_theme 
                        if mode == "light" 
                        else user_theme.dark_theme
                    )
                    if theme_name:
                        return {
                            "theme_name": theme_name,
                            "mode": mode,
                            "source": "user_override"
                        }
            except frappe.DoesNotExistError:
                pass  # No user override set
        
        # Fall back to site defaults
        theme_name = (
            site_settings.default_light_theme 
            if mode == "light" 
            else site_settings.default_dark_theme
        )
        
        if theme_name:
            return {
                "theme_name": theme_name,
                "mode": mode,
                "source": "site_default"
            }
        
        # Ultimate fallback to Frappe default
        return {
            "theme_name": "Standard",
            "mode": mode,
            "source": "frappe_default"
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting effective desk theme: {str(e)}")
        return {
            "theme_name": "Standard",
            "mode": "light",
            "source": "error_fallback"
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
            order_by="is_standard desc, theme_name asc"
        )
        
        return [
            {
                "name": t.name,
                "label": t.theme_name or t.name,
                "is_standard": t.is_standard
            }
            for t in themes
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
                "dark_theme": user_theme.dark_theme
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
                    "message": _("User theme overrides are not allowed by administrator")
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
        
        return {
            "success": True,
            "message": _("Theme settings saved successfully")
        }
        
    except Exception as e:
        frappe.log_error(f"Error saving user theme settings: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


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
            "force_modern_ui": settings.force_modern_ui
        }
    except frappe.DoesNotExistError:
        return {"exists": False}


@frappe.whitelist()
def save_modern_theme_settings(
    default_light_theme,
    default_dark_theme,
    allow_user_override=True,
    force_modern_ui=True
):
    """
    Save site-wide Modern Theme Settings (admin only)
    
    Returns:
        dict: {"success": bool, "message": str}
    """
    if not frappe.has_permission("Modern Theme Settings", "write"):
        frappe.throw(_("Not permitted"))
    
    try:
        try:
            settings = frappe.get_doc("Modern Theme Settings")
        except frappe.DoesNotExistError:
            settings = frappe.new_doc("Modern Theme Settings")
        
        settings.default_light_theme = default_light_theme
        settings.default_dark_theme = default_dark_theme
        settings.allow_user_override = allow_user_override
        settings.force_modern_ui = force_modern_ui
        
        settings.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Modern Theme Settings saved successfully")
        }
        
    except Exception as e:
        frappe.log_error(f"Error saving modern theme settings: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


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
