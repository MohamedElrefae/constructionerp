# P00/G0 MariaDB provenance continuation — fingerprint confirmation and witness-possibility source review, 2026-11-01

Verdict: **fingerprint CONFIRMED from two further official upstream channels; extended source review found no construct that simultaneously satisfies all witness-compliance dimensions — the witness-existence question remains open by documented reasons, not by assumption.** Workstream gate remains BLOCKED. This document is source-and-document-only. It accepts nothing, freezes nothing, executes nothing; it verifies no target and authorizes no reliance on the historical baseline for a new operation. AI review here is not independent human custody; no independent human adjudicator participates; the custodian-cannot-self-accept rule is untouched; the prior unauthorized inspection remains unverified and excluded (no incident-derived material was used or referenced beyond its exclusion status).

Scope executed: (1) confirmation of signing-key fingerprint `177F4010FE56CA3336300305F1656F24C74CD1D8` from one further named official statement channel of the upstream project (two were obtained); (2) extended semantic review of additional upstream MariaDB 10.11.14 source paths bearing on whether a compliant non-mutating per-transaction witness can exist; (3) this documentation. Exclusions observed in full: no target access of any kind; no target writes including rejected attempts; no identity collection; no incident-derived material; no custody acts; no unofficial mirrors, prebuilt binaries or target-derived artifacts; no provisioning, implementation, testing, qualification or deployment. Retrieval/review workspace: `/tmp/opencode/p00-g0-mariadb-provenance` (outside the repository); artifacts from the prior round were reused (digests recorded there).

## 1. Evidence inventory

**Fingerprint confirmation (new this round):**

| Channel (official, upstream project) | HTTP | Result |
|---|---|---|
| `https://mariadb.org/mariadb_release_signing_key.pgp` (project website named signing-key artifact) | 200 | Key fingerprint computes to `177F4010FE56CA3336300305F1656F24C74CD1D8` — **matches target** |
| `https://mirror.mariadb.org/yum/RPM-GPG-KEY-MariaDB` (official mirror infrastructure, yum repo key) | 200 | Key fingerprint computes to `177F4010FE56CA3336300305F1656F24C74CD1D8` — **matches target** |
| `https://archive.mariadb.org/PublicKey` (used in round 1) | 200 | Same key |

Byte-comparison: all three key files are **byte-identical**, local SHA256 `00adb387f4c12e8982cfc28165d225695621494354cd58108c6845063bfb74b5`. Channels probed that carried no fingerprint text (recorded for completeness): `downloads.mariadb.org` front page, `mariadb.org/download/` (incl. release-specific query form), `archive.mariadb.org/STATUS`, `mariadb.com/kb/...` signing/gpg page slugs (JS-rendered shells), `mariadb.org/keys/` (404). The key carries only self-signatures — no cross-certification by another key exists, and none is claimed.

**Witness-review source evidence (upstream `mariadb-10.11.14.tar.gz`, member paths as cited):**

