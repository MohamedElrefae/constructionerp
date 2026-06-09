# EV-032 - WP2.8 BOQ Import Error Report Workbook

Date: 2026-06-09

## Scope

Generated an Excel import review workbook with explicit `Error` and `Warning` columns.

## Implementation Verified

- Added `BOQImportService.generate_import_error_report(...)`.
- Added API method `generate_boq_import_error_report(...)`.
- Report workbook contains:
  - `Import Review` worksheet
  - `Summary` worksheet
  - source row/sheet fields
  - normalized BOQ fields
  - detected type
  - proposed WBS/parent
  - `Error`
  - `Warning`
- Report files are private and attached through a `File` record.
- Unmanaged pre-insert workbook residue is deleted after Frappe stores the private file.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/services/boq_import_service.py \
  apps/construction/construction/api/boq_api.py \
  apps/construction/construction/tests/test_boq_excel_parser.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_error_report_smoke
```

Result: passed.

Key returned evidence:

```json
{
  "success": true,
  "header": "BOQ-2026-0050",
  "file_url": "/private/files/BOQ_Import_Error_Report_BOQ-2026-0050_20260609_222524079f1c.xlsx",
  "sheet_names": ["Import Review", "Summary"],
  "row_count": 2,
  "error_cells": [
    "parent_wbs_not_found: Parent WBS 50 was not found in the uploaded file or target Draft BOQ.",
    "parent_wbs_not_found: Parent WBS 50 was not found in the uploaded file or target Draft BOQ."
  ],
  "warning_cells": [
    "adjacent_duplicate_item: Adjacent row has identical description, unit, quantity, and rate."
  ],
  "is_private": 1,
  "summary": {
    "row_count": 2,
    "item_count": 2,
    "error_count": 2,
    "warning_count": 1
  }
}
```

```bash
find sites/v16.localhost/private/files -maxdepth 1 -name 'BOQ_Import_Error_Report_*' -print | tail -5
```

Result: no rows after smoke cleanup.

## Acceptance

`WP2.8 = VER`
