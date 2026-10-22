# EV-033 - WP2.9 BOQ Import File Size, Row Count, and Async Threshold Policy

Date: 2026-06-09

## Scope

Added explicit BOQ Excel import guardrails for file size, row count, and synchronous import threshold.

## Policy Implemented

- `MAX_IMPORT_FILE_SIZE_BYTES = 25 MB`
- `MAX_IMPORT_ROW_COUNT = 10000`
- `ASYNC_IMPORT_ROW_THRESHOLD = 2000`

## Behavior

- File size above hard limit returns `file_size_limit_exceeded`.
- Row count above hard limit returns `row_count_limit_exceeded`.
- Row count above synchronous threshold remains previewable but returns:
  - `import_policy.requires_async = true`
  - warning code `async_import_required`
- Synchronous `dry_run=False` commit is blocked when `requires_async = true`.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/services/boq_import_service.py \
  apps/construction/construction/tests/test_boq_excel_parser.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_import_policy_smoke
```

Result: passed.

Key returned evidence:

```json
{
  "success": true,
  "header": "BOQ-2026-0051",
  "async_preview_success": true,
  "async_requires_async": true,
  "async_warning_codes": ["async_import_required"],
  "async_commit_error": "This BOQ Excel import exceeds the synchronous row threshold and must use async import.",
  "row_limit_error_codes": ["row_count_limit_exceeded"],
  "file_limit_error_codes": ["file_size_limit_exceeded"]
}
```

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_parser_smoke
```

Result: passed.

Cleanup verification:

- No temporary `WP2.9 Import Policy Smoke` BOQ Header rows remained.
- `enable_boq_excel_import_commit = 0`.

## Acceptance

`WP2.9 = VER`
