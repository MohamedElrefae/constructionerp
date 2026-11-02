# P00/G0 — Mechanism design and selection study (Gate G8), 2026-11-02

**Status: DESIGN AND SELECTION RECORD ONLY.** No code, package, environment, configuration, target access, Q7 execution, D2 action, custody, qualification, or closure. The recommendation below is a design position, not a selection for execution and not a qualified witness. Machine-readable twin: `P00_G0_MECHANISM_DESIGN_SELECTION_STUDY.json`. Gate remains **BLOCKED**.

**Source basis (digest-verified):** MariaDB Server 10.11.14 tarball, SHA-256 `8a571cb14fb1d4e3663d8e98f3d4200c042fc8b2a4aaaab495860dea8b7d052f` (112,475,645 bytes). File:line references are to that artifact.

**Preserved constraints applied throughout:** non-mutating reads only; no configuration change (so the PFS path is excluded); no PROCESS privilege; no identity collection; no query bodies; no D2; no target access.

## 1. Requirement comparison (S1–S6)

Criteria: R1 non-mutating · R2 per-transaction · R3 identity-free output · R4 freshness/visibility · R5 correlation integrity · R6 redaction safety · R7 D8 compatibility · R8 Q7 compatibility · R9 preserved rules · R10 stop-condition compatibility.

| Surface | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1** `@@tx_read_only` | pass | **fail** (session default, not live) | pass | **fail** (not live state) | n/a | pass (trivial) | partial | fail (T2/T4 depend on live state) | pass | pass | **Rejected** |
| **S2** protocol status bit | pass | pass | pass | pass (immediate) | **fail** (no SQL surface) | pass | partial | fail (no observable seam) | pass | pass | **Rejected** |
| **S3** PFS `events_transactions.ACCESS_MODE` | **fail** (instrument off; enabling = config change) | pass | pass (columns filterable) | pass (in-memory current) | pass (THREAD_ID) | pass | pass | partial | **fail** (config change excluded) | **fail** | **Rejected** |
| **S4** `I_S.INNODB_TRX` (`trx_is_read_only`) | pass | pass | pass (with exclusions) | **partial** (0.1 s cache) | pass (own-connection predicate) | pass (contract) | pass | pass | pass | pass | **RECOMMENDED (conditional)** |
| **S5** session status counters | pass | **fail** (cumulative) | pass | n/a | fail | pass | fail | fail | pass | pass | **Rejected** |
| **S6** `SHOW ENGINE INNODB STATUS` | pass | partial (engine-wide) | **fail** (free text) | n/a | fail | **fail** (text) | fail | fail | **fail** (PROCESS grant) | fail | **Rejected** |

### 1.1 Decision

**Recommendation: `S4` — `information_schema.INNODB_TRX.trx_is_read_only` — as the primary and only surface.** No supplementary surface is recommended:
- S1 is a session *declaration default*, not live state; using it as evidence would repeat the exact ambiguity D6 warns about.
- S2 is truthful but has no SQL-observable surface (protocol status only).
- S3 is architecturally ideal but requires enabling a disabled-by-default instrument — an excluded configuration change.
- S5 is session-cumulative; S6 is free text behind global PROCESS.

`NO_SELECTION` is **not** recorded because S4 satisfies every requirement in design terms, with one characterized limitation (§2) and one testable unknown (freshness, §6) that the Q7 matrix is designed to probe.

## 2. Critical semantic finding (must shape the design)

Source: `storage/innobase/trx/trx0trx.cc:904-912`:

```
trx->read_only = srv_read_only_mode
    || (!trx->dict_operation && thd_trx_is_read_only(trx->mysql_thd));
if (!trx->auto_commit) { trx->will_lock = true; }
else if (!trx->will_lock) { trx->read_only = true; }
```

Consequences:
1. `trx_is_read_only = 1` means "InnoDB will reject writes from this trx" — an **enforcement** property, not a declaration record.
2. **Autocommit non-locking statements are forced read-only** — a plain autocommit `SELECT` shows `trx_is_read_only = 1` without any declared `START TRANSACTION READ ONLY`. The column `trx_autocommit_non_locking` (`i_s.cc:355`) exists to distinguish this case.
3. With `innodb_read_only = ON` (global mode), every trx is read-only; attribution to a declaration is impossible → indeterminate.
4. In an explicit multi-statement transaction, `read_only = thd_trx_is_read_only()` reflects the transaction access mode — the declaration the witness cares about.

Therefore the design classifies **declared-mode evidence only** for explicit multi-statement transactions, treats autocommit rows and global-mode rows as indeterminate, and never reports "read-only" from those cases.

## 3. Implementation-ready design specification

### 3.1 Selected surface (source identity)

