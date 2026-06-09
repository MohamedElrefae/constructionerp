# EV-035 - WP2.11 BOQ Export Privacy Normalization

Date: 2026-06-09

## Scope

Normalized BOQ Excel/PDF export privacy and file URLs.

## Implementation Verified

- Header Excel export now stores private files under `/private/files/...`.
- Full BOQ Excel export now stores private files under `/private/files/...`.
- Header PDF export now stores private files under `/private/files/...`.
- Full BOQ PDF export now stores private files under `/private/files/...`.
- All four export paths create `File` records with `is_private = 1`.
- Unmanaged pre-insert file copies are removed after Frappe creates the final stored private file.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/services/boq_export_service.py \
  apps/construction/construction/tests/test_boq_excel_parser.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_export_privacy_smoke
```

Result: passed.

Key returned evidence:

```json
{
  "success": true,
  "header": "BOQ-2026-0054",
  "exports": [
    {
      "label": "header_excel",
      "file_url": "/private/files/BOQ_Header_BOQ-2026-0054_20260609_222956383e53.xlsx",
      "is_private": 1,
      "exists": true
    },
    {
      "label": "full_excel",
      "file_url": "/private/files/BOQ_BOQ-2026-0054_20260609_2229569516d6.xlsx",
      "is_private": 1,
      "exists": true
    },
    {
      "label": "header_pdf",
      "file_url": "/private/files/BOQ_Header_BOQ-2026-0054_20260609_222957739bb7.pdf",
      "is_private": 1,
      "exists": true
    },
    {
      "label": "full_pdf",
      "file_url": "/private/files/BOQ_BOQ-2026-0054_20260609_222958c33e45.pdf",
      "is_private": 1,
      "exists": true
    }
  ]
}
```

Cleanup verification:

- No temporary `WP2.11 Export Privacy Smoke` BOQ Header rows remained.
- No `/files/...` or `/private/files/...` export files for the smoke BOQ remained after cleanup.
- No matching `File` records remained.

## Acceptance

`WP2.11 = VER`
