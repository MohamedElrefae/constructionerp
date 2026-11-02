# P00/G0 — Evidence-package designs (Phase B), 2026-11-01

**Status: NON-EXECUTABLE DESIGNS ONLY.** These eight designs define how each Q1–Q8 evidence package would be produced **if and when separately authorized**. Nothing here is produced, implemented, tested, qualified, accepted or authorized. Machine-readable twin: `P00_G0_EVIDENCE_PACKAGE_DESIGNS.json`. Verification: MiMo-V2.6-Flash, recorded in `P00_G0_EVIDENCE_PACKAGE_DESIGNS_VERIFICATION.md`.

Common constraints (apply to all packages): worst-case analysis only (sampling ⇒ INCOMPLETE); confirmed-failure branch split per the stable artifact's rules 4(a)/6 (safe ⇒ FAIL visible on the attempt/overall assessment; leak-risk ⇒ withhold + INCOMPLETE); outputs limited to closed vocabularies and fixed reason sets; no credentials, raw unexpected values, SQL/script bodies, user identities, document identifiers or unrelated business records; incident-derived material excluded; stopped attempts are not completed campaigns; confirmed failures remain visible; redaction uncertainty ⇒ INCOMPLETE, never a pass; no broader-access retry after a stop.

---

## Q1 — Read-path inventory

- **Purpose:** establish a closed manifest of every input channel the comparison method reads.
- **Inputs:** method interface declaration; the recorded upstream source reference paths (10.11.14); spec REV_02 §1.1.
- **Procedure:** enumerate every read site from the interface declaration and a static read-path review; record each channel's **surface, field, type and cardinality**; map each read to a fixed preapproved class; record any read that cannot be classified.
- **Expected evidence:** the closed manifest; the read-set enumeration; the source-level review record with file/line references.
- **Redaction rules:** field names, types and classes only — no server values, no row data, no samples.
- **Failure/stop conditions:** unclassifiable read ⇒ stop, UNKNOWN; incomplete read-set ⇒ INCOMPLETE; any read of an identity-bearing field ⇒ Q1 fails (stop).
- **Status mapping:** manifest incomplete ⇒ INCOMPLETE; unclassifiable channel ⇒ UNKNOWN; confirmed identity-bearing channel ⇒ failure recorded, attempt INCOMPLETE.
- **Required artifacts:** `q1_manifest.json`, `q1_readset_review.md`.
- **Qualification criteria:** completeness demonstrated by design-level enumeration accepted by independent technical review; no sampling-based claims.

## Q2 — Input value-domain proof

- **Purpose:** prove per-field that no identity-bearing value can enter.
- **Inputs:** Q1 manifest; field type declarations.
- **Procedure:** for each field, enumerate its possible value domain worst-case; classify each as bounded-class, opaque-handle, or excluded; document why no free-text field, user/host/credential-bearing field, or server-generated string capable of embedding identity can enter.
- **Expected evidence:** per-field domain tables; exclusion rationale; class mapping.
- **Redaction rules:** domain descriptors and class labels only; no example values retained.
- **Failure/stop conditions:** any free-text or identity-bearing field ⇒ stop; undetermined domain ⇒ INCOMPLETE; unrecognized field ⇒ UNKNOWN.
- **Status mapping:** per-field table incomplete ⇒ INCOMPLETE; unclassifiable value domain ⇒ UNKNOWN.
- **Required artifacts:** `q2_domains.json`, `q2_analysis.md`.
- **Qualification criteria:** worst-case coverage of every Q1 channel, independently reviewed.

## Q3 — Opaque-handle lifecycle proof

- **Purpose:** prove correlating handles carry no identity and cannot be resolved to a principal.
- **Inputs:** mechanism design (future); spec REV_02 Q3/E3 requirements.
- **Procedure:** document construction (non-principal derivation), uniqueness scope (single assessment), resolvability analysis, lifecycle (creation, destruction at record close, never carried across assessments).
- **Expected evidence:** construction record; uniqueness statement; resolvability analysis; lifecycle/destruction record.
- **Redaction rules:** handles recorded only as opaque tokens with no derivable attributes.
- **Failure/stop conditions:** any principal derivation or external resolvability ⇒ stop; undocumented lifecycle ⇒ INCOMPLETE; conflicting construction evidence ⇒ FAIL where safe.
- **Status mapping:** missing construction proof ⇒ INCOMPLETE; derivable handle ⇒ failure (attempt INCOMPLETE); unresolvable uniqueness ⇒ UNKNOWN.
- **Required artifacts:** `q3_handle_lifecycle.json`, `q3_review.md`.
- **Qualification criteria:** independent review confirms non-derivability and destruction guarantees by design.

## Q4 — Bounded adversarial negative-search

