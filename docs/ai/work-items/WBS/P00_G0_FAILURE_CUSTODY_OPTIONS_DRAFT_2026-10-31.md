# P00/G0 protected failure and custody options — planning draft

**Source-and-document-only design. Not an approval, grant, implementation, test, qualification, evidence package or acceptance.** No target, credential, socket, custody path, administrative inspection or environment was accessed for this paper. P00/G0, H01 and H02 remain OPEN; P1 DEFERRED; P2 implementation, lab provisioning and native testing PAUSED. Prior reported unauthorized inspection remains unverified and excluded from evidence, fixtures, expected results and target facts; do not assume it was contained. The owner-approved historical baseline is weaker assurance, not independently verified current state.

Mandatory boundaries for every option: independently qualified non-mutating active database-enforced READ ONLY on the same reliably correlated transaction before target identity queries; uncertain enforcement, visibility, access, mapping or cleanup => UNKNOWN/INCOMPLETE, never absence; independent qualified non-secret mapping; no broader-privilege retry after a stop. No credentials, SQL/script bodies, user identities, document identifiers, raw unexpected values or unrelated business records may be collected. A custodian cannot self-accept custody evidence; no independent human adjudicator participates; AI review is not independent human custody. Admin Construction may hold acceptance-authority and custodian roles with disclosed reduced separation. Neither a service, a different account, nor a signature alone demonstrates independence or human separation. A compliant acceptance mechanism is unresolved; no option below asserts one exists.

## 1. Protected failure record options

### A — fixed closed-enum record and separately protected integrity reference (recommended design candidate)

**Technical design.** A separately qualified producer maps independently confirmed outcomes in memory into a fixed schema of versioned, non-sensitive enums. It never serializes a suppressed value, column, raw error, SQL, identity, document ID, credential, exception, count, length or hash of a suppressed/low-entropy value. A fixed record shape and non-semantic identifier scheme are independently reviewed for inference through presence, omission, order, timing, file names and cardinality. Proposed internal fields: schema/version, opaque binding to approved attempt and method, failure status (`CONFIRMED_FAILURE`/`UNCONFIRMED`), completeness (`COMPLETE`/`INCOMPLETE`), fixed broad limitation class, integrity-reference link and separately authenticated attestation references. Each field is conditional on a leakage review; no per-column or unexpected-value code. A confirmed failure remains a separate internal failure dimension even where completeness is INCOMPLETE. No later PASS clears it without independent adjudication and append-only disposition. External output is a separate minimal approved classification; if even the classification discloses a suppressed value, emit nothing through that channel. If a safe protected record or independent attestation cannot be established, suspend reliance and keep the attempt/campaign INCOMPLETE; never transform a confirmed failure into no failure.

Use exclusively created files relative to a qualified directory handle, no-follow and no replacement, verified ownership/ACL/mode, durable writes and independently protected SHA-256 reference of reviewed non-secret canonical record bytes. A hash beside a mutable file is not authenticity. Bind evidence, attempt, catalog version, attestation, invalidation and reference with opaque non-sensitive anti-replay identifiers; exact encoding, safe destination, protected reference and trusted clock require design and qualification. This proposal authorizes no file or directory action.

**Required evidence.** Independent schema/side-channel review; preapproved fixed field domains and overflow behavior; separately authorized synthetic controls demonstrating false-positive and false-negative detection, suppression, complete channel coverage, failed writes/close, tampering, replay, reordering, missing record, invalidation and restore. A separately qualified observer verifies the record producer and protected reference; its authority and role boundaries are unqualified. All channels, including client, driver, server/audit, logs, error paths, terminal, telemetry, crash and evidence transport, require approved non-disclosure behavior before collection. No successful query or empty output establishes visibility.

**Limitations.** A fixed status can itself reveal information; suppression may make independent reconciliation impossible, requiring INCOMPLETE. Integrity references detect changes only under their separate protection and do not create organizational independence. No protected location, failure record or authority is currently qualified.

**Future owner decisions/authorization.** Approve specific evidence and integrity-reference destinations, permitted readers and custody policy as needed; authorize assessment, creation/configuration, synthetic tests, qualification and any later collection separately. No new retention policy is proposed.

