# P00/G0 — Q7 matrix execution run record, 2026-11-02

**Status: RUN TERMINATED BY STOP — 5 of 23 cases executed (4 expected-behaviour met, 1 confirmed FAIL); Q7 remains `INCOMPLETE`; authorization consumed by the stop; no retry.** Gate remains BLOCKED. No target access, no D2, no custody, no acceptance, no qualification, no closure.

## 1. Execution parameters (as authorized)

| Field | Value |
|---|---|
| Principal | ephemeral local OS user (opaque; no personal identity recorded) |
| Mechanism | `s4_extract.py` — SHA-256 **`e9dc45866a6bbe35b30b8e8db1e5c1fc425d0b4d9d473ad0e9ed1711ebcdc8e3`** (verified before the run) |
| Harness | `run_q7_matrix.py` — SHA-256 `ebef0966ad1838b0149dbdc74c40c050e971439d00fd294d17d10a87b2cd550e` |
| Environment | `p00-g0-disposable-01` re-provisioned: exact `10.11.14-MariaDB-0ubuntu0.24.04.1`, private datadir, socket-only (`skip_networking=1`), synthetic fixture only (3 rows) |
| Destination | ERFs held **in memory only** (never written to disk), discarded when the harness exited; environment torn down immediately |
| Review | independent technical review of this record (separate record) |
| Expiry | consumed by the stop condition |

## 2. Results (executed in order: controls first, then matrix order)

| # | Case | Kind | Observed | Expected (per matrix) | Coarse-leak probe | Result |
|---|---|---|---|---|---|---|
| 1 | `Q7-P1-04` | control (real DB, declared RO txn) | `C1/UNKNOWN` | eligible-path expectation (never a pass claim) | pass | **met — not a pass claim** |
| 2 | `Q7-P2-04` | control (real DB, explicit RW txn) | `C2/UNKNOWN` | pass boundary | pass | **PASS** |
| 3 | `Q7-P1-01` | P1 (non-allowlisted field) | `C5/INCOMPLETE` | INCOMPLETE | pass | **PASS** |
| 4 | `Q7-P1-02` | P1 (out-of-enum value) | `C3/UNKNOWN` | UNKNOWN | pass | **PASS** |
| 5 | `Q7-P1-03` | P1 (conflicting duplicate reads) | `C3/UNKNOWN` | **INCOMPLETE** | pass | **FAIL** |

**Stop (S2 per the matrix row; substantively an evidence-conflict stop):** `Q7-P1-03` — observed status `UNKNOWN` ≠ expected `INCOMPLETE`. The mechanism maps multiple/conflicting rows to `MODE_INDETERMINATE`/`UNKNOWN` and does **not** implement conflicting-evidence detection that would yield `INCOMPLETE`. The run terminated; the remaining 18 cases were not executed; no retry.

## 3. Findings

1. **F1 — real-surface controls behaved as designed (limited runtime evidence):** in a declared `START TRANSACTION READ ONLY` session, `INNODB_TRX.trx_is_read_only = 1` (classified `C1`); in an explicit read-write transaction it was `0` (`C2`). This is a **surface behavior observation**, not a qualified witness and not general runtime validation.
2. **F2 — component gap (the stop):** conflicting duplicate reads are not detected as conflicting evidence; the implementation lacks a two-observation comparison path and therefore cannot emit `INCOMPLETE` for that condition as the matrix requires. This is a genuine implementation defect discovered by Q7, recorded as a confirmed failure.
3. **F3 — D5 observed (single observation, empirical support only):** a first harness attempt without an idle gap produced a **stale-cache absence** of the current transaction row between back-to-back sessions (<100 ms apart); adding the mandated ≥150 ms idle gap produced the row. This is empirical support for the `CACHE_MIN_IDLE_TIME_NS` (0.1 s) freshness rule and the forced-refresh design; it is not a full characterization. It also indicates that absence in a very fast sequence can be an artifact of cache age rather than transaction state. The first attempt was corrected within the same assessment (same surface, no broader access); it is not a Q7 retry of a stopped case.
4. **F4 — redaction/vocabulary behavior held for the cases reached:** forbidden columns mapped to `C5/INCOMPLETE`; out-of-enum values mapped to `C3/UNKNOWN`; no forbidden value or identifier appeared in any record (probes passed); handles were random 32-hex; digest chain linked per record.

## 4. Ephemeral evidence statement

Per the authorization, ERF records existed only in process memory and were destroyed at exit; the environment was torn down (datadir removed; no server process remains; verified). Only the redacted per-case summary above is recorded. Digest prefixes of the in-memory ERFs (not persisted beyond the run): `307ca7d0…`, `740d55da…`, `ff91f363…`, `5f7b29bf…`, `8d76b4d3…`.

## 5. Status after the run

- Q7: **INCOMPLETE** (5/23 executed; 1 confirmed failure).
- The mechanism requires a revision (conflict detection) before a re-run; a re-run needs a new authorization and a new mechanism digest.
- The witness remains unqualified; D5 now has empirical support for the freshness rule but no full characterization.
- Gate BLOCKED; P00/G0, H01, H02 open; P1 deferred; P2 paused.

## 6. Boundaries observed

No target/production/staging access; no D2 creation/access/placement; no credentials/identities/document identifiers collected and no captured SQL bodies (only mode/flag declarations such as `START TRANSACTION READ ONLY` and `skip_networking=1` appear); no configuration change (PFS untouched); no custody; no acceptance; no qualification; no closure; stopped attempt is not a completed campaign; no broader-access retry.
