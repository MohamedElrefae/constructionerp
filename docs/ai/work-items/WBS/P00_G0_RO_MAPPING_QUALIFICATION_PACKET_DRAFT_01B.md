# P00/G0 READ ONLY and site mapping qualification packet — draft 01b

**INDEPENDENT REVIEW: BLOCKING.** Revision 01b contains unresolved gate, scoring, evidence and role-separation contradictions; do not execute or accept the proposed schema. See review disposition at the end.

**Design and review only. NOT A GRANT, implementation, test result, or qualified method.** No target, socket, credentials, custody location, administrative state, or configuration was accessed for this packet. No environment was created and no cases run. P00/G0 and H01/H02 remain open; P1 deferred; P2 implementation, disposable-lab provisioning and native testing paused. This packet does not amend accepted artifact bytes or hashes. The previous delegate's reported unauthorized site inspection remains unverified and is excluded as evidence. No authorization for further inspection follows.

## Objective and hard gates

Determine whether an exact, bounded, independently reviewed method can (1) verify database-enforced READ ONLY for the active transaction before identity queries, and (2) establish a narrowly scoped site-to-database/socket mapping without collecting credentials or executing configuration hooks. Qualifying the lab method is not target qualification, independent target binding, runtime code binding, writer exclusion, inventory closure, implementation, or activation. Owner-approved historical baseline remains weaker assurance. Numeric MariaDB version must be exactly 10.11.14; the full reference is `10.11.14-MariaDB-0ubuntu0.24.04.1`; an altered or unrecognized suffix is UNKNOWN. Custody evidence cannot be self-accepted by its custodian; AI review is not independent human custody.

No credential, raw unexpected value, SQL/script body, user identity, document identifier or unrelated business record may be collected. Lab uses solely synthetic, non-secret fixtures; any live secret in a fixture is an immediate stop. Query text in this source-level specification is design material, not collected execution output. No broader-privilege retry after a stop. Any uncertain visibility, schema, enforcement, logging, binding or cleanup is INCOMPLETE, not absence. Successful SELECT, zero rows or `@@in_transaction=1` is not proof of enforcement or complete visibility.

## Proposed disposable environment — not provisioned

A separate isolated VM, not a container on the live bench, with default-deny networking, no live mounts, credentials, production configuration, backups or data. It must have a separately named approved root, site, DB, socket, principal, evidence destination and resource limits, all distinct from every live/rehearsal target; explicit deny rules for live sites and sockets. Proposed MariaDB 10.11.14 with identical full version only if an independently verified image/package is available; otherwise exact-target claim BLOCKED. Pin OS, server, storage engine, Frappe source revision, driver, client, helper, configuration, and verifier by version and hash; avoid claiming local checkout binds runtime. Use synthetic objects, identities and data. Privileged setup, observer and ordinary client are separately scoped. No builder retains write access to frozen candidate or evidence during validation. Supervisor controls descendants; interruption or uncertain isolation stops and invalidates run. H02 containment and S3–S5 remain unqualified; no current launcher is assumed trustworthy.

Before execution a separate reviewed grant must authorize exact provision, configuration, disposable identity setup, synthetic writes and negative tests, evidence destination, cleanup and qualification execution. No writes or lock probes are permitted on target. Specify and validate network isolation, resource identity and process containment separately. Run each case in a fresh disposable generation; freeze candidate and bind all components, close admission before evidence sealing, confirm descendants and writers gone, recheck hashes and seal output. Any uncertainty or post-freeze mutation invalidates the attempt. No automatic destructive cleanup when resource identity is uncertain.

## Candidate A: active READ ONLY verification

One dedicated connection, reconnect disabled and client-side statement allowlist, exact approved server/driver/principal. Establish a single active transaction with `START TRANSACTION READ ONLY`; investigate an internal connection correlation mechanism; none is specified or qualified, and no token may be output. This is a hypothesis, not a usable procedure. Candidate verifier reads only the correlated row of `INFORMATION_SCHEMA.INNODB_TRX` and checks `TRX_MYSQL_THREAD_ID` and `TRX_IS_READ_ONLY=1`, with exact expected schema, type, cardinality, visibility and freshness. Exact SQL, access rights and engine behavior require separate source review and qualification; no operational query set is accepted here. A missing/duplicate/hidden/stale row, inaccessible metadata, unproven linkage, changed connection, implicit commit, unknown engine coverage or unexpected value means UNKNOWN and stops before identity queries. Default `tx_read_only` and `@@in_transaction` are supporting context only, never independent proof of current enforcement. If the required metadata is not exposed to the permitted principal, stop; do not grant PROCESS or change principal to make it pass.

