# P00/G0 — Q7 adversarial test-design matrix (document-only), 2026-11-01

**Status: TEST-DESIGN RECORD ONLY — no case is authorized for execution under this authorization.** No test was run; no target, live observation, correlation/visibility collection, configuration change, or D2 access occurred. **Q7 remains `INCOMPLETE` upon issuance.** Gate remains **BLOCKED**. Machine-readable twin: `P00_G0_Q7_ADVERSARIAL_TEST_DESIGN_MATRIX.json`.

**Consistency basis:** Phase E tests T1–T12 (proof plan §9); Q7 predicates P1–P6 (Phase H evidence §Q7); D8 bounded-classification set (C1–C6 labels, E1–E4 expected classes, statuses UNKNOWN/INCOMPLETE/FAIL); preserved business rules; the accepted Phase H/Q8 record chain (Gate G4). Every expected status below uses only the stable statuses; no comparison or execution occurs here.

**Authorization limits (as issued):** document-only design; no execution of any test; no target access; no live observation, correlation or visibility evidence collection; no configuration change; no D2 creation/access/placement; no custody acceptance; no qualification; no closure; no broader-access retry. This matrix expires the authorization upon issuance and triggers no execution.

---

## 1. Conventions

### 1.1 Predicate references (P1–P6, from the Phase H Q7 design)

- **P1** field allowlist (booleans/enums only)
- **P2** absolute exclusions (text, identifiers, pointers, raw timers)
- **P3** at-risk assessed per statement
- **P4** coarse-leak check before every emission
- **P5** withheld values never emitted
- **P6** uncertainty ⇒ `INCOMPLETE` (never a pass)

### 1.2 Status and stop mapping (Phase E stop matrix; S1–S12 numbering)

| S# | Trigger | Status |
|---|---|---|
| S1 | identity/credential/query-body/suppressed-value exposure risk | INCOMPLETE (withhold) |
| S2 | redaction sufficiency uncertain (or confirmed redaction failure) | INCOMPLETE on uncertainty; **FAIL visible** where the failure is confirmed and safe to state |
| S3 | correlation invalidated | UNKNOWN |
| S4 | freshness/visibility gap | INCOMPLETE |
| S5 | version-context mismatch | UNKNOWN |
| S6 | value outside closed vocabulary | UNKNOWN |
| S7 | method unqualified | UNKNOWN (classification fact) |
| S8 | authorization record missing | UNKNOWN |
| S9 | suspected incident/target-derived input | UNKNOWN |
| S10 | integrity-chain break | FAIL where safe; INCOMPLETE on leak risk |
| S11 | need for excluded activity (config/write/target/identity/provisioning/testing) | stop; INCOMPLETE else UNKNOWN |
| S12 | unexpressible output | UNKNOWN |

### 1.3 Coarse-leak probe template (applies to every case marked P4)

**Definition:** emit only the permitted bounded output for the case; then attempt to infer from *any* emitted field (status, reason, timing class, field count, ordering) the suppressed value, its identity, its exact boundary, or its presence/absence beyond the permitted coarse class.
**Pass boundary:** no suppressed information is inferable; output contains only allowed labels/statuses/reasons.
**Fail boundary:** any suppressed value, exact boundary, or extra presence/absence is inferable ⇒ the case fails; withhold the offending output; record `INCOMPLETE` (or `FAIL` if a redaction failure is confirmed and safely stateable).

### 1.4 Required evidence-record fields (future execution only — no record is created now)

