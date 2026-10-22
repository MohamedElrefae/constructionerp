# EV-017: WP1 Verification Bundle

Date: 2026-06-09

Task: `WP1.10`

## Scope

This evidence records the WP1 verification bundle after `WP1.1` through `WP1.9`.

## Standard Test Runner

Command attempted:

```bash
bench --site v16.localhost run-tests --app construction --module construction.tests.test_boq_wbs_resequence --skip-before-tests
```

Result: blocked before the target test module executed.

Observed blocker:

```text
Year start date or end date is overlapping with Fiscal Year 2025-2026.
```

This is the same ERPNext test bootstrap class of blocker previously recorded in `EV-006`; it occurs before loading the target construction test module.

Additional note: an earlier parallel attempt to run multiple Frappe test commands also produced a shared `System Settings` timestamp mismatch. WP1 test commands should be run serially in this bench environment.

## Server Smoke Verification

The isolated bench-execute smoke checks were run on `v16.localhost`.

### Race-Safe WBS Generation

```bash
bench --site v16.localhost execute construction.tests.test_boq_wbs_generation.run_concurrent_wbs_insert_smoke --kwargs '{"child_count": 4}'
```

Result:

```json
{
  "boq_header": "BOQ-2026-0033",
  "requested_inserts": 4,
  "successful_inserts": 4,
  "errors": [],
  "wbs_codes": ["01.001", "01.002", "01.003", "01.004"],
  "distinct_wbs_codes": true,
  "health": {
    "structures_checked": 5,
    "items_checked": 4,
    "issue_count": 0
  }
}
```

### Delete Safety

```bash
bench --site v16.localhost execute construction.tests.test_boq_structure_delete_safety.run_boq_structure_delete_safety_smoke
```

Result: delete was blocked for BOQ Structure `rvetpphgb9` because linked BOQ Item `اسقف خرسانية` has stages. The BOQ Structure and BOQ Item both still existed after the attempted delete.

### Conversion Safety

```bash
bench --site v16.localhost execute construction.tests.test_boq_structure_conversion.run_boq_structure_conversion_smoke
```

Result: empty group-to-leaf conversion created a BOQ Item; staged leaf-to-group conversion was blocked, and the linked BOQ Item remained intact.

### Draft-Only Resequence

```bash
bench --site v16.localhost execute construction.tests.test_boq_wbs_resequence.run_wbs_resequence_smoke
```

Result:

```json
{
  "draft_header": "BOQ-2026-0038",
  "success": {
    "changed_count": 4,
    "structure_count": 4,
    "audit_comment": "acjjgijaep",
    "audit_exists": true,
    "final_codes": {
      "Root": "01",
      "Child Group": "01.01",
      "Nested Leaf": "01.01.001",
      "Child Leaf": "01.002"
    }
  },
  "non_draft_block": {
    "header": "BOQ-2026-0039",
    "status": "Pricing",
    "blocked": true,
    "message": "WBS resequence is allowed only while BOQ Header is Draft."
  }
}
```

### Cleanup and Flag State

```bash
bench --site v16.localhost execute construction.tests.test_boq_wbs_generation.cleanup_wbs_generation_smoke_records
bench --site v16.localhost execute construction.tests.test_boq_wbs_resequence.cleanup_wbs_resequence_smoke_records
bench --site v16.localhost execute construction.services.feature_flags.get_flags
```

Result: cleanup returned no remaining smoke headers; all seven rollout flags returned `false`.

### Final WBS Health

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

## Browser QA

Command/action attempted: start local bench with `bench start`, then connect to the in-app Browser for manual BOQ tree/form QA.

Result: bench started successfully on `http://127.0.0.1:8000`, but the in-app Browser connection was rejected by the app usage-limit guard before navigation could occur. Bench was stopped cleanly afterward.

Browser QA status: blocked until Browser usage is available again or a reviewer performs manual UI QA and attaches screenshots.

## Review Conclusion

`WP1.10` is not fully verified yet because the required browser/manual tree QA is blocked, and the standard Frappe runner is blocked by existing ERPNext test bootstrap data. The implemented WP1 server behaviors are verified through isolated smoke checks and final WBS health.
