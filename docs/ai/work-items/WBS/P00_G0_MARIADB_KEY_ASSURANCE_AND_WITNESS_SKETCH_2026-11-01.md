# P00/G0 MariaDB — key-assurance settlement and bounded-classification witness sketch (document-only), 2026-11-01

Verdict: **assurance level SETTLED as key-material-only confirmation; witness requirements SKETCHED as requirements only — no candidate selected, assessed, or qualified; workstream gate remains BLOCKED.** This document is source-and-document-only. It implements nothing, configures nothing (including `performance_schema`), tests nothing, provisions nothing, qualifies nothing, authorizes nothing. It grants no acceptance, catalog-freeze, or execution authority, verifies no target, and authorizes no reliance on the historical baseline for a new operation. AI review is not independent human custody; no independent human adjudicator participates; the custodian cannot self-accept custody evidence; the prior unauthorized inspection remains unverified and excluded (no incident-derived material was used); the owner-approved weaker-assurance historical baseline remains a historical reference only.

Exclusions observed in full: no target access of any kind; no target writes including rejected write attempts; no identity collection; no incident-derived material; no custody acts; no `performance_schema` configuration changes; no unofficial mirrors, prebuilt binaries or target-derived artifacts; no provisioning, implementation, testing, qualification or deployment. Record timestamp (UTC): 2026-10-31T23:35:15Z.

Preserved exact-matching requirements (untouched): numeric core `10.11.14`; accepted historical full reference `10.11.14-MariaDB-0ubuntu0.24.04.1`; changed or unrecognized suffix classified **UNKNOWN** (no new suffix comparison was performed in this round).

## Part A — Formal recording of the settled assurance level (signing-key fingerprint)

**Settled assurance level: key-material-only confirmation.** The MariaDB signing-key fingerprint `177F4010FE56CA3336300305F1656F24C74CD1D8` is confirmed to the level of: three official upstream key files, published by the upstream project on three separate named official channels, which are byte-identical to each other and each of which independently computes to the settled fingerprint.

Basis of record (as established in rounds 1–2 and re-verified read-only at this settlement):

| Channel | File | Local SHA-256 (re-verified this round) |
|---|---|---|
| `archive.mariadb.org/PublicKey` | key file | `00adb387f4c12e8982cfc28165d225695621494354cd58108c6845063bfb74b5` |
| `mariadb.org/mariadb_release_signing_key.pgp` | key file | `00adb387f4c12e8982cfc28165d225695621494354cd58108c6845063bfb74b5` |
| `mirror.mariadb.org/yum/RPM-GPG-KEY-MariaDB` | key file | `00adb387f4c12e8982cfc28165d225695621494354cd58108c6845063bfb74b5` |

Supporting facts of record: the tarball detached signature verifies Good from this key over the locally digested tarball (round 1); the key carries only self-signatures (no cross-certification exists or is claimed); no official page probed so far states the fingerprint as literal text; all key retrieval was read-only over HTTPS from the named official channels.

**Recorded as settled:** key-material-only confirmation is accepted as the assurance level for the current provenance record. **Recorded as available upgrade, not required:** publication of the fingerprint as literal text on a further official project page would be a possible stronger-assurance upgrade; it is *not required* for the current provenance record, and its absence does not raise any discrepancy against the settled record. The settled level is explicitly bounded: it establishes key identity and signature validity for provenance purposes only; it is not custody, not acceptance, and not qualification.

## Part B — Document-only sketch: requirements for a D8/D5-conformant bounded-classification witness

**Status of this sketch:** requirements elicitation only, derived from the disposition's rules (D8 identity boundary, D5 timing/visibility, D13 status taxonomy) and from the source-review findings recorded in the provenance documents. It selects no mechanism, names no tool, approves no configuration, and makes no claim that any compliant witness exists. Nothing here is implemented, tested, or authorized; nothing here may be read as an execution grant.

**Recording status (settled precondition list):** under a source-and-document-only continuation authorization dated 2026-11-01, the witness requirements in Part B (B.1 through B.7) are hereby **recorded as the feasibility record's settled precondition list** — the fixed preconditions against which any future candidate witness must be evaluated before assessment is even possible. Recording does not qualify any method, select any mechanism, assess any candidate, or authorize anything; the list's substance and its unfulfilled prerequisites (B.7) remain exactly as written. The same continuation commissioned a document-only consistency pass of this sketch against `P00_G0_MARIADB_FEASIBILITY_REVIEW_DISPOSITION_REV_05_2026-10-31.md` (recorded in `P00_G0_MARIADB_WITNESS_SKETCH_CONSISTENCY_PASS_2026-11-01.md`) and a document-only draft of the D8 bounded-classification proposal (recorded in `P00_G0_MARIADB_D8_BOUNDED_CLASSIFICATION_DRAFT_2026-11-01.md`). Any wording findings from that pass are recorded there with proposed fixes pending authorization; no fix has been applied to this document beyond this recording statement.

