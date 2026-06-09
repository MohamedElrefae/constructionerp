# EV-013: Race-Safe WBS Generation

Date: 2026-06-09

Task: `WP1.4`

## Implementation

Changed BOQ Structure WBS generation from count-based sequencing to lock-based sequencing.

Source changes:

- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_wbs_generation.py`

New behavior:

- Root inserts lock the BOQ Header row before reading root siblings.
- Child inserts lock the parent BOQ Structure row before reading sibling WBS codes.
- Existing sibling WBS codes are read under lock.
- The next sequence is generated from the maximum existing last WBS segment, not from `count + 1`.
- The unique `(boq_header, wbs_code)` constraint remains the final database guard.

## Concurrent Insert Verification

Command:

```bash
bench --site v16.localhost execute construction.tests.test_boq_wbs_generation.run_concurrent_wbs_insert_smoke --kwargs '{"child_count": 4}'
```

Result:

```json
{
  "requested_inserts": 4,
  "successful_inserts": 4,
  "errors": [],
  "wbs_codes": ["01.001", "01.002", "01.003", "01.004"],
  "distinct_wbs_codes": true,
  "health": {
    "structures_checked": 5,
    "items_checked": 4,
    "issue_count": 0,
    "by_type": {},
    "by_severity": {}
  }
}
```

## Cleanup Verification

Commands:

```bash
bench --site v16.localhost execute construction.tests.test_boq_wbs_generation.cleanup_wbs_generation_smoke_records
bench --site v16.localhost execute construction.services.boq_wbs_health.run_wbs_health_check
bench --site v16.localhost execute frappe.client.get_count --args '["BOQ Structure"]'
bench --site v16.localhost execute frappe.client.get_count --args '["BOQ Item"]'
```

Result:

```json
{
  "health": {
    "structures_checked": 6,
    "items_checked": 2,
    "issue_count": 0
  },
  "boq_structure_count": 6,
  "boq_item_count": 2
}
```

Conclusion:

Concurrent same-parent inserts generated distinct WBS codes and cleanup returned the site to its original BOQ dataset size.
