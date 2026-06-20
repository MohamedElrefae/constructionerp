# Consultant Review Response - BOQ Excel Import Finish Scope

Date: 2026-06-16

## Status

The four consultant follow-up items from the BOQ Excel import finish review were implemented in the working tree and verified against `v16.localhost`.

## Completed Items

### P1.1 Commit failure savepoint / rollback

Implemented in `construction/services/boq_import_service.py`.

- Added a database savepoint before the structure/item mutation loop.
- On mutation failure, rolls back to the savepoint.
- Preserves the `BOQ Import Batch` row as `Failed`.
- Stores the exception text in `BOQ Import Batch.error_message`.
- Added smoke coverage that injects a mid-import failure and verifies:
  - no partial `BOQ Structure` rows remain,
  - no partial `BOQ Item` rows remain,
  - the failed batch remains available with `error_message`.

### P1.2 BOQ Header authorization for import APIs

Implemented in `construction/api/boq_api.py`.

- Added `_assert_boq_header_access()`.
- `import_boq_excel()` now checks:
  - read access for preview,
  - write access for commit,
  - project scope access through the existing scope hierarchy pattern.
- `generate_boq_import_error_report()` now checks read/scope access when a BOQ Header is supplied.
- `get_boq_import_status()` now also checks `BOQ Import Batch` read permission and BOQ Header read/scope access.

### P2.1 Status API returns failed-batch error message

Implemented in `construction/services/boq_import_service.py`.

- `get_import_status()` now returns `error_message`.
- Smoke coverage verifies the field through the status API response.

### P2.2 Preview-only UI visible when preview is enabled

Implemented in:

- `construction/api/boq_api.py`
- `construction/construction/doctype/boq_header/boq_header.js`

Changes:

- `is_boq_excel_import_enabled()` now returns `enabled = preview_enabled`.
- `commit_enabled` remains available separately for the future preview-then-commit UI.
- BOQ Header dialog copy no longer tells users to call the API directly.

## Verification

Static checks:

```bash
ruff format --check construction/api/boq_api.py construction/services/boq_import_service.py construction/tests/test_boq_import_status_smoke.py
ruff check construction/api/boq_api.py construction/services/boq_import_service.py construction/tests/test_boq_import_status_smoke.py
python3 -m py_compile construction/api/boq_api.py construction/services/boq_import_service.py construction/tests/test_boq_import_status_smoke.py
node --check construction/construction/doctype/boq_header/boq_header.js
```

Result: passed.

Frappe smoke checks:

```bash
bench --site v16.localhost execute construction.tests.test_boq_import_status_smoke.run
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_parser_smoke
```

Result: passed.

Notable smoke evidence:

- `helper_partial` now returns `enabled: true`, `preview_enabled: true`, `commit_enabled: false`.
- Injected rollback failure returns the expected failure.
- Rollback counts after injected failure are `structures: 0`, `items: 0`.
- Failed batch remains available with `error_message`.

## Updated Verdict

The four P1/P2 consultant concerns are now resolved in code and smoke-tested. The remaining larger deferred items are still product scope decisions, not contradictions in the current implementation:

- async large-file import,
- full preview-then-commit UI,
- optional status UI surface.