| Surface | Source reference | Finding |
|---|---|---|
| `tx_read_only` variable | `sql/sys_vars.cc:4356-4364`; `sql/sys_vars.inl:44` | Session variable; `SESSION_VAR` binds `offsetof(SV, X)` → reads/writes the **session-default struct**, not the live per-transaction flag |
| Live per-trx flag | `sql/transaction.cc:60,163-165` | `thd->tx_read_only` copied from default at start; set true by `START TRANSACTION READ ONLY` |
| Protocol status bit | `sql/handler.cc:1396-1402`; `sql/transaction.cc:210-211` | `SERVER_STATUS_IN_TRANS_READONLY` set at real-transaction start from the live flag; surfaced in protocol server status; no SQL-visible status name found (`sql/sys_vars.cc`, `sql/sql_show.cc` negative) |
| Session tracker | `sql/transaction.cc:163-168,194-196` | `session_track_transaction_info` pushes read/read-write flags to the client on change (protocol-level, opt-in) |
| Change rules | `sql/sys_vars.cc:4318-4345` | `SET DEFAULT` blocked in active multi-statement transaction; `SET SESSION` updates default and live only outside an active transaction → mode is **session-authoritative/self-reported** |
| Per-trx write rejection | `sql/sql_parse.cc:3840-3846` (after implicit commits); command list `sql/sql_parse.cc:842-878` (38 DDL-type commands flagged `CF_DISALLOW_IN_RO_TRANS`, defined `sql/sql_class.h:7565`); `sql/sql_base.cc:1976,4412`; `sql/sql_insert.cc:560` | `ER_CANT_EXECUTE_IN_READ_ONLY_TRANSACTION` = "Cannot execute statement in a READ ONLY transaction" (`sql/share/errmsg-utf8.txt:8793-8794`) — server-side per-trx enforcement exists |
| Server-wide read-only denial | `sql/sql_parse.cc:1473-1512` (round 1) + `sql/transaction.cc:174-186` (explicit `READ WRITE` under `opt_readonly` denied unless `PRIV_IGNORE_READ_ONLY`) | Statement+table-scope enforcement with privilege exemption |
| `INNODB_TRX` | `storage/innobase/handler/i_s.cc:363-396`; `storage/innobase/trx/trx0i_s.cc:1046-1062` (round 1) | Cache skips `TRX_STATE_NOT_STARTED`; own-transaction visibility depends on refresh timing (D5) |
| PFS per-transaction event | `storage/perfschema/table_events_transactions.cc:424-427` (`ACCESS_MODE` enum READ_ONLY/READ_WRITE), columns include state/mode/isolation/autocommit/source/timers — **no user, host or statement-text column** | SQL-readable per-transaction read-only state **if instrumented** |
| PFS transaction instrument default | `storage/perfschema/pfs_instr_class.cc:261` — `global_transaction_class.m_enabled= false; /* Disabled by default */` | `events_transactions_current` is **empty by default**; enabling requires `setup_instruments`/`setup_consumers` configuration writes — state changes not performed here and not covered by this authorization |
| Identity-bearing surfaces | `storage/perfschema/table_threads.cc:53-54` (`PROCESSLIST_USER`, `PROCESSLIST_HOST`); `table_users.cc`; `table_processlist.cc` | Carry user/host → out of scope under the disposition's identity rules |
| Statement text surfaces | `storage/perfschema/table_events_statements.h:74` (`SQL_TEXT`); prepared-statement SQL text `table_prepared_stmt_instances.cc:64` | Query bodies are out-of-scope material under the disposition's identity rules |
| Session counters | `sql/sql_parse.cc:3922-3924` (`SHOW STATUS` → `execute_show_status`); `sql/sql_class.h:923` (`system_status_var`) | Cumulative session/global counters; non-mutating reads; not transaction-scoped |
| Engine status | `sql/sql_parse.cc:4226-4231`; `sql/privilege.h:643` (round 1) | `SHOW ENGINE … STATUS` gated on global PROCESS |

## 2. Findings

1. **Fingerprint**: the MariaDB signing-key fingerprint `177F4010FE56CA3336300305F1656F24C74CD1D8` is now confirmed from two further named official channels of the upstream project, byte-identical to the round-1 key and identical in fingerprint. The round-1 limitation ("no second official statement page located") is **resolved for key-material channels**. Note honestly: these channels *publish the key*; none of the probed pages states the fingerprint as literal text — textual-fingerprint publication was not found.
2. **Witness-possibility review**: MariaDB 10.11.14 does maintain a genuine per-transaction read-only state (`thd->tx_read_only`) with server-side enforcement (disallow-list + change-data denial + explicit read-only-transaction error) and several non-mutating observation points. However, each reviewed surface fails at least one compliance dimension:
   - `@@tx_read_only` — SQL-readable, non-mutating, identity-free, but reads the **session default**, not the current transaction's live mode; and the mode is session-authoritative (self-reported).
   - `SERVER_STATUS_IN_TRANS_READONLY` — truthful per-transaction and non-mutating, but protocol-status only (not SQL-queryable) and same-session self-consistency, not independent.
   - PFS `events_transactions.ACCESS_MODE` — the closest SQL-per-transaction, identity-free, text-free candidate, but **disabled by default**; activating it is a configuration write requiring its own authorization and side-effect assessment (disposition D2), and it still observes only the same session's self-consistent state.
   - `INNODB_TRX` — engine-level with the documented D5 skip/timing gaps.
   - `SHOW SESSION STATUS` deltas — session-cumulative, not transaction-scoped.
   - Identity-bearing and statement-text surfaces — excluded by the disposition's identity/out-of-scope rules.
   - `SHOW ENGINE INNODB STATUS` — global PROCESS gate (D7).
   - Attempting writes to "test" rejection — prohibited regardless of outcome (disposition), so unusable as a probe.
