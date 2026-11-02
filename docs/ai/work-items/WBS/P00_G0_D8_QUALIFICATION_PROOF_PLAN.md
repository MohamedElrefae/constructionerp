# P00/G0 — D8 qualification-proof plan (Phase E), 2026-11-01

**Status: PLAN ONLY — source-and-document-only; no execution, no test run, no observation, no custody act, no acceptance.** Baseline: Gate D selections **D2 destination (not created/accessed) · C3 no acceptance · acceptance authority undesignated · R2 retention classes + B2 encryption/backup**. Bound artifacts: D8 REV_03 `bbe59661…dc10322`; spec REV_02 `0a3aa5c6…98328e`. Verification: MiMo-V2.6-Flash (technical separation only). Gate remains BLOCKED.

## 1. Exact evidence required for each Q1–Q8 class (per class, per spec REV_02)

| Class | Evidence to be produced (when separately authorized) | Producing mode |
|---|---|---|
| Q1 read-path inventory | closed channel manifest (surface, field, type, cardinality); design-level read-set enumeration; source-level read-path review with file/line refs | source-and-document-only |
| Q2 value-domain proof | per-field worst-case domain enumerations; exclusion rationale (free-text / user-host-credential / server-generated identity-embedding strings) | source-and-document-only |
| Q3 handle lifecycle | construction record (non-principal), uniqueness scope, resolvability analysis, lifecycle incl. never-carried-across-assessments | design + document review (source-level) |
| Q4 adversarial negative-search | adversarial class outcomes, residual-risk statement, class withdrawals | source-and-document-only (class-level reasoning) |
| Q5 no-passthrough proof | emission-site→constant map; closed vocabulary proof; transform-absence analysis | source-and-document-only |
| Q6 re-identification analysis | auxiliary-category attack analysis; coarsening decisions | document-only |
| Q7 redaction-method qualification | predicate worst-case analysis; at-risk record; coarse-leak check design | source-and-document-only analysis; **adversarial tests only under separate grant**; sufficiency claims remain INCOMPLETE until such test evidence exists |
| Q8 package review | review record under technical separation (findings, severities, resolutions) | document-only |

## 2. Required observation mechanism (requirements; no mechanism selected)

Server-produced state read-only; non-mutating w.r.t. data/config/counters-as-credentials; available without any configuration change (PFS enablement excluded); never session-self-report alone; emits only preapproved bounded classifications; no write attempts (including rejected). Candidate classes remain those surveyed in provenance records; none selected.

## 3. Transaction-correlation method

Same-server, same-connection, uninterrupted correlation; server-side start marker required before any observation; opaque ephemeral handle (non-principal construction, single-assessment scope, destroyed at record close); invalidation on reconnect/handle reuse/restart/pool switch ⇒ UNKNOWN; correlation record contents fixed (handle token, marker presence, continuity flag, observation points, **surface identities**, timestamps).

## 4. Visibility evidence

Per-surface freshness bound with maximum age; positive start-proof before any observation (absence never evidence); two-dimension consistency required of any match candidate; per-surface refresh characterization required **before** that surface may support a match (D5 closure); surfaces lacking characterization may not support a match (INCOMPLETE).

## 5. Redaction boundary

Closed vocabularies only (C1–C6, E1–E4, statuses, fixed reason set); at-risk predicate assessed per statement; coarse-status leak check before every emission; suppressed absolutely: identities, credentials, query bodies, unexpected values, indirect identifiers, hostnames/usernames, free-text server output; uncertain redaction ⇒ withhold ⇒ INCOMPLETE (never a pass).

## 6. Failure-record format (fixed fields)

`attempt_id` (opaque) · `timestamp_utc` · `package_id` · `surface_class` · `correlation` {handle token, start-marker present, continuity} · `freshness` {bound, age class} · `class_outcomes` {per dimension C1–C6} · `status` {UNKNOWN|INCOMPLETE|FAIL} · `reason` {fixed enum} · `redaction_decision` {emitted|withheld} · `preservation_state` {visible|redacted-record|withheld} · `integrity` {prev digest, this digest} · `pending` {items awaiting owner designation, e.g. integrity anchoring}. Immutable-append; one entry per attempt; confirmed FAIL visible when safe; never erased by incompleteness; co-occurrence derivation yields exactly one final status per stop event.

## 7. Provenance and integrity controls (baseline-adjusted)

