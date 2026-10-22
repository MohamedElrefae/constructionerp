# Phase 2 result: blocked on failure-class recording

Reference: committed/frozen Phase 1 `4b77803af418cea8459c4cb7d9a0248674845da3`.

The final run executed 110 tests: 108 passed, 2 failed. All 93 frozen regression tests passed. All 51 frozen source/config/prompt/template files and both checker scripts retain their recorded bytes. No project commit or site operation occurred. Synthetic baseline/owner commits exist only in disposable test repositories.

## P2-F001 — Required adapter failure classes are discarded

**Classification:** implementation defect; Phase 2 exit blocker.  
**Location:** `orchestrator/engine.py:426–428` (`Engine._collect`).

Two independent scenarios reproduce the same defect:

1. A synthetic terminal result contains malformed output. The actual Codex parser raises `WorkflowError("MALFORMED_RESULT: ...")`.
2. A synthetic terminal observation arrives without its captured stdout evidence. `Engine.accept` raises `WorkflowError("EVIDENCE_UNAVAILABLE")`.

In both cases, the collector stores `failure=type(exc).__name__`, so the database records `WorkflowError`. The checkpoint records `PAUSED / RECONCILIATION_REQUIRED`. No valid result is accepted and advancement stops, but neither durable record retains the required failure classification. Canonical §6.2 requires the named classes to be recorded, not just a generic pause.

The executable regressions are `verification/phase2/test_scenarios.py::test_failure_classes_block_and_record_named_class[MALFORMED_RESULT]` and `[EVIDENCE_UNAVAILABLE]`. They call the actual collection and parser logic against synthetic bytes; no provider is contacted.

## Bounded proposed correction — not applied

Preserve the recognized structured failure class when the collector records the rejected job. Keep the untrusted result unaccepted, keep reconciliation mandatory, and keep the existing retry rules. Do not publish raw exception content that may contain sensitive data. Unknown exceptions must remain visibly uncertain rather than being silently assigned a fabricated class.

The change belongs in frozen `orchestrator/engine.py`; the existing new regressions already specify the required outcome. Obtain the owner's frozen-source amendment authorization under canonical §10, implement the correction, rerun the complete Phase 2 suite, and record a replacement freeze only after passing. No project commit is included in this proposal.

## Verification scope

Routing, complete repair context, PLAN-grant retention, independent quorum pass/fail/incomplete, duplicate-result handling, stale approval, both escalation thresholds across restart, process kill/resume, candidate drift rejection, post-commit/pre-record reconciliation, and actual `VACUUM INTO` recovery pass. Missing-binary proven-nonlaunch retry, authentication, denial and timeout scenarios pass.

Stage 4 wire/schema checks remain covered by frozen tests. This run does not certify ERP proposal composition or private-site snapshot integration, and no synthetic run counts as real native-pilot acceptance.
