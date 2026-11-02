# P00/G0 — Custody and acceptance options (Phase C), 2026-11-01

**Status: DESIGN-ONLY OPTIONS — nothing selected, nothing created, no directory, permission, backup, key or custody action taken or authorized.** Eight areas, each with option sets and tradeoffs. Selection of the evidence destination, custody-acceptance process, acceptance authority and retention/recovery arrangement is **Owner Gate D** (Phase D). Machine-readable twin: `P00_G0_CUSTODY_ACCEPTANCE_OPTIONS.json`. Verification: MiMo-V2.6-Flash (technical separation only — not independent human custody, not acceptance).

Binding constraints for every option: no independent human adjudicator participates; the custodian cannot self-accept custody evidence; AI review is not independent human custody; the external human acceptor remains an **unselected** option; acceptance authority and evidence destination remain **undesignated** until the owner selects them; no credentials, identities, document identifiers or unrelated business records are collected; incident-derived material is excluded; retention decisions are owner decisions; any creation/configuration requires separate owner authorization beyond this design.

---

## 1. Evidence destination

| Option | Description | Tradeoffs |
|---|---|---|
| D1 | This workstream's in-repo docs directory | Simplest; versioned with the workstream; lowest assurance — not an independent location; digest chain only |
| D2 | Owner-managed out-of-repo encrypted store (path owner-chosen) | Separates evidence from the workstream tree; encryption/key decisions fall to area 3; requires owner-managed path and access model |
| D3 | External attested repository (third-party or organizational system) | Highest assurance potential; introduces external dependency, retention/authority questions, and acceptance-authority interplay |

## 2. Directory, ownership, permission, path-safety model

| Option | Description | Tradeoffs |
|---|---|---|
| P1 | Owner-only directory, `0700`, single principal | Minimal surface; no collaborative access; owner is sole custodian (self-acceptance prohibition still binds acceptance) |
| P2 | Dedicated service account with ACLs for recorder/acceptor separation | Supports role separation (recorder ≠ acceptor); more configuration, more principals to govern |
| P3 | Read-only mount plus append-only staging | Strong append-only property; operational complexity; writes occur only in staging |

## 3. Backup, recovery, encryption, key custody

| Option | Description | Tradeoffs |
|---|---|---|
| B1 | No backup — records ephemeral, regenerable only from authorized work | Lowest operational risk of key loss; weakest preservation; unsuitable if evidence must persist |
| B2 | Encryption at rest with owner-held key; periodic backup with restore verification | Balanced; key custody concentrated with owner; requires restore-test discipline |
| B3 | Dual-control/escrow key custody with independent backup custodian | Strongest continuity; adds a second principal and governance of that principal; conflicts with minimal-principal preferences |

## 4. Protected integrity-reference location

| Option | Description | Tradeoffs |
|---|---|---|
| I1 | Local digest chain carried in the record | Simple; tamper-evidence only; a party controlling the store could rewrite the chain |
| I2 | Separate append-only media (WORM or distinct host/media) | Stronger separation; operational overhead; still administered by the same owner |
| I3 | External timestamping/notarization service | Independent time/integrity anchor; external dependency and disclosure considerations |

## 5. Retention and destruction

| Option | Description | Tradeoffs |
|---|---|---|
| R1 | Minimal retention with scheduled destruction and verification records | Least data at rest; destroys re-verification ability after the window |
| R2 | Fixed retention classes per record type | Predictable lifecycle; requires upfront classification |
| R3 | Owner-directed indefinite hold | Maximum preservation; maximum exposure and least-data tension (must be justified) |

## 6. Custody-acceptance process (compatible with the no-self-acceptance rule)

| Option | Description | Tradeoffs |
|---|---|---|
| C1 | Owner accepts evidence as acceptance authority (owner ≠ custodian of the evidence being accepted) | No new role; the owner must not be the custodian/recorder of the same evidence; acceptance remains a business act, not adjudication |
| C2 | Designated external human acceptor (currently an unselected option) | Separation of acceptance from ownership; requires selecting a person/role and evaluating compatibility with the no-adjudicator rule; not approved today |
| C3 | No acceptance — records remain unaccepted inputs to any future decision | Fully preserves the status quo; nothing becomes "accepted evidence"; blocks progress toward gate closure by design |

## 7. Invalidation authority

| Option | Description | Tradeoffs |
|---|---|---|
| V1 | Owner only | Simple, consistent with ownership; single point of failure |
| V2 | Designated acceptor (if C2 selected) | Separates invalidation from ownership; requires the acceptor role to exist |
| V3 | Technical verifier for integrity failures only (scope-limited) | Fast integrity response; must not extend into business invalidation |

## 8. Conflict checks and attestation chain

| Option | Description | Tradeoffs |
|---|---|---|
| A1 | Self-declaration of conflicts by participants, recorded | Lightest; weakest independence signal |
| A2 | Reviewer attestation under technical separation (recorder ≠ reviewer) | Meaningful separation without new roles; still not independent human custody |
| A3 | Third-party attestation (external) | Strongest independence claim; external dependency; overlaps with C2 selection questions |

---

**Selection status: NONE.** No option in any area is selected, recommended, or represented as approved. Choosing among D1–D3, P1–P3, B1–B3, I1–I3, R1–R3, C1–C3, V1–V3, A1–A3, and designating (or leaving undesignated) the acceptance authority, is **Owner Gate D**. No directory creation, permission change, backup configuration, key handling, or custody act occurs before a separate owner authorization beyond this design.

P00/G0, H01, H02 open/BLOCKED; P1 deferred; P2 paused.