Independent lab observer and pre-existing synthetic fixture, separated from verifier, establish ground truth without trusting the verifier. In a separately authorized disposable lab only, a controlled negative mutation attempt against a dedicated non-business object is made under the same transaction, with exact expected server error and no durable change verified by the independent observer. The negative attempt itself is a lab write attempt and requires explicit approval; it is **not** an authorized production verifier. Error alone does not prove general enforcement, storage-engine coverage or target enforcement. Capture server/version/build, driver behavior, full approved statement sequence IDs, transaction continuity, visibility, independent observer outcome, and fixture before/after integrity classification. Do not infer absent writes from missing log rows. A qualified target verifier must be non-mutating, and needs its own demonstrated linkage and target-specific qualification; lab qualification alone cannot make it qualified on the target.

## Candidate B: mapping without secret collection

Primary candidate is a separately approved, authenticated, integrity-protected **non-secret mapping attestation** produced by an independently qualified configuration authority from an approved non-secret source. It must bind site, approved config/source revision, database and socket, generation time, effective configuration context, source identity, override/hook disposition, method and expiration. The checker consumes only the fixed expected fields in memory and emits fixed match/unknown classifications. A self-authored or owner assertion alone does not establish independent target binding. The attestation producer, trust anchor, authenticity, lifecycle, revocation, approved non-secret source and current availability are all unresolved; if no such source exists, mapping remains BLOCKED. A full Frappe config loader, JSON parser that reads a credential-bearing document into memory, or an unqualified hook is not an acceptable shortcut under the no-credential-collection rule.

Alternative for lab investigation only: a standalone bounded parser for **synthetic non-secret configuration** models common config, site overrides, environment overrides, defaults and hook-related uncertainty, and compares its results against a synthetic reference oracle. It never invokes the live Frappe loader. The local source `apps/frappe/frappe/config.py` indicates common config, site config, environment overrides and `extra_config` hooks affect configuration; this source observation is not evidence of live state. A synthetic parser cannot prove its live inputs omit secrets or that it matches a running worker; do not apply to a real secret-bearing file. If runtime overrides/hooks cannot be bounded, return UNKNOWN. Binding of running worker and uninterrupted exclusion remain separate dependencies even on match.

## Case matrix — design only, NOT RUN

All cases require a separately authorized disposable environment. Each expected outcome is a required acceptance condition, not an observed result.

| ID | Synthetic case | Required result |
|---|---|---|
| RO-01 | Correct server/build, permitted principal, active READ ONLY and visible correlated metadata | Candidate reports eligible only if independent observer establishes correct linkage and exact expected state; otherwise UNKNOWN. |
| RO-02 | Active READ WRITE transaction with same session defaults | Verifier must reject; session defaults cannot yield pass. |
| RO-03 | Missing, hidden, duplicate, stale or wrong-connection metadata row | UNKNOWN; no identity query. |
| RO-04 | Simulated reconnect, implicit commit, changed transaction or verifier/session correlation | Stop and invalidate attempt. |
| RO-05 | Disposable synthetic write attempt in active READ ONLY; independent before/after check | Exact documented rejection and no durable fixture mutation; other error is UNKNOWN. Never performed on target. |
| RO-06 | Permissions withheld and insufficient visibility; schema/type/engine mismatch | UNKNOWN; no privileged retry. |
| RO-07 | Observer unavailable, logging failure, timeout or server disconnect | INCOMPLETE; cleanup handled as below. |
| MAP-01 | Valid signed synthetic attestation with exact expected non-secret binding | Match only after independent issuer, signature, scope and freshness checks; runtime binding remains unproved. |
| MAP-02 | Signature failure, wrong issuer, stale/revoked record, changed scope, missing field or duplicate field | UNKNOWN/STOP; no fallback. |
| MAP-03 | Synthetic common/site precedence, environment override, defaults, hook-present and hook-failure fixtures | Compare to reviewed synthetic oracle; unknown hook or missing effective context yields UNKNOWN. |
| MAP-04 | Synthetic canary resembling a credential or unexpected input in fixture/output/log path | Canary must never appear in records; prohibited data detected before collection causes STOP; no raw capture. Synthetic canaries are not credentials. |
| MAP-05 | Source revision or attestation altered between review and observation; symlink or resource substitution | STOP; invalidate bindings; no automatic adoption or cleanup. |
| BOTH-01 | Suppressed value, malformed row, output serialization, exception, partial evidence, rollback/close failure | Generic coarsened stop, no raw output; INCOMPLETE. |
| BOTH-02 | Supervisor interruption, stray descendant, post-freeze mutation or unsealed evidence | INCOMPLETE; no reuse or success assertion. |

