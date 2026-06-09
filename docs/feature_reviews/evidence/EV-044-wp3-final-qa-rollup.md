# EV-044 - WP3.8 Stage Measurement/Certification Final QA Rollup

Date: 2026-06-09

## Scope

Ran final WP3 QA after completing stage policy, locking, UI behavior, certified-stage safety, and bulk update API.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.py \
  apps/construction/construction/services/boq_lifecycle.py \
  apps/construction/construction/services/boq_operational.py \
  apps/construction/construction/api/boq_api.py \
  apps/construction/construction/tests/test_boq_item_stage.py
```

Result: passed.

```bash
node --check apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.js
node --check apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage_list.js
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_item_stage.run_stage_policy_smoke
bench --site v16.localhost execute construction.tests.test_boq_item_stage.run_stage_certification_role_smoke
bench --site v16.localhost execute construction.tests.test_boq_item_stage.run_stage_bulk_update_smoke
```

Result: all passed.

Process-level concurrency verification:

- Setup created `BOQ-2026-0137`.
- Two separate `bench execute` processes tried to insert stages with planned quantity `6` each against a BOQ Item quantity of `10`.
- One process succeeded.
- One process failed with:

```text
Total planned quantity (12.0) exceeds BOQ Item quantity (10.0)
```

Inspection returned:

```json
{
  "success": true,
  "header": "BOQ-2026-0137",
  "stage_rows": [
    {
      "name": "BOQ-STG-00139",
      "stage_code": "ROLL-2",
      "planned_qty": 6.0
    }
  ],
  "total_planned": 6.0
}
```

## Coverage Verified

- Frozen/Locked BOQ planning fields are immutable.
- Frozen/Locked measurement fields remain editable before certification.
- Certified stages cannot be edited.
- Certified stages cannot be deleted.
- Non-certifier users cannot certify stages.
- Admin/certifier certification succeeds.
- Bulk update API is feature-flagged.
- Bulk update API saves through normal validations.
- Concurrent stage planned quantity over-allocation is blocked.
- Form and list client scripts are syntactically valid.

## Cleanup Verification

```bash
bench --site v16.localhost mariadb -e "
select name, title from \`tabBOQ Header\` where title like 'WP3%Smoke';
select field, value from \`tabSingles\`
where doctype='Construction Settings' and field='enable_stage_measurement_ui';
"
```

Result:

- No temporary WP3 smoke BOQ Header rows remained.
- `enable_stage_measurement_ui = 0`.

## Visual QA Note

Browser screenshots were not captured because in-app browser tooling was not exposed in this turn. UI behavior is covered by JS syntax checks and server-side validation smokes.

## Acceptance

`WP3.8 = VER`

WP3 is functionally verified through direct bench execution smokes, process-level concurrency verification, client syntax checks, and cleanup checks.
