# P00/G0 — Phase H source-only evidence package (Q1–Q8), 2026-11-01

**Status: SOURCE-ONLY EVIDENCE RECORDS — no target access, no live observation, no tests, no D2 access, no acceptance, no qualification.** Executed under the Gate G authorization (2026-11-01) limited to the source-and-document-only Phase H subset; the authorization expired upon completion of this subset. Gate remains BLOCKED. Machine-readable twin: `P00_G0_PHASE_H_SOURCE_ONLY_EVIDENCE.json`. Verification: MiMo-V2.6-Flash (internal technical verification; recorded separately).

**Authorization basis and limits (as executed):** public source and documentation only; Q1–Q8 as listed; Q7 expressly recorded INCOMPLETE pending future adversarial testing; no production/staging/lab/disposable target; no live observation, correlation, visibility testing; no D2 creation/configuration/access/placement; no credentials, identities, raw unexpected values, SQL/script bodies, document identifiers or unrelated business records collected or transmitted; no qualification execution, deployment or closure; no broader-access retry. No stop condition was triggered; the subset completed within the boundary.

**Incident exclusion:** the prior unauthorized inspection remains unverified and excluded; no incident-derived material informed this package; inputs are limited to the digest-verified public source artifact and the workstream's own documents.

**Authored-source basis:** MariaDB Server 10.11.14 upstream source tarball, re-retrieved this round from the official release endpoint and digest-verified against the recorded provenance value `8a571cb14fb1d4e3663d8e98f3d4200c042fc8b2a4aaaab495860dea8b7d052f` (byte size 112,475,645). All file:line references below are to that artifact. This is source-level analysis only; it establishes nothing about any runtime.

**Scope caveat (recorded, not a stop):** no observation mechanism has been selected; therefore Q1–Q8 are produced as **candidate-surface analyses** over the six surfaces enumerated in earlier review rounds. Completeness relative to any future selected method is INCOMPLETE by construction (method unselected). No comparison is performed.

---

## Q1 — Read-path inventory (candidate surfaces; source-verified)

Closed inventory for the enumerated survey scope. Each surface is a *candidate*; none is selected.

| # | Surface | Source read path (10.11.14) | Nature |
|---|---|---|---|
| S1 | `tx_read_only` session variable (session default; live flag separate) | `sql/sys_vars.cc:4356-4364` (`Sys_var_tx_read_only`, `SESSION_VAR(tx_read_only)`); `sql/sys_vars.inl:44` (`offsetof(SV, X)` → session-default struct) | SQL-readable boolean (session default) |
| S2 | Live per-transaction read-only state and its protocol status bit | `sql/transaction.cc:60` (copy default), `:163-165` (READ ONLY sets live flag), `:210-211`; `sql/handler.cc:1396-1402` (`SERVER_STATUS_IN_TRANS_READONLY` set at real trx start) | server state; protocol status bit (not SQL-named) |
| S3 | `performance_schema.events_transactions_*` `ACCESS_MODE` | `storage/perfschema/table_events_transactions.cc:425-427` (`m_read_only ? TRANS_MODE_READ_ONLY : TRANS_MODE_READ_WRITE`); instrument default OFF: `storage/perfschema/pfs_instr_class.cc:261-264` | SQL-readable enum, **only if instrumented** (enabling = configuration change, excluded) |
| S4 | `information_schema.INNODB_TRX` | `storage/innobase/handler/i_s.cc` field array (columns below); fill `storage/innobase/trx/trx0i_s.cc:488` (`row->trx_is_read_only = trx->read_only`); cache `:1046-1062` (`fetch_data_into_cache`, skips `TRX_STATE_NOT_STARTED`); cache-fill path `i_s.cc:363-396` | SQL-readable engine view; cache timing/visibility limits (D5) |
| S5 | Session status counters | `sql/sql_parse.cc:3922` (`SQLCOM_SHOW_STATUS` → `execute_show_status`); `sql/sql_class.h:923` (`system_status_var`) | cumulative counters; not transaction-scoped |
| S6 | `SHOW ENGINE INNODB STATUS` | `sql/sql_parse.cc:4226-4231`; `sql/privilege.h:643` (`PRIV_STMT_SHOW_ENGINE_STATUS = PROCESS_ACL`) | engine-wide free-text; global PROCESS gate; text excluded from bounded use |

**Cardinality (per surface, as enum/bit domains):** S1 {0,1}; S2 {0,1} bit (protocol-only); S3 `ACCESS_MODE` {READ ONLY, READ WRITE}; S4 `trx_is_read_only` {0,1}, `trx_state` {RUNNING, LOCK WAIT, ROLLING BACK, COMMITTING}; S5 unbounded numeric counters; S6 free text (unbounded, excluded). This closes the manifest's cardinality field for the enumerated scope.

**Status: source inventory COMPLETE for the enumerated surfaces; INCOMPLETE relative to any future selected method (method unselected — recorded limitation, not a stop).**

