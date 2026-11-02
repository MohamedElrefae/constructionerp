# P00/G0 — Q7 matrix execution run record 3 (Gate G13-B), 2026-11-02

**Status: COMPLETE — 23/23 cases, no stop, 16 live PASS + 7 vacuous PASS.** Q7 remains `INCOMPLETE` pending a separately authorized determination; this run does not self-qualify and does not close Q7. Gate BLOCKED; witness unqualified; no closure. Runs 1 and 2 are preserved unchanged.

## 1. Parameters

| Field | Value |
|---|---|
| Authorization | Gate G13-B (owner letter, 2026-11-02), after G13-A VERIFIED |
| Principal | ephemeral local OS user (opaque; no personal identity recorded) |
| Mechanism | `s4_extract.py` v3 — SHA-256 `f644a2288839853b6dc9fa86d19221ca5f3a6738d1b23f2b2aedcce6063fd1c4` (verified before run) |
| Harness | `run_q7_matrix.py` — SHA-256 `242b4efd431be5909db6ecfa31b5f1a46fababf6d769a50502fac959d94874e5` |
| Environment | `p00-g0-disposable-03`: exact `10.11.14-MariaDB-0ubuntu0.24.04.1`, `skip_networking=1`, private datadir, synthetic fixture (3 rows) |
| Destination | ERFs in memory only; never written to disk; discarded at exit |
| Teardown | verified: datadir removed, socket removed, no server process remains |
| Review | independent technical review of this record (separate record) |

## 2. Results — 23/23

| # | Case | Observed | Expected (matrix) | Probe | Result |
|---|---|---|---|---|---|
| 1 | Q7-P1-04 (control, real DB RO) | `C1/UNKNOWN` | control | pass | PASS (expected behaviour met; not a pass claim) |
| 2 | Q7-P2-04 (control, real DB RW) | `C2/UNKNOWN` | control | pass | PASS |
| 3 | Q7-P1-01 (non-allowlisted) | `C5/INCOMPLETE` | INCOMPLETE | pass | PASS |
| 4 | Q7-P1-02 (out-of-enum) | `C3/UNKNOWN` | UNKNOWN | pass | PASS |
| 5 | Q7-P1-03 (conflicting reads) | `—/INCOMPLETE` (`conflicting_evidence`) | INCOMPLETE | pass | PASS |
| 6 | Q7-P2-01 (text) | `C5/INCOMPLETE` | INCOMPLETE | pass | PASS |
| 7 | Q7-P2-02 (identifier) | `C5/INCOMPLETE` | INCOMPLETE | pass | PASS |
| 8 | Q7-P2-03 (pointer/free-text) | `C5/INCOMPLETE` | INCOMPLETE | pass | PASS |
| 9 | Q7-P3-01 (statement names value) | vacuous (R1) | INCOMPLETE (no statement channel) | n/a | PASS (vacuous) |
| 10 | Q7-P3-02 (comparative) | vacuous (R1) | INCOMPLETE | n/a | PASS (vacuous) |
| 11 | Q7-P3-03 (label-only control) | `C1/UNKNOWN` | control | pass | PASS |
| 12 | Q7-P4-01 (coarse-leak on withheld detail) | `C5/INCOMPLETE`; canary absent | INCOMPLETE | pass | PASS |
| 13 | Q7-P4-02 (timing) | vacuous (R4: no transaction/engine time channel) | INCOMPLETE if leak | n/a | PASS (vacuous) |
| 14 | Q7-P4-03 (coarse control) | `C1/UNKNOWN` | control | pass | PASS |
| 15 | Q7-P5-01 (withheld value present) | `C5/INCOMPLETE`; canary absent from serialized record | FAIL / INCOMPLETE | pass | PASS |
| 16 | Q7-P5-02 (reconstruction) | vacuous (R5: no aggregates) | INCOMPLETE | n/a | PASS (vacuous) |
| 17 | Q7-P5-03 (staging residue) | vacuous (R6: no staging channel) | FAIL / INCOMPLETE | n/a | PASS (vacuous) |
| 18 | Q7-P6-01 (ambiguity) | `—/INCOMPLETE` (`evaluation_ambiguous`) | INCOMPLETE | pass | PASS |
| 19 | Q7-P6-02 (conflicting surfaces) | `—/INCOMPLETE` (`conflicting_evidence`) | INCOMPLETE | pass | PASS |
| 20 | Q7-P6-03 (predicate error) | `—/INCOMPLETE` (`evaluation_aborted`) | INCOMPLETE | pass | PASS |
| 21 | Q7-BND-01 (handle derivation) | `C1/UNKNOWN`; random handle, no derivation path | pass if not derivable | pass | PASS |
| 22 | Q7-BND-02 (handle reuse) | vacuous (R2) | UNKNOWN | n/a | PASS (vacuous) |
| 23 | Q7-BND-03 (identifier linkage) | vacuous (R3: no identifier channel) | INCOMPLETE | n/a | PASS (vacuous) |

**Stop: none.** No mismatch, no probe failure, no redaction leak, no stop condition triggered.

## 3. Findings

1. **Error mapping (v3) validated:** predicate/evaluation error → `INCOMPLETE`/`evaluation_aborted` (case 20), distinguishing aborted evaluation from out-of-enum (`C3/UNKNOWN`, case 4).
2. **Canary probes pass:** withheld-detail (`P4-01`) and canary-absence (`P5-01`) cases emit `C5/INCOMPLETE` with the canary absent from the serialized record — no passthrough.
3. **Conflict/ambiguity discipline holds** across single and paired observation paths (cases 5, 18, 19).
4. **Controls:** declared RO transaction → `C1`; explicit RW → `C2` (surface observation only).
5. **Vacuous rulings applied** (R1–R6) with lapse conditions; no other case reinterpreted.

## 4. Status

- **Q7: execution complete (23/23, 0 stop) but remains `INCOMPLETE`** until a separately authorized review determines otherwise; the run does not self-qualify.
- Witness remains **unqualified**; criteria 1–4 (runtime observation, correlation, mapping source, visibility characterization) undemonstrated; D5 empirically supported but uncharacterized.
- Gate **BLOCKED**; P00/G0, H01, H02 open; P1 deferred; P2 paused.

## 5. Boundaries

No production/staging/target access; no D2 creation/access/placement; no credentials/identities/SQL bodies/document identifiers collected; no configuration change; no custody; no acceptance; no qualification; no closure; ERFs ephemeral; environment torn down and verified.

*Run record only. Accepts nothing, qualifies nothing, closes nothing.*
