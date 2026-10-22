# EV-038 - WP2.12 Arabic RTL Excel Export

Date: 2026-06-09

## Scope

Implemented Arabic-aware RTL Excel export for BOQ workbooks.

## Implementation Verified

- Added Arabic export helpers in `BOQExportService`.
- Arabic mode is detected from `frappe.local.lang == "ar"`.
- Full BOQ Excel worksheet title becomes `جدول الكميات`.
- `ws.sheet_view.rightToLeft = True` is applied in Arabic mode.
- BOQ-specific Arabic labels are used for:
  - WBS Code
  - Title / Description
  - Type
  - Unit
  - Quantity
  - Unit Price
  - Factor
  - Line Total
  - Ref
  - Grand Total
- Header Excel export also uses Arabic labels and RTL worksheet direction.
- Numeric cells remain real Excel numeric values with Western digits for QS/software compatibility.
- Added missing Arabic export label entries to `ar.po`.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/services/boq_export_service.py \
  apps/construction/construction/tests/test_boq_excel_parser.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_export_rtl_smoke
```

Result: passed.

Key returned evidence:

```json
{
  "success": true,
  "header": "BOQ-2026-0058",
  "sheet_title": "جدول الكميات",
  "right_to_left": true,
  "headers": [
    "كود البند",
    "الوصف",
    "النوع",
    "الوحدة",
    "الكمية",
    "سعر الوحدة",
    "المعامل",
    "إجمالي البند",
    "المرجع"
  ],
  "numeric_cells": {
    "quantity": 12.5,
    "unit_price": 100,
    "line_total": 1250
  }
}
```

Cleanup verification:

- No temporary `WP2.12 RTL Export Smoke` BOQ Header rows remained.
- No matching `File` records or private files remained after smoke cleanup.

## Acceptance

`WP2.12 = VER`
