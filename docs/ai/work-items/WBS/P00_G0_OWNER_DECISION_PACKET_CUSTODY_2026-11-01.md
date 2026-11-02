# P00/G0 — Owner decision packet: custody, destination, acceptance authority, retention (Phase D gate), 2026-11-01

**This is a decision packet, not a decision.** Nothing below is selected, approved, or executable. Selecting any option is the owner's business decision; executing a selection (directory creation, permissions, backup configuration, key handling, custody act, evidence placement) requires a **separate owner authorization** beyond selection. Gate remains BLOCKED before and after selection until the §10 closure conditions are met.

Packet basis: verified Phase A plan, Phase B designs, Phase C options (digests in the ledger). Verifier: MiMo-V2.6-Flash (technical separation only — not independent human custody, not acceptance).

## 1. Decisions requested (four)

| # | Decision | Options (design-only, none selected) |
|---|---|---|
| 1 | Evidence destination | D1 in-repo workstream dir · D2 owner-managed out-of-repo encrypted store · D3 external attested repository |
| 2 | Custody-acceptance process | C1 owner-as-acceptor (owner ≠ recorder/custodian of that evidence) · C2 designated external human acceptor (currently unselected; compatibility with the no-adjudicator rule must be evaluated) · C3 no acceptance (records remain inputs) |
| 3 | Acceptance authority | Undesignated. Options track decision 2: owner (C1) · designated external acceptor (C2) · remain undesignated (C3) |
| 4 | Retention and recovery arrangement | R1 minimal retention + verified destruction · R2 fixed retention classes · R3 owner-directed indefinite hold — combined with backup/key options B1 (none/ephemeral) · B2 (encrypted, owner key, restore-tested) · B3 (dual-control/escrow) |

Supporting areas the owner may also direct (no selection required now): permission model (P1/P2/P3), integrity-reference location (I1/I2/I3), invalidation authority (V1/V2/V3), conflict checks/attestation chain (A1/A2/A3).

## 2. Assurance tradeoffs (summary, non-recommending)

- **Highest preservation**: D3 + B3 + I3 + R3 — strongest continuity and independence potential, largest external dependency and exposure.
- **Balanced**: D2 + B2 + I2 + R2 — encrypted owner-managed store with restore-tested backup and separate append-only integrity media.
- **Minimal-footprint**: D1 + B1 + I1 + R1 — simplest, weakest custody independence; suitable only if evidence is expected to be provisional.
- **No-acceptance posture**: C3 keeps every record an unaccepted input; this is fully consistent with all preserved rules and intentionally blocks progress toward gate closure.
- Governance interactions: C2/R3/A3 enlarge external dependence and touch the external-acceptor question that remains deliberately unselected; C1 is only permissible if the owner is not the recorder/custodian of the evidence accepted; any choice must keep the custodian from self-accepting.

## 3. Recommended option, if any

**None.** The technical worker makes no recommendation: the choice trades assurance against exposure and touches governance decisions reserved to the owner. No option is represented as approved.

## 4. What happens after selection

1. The owner records the four selections (and any supporting-area directions) in a signed decision record.
2. A **separate** authorization is required for execution: directory creation, permissions, backup/key configuration, evidence placement, or any custody act — none of which is authorized by this packet or by selection alone.
3. Only then may Phase E (qualification-proof plan) proceed, using the selected arrangement; Phase F (feasibility verdict) follows; any target-side step still requires Gate G (and Gate I for qualification execution).
4. The gate remains BLOCKED throughout; closure additionally requires §10 conditions and the owner's separate closure acceptance.

## 5. Exact authorization wording (template, for the owner to adapt and sign)

> I select the following P00/G0 custody arrangement: evidence destination **[D1 | D2 | D3, with path/repository if applicable]**; custody-acceptance process **[C1 | C2 | C3]**; acceptance authority **[owner | designated external human acceptor (name/role) | remain undesignated]**; retention and recovery **[R1 | R2 | R3] with backup/key option [B1 | B2 | B3]**; permission model **[P1 | P2 | P3]**; integrity-reference location **[I1 | I2 | I3]**; invalidation authority **[V1 | V2 | V3]**; conflict/attestation **[A1 | A2 | A3]**.
>
> I separately authorize execution of this selection **only to the extent of [create the evidence directory at <path> / configure permissions / configure backup and key handling / place the following evidence artifacts: <list>]**, under the preserved rules (no independent human adjudicator; custodian cannot self-accept custody evidence; AI review is not independent human custody; incident material excluded; no credentials/identities collected; baseline historical reference only).
>
> This authorization does not authorize target access, credential access, administrative inspection, privilege changes, provisioning, implementation, testing, qualification execution, or deployment, and does not close P00/G0, H01 or H02 or change the BLOCKED gate status.

## 6. Stop condition honored

Per the approved plan, this packet stops the flow at Gate D: no directory creation, permission change, backup configuration, key handling, evidence placement, or custody act has occurred or will occur without the separate execution authorization above.

P00/G0, H01, H02 open/BLOCKED; P1 deferred; P2 paused.