### B — no persistent failure record where safe output cannot be proved

**Technical design.** Stop before collection if no approved safe record and reference are available. If a failure arises in an authorized future attempt and even a generic status would leak, cease work and use only a separately approved non-leaking escalation channel; otherwise emit nothing and retain INCOMPLETE. Never record raw values or treat no output as success.

**Required evidence.** Independently reviewed detection and channel-suppression design, synthetic coverage and failure tests, and an independently authenticated safe escalation process. None is qualified.

**Limitations.** With no safely retained and independently attested failure record, the failure cannot be reconciled or accepted; G0 cannot close on missing evidence. This is a fail-closed fallback, not proof that failure did not occur.

**Future owner decisions/authorization.** Approve a named escalation destination and separately authorize any environment or collection activity. Acceptance of an incomplete result does not turn it into a pass.

## 2. Custody-acceptance options

### C — bounded separate acceptance authority process (design hypothesis, not an approved role change)

**Technical design.** For each custody evidence package, bind evidence identity, custodian role, producer role, proposed acceptor authority, protected manifest hash, acceptance decision, grant, limitations and conflict check in a separate authenticated append-only acceptance record. Acceptance must be issued by an authority that did not act as that evidence package's custodian; a custodian's own declaration or separate account is insufficient. The accepted role overlap is disclosed in each record and cannot eliminate the no-self-acceptance rule. Define authority, evidence-specific conflict test, issuer authentication, anti-replay, revocation and audit integrity through independently reviewed governance. Do not assume AI review, a service signature or another account provides independent human custody.

**Required evidence.** A concrete approved role and authority matrix, disclosed overlap, evidence-specific conflict check, independently authenticated acceptance and protected provenance, plus separately authorized qualification of controls. The identity and permissible nature of any acceptor are not determined here. No independent human adjudicator participates under the accepted amendment.

**Limitations.** Because the same owner controls the accounts, account changes do not create different humans. Whether any proposed mechanism satisfies the existing non-self-acceptance and independent-attestation requirements has not been established. Unless a compatible authority and mechanism are actually established and independently assessed, custody evidence cannot be accepted. No new independent human adjudicator is inferred, and no non-human substitute is deemed approved.

**Future owner decisions/authorization.** Decide whether a concrete proposed acceptance authority/process is acceptable under existing governance, or leave acceptance blocked; a policy change or role change requires explicit owner decision. Authorize any implementation and qualification separately.

### D — preserve custody acceptance as unresolved

**Technical design.** Do not issue custody acceptance until a process meeting all accepted conditions is identified and independently assessed. Keep evidence and gate disposition INCOMPLETE; record only permitted redacted status in an approved protected location if available. Independent AI review may challenge artifacts but cannot serve as independent human custody or transform an incomplete record into accepted evidence.

**Required evidence.** A future approved process, independent technical review, protected provenance and separate acceptance record. None is established.

**Limitations.** This preserves the current rules and leaves G0 open. No indefinite-closure risk is silently accepted or changed by this document.

**Future owner decisions/authorization.** No new governance decision is needed to keep existing status; any later change, creation or qualification needs its own explicit authorization.

## 3. Invalidation, provenance and integrity — common design

A detected forbidden pre-gate transmission, suspect witness, canary escape, compromised reference or invalidated evidence triggers immediate stop and suspension of reliance. The provisional safety stop is distinct from a final acceptance or adjudication. An independently authenticated and independently adjudicated append-only invalidation/correction record must bind affected package, attempt, catalog revision, generation, relevant attestation references and reason class without revealing suppressed values. It preserves uncorrected adverse findings and cascades suspension to dependent conclusions, including any prior lab completion; it cannot be issued solely by the affected producer/custodian. A later PASS cannot silently clear a confirmed failure. If authority, safe channel, authenticity or binding is uncertain, no final disposition is claimed and the status is INCOMPLETE. The attestor, trust root, conflict rules and acceptance mechanism are unresolved; no independent human adjudicator is introduced by this proposal.

