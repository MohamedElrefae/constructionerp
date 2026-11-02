# P00/G0 — Closure execution plan (staged), 2026-11-01

**Status: PLANNING RECORD ONLY — no stage is authorized or started.** Each stage requires its own explicit owner authorization; the plan itself authorizes nothing, creates no custody, and does not alter C3. Gate BLOCKED. Companion: `P00_G0_CLOSURE_DECISION_PACKET_2026-11-01.md`, `P00_G0_OWNER_CLOSURE_DECISION_RECORD_2026-11-01.md`.

## 1. Stage map (each stage gated)

| Stage | Purpose | Gate | Outputs (once authorized) |
|---|---|---|---|
| S0 | Choose closure path (C3 revision R0–R3; authority A0–A2) | **owner** | decision record entry |
| S1 | Fix arrangement requirements (P/I/V/A, retention durations, key handling) | **owner** | arrangement specification |
| S2 | Create/configure D2 store (dir, permissions, encryption, backup, keys) | **owner — separate execution authorization** | arrangement record + configuration evidence |
| S3 | Place evidence artifacts + digest manifests | **owner — separate execution authorization** | placement manifest, chain verification |
| S4 | Runtime qualification (criteria 1–4) and/or Q7 adversarial tests | **owner — Gate G/I scope** | redacted runtime evidence, Q7 test evidence |
| S5 | Q8 re-review of any new/changed evidence | document-only act (authorization) | updated review record |
| S6 | Final closure determination and owner acceptance | **owner — closure only** | signed closure record; gate transition |

Skipping stages constrains what can be claimed: closure cannot be reached without S2–S3 (criteria 6–7), S4 (criteria 1–4), and S6 (criterion 9); S1/S5 are prerequisites for defensible claims.

## 2. Stage details

### S0 — Closure path decision
Inputs: closure packet §2–§3; current criterion statuses. Decisions: C3 revision option (R0–R3), acceptance-authority option (A0–A2). Accept checks: selections recorded in the owner decision record; no execution implied. Stop: any attempt to treat the decision as authorization to execute.

### S1 — Arrangement specification
Inputs: packet §4; Phase C options. Outputs: concrete parameter set (retention durations per class; key lifecycle; backup cadence and restore-test cadence; permission model; integrity anchoring; invalidation authority; attestation chain). Accept checks: every undesignated area resolved or explicitly deferred; no configuration performed yet. Stop: need to reach into D2 or the target.

### S2 — D2 store creation/configuration
Preconditions: S0 + S1 complete; separate execution authorization. Actions (when authorized): create dedicated path; set permissions; configure encryption at rest with owner-held key; configure backups and restore test; record configuration evidence with digests. Accept checks: configuration evidence complete; no evidence files placed yet; failure → stop (record UNKNOWN/INCOMPLETE; no broader retry). Rollback: teardown of the store is itself a destructive act and must be explicitly authorized.

### S3 — Evidence placement
Preconditions: S2 complete; separate authorization. Actions: compute digest manifest of every artifact before placement; place; recompute and verify; record placement event (who/what/when/digest); verify chain. Accept checks: manifest before/after consistent; no artifact altered (placement must not change bytes); failures recorded, never erased. Stop: any digest mismatch ⇒ FAIL where safe; placement halts.

### S4 — Runtime qualification / Q7 tests
Preconditions: target-side authorization (Gate G/I scope); defined principal, mechanism, destination; all stop conditions accepted. Actions only as authorized; every attempt records statuses per the stop matrix; uncertainty ⇒ UNKNOWN/INCOMPLETE; no broader retry. Accept checks: redaction verified; correlation/visibility evidence captured; Q7 test outcomes recorded. Stop: any stop condition ⇒ attempt terminated, authorization consumed.

### S5 — Q8 re-review
Preconditions: S3/S4 produced new evidence. Actions: document-only review against Q1–Q8 entry/exit criteria; reviewer ≠ author; findings with severities. Accept checks: no nonconformance unresolved; disagreements recorded. Stop: rule-affecting disagreement ⇒ owner escalation.

### S6 — Closure determination
Preconditions: all nine §10 criteria demonstrably met; S5 review issued; owner authorization. Actions: owner signs closure record stating permitted claims only; gate transition recorded. Accept checks: every claim traceable to evidence; no non-permitted claim (§5 of packet). Stop: any unmet criterion ⇒ no closure.

## 3. Stop and integrity rules (all stages)

Any of: preserved-rule change, target/credential need, destination/authority selection, custody selection, digest change, unsafe preservation, redaction/correlation/visibility/integrity failure, incident material, broader retry — halts execution; the stage records UNKNOWN/INCOMPLETE/FAIL; the owner is asked only for the specific decision. Stopped attempts are not completed campaigns; confirmed failures stay visible.

## 4. Authorization wording templates (owner to adapt and sign)

**S0 — closure path:**
> I select, for P00/G0 closure planning: C3 revision option **[R0|R1|R2|R3]** and acceptance-authority option **[A0|A1|A2]**; arrangement areas **[P/I/V/A selections or deferred]**. This selection authorizes no execution and does not alter C3 unless R1/R2 is selected and recorded as a revision.

**S2 — arrangement setup (separate):**
> I authorize creation/configuration of the D2 evidence store at **[path]** limited to: **[directory, permissions, encryption at rest with owner-held key, backup schedule, restore test]**. No evidence placement, target access, configuration beyond this list, or custody act. Stop on any uncertainty; record outcomes; no broader retry.

**S3 — evidence placement (separate):**
> I authorize placement of **[artifact list with digests]** into the D2 store, with digest manifests before/after and chain verification. No modification of artifact bytes; failures recorded; stop on mismatch.

**S4 — runtime / Q7 tests (separate):**
> I authorize **[target-side observation scope / Q7 adversarial tests]** using **[principal, mechanism, destination]**, under the stop matrix; redaction mandatory; no broader retry; any stop consumes this authorization.

**S6 — closure (separate, owner-only):**
> I accept closure of P00/G0 on **[date]** against criteria **[1–9 as evidenced]**, with claims limited to **[permitted claim list]**. The gate may transition from BLOCKED to CLOSED by this record only.

## 5. Current position

S0 not started; all stages unauthorized; no store exists; no evidence placed; no runtime work; C3 unchanged; gate BLOCKED.

P00/G0, H01, H02 open; P1 deferred; P2 paused.
