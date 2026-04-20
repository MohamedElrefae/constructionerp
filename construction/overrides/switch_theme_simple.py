"""
Simplified Theme Switch Override - SQL-based to avoid Python controller import issues
"""
import frappe


@frappe.whitelist()
def switch_theme(theme_name=None):
    """
    Override Frappe's default switch_theme to handle construction themes.
    Uses SQL to avoid Python controller import issues.
    
    Args:
        theme_name: Theme name (can be Frappe standard or Construction theme)
    """
    # Handle missing theme_name
    if not theme_name:
        # Get current mode and return success
        user = frappe.session.user
        user_doc = frappe.get_doc("User", user)
        mode = "dark" if user_doc.desk_theme in ["Dark", "automatic"] else "light"
        return {"message": f"Theme check - current mode: {mode}", "mode": mode}
    user = frappe.session.user
    
    try:
        # Check if this is a construction theme using SQL
        construction_theme = frappe.db.sql("""
            SELECT name, theme_type FROM `tabConstruction Theme`
            WHERE theme_name = %s AND is_active = 1
            LIMIT 1
        """, (theme_name,), as_dict=True)
        
        if construction_theme:
            # It's a construction theme - persist to User Desk Theme
            theme_record = construction_theme[0]
            is_dark = 'Dark' in (theme_record.theme_type or '')
            mode = 'dark' if is_dark else 'light'
            
            # Update User.desk_theme
            desk_theme_value = "Dark" if is_dark else "Light"
            frappe.db.set_value("User", user, "desk_theme", desk_theme_value, update_modified=False)
            
            # Update or create User Desk Theme record
            existing = frappe.db.get_value("User Desk Theme", {"user": user}, "name")
            if existing:
                udt = frappe.get_doc("User Desk Theme", existing)
                udt.inherit_from_site = 0
                if is_dark:
                    udt.dark_theme = theme_record.name
                else:
                    udt.light_theme = theme_record.name
                udt.save(ignore_permissions=True)
            else:
                udt = frappe.new_doc("User Desk Theme")
                udt.user = user
                udt.inherit_from_site = 0
                if is_dark:
                    udt.dark_theme = theme_record.name
                else:
                    udt.light_theme = theme_record.name
                udt.insert(ignore_permissions=True)
            
            frappe.db.commit()
            return {"message": f"Theme switched to {theme_name}", "mode": mode}
        else:
            # It's a standard Frappe theme (Light/Dark)
            # Map to mode
            mode = "dark" if theme_name in ["Dark", "Automatic"] else "light"
            frappe.db.set_value("User", user, "desk_theme", mode)
            
            return {"message": f"Theme switched to {theme_name}", "mode": mode}
            
    except Exception as e:
        frappe.logger().error(f"[Theme Switch] Error: {str(e)}")
        # Fallback to just setting desk_theme
        mode = "dark" if "dark" in theme_name.lower() else "light"
        frappe.db.set_value("User", user, "desk_theme", mode)
        return {"message": f"Theme switched to {mode}", "mode": mode}