### B.1 Required observation mechanism (requirements, not selection)

1. Must observe **server-produced state** read-only: every read path must be non-mutating with respect to target data, server configuration, and counters-as-credentials; no write attempt — including rejected attempts — may be used as a probe.
2. Must be obtainable **without any configuration change**: surfaces whose availability depends on enabling instruments/consumers (e.g., `performance_schema` transaction events, disabled by default per `pfs_instr_class.cc:261`) are ineligible unless a future, separately authorized side-effect assessment says otherwise; that assessment is out of scope and not made here.
3. Must not rely on **session-self-reported state alone**: variables or flags the observing session itself can set (e.g., session-default `tx_read_only` semantics) may be inputs but never the sole basis of a match, because they are self-attestation, not observation of enforcement.
4. Must emit only a **bounded classification** from a fixed preapproved set against fixed expected classes (D8); the raw observation values must never cross the boundary. The set itself is unselected in this sketch; any actual set requires D8's separately qualified method proving neither inputs nor outputs reveal identities, plus separate authorization.
5. Must respect the out-of-scope list: identities, credentials, query bodies, unexpected values, indirect identifiers — excluded as inputs and outputs alike.

### B.2 Transaction-correlation evidence (requirements)

1. Same-server, same-connection, **uninterrupted** correlation between observation points: any reconnect, thread-id reuse, server restart, or connection-pool switch invalidates the correlation → UNKNOWN, never a match.
2. Correlation anchor must be an **opaque, non-identifying session handle** plus server-side transaction start markers; the handle is ephemeral and may not be retained beyond the bounded record.
3. **Absence is not evidence**: a transaction record that is absent, not-started, or not yet visible (D5's skipped `TRX_STATE_NOT_STARTED`) classifies as UNKNOWN — it may never be mapped to read-only or to a pass.
4. The record must show *when* the correlation was established relative to transaction start (B.3), or the correlation is INCOMPLETE.

### B.3 Visibility evidence (requirements)

1. **Freshness bound**: every observation must be timestamped with a defined maximum age relative to the transaction event observed; a surface with uncharacterized refresh timing (D5's cache timing) may not support a match until its timing is characterized under a separately authorized scope.
2. **Start-proof before match**: the mechanism must positively establish that the transaction started (server-confirmed start marker), not infer it from an empty result.
3. **Two-dimension consistency (requirement class, not selection)**: a match candidate would need consistency between (a) declared/enforced mode state and (b) an independent enforcement-observable dimension; the choice and validity of dimensions is undecided and requires the evidence in B.7.
4. Visibility claims are bounded to what the source review showed each surface can and cannot display (recorded provenance documents); no surface's visibility may be assumed beyond that.

### B.4 Redaction boundary (requirements)

1. Permitted across the boundary: only preapproved non-identifying bounded classifications and opaque ephemeral handles; fixed expected classes.
2. Suppressed absolutely: raw identities, credentials, query bodies, unexpected values, indirect identifiers, hostnames/usernames, and any free-text server output that could embed them.
3. **Uncertain redaction ⇒ INCOMPLETE** (D8/legend): if redaction sufficiency cannot be established for any input or output, withhold the value and mark the attempt and overall assessment INCOMPLETE; never emit an unredacted or partially understood value.
4. **Record redaction**: confirmed adverse observations must be preserved in an independently attestable redacted record where safe; if even a coarse status could reveal a suppressed value, withhold it; a missing record or incomplete state may never erase a known failure (disposition D13 rule).
5. The redaction method itself requires D8's separately qualified proof (neither inputs nor outputs reveal identities) — evidence not yet held (B.7).

### B.5 Independence and attestation requirements (constraints; nothing selected)

1. Technical independence first: observation must be independent of the session's self-report (B.1.3) and recorded immutably relative to the observer (protected integrity reference destination remains an owner decision — unresolved).
2. **Role separation preserved**: the attester/observer does not accept its own record; the custodian cannot self-accept custody evidence; the acceptance authority remains undesignated; an external human acceptor remains an unselected option; no independent human adjudicator participates; AI review is not independent human custody.
3. Consequently, **no attestation chain can be completed inside this sketch**: independence of acceptance is a governance precondition (owner decisions) that must precede any candidate assessment; this sketch selects no role and assumes no compatibility with existing rules.
4. Any attestation design must pass conflict checks and independent attestation per the disposition's unresolved governance paragraph — unresolved, and not resolved here.

### B.6 Failure and stop conditions (requirements)

STOP (record UNKNOWN or INCOMPLETE and stop; never a match):
1. Any need for target access, a write attempt (even rejected), identity collection, incident-derived material, `performance_schema` or any configuration change, provisioning, or testing.
2. Correlation integrity lost (B.2.1) ⇒ UNKNOWN (the fact of same-transaction identity is not established); freshness unprovable (B.3.1) ⇒ INCOMPLETE (evidence exists but is insufficient to conclude).
3. Unmatched or indeterminate classification (classifications whose values the record cannot establish) ⇒ UNKNOWN; any value outside the fixed preapproved sets ⇒ UNKNOWN; any redaction uncertainty (B.4.3) ⇒ INCOMPLETE (evidence exists but cannot be safely concluded).
4. Version context mismatch: changed or unrecognized suffix relative to the recorded references ⇒ **UNKNOWN**.
5. Any exposure risk to suppressed values at output time (including coarse status leaks).
6. Trust-chain break for any input artifact (digest/signature mismatch) — records the provenance failure as FAIL where safe, never a pass.

Failure preservation: confirmed FAIL remains visible when safe and may never be silently converted to pass or erased by an incomplete state (D13).

### B.7 Evidence required before any candidate could be assessed (prerequisite list; none held or granted here)

1. **Timing characterization** of the candidate surface's refresh/visibility semantics for not-started/just-started transactions (closes D5 for that surface) — requires a separately authorized scope; runtime work excluded here.
2. **Non-mutation proof** for the read path: source-level argument (partially available from the recorded source review) plus, later, runtime evidence under its own authorization.
3. **Correlation-marker availability proof**: existence and stability of server-side start markers and opaque handles under the recorded version (source evidence partly recorded; runtime confirmation excluded).
4. **D8 qualification of the comparison method**: independent proof that neither inputs nor outputs reveal identities, with an enumerated fixed classification set and expected classes.
5. **Redaction-method qualification** and the safe-failure record design (D13), independently reviewable.
6. **Threat matrix and least-data analysis** for the exact statement/engine context (disposition candidate requirements).
7. **Governance decisions first**: acceptance authority and protected integrity-reference destination (owner), conflict checks, any attestation process — none decided; without them, no attestation chain exists (B.5.3).
8. **Exact version context**: recorded numeric core and full reference remain the historical reference; current target confirmation would require its own separate authorization and is not performed or implied here.

## Part C — Findings, limitations, unresolved questions, separated decisions

**Findings:** (1) the key-assurance level is formally settled as key-material-only, with the upgrade path recorded as available but not required; (2) the witness question is now expressed as seven prerequisite evidence classes and explicit stop/failure rules — the sketch converts "can a witness exist?" into auditable preconditions without asserting feasibility or infeasibility; (3) all preservation rules carried through unchanged.

**Limitations:** document-only; no mechanism selected; no candidate assessed; no code executed beyond read-only digest re-verification of already-held key files; PFS consumer defaults and adjacent server paths remain unexamined beyond prior rounds; nothing here reflects runtime knowledge of any system.

**Unresolved questions:** all carried forward (textual fingerprint publication; D5 timing closure; D8 method qualification; independence-of-observation design; PFS-enablement side-effect assessment — excluded and unassessed; witness feasibility itself), plus: which fixed classification set, if any, could ever satisfy B.1.4/B.4.5 — undecided.

**Separated decisions — business/owner (none decided):** acceptance authority/evidence destination; any custody-acceptance process; external-human-acceptor selection (unselected); any no-adjudicator rule change; retention/baseline amendments (restating baseline needs no new decision; changing does); whether to accept this sketch as an input (no recommendation).

**Separated decisions — authorization (none granted):** any runtime or target-side observation scope; any configuration change including `performance_schema`; any D8/D4 method qualification scope; any extended source review; any sanitized-manifest or named-environment scope; any target, credential, custody, administrative, privilege, provisioning, testing, qualification or deployment scope; any acceptance, catalog-freeze or execution authority.

## Part D — Minimum next authorization

A source-and-document-only step, none of it implying feasibility: (a) close or continue the analysis — i.e., record these witness requirements as the feasibility record's settled precondition list, or commission one further document-only pass that stress-tests the sketch against the disposition for internal consistency; and/or (b) a document-only draft of the D8 bounded-classification proposal (enumerated set and expected classes) for later review — under the same exclusions as this round (no target access of any kind, no writes, no identity collection, no incident-derived material, no custody acts, no configuration changes, no provisioning/implementation/testing/qualification/deployment). A scope description only: it grants nothing and recommends no acceptance, catalog freeze, or execution grant.

P00/G0, H01 and H02 remain open; P1 deferred; P2 implementation, disposable-lab provisioning and native testing paused.
