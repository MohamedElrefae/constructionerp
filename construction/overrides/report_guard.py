# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""Minimal, dependency-free report-scope fail-closed guard.

This module exists so that report-scope enforcement can FAIL CLOSED at worker
startup even if the full enforcement module (``construction.overrides.scope_report``)
cannot be imported (e.g. a bad edit, a missing import, or an early import error).

It deliberately has NO dependency on ``scope_report`` — it only relies on
``frappe`` — so ``construction/__init__.py`` can install the guard first and still
continue if ``scope_report`` later fails. While the guard is active, every
protected (allowlisted) report RAISES ``frappe.PermissionError``; all other
reports pass through to the original runner unchanged.

``scope_report.apply_report_monkeypatch`` upgrades this guard to the full
enforcement wrapper on success, re-using the original runner captured here.
"""

import inspect

import frappe
from frappe import _

# The plan-specified financial reports + Project-wise Profitability.
FINANCIAL_REPORTS: frozenset[str] = frozenset(
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

# Dashboard charts use Script Reports, which execute report SQL directly and
# therefore cannot rely on permission_query_conditions for row-level scope.
# Keeping them in this protected set ensures the run wrapper rewrites their
# filters before execution instead of granting broad ERPNext roles.
DASHBOARD_REPORTS: frozenset[str] = frozenset(
    {
        "Purchase Order Trends",
        "Purchase Receipt Trends",
        "Purchase Analytics",
        "Fixed Asset Register",
    }
)

# These are the only reports the backend wrapper mutates. All other reports
# pass through to the original `run` unchanged.
ALLOWED_REPORTS: frozenset[str] = FINANCIAL_REPORTS | DASHBOARD_REPORTS

# The real, un-patched ``frappe.desk.query_report.run`` captured once at startup.
_ORIGINAL_RUN = None
_ORIGINAL_RUN_SIG = None
_GUARD_INSTALLED = False


def resolve_report_name(args: tuple, kwargs: dict) -> str | None:
    """Return the report name from either a positional or keyword arg."""
    if kwargs.get("report_name"):
        return kwargs["report_name"]
    if args:
        return args[0]
    return None


def get_original_run():
    return _ORIGINAL_RUN


def get_original_run_sig():
    return _ORIGINAL_RUN_SIG


def _fail_closed_guard(*args, **kwargs):
    """Fail-closed stand-in for ``query_report.run`` while the full enforcement
    module is unavailable. Protected reports are DENIED; others pass through.

    Raises ``frappe.PermissionError`` directly (not via ``frappe.throw``) so the
    denial is robust even when no request context is bound in the process.
    """
    try:
        report_name = resolve_report_name(args, kwargs)
    except Exception:
        report_name = None
    if report_name in ALLOWED_REPORTS:
        raise frappe.PermissionError(
            _(
                "Security Error: Report scope enforcement is unavailable. "
                "Access to protected reports is denied."
            )
        )
    return _ORIGINAL_RUN(*args, **kwargs)


def install_report_guard() -> bool:
    """Capture the original runner and install the fail-closed guard.

    Returns True when the guard is active (or the original was already replaced
    by a full runner). This is deliberately callable from ``construction.__init__``
    BEFORE ``scope_report`` is imported, so the guard exists even if that import
    fails.
    """
    global _ORIGINAL_RUN, _ORIGINAL_RUN_SIG, _GUARD_INSTALLED

    try:
        from frappe.desk import query_report
    except Exception:
        # frappe.desk not importable yet — nothing we can do; the health probe
        # will report degraded. Return False so callers know.
        _GUARD_INSTALLED = False
        return False

    current = getattr(query_report.run, "__name__", "")
    if current in ("_scope_aware_run", "_fail_closed_guard"):
        # Already fully patched or already guarded — leave as is.
        _GUARD_INSTALLED = True
        return True

    try:
        _ORIGINAL_RUN = query_report.run
        _ORIGINAL_RUN_SIG = inspect.signature(_ORIGINAL_RUN)
    except Exception:
        _GUARD_INSTALLED = False
        return False

    query_report.run = _fail_closed_guard
    _GUARD_INSTALLED = True
    return True


def is_guard_active() -> bool:
    """True when the fail-closed guard is the installed query_report.run."""
    try:
        from frappe.desk import query_report
    except Exception:
        return False
    return getattr(query_report.run, "__name__", "") == "_fail_closed_guard"


def restore_fail_closed_guard() -> bool:
    """Re-install the fail-closed guard on ``query_report.run``.

    Used when the full enforcement wrapper is being installed and a step after
    assigning it fails (e.g. ``_patch_report_access_gates``), so the guard is put
    back and protected reports remain DENIED rather than being served by a
    half-installed wrapper.
    """
    global _GUARD_INSTALLED
    try:
        from frappe.desk import query_report
    except Exception:
        _GUARD_INSTALLED = False
        return False
    if _ORIGINAL_RUN is None:
        _GUARD_INSTALLED = False
        return False
    query_report.run = _fail_closed_guard
    _GUARD_INSTALLED = True
    return True


__all__ = [
    "ALLOWED_REPORTS",
    "DASHBOARD_REPORTS",
    "FINANCIAL_REPORTS",
    "get_original_run",
    "get_original_run_sig",
    "install_report_guard",
    "is_guard_active",
    "resolve_report_name",
]
