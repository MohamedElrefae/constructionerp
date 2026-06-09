# EV-046 - WP4 Transaction Scope Registry

Date: 2026-06-09

Tasks: `WP4.2`, `WP4.3`, `WP4.4`

## Scope

Define and verify the supported BOQ transaction matrix for Egypt/Gulf construction ERP workflows.

## Supported Matrix

| Parent DocType | Child Table | Child DocType | Applicability Gate | Allowed BOQ Status |
| --- | --- | --- | --- | --- |
| Purchase Order | items | Purchase Order Item | expense_category = Direct | Frozen, Locked |
| Purchase Receipt | items | Purchase Receipt Item | expense_category = Direct | Frozen, Locked |
| Purchase Invoice | items | Purchase Invoice Item | expense_category = Direct | Frozen, Locked |
| Sales Invoice | items | Sales Invoice Item | is_progress_billing = 1 | Frozen, Locked |
| Stock Entry | items | Stock Entry Detail | expense_category = Direct | Frozen, Locked |
| Timesheet | time_logs | Timesheet Detail | direct-labor designation policy | Frozen, Locked |
| Journal Entry | accounts | Journal Entry Account | expense_category = Direct | Frozen, Locked |
| Material Request | items | Material Request Item | expense_category = Direct | Frozen, Locked |

Unsupported transaction DocTypes are ignored by the BOQ transaction validator.

## Implementation

- Added `construction.services.boq_scope_registry`.
- `boq_transaction_validation.py` now reads its child-table map from the registry instead of keeping a separate hardcoded policy.
- Registry uses the shared `ALLOWED_TRANSACTION_BOQ_STATUSES` from `boq_scope_filters.py`, keeping server validation and client dropdown status rules aligned.

## Verification

Command:

```bash
bench --site v16.localhost execute construction.tests.test_transaction_validation.run_wp4_scope_registry_smoke
```

Result summary:

```json
{
  "status": "passed",
  "flag_restored": false,
  "unsupported_behavior": "ignored"
}
```

The smoke verified:

- 8 supported transaction DocTypes.
- Correct child table and child DocType mapping.
- All supported child DocTypes expose `boq_item`.
- Allowed statuses are `Locked` and `Frozen`.
- `enable_boq_scope_registry` toggles correctly and was restored to `0`.
- Unsupported `Delivery Note` is ignored by BOQ validation.

## Status

`WP4.2`, `WP4.3`, and `WP4.4` can move to `VER`.
