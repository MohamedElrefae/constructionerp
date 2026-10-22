# EV-043 - WP3.7 Bulk Stage Measurement and Certification API

Date: 2026-06-09

## Scope

Added feature-flagged bulk update API for BOQ Item Stage measurement and certification fields.

## Implementation

Added `construction.api.boq_api.bulk_update_boq_item_stages`.

The method:

- Requires `Construction Settings.enable_stage_measurement_ui = 1`.
- Accepts a list of stage update rows.
- Allows only measurement/certification fields:
  - Stage Status
  - Measured Executed Qty
  - Certified Qty
  - Percent Complete
  - Description
- Saves every stage through normal `BOQ Item Stage` validation.
- Cannot bypass Frozen/Locked planning locks.
- Cannot bypass certified-stage immutability.
- Cannot bypass certification role policy.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/api/boq_api.py \
  apps/construction/construction/tests/test_boq_item_stage.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_item_stage.run_stage_bulk_update_smoke
```

Result: passed.

Key returned evidence:

```json
{
  "success": true,
  "disabled_blocked": true,
  "measurement_success": true,
  "guest_certification_blocked": true,
  "admin_certification_success": true,
  "rows": [
    {
      "stage_code": "BULK-1",
      "measured_executed_qty": 2.0,
      "certified_qty": 2.0,
      "percent_complete": 40.0,
      "stage_status": "Certified"
    },
    {
      "stage_code": "BULK-2",
      "measured_executed_qty": 3.0,
      "certified_qty": 0.0,
      "percent_complete": 60.0,
      "stage_status": "In Progress"
    }
  ]
}
```

Cleanup verification:

```bash
bench --site v16.localhost mariadb -e "
select name, title from \`tabBOQ Header\`
where title in ('WP3 Bulk Stage Smoke','WP3 Certification Role Smoke');
select field, value from \`tabSingles\`
where doctype='Construction Settings' and field='enable_stage_measurement_ui';
"
```

Result:

- No temporary smoke BOQ Header rows remained.
- `enable_stage_measurement_ui = 0`.

## Acceptance

`WP3.7 = VER`
