# P00/G0 MariaDB — D8 qualification-design specification for precondition B.7.4 (document-only), 2026-11-01

**Status: DESIGN SPECIFICATION ONLY — requirements and evidence standards, no implementation, execution, testing, configuration or qualification act.** This document defines what a future D8 qualification of the bounded-classification comparison method would have to prove, control, and be authorized to do. It does not qualify any method, select any mechanism or surface, execute any proof, or authorize any operation. **This document grants no acceptance, catalog-freeze, execution, custody, qualification, or target-verification authority. The workstream gate remains BLOCKED.** AI review is not independent human custody; no independent human adjudicator participates; the custodian cannot self-accept custody evidence; the prior unauthorized inspection remains unverified and excluded (no incident-derived material informed this document); the owner-approved weaker-assurance historical baseline remains a historical reference only.

Preserved exactly: numeric core `10.11.14`; accepted historical full reference `10.11.14-MariaDB-0ubuntu0.24.04.1`; changed or unrecognized suffix classified **UNKNOWN**. Terminology follows the legend of `P00_G0_MARIADB_FEASIBILITY_REVIEW_DISPOSITION_REV_05_2026-10-31.md` (UNKNOWN = fact not established; INCOMPLETE = evidence exists but insufficient, unauthenticated, or cannot be safely preserved or concluded; FAIL remains independently visible when safe; BLOCKED is gate status).

Version binding: this specification is bound to the stable D8 input-candidate artifact `P00_G0_MARIADB_D8_BOUNDED_CLASSIFICATION_DRAFT_REV_03_2026-11-01.md`, SHA-256 `bbe596610537583e370ff7319a44acda588b5c9cefcf50e10f5366c9adc10322` (per its closure record), and to the settled witness precondition list (sketch B.1–B.7). A change to either artifact voids this binding and requires re-issue of this specification.

## Part 1 — Evidence required to prove that neither inputs nor outputs reveal identities

The D8 qualification requires an independently reviewable proof package. Evidence classes below are **requirements on that package**, not the package itself; none has been produced, and producing this design qualifies nothing. All proofs must be **worst-case (universal)** over the defined domains; any claim resting on sampling or typical-case testing is recorded **INCOMPLETE**, never a proof.

### 1.1 Input-side proof (no identity enters the comparison)

