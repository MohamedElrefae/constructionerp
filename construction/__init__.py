import frappe

__version__ = "0.0.5"

# ─────────────────────────────────────────────────────────────────────────
# Report-scope enforcement — FAIL CLOSED at startup.
#
# The minimal, dependency-free guard (overrides/report_guard) is installed
# FIRST so it is in place even if the full enforcement module
# (overrides/scope_report) cannot be imported. scope_report's
# apply_report_monkeypatch() UPGRADES that guard to the full wrapper on
# success; on any failure the guard remains.
#
# FAIL-CLOSED policy: if the guard itself cannot be imported or installed,
# OR the original runner cannot be captured, this is a FATAL startup error —
# the application refuses to become ready (raises) rather than serving
# protected reports unscoped. Log-and-continue is NOT acceptable here.
#
# Health probe: construction.overrides.scope_report.report_enforcement_health()
# ─────────────────────────────────────────────────────────────────────────


class ReportScopeEnforcementError(RuntimeError):
    """Fatal startup error: report-scope enforcement could not be installed.

    Raised when neither the fail-closed guard nor the full enforcement wrapper
    can be installed, so protected reports would otherwise be served without
    tenant filtering.
    """


# 1. Install the fail-closed guard. Failure here is FATAL.
_guard_error = None
try:
    from construction.overrides.report_guard import install_report_guard, is_guard_active

    _GUARD_OK = install_report_guard()
    if not _GUARD_OK:
        _guard_error = (
            "report_guard.install_report_guard() returned False; the original "
            "query_report.run could not be captured or the guard could not be installed."
        )
except Exception as e:
    _GUARD_OK = False
    _guard_error = f"report_guard could not be imported/installed: {e}"

if not _GUARD_OK:
    raise ReportScopeEnforcementError(
        "FATAL: report scope enforcement is unavailable and no fail-closed guard "
        f"could be installed. Refusing startup. {_guard_error}"
    )

# 2. Attempt the full enforcement wrapper (upgrades the guard on success).
try:
    from construction.overrides.scope_report import apply_report_monkeypatch

    _REPORT_ENFORCEMENT_OK = apply_report_monkeypatch()
except Exception as e:
    _REPORT_ENFORCEMENT_OK = False
    _guard_error = str(e)

if _REPORT_ENFORCEMENT_OK:
    # Full enforcement active — nothing else to do.
    pass
else:
    # Guard is active (degraded mode): protected reports are DENIED. This is a
    # safe state, not a fatal one. Surface it loudly for operators.
    import frappe

    if hasattr(frappe, "log_error"):
        frappe.log_error(
            "Report scope enforcement DEGRADED at startup: the fail-closed guard is active "
            f"and protected reports are DENIED. {_guard_error}",
            "Scope Report Monkeypatch",
        )


try:
    from construction.translation_loader import is_translation_loader_installed  # noqa: F401
except Exception as e:
    import frappe as _f

    try:
        _f.log_error(f"Translation loader import failed: {e}", "Translation Loader")
    except Exception:
        pass