3. **Synthesis**: within the reviewed paths, no construct simultaneously provides non-mutation, per-transaction truthfulness, identity-freeness, and **independent attestability**. The last dimension cannot originate inside the server: independent attestation is a custody matter, excluded from this scope and reserved to governance (custodian cannot self-accept; AI review is not independent human custody). The source review does **not** prove a compliant witness impossible — no impossibility proof was established. It narrows the question: any candidate must (i) rest on a separately qualified comparison of only preapproved non-identifying bounded classifications (disposition D8), (ii) close the D5 timing/visibility gap by design, and (iii) obtain independent attestation externally — none of which this round provides, proposes, or qualifies.

## 3. Limitations

- Source review only: no compilation, no execution, no runtime confirmation, no target access; all statements are about upstream 10.11.14 code as archived, not about any running system.
- Code reading is bounded to the paths cited; adjacent logic (binlog interactions, replication, Galera/wsrep branches beyond the lines quoted) was not exhaustively reviewed.
- PFS consumer-flag defaults (`table_setup_consumers.cc`) were not individually asserted beyond the instrument-class default, which alone gates event availability.
- Fingerprint textual-publication search was bounded to the listed official endpoints; absence there is not proof none exists.

## 4. Verified items

1. Fingerprint `177F4010FE56CA3336300305F1656F24C74CD1D8` confirmed from two further official upstream channels; all three key files byte-identical (digest recorded in §1).
2. Existence, semantics and source locations of the per-transaction read-only state, its enforcement paths, and each observation surface listed in §1's table.
3. Transaction-instrument default state (disabled) as recorded.
4. Preservation invariants of this round: exact numeric core `10.11.14` and accepted historical full reference `10.11.14-MariaDB-0ubuntu0.24.04.1` untouched; changed-or-unrecognized-suffix → UNKNOWN rule untouched (no new suffix comparison performed); no independent human adjudicator; custodian cannot self-accept custody evidence; AI review is not independent human custody; prior unauthorized inspection unverified and excluded; owner-approved weaker-assurance historical baseline remains a historical reference only.

## 5. Unverified items

- Everything carried forward from the provenance analysis (prior review transcripts/qualifications; current target and runtime string; owner handoff record; earlier feasibility-document citations; incident-exclusion completeness; binary-package build provenance), all still unverified by design or by exclusion.
- Whether a compliant witness can ultimately be constructed (open — see §2.3; no position of acceptance or rejection is taken).
- Whether enabling PFS transaction instrumentation would be permitted under any future side-effect assessment (not assessed; not authorized).
- Whether textual fingerprint statements exist on further official pages not probed.

## 6. Unresolved questions

1. Whether the project publishes the fingerprint as literal text on any official page (only key-material publication confirmed so far).
2. How a candidate witness would establish **independence** of observation from the observed session without a custody/attestation mechanism — outside server source and outside current scope.
3. Whether a non-mutating correlation exists that closes the D5 timing gap for not-started/just-started transactions (not found in reviewed paths; not exhaustively searched).
4. Whether the bounded-classification comparison method required by D8 can be separately qualified (design question, separate authorization).

## 7. Separated decisions (none decided here)

**Business/owner decisions**: acceptance-authority/evidence destination; any compatible custody-acceptance process; external-human-acceptor selection (remains unselected); any no-adjudicator rule change; retention/baseline amendments (restating baseline = no new decision; changing = owner decision); whether to accept this analysis as an input (no recommendation).

**Authorization decisions (none granted here)**: any configuration change to performance_schema (instrument/consumer enablement); any extended source review beyond cited paths; any second-round retrieval beyond the named channels; any sanitized-incident-manifest scope; any named-environment scope; any target, credential, custody, administrative, privilege, provisioning, testing, qualification or deployment scope; any acceptance, catalog-freeze or execution authority.

## 8. Minimum next authorization

A source-and-document-only step limited to: (a) locating a textual fingerprint statement on one further named official project page **or** formally recording key-material-only confirmation as the settled assurance level, and (b) a design-document exercise (document-only) sketching, without implementation, what a bounded-classification witness would need per D8/D5 — or, alternatively, closing this analysis as sufficient for the feasibility record — under the same exclusions as this round. A scope description only; it grants nothing and recommends no acceptance, catalog freeze, or execution grant.

P00/G0, H01 and H02 remain open; P1 deferred; P2 implementation, disposable-lab provisioning and native testing paused.
