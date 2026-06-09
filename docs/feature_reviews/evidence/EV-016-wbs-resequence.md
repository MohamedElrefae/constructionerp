# EV-016: Draft-Only WBS Resequence

Date: 2026-06-09

Task: `WP1.9`

## Implementation Reviewed

Implemented controlled WBS resequencing in:

- `/home/mohamed/frappe-bench/apps/construction/construction/services/wbs_generator.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_wbs_resequence.py`

The public method is:

```text
construction.services.wbs_generator.resequence_wbs(boq_header)
```

Controls:

- Requires `enable_boq_wbs_resequence = 1`.
- Requires `System Manager` role.
- Requires BOQ Header status `Draft`.
- Locks the BOQ Header row during resequence.
- Uses two-phase WBS updates with temporary unique codes first, so the unique `(boq_header, wbs_code)` constraint is not violated during code swaps.
- Writes a before/after audit `Comment` on the BOQ Header.

## Verification Commands

```bash
bench --site v16.localhost execute construction.tests.test_boq_wbs_resequence.run_wbs_resequence_smoke
```

Result:

```json
{
  "draft_header": "BOQ-2026-0024",
  "success": {
    "changed_count": 4,
    "structure_count": 4,
    "audit_comment": "97lq69va5l",
    "audit_exists": true,
    "final_codes": {
      "Root": "01",
      "Child Group": "01.01",
      "Nested Leaf": "01.01.001",
      "Child Leaf": "01.002"
    }
  },
  "non_draft_block": {
    "header": "BOQ-2026-0025",
    "status": "Pricing",
    "blocked": true,
    "message": "WBS resequence is allowed only while BOQ Header is Draft."
  }
}
```

Post-smoke feature flag reset:

```bash
bench --site v16.localhost execute construction.services.feature_flags.get_flags
```

Result: all seven Improve Now rollout flags returned `false`, including `enable_boq_wbs_resequence`.

Cleanup check:

```bash
bench --site v16.localhost execute construction.tests.test_boq_wbs_resequence.cleanup_wbs_resequence_smoke_records
```

Result:

```json
{"deleted_headers": [], "count": 0}
```

Final WBS health check:

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

## Review Conclusion

`WP1.9` is verified. Draft resequence succeeds with an audit record, non-Draft resequence is blocked, rollout flag state returns to disabled, cleanup leaves no disposable records, and WBS health remains clean.