- **E1 Input-inventory completeness**: a closed manifest of every input channel the method reads (surface, field, type, cardinality), each mapped to a fixed preapproved class from the stable artifact's enumeration. Completeness must be established by design-level enumeration of the method's full read set (interface declaration plus source-level read-path review), not by observation of observed traffic.
- **E2 Input value-domain proof**: per input field, an enumeration of its possible values demonstrating that no free-text, no user/host/credential-bearing field, and no server-generated string capable of embedding identity can enter. Analysis is per field, worst-case.
- **E3 Opaque-handle non-carry proof**: for every correlating handle: construction (not derived from username, host, account, or any principal attribute), uniqueness scope (single assessment), resolvability (no back-channel resolves handle to principal within the method's reach), and lifecycle (created per assessment; destroyed at record close; never carried across assessments).
- **E4 Negative-search evidence**: a documented adversarial search of the input space for any value or combination that could encode or re-derive identity (including indirect identifiers: timestamps joined to external data, ordering, cardinality patterns), with the residual-risk statement it produces. Residual risk that cannot be bounded forces the affected input's class to be withdrawn (stop, §4).

### 1.2 Output-side proof (no identity leaves the comparison)

- **E5 Output-domain proof**: every emitted value belongs to a closed constant vocabulary — the classification codes C1–C6, expected-class codes E1–E4, statuses UNKNOWN/INCOMPLETE/FAIL, and a fixed enumerated reason set. **No-passthrough proof**: no output value is, derives from, or is a transformation of any server-observed value; outputs are label constants only.
- **E6 Re-identification analysis**: an adversarial analysis of the complete output record (labels, statuses, reasons, timing granularity, handle) against realistic external auxiliary data, bounding what re-identification would require; any field whose retention is not necessary for the record's purpose must be coarsened or dropped (least-data rule).
- **E7 Redaction-method qualification**: documented redaction predicates with worst-case input analysis, the "at risk" predicate applied per statement, and — under a future separately authorized scope — adversarial test evidence; until such evidence exists, the redaction method's sufficiency claims are **INCOMPLETE**.
- **E8 Independent review of the package**: the complete proof package must be reviewed under technical author/reviewer separation; such review is not independent human custody, is not acceptance, and does not by itself qualify the method.

### 1.3 Proof outcome classification

Proof outcomes: **met** (all evidence classes satisfied worst-case), **unmet** (a class fails), or **incomplete** (evidence insufficient/unauthenticated). Unmet or incomplete ⇒ the comparison may not proceed; the attempt records **UNKNOWN** (unqualified comparison, per the stable artifact's rule 10) and stops. "Met" records eligibility for the separate authorization step (Part 3) — it is never itself an acceptance, qualification act, or gate change.

## Part 2 — Required controls (transaction-correlation, visibility, redaction, failure-record, provenance, integrity)

1. **Transaction-correlation controls**: same-server, same-connection, uninterrupted correlation across all observation points; server-side transaction start marker required before any observation; correlation record contents (opaque ephemeral handle, start marker, observation points, timestamps, surface identities); automatic invalidation on reconnect, thread-id reuse, server restart, or pool switch ⇒ **UNKNOWN**, never a match; handle lifecycle per E3.
2. **Visibility controls**: a defined maximum-age freshness bound per surface, enforced at collection; positive start-proof before any observation (absence is never evidence — D5); two-dimension consistency required of any match candidate (requirement class; dimension choice undecided); no surface's visibility assumed beyond the recorded source review; any surface lacking characterized refresh timing may not support a match (**INCOMPLETE** until characterized under its own authorized scope).
3. **Redaction controls**: only preapproved non-identifying classifications, statuses, reasons and opaque handles cross the boundary; the "at risk" predicate assessed per statement; uncertain redaction ⇒ withhold ⇒ **INCOMPLETE**; a coarse-status leak check before every emission; suppression of identities, credentials, query bodies, unexpected values, indirect identifiers, hostnames/usernames and free-text server output as inputs and outputs alike.
4. **Failure-record controls** (D13 pattern): a fixed record format; every attempt produces exactly one record entry (classified outcome, stop, or failure); confirmed **FAIL** remains visible when safe and is never converted or erased; leak-risk ⇒ withhold the value, preserve the failure in the attestable redacted record where safe, and mark the attempt and overall assessment **INCOMPLETE**; a missing record or an incomplete state may never erase a known failure; the co-occurrence derivation of the stable artifact (one final status per stop event; UNKNOWN if any co-trigger's reason is an unestablished fact, otherwise INCOMPLETE; no conversion; no pass) governs all records.
5. **Provenance controls**: version binding of every input and surface to the exact recorded references (changed or unrecognized suffix ⇒ **UNKNOWN**); digest-binding of every design input artifact (including the stable D8 artifact and this specification); point-in-time records with timestamps; input-proprovenance screening that rejects any incident-derived or target-derived material; no reliance on unofficial mirrors, prebuilt binaries, or unauthenticated sources anywhere in the chain.
6. **Integrity controls**: records are immutable-append with a digest chain (each entry bound to its predecessor); tamper-evidence on any alteration or reordering; separation of recorder from acceptor (the attester/observer never accepts its own record — the custodian cannot self-accept custody evidence); the **protected integrity-reference destination remains an owner decision** (Part 5) and, until designated, record integrity is at best technical tamper-evidence, not custody.

## Part 3 — Separate authorization record required before any B.7.4 use

No B.7.4 use of the classification comparison may occur without a prior, complete, separately issued authorization record containing, at minimum:

1. Named scope: the exact operation, surfaces, session context, and the digest-bound version of the classification set/expected classes (the stable artifact binding in this document's header).
2. Reference to the qualification proof package (Part 1) with outcome "met", and to the control set (Part 2) as implemented-by-design.
3. Named roles: observer/recorder, acceptor, and evidence destination — with the governance checks recorded: acceptance authority designated (owner decision), custodian ≠ acceptor of its own evidence, no independent human adjudicator participating, AI review identified as not independent human custody, external human acceptor selected-or-not by owner decision.
4. Retention and destruction decisions: record lifetime, handle destruction point, redacted-record retention, and the protected integrity-reference destination (owner decision).
5. The stop-condition acknowledgment (Part 4) and the exclusions list (no target access of any kind, no target writes including rejected attempts, no identity collection, no incident-derived material, no custody acts, no configuration changes, no provisioning/implementation/testing/qualification/deployment, no unofficial mirrors/prebuilt binaries/target-derived artifacts).
6. The exact version context (numeric core and full reference) and an explicit statement of what the authorization does not grant (no acceptance, catalog freeze, execution, custody, qualification or target-verification authority beyond the named scope).

An absent, incomplete, or internally inconsistent authorization record ⇒ the attempt stops and records **UNKNOWN** (the required fact is not established); a record that conflicts with the governance constraints is not curable by inspection — it returns to the owner (Part 5).

## Part 4 — Stop conditions and failure classifications

**Stop conditions** (any one halts the attempt; each records exactly one status by the stable artifact's mapping):
1. Any exposure risk to identities, credentials, query bodies, suppressed values, or other out-of-scope data, at input or output ⇒ **INCOMPLETE** (withhold).
2. Redaction sufficiency uncertain ⇒ **INCOMPLETE**.
3. Correlation invalidated (reconnect, handle reuse, restart, pool switch) ⇒ **UNKNOWN**.
4. Freshness unprovable or surface visibility uncharacterized ⇒ **INCOMPLETE**.
5. Version-context mismatch (changed or unrecognized suffix, or missing version binding) ⇒ **UNKNOWN**.
6. Any unapproved value outside the closed vocabularies (labels, statuses, reasons) ⇒ **UNKNOWN**.
7. Method unqualified (proof outcome not "met") or qualification evidence incomplete ⇒ **UNKNOWN** (unqualified comparison), per the stable artifact's rule 10.
8. Authorization record absent, incomplete, or inconsistent ⇒ **UNKNOWN** (Part 3).
9. Any suspected incident-derived or target-derived input material ⇒ **UNKNOWN** (exclusion fact not established); the attempt stops and no incident-specific observation is recorded.
10. Any integrity-chain break in the record or its inputs ⇒ **FAIL**, preserved visible when safe, never a pass; withhold and mark **INCOMPLETE** where the failure itself is at risk of leaking a suppressed value.
11. Any need for a configuration change (including `performance_schema`), a write attempt (including rejected), target access, identity collection, provisioning, or testing ⇒ stop; the attempt records **INCOMPLETE** if evidence exists but the authorized scope cannot proceed, otherwise **UNKNOWN**.
12. Any output value that cannot be expressed in the closed vocabularies ⇒ **UNKNOWN** (out-of-enumeration rule of the stable artifact).

**Failure classification discipline**: one status per condition; UNKNOWN and INCOMPLETE distinct and non-interchangeable, neither converting to the other or to a pass; co-occurring stops resolved by the stable artifact's co-occurrence derivation (exactly one final status per event; UNKNOWN if any co-trigger's reason is an unestablished fact, otherwise INCOMPLETE); FAIL independently visible when safe; BLOCKED unchanged as gate status and never inferable from any record.

## Part 5 — Separated decisions reserved to the owner (none decided or recommended here)

**Business/owner decisions (reserved):**
- Designation of the acceptance authority and the protected integrity-reference/evidence destination.
- Any compatible custody-acceptance process (custodian-cannot-self-accept prohibition unchanged); selection or continued non-selection of an external human acceptor (currently unselected).
- Any change to the no-independent-human-adjudicator rule (explicit owner decision required if ever needed).
- Retention and destruction schedules; any identity-handling decision (none currently authorized); any amendment to the owner-approved weaker-assurance historical baseline (restating needs no new decision; changing does).
- Whether this qualification-design specification is accepted as an input to the workstream record, and whether any qualification effort is ever commissioned at all.

**Authorization decisions (reserved; none granted):**
- The Part 3 authorization record itself, if ever issued.
- Any scope to execute the qualification proof (including any future adversarial testing, which would require its own explicit grant).
- Any observation or comparison operation; any runtime or target-side scope; any configuration change including `performance_schema`; any extended source review; any sanitized-incident-manifest scope; any named-environment scope; and any target, credential, custody, administrative, privilege, provisioning, testing, qualification or deployment scope.

## Limitations

Document-only; no method, mechanism or surface is selected; no proof, test, or observation was executed; no runtime knowledge of any system is reflected; the specification itself qualifies nothing and satisfies no part of precondition B.7.4 (it is a design of the evidence standard, not the evidence); nothing here may be read as an execution grant or as a recommendation of acceptance, catalog freeze, or execution.

P00/G0, H01 and H02 remain open; P1 deferred; P2 implementation, disposable-lab provisioning and native testing remain paused.