## Q2 — Value-domain proof (per surface, worst-case field analysis)

Classification key: **P** = permitted bounded field (boolean/enum → label constants); **X** = excluded (identity-bearing, free-text, or correlatable identifier); **C** = coarse-only (timing/aggregate, permitted only in reduced form).

**S1 (`tx_read_only`)**: domain {0,1} → **P** (maps to MODE_READONLY / MODE_READWRITE when read; note it is the session default, not the live per-transaction mode). The field-class letters **P/X/C** used below are distinct from the Q7 predicate labels **P1–P6** (notation note).
**S2**: status bit {0,1} → **P** in principle; protocol-level only (no SQL name found) → usability limited (recorded).
**S3** fields: `ACCESS_MODE` {READ ONLY, READ WRITE} → **P**; `STATE` {ACTIVE, COMMITTED, ROLLED BACK} → **P**; `ISOLATION_LEVEL` enum → **P**; `AUTOCOMMIT` {YES, NO} → **P**; `THREAD_ID` → **X** (correlatable session key); `EVENT_ID`/`END_EVENT_ID`/`NESTING_EVENT_ID` → **X** (sequence keys); `TRX_ID` → **X** (transaction linkage); `GTID`, `XID_FORMAT_ID`, `XID_GTRID`, `XID_BQUAL`, `XA_STATE` → **X** (transaction identifiers); `SOURCE` → **X** (implementation string, non-identity but unnecessary); timers `TIMER_START/END/WAIT` → **C** (coarse timing only); `OBJECT_INSTANCE_BEGIN` → **X** (memory pointer); `NUMBER_OF_SAVEPOINTS`-class counters → **C**.
**S4 (`INNODB_TRX`)** columns and classes: `trx_id` X (linkage); `trx_state` {RUNNING, LOCK WAIT, ROLLING BACK, COMMITTING} P; `trx_started` C (datetime, coarse only); `trx_requested_lock_id` X; `trx_wait_started` C; `trx_weight` C; `trx_mysql_thread_id` X (correlatable key); `trx_query` **X** (SQL text — absolutely excluded); `trx_operation_state` X (free-text-ish); `trx_tables_in_use`, `trx_tables_locked`, `trx_lock_structs`, `trx_lock_memory_bytes`, `trx_rows_locked`, `trx_rows_modified`, `trx_concurrency_tickets` C (numeric aggregates; `trx_rows_modified` may support bounded class {0, >0} only if a future method justifies it); `trx_isolation_level` P; `trx_unique_checks`, `trx_foreign_key_checks` P; `trx_last_foreign_key_error` X (free text); **`trx_is_read_only` {0,1} → P (engine per-transaction read-only flag)**; `trx_autocommit_non_locking` {0,1} → P.
**S5**: cumulative counters → **C** (session-scoped, not per-transaction; deltas only; no identity).
**S6**: engine-wide free text → **X** for bounded use (excluded entirely; global PROCESS gate).

**Status: COMPLETE for these surface field domains; INCOMPLETE for method-specific domains (method unselected).**

## Q3 — Handle-lifecycle design record (design only; no implementation)

Required properties for any future correlation handle: (1) construction from a CSPRNG, minimum 128 bits, **never derived** from user, host, account, thread id, connection id, or any principal attribute; (2) no mapping table or back-channel resolves the handle to a principal; (3) uniqueness scope = single assessment; (4) lifecycle: created at assessment start, used only within the assessment, destroyed at record close; (5) **never carried across assessments**; (6) never logged outside the bounded record. Status: **design record COMPLETE; implementation and lifecycle evidence ABSENT ⇒ INCOMPLETE** (no runtime work authorized).

## Q4 — Class-level adversarial negative search (no data collection)

| Class | Attempt | Outcome / residual risk |
|---|---|---|
| A1 SQL/statement text encoded | read `trx_query` / engine status text | excluded by design; risk if a future method includes text → **stop** (class withdrawn) |
| A2 session-identifier joins | `trx_mysql_thread_id`, `THREAD_ID` | excluded; residual: none if never emitted |
| A3 transaction-identifier joins | `trx_id`, `GTID`, `XID_*` | excluded; residual: none if never emitted |
| A4 timing joins | `trx_started`, timers | coarse-only; residual: sequence inference if timestamps too fine → coarsen |
| A5 ordering/cardinality inference | record shape | bounded by single-assessment scope; residual low |
| A6 handle derivation | handle construction | design forbids principal derivation; residual: implementation must be verified later |
| A7 cross-assessment linkage | lifecycle rule | forbidden by design; residual: none if lifecycle enforced |
| A8 coarse-status leakage | status strings | at-risk predicate + coarse-leak check (Q7) |

**Status: COMPLETE for enumerated classes; adversarial *validation* remains INCOMPLETE (runtime excluded).** No residual risk required class withdrawal in this source-only pass; A1/A2/A3 are excluded by design.

## Q5 — No-passthrough proof (design-level, per surface)

