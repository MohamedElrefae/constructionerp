"""
DEPRECATED — legacy theme-switch endpoint.

This module previously implemented its own, looser theme-switch contract that
accepted non-enum values (e.g. lowercase ``dark``) and wrote them directly to
``User.desk_theme``. That conflicting contract is eliminated: this module is now
a thin, deprecated shim that delegates entirely to the remediated
``construction.overrides.switch_theme_simple.switch_theme`` and performs NO
independent reads or writes. Both dotted routes therefore enforce exactly the
same strict contract: exact Frappe enum values (``Dark`` / ``Light`` /
``Automatic``), authentication, savepoint rollback, and no interior commit.
"""

import frappe

from construction.overrides.switch_theme_simple import switch_theme as _strict_switch_theme


@frappe.whitelist()
def switch_theme(theme=None, theme_name=None):
    """DEPRECATED: use ``construction.overrides.switch_theme_simple.switch_theme``.

    Thin compatibility shim: forwards to the strict implementation, which
    validates the theme enum, authorizes the session, wraps writes in a
    savepoint, and never commits internally. Any invalid value is rejected by
    the strict implementation (this shim cannot bypass it).
    """
    frappe.logger("switch_theme").warning(
        "Deprecated endpoint construction.overrides.switch_theme.switch_theme was "
        "called; delegating to switch_theme_simple.switch_theme."
    )
    return _strict_switch_theme(theme=theme, theme_name=theme_name)
