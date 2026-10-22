"""
Simplified Theme Switch Override - SQL-based to avoid Python controller import issues
"""

import frappe
from frappe import _

# Frappe's core switch_theme accepts `theme` and stores these exact Select values.
_STANDARD_THEMES = frozenset({"Dark", "Light", "Automatic"})


@frappe.whitelist()
def switch_theme(theme=None, theme_name=None):
    """
    Override Frappe's default switch_theme to handle construction themes.

    Signature is API-compatible with core ``frappe.core.doctype.user.user.switch_theme``,
    which is invoked as ``switch_theme(theme=...)``. ``theme_name`` is accepted as a
    legacy alias; if both are supplied and disagree, a ValidationError is raised.

    Standard themes use the exact Frappe Select values ``Dark`` / ``Light`` /
    ``Automatic``. Construction themes are resolved by ``theme_name``.

    Transaction model: Frappe owns the request transaction — we do NOT commit.
    Writes are wrapped in a savepoint so a failure rolls back and re-raises
    (no catch-and-success). Only an authenticated, non-Guest session user may
    switch — used to switch their OWN theme.
    """
    user = frappe.session.user

    if user in ("", "Guest"):
        frappe.throw(_("Not permitted to switch themes from this session."), frappe.PermissionError)

    # Normalize the two accepted argument names, rejecting disagreement.
    if theme is not None and theme_name is not None and str(theme) != str(theme_name):
        frappe.throw(
            _("Conflicting theme arguments: theme='{0}' vs theme_name='{1}'").format(theme, theme_name),
            frappe.ValidationError,
        )
    theme_value = theme or theme_name

    if not theme_value:
        user_doc = frappe.get_doc("User", user)
        current = user_doc.desk_theme or "Light"
        mode = "dark" if current in ("Dark", "Automatic") else "light"
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
            (theme_value,),
            as_dict=True,
        )

        if construction_theme:
            theme_record = construction_theme[0]
            is_dark = "Dark" in (theme_record.theme_type or "")
            desk_theme_value = "Dark" if is_dark else "Light"
            mode = "dark" if is_dark else "light"

            frappe.db.set_value("User", user, "desk_theme", desk_theme_value, update_modified=False)

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

            return {"message": f"Theme switched to {theme_value}", "mode": mode}

        # Standard Frappe theme — preserve the exact Select enum value.
        if theme_value not in _STANDARD_THEMES:
            frappe.throw(
                _("Unknown theme '{0}'. Valid standard themes: Dark, Light, Automatic.").format(theme_value),
                frappe.ValidationError,
            )
        frappe.db.set_value("User", user, "desk_theme", theme_value)
        mode = "dark" if theme_value in ("Dark", "Automatic") else "light"
        return {"message": f"Theme switched to {theme_value}", "mode": mode}
    except Exception:
        # Atomic rollback of all writes in this request; re-raise so the client
        # receives an error rather than a misleading success.
        frappe.db.rollback(save_point=savepoint)
        frappe.logger().error(f"[Theme Switch] Error for user '{user}', theme '{theme_value}'")
        raise
