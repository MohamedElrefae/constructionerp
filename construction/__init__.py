__version__ = "0.0.4"

# Apply scope-context report monkeypatch at import time.
# Wrapped in try/except so an import-time failure never breaks the app.
try:
    from construction.overrides.scope_report import apply_report_monkeypatch

    apply_report_monkeypatch()
except Exception:
    pass
