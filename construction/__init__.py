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


# ─────────────────────────────────────────────────────────────────────────
# Translation catalog runtime optimization.
#
# The Construction app can seed every msgid from the Arabic .po files into
# ``tabTranslation`` as catalog rows so users can edit any UI string from the
# Translation list. Catalog rows are not needed at runtime because the .mo
# catalog already supplies the same strings, so we exclude them from the
# in-memory user-translations dict to keep worker memory flat and boot fast.
# ─────────────────────────────────────────────────────────────────────────

try:
    import frappe.translate as _translate

    def _get_user_translations_excluding_catalog(lang: str):
        """Load user translations but skip auto-created catalog entries.

        Manual overrides (ct_is_catalog_entry = 0 or field absent) are still
        loaded, so user edits take precedence over the .mo catalog.
        """
        if not lang:
            return {}

        def _read_from_db():
            user_translations = {}
            # Field may not exist until the first migrate/patch runs; fall back
            # gracefully to an unfiltered read if the column is missing. At that
            # point no catalog rows exist yet, so the result is equivalent.
            try:
                rows = frappe.get_all(
                    "Translation",
                    fields=["source_text", "translated_text", "context"],
                    filters={
                        "language": lang,
                        "ct_is_catalog_entry": 0,
                    },
                )
            except Exception:
                rows = frappe.get_all(
                    "Translation",
                    fields=["source_text", "translated_text", "context"],
                    filters={"language": lang},
                )

            for t in rows:
                key = t.source_text
                if t.context:
                    key += ":" + t.context
                user_translations[key] = t.translated_text
            return user_translations

        return frappe.cache.hget(
            _translate.USER_TRANSLATION_KEY, lang, generator=_read_from_db
        )

    _translate.get_user_translations = _get_user_translations_excluding_catalog
except Exception:
    # Do not block startup if the optimization cannot be installed.
    pass
