# EV-045 - WP4 Journal Entry Account Compatibility

Date: 2026-06-09

Task: `WP4.1`

## Scope

Verify that `Journal Entry Account` supports the same BOQ attribution fields used by purchasing, stock, sales, timesheet, and material request transaction rows.

## Verification

Command:

```bash
bench --site v16.localhost execute construction.tests.test_transaction_validation.run_wp4_journal_entry_account_smoke
```

Result:

```json
{
  "status": "passed",
  "fields": ["boq_header", "boq_item", "boq_item_stage", "boq_structure"],
  "boq_header": "BOQ-2026-0143",
  "boq_structure": "sl15mc3je0"
}
```

## Review Notes

- `Journal Entry Account` has `boq_header`, `boq_structure`, `boq_item`, and `boq_item_stage` as Link custom fields.
- Server validation accepts a Journal Entry row-style payload.
- Server validation derives and populates `boq_header` and `boq_structure` from the selected `boq_item`.
- A full submitted Journal Entry was not created because GL posting requires accounting master setup that is outside WP4 scope; row-level server compatibility is verified.

## Status

`WP4.1` can move to `VER`.
