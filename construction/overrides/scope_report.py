# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""
Scope Context enforcement for Query Reports.

Monkey-patches frappe.desk.query_report.run so that restricted users cannot
bypass the active scope context when running financial/operational reports.

Rules:
- If scope context is disabled or user is Administrator: bypass.
- If user has a finance/unrestricted role: bypass.
- Otherwise, force report filters to the user's active scope context,
  intersecting multi-select values with allowed hierarchy values.
"""

import json

import frappe
from frappe import _

from construction.api.scope_context_api import get_user_scope_context, get_user_scope_hierarchy

SCOPE_DIMENSIONS = ("company", "cost_center", "project", "department")

# Roles that are allowed to run reports without forced scope filters.
# These roles are expected to have read access to Company/Project/Cost Center.
UNRESTRICTED_REPORT_ROLES = {
    "System Manager",
    "Accounts Manager",
    "Accounts User",
    "Finance Manager",
}

_ORIGINAL_RUN = None


def apply_report_monkeypatch():
    """Replace frappe.desk.query_report.run with the scope-aware wrapper."""
    global _ORIGINAL_RUN

    if _ORIGINAL_RUN is not None:
        return

    try:
        from frappe.desk import query_report
    except Exception:
        return

    _ORIGINAL_RUN = query_report.run
    query_report.run = _scope_aware_run


def _scope_aware_run(*args, **kwargs):
    """Wrapper that enforces scope context before delegating to the original runner."""
    if _ORIGINAL_RUN is None:
        raise RuntimeError("Original query_report.run was not captured")

    # Only enforce when scope context is enabled and user is not Administrator.
    settings = frappe.get_single("Construction Settings")
    if not settings or not settings.enable_scope_context:
        return _ORIGINAL_RUN(*args, **kwargs)

    user = kwargs.get("user") or frappe.session.user
    if user == "Administrator":
        return _ORIGINAL_RUN(*args, **kwargs)

    if _has_unrestricted_report_role(user):
        return _ORIGINAL_RUN(*args, **kwargs)

    # Parse/normalize filters so we can enforce scope on them.
    filters = kwargs.get("filters")
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = {}
    elif filters is None:
        filters = {}

    filters = _enforce_scope_filters(filters, user)
    kwargs["filters"] = filters

    return _ORIGINAL_RUN(*args, **kwargs)


def _has_unrestricted_report_role(user):
    """Return True if the user has any role that bypasses report scope enforcement."""
    user_roles = set(frappe.get_roles(user))
    return bool(user_roles & UNRESTRICTED_REPORT_ROLES)


def _enforce_scope_filters(filters, user):
    """Force scope-dimension filters to the user's active scope context."""
    scope_doc = get_user_scope_context(user)
    scope = {
        "company": scope_doc.company if scope_doc else None,
        "cost_center": scope_doc.cost_center if scope_doc else None,
        "project": scope_doc.project if scope_doc else None,
        "department": scope_doc.department if scope_doc else None,
    }

    hierarchy = get_user_scope_hierarchy(user)
    allowed = {
        "company": {c["name"] for c in hierarchy.get("companies", [])},
        "cost_center": {cc["name"] for cc in hierarchy.get("cost_centers", [])},
        "project": {p["name"] for p in hierarchy.get("projects", [])},
        "department": {d["name"] for d in hierarchy.get("departments", [])},
    }

    for dimension in SCOPE_DIMENSIONS:
        scoped_value = scope.get(dimension)
        allowed_values = allowed.get(dimension)
        incoming = filters.get(dimension)

        if incoming is not None:
            # MultiSelectList filters may arrive as a list; intersect with allowed values.
            if isinstance(incoming, list):
                intersected = [v for v in incoming if v in allowed_values]
                if intersected:
                    filters[dimension] = intersected
                elif scoped_value:
                    filters[dimension] = scoped_value
                else:
                    filters[dimension] = []
            elif incoming in allowed_values:
                filters[dimension] = incoming
            elif scoped_value:
                filters[dimension] = scoped_value
            else:
                filters[dimension] = None
        elif scoped_value:
            # Inject the scoped value so users cannot view cross-organization data.
            filters[dimension] = scoped_value

    return filters
