# Escalation Fix — Stage 4 Repair Loop (2026-09-19)

**Work item:** erp-arabic-bilingual-data
**Stage:** 4 (PANEL_REVIEW)

## Problem

The Stage 4 quorum branch in `routing.py` handled blocking panel findings and renewal
without advancing the repair budget (`unsuccessful_cycles`, `unchanged_rounds`). The
escalation thresholds therefore never fired and the proposer ↔ panel loop ran
indefinitely (57+ accumulated findings).

Two contributing causes:
1. The quorum branch never called the escalation bookkeeping that the code-review path
   (`review_outcome`) uses.
2. Engine-synthesized `row_rejected` findings had no snapshot and used the row *index* in
   their summary, so repeated rejections of the same row were not recognizable as the
   same blocker.

## Fix

- `routing.escalation_cycle(state, blocking_findings)` centralizes the budget update:
  increments `round`/`unsuccessful_cycles`, derives stable snapshot digests (with a
  classification+summary fallback for panel findings that carry no snapshot), updates
  `unchanged_rounds`, and reports whether the budget is exhausted.
- The Stage 4 `all_blocking` and `renewal_required` branches now call it. Escalation
  pauses with `ESCALATED` and preserves `next_roles=["proposer"]` for a clean resume.
- `stage4.validate_and_store_review` now summarizes row rejections by the row
  **identity** (stable across revisions) rather than its index.

## Result

After the proposal revision cycle, the workflow paused:

```
pause_reason = ESCALATED
unsuccessful_cycles = 2
unchanged_rounds = 2
round = 2
```

Owner resume requires `resume --reset-escalation-budget --reason ...`. Full orchestrator
suite: **225 passed**. No ERP mutation, DRY_RUN, IMPORT, commit, push, or merge occurred.