A qualification pass requires every applicable case, independent evidence, no contradictory or missing outcomes, and documented limitations. A single green case is not a waiver for remaining unknowns. No target or G0 pass may be inferred.

## Evidence, redaction and failure handling

Before execution approve safe logging boundaries for client, driver, server, audit, supervisor, operating system, error handlers and evidence transport. Disable unneeded logging only in an authorized lab; do not disable production controls. Prove redaction with synthetic canaries without ever recording the canary. No raw SQL/script bodies, exception text, connection strings, account names, sensitive fields, config bytes, fixture contents or unexpected values in output. Use the proposed fixed schema in revision 01b below; it is not yet accepted or qualified. No free text. Coarsen or suppress any stop record if its field, code, order or cardinality could reveal a suppressed value. A null result or zero rows is limited to exact scope.

Candidate is bound to sealed source, approved statements by ID, lab server/driver/fixture identities, supervisor generation and independent observer evidence. Manifest records hashes, method version, case dispositions, approvals and evidence references; store separately protected integrity reference with owner-approved destination. Custody overlap is disclosed; custodian cannot self-accept evidence. AI can review technical evidence but does not provide independent human custody. If safe destination, trusted clock, evidence integrity, authorization or logging cannot be demonstrated, stop before case execution. On any stop, cease statements, attempt rollback on the same connection if safe and close; rollback or close uncertainty yields INCOMPLETE. Failure to establish descendant termination or safe cleanup also invalidates attempt. Do not retry with broader privileges or remove uncertain objects.

## Decisions, dependencies and review

Engineering must define exact verifier query, engine/visibility proof, synthetic fixture, trusted non-secret attestation issuer and source, signature/revocation, effective-context handling, lab topology and evidence mechanics. Frappe app-version query and production principal remain separate unresolved design dependencies. Owner decisions are limited to explicit future authorization of a named environment and scope, approval of evidence/backup destinations and custody governance, and any change to business rules or risk acceptance. This packet selects no live principal, destination or target access. Source-only independent review must challenge every case and assumption before any execution grant is proposed. Prior reviewer disagreement on suffix and custody self-acceptance does not change the owner rules.

