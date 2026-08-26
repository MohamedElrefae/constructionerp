__version__ = "0.0.5"

# Apply scope-context report enforcement at import time.
#
# Fail-closed architecture: apply_report_monkeypatch() installs a
# DENY-protected-reports guard FIRST and only swaps in the full
# enforcement wrapper when installation succeeds completely. If this
# import fails outright, protected reports remain denied (never served
# unscoped). Health probe: construction.overrides.scope_report.report_enforcement_health()
try:
    from construction.overrides.scope_report import apply_report_monkeypatch

    _REPORT_ENFORCEMENT_OK = apply_report_monkeypatch()
except Exception as e:
    _REPORT_ENFORCEMENT_OK = False
    import frappe

    if hasattr(frappe, "log_error"):
        frappe.log_error(
            f"CRITICAL: Report scope enforcement failed to install; protected reports are DENIED: {e}",
            "Scope Report Monkeypatch",
        )

if not _REPORT_ENFORCEMENT_OK:
    try:
        import frappe

        if hasattr(frappe, "log_error"):
            frappe.log_error(
                "Report scope enforcement DEGRADED at startup: protected reports are denied "
                "until workers restart with corrected code. Run "
                "construction.overrides.scope_report.report_enforcement_health() to inspect.",
                "Scope Report Monkeypatch",
            )
    except Exception:
        pass