- **Purpose:** adversarially search the input space for identity-encoding values or combinations.
- **Inputs:** Q1/Q2 outputs; auxiliary-data categories (categories only, no data collected).
- **Procedure:** enumerate adversarial input/value/combination classes (including indirect identifiers: timing joins, ordering, cardinality); record each class's outcome and residual risk.
- **Expected evidence:** search log in class terms; residual-risk statement; class-withdrawal decisions.
- **Redaction rules:** findings expressed only as class outcomes and statuses; no discovered value retained.
- **Failure/stop conditions:** unbounded residual risk ⇒ withdraw the affected input class ⇒ Part 4 stop 1 (INCOMPLETE); search inconclusive ⇒ INCOMPLETE; discovered identity-encoding path ⇒ stop.
- **Status mapping:** per stable artifact: exposure risk ⇒ INCOMPLETE; unmatched/undetermined search outcomes ⇒ UNKNOWN.
- **Required artifacts:** `q4_negative_search.json`, `q4_residual_risk.md`.
- **Qualification criteria:** bounded residual risk per class, independently reviewed; unbounded ⇒ class withdrawn, not waived.

## Q5 — No-passthrough proof

- **Purpose:** prove emitted outputs are label constants, never server-value transformations.
- **Inputs:** output vocabulary (C1–C6, E1–E4, statuses, reasons); emission-path design.
- **Procedure:** map every emission site to a constant; analyze for any substring/transform path from server values; enumerate the closed vocabulary.
- **Expected evidence:** emission mapping table; vocabulary closure proof; transform-absence analysis.
- **Redaction rules:** outputs are constants only; no observed values in the proof.
- **Failure/stop conditions:** any passthrough path ⇒ stop (Q5 fails); unanalyzed emission site ⇒ INCOMPLETE.
- **Status mapping:** unanalyzed site ⇒ INCOMPLETE; confirmed passthrough ⇒ failure recorded, attempt INCOMPLETE; non-constant output ⇒ UNKNOWN (out-of-vocabulary).
- **Required artifacts:** `q5_emission_map.json`, `q5_vocabulary.md`.
- **Qualification criteria:** complete emission-site coverage and independent review of the no-transform analysis.

## Q6 — Re-identification analysis

- **Purpose:** bound what re-identification would require from the complete output record.
- **Inputs:** output record schema (labels, statuses, reasons, timing granularity, handle); auxiliary-data categories.
- **Procedure:** enumerate realistic auxiliary-data categories; analyze joins/combinations; identify any field whose retention enables re-identification; apply least-data coarsening.
- **Expected evidence:** attack analysis; coarsening decisions; residual-risk statement.
- **Redaction rules:** analysis in category terms; no auxiliary dataset is collected or retained.
- **Failure/stop conditions:** unbounded re-identification risk ⇒ INCOMPLETE; required coarsening undecidable ⇒ stop; any field whose purpose cannot be justified ⇒ drop.
- **Status mapping:** unresolved risk ⇒ INCOMPLETE; undetermined auxiliary category ⇒ UNKNOWN.
- **Required artifacts:** `q6_reid_analysis.md`, `q6_coarsening.json`.
- **Qualification criteria:** bounded risk under stated auxiliary assumptions, independently reviewed.

## Q7 — Redaction-method qualification

- **Purpose:** qualify the redaction boundary and its predicates.
- **Inputs:** redaction predicates; "at risk" per-statement definition; spec Part 2 control 3.
- **Procedure:** worst-case analysis of each predicate; coarse-status leak check design; adversarial test plan (tests only under a future separate grant).
- **Expected evidence:** predicate analysis; leak-check design; test plan (not executed); test evidence only when separately authorized.
- **Redaction rules:** predicates and class outcomes only; no suppressed values, no examples.
- **Failure/stop conditions:** uncertain redaction sufficiency ⇒ INCOMPLETE; coarse-status leak path ⇒ stop; test execution without grant ⇒ prohibited.
- **Status mapping:** uncertain ⇒ INCOMPLETE (never a pass); missing predicate analysis ⇒ INCOMPLETE; unclassifiable redaction need ⇒ UNKNOWN.
- **Required artifacts:** `q7_redaction_predicates.md`, `q7_test_plan.md` (plan only).
- **Qualification criteria:** worst-case analysis reviewed; test evidence outstanding until separately granted; no pass is claimable without it.

## Q8 — Independent package review

- **Purpose:** review the complete Q1–Q7 package under technical author/reviewer separation.
- **Inputs:** Q1–Q7 artifacts.
- **Procedure:** structured review of completeness, internal consistency, boundary restatements, status mapping; record disagreements without erasure; escalate rule-affecting issues to the owner.
- **Expected evidence:** review record with findings, severities and resolutions.
- **Redaction rules:** review notes in class terms; no values.
- **Failure/stop conditions:** unresolved blocking finding ⇒ package INCOMPLETE; reviewer disagreement on a preserved rule ⇒ owner escalation (stop).
- **Status mapping:** review record complete ⇒ package eligible for Part 3 consideration only; missing review ⇒ INCOMPLETE.
- **Required artifacts:** `q8_review_record.md`.
- **Qualification criteria:** review under technical separation only — **not** independent human custody, **not** acceptance, **not** qualification of the method.

---

All eight designs remain non-executable: producing them did not create evidence, did not test or configure anything, and authorizes nothing. The gate remains BLOCKED.

P00/G0, H01, H02 open; P1 deferred; P2 paused.
