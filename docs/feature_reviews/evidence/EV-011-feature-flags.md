# EV-011: Construction Settings Rollout Flags

Date: 2026-06-09

Task: `T0.5`

## Implementation

Added seven Improve Now rollout flags to `Construction Settings`:

- `enable_boq_excel_import_preview`
- `enable_boq_excel_import_commit`
- `enable_boq_wbs_resequence`
- `enable_stage_measurement_ui`
- `enable_boq_scope_registry`
- `enable_bilingual_boq_print`
- `enable_variation_orders`

All flags default to `0`.

Added shared Python runtime helper:

`/home/mohamed/frappe-bench/apps/construction/construction/services/feature_flags.py`

## Migration

First migrate attempt failed because bench services were not running:

```text
Service redis_cache is not running.
Cannot run bench migrate without the services running.
```

Bench services were started with:

```bash
bench start
```

Then migration succeeded:

```bash
bench --site v16.localhost migrate
```

## Runtime Verification

Command:

```bash
bench --site v16.localhost execute construction.services.feature_flags.get_flags
```

Result:

```json
{
  "enable_bilingual_boq_print": false,
  "enable_boq_excel_import_commit": false,
  "enable_boq_excel_import_preview": false,
  "enable_boq_scope_registry": false,
  "enable_boq_wbs_resequence": false,
  "enable_stage_measurement_ui": false,
  "enable_variation_orders": false
}
```

Conclusion:

The seven rollout flags are synced to `v16.localhost`, readable from Python at runtime, and default to disabled.
