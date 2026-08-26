"""
Simplified Theme Switch Override - SQL-based to avoid Python controller import issues
"""

import frappe
from frappe import _


@frappe.whitelist()
def switch_theme(theme_name=None):
    """
    Override Frappe's default switch_theme to handle construction themes.

    Uses SQL to avoid Python controller import issues.

    Transaction model: Frappe owns the request transaction — we do NOT commit
    here. All writes are wrapped in a savepoint so that if any step fails the
    partial state is rolled back and the client receives an error (no
    catch-and-success that hides inconsistent state).

    Args:
        theme_name: Theme name (can be Frappe standard or Construction theme)
    """
    user = frappe.session.user

    # Reject Guest/prohibited writes up front.
    if user in ("", "Guest"):
        frappe.throw(_("Not permitted to switch themes from this session."), frappe.PermissionError)

    def _authorize_user_write():
        if not frappe.has_permission("User", "write", user=user):
            if user != frappe.session.user:
                frappe.throw(
                    _("You may only switch your own theme."), frappe.PermissionError
                )

    if not theme_name:
        user_doc = frappe.get_doc("User", user)
        mode = "dark" if user_doc.desk_theme in ["Dark", "automatic"] else "light"
        return {"message": f"Theme check - current mode: {mode}", "mode": mode}

    savepoint = f"sp_switch_theme_{frappe.generate_hash(length=8)}"
    frappe.db.savepoint(savepoint)
    try:
        construction_theme = frappe.db.sql(
            """
            SELECT name, theme_type FROM `tabConstruction Theme`
            WHERE theme_name = %s AND is_active = 1
            LIMIT 1
            """,
            (theme_name,),
            as_dict=True,
        )

        if construction_theme:
            theme_record = construction_theme[0]
            is_dark = "Dark" in (theme_record.theme_type or "")
            mode = "dark" if is_dark else "light"

            # Permission-aware write to the user's own desk_theme field.
            _authorize_user_write()
            desk_theme_value = "Dark" if is_dark else "Light"
            frappe.db.set_value(
                "User", user, "desk_theme", desk_theme_value, update_modified=False
            )

            # Update or create User Desk Theme record.
            existing = frappe.db.get_value("User Desk Theme", {"user": user}, "name")
            if existing:
                udt = frappe.get_doc("User Desk Theme", existing)
                udt.inherit_from_site = 0
                udt.dark_theme = theme_record.name if is_dark else udt.dark_theme
                udt.light_theme = theme_record.name if not is_dark else udt.light_theme
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

            return {"message": f"Theme switched to {theme_name}", "mode": mode}
        else:
            mode = "dark" if theme_name in ["Dark", "Automatic"] else "light"
            _authorize_user_write()
            frappe.db.set_value("User", user, "desk_theme", mode)
            return {"message": f"Theme switched to {theme_name}", "mode": mode}
    except Exception:
        # Atomic rollback of all writes in this request; re-raise so the client
        # receives an error rather than a misleading success.
        frappe.db.rollback(save_point=savepoint)
        frappe.logger().error(f"[Theme Switch] Error for user '{user}', theme '{theme_name}'")
        raise
