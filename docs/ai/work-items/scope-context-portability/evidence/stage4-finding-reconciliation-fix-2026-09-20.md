# Stage 4 Finding Reconciliation Fix (2026-09-20)

## Problem

The Stage 4 quorum branch in `routing.py` only ever appended blocking findings. When the
proposer fixed a rejected row, a later panel approval did **not** clear the earlier
row-rejection finding. The stale finding stayed in state, recurred every round, drove
`unchanged_rounds` to 2, and forced `ESCALATED` indefinitely even though the proposal was
correct. The code-review path (`review_outcome`) already reconciled findings on PASS; the
panel path did not.

This is why the panel kept "rejecting" rows 8/23/GST after the owner-mandated Arabic was
applied: the current proposal was correct, but the old findings were never cleared.

## Fix

In the quorum `all_blocking` branch, before escalation:

- Build `approved_rows` / `rejected_rows` from the **current** panel row decisions.
- Resolve (drop) a `row_rejected` finding whose row is currently approved.
- For legacy findings that predate `row_identity` (summarized by index or redacted
  identity), resolve them once the current panel has no remaining rejections.
- Rebuild `state["findings"]` from the survivors plus genuinely new findings, then run
  `escalation_cycle` on the **surviving** set.

Also added `row_identity` to the sanitized review metadata (`stage4.py`) so reconciliation
can key on the stable identity.

## Verification

Full orchestrator suite: **225 passed**. No ERP mutation, DRY_RUN, IMPORT, commit, push,
or merge.
