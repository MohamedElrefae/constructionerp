# Scope Descriptor — bilingual-terms-conditions-master

**Work item:** `bilingual-terms-conditions-master`
**Branch:** `develop`
**Status:** `COMPLETE` — patch v9_12 applied, registry `Terms and Conditions` active, 15-module matrix
**Base commit:** `0f3bd24` (Brand master onboarding complete)
**Date:** 2026-10-04
**Authority:** owner directive in session (Terms and Conditions second of the deferred ledgers queue)
**Scope:** patch `v9_12` (Arabic columns on `Terms and Conditions`), registry onboarding to `active`,
triple registration (F1), pilot test module, P95 measurement, matrix integration.

---

## 1. Field audit (read-only, `v16.localhost`, 2026-10-04)

| Property | Value |
|---|---|
| Registry entry | **ABSENT** |
| Rows | **1** (`_Test Terms and Conditions`) |
| `autoname` | `field:title` |
| `title_field` / `meta.search_fields` | none / none |
| Fields | `title` (Data, reqd) · `disabled` (Check) · `selling` (Check) · `buying` (Check) · `terms` (Text Editor) · `terms_and_conditions_help` (HTML) |
| Index | PRIMARY on `name` only |
| Arabic column | **absent** → patch required |
| Narrative tier | `terms` → Tier 2 via `narrative_sanitizer.get_narrative_fields_for_doctype("Terms and Conditions")` |

Consequences carried into design:

1. `field:title` is the **9th** master with that autoname pattern (precedents: `Brand`, `Payment Terms
   Template`, `Asset Category`, `UOM`, `Territory`, `Customer Group`, `Item Group`,
   `Supplier Group`, `Item`) — registry shape is copied from `Brand` / `Payment Terms Template`
   (`identity_field: name`, `english_field: title`, `arabic_field: title_ar`, `norm_field: title_ar_norm`).
2. `terms` is narrative Tier 2 and therefore **excluded from `search.fields`** by established
   policy (narrative prose never enters registry search fields).
   Search fields are exactly `["title", "title_ar"]`.
3. 1 row means no zero-row seed contract applies; P95 can measure real data plus a fixture prefix.
4. Rows are ERPNext test fixtures (`_Test …`); measurement fixtures use prefix `CT-TERMS-`
   and are deleted after the run.

---

## 2. Architecture & Governance (F1 & D5)

### 2.1 Finding F1 Applied — Triple Registration

Per finding F1 in `bilingual-brand-master/SCOPE.md` §3.1, onboarding a master requires three registrations:
1. **Schema & Norm fields**: patch `v9_12` (`add_terms_and_conditions_arabic_fields.py`) adding `title_ar` and `title_ar_norm`.
2. **Bilingual Registry**: active entry with search configuration in `bilingual_registry.json`.
3. **Save-time Gate (`doc_events`)**: `enforce_bilingual_arabic_policy` for Arabic policy & norm derivation, plus `narrative_sanitizer.validate_narrative_fields` for narrative Tier 2 field `terms`.

### 2.2 Invariant D5 Preserved

- Code diad (`bilingual_service.py`, `search.py`) remains **0 bytes** diff across all seven reference commits.
- Bilingual registry grows monotonically (additive entry for `Terms and Conditions`, no regressions).

---

## 3. Deliverables

1. `construction/patches/v9_12/add_terms_and_conditions_arabic_fields.py` + `patches.txt` entry —
   adds `title_ar` (Data) and `title_ar_norm` (Data, read-only/hidden) after `title`,
   idempotent, with `revert()`; backfills `_norm` for existing non-empty Arabic.
2. Registry entry `"Terms and Conditions"` → `state: active`, with `search.fields = ["title", "title_ar"]`.
3. `construction/hooks.py` `doc_events` registration for both bilingual policy and narrative sanitizer.
4. `construction/tests/test_bilingual_terms_conditions_pilot.py` — 8 tests: zero-service-edit guard,
   patch idempotence/reversibility, registry resolution, fail-closed on missing field,
   norm derivation + poison overwrite, BIDI rejection, identity/rename preservation, search across Alef/tatweel/diacritics.
5. P95 harness `evidence/scripts/measure_terms_conditions_p95.py` + measurement JSON + log, applying
   the two-tier SLA (governed ≤1.50 ms; Tier 2A ≥1.0 ms → ≤1.15×; Tier 2B <1.0 ms → ≤1.50×),
   **5 rounds × n=100 min-of-rounds**.
6. Matrix integration: module added to `scripts/run_bilingual_regression_matrix.sh`
   (15 modules, 189 tests) and all evidence pinned in `evidence/MANIFEST.json`.

---

## 4. Invariants

- **Code Diad Immutability**: `bilingual_service.py` and `search.py` stay byte-identical to all seven reference commits.
- **Monotonic Registry Growth**: Registry entry is additive; existing entries, unicode_policy, and governance blocks are untouched.
- `terms` (narrative Tier 2) never enters `search.fields`.
- All SQL parameterized; vendor repos untouched.

---

## 5. Out of scope

- `Asset` (remaining deferred ledger, sequenced after this work item).
- `Company` (GATED on statutory/legal/tax review).
- Wiring `SearchableDropdownEnhancer` / D4 remediation (deferred per `search-query-convention/SCOPE.md`).

---

## 6. Results (2026-10-04, evidence pinned in `evidence/MANIFEST.json`)

| Check | Result |
|---|---|
| Pilot module `test_bilingual_terms_conditions_pilot` | **8/8 OK** |
| Regression matrix `run_bilingual_regression_matrix.sh` | **189/189 across 15 modules** |
| ADR vs evidence reconciler | **19/19 PASS** |
| Invariant guard (D5 split) | code diad byte-identical to 7 refs; registry monotonic growth over 19 baseline masters; `test_transaction_link_search` **20/20** |
| Site migration | `v9_12` executed and recorded in `Patch Log`; all 21 registry masters resolve their `arabic_field` |
| P95 / two-tier SLA | baseline 0.441 ms, bilingual 0.627 ms, ratio **1.4218×** → Tier 2B (≤1.50×) and universal ceiling (≤1.50 ms) → `COMPLIANT_WITH_TWO_TIER_SLA` |

**Cleanup:** `_Test Terms and Conditions.title_ar` / `title_ar_norm` restored and no `CT-TERMS-` fixtures remain.
