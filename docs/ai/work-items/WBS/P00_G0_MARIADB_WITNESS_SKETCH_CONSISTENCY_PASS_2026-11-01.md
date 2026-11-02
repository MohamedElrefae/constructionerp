# P00/G0 MariaDB — witness-sketch consistency pass against the disposition (document-only), 2026-11-01

Verdict: **ALIGNED IN SUBSTANCE across all six required dimensions; two minor wording findings, zero blocking.** This is a document-only consistency pass: a direct read-and-compare of `P00_G0_MARIADB_KEY_ASSURANCE_AND_WITNESS_SKETCH_2026-11-01.md` (sketch) against `P00_G0_MARIADB_FEASIBILITY_REVIEW_DISPOSITION_REV_05_2026-10-31.md` (applicable disposition). It verifies only; it implements nothing, configures nothing (including `performance_schema`), tests nothing, qualifies nothing, authorizes nothing. It grants no acceptance, catalog-freeze, or execution authority, verifies no target, and authorizes no reliance on the historical baseline for a new operation. The sketch's recorded status as the feasibility record's settled precondition list is unaffected by the findings below.

Method: line-level comparison of the two named documents only (plus this round's recording edit to the sketch's Recording-status block). No other files, no commands beyond reading them, no source retrieval, no target access of any kind, no writes except this record. AI review is not independent human custody; no independent human adjudicator participates; the custodian cannot self-accept custody evidence; the prior unauthorized inspection remains unverified and excluded (neither document contains incident-derived material, key names, values, or identifying details); the owner-approved weaker-assurance historical baseline remains a historical reference only.

Preservation items verified in the sketch (present and uncontradicted): numeric core `10.11.14`; accepted historical full reference `10.11.14-MariaDB-0ubuntu0.24.04.1`; changed or unrecognized suffix ⇒ UNKNOWN (sketch B.6.4 restates the rule exactly); all governance constraints (B.5); incident exclusion (header + B.6.1).

## 1. Dimension-by-dimension results

### 1.1 Terminology — ALIGNED, one minor finding
- Disposition legend terms used correctly where used: UNKNOWN (fact not established), INCOMPLETE (evidence exists but insufficient/unauthenticated/unsafe), FAIL (visible when safe), BLOCKED (gate status only; sketch uses it only for the gate).
- No misuse of Sustain/Decline-proposal (no disposition table in the sketch).
- Finding **T1 (minor)**: sketch B.6.3 says "**ambiguous classification**"; the disposition (REV_05) replaced that term with "**indeterminate classification**" precisely to remove dual use of "ambiguous" (its conjunct-sense partner is now "underdetermined conjuncts"). The sketch's mapping intent is preserved by legend context, but the term drifted. Proposed fix (not applied): replace in B.6.3 "Unmatched or ambiguous classification" with "Unmatched or indeterminate classification — classifications whose values the record cannot establish".

