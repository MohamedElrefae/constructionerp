# EV-008: WBS Policy Input After Health Check

Date: 2026-06-08

Task: `WP1.1`

Input evidence:

- `EV-005`: Existing `v16.localhost` BOQ dataset identified.
- `EV-007`: WBS health check completed with zero detected issues.

Health-check conclusion:

- No duplicate WBS codes found.
- No blank WBS codes found.
- No missing parent structures found.
- No invalid nested-set bounds found.
- No orphan BOQ Items found.
- No BOQ Item/header mismatches found.
- No BOQ Items linked to group structures found.
- No leaf structures missing BOQ Items found.

Recommended WBS policy for approval:

1. WBS codes may be generated and resequenced only while BOQ Header status is `Draft`.
2. WBS codes become immutable when BOQ Header status moves to `Pricing`.
3. WBS codes remain immutable in `Frozen` and `Locked`.
4. Resequence must be a privileged server operation, not a normal form save.
5. Resequence must write an audit record showing before/after WBS mapping.
6. A unique `(boq_header, wbs_code)` constraint is safe to plan after a migration preflight because the current checked dataset has no WBS conflicts.

Approval status:

Superseded by `EV-009: Variation Order Architecture`.

Reason:

`EV-008` covered only Contract BOQ WBS stability. `EV-009` adds the execution-phase rule that post-lock scope changes must go through Variation Orders, while keeping the Contract BOQ immutable.
