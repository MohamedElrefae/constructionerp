# EV-041 - WP3.2 Stage Distribution Locking

Date: 2026-06-09

## Scope

Verified and hardened BOQ Item Stage planned quantity distribution locking.

## Finding

The previous validation used a parent `BOQ Item` `SELECT ... FOR UPDATE` and then read sibling stages through a normal `frappe.get_all` query. Separate-process concurrency testing showed that two requests could both validate against the same pre-insert state and over-allocate planned stage quantity.

## Implementation

The validation now:

- Acquires a per-BOQ-item MariaDB named lock with `GET_LOCK`.
- Releases the named lock through Frappe `after_commit` / `after_rollback` callbacks.
- Reads existing sibling stages with `SELECT ... FOR UPDATE` so the validation uses a locked current read.
- Keeps the existing parent `BOQ Item` row lock.

## Verification Commands

```bash
./env/bin/python -m py_compile \
  apps/construction/construction/services/boq_operational.py \
  apps/construction/construction/tests/test_boq_item_stage.py
```

Result: passed.

Process-level concurrency setup:

```bash
bench --site v16.localhost execute construction.tests.test_boq_item_stage.setup_stage_concurrent_process_smoke
```

Returned:

```json
{
  "success": true,
  "header": "BOQ-2026-0105",
  "boq_item": "BOQI-BOQ-2026-0105-0106"
}
```

Two separate `bench execute` processes were launched concurrently against the same BOQ Item:

```bash
bench --site v16.localhost execute construction.tests.test_boq_item_stage.insert_stage_for_item_smoke --args '["BOQI-BOQ-2026-0105-0106", "PROC-1", 6]'
bench --site v16.localhost execute construction.tests.test_boq_item_stage.insert_stage_for_item_smoke --args '["BOQI-BOQ-2026-0105-0106", "PROC-2", 6]'
```

Result:

- One process succeeded.
- One process failed with:

```text
Total planned quantity (12.0) exceeds BOQ Item quantity (10.0)
```

Inspection and cleanup:

```bash
bench --site v16.localhost execute construction.tests.test_boq_item_stage.inspect_stage_concurrent_process_smoke --args '["BOQ-2026-0105"]'
```

Returned:

```json
{
  "success": true,
  "header": "BOQ-2026-0105",
  "stage_rows": [
    {
      "name": "BOQ-STG-00107",
      "stage_code": "PROC-1",
      "planned_qty": 6.0
    }
  ],
  "total_planned": 6.0
}
```

Final cleanup check:

```bash
bench --site v16.localhost mariadb -e "
select name, title from \`tabBOQ Header\`
where title in ('WP3 Concurrent Stage Smoke','WP3 Concurrent Process Stage Smoke');
"
```

Result: no rows.

## Acceptance

`WP3.2 = VER`