Extraction mapping: **only the closed vocabulary of the stable artifact may cross** — C1–C6 `MODE_*` labels, statuses (UNKNOWN/INCOMPLETE/FAIL) and fixed reasons. Every emitted value is a label constant derived from a permitted field: S1 {0,1} → MODE_READONLY/MODE_READWRITE; S3 `ACCESS_MODE` → MODE_*; S4 `trx_is_read_only` → MODE_*; S5 → aggregate class only. Fields such as `STATE`, `ISOLATION_LEVEL`, `AUTOCOMMIT`, `trx_state` and the check flags are **internal-only inputs** that may inform derivation but are never emitted; emitting any new label would require a new stable-artifact revision and is out of scope (no class outside C1–C6 is emitted). **No passthrough** of identifiers (`trx_id`, `THREAD_ID`, `trx_mysql_thread_id`, `GTID`, `XID_*`), text (`trx_query`, `trx_last_foreign_key_error`, S6), pointers (`OBJECT_INSTANCE_BEGIN`), or raw timers; timers only as coarse classes. S2 has **no SQL extraction path** (protocol-level bit only; no SQL-visible name), so it cannot be used for emission and is recorded as not usable for the bounded output. S6 is excluded as a bounded source. Status: **design proof COMPLETE for the enumerated surfaces; implementation proof ABSENT ⇒ INCOMPLETE.**

## Q6 — Re-identification analysis (document-only)

Output record (planned): package id, attempt entries, C-codes, statuses, fixed reasons, coarse timestamps, ephemeral handle. Auxiliary categories analyzed: session/processlist views, engine history, binlog/transaction history, PFS session attributes, OS logs. Joins: handle → none (random, no mapping); identifiers → none (excluded); timestamps → coarse, limiting sequence joins; cardinality/ordering → bounded by single-assessment scope. Residual risk: bounded under these assumptions; empirical validation INCOMPLETE. Least-data: no field retained without purpose; handle destroyed at close. Status: **analysis COMPLETE (assumption-bounded); empirical validation INCOMPLETE.**

## Q7 — Redaction-predicate design analysis (**expressly INCOMPLETE**)

Predicates designed: P1 field allowlist (booleans/enums only); P2 absolute exclusion of text/identifiers/pointers/raw timers; P3 at-risk per statement (statement may convey or permit inference of a suppressed value); P4 coarse-leak check before every emission; P5 withheld values never emitted, attempt and overall assessment marked INCOMPLETE; P6 uncertain redaction ⇒ INCOMPLETE (never a pass). Design analysis: worst-case argument per predicate; no counterexample found at source level. **Status: INCOMPLETE — as expressly required by the Gate G authorization, redaction sufficiency cannot be established until future adversarial testing, which is not authorized here.**

## Q8 — Planned evidence-package review (plan + internal verification note)

Planned review protocol: entry criteria = Q1–Q7 artifacts complete with statuses; reviewer ≠ author (technical separation); checklist = completeness, consistency, boundary preservation, redaction safety, status correctness, stop handling; exit = findings recorded with severities and resolutions, disagreements never erased, rule-affecting issues escalated to the owner; the review is technical separation only — **not independent human custody, not acceptance (C3), not qualification**. Status: **review plan COMPLETE; formal independent package review remains a future act.** The internal MiMo verification of this package (per the execution plan §7) is recorded separately and is not a substitute for the formal Q8 review.

---

## Status summary

| Class | Status |
|---|---|
| Q1 | COMPLETE (enumerated surfaces) / INCOMPLETE vs unselected method |
| Q2 | COMPLETE (surface domains) / INCOMPLETE vs unselected method |
| Q3 | design COMPLETE / evidence INCOMPLETE (no implementation) |
| Q4 | COMPLETE (classes) / validation INCOMPLETE |
| Q5 | design proof COMPLETE / implementation INCOMPLETE |
| Q6 | analysis COMPLETE / empirical INCOMPLETE |
| Q7 | **INCOMPLETE (pending adversarial testing — as authorized)** |
| Q8 | plan COMPLETE / formal review pending |

**Key source finding (not a qualification):** MariaDB 10.11.14 exposes `INNODB_TRX.trx_is_read_only`, filled from the engine transaction flag (`trx0i_s.cc:488`), in addition to the SQL-level session/status and PFS enum surfaces. Whether any of these can serve as a **qualified non-mutating per-transaction witness** remains undetermined: the I_S path retains the D5 cache/visibility limits (`trx0i_s.cc:1046-1062` skips `TRX_STATE_NOT_STARTED`), the PFS path requires an excluded configuration change (instrument default OFF), and no runtime evidence exists. Nothing here qualifies a method.

**Stop/expiry:** no stop condition occurred; the authorized subset completed; the Gate G authorization expired on completion. D2 untouched; C3 unchanged; acceptance authority undesignated; no custody created. Gate BLOCKED. P00/G0, H01, H02 open; P1 deferred; P2 paused.
