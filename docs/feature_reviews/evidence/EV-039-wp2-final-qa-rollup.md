# EV-039 - WP2.13 BOQ Excel Import/Export Final QA Rollup

Date: 2026-06-09

## Scope

Ran final WP2 import/export QA after completing `WP2.1` through `WP2.12`.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/services/boq_import_service.py \
  apps/construction/construction/services/boq_export_service.py \
  apps/construction/construction/api/boq_api.py \
  apps/construction/construction/tests/test_boq_excel_parser.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_parser_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_commit_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_duplicate_import_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_error_report_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_import_policy_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_export_depth_map_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_export_privacy_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_export_rtl_smoke
```

Result: all passed.

## Coverage Verified

- Structured, semi-structured, flat, Arabic-header, ambiguous-row, parent validation, and WBS collision preview.
- Draft-only commit with import batch traceability.
- Duplicate re-import and stale-preview duplicate guard.
- Import error report workbook with populated `Error` and `Warning` columns.
- File-size, row-count, and async threshold policy.
- Export depth precomputed map.
- Private Excel/PDF export URLs and `File.is_private = 1`.
- Arabic RTL Excel export with BOQ-specific Arabic labels and Western numeric Excel cells.

## Cleanup Verification

```bash
bench --site v16.localhost mariadb -e "
select name, title from \`tabBOQ Header\`
where title like 'WP2.%Smoke%' or title like 'WP2.% Smoke%';
select field, value from \`tabSingles\`
where doctype='Construction Settings' and field='enable_boq_excel_import_commit';
"
```

Result:

- No temporary WP2 smoke BOQ Header rows remained.
- `enable_boq_excel_import_commit = 0`.

```bash
find sites/v16.localhost/private/files -maxdepth 1 \( -name '*BOQ-2026-0060*' -o -name '*BOQ-2026-0063*' -o -name '*BOQ-2026-0065*' -o -name '*BOQ-2026-0066*' -o -name '*BOQ-2026-0067*' -o -name '*BOQ-2026-0069*' -o -name '*BOQ-2026-0071*' \) -print
```

Result: no files.

```bash
bench --site v16.localhost mariadb -e "
select file_url from \`tabFile\`
where file_url regexp 'BOQ-2026-(0060|0063|0065|0066|0067|0069|0071)';
"
```

Result: no rows.

## Frappe Test Runner Note

```bash
bench --site v16.localhost run-tests --app construction --module construction.tests.test_boq_excel_parser
```

Result: blocked before reaching the construction test module by existing ERPNext Fiscal Year bootstrap overlap:

```text
Year start date or end date is overlapping with Fiscal Year 2025-2026.
```

This is recorded as an environment/bootstrap blocker, not a WP2 construction failure.

## Acceptance

`WP2.13 = VER`

WP2 is functionally verified through direct bench execution smokes and cleanup checks.