Document source lineage for every expected value, fixture, catalog and evidence reference and verify the reported unauthorized inspection is not used as evidence. If lineage cannot be established, stop reliance. Owner-approved historical baseline and version reference are decisions recorded in the handoff, not independently verified target facts. A protected record of versioned hashes, canonicalization, decisions and update history outside the evidence directory is required. Separate signing/attestation credentials, if designed later, require separately authorized key provisioning and custody; do not request or collect credentials. SHA-256 comparison alone is not authenticity, trusted time or custody. The historical accepted artifact bytes/hashes remain unchanged.

## 4. MariaDB comparison — proposed parser and vectors, NOT RUN

**Technical design.** In an approved fixed input boundary, compare bounded ASCII bytes with no trimming, case folding or normalization. Maximum 128 bytes is a proposed safety bound, not a qualified server specification. Suppress all raw non-match bytes, their length and hashes. The only positive full-reference classification is exact byte equality to `10.11.14-MariaDB-0ubuntu0.24.04.1`. Otherwise require core grammar `DIGITS.DIGITS.DIGITS` ending at end-of-input or before `-`, with ASCII digits only; reject core leading zeros except the single digit `0`, empty components, extra core segments, non-ASCII/control/whitespace, oversized input or ambiguous syntax as UNKNOWN. A valid different numeric triple => NUMERIC_MISMATCH and stop. With numeric core exactly `10.11.14`, any bare, changed, unrecognized or malformed suffix => UNKNOWN and stop. Dots/digits after a hyphen belong to the suffix, not the core. Exact grammar, output classification, interpretation and implementation require independent review; no qualified parser exists.

| Synthetic input | Expected classification (design, not test result) |
|---|---|
| `10.11.14-MariaDB-0ubuntu0.24.04.1` | MATCH_REFERENCE |
| `10.11.15-MariaDB-0ubuntu0.24.04.1` | NUMERIC_MISMATCH; stop |
| `10.11.14` | UNKNOWN; stop |
| `10.11.14-MariaDB-0ubuntu0.24.04.2` | UNKNOWN; stop |
| `10.11.14.1` | UNKNOWN; stop |
| `010.11.14-MariaDB-0ubuntu0.24.04.1` | UNKNOWN; stop |
| reference with trailing newline, case change or non-ASCII | UNKNOWN; stop |
| empty input or input over 128 bytes | UNKNOWN; stop |

**Safe output domain.** Approved output, if separately qualified, consists only of fixed `MATCH_REFERENCE`, `NUMERIC_MISMATCH`, `UNKNOWN`, or `NOT_RUN` and a generic incomplete disposition; no free text. Numeric mismatch is itself potentially sensitive, so emit it only if an independently reviewed policy permits that classification without indirect disclosure; otherwise coarsen to UNKNOWN or suppress the record, and keep INCOMPLETE. Never infer absence from suppressed output. No output domain is approved or qualified yet.

**Required evidence.** Independent grammar and vector review, exact input framing and bounded parser design, no-echo and logging boundary, validation on separately authorized synthetic fixtures including malformed and overflow cases, independent witness, result redaction and byte-to-result binding. Qualification on an isolated lab does not establish target enforcement or runtime binding. No test has run.

**Limitations and decisions.** Version bytes reported by one future connection establish only point-in-time agreement with a weaker-assurance owner baseline, not independent target identity. The bound is a technical proposal; owner approval of a target, principal, destination, access or collection remains separate. Changed or unrecognized suffix remains UNKNOWN; no rule change is proposed.

## 5. Status and decision boundary

Option A and C are technical candidates only; their safeguards, issuer and acceptance authority are not established. B and D provide fail-closed blocked paths when evidence or acceptance cannot be established. A successful AI review is not custody acceptance or authorization. Future technical designs should be independently reviewed before an owner is asked to approve a concrete destination or scope. Any actual assessment, path access, creation, configuration, backup, restoration, privilege inspection, provisioning, test, qualification, collection, implementation or deployment requires a separate current explicit grant. No acceptance, catalog freeze or execution is recommended.
