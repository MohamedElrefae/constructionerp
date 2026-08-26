__version__ = "0.0.5"

# ─────────────────────────────────────────────────────────────────────────
# Report-scope enforcement — FAIL CLOSED at startup.
#
# Order matters: the minimal, dependency-free guard (overrides/report_guard)
# is installed FIRST so it is in place even if the full enforcement module
# (overrides/scope_report) cannot be imported. While the guard is active,
# protected reports are DENIED (never served unscoped). scope_report's
# apply_report_monkeypatch() then UPGRADES that guard to the full wrapper on
# success; on any failure the guard remains.
#
# Health probe: construction.overrides.scope_report.report_enforcement_health()
# ─────────────────────────────────────────────────────────────────────────

# 1. Install the fail-closed guard from a module with no scope_report dependency.
try:
    from construction.overrides.report_guard import install_report_guard

    _GUARD_OK = install_report_guard()
except Exception:
    _GUARD_OK = False

# 2. Attempt the full enforcement wrapper (upgrades the guard on success).
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

if _REPORT_ENFORCEMENT_OK:
    # Full enforcement active — nothing else to do.
    pass
elif _GUARD_OK:
    try:
        import frappe

        if hasattr(frappe, "log_error"):
            frappe.log_error(
                "Report scope enforcement DEGRADED at startup: the fail-closed guard is active and "
                "protected reports are DENIED. Run "
                "construction.overrides.scope_report.report_enforcement_health() to inspect.",
                "Scope Report Monkeypatch",
            )
    except Exception:
        pass
else:
    try:
        import frappe

        if hasattr(frappe, "log_error"):
            frappe.log_error(
                "Report scope enforcement COULD NOT BE INSTALLED (neither guard nor wrapper). "
                "If protected reports are reachable, scope isolation is DISABLED. Investigate "
                "immediately.",
                "Scope Report Monkeypatch",
            )
    except Exception:
        pass
