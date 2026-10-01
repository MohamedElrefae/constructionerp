# Wave 1 Canary Disposition — Comparative P95 Artifact

**Work item:** `bilingual-wave1-masters` (Phase 1 + Phase 2)
**Branch:** `feature/bilingual-wave1-masters`
**Date:** 2026-10-02
**Status:** `ACCEPTED_KNOWN_MISMATCH` — latency gate UNEVALUATED for this candidate
**Authority:** owner instruction given in session; transcribed by the agent

---

## 1. Summary

Two tests in `construction/tests/test_bilingual_account_pilot.py` govern comparative search
latency for the Account bilingual path. One passes on this branch; one fails. Neither result
establishes that Wave 1 search latency is within the canonical bound.

| Test | Result on this branch | What it actually asserts |
|---|---|---|
| `test_comparative_p95_artifact_bound_and_gate` | **FAIL** | Code hashes match the preserved artifact, **and** the preserved measurement satisfies the 1.10× ceiling |
| `test_comparative_p95_live_measurement_is_balanced_and_bound` | PASS | Structural properties only — **no latency comparison** |

Account pilot suite: **52 / 53**. Wave 1 suites: **16 / 16**.

## 2. The latency gate is unevaluated for this candidate

`test_comparative_p95_live_measurement_is_balanced_and_bound` verifies structural
integrity — match-set equivalence, alternating pair order balance, per-call SQL query
counts, environment binding and the statistic contract. It does **not** compare P95 against
any ceiling. Its own comment states the reason:

> *"The latency gate itself is decided by the artifact test above, which is hash-bound to the
> CURRENT code and regenerated each cycle (a live sub-2ms baseline is too small for a stable
> 10% split; the artifact is forced current by the hash check, so it cannot go stale)."*

The canonical comparison exists only in the artifact test:

```python
limit = m["baseline"]["p95_ms"] * 1.10  # canonical 10% rule; floor REJECTED by the owner
self.assertLessEqual(m["bilingual"]["p95_ms"], limit, ...)
```

That comparison is unreachable while the test fails on hashes. **No assertion currently in
the suite bounds Wave 1 search latency.** This disposition does not assert otherwise.

## 3. The hash mismatch is intentional, and the hash check is load-bearing

`test_comparative_p95_artifact_bound_and_gate` fails on the code-hash assertion because this
candidate intentionally modified `construction/services/bilingual_service.py` and
`construction/searchable_dropdown/api/search.py` in commit `81af417` (generalizing
`norm_field` resolution from the hardcoded `AR_NORM_FIELD` constant to registry-driven
resolution across six masters).

The hash binding is not a cosmetic tamper check. It is the mechanism that forces
re-measurement whenever governed code changes; without it, the preserved measurement could
silently describe code that no longer exists, and the latency gate would pass against stale
inputs. Dispositioning the mismatch therefore does not preserve the performance contract —
it suspends it.

A superseded claim was retracted during this disposition. An earlier draft asserted that
live measurement "remains within the 10% ceiling — PASS." That is unsupported: the live
test performs no latency comparison.

## 4. Ownership boundary

The preserved artifact is `docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage3/p95-measurement.json`,
owned by the `erp-arabic-bilingual-data` work item (introduced in commit `0d96cdc`). It is
untouched by this branch. `git diff` against that path is empty.

The artifact also encodes an owner decision that must not be silently replaced:

> `"gate": "<= baseline_p95_ms * 1.10 (canonical 10% rule; the prior 15 ms floor was REJECTED by the owner)"`

Re-measuring and re-pinning it is therefore a governance maintenance run under
`erp-arabic-bilingual-data` requiring explicit owner sign-off, not a side effect of Wave 1.

## 5. Disposition

1. The hash mismatch is **accepted as a known, intentional consequence** of commit `81af417`.
2. Comparative search latency for Wave 1 masters is **UNEVALUATED**. No performance claim is
   made by this work item.
3. The Stage-3 artifact is **not modified**. Re-pinning is deferred to an owner-authorized
   governance maintenance run under `erp-arabic-bilingual-data`.
4. All six Wave 1 masters remain `schema_installed`. Promotion to `active` requires the
   latency evaluation to be performed, consistent with Phase 1 §F and Phase 2 §2.3 / §3.G.

## 6. What re-pinning would require

Recorded for the future governance run; **not performed here**.

1. Owner authorization for a Stage-3 evidence maintenance run under
   `erp-arabic-bilingual-data`, explicitly addressing the previously rejected 15 ms floor.
2. `measure_search_p95` executed on Wave 1 governed code, with the same fixture discipline
   and cleanup as the preserved session.
3. A regenerated artifact whose `code_hashes` match the Wave 1 blobs, retaining
   `match_sets_equal`, per-round nearest-rank recomputability and min-over-rounds selection.
4. Re-run of the account pilot suite reaching 53 / 53.
5. Independent confirmation that the 1.10× rule, not the rejected floor, remains canonical.

## 7. Verification performed for this disposition

- `git diff 81af417 -- construction/services/bilingual_service.py` → empty
- `git diff 81af417 -- construction/searchable_dropdown/api/search.py` → empty
- `git diff -- docs/ai/work-items/erp-arabic-bilingual-data/` → empty
- `grep -n "1.10" construction/tests/test_bilingual_account_pilot.py` → single occurrence at
  line 1308, inside the failing artifact test only
