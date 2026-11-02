# P00/G0 — S4 component revision record (v2), 2026-11-02

**Status: REVISED AND UNIT-TESTED (synthetic inputs only); NOT EXECUTED against any database.** No provisioning, no Q7 execution, no target, no D2, no custody, no acceptance, no qualification, no closure. Q7 remains `INCOMPLETE`; witness unqualified; gate BLOCKED.

## 1. Authorization and scope

Document-and-code revision authorization (2026-11-02): (1) conflicting-evidence detection ⇒ INCOMPLETE/`conflicting_evidence`, no class; (2) unevaluable input ⇒ INCOMPLETE/`evaluation_ambiguous`; (3) matrix-to-interface rulings for Q7-P3-01/02 and Q7-BND-02 + harness alignment; (4) updated synthetic unit tests; (5) new digest + independent review. No DB execution, no provisioning.

## 2. Changes

1. **Conflict detection (`assess()`)**: performs two observations within one assessment (freshness rule applied between them). If the comparable keys differ ⇒ `INCOMPLETE`, reason `conflicting_evidence`, **no class emitted**. If they agree ⇒ normal classification. Multi-row observations remain `C3/UNKNOWN`.
2. **Ambiguity mapping**: unevaluable input (missing/non-numeric field) ⇒ `INCOMPLETE`, reason `evaluation_ambiguous`, no class. Out-of-enum values (e.g., `7`) remain `C3/UNKNOWN` (`unexpected_value`) per the matrix.
3. **Freshness fix**: the first read of an assessment is fresh by definition (no prior read in the instance); subsequent reads enforce the ≥150 ms idle gap. (Found while wiring `assess()`; a defect that would have marked the first read unproven.)
4. **Rulings** recorded in `P00_G0_Q7_MATRIX_INTERFACE_RULINGS_2026-11-02.md` (P3-01/02 and BND-02 vacuous-by-construction; BND-03 left live as a residual gap).
5. **Harness alignment** for the revised API and rulings.

## 3. Artifacts and digests

| File | SHA-256 |
|---|---|
| `apps/construction/scripts/p00_g0_witness/s4_extract.py` | `5ea3036edd6182867f706159d4e4f73f5b4226563e5e4556edfe0485c774c610` |
| `apps/construction/scripts/p00_g0_witness/test_s4_extract.py` | `e7036fcc40e979b3c6e74b94b34c09703b2c15f5e26769f16eb0297444b709cd` |
| `apps/construction/scripts/p00_g0_witness/run_q7_matrix.py` | `8a81fd9c0b459c23e3c93ed8e279fa3286d05e5ed23ba147751b782ef1dc0203` |

## 4. Unit tests (synthetic only)

`python3 -m unittest discover -s apps/construction/scripts/p00_g0_witness -v` → **19 tests, all OK**. New coverage: conflicting evidence ⇒ INCOMPLETE/`conflicting_evidence` with `redaction_decision: withheld`; agreeing observations ⇒ C1; unevaluable input ⇒ INCOMPLETE/`evaluation_ambiguous`; out-of-enum remains `C3/UNKNOWN`; existing record/digest/freshness/vocabulary tests retained.

## 5. Status and limitations

- Component revision: **COMPLETE** at design level, unit-tested; **not integrated or executed** against a database in this round.
- The prior Q7 run's stop remains recorded and unchanged; Q7 remains `INCOMPLETE` (5/23).
- A future Q7 run requires: fresh environment provisioning, the new mechanism digest (`5ea3036e…`), a **new** execution authorization (the previous one is consumed), and resolution or acceptance of the residual `Q7-BND-03` interpretation gap.
- The witness remains unqualified; D5 remains empirically supported but uncharacterized.

## 6. Independent review outcome

Reviewer: MiMo-V2.6-Flash (technical author/reviewer separation; not custody, not acceptance, not qualification). **VERDICT: VERIFIED** — digests recomputed and matched; the five authorized items confirmed; conflict/ambiguity semantics correct; rulings coherent; BND-03 left live; no overclaiming; Q7 remains INCOMPLETE.

Findings recorded (not fixed in this round, because any code/test edit would change the verified digests and require a fresh review):
1. (minor) the `assess()`-path ambiguity branch (row failing `_row_key`) is covered only at `classify()` level; the assess-path variant is unexercised by a dedicated test.
2. (informational) `_row_key` compares multi-row observations by row count only; outcome is `C3/UNKNOWN` either way, so no class-emission impact.
3. (informational) the freshness comment says "first read in this assessment" while the state is per-instance; behavior matches the record's wording.

These are recorded for a future revision; none affects the current semantics or any status.

## 7. Non-actions

No database execution; no environment provisioning; no configuration change; no target access; no D2 action; no evidence placement; no custody; no acceptance; no qualification; no closure; no broader retry.
