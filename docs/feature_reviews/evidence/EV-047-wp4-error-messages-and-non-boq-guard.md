# EV-047 - WP4 Error Messages and Non-BOQ Guard

Date: 2026-06-09

Tasks: `WP4.5`, `WP4.6`

## Scope

Verify that transaction BOQ validation fails with clear user-facing messages and does not unexpectedly validate unsupported transaction DocTypes.

## Implementation

Updated `construction.services.boq_accounting.validate_transaction_row` to give clearer messages for:

- BOQ header/structure/stage selected without BOQ item.
- Missing BOQ item record.
- BOQ Header status not eligible for transactions.
- Project mismatch.
- Stage not belonging to the selected BOQ Item.

`construction.services.boq_transaction_validation.validate_document` now returns immediately when the parent DocType is not in the BOQ transaction registry.

## Verification

Command:

```bash
bench --site v16.localhost execute construction.tests.test_transaction_validation.run_wp4_error_message_smoke
```

Result:

```json
{
  "status": "passed",
  "checks": [
    {
      "scenario": "missing_item",
      "message": "Row 1: BOQ attribution is incomplete. Select a BOQ Item or clear the BOQ fields."
    },
    {
      "scenario": "stage_parentage",
      "message": "Row 2: BOQ Item Stage definitely-missing-stage does not belong to selected BOQ Item BOQI-BOQ-2026-0143-0144."
    },
    {
      "scenario": "invalid_status",
      "message": "Row 3: BOQ Header BOQ-2026-0146 is Draft. Transaction attribution is allowed only for Locked, Frozen."
    },
    {
      "scenario": "project_mismatch",
      "message": "Row 4: Project mismatch. Transaction: PROJ-0005, BOQ: PROJ-0004"
    }
  ]
}
```

Additional cleanup verification:

```sql
select name,title
from `tabBOQ Header`
where title like 'Test Transaction BOQ%'
   or title like 'WP4 Draft Status Smoke%';
```

Result: no rows.

## Status

`WP4.5` and `WP4.6` can move to `VER`.
