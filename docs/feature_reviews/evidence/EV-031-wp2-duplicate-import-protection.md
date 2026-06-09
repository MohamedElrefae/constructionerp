# EV-031 - WP2.7 Duplicate Import Protection

Date: 2026-06-09

## Scope

Added commit-time duplicate WBS protection for BOQ Excel imports.

## Implementation Verified

- Commit now locks the target `BOQ Header` row with `SELECT ... FOR UPDATE` before final WBS validation.
- Commit validates that proposed import WBS codes are present and unique inside the preview payload.
- Commit validates that proposed WBS codes do not already exist in the target Draft BOQ immediately before creating an import batch.
- Existing dry-run structured WBS collision validation remains active.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/services/boq_import_service.py \
  apps/construction/construction/tests/test_boq_excel_parser.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_duplicate_import_smoke
```

Result: passed.

Key returned evidence:

```json
{
  "success": true,
  "header": "BOQ-2026-0046",
  "first_import_batch": "BOQIMP-20260609-9b67bf94",
  "second_import_blocked": true,
  "second_import_error": "BOQ Excel import has blocking errors and cannot be committed.",
  "stale_preview_blocked": true,
  "stale_preview_error": "Cannot commit BOQ Excel import because WBS code(s) already exist in this Draft BOQ: 88.",
  "import_batch_count": 1
}
```

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_parser_smoke
```

Result: passed. Existing preview/parser behavior remained valid.

```bash
bench --site v16.localhost mariadb -e "
select name from \`tabBOQ Header\` where title like 'WP2.7 Duplicate Import Smoke%';
select field, value from \`tabSingles\` where doctype='Construction Settings' and field='enable_boq_excel_import_commit';
"
```

Result:

- No temporary `WP2.7 Duplicate Import Smoke` BOQ Header rows remained.
- `enable_boq_excel_import_commit = 0`.

## Acceptance

`WP2.7 = VER`
