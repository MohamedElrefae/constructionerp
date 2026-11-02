# P00/G0 — Amendment to the Gate G8 mechanism study (evidence mapping), 2026-11-02

**Status: DOCUMENTED AMENDMENT — the Gate G8 study file itself is unchanged (digest `641bf0d0…f8122501` preserved); this document amends one mapping decision only.** No execution, no provisioning, no target, no D2, no custody, no acceptance, no qualification, no closure.

## 1. Amended mapping

Gate G8 study §3.2 stated: "query or verification error ⇒ `C6` (`UNKNOWN`, or `FAIL` on integrity break)".

**Amended to:** evaluation/predicate **errors** (query execution failure, aborted evaluation) ⇒ **`INCOMPLETE`**, reason `evaluation_aborted`, no class emitted, record `withheld` — because an aborted evaluation means *evidence is insufficient*, not that the fact is unestablished. **Integrity failures** (digest/signature mismatch or record tamper) continue to map to **`FAIL`** (`integrity_failure`), preserved visible when safe.

## 2. Rationale

- Consistent with the spec's rule that uncertainty yields `INCOMPLETE` (P6) and with the Q7 matrix's `Q7-P6-03` expectation (predicate skipped by error ⇒ `INCOMPLETE`).
- Keeps `UNKNOWN` for facts that are genuinely unestablished (absence, out-of-enum, unqualified method).
- Preserves the `FAIL` channel exclusively for confirmed integrity failures.

## 3. Effect

- The component (v3) implements the amended mapping: errors ⇒ `Outcome(None, INCOMPLETE, "evaluation_aborted")`; `integrity_failed=True` ⇒ `Outcome(None, FAIL, "integrity_failure")`.
- All other study decisions (surface selection S4, extraction contract, C1–C6 mapping, P1–P6 predicates, freshness, correlation, environment requirements) are unchanged.
- The study's digest binding remains valid because the study file was not edited; this amendment is a separate, referenced record. A future revision of the study should fold it in.

## 4. Statement

Documentation only. No component or database action occurred under this amendment itself; the component change is recorded separately in `P00_G0_S4_COMPONENT_REVISION_RECORD_3_2026-11-02.md`.