### 1.2 UNKNOWN / INCOMPLETE taxonomy — ALIGNED, one minor finding
- Correct per-condition uses verified: correlation invalidated/absent evidence/not-started/absence ⇒ UNKNOWN (sketch B.2.1, B.2.3; disposition D8 "absent evidence … UNKNOWN"); uncertain redaction ⇒ INCOMPLETE (B.4.3 = disposition D8 exactly); timing evidence insufficient ⇒ INCOMPLETE (B.2.4); suffix mismatch ⇒ UNKNOWN (B.6.4 = provenance rule); trust-chain break ⇒ FAIL-where-safe never pass (B.6.6); no silent conversion anywhere; B.7 prerequisites carry no status claims.
- Finding **T2 (minor)**: the B.6 STOP header pairs "record UNKNOWN or INCOMPLETE" without per-condition legend-keyed mapping, and items B.6.2 and B.6.3 each contain two conditions (correlation lost + freshness unprovable; unmatched classification + value-outside-sets + redaction uncertainty). This mirrors the paired-use issue the disposition itself corrected (REV_04 fix #2). Substance is inferable from the legend but not explicit. Proposed fix (not applied): map each stop condition explicitly — correlation integrity lost ⇒ UNKNOWN (fact of same-transaction identity not established); freshness unprovable ⇒ INCOMPLETE (evidence present but insufficient to conclude); indeterminate/unmatched classification ⇒ UNKNOWN; value outside the fixed preapproved sets ⇒ UNKNOWN; redaction uncertainty ⇒ INCOMPLETE (already explicit at B.4.3).

### 1.3 Redaction boundaries — ALIGNED
- Out-of-scope list identical to disposition D8 (identities, credentials, query bodies, unexpected values, indirect identifiers); sketch's additions (hostnames/usernames, free-text server output) are strictly stricter, contradicting nothing.
- "Suppress and stop if disclosure or binding is uncertain" ⇒ sketch B.4.3 withhold + INCOMPLETE + B.6.5 stop ✓.
- D8's qualification precondition ("separately qualified method proves neither inputs nor outputs reveal identities, and the operation separately authorized") ⇒ sketch B.1.4 + B.4.5, evidence pending at B.7.4 ✓.
- Record-redaction rules (Decisions section: attestable redacted record where safe; coarse-status leak ⇒ withhold + mark INCOMPLETE; missing record or incomplete state never erases a known failure) ⇒ sketch B.4.4 ✓ at rule-level identity.
- No comparison/collection occurs in the sketch (D8 "No actual comparison occurs here") ✓.

### 1.4 Transaction-correlation requirements — ALIGNED
- "same-server, connection and uninterrupted transaction correlation" ⇒ sketch B.2.1 verbatim-level ✓ (reconnect, thread-id reuse, restart, pool switch all invalidate ⇒ never a match).
- D5's "row presence, cache age and self-observation or fail closed" ⇒ B.2.3 (presence; absence is not evidence), B.3.1 (freshness/cache age), B.3.2 (start-proof/self-observation), STOP conditions (fail closed) ✓.
- Disposition's "independent witness and redaction/ordering oracles" ⇒ sketch B.3.3 (two-dimension consistency, requirement class) and B.3.1 timestamps (ordering); ordering-oracle is served by the freshness/correlation-timing requirements — recorded as substance-aligned, not separately named; informational only.
- "Missing ⇒ UNKNOWN; underdetermined ⇒ INCOMPLETE" conjunct discipline ⇒ substance present in the sketch but not per-condition explicit (Finding T2).

### 1.5 Governance constraints — ALIGNED
- Every governance line of the disposition present and uncontradicted in sketch B.5: no independent human adjudicator participates; custodian cannot self-accept custody evidence; AI review is not independent human custody; attester does not become acceptor; external human acceptor remains an unselected option; acceptance authority undesignated (B.5.1, B.7.7); conflict checks and independent attestation unresolved (B.5.4); no compatibility with the no-adjudicator rule assumed.
- The sketch's "no attestation chain can be completed inside this sketch" (B.5.3) is scoped to the sketch, not a universal impossibility claim — consistent with the disposition's "No process is declared impossible" ✓ (verified-scoped, informational).
- The disposition's Admin-Construction dual-role clause is not restated in the sketch; omission, not contradiction (the prohibition it qualifies is preserved) — informational.

### 1.6 Incident-exclusion rules — ALIGNED
- Sketch header declares the prior unauthorized inspection unverified and excluded, with no incident-derived material used; B.6.1 stops on incident-derived material; B.4 suppresses identifying detail; no key names, values or identifying details appear in either document; no completeness or containment claim is made anywhere in the sketch (matching "exclusion completeness … unverified"); sanitized-manifest scope ownership not contradicted ✓.

## 2. Findings list

| # | Severity | Location | Issue | Proposed fix (NOT applied — pending authorization) |
|---|---|---|---|---|
| T1 | minor | sketch B.6.3 | "ambiguous classification" drifts from disposition's settled term "indeterminate classification" | Replace with "indeterminate classification — classifications whose values the record cannot establish" |
| T2 | minor | sketch B.6 header, items 2–3 | Paired UNKNOWN/INCOMPLETE stop conditions lack per-condition legend-keyed mapping (disposition's established discipline) | Add the explicit per-condition mapping given in §1.2 of this pass |

No blocking findings. Both findings concern wording explicitness only; every mapping's substance is already correct under the disposition's legend, and no invariant, boundary, governance rule, or exclusion is violated by the sketch as written.

## 3. Required evidence

None to resolve discrepancies (none blocking). The B.7 prerequisite evidence list stands unchanged as the feasibility record's settled precondition list: timing characterization (D5 closure), non-mutation proof, correlation-marker availability, D8 method qualification, redaction-method qualification with safe-failure record design, threat matrix/least-data analysis, governance decisions first (acceptance authority, integrity-reference destination, conflict checks), exact version context — all unheld, all requiring their own authorized scopes.

## 4. Separated decisions (none decided here)

**Business/owner (none decided):** whether to approve the two proposed wording fixes (T1/T2) or leave the sketch as recorded; acceptance authority/evidence destination; any custody-acceptance process; external-acceptor selection (unselected); any no-adjudicator rule change; retention/baseline amendments; whether to accept this pass as an input (no recommendation).

**Authorization (none granted):** any correction edit beyond this pass's record; any method qualification; any runtime or target-side scope; any configuration change including `performance_schema`; any extended source review; any target, credential, custody, administrative, privilege, provisioning, testing, qualification or deployment scope; any acceptance, catalog-freeze or execution authority.

## 5. Minimum next authorization

A source-and-document-only step: (a) apply the two recorded wording fixes (T1/T2) to the sketch, if approved, followed by this same document-only comparison to confirm zero findings; and/or (b) review the companion D8 bounded-classification draft (`P00_G0_MARIADB_D8_BOUNDED_CLASSIFICATION_DRAFT_2026-11-01.md`) document-only for legend-keyed correctness — under the same exclusions as this round (no target access of any kind, no target writes including rejected attempts, no identity collection, no incident-derived material, no custody acts, no configuration changes, no provisioning/implementation/testing/qualification/deployment). A scope description only: it grants nothing and recommends no acceptance, catalog freeze, or execution grant.

## 6. Re-run record (2026-11-01 continuation)

Under a further source-and-document-only authorization dated 2026-11-01, fixes **T1** and **T2** were applied to the sketch exactly as recorded above (assertion-checked, single-match replacements): STOP item 3 now uses the settled term "indeterminate classification" with its legend gloss and explicit mappings (unmatched/indeterminate ⇒ UNKNOWN; value outside the fixed preapproved sets ⇒ UNKNOWN; redaction uncertainty ⇒ INCOMPLETE); STOP item 2 now maps correlation integrity lost ⇒ UNKNOWN (fact of same-transaction identity not established) and freshness unprovable ⇒ INCOMPLETE (evidence exists but is insufficient to conclude). Verification at re-run: zero occurrences of "ambiguous" remain in the sketch; all per-condition legend-keyed mappings are present; the sketch's preservation block, governance section, redaction boundary, correlation requirements and incident exclusion were untouched by the edits.

The comparison was re-run against `P00_G0_MARIADB_FEASIBILITY_REVIEW_DISPOSITION_REV_05_2026-10-31.md`, digest re-verified as `9fc006b6fb6faefea74b8aabd025cdd5abc37b7a91f0a4f1ad68e79f43797df0` (identical to the recorded comparison baseline): **zero remaining findings across all six dimensions** — terminology, UNKNOWN/INCOMPLETE taxonomy, redaction boundaries, transaction-correlation requirements, governance constraints, and incident-exclusion rules. Findings T1 and T2 are superseded by this record and retained above only as history. No other change was made to the sketch, and no other document was modified this round except this record.

P00/G0, H01 and H02 remain open; P1 deferred; P2 implementation, disposable-lab provisioning and native testing paused.