ERF fields, per case run: `attempt_id` (opaque) · `case_id` · `predicate` · `objective` · `input_class` · `expected_status` · `observed_status` · `probe_result` {pass|fail} · `suppression_outcome` {withheld|emitted-allowed|n/a} · `correlation_probe_result` · `stop_triggered` {S#|none} · `integrity` {prev_digest, this_digest} · `reviewer_separation` {author|reviewer} · `timestamp_class` (coarse) · `notes_redacted`.

---

## 2. Case matrix

### 2.1 P1 — field allowlist

| ID | Adversarial objective | Input class / condition (abstract) | Expected bounded status | Stop on failure |
|---|---|---|---|---|
| `Q7-P1-01` | detect a non-allowlisted field entering the extraction path | input class: field outside the allowlist, type-valid | **INCOMPLETE** (withhold) | S2 |
| `Q7-P1-02` | detect an allowlisted field yielding a value outside its enum | input class: allowlisted field, out-of-enum value | **UNKNOWN** (out-of-vocabulary) | S6 |
| `Q7-P1-03` | detect conflicting duplicate reads of one allowlisted field | input class: same field, two conflicting valid values | **INCOMPLETE** (inconsistent evidence) | S2 |
| `Q7-P1-04` | control: confirm the clean path emits nothing extra | input class: all fields allowlisted, enums valid | eligible-path expectation only (**E1 consideration**, never a pass claim) | none (control) |

Coarse-leak probe: emitted output must not reveal the rejected field's identity or value (only the refusal class). Suppression boundary: for `Q7-P1-01`/`03`, the attempt and overall assessment are `INCOMPLETE`, value withheld.

### 2.2 P2 — absolute exclusions

| ID | Adversarial objective | Input class / condition | Expected bounded status | Stop on failure |
|---|---|---|---|---|
| `Q7-P2-01` | detect query/statement text entering any read path | input class: text-bearing field (content not retained) | **INCOMPLETE** (withhold; class withdrawn) | S1 |
| `Q7-P2-02` | detect a consumer request for an identifier field | input class: identifier field requested | **INCOMPLETE** (refuse) | S1 |
| `Q7-P2-03` | detect pointer/free-text engine field exposure | input class: pointer or free-text field | **INCOMPLETE** | S1 |
| `Q7-P2-04` | control: exclusions absent from payload | input class: payload with no excluded fields | no status change (pass boundary) | none (control) |

Coarse-leak probe: the refusal must not echo the requested identifier or its shape; pass boundary = refusal conveys only a class, no value fingerprint.

### 2.3 P3 — at-risk assessed per statement

| ID | Adversarial objective | Input class / condition | Expected bounded status | Stop on failure |
|---|---|---|---|---|
| `Q7-P3-01` | detect a statement that names a suppressed value | input class: statement referencing a suppressed value (abstracted) | **INCOMPLETE** (statement withheld) | S2 |
| `Q7-P3-02` | detect inference via comparison ("above/below boundary") | input class: comparative statement permitting inference | **INCOMPLETE** | S2 |
| `Q7-P3-03` | control: statement references only label/status | input class: class-only statement | pass boundary (no inference) | none (control) |

Coarse-leak probe: verify the withheld statement is not reconstructible from the emitted reason/status pair.

### 2.4 P4 — coarse-leak check

| ID | Adversarial objective | Input class / condition | Expected bounded status | Stop on failure |
|---|---|---|---|---|
| `Q7-P4-01` | detect whether a coarse status itself reveals suppressed detail | input class: coarse status adjacent to withheld detail | **INCOMPLETE** (withhold even the coarse status if it leaks) | S2 |
| `Q7-P4-02` | detect timing granularity leaking activity boundaries | input class: precise timestamp alongside coarse result | **INCOMPLETE** (coarsen or withhold) | S2 (S4 if visibility-related) |
| `Q7-P4-03` | control: coarse status leaks nothing | input class: coarse status only | pass boundary | none (control) |

Probe definition and pass/fail boundary: §1.3. Suppression boundary: `Q7-P4-01` requires withhold + `INCOMPLETE`; `Q7-P4-02` requires coarsening to a class boundary that admits no inference.

### 2.5 P5 — withheld values never emitted

| ID | Adversarial objective | Input class / condition | Expected bounded status | Stop on failure |
|---|---|---|---|---|
| `Q7-P5-01` | detect a withheld value present in a record or log | input class: record containing a withheld value (simulated marker only) | **FAIL** (confirmed redaction failure, visible when safe); **INCOMPLETE** if stating the failure leaks | S2 (status per legend: FAIL confirmed; INCOMPLETE on leak risk) |
| `Q7-P5-02` | detect reconstruction from aggregate classes | input class: multiple emitted classes combining to one value | **INCOMPLETE** (withhold those classes) | S2 |
| `Q7-P5-03` | detect withheld value persisting into staging after close | input class: staging residue of withheld value (lifecycle) | **FAIL** where safe; else **INCOMPLETE** | S2 |

Probe: reconstruction attempt across the full output; pass boundary = no combination recovers the value or its exact boundary.

### 2.6 P6 — uncertainty ⇒ INCOMPLETE

| ID | Adversarial objective | Input class / condition | Expected bounded status | Stop on failure |
|---|---|---|---|---|
| `Q7-P6-01` | predicate evaluation itself ambiguous | condition: classification ambiguous under the predicate | **INCOMPLETE** (never pass) | S2 |
| `Q7-P6-02` | conflicting surface evidence | condition: two permitted surfaces disagree | **INCOMPLETE** | S2 |
| `Q7-P6-03` | predicate skipped by error | condition: evaluation aborted mid-case | **INCOMPLETE** | S2 |

Coarse-leak probe: an `INCOMPLETE` may not encode which predicate failed in a way that reveals suppressed state beyond the allowed reason class.

### 2.7 Binding / correlation leakage (where applicable)

| ID | Adversarial objective | Input class / condition | Expected bounded status | Stop on failure |
|---|---|---|---|---|
| `Q7-BND-01` | detect handle→session derivation | condition: attempt to resolve the opaque handle to a session/principal | **FAIL** if derivable (never a pass); otherwise pass boundary | S1 (identity exposure class) |
| `Q7-BND-02` | detect cross-assessment handle reuse | condition: same handle presented in a second assessment | **UNKNOWN** (correlation invalid) | S3 |
| `Q7-BND-03` | detect transaction-identifier linkage | condition: attempt to bind record to a transaction identifier | **INCOMPLETE** (identifier excluded) | S1 |

---

## 3. Cross-map to Phase E T1–T12

| Phase E case | Matrix relationship |
|---|---|
| T1 eligible path | `Q7-P1-04` control |
| T2 reconnect mid-attempt | `Q7-BND-02` (correlation invalid ⇒ UNKNOWN) |
| T3 absent/not-started record | no Q7 case (visibility/absence domain) |
| T4 redaction uncertain | `Q7-P3-01/02`, `Q7-P6-01` |
| T5 version suffix mismatch | no Q7 case (version domain; S5) |
| T6 unqualified comparison | no Q7 case (S7 domain) |
| T7 integrity break | `Q7-P5-01` adjacent (record integrity) |
| T8 out-of-vocabulary | `Q7-P1-02` |
| T9 missing authorization record | no Q7 case (S8 domain) |
| T10 incident-derived input | no Q7 case (S9 domain) |
| T11 excluded-activity need | no Q7 case (S11 domain) |
| T12 exposure risk | `Q7-P2-*`, `Q7-BND-01` |

## 4. Required evidence fields (future execution only)

Each case's future run must populate the ERF fields of §1.4 and nothing else; no SQL text, identities, credentials, raw values or document identifiers. **No evidence record is created, and no case is authorized for execution, under this authorization.**

## 5. Non-execution statement and expiry

**Explicit statement: no case in this matrix is authorized for execution under this authorization.** The matrix defines test cases, expected bounded statuses, probes, stop conditions and future evidence fields only. Q7 remains `INCOMPLETE`; the gate remains `BLOCKED`; no qualification, acceptance, custody or closure is implied. This authorization expired upon issuance of this matrix.

P00/G0, H01, H02 open; P1 deferred; P2 paused.
