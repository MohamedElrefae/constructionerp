# EV-048 - WP4 Final QA Rollup

Date: 2026-06-09

Task: `WP4.7`

## Commands

Syntax checks:

```bash
python -m py_compile \
  apps/construction/construction/services/boq_scope_registry.py \
  apps/construction/construction/services/boq_transaction_validation.py \
  apps/construction/construction/services/boq_accounting.py \
  apps/construction/construction/tests/test_transaction_validation.py

node --check apps/construction/construction/public/js/boq_filters.js
```

Direct WP4 smokes:

```bash
bench --site v16.localhost execute construction.tests.test_transaction_validation.run_wp4_journal_entry_account_smoke
bench --site v16.localhost execute construction.tests.test_transaction_validation.run_wp4_scope_registry_smoke
bench --site v16.localhost execute construction.tests.test_transaction_validation.run_wp4_error_message_smoke
```

Formal runner attempt:

```bash
bench --site v16.localhost run-tests --app construction --module construction.tests.test_transaction_validation --skip-before-tests
```

## Results

- Python syntax checks passed.
- Client JS syntax check passed.
- Journal Entry Account compatibility smoke passed.
- Transaction registry smoke passed.
- Error message smoke passed.
- Cleanup check found no leftover WP4 BOQ Header smoke records.
- `enable_boq_scope_registry` was restored to `0`.

The formal Frappe test runner is still blocked before reaching construction tests by the existing ERPNext Fiscal Year bootstrap overlap:

```text
Year start date or end date is overlapping with Fiscal Year 2025-2026.
```

This is the same environment/test-runner blocker recorded in earlier evidence and is not a WP4 behavior failure.

## Status

`WP4.7` can move to `VER` based on direct verified smokes. Formal runner remains an environment blocker until the ERPNext test bootstrap data is isolated.
