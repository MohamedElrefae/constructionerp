# EV-030 - WP2.6 BOQ Excel Commit Import

Date: 2026-06-09

## Scope

Implemented `dry_run=False` BOQ Excel import commit for Draft BOQ Headers.

## Implementation Verified

- `BOQImportService.import_from_excel(..., dry_run=False)` now commits parsed preview rows into the database.
- Commit is protected by `Construction Settings.enable_boq_excel_import_commit`.
- Commit requires `confirmed_import_mode`.
- Commit is blocked unless the target `BOQ Header.status` is `Draft`.
- Commit is blocked when parser/preview returns errors.
- A `BOQ Import Batch` record is created and moved to `Committed`.
- Imported `BOQ Structure` and `BOQ Item` records receive import traceability fields.
- Commit uses normal `BOQ Structure.after_insert()` behavior to create leaf `BOQ Item` records, then updates those items.
- WBS health is run after commit.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/services/boq_import_service.py \
  apps/construction/construction/tests/test_boq_excel_parser.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_commit_smoke
```

Result: passed.

Key returned evidence:

```json
{
  "success": true,
  "header": "BOQ-2026-0043",
  "import_batch": "BOQIMP-20260609-6d43a74f",
  "batch_status": "Committed",
  "created_structure_count": 3,
  "created_item_count": 2,
  "created_wbs_codes": ["01", "01.001", "01.002"],
  "item_line_totals": [300.0, 225.0],
  "health": {
    "healthy": true,
    "summary": {
      "structures_checked": 3,
      "items_checked": 2,
      "issue_count": 0
    },
    "issues": []
  },
  "flag_block_error": "BOQ Excel commit is disabled by Construction Settings."
}
```

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_parser_smoke
```

Result: passed. Existing preview/parser behavior remained valid after adding commit.

```bash
bench --site v16.localhost mariadb -e "
select name from \`tabBOQ Header\` where title like 'WP2.6 Commit Smoke%';
select name from \`tabBOQ Import Batch\` where source_file_name like 'tmp%.xlsx' order by creation desc limit 5;
"
```

Result: no rows returned. Temporary smoke records were cleaned up.

## Acceptance

`WP2.6 = VER`

Commit import is now available behind feature flag, verified on `v16.localhost`, and traceable through `BOQ Import Batch`.
