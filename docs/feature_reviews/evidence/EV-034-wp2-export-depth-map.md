# EV-034 - WP2.10 BOQ Export Depth Map

Date: 2026-06-09

## Scope

Replaced per-node BOQ export depth calculation with a precomputed parent/depth map.

## Implementation Verified

- `BOQExportService.get_tree_data(...)` now computes `depth_by_structure` once from the loaded `BOQ Structure` rows.
- The legacy `_calculate_depth(...)` method remains for compatibility but is no longer used by `get_tree_data(...)`.
- Depth resolution handles roots, children, leaves, missing parents, and cycle fallback defensively.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/services/boq_export_service.py \
  apps/construction/construction/tests/test_boq_excel_parser.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_export_depth_map_smoke
```

Result: passed.

Key returned evidence:

```json
{
  "success": true,
  "header": "BOQ-2026-0052",
  "structure_count": 3,
  "depth_by_wbs": {
    "01": 0,
    "01.01": 1,
    "01.01.001": 2
  },
  "legacy_depth_function_called": false
}
```

Cleanup verification:

```bash
bench --site v16.localhost mariadb -e "
select name from \`tabBOQ Header\` where title like 'WP2.10 Export Depth Smoke%';
"
```

Result: no rows.

## Acceptance

`WP2.10 = VER`
