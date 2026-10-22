# F08 — Concurrency and atomicity: live overlapping-request evidence

**Date:** 2026-10-13
**Candidate:** construction `1e46488` · frappe 16.51.1 · erpnext 16.50.0 · MariaDB 10.11.14
**Site:** v16rehearsal.localhost (Owner session; enforcement ON)
**Method:** two spawned processes, each with an independent DB connection (`frappe.connect()` per process), synchronized on a 2-party barrier; ops are real submit/cancel/save + commit. Losers retried once per the protocol's own retry contract.
**Status:** 4/4 scenarios consistent. F08 **Engineering verified** for the specified scenarios; the pre-existing 12-test service suite covers protocol units. No new lock protocol introduced.

## 1. Fixtures

Dedicated header BOQ-2026-8579 (Draft, PROJ-0014) + 2 items (manual est 50). Draft analyses created sequentially as Administrator; all overlapping ops run as the Owner identity.

## 2. Results

| Scenario | Overlap outcome | After one bounded retry | Invariant verified |
|---|---|---|---|
| S1 concurrent submits, different items | One won; loser fail-closed `QueryTimeoutError: This BOQ is being changed by another user. Retry the complete operation.` | Both Approved | Items 100/120 each; header 3000 = 1000+2000 |
| S2 duplicate submits, same analysis | One won; loser fail-closed `TimestampMismatchError` (22 ms apart) | — (no retry needed) | Exactly one Approved; clean supersede chain; values applied once |
| S3 submit-A5 overlaps cancel-A4 | Cancel won; submit fail-closed with retryable contention | Submit ok; chain A2→(A4 cancelled)→A5 Approved | Active = A5; item matches (100/120); no orphan basis |
| S4 item edit overlaps submit, same item | Edit won (qty 30); submit fail-closed | Submit ok | Edit + approval each applied once; header 5000 = 3000+2000; one Approved-active per item |

## 3. Contention, retry, deadlock record

- No deadlocks observed; no partial commits (every post-scenario read reconciled counts, active analyses, values and totals).
- Contention surfaces exclusively as fail-closed retryable errors (NOWAIT lock protocol) or optimistic timestamp mismatch — both documented behaviors, never silent overwrites. The previously calculated 310-overwrites-330 race shape from G05 does not occur: losers fail instead of writing stale totals.
- Retry rule demonstrated: exactly one bounded whole-operation retry, then consistency asserted. No unbounded retry loops.

## 4. Remaining

Stack-level (web/worker) contention under realistic load belongs to F37; F05–F07 sequential invariants unchanged; F04/F06 baselines untouched (dedicated header; final F08 state: 2 items, 5-analysis history, totals 5000).