References: [MariaDB INNODB_TRX](https://mariadb.com/docs/server/reference/system-tables/information-schema/information-schema-tables/information-schema-innodb-tables/information-schema-innodb_trx-table), [MariaDB SET TRANSACTION](https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/set-commands/set-transaction), and local source `apps/frappe/frappe/config.py`. These establish design leads only, not runtime facts or qualification.

## Independent review disposition — revision 01a

An independent AI reviewer reviewed this packet alone; no source or runtime facts were verified by that review. Its findings are incorporated below. Revision 01a received a text-only independent recheck; this revision 01b has not yet been independently reviewed. **No execution grant is ready.** The core non-mutating verifier has no demonstrated mechanism that establishes active enforcement on the target; feasibility remains UNKNOWN and the target check BLOCKED. Do not assert that it is permanently impossible or loosen the required assurance without evidence and an explicit owner decision. The InnoDB row may be absent for an inactive engine transaction or hidden by privileges, and same-principal connections may race; all are unresolved, fail-closed cases.

Add acceptance cases, in addition to the matrix above:

- RO-08: an attempted identity query before successful gate verification is rejected before transmission; after a successful gate it may run only on the same authenticated, unbroken transaction/session. The synthetic query and gate are independently observed. Reconnect, changed transaction or bypass attempt stops.
- RO-09: pair the synthetic permanent-object READ ONLY rejection with the identical operation under an authorized READ WRITE control using equivalent fixture, principal and privileges. Establish the reviewed server error/SQLSTATE set before the run; any alternative error or failed positive control is UNKNOWN. This does not qualify target writes. Investigate temporary-table exceptions and engine coverage for the exact build before making any broader claim; do not assume a universal READ ONLY write prohibition.
- RO-10: test a competing same-principal session, wrong/stale metadata rows and connection-ID reuse. Define server-issued correlation and independently demonstrate lifetime and anti-confusion guarantees before execution. Failure is UNKNOWN.
- OUT-01: a controlled synthetic-only in-memory detector must positively detect a known canary in a quarantined test channel that is never retained or exported; separately test that output filters block it. The detector and test channel are independent of the production record sink. Record only detector PASS/FAIL, never the canary, hash or raw logs. A detector that fails its positive control makes the result INCOMPLETE. Proving absence in a test is bounded to tested channels and cannot prove universal absence.
- OUT-02: synthetic clock, destination, signing, evidence-sealing and close failures must each stop before unsafe publication; report INCOMPLETE without sensitive values.

Proposed output must use a separately reviewed and approved fixed schema, fixed field order and fixed cardinality; a future approved static mapping collapses all unexpected-value or sensitive-column events into a single generic stage outcome. No condition-specific code, timing, count, order or filename may disclose a suppressed value. If fixed output itself would reveal one, suppress the entire record and use a separately approved safe escalation channel.

Mapping attestation is BLOCKED until an issuer, independently qualified non-secret source, exact field domains, trust anchor, authenticity/revocation process and lifetime/clock policy are defined. Both producer and checker obey the no-credential-collection boundary; a source must be proven non-secret before any read, not inferred by the reader. Synthetic-only experiments cannot establish a live source is safe. No issuer is presently qualified and no owner assertion alone supplies independent binding. No fixed validity period is invented.

A supervisor cannot certify its own containment or termination. A separately qualified observer outside its process/control boundary must independently verify isolation, admission closure, descendants and evidence writers, candidate bindings and cleanup; define observer privileges, channels and non-collusion assumptions before any run. No such observer or H02 mechanism is currently qualified. Custody and acceptance likewise remain BLOCKED until a viable arrangement respects the no-self-acceptance rule and explicitly acknowledges that no independent human adjudicator has been identified. AI review does not fill that role.

A second single-file AI review also found the packet is not executable. Additional unresolved work includes exact transaction pre-state and engine registration, connection-ID reuse and freshness, observer privileges and narrowly projected metadata, an independently sourced rejection-code catalog, and a pinned statement/candidate catalog. Observer access must never collect unrelated sessions' identities or SQL. Lab-only privileges must be separately authorized and cannot be transferred to the target. The required evidence schema must be designed and reviewed to support fixed statement IDs, fixture integrity and rejection classification without storing SQL, secrets or indirectly revealing suppressed values; if it cannot, no pass is possible. Do not create a raw-evidence exception to the redaction rule. Mandatory case applicability must be predetermined in the reviewed version; an omitted mandatory case yields INCOMPLETE, not PASS. Any new attempt after an incomplete attempt requires fresh scope-specific authorization; no broader-privilege retry. Drift in server, driver, identity, admission or candidate invalidates the run. Quarantine uncertain lab resources rather than deleting them; any remediation needs separate authorization.

MAP-03 means synthetic data-model testing only; it must not execute real configuration hooks. Synthetic oracle independence and coverage are unproven. A canary may exist transiently in a synthetic test fixture or quarantined test channel, but may not enter retained evidence, logs or exported records. Synthetic authentication and principal handling must be specified in a separate approved lab design without using or collecting any live credential or user identity. Review findings about MariaDB exceptions and privileges are hypotheses until sourced and qualified. Neither reviewer can determine from this packet that a compliant target verifier is impossible, nor can either grant an exception to owner rules. The earlier unauthorized-inspection incident is recorded and unverified, not declared resolved; any further incident investigation requires its own scoped authorization.


## Revision 01b — proposed gate and evidence schema

**Design only; no field set, statement, witness, or case is approved for execution.** This section supersedes conflicting descriptions above. Owner risk acceptance alone is not evidence and cannot turn UNKNOWN/BLOCKED into PASS or waive any existing mandatory gate. No independent human adjudicator is asserted; a compliant non-self-acceptance process remains unresolved. Source availability is required as well as authenticity, qualification and freshness for mapping.

Gate state machine (all transitions are proposed and require separately reviewed implementation and evidence): `CLOSED -> PRECHECKED -> TRANSACTION_OPEN -> VERIFIED -> QUERY_ALLOWED -> CLOSED`; any uncertainty, unexpected operation, reconnect, expired proof, change of transaction or loss of witness transitions irrevocably to `STOPPED` for that attempt. `PRECHECKED` requires authorized binding, exact reviewed version/configuration, safe logging and qualified observer. `TRANSACTION_OPEN` requires checked pre-state and approved transaction-start statement. `VERIFIED` requires a qualified non-mutating active enforcement method with demonstrated same-transaction correlation and visibility; none currently exists. Only `VERIFIED` permits `QUERY_ALLOWED`, for a pinned reviewed identity statement ID catalog on the same connection and active transaction; a query before this state is rejected before transmission. No `STOPPED -> QUERY_ALLOWED` transition. `CLOSED` requires confirmed rollback/close; failure or uncertainty means INCOMPLETE, not success. A separately qualified client-boundary witness must show allowed/refused statement IDs and gate transitions without capturing SQL or credentials; its integrity, independence, coverage and time-of-check/time-of-use guarantees are unproven. Statement catalog, byte-to-ID binding, gate implementation and witness do not yet exist.

Proposed evidence record schema v1: one fixed-order object with exactly one field per item below; all values are bounded enumerations or pre-reviewed identifiers, never arbitrary text. This is a proposal for future review, not a qualified redaction mechanism. If any field, code, timing, count or identifier can identify a suppressed value, suppress the whole record and use the separately approved safe escalation channel. The actual wire format, safe identifiers, permissions and integrity mechanism remain unqualified.

| Order | Field | Allowed values or bound |
|---|---|---|
| 1 | schema | constant `P00-QUAL-1` |
| 2–4 | grant_ref, packet_ref, attempt_ref | pre-issued opaque safe identifiers from reviewed allowlist; no embedded names or values |
| 5–6 | candidate_hash, catalog_hash | 64 lowercase SHA-256 hex of approved non-secret artifacts, or `UNAVAILABLE` |
| 7 | case_slot | one preapproved non-sensitive slot ID from the fixed case catalog; never a raw condition or column |
| 8 | required | `YES` only for this packet's mandatory cases |
| 9 | case_result | `PASS`, `FAIL`, `UNKNOWN`, `NOT_RUN` |
| 10 | attempt_disposition | `COMPLETE`, `STOPPED`, `INCOMPLETE` |
| 11 | gate_correlation | `VERIFIED`, `REJECTED`, `UNKNOWN`, `NOT_RUN` |
| 12 | control_result | `PASS`, `FAIL`, `UNKNOWN`, `NOT_RUN` |
| 13 | detector_result | `PASS`, `FAIL`, `UNKNOWN`, `NOT_RUN` |
| 14 | error_class | `EXPECTED`, `OTHER`, `UNKNOWN`, `NOT_RUN`; no raw errno or SQLSTATE |
| 15 | prestate | `EXPECTED`, `OTHER`, `UNKNOWN`, `NOT_RUN` |
| 16 | witness_class | `QUALIFIED`, `UNQUALIFIED`, `UNKNOWN`, `NOT_RUN` |
| 17 | fixture_integrity | `EXPECTED`, `OTHER`, `UNKNOWN`, `NOT_RUN` |
| 18 | sealing | `COMPLETE`, `INCOMPLETE`, `UNKNOWN` |
| 19 | cleanup | `COMPLETE`, `INCOMPLETE`, `UNKNOWN` |
| 20 | custody_acceptance | `ACCEPTED_NON_SELF`, `NOT_ACCEPTED`, `UNKNOWN` |
| 21 | limitation | `NONE`, `SCOPE_LIMITED`, `UNQUALIFIED`, `UNKNOWN` |
| 22 | reference | approved opaque manifest reference or `UNAVAILABLE` |

The case slot list and statement catalog are not yet defined; until a redaction review proves the fixed slot cannot indirectly identify a suppressed value, suppress the record. Hashes must never cover secrets, unexpected raw values or low-entropy confidential values. Independent observation of an exact reviewed error is represented only by `EXPECTED`, and its decision process needs separate verification; raw error, raw SQL and account identities remain prohibited. Per-run metadata including timestamps must be separately specified and approved with fixed bounds before use; this record does not silently authorize them. Observer and custodian roles/attribution must be independently documented without identity leakage or invented human separation.

## Revision 01b — mandatory case scoring

All case IDs listed below are **mandatory design requirements**, including each subcondition; none is currently executable. Each is in a fresh separately bound generation except a deliberately paired control using two independently verified equivalent fresh generations. `PASS` means the specified expected observation and all independently witnessed preconditions/cleanup are established. `FAIL` means an established contrary outcome, including prohibited transmission or a failed control. `UNKNOWN` means a result cannot be determined safely; `NOT_RUN` means no attempt. `STOPPED` is an attempt disposition, not a case result; a stop with uncertain result maps to `UNKNOWN` plus `STOPPED`. Any missing mandatory case, unsafe output, unqualified witness, cleanup or sealing makes the overall attempt `INCOMPLETE`; a case-level PASS never alone approves a target or G0. No case may be declared inapplicable without a separately reviewed change to the packet and authorization.

| Mandatory cases | Expected observation for PASS; otherwise FAIL if a contrary observation is proven, UNKNOWN if not |
|---|---|
| RO-01 | Correctly bound lab READ ONLY state is reported eligible only after independent verification of linkage and all prerequisites. |
| RO-02 | READ WRITE control is rejected by the verifier despite matching session defaults. |
| RO-03 | Each hidden, missing, duplicate, stale and wrong-session variant stops before identity transmission. |
| RO-04 | Each reconnect, implicit commit, changed transaction and correlation variant stops and invalidates the attempt. |
| RO-05 | In lab only, approved permanent synthetic fixture rejects the operation with independently witnessed reviewed error class and unchanged durable fixture; other error is UNKNOWN. |
| RO-06 | Each permission, visibility, schema, type and engine mismatch stops without privilege escalation. |
| RO-07 | Each observer, logging, timeout and disconnect failure yields a safe stop and INCOMPLETE. |
| RO-08 | Independently witnessed client boundary refuses every pre-gate identity ID; post-gate IDs use the same proved transaction; bypass and gate-to-query race are rejected. |
| RO-09 | Fresh matched READ ONLY and READ WRITE lab generations use equivalent fixture, principal and rights; independent observer verifies READ WRITE durable effect and cleanup, and READ ONLY rejection/no durable effect. |
| RO-10 | Same-principal concurrent session, stale/wrong row and reused ID never create a false gate pass. |
| MAP-01 | Synthetic attestation passes only independently qualified signature, issuer, source, schema, availability, scope and freshness checks. |
| MAP-02 | Every invalid signature, issuer, expiry, revocation, availability, scope and field variant stops without fallback. |
| MAP-03 | Synthetic-only precedence/oracle cases match independently reviewed expectations; unknown hooks stop, with no real hook execution. |
| MAP-04 | Synthetic canary is absent from every retained/exported channel and output-filter positive controls work; no live secret is read. |
| MAP-05 | Drift, substitution or symlink cases stop without adoption or unsafe cleanup. |
| BOTH-01 | Every malformed, suppressed, serialization and cleanup failure produces safe generic stop and INCOMPLETE. |
| BOTH-02 | Each interruption, stray descendant, mutation and unsealed-evidence case invalidates the attempt. |
| OUT-01 | Independent in-memory witness confirms the synthetic detector fires and each output-filter channel blocks the canary; channel coverage is documented without storing the canary. |
| OUT-02 | Each clock, destination, signature, sealing and close failure stops before unsafe publication. |

Attestation issuer, source classification by construction, exact domains, signing and revocation, clock/lifetime and availability checks remain undefined. Observer independence, privileges and channel integrity, detector witness, lab containment and fixture cleanup remain unqualified. Nothing here establishes their feasibility or existence.


## Independent review disposition for revision 01b

A single-document AI review found 01b not executable. Blocking findings include: metadata-only RO case success can be confused with verified enforcement; the state machine does not specify verifier statements or safe cleanup after STOPPED; case and attempt records, scoring and disposition precedence are underspecified; suffix drift lacks an explicit mandatory case; witness qualification and custody acceptance require independent authority and cannot be self-attested; per-variant scoring may leak suppressed conditions; and manifest, identifiers and timestamps require the same redaction boundary. Source/issuer qualification and lifecycle, independently qualified witnesses and role separation remain unresolved. Treat all 01b gate, schema and scoring descriptions as unapproved proposals, not operational controls. The incident exclusion in this document is unchanged and cannot be superseded by the 01b schema section.

The reviewer proposed corrections; no corrected revision or recheck is claimed here. Case-level PASS on synthetic checks cannot establish qualified active enforcement, target identity or G0 closure. An absent or uncertain required binding, acceptance or seal prevents a successful attempt. Do not infer that an independent human adjudicator exists or is required by the accepted governance amendment; no self-acceptance remains mandatory.
