# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""
Scope Context enforcement for Query Reports (Option A+).

Monkey-patches ``frappe.desk.query_report.run`` so that restricted users
cannot bypass the active Scope Context when running the **allowlisted**
financial / operational reports.

Rules:

- If scope context is disabled, the user is Administrator, or the user
  has a finance / system role: bypass entirely.
- If the report name is **not** in :data:`ALLOWED_REPORTS`: bypass
  entirely. Only the 10 plan-specified financial reports (plus
  Project-wise Profitability if installed) are gated. Everything else
  keeps Frappe's default behaviour.
- For a restricted user running an allowlisted report: rewrite the
  filter dict to **strictly** match the active Scope Context. The
  user cannot pick a different allowed company / project / cost
  center / department than what the top-bar scope context is set to.
  This is a deliberate, conservative policy: the top bar is the
  single source of truth, the report cannot widen it.
- Filters may arrive as positional or keyword args, and as a dict,
  a JSON string, or ``None``. All four cases are normalised.
- The rewritten filter is written back in the SAME form (positional
  or keyword) the caller used. The wrapper never passes ``filters``
  to the original in both forms (which would raise
  ``TypeError: got multiple values for argument 'filters'``).
"""

import inspect
import json
import logging
from typing import Any

import frappe
from frappe import _

from construction.api.scope_context_api import (
    get_user_scope_context,
    get_user_scope_hierarchy,
)

logger = logging.getLogger(__name__)

# The 10 plan-specified financial reports + Project-wise Profitability.
# These are the only reports the backend wrapper mutates. All other
# reports pass through to the original `run` unchanged.
ALLOWED_REPORTS: frozenset[str] = frozenset(
    {
        "General Ledger",
        "Trial Balance",
        "Profit and Loss Statement",
        "Balance Sheet",
        "Accounts Payable",
        "Accounts Payable Summary",
        "Accounts Receivable",
        "Accounts Receivable Summary",
        "Budget Variance Report",
        "Cash Flow",
        "Project-wise Profitability",
    }
)

# Roles allowed to run reports without forced scope filters.
UNRESTRICTED_REPORT_ROLES: frozenset[str] = frozenset(
    {
        "System Manager",
        "Accounts Manager",
        "Accounts User",
        "Finance Manager",
    }
)

# Scope dimensions enforced by the wrapper. The keys are the canonical
# report-filter fieldnames used by ERPNext financial reports.
SCOPE_DIMENSIONS: tuple[str, ...] = (
    "company",
    "cost_center",
    "project",
    "department",
)

# Cached signature of the original run() so we can normalize positional
# args safely.
_ORIGINAL_RUN = None
_ORIGINAL_RUN_SIG = None


def apply_report_monkeypatch() -> None:
    """Replace ``frappe.desk.query_report.run`` with the scope-aware wrapper."""
    global _ORIGINAL_RUN, _ORIGINAL_RUN_SIG

    if _ORIGINAL_RUN is not None:
        return

    try:
        from frappe.desk import query_report
    except Exception:
        return

    _ORIGINAL_RUN = query_report.run
    _ORIGINAL_RUN_SIG = inspect.signature(_ORIGINAL_RUN)
    query_report.run = _scope_aware_run


# ---------------------------------------------------------------------------
# Argument normalization
# ---------------------------------------------------------------------------


def _resolve_report_name(args: tuple, kwargs: dict) -> str | None:
    """Return the report name from either a positional or keyword arg."""
    if kwargs.get("report_name"):
        return kwargs["report_name"]
    if args:
        return args[0]
    return None


def _resolve_user(args: tuple, kwargs: dict) -> str:
    """
    Return the user from either a keyword or positional arg.

    Mirrors the real Frappe signature ``run(report_name, filters=None,
    user=None, ...)`` so that callers invoking positionally — e.g.
    ``run("General Ledger", filters, "some-user@example.com")`` —
    are honoured. Falls back to ``frappe.session.user`` only when no
    explicit value is supplied.
    """
    if kwargs.get("user"):
        return kwargs["user"]
    if _ORIGINAL_RUN_SIG is None:
        return frappe.session.user
    try:
        bound = _ORIGINAL_RUN_SIG.bind_partial(*args, **kwargs)
        bound_user = bound.arguments.get("user")
        if bound_user:
            return bound_user
    except TypeError:
        # Caller passed something we cannot bind; fall through to session.
        pass
    return frappe.session.user


def _normalize_filters(args: tuple, kwargs: dict):
    """
    Return ``(new_args, new_kwargs, filters_value)`` after parsing
    the caller's ``filters`` argument into a Python dict.

    Strategy: detect the original transport (positional or keyword)
    and pass `filters` back in the SAME form after rewriting.
    """
    sig = _ORIGINAL_RUN_SIG
    if sig is None:
        return args, kwargs, {}

    try:
        bound = sig.bind_partial(*args, **kwargs)
    except TypeError:
        return args, kwargs, {}

    bound.apply_defaults()

    raw = bound.arguments.get("filters")
    if raw is None:
        parsed: dict[str, Any] = {}
    elif isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                parsed = {}
        except Exception:
            parsed = {}
    elif isinstance(raw, dict):
        parsed = dict(raw)
    else:
        parsed = {}

    # Detect the underlying signature. If the function has a named
    # `filters` parameter, we must respect its slot. Otherwise (e.g.
    # `*args, **kwargs`), we can pass `filters` as a kwarg.
    filters_index = None
    for i, p in enumerate(sig.parameters.values()):
        if p.name == "filters":
            filters_index = i
            break

    new_args = bound.args
    new_kwargs = dict(bound.kwargs)

    if filters_index is not None and filters_index < len(new_args):
        # Strict signature. The filters value is in new_args at
        # filters_index. Keep it there. Do NOT also put it in new_kwargs.
        if new_args[filters_index] is not parsed:
            new_args = (
                *new_args[:filters_index],
                parsed,
                *new_args[filters_index + 1:],
            )
        new_kwargs = {k: v for k, v in new_kwargs.items() if k != "filters"}
    else:
        # *args, **kwargs signature. Pass `filters` only via kwargs.
        if "filters" in new_args:
            new_args = tuple(a for a in new_args if a is not raw and a is not parsed)
        new_kwargs["filters"] = parsed

    return new_args, new_kwargs, parsed


# ---------------------------------------------------------------------------
# Scope enforcement
# ---------------------------------------------------------------------------


def _has_unrestricted_report_role(user: str) -> bool:
    """Return True if the user has any role that bypasses report scope enforcement."""
    user_roles = set(frappe.get_roles(user))
    return bool(user_roles & UNRESTRICTED_REPORT_ROLES)


def _enforce_scope_filters_strict(filters: dict, user: str) -> dict:
    """
    Force scope-dimension filters to the user's **active** Scope Context.

    Policy:
      - Company: scalar, always the active scope value.
      - Cost Center: list, always `[scope.cost_center, *descendants]`.
      - Project: list, always `[scope.project]` (or `[]` if none).
      - Department: list, always `[scope.department]` (or `[]` if none).
      - A restricted user cannot widen any filter beyond the top bar.

    If the user has no Scope Context record at all, the dimension is
    left as `None` so the report's own validation (or its required
    filter) catches the missing value. This is the safe default.
    """
    scope_doc = get_user_scope_context(user)
    scope = {
        "company": scope_doc.company if scope_doc else None,
        "cost_center": scope_doc.cost_center if scope_doc else None,
        "project": scope_doc.project if scope_doc else None,
        "department": scope_doc.department if scope_doc else None,
    }

    # Hierarchy is consulted only for cost-center descendant expansion.
    hierarchy = get_user_scope_hierarchy(user) if scope_doc else {}
    cost_centers_index = {cc["name"]: cc for cc in hierarchy.get("cost_centers", [])}

    for dimension in SCOPE_DIMENSIONS:
        scoped_value = scope.get(dimension)

        if dimension == "cost_center" and scoped_value:
            # Build the strict list = scoped value + descendants via lft/rgt.
            scoped_node = cost_centers_index.get(scoped_value)
            if scoped_node:
                lft, rgt = scoped_node.get("lft"), scoped_node.get("rgt")
                if lft is not None and rgt is not None:
                    descendants = [
                        cc["name"]
                        for cc in hierarchy.get("cost_centers", [])
                        if cc.get("lft") is not None
                        and cc.get("rgt") is not None
                        and cc["lft"] >= lft
                        and cc["rgt"] <= rgt
                    ]
                else:
                    descendants = [scoped_value]
            else:
                descendants = [scoped_value]
            filters[dimension] = descendants
        elif dimension == "cost_center":
            # No scope or cost_center is empty — strict list is empty.
            filters[dimension] = []
        elif dimension == "company":
            # Company is always scalar (Link field) in ERPNext reports.
            filters[dimension] = scoped_value
        elif dimension == "project":
            # Project is MultiSelectList. Always present as a list.
            filters[dimension] = [scoped_value] if scoped_value else []
        elif dimension == "department":
            # Department is MultiSelectList.
            filters[dimension] = [scoped_value] if scoped_value else []

    return filters


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def _scope_aware_run(*args, **kwargs):
    """The patched entry point. Delegates to the original after filtering."""
    if _ORIGINAL_RUN is None:
        raise RuntimeError("Original query_report.run was not captured")

    # 1. Resolve the report name early so we can decide on enforcement.
    report_name = _resolve_report_name(args, kwargs)

    # 2. Bypass when scope context is disabled.
    try:
        settings = frappe.get_single("Construction Settings")
        if not settings or not settings.enable_scope_context:
            return _ORIGINAL_RUN(*args, **kwargs)
    except Exception:
        # If settings are unavailable, do not break the report.
        return _ORIGINAL_RUN(*args, **kwargs)

    # 3. Bypass for Administrator.
    user = _resolve_user(args, kwargs)
    if user == "Administrator":
        return _ORIGINAL_RUN(*args, **kwargs)

    # 4. Bypass for unrestricted finance / system roles.
    if _has_unrestricted_report_role(user):
        return _ORIGINAL_RUN(*args, **kwargs)

    # 5. Bypass for non-allowlisted reports. This is the critical
    #    Option A+ invariant: only the 10 plan-specified reports
    #    are gated. Everything else keeps Frappe's default behaviour.
    if report_name not in ALLOWED_REPORTS:
        return _ORIGINAL_RUN(*args, **kwargs)

    # 6. Normalise positional / keyword args so we can read filters
    #    regardless of how the caller invoked the function. The
    #    normalizer returns the location of the filters value so the
    #    rewritten value lands in exactly one place.
    new_args, new_kwargs, filters = _normalize_filters(args, kwargs)

    # 7. Enforce strict active-scope policy.
    filters = _enforce_scope_filters_strict(filters, user)

    # 8. Write the rewritten `filters` back to its proper slot. If the
    #    function has a strict signature with a named `filters`
    #    parameter, the value lives in new_args at filters_index; if
    #    not, it lives in new_kwargs. We always check both and
    #    update whichever is the canonical slot.
    sig = _ORIGINAL_RUN_SIG
    if sig is not None:
        filters_index = None
        for i, p in enumerate(sig.parameters.values()):
            if p.name == "filters":
                filters_index = i
                break
        if filters_index is not None and filters_index < len(new_args):
            new_args = (
                *new_args[:filters_index],
                filters,
                *new_args[filters_index + 1:],
            )
            if "filters" in new_kwargs:
                new_kwargs = {k: v for k, v in new_kwargs.items() if k != "filters"}
        else:
            new_kwargs["filters"] = filters

    return _ORIGINAL_RUN(*new_args, **new_kwargs)
