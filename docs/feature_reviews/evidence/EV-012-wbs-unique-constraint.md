# EV-012: WBS Unique Constraint Preflight and Migration

Date: 2026-06-09

Task: `WP1.3`

## Implementation

Added a migration/preflight path for unique `(boq_header, wbs_code)` on `BOQ Structure`.

Source changes:

- `/home/mohamed/frappe-bench/apps/construction/construction/services/boq_wbs_health.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/patches/v6_8/add_boq_structure_wbs_unique_constraint.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/patches.txt`
- `/home/mohamed/frappe-bench/apps/construction/construction/install.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.py`

The implementation runs WBS health validation before adding the constraint and uses an after-migrate path so the unique index survives normal Frappe DocType sync.

## Migration Verification

Command:

```bash
bench --site v16.localhost migrate
```

Result:

```text
Executing construction.patches.v6_8.add_boq_structure_wbs_unique_constraint in v16.localhost
Success: Done
```

Final migrate cycle also completed successfully after the durable after-migrate path was added.

## Database Verification

Command:

```bash
bench --site v16.localhost mariadb --execute "SHOW INDEX FROM \`tabBOQ Structure\` WHERE Key_name = 'unique_boq_header_wbs_code'"
```

Result:

```text
Key_name                    Seq_in_index  Column_name
unique_boq_header_wbs_code  1             boq_header
unique_boq_header_wbs_code  2             wbs_code
```

## Health Check Verification

Command:

```bash
bench --site v16.localhost execute construction.services.boq_wbs_health.run_wbs_health_check
```

Result:

```json
{
  "healthy": true,
  "summary": {
    "structures_checked": 6,
    "items_checked": 2,
    "issue_count": 0,
    "by_type": {},
    "by_severity": {}
  },
  "issues": []
}
```

## Idempotency Verification

Command:

```bash
bench --site v16.localhost execute construction.services.boq_wbs_health.ensure_wbs_unique_constraint
```

Result:

```json
{
  "created": false,
  "index_name": "unique_boq_header_wbs_code",
  "health": {
    "structures_checked": 6,
    "items_checked": 2,
    "issue_count": 0,
    "by_type": {},
    "by_severity": {}
  }
}
```

Conclusion:

The WBS unique constraint is present, health-gated, and idempotent.
