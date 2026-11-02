# P00/G0 — Q7 matrix execution run record 2 (Gate G12), 2026-11-02

**Status: EXECUTED — INDEPENDENT REVIEW RETURNED BLOCKED; RESULT CLAIM WITHDRAWN.** 23 of 23 harness entries ran with no stop, but **6 cases were not faithfully instantiated** against the matrix's stated input classes and expected statuses, and the independent review identified the deviations. Effective conformance: **17 cases faithful; 6 non-conformant**. Q7 remains `INCOMPLETE`. Gate BLOCKED; witness unqualified; no closure. Run 1 is preserved unchanged; this record supersedes nothing.

## 1. Execution parameters

| Field | Value |
|---|---|
| Authorization | Gate G12 (owner letter, 2026-11-02, Option A) |
| Principal | ephemeral local OS user (opaque; no personal identity recorded) |
| Mechanism | `s4_extract.py` — SHA-256 `5ea3036edd6182867f706159d4e4f73f5b4226563e5e4556edfe0485c774c610` (verified before run) |
| Harness | `run_q7_matrix.py` — SHA-256 `896ca446bd4f8bfaf1c033736ca4db5ab2f7773b968d421337272ab2219421be` (R3-aligned; note: the rulings document and revision record reference the pre-R3 harness digest `8a81fd9c…`; this record's digest is the current one) |
| Environment | `p00-g0-disposable-02`: exact `10.11.14-MariaDB-0ubuntu0.24.04.1`, private datadir, socket-only, synthetic fixture (3 rows) |
| Destination | ERFs in memory only; never written to disk; discarded at exit |
| Teardown | verified: datadir and socket removed, no server process remains |

## 2. Results as executed, with conformance classification

**Faithful cases (17) — scenario and expectation match the matrix:**

| # | Case | Observed | Matrix expectation | Probe | Result |
|---|---|---|---|---|---|
| 1 | Q7-P1-04 | `C1/UNKNOWN` | control (eligible path; never a pass claim) | pass | faithful (expected behaviour met) |
| 2 | Q7-P2-04 | `C2/UNKNOWN` | control (pass boundary) | pass | faithful |
| 3 | Q7-P1-01 | `C5/INCOMPLETE` | INCOMPLETE | pass | faithful |
| 4 | Q7-P1-02 | `C3/UNKNOWN` | UNKNOWN | pass | faithful |
| 5 | Q7-P1-03 | `—/INCOMPLETE` (`conflicting_evidence`) | INCOMPLETE | pass | faithful |
| 6 | Q7-P2-01 | `C5/INCOMPLETE` | INCOMPLETE | pass | faithful |
| 7 | Q7-P2-02 | `C5/INCOMPLETE` | INCOMPLETE | pass | faithful |
| 8 | Q7-P2-03 | `C5/INCOMPLETE` | INCOMPLETE | pass | faithful |
| 9 | Q7-P3-01 | vacuous (R1) | INCOMPLETE (no statement channel) | n/a | faithful (ruled vacuous) |
| 10 | Q7-P3-02 | vacuous (R1) | INCOMPLETE (no statement channel) | n/a | faithful (ruled vacuous) |
| 11 | Q7-P3-03 | `C1/UNKNOWN` | control | pass | faithful |
| 12 | Q7-P6-01 | `—/INCOMPLETE` (`evaluation_ambiguous`) | INCOMPLETE | pass | faithful |
| 13 | Q7-P6-02 | `—/INCOMPLETE` (`conflicting_evidence`) | INCOMPLETE | pass | faithful |
| 14 | Q7-BND-01 | `C1/UNKNOWN` | pass if not derivable | pass | faithful |
| 15 | Q7-BND-02 | vacuous (R2) | UNKNOWN (reuse invalid) | n/a | faithful (ruled vacuous) |
| 16 | Q7-BND-03 | vacuous (R3) | INCOMPLETE (identifier attempt) | n/a | faithful (ruled vacuous) |
| 17 | Q7-P4-03 | `C1/UNKNOWN` | control | pass | faithful |

**Non-conformant cases (6) — harness did not instantiate the matrix condition/expectation:**

| # | Case | Matrix expectation | What the harness actually ran | Why non-conformant |
|---|---|---|---|---|
| 18 | Q7-P4-01 | **INCOMPLETE** (withhold coarse status if it leaks) | clean row → `C1/UNKNOWN` | no withheld-detail scenario was instantiated; expected status set to UNKNOWN |
| 19 | Q7-P4-02 | **INCOMPLETE** (if precise timing enables inference) | clean row → `C1/UNKNOWN` | timing-inference scenario not instantiated |
| 20 | Q7-P5-01 | **FAIL / INCOMPLETE** (withheld value present in record) | clean row → `C1/UNKNOWN` | no simulated withheld-value marker; leak-detection path unexercised |
| 21 | Q7-P5-02 | **INCOMPLETE** (reconstruction from aggregates) | clean row → `C1/UNKNOWN` | no aggregate-combination scenario |
| 22 | Q7-P5-03 | **FAIL / INCOMPLETE** (staging residue) | clean row → `C1/UNKNOWN` | no staging-residue scenario |
| 23 | Q7-P6-03 | **INCOMPLETE** (predicate skipped by error) | error → `C6/UNKNOWN` | component maps query error to UNKNOWN; matrix expects INCOMPLETE |

## 3. Review findings (recorded, unresolved)

1. **Major** — the six expected-status deviations above; the earlier "23/23 pass" claim in this record's first issue is **withdrawn**. No ruling covers these cases.
2. **Major** — P5-01/02/03 conditions (simulated marker, aggregate reconstruction, staging residue) were not exercised; they must not be counted as live passes.
3. **Minor** — harness digest differs from the pre-R3 value cited in the rulings/revision documents (`8a81fd9c…`); this record cites the current `896ca446…`. The change is the R3 alignment; the digest should be carried into a successor document.
4. **Informational** — "closed at the component level" wording: the G10 gap is *addressed in component v2*, subject to review; it is not "closed" by any record.

## 4. Status after the run and review

- **Q7: `INCOMPLETE`** — 17 faithful cases; 6 non-conformant; no valid "complete" claim.
- The witness remains **unqualified**; criteria 1–4 undemonstrated; D5 empirically supported but uncharacterized.
- Gate **BLOCKED**; P00/G0, H01, H02 open; P1 deferred; P2 paused.

## 5. Boundaries observed

No production/staging/target access; no D2 creation/access/placement; no credentials/identities/SQL bodies/document identifiers collected; no configuration change; no custody; no acceptance; no qualification; no closure; ERFs ephemeral; environment torn down and verified.

*Run record only, corrected after review. It accepts nothing, qualifies nothing, and closes nothing.*