- Version binding: exact recorded references (`10.11.14` / `10.11.14-MariaDB-0ubuntu0.24.04.1`); changed or unrecognized suffix ⇒ UNKNOWN.
- Digest binding of design inputs (D8 REV_03, spec REV_02, this plan) and of every evidence artifact.
- Incident/target-derived input screening at ingestion; any suspicion ⇒ stop, UNKNOWN, no incident-specific observation recorded.
- D2 destination: records destined for the owner-managed encrypted store **once authorized**; nothing is written now.
- B2: encryption at rest with owner-held key; restore-tested backup — configurations are future actions, not performed here.
- Invalidation authority (V1–V3) **undesignated**: record invalidation is a pending owner decision; no invalidation mechanism is selected.
- Integrity anchoring (I1–I3) **undesignated**: records carry local digest chains (tamper-evident only) and each record marks `integrity_anchoring: PENDING_OWNER_DESIGNATION`.
- C3: no acceptance step exists; records remain unaccepted inputs; no attestation chain claim is made.

## 8. Stop conditions (inherited, twelve, baseline-adjusted)

Exposure risk ⇒ INCOMPLETE (withhold); redaction uncertainty ⇒ INCOMPLETE; correlation invalidation ⇒ UNKNOWN; freshness/visibility gap ⇒ INCOMPLETE; version mismatch ⇒ UNKNOWN; out-of-vocabulary ⇒ UNKNOWN; unqualified method ⇒ UNKNOWN on classification fact; missing/incomplete authorization record ⇒ UNKNOWN; suspected incident/target-derived input ⇒ UNKNOWN; integrity break ⇒ FAIL where safe (observation/failure context) with provenance-context failures governed separately (UNKNOWN/INCOMPLETE); need for excluded activity (config/write/target/identity/provisioning/testing) ⇒ stop (INCOMPLETE if evidence exists but scope cannot proceed, else UNKNOWN); unexpressible output ⇒ UNKNOWN. No broader-access retry; stopped attempt ≠ completed campaign.

## 9. Test cases and expected classifications (definitions only — no execution; execution requires separate authorization)

| # | Case (description only) | Expected classification |
|---|---|---|
| T1 | read-only transaction, correlation intact, freshness within bound, two dimensions consistent | eligible path (E1 consideration only) |
| T2 | reconnect mid-attempt | UNKNOWN (correlation invalidated) |
| T3 | transaction record absent / not-started per D5 | UNKNOWN (absence not evidence) |
| T4 | redaction sufficiency uncertain for a value statement | INCOMPLETE (withhold) |
| T5 | version suffix changed or unrecognized | UNKNOWN |
| T6 | comparison attempted without qualification proof | UNKNOWN (unqualified comparison, on classification fact) |
| T7 | digest mismatch on observation record | FAIL where safe; INCOMPLETE if failure statement itself leaks |
| T8 | output value outside closed vocabulary | UNKNOWN |
| T9 | authorization record absent/incomplete | UNKNOWN |
| T10 | suspected incident-derived input | UNKNOWN; no incident-specific observation |
| T11 | need for configuration change (incl. PFS enablement) | stop; INCOMPLETE/UNKNOWN by reason |
| T12 | exposure risk at input/output | INCOMPLETE (withhold) |

## 10. Evidence-package structure (planned layout only; nothing created)

Per package `pkg-<class>/`: `manifest.json` (inputs, digests, version binding, source refs) · `evidence/` (Q-specific artifacts) · `redaction/` (predicate record, withheld-values log in class terms) · `failures/` (failure/stop records per §6) · `review/` (Q8 record) · `integrity/` (digest chain, anchoring placeholder marked PENDING). Packages are defined here as a plan; **no directory or file is created** until a separate owner authorization permits arrangement setup and evidence production.

## 11. Independent review requirements

Q8 review under technical author/reviewer separation; reviewer ≠ author; conflicts declared per undesignated-attestation note (A1–A3 unselected); disagreements recorded, never erased; rule-affecting disagreements escalate to the owner; review is **not** independent human custody, **not** acceptance (C3), and does not qualify the method.

## 12. Feasibility inputs (for Phase F)

Source-and-document-only classes (Q1, Q2, Q3 design record, Q4 class-level, Q5, Q6, Q7-analysis, Q8) are producible under the existing boundary. Runtime-dependent evidence (live correlation/visibility evidence, Q7 adversarial tests, any target-side observation) requires new owner authorization (Gate G/I). Under C3, closure remains impossible by design (no acceptance step exists) — this is consistent with the preserved rules and is not a defect.

P00/G0, H01, H02 open/BLOCKED; P1 deferred; P2 paused.
