# P00/G0 MariaDB feasibility workstream — consultant briefing letter

**Date:** 2026-11-01
**Prepared by:** the owner's technical workstream (DeepSeek V4.1 Flash under T3 Code orchestration; MiMo-V2.6-Flash as independent technical verifier)
**Prepared for:** the owner's consultant (Perplexity AI agent workflow) — for review, revision and reply
**Subject:** end-to-end status, evidence, decisions and open questions of the P00/G0 MariaDB D8 read-only witness workstream
**Disclosure note:** this letter contains no credentials, identities, document identifiers, or incident-derived material. Whether and how far to share it externally is the owner's decision. This letter is a briefing document only: it authorizes nothing, accepts nothing, and changes no gate status.

---

## 1. Executive summary (read this first)

- The workstream concerns a MariaDB **read-only, non-mutating feasibility question** (P00/G0): can a *qualified, non-mutating, per-transaction witness* demonstrate that a database transaction is running under read-only enforcement — without collecting identities and without touching the production target?
- A **governance-heavy evidence program** has produced a stable document baseline: a reviewed disposition (REV_05), a public-source provenance analysis with verified chain, a stable D8 bounded-classification artifact (REV_03), a stable qualification-design specification (REV_02), and execution-planning phases A–F of an owner-approved programmatic execution plan.
- A **feasibility verdict** now exists: `FEASIBLE_WITH_NEW_AUTHORIZATION`. Source-only work can proceed; runtime evidence and tests require a new owner authorization (Gate G).
- **The gate remains BLOCKED.** No target was accessed. No evidence was accepted (by the owner's Gate D choice C3). No custody location exists. The next step is an owner decision at Gate G.
- **What the consultant is asked to do:** review consistency and soundness end-to-end (governance, evidence design, feasibility reasoning), identify gaps or contradictions, and recommend a Gate G path and wording — without inventing authority or assuming target knowledge.

## 2. Background and purpose

P00/G0 investigates MariaDB **10.11.14** read-only feasibility for a Frappe/ERPNext deployment context. The central technical question: is there a **compliant witness** that a transaction is read-only — non-mutating, per-transaction, identity-free, and independently attestable? The workstream is deliberately conservative: every uncertainty is recorded as `UNKNOWN` or `INCOMPLETE`, never converted to a pass; every claim is scoped; no target access is authorized at any point so far.

The document lineage (all in `apps/construction/docs/ai/work-items/WBS/`):
1. Feasibility source doc and its AI review (reported, not independently reverified): findings D1–D14.
2. `P00_G0_MARIADB_FEASIBILITY_REVIEW_DISPOSITION_REV_05_2026-10-31.md` — disposition, legend, D1–D14 dispositions, governance, scope boundaries.
3. Provenance records — public-source chain verified: upstream tarball + distribution source package, digests and signatures (MariaDB signing key fingerprint **177F4010FE56CA3336300305F1656F24C74CD1D8**; three official key files byte-identical, SHA-256 `00adb387f4c12e8982cfc28165d225695621494354cd58108c6845063bfb74b5`).
4. `P00_G0_MARIADB_D8_BOUNDED_CLASSIFICATION_DRAFT_REV_03_2026-11-01.md` — **stable D8 artifact** (classification codes C1–C6, expected classes E1–E4, legend-keyed mapping rules, stop discipline, co-occurrence derivation).
5. `P00_G0_MARIADB_D8_QUALIFICATION_DESIGN_SPEC_REV_02_2026-11-01.md` — **stable evidence-standard specification** (Q1–Q8 evidence classes, six controls, twelve stops, pre-authorization record, separated decisions).
6. Owner-approved **End-to-End Programmatic Execution Plan** (2026-11-01) — phases A–J, internal verification protocol, stop conditions.
7. Phases A–F executed (plan, evidence-package designs, custody options, owner Gate D, proof plan, feasibility verdict).

## 3. Stable artifacts and digests

| Artifact | SHA-256 | Role |
|---|---|---|
| `P00_G0_MARIADB_D8_BOUNDED_CLASSIFICATION_DRAFT_REV_03_2026-11-01.md` | `bbe596610537583e370ff7319a44acda588b5c9cefcf50e10f5366c9adc10322` | stable D8 input candidate for precondition B.7.4 |
| `P00_G0_MARIADB_D8_QUALIFICATION_DESIGN_SPEC_REV_02_2026-11-01.md` | `0a3aa5c6ed7c0a3dffd09b87e2f53905818d66e7379e6ce9f5d5874e0198328e` | stable evidence-standard design input |
| D8 record closure | `P00_G0_MARIADB_D8_BOUNDED_CLASSIFICATION_RECORD_CLOSURE_2026-11-01.md` | recorded binding + stop point |
| Spec closure | `P00_G0_MARIADB_D8_QUALIFICATION_DESIGN_SPEC_CLOSURE_2026-11-01.md` | recorded binding + stop point |

Rules of the binding: any byte change to either digest-bound artifact voids its binding and requires re-issue; either artifact is an **input candidate / design input only** — neither satisfies, partially satisfies, nor qualifies precondition B.7.4.

## 4. Preserved business rules (must not change)

1. Numeric MariaDB core `10.11.14`.
2. Accepted historical full reference `10.11.14-MariaDB-0ubuntu0.24.04.1`.
3. Changed or unrecognized suffix ⇒ `UNKNOWN`.
4. No independent human adjudicator participates.
5. The custodian cannot self-accept custody evidence.
6. AI review is not independent human custody.
7. The external human acceptor remains an unselected option.
8. Acceptance authority and evidence destination remain undesignated until the owner selects them (destination now selected as D2; authority still undesignated).
9. The prior unauthorized inspection remains unverified and excluded from evidence.
10. The owner-approved weaker-assurance historical baseline is a historical reference only — not current target state, not runtime binding, not authorization for a new operation.
11. `UNKNOWN` = a fact is not established.
12. `INCOMPLETE` = evidence exists but is insufficient, unauthenticated, or unsafe to conclude.
13. `UNKNOWN` and `INCOMPLETE` are never interchangeable.
14. A stopped attempt is not a completed campaign.
15. A confirmed failure remains visible and is never erased.
16. Redaction uncertainty results in `INCOMPLETE`, never a pass.
17. No retry with broader access after a stop condition.
18. No credentials, raw unexpected values, SQL/script bodies, user identities, document identifiers, or unrelated business records may be collected.

## 5. Owner Gate D decision (recorded 2026-11-01)

| Decision | Selection | Meaning |
|---|---|---|
| Evidence destination | **D2** | owner-managed out-of-repo encrypted store — **not created, configured or accessed** |
| Custody-acceptance process | **C3** | **no acceptance**; records remain unaccepted inputs |
| Acceptance authority | **undesignated** | remains the owner's decision |
| Retention/recovery | **R2 + B2** | fixed retention classes per record type; encryption at rest with owner-held key; restore-tested backup |

Consequences: no evidence is "accepted"; closure of P00/G0 is impossible by design under C3 until the owner revisits acceptance; integrity anchoring (I1–I3), invalidation authority (V1–V3), permission model (P1–P3) and attestation chain (A1–A3) remain undesignated and are marked PENDING in planning records.

## 6. Phase E — qualification-proof plan (verified)

Eleven elements: (1) exact evidence per Q1–Q8; (2) observation-mechanism requirements (server-produced state read-only; no configuration change; never session-self-report alone; bounded classifications only; no write attempts); (3) transaction correlation (same-server/same-connection/uninterrupted; server-side start marker; opaque ephemeral handle; invalidation ⇒ UNKNOWN); (4) visibility evidence (freshness bounds, start-proof, two-dimension consistency, per-surface characterization before use); (5) redaction boundary (closed vocabularies; at-risk per statement; coarse-leak check; suppress ⇒ INCOMPLETE); (6) fixed failure-record format (13 fields, immutable-append, digest chain, FAIL visible when safe); (7) provenance/integrity controls (exact version binding, digest bindings, incident screening, anchoring PENDING, C3 no acceptance step); (8) twelve stop conditions with legend-keyed statuses; (9) test definitions T1–T12 with expected classifications (execution gated); (10) planned-only evidence-package structure (nothing created); (11) independent review under technical separation only.

Independently verified by MiMo-V2.6-Flash: **VERIFIED** (three low findings resolved; re-verification none found). Verification records exist for each phase.

## 7. Phase F — feasibility verdict (verified)

**`FEASIBLE_WITH_NEW_AUTHORIZATION`** — governing verdict for completing the proof.
- **Feasible now (source-and-document-only):** Q1 read-path inventory, Q2 value-domain proof, Q3 handle-lifecycle design record, Q4 class-level negative search, Q5 no-passthrough proof, Q6 re-identification analysis, Q7 redaction-predicate analysis (sufficiency remains INCOMPLETE until tests), Q8 package review.
- **Requires new owner authorization (Gate G/I):** live correlation/visibility evidence, Q7 adversarial tests, evidence placement + D2 arrangement setup (separate authorization), qualification execution/deployment.
- **Why not the alternatives:** the complete proof needs gated runtime evidence (rules out "existing authorization" as a whole); no preserved rule makes a compliant method impossible (rules out "not feasible"); C3 blocks closure by design, not feasibility.

## 8. Status ledger

| Phase | Status |
|---|---|
| A plan | COMPLETE — VERIFIED |
| B evidence-package designs | COMPLETE — VERIFIED |
| C custody/acceptance options | COMPLETE — VERIFIED |
| D owner gate 1 | DECIDED (D2 + C3 + undesignated + R2/B2) |
| E proof plan | COMPLETE — VERIFIED |
| F feasibility verdict | COMPLETE — VERIFIED (`FEASIBLE_WITH_NEW_AUTHORIZATION`) |
| G owner gate 2 | **STOPPED — awaiting owner** |
| H source-only execution | not started (available on owner direction) |
| I qualification execution | NOT AUTHORIZED |
| J review/closure | not reached |

Gate: **BLOCKED.** P00/G0, H01, H02: OPEN/BLOCKED. P1: DEFERRED. P2 implementation, disposable-lab provisioning, native testing: PAUSED.

## 9. What the consultant is asked to do

Please review the end-to-end record and reply with:

1. **Consistency check** — do the governance rules, the D8 artifact, the specification, the proof plan and the verdict fit together without contradiction? Flag any rule that is silently weakened or any status mapping that drifts.
2. **Soundness check** — is `FEASIBLE_WITH_NEW_AUTHORIZATION` the right verdict given C3 and the absence of target access? Is the source-only/runtime split correctly drawn?
3. **Gap analysis** — what evidence classes, controls or stop conditions are missing, under-specified, or untestable as written? (Specifically: identity-proof completeness for Q1/Q2/Q4/Q5; the D5 timing gap; the rule-3/rule-10 object separation; stop 10's context split.)
4. **Gate G recommendation** — given the owner's posture (no target access so far; no acceptance under C3; conservative governance), what is the narrowest defensible next authorization: the source-only Phase H subset, a scoped runtime observation, Q7 adversarial tests, or none? Provide exact suggested authorization wording.
5. **Risk assessment** — what could go wrong in each option (evidence overreach, identity leakage, correlation failure, false assurance), and which failure modes the stop matrix may not catch.
6. **Closure realism** — under C3, what would a defensible closure path look like if the owner ever wants one (acceptance authority selection, evidence destination verification, integrity anchoring), and what should *not* be claimed?

Please answer in terms of the preserved rules above; do not assume any target behavior, do not assume the baseline is current, and do not propose anything that requires credentials, identities, or incident-derived material.

## 10. Appendix — artifact inventory (paths relative to `apps/construction/docs/ai/work-items/WBS/`)

- Disposition: `P00_G0_MARIADB_FEASIBILITY_REVIEW_DISPOSITION_REV_05_2026-10-31.md` (+ prior revisions 01–04, provenance/continuation docs)
- Provenance: `P00_G0_MARIADB_PUBLIC_SOURCE_PROVENANCE_2026-11-01.md`, `P00_G0_MARIADB_PROVENANCE_CONTINUATION_2026-11-01.md`, `P00_G0_MARIADB_KEY_ASSURANCE_AND_WITNESS_SKETCH_2026-11-01.md`
- D8 chain: `P00_G0_MARIADB_D8_BOUNDED_CLASSIFICATION_DRAFT_2026-11-01.md` → `_REV_02_` → `_REV_03_`; closure record
- Spec chain: `P00_G0_MARIADB_D8_QUALIFICATION_DESIGN_SPEC_2026-11-01.md` → `_REV_02_`; closure record
- Program: `P00_G0_TECHNICAL_CONTINUATION_PLAN.md/.json`, `P00_G0_EVIDENCE_PACKAGE_DESIGNS.md/.json`, `P00_G0_CUSTODY_ACCEPTANCE_OPTIONS.md/.json`, `P00_G0_OWNER_DECISION_PACKET_CUSTODY_2026-11-01.md`, `P00_G0_OWNER_GATE_D_DECISION_RECORD_2026-11-01.md`, `P00_G0_D8_QUALIFICATION_PROOF_PLAN.md/.json`, `P00_G0_D8_FEASIBILITY_VERDICT.md/.json`
- Verifications: `*_VERIFICATION.md` for phases A–F
- Ledger: `P00_G0_CONTINUATION_LEDGER_2026-11-01.md`

## 11. Definitions (for the consultant)

- **Witness**: a mechanism producing observable evidence that a transaction is read-only, without mutating target data.
- **Bounded classification**: a fixed, non-identifying label (e.g. `MODE_READONLY`, `MODE_ABSENT`, `MODE_WITHHELD`) emitted instead of raw values.
- **UNKNOWN / INCOMPLETE**: see rules 11–13 above; neither may ever be recorded as a pass or converted into the other.
- **C3**: the owner's current choice that no evidence is accepted; records remain inputs to any future decision.
- **Gate G**: the owner decision point that would authorize execution beyond source-and-document-only work.

*End of letter. This briefing is a status document, not an authorization; the gate remains BLOCKED.*