| Field | Value |
|---|---|
| Surface | `INNODB_TRX.trx_is_read_only` (plus `trx_autocommit_non_locking`, `trx_state` as supporting flags) |
| Source references | column defs `storage/innobase/handler/i_s.cc:355` (and field array); fill `storage/innobase/trx/trx0i_s.cc:488` (`row->trx_is_read_only = trx->read_only;`); semantics `storage/innobase/trx/trx0trx.cc:904-912`; cache `storage/innobase/trx/trx0i_s.cc:961-973, 1046-1062`; read path `storage/innobase/handler/i_s.cc:363-396` |
| Digest basis | tarball `8a571cb1…7d052f` |

### 3.2 Extraction contract

**Permitted inputs:** `trx_is_read_only` {0,1}; `trx_autocommit_non_locking` {0,1}; `trx_state` enum; the predicate value `CONNECTION_ID()` used **only inside the WHERE clause** to select the observer's own session row; `@@innodb_read_only` {0,1} (global mode flag).
**Forbidden inputs and outputs:** `trx_query` (SQL text); `trx_mysql_thread_id` (never emitted, never logged, never retained — predicate use only); `trx_id`, `GTID`, `XID_*`, `XA_STATE`; `trx_requested_lock_id`, `trx_last_foreign_key_error`; `OBJECT_INSTANCE_BEGIN`; raw timers (`trx_started`, `trx_wait_started`, `TIMER_*`); all user/host fields; any row of another session.
**Output vocabulary:** only `C1` `MODE_READONLY`, `C2` `MODE_READWRITE`, `C3` `MODE_INDETERMINATE`, `C4` `MODE_ABSENT`, `C5` `MODE_WITHHELD`, `C6` `MODE_ERROR`, and statuses `UNKNOWN`/`INCOMPLETE`/`FAIL` with fixed reason keys. **No passthrough.**
**Failure behavior:** absent row ⇒ `C4`/`UNKNOWN`; predicate/row ambiguity ⇒ `C3`/`UNKNOWN`; withheld due to redaction doubt ⇒ `C5`/`INCOMPLETE`; query or verification error ⇒ `C6` (`UNKNOWN`, or `FAIL` on integrity break); never a pass.

### 3.3 C1–C6 classification mapping (declared-mode question)

```
row = read own-session row via predicate (no emission)
if no row                          -> C4 MODE_ABSENT -> UNKNOWN (absence != read-only)
elif trx_autocommit_non_locking=1  -> C3 MODE_INDETERMINATE -> UNKNOWN (autocommit read-only is trivial)
elif @@innodb_read_only=1          -> C3 MODE_INDETERMINATE -> UNKNOWN (global mode confounds attribution)
elif trx_is_read_only=1            -> C1 MODE_READONLY     (declared read-only, enforced by engine)
elif trx_is_read_only=0            -> C2 MODE_READWRITE    (adverse if read-only expected)
else                               -> C3/C6 by error path
```
Mapping of C-codes to statuses follows the D8 artifact: C4/C3 ⇒ UNKNOWN (unestablished/indeterminate), C5 ⇒ INCOMPLETE (withheld), C6 ⇒ UNKNOWN (or FAIL where a confirmed integrity failure is safely stateable), C2 adverse ⇒ preserved FAIL where safe; no conversion; no pass.

### 3.4 P1–P6 implementation design

- **P1 allowlist:** only the four permitted fields plus the predicate; any other column requested ⇒ `C5`/INCOMPLETE and stop.
- **P2 absolute exclusions:** text, identifiers, pointers, timers, other sessions' rows; the predicate's `CONNECTION_ID()` value is used in-SQL only, never bound to output, never logged.
- **P3 at-risk per statement:** the emitted record states only class + status + fixed reason; no statement may describe the session, transaction id, or timing precisely.
- **P4 coarse-leak check:** before emission verify that `MODE_READONLY` for an explicit txn reveals nothing beyond the class (it does not reveal which table/rows were read); statuses carry no boundary information.
- **P5 withheld values never emitted:** C5 path suppresses the value; failure preserved in the redacted record where safe.
- **P6 uncertainty ⇒ INCOMPLETE:** any evaluation doubt (predicate error, version mismatch, cache ambiguity) yields INCOMPLETE, never a pass.

### 3.5 Failure-record interface

