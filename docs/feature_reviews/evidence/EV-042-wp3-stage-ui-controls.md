# EV-042 - WP3.3/WP3.4 Stage Measurement UI Controls and Progress Indicators

Date: 2026-06-09

## Scope

Added BOQ Item Stage form/list UI behavior for measurement and certification workflows.

## Implementation

Form UI:

- Fetches BOQ Header status and applies read-only behavior.
- Freezes identity/planning fields when BOQ is `Frozen` or `Locked`.
- Locks all fields when the stage is certified or has certified quantity.
- Makes `certified_qty` read-only unless the user has one of:
  - System Manager
  - Construction Owner
  - Project Manager
- Adds dashboard indicators for:
  - Measured %
  - Certified %
  - Progress %
- Shows headline guidance for certified stages and non-certifier users.

List UI:

- Added `boq_item_stage_list.js`.
- Adds scan indicators for:
  - Certified
  - Over Measured
  - Completed
  - On Hold
  - In Progress
  - Not Started

Server role safety:

- Non-certifier users cannot set `certified_qty` or move a stage to `Certified`, even through API or direct save.

## Verification Commands

```bash
node --check \
  apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.js

node --check \
  apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage_list.js
```

Result: passed.

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.py \
  apps/construction/construction/tests/test_boq_item_stage.py
```

Result: passed.

```bash
bench --site v16.localhost execute construction.tests.test_boq_item_stage.run_stage_certification_role_smoke
```

Result: passed.

Key returned evidence:

```json
{
  "success": true,
  "guest_certification_blocked": true,
  "guest_error": "Only Project Manager, Construction Owner, or System Manager can certify BOQ Item Stages.",
  "admin_certification_allowed": true
}
```

## Visual QA Note

In-app browser tooling was not exposed in this turn, so no browser screenshot was captured. The client scripts passed JavaScript syntax checks and the role-sensitive behavior is backed by server validation.

## Acceptance

- `WP3.3 = VER`
- `WP3.4 = VER`
