# P00/G0 — S4 component revision record v3 (Gate G13-A), 2026-11-02

**Status: REVISED AND UNIT-TESTED (synthetic only); NOT EXECUTED against any database.** No provisioning, no run, no target, no D2, no custody, no acceptance, no qualification, no closure. Q7 remains `INCOMPLETE`; witness unqualified; gate BLOCKED.

## 1. Authorization

Gate G13-A (owner letter, 2026-11-02): component error mapping; study-mapping amendment; rulings R4–R6; harness probes for P4-01/P5-01; updated tests; digests + independent review. No execution.

## 2. Changes

1. **Component v3 (`s4_extract.py`)**
   - Evaluation/predicate **errors** now map to `INCOMPLETE`, reason `evaluation_aborted`, no class, `redaction_decision: withheld` (previously `C6/UNKNOWN`).
   - **Integrity failures** (explicit `integrity_failed=True`) map to `FAIL`, reason `integrity_failure`, no class, `withheld`; preserved visible when safe.
   - `assess()` inherits the same mapping (errors in either observation ⇒ `INCOMPLETE`/`evaluation_aborted`).
   - New reason `evaluation_aborted` added to the fixed reason set; closed vocabulary otherwise unchanged.
2. **Study amendment** — `P00_G0_MECHANISM_DESIGN_SELECTION_STUDY_AMENDMENT_2026-11-02.md` records the mapping change; the study file itself is unchanged (digest preserved).
3. **Rulings R4–R6** appended to `P00_G0_Q7_MATRIX_INTERFACE_RULINGS_2026-11-02.md`: R4 timing channel (no transaction/engine timestamp; `idle_gap_ms` harness-only), R5 aggregates, R6 staging — each vacuous-by-construction with lapse conditions.
4. **Harness probes**
   - `Q7-P4-01`: withheld-detail probe — a suppressed canary field (`C5/INCOMPLETE`) plus verification that the serialized record contains no trace of the field or its canary.
   - `Q7-P5-01`: canary-absence probe — same scenario; assert the canary is absent from the entire serialized record.
   - `Q7-P4-02`, `Q7-P5-02`, `Q7-P5-03`: now vacuous per R4/R5/R6.
   - `Q7-P6-03`: expected `INCOMPLETE` (evaluation aborted).
   - Global probe: any record containing the canary constant fails.

## 3. Digests

| Artifact | SHA-256 |
|---|---|
| `apps/construction/scripts/p00_g0_witness/s4_extract.py` | `f644a2288839853b6dc9fa86d19221ca5f3a6738d1b23f2b2aedcce6063fd1c4` |
| `apps/construction/scripts/p00_g0_witness/test_s4_extract.py` | `42091cf6bd70bca8c7efcb9ce68a62206736ce2e1e6806a0621711f09aa7cfe9` |
| `apps/construction/scripts/p00_g0_witness/run_q7_matrix.py` | `242b4efd431be5909db6ecfa31b5f1a46fababf6d769a50502fac959d94874e5` |
| Rulings document (with R3–R6) | `6abf9cf8f3682c629e6c9aefd199421e4a61539d130cf26f56187d1794fffd63` |
| Study (unchanged) | `641bf0d0e93816d4d03ae382a0be9ad65ba330931b7229a75daf4c20f8122501` |

## 4. Unit tests (synthetic only)

`python3 -m unittest discover -s apps/construction/scripts/p00_g0_witness -v` → **20 tests, all OK**. Updated/added: query error ⇒ `INCOMPLETE`/`evaluation_aborted`/withheld; integrity failure ⇒ `FAIL`/`integrity_failure`/withheld; prior conflict/ambiguity/vocabulary/digest/freshness tests retained.

## 5. Status

Component v3 is ready for a future G13-B run (not executed here). The witness remains unqualified; Q7 remains `INCOMPLETE` (17 faithful cases from run 2); gate BLOCKED.

## 6. Independent review outcome (Gate G13-A)

Reviewer: MiMo-V2.6-Flash. **VERDICT: VERIFIED.** Digests recomputed and matched (`f644a228…`, `42091cf6…`, `242b4efd…`, `6abf9cf8…`); error⇒INCOMPLETE/withheld, integrity⇒FAIL precedence, canary probes, R4–R6 coverage and P6-03 expectation all confirmed; no silent reinterpretation; no overclaiming.

Findings recorded (not fixed, to preserve the verified digests):
1. (low) rulings §4 still shows the pre-v3 harness digest `8a81fd9c…` and "19/19"; it is superseded by this record (harness `242b4efd…`, 20/20).
2. (low) R4's "harness-only" wording: `idle_gap_ms` is measured by the component's monotonic clock across `_enforce_freshness`/`_read_once` and may include prior query time; the substantive claims (no absolute/transaction/engine timestamp; no transaction-state content) hold.
3. (low) `s4_extract.py` docstring still says "revision 2"; behavior matches v3 as recorded.

## 7. Non-actions

No database execution; no provisioning; no configuration change; no target; no D2; no custody; no acceptance; no qualification; no closure.