One immutable-append entry per attempt: `attempt_id` (opaque) · `case_id` (Q7 ID) · `surface` (`S4`) · `correlation` {predicate used: own-connection; handle token; continuity flag} · `freshness` {idle-gap achieved, cache-age bound class} · `class_outcomes` {C-code + reason} · `status` {UNKNOWN|INCOMPLETE|FAIL} · `stop` {S#|none} · `integrity` {prev_digest, this_digest} · `redaction_decision` {emitted label|withheld} · `timestamp_class` (coarse) · `notes_redacted`. Append-only, digest-chained; no deletion; confirmed failures preserved.

### 3.6 Opaque handle and correlation design

- Handle: CSPRNG ≥128-bit, random, never derived from connection id, user, host, thread id, or trx id; single-assessment scope; destroyed at record close; never carried across assessments; never logged.
- Correlation: the witness reads only the **observer's own session row** via the in-SQL predicate `trx_mysql_thread_id = CONNECTION_ID()`; the value is never emitted, stored, or logged. Correlation is therefore inherent (own session), not an identity lookup.
- Invalidation: reconnect, transaction restart, connection-pool switch, or handle reuse ⇒ `UNKNOWN` (stop S3).

### 3.7 Freshness, visibility, invalidation rules

- The I_S cache refetches only when idle > **0.1 s** (`CACHE_MIN_IDLE_TIME_NS = 100000000`, `trx0i_s.cc:961`); within 100 ms a read may serve a stale snapshot.
- Rule: the witness performs its read only after an idle gap ≥ 150 ms since the previous I_S read in the session; this forces a refetch and bounds staleness to ≤ 100 ms plus query latency.
- Absence of the own-session row after the forced refresh ⇒ `C4`/`UNKNOWN` (never a pass); one bounded retry after ≥150 ms is permitted **within the same assessment** (same surface, same scope); further absence ends the attempt as UNKNOWN (no broader retry).
- D5 characterization remains a **Q7 test seam** (timing cases); no runtime claim is made by this design.

### 3.8 Test seams required by the Q7 matrix

| Seam | Q7 cases |
|---|---|
| Row presence/absence of own-session row | T2/T3 analogues; Q7-P1-04 control |
| Cache refresh timing (idle-gap enforcement) | T-timing; Q7-P4-02 |
| Autocommit vs explicit transaction discrimination | new seam; Q7 control variant |
| Forbidden-column rejection | Q7-P1-01/02, Q7-P2-01/02/03 |
| Output vocabulary enforcement | Q7-P1-02, Q7-P6-03 |
| Correlation invalidation | Q7-BND-02 |
| Redaction/withholding | Q7-P3-01/02, Q7-P5-01/02 |
| Integrity chain break | Q7-P5-01 adjacent (T7) |

### 3.9 Disposable-environment requirements (proposed, not provisioned)

| Field | Requirement |
|---|---|
| Name | `p00-g0-disposable-01` (proposal) |
| Lifetime | ≤ 24 h, single-use, destroyed after the run |
| Isolation | container/namespace with no route to any production/staging network; local MariaDB 10.11.14 only; no host credentials; no user data (synthetic fixtures only) |
| Teardown | destroy container and database volume; delete ephemeral ERFs; record teardown verification |
| Evidence destination boundary | **ephemeral in-memory run records only**; no D2 access; no placement; ERFs destroyed at teardown unless a later destination authorization applies |
| Fixtures | synthetic sessions/transactions only; no identities, credentials, SQL bodies, or document identifiers |

### 3.10 Implementation prerequisites and prohibited activities

**Prerequisites (each separately authorized):** (1) approve this design; (2) implement the extraction/redaction component bound to this specification (digest-recorded) with unit tests using synthetic inputs; (3) independent technical review of the component; (4) provision the disposable environment above; (5) issue Q7 execution scope with principal/mechanism/environment/destination fully populated.
**Prohibited (unchanged):** configuration changes (including enabling PFS instruments); PROCESS or any privilege escalation; target access; writes of any kind (including rejected attempts); identity collection; query-body capture; D2 access; custody; qualification; closure; broader-access retry.

## 4. Limitations of this recommendation

1. **Design position only** — recommendation ≠ selection for execution; nothing is qualified; Q7 remains INCOMPLETE.
2. **Freshness** is bounded by source reasoning (0.1 s cache + forced-refresh rule) but not characterized at runtime; D5 remains open until Q7 tests run.
3. **Declared-mode scope**: the witness evidences *engine-level read-only enforcement for an explicit multi-statement transaction*; it does not prove the absence of past writes or the absence of autocommit reads. Autocommit and global-mode rows are indeterminate by design.
4. Correlation uses the session's own connection id inside the predicate only; the identity rules are preserved by never emitting/storing/logging it, but a Q7 binding test must confirm this non-emission.
5. S3 remains the architecturally cleaner alternative if the owner ever permits instrument configuration; it is excluded today.

## 5. Non-execution statement and expiry

No code, package, environment, configuration, test, or target interaction occurred. The study selects no implementation for execution, creates no custody, qualifies no witness, and closes nothing. This authorization expired upon issuance of this study.

Gate BLOCKED. P00/G0, H01, H02 open; P1 deferred; P2 paused.
