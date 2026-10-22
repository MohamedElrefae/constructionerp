# EV-040 - WP3 Stage Edit Policy and Certified Stage Locks

Date: 2026-06-09

## Scope

Approved and implemented the BOQ Item Stage edit policy for Frozen/Locked BOQs and Certified stages.

## Approved Policy

For Egypt/Gulf construction execution workflows:

- Contract planning fields freeze when the BOQ Header is `Frozen` or `Locked`.
- Measurement fields remain editable while execution is ongoing.
- Certified stages become audit records and cannot be modified or deleted.
- Corrections after certification must be represented by adjustment stages, not direct edits.

## Server Behavior Implemented

When BOQ Header is `Frozen` or `Locked`, these stage fields are immutable:

- Project
- BOQ Header
- BOQ Structure
- BOQ Item
- Stage Code
- Stage Name
- Planned Qty

These execution fields remain editable before certification:

- Measured Executed Qty
- Certified Qty
- Percent Complete
- Stage Status
- Description

When a stage is Certified, or has `certified_qty > 0`, these fields are immutable:

- Project
- BOQ Header
- BOQ Structure
- BOQ Item
- Stage Code
- Stage Name
- Stage Status
- Planned Qty
- Measured Executed Qty
- Certified Qty
- Percent Complete
- Description

Certified stages are also protected from delete through `BOQItemStage.on_trash`.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.py \
  apps/construction/construction/services/boq_lifecycle.py \
  apps/construction/construction/tests/test_boq_item_stage.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_item_stage.run_stage_policy_smoke
```

Result: passed.

Key returned evidence:

```json
{
  "success": true,
  "frozen_measurement_allowed": true,
  "locked_measurement_allowed": true,
  "frozen_planned_blocked": true,
  "frozen_name_blocked": true,
  "certified_edit_blocked": true,
  "certified_delete_blocked": true
}
```

Cleanup verification:

```bash
bench --site v16.localhost mariadb -e "
select name, title from \`tabBOQ Header\`
where title in ('WP3 Stage Policy Smoke','WP3 Certified Stage Smoke');
"
```

Result: no rows.

## Acceptance

- `WP3.1 = VER`
- `WP3.5 = VER`
- `WP3.6 = VER`
