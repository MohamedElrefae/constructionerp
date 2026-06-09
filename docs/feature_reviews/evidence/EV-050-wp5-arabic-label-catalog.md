# EV-050 - WP5 Arabic Label Catalog

Date: 2026-06-09

Task: `WP5.4`

## Scope

Verify Arabic labels for BOQ, WBS, item, stage, measurement, certification, and scope terms.

## Verification

Command:

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_arabic_label_catalog_smoke
```

Result:

```json
{
  "success": true,
  "categories": {
    "boq": 3,
    "wbs": 2,
    "stage": 5,
    "measurement": 3,
    "certification": 4,
    "scope": 7
  },
  "total_labels_checked": 24
}
```

## Status

`WP5.4` can move to `VER`.
