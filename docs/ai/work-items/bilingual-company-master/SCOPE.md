# Scope Descriptor — bilingual-company-master

**Work item:** `bilingual-company-master`
**Branch:** `develop`
**Status:** `COMPLETE` — patch v9_14 applied, registry `Company` active, F1 dual-hook, 18-module matrix
**Base commit:** `e513f16`
**Date:** 2026-10-04
**Authority:** owner directive in session (Company final master of the deferred ledgers queue; statutory/legal/tax review released)
**Scope:** patch `v9_14` (Arabic columns on `Company`), registry onboarding to `active`,
F1 dual-hook registration, pilot test module, P95 measurement, matrix integration.

---

## 1. Field audit (read-only, `v16.localhost`, 2026-10-04)

| Property | Value |
|---|---|
| Registry entry | **ABSENT** |
| Rows | **21** |
| `autoname` | `field:company_name` (`name == company_name`) |
| `title_field` / `meta.search_fields` | none / none |
| Flags | `is_submittable = 0`, `track_changes = 1` |
| Required fields | `company_name` (Data) · `abbr` (Data) · `default_currency` (Link→Currency) · `country` (Link→Country) |
| Other fields | `company_description` (Text Editor) · `sales_monthly_history` (Small Text) · `parent_company` · `chart_of_accounts` · … |
| Arabic column | **absent** → patch required |
| Narrative tier | **present** — `narrative_sanitizer.get_narrative_fields_for_doctype("Company")` → `{'company_description': 2, 'sales_monthly_history': 1}` |
| Dependencies on site | Currency (`SAR`, `USD`, `EGP`) · Country (`Saudi Arabia`, `Egypt`) |

Consequences carried into design:

1. `autoname: field:company_name` means `name` is identical to `company_name`. Registry shape:
   `english_field: company_name`, `arabic_field: company_name_ar`, `norm_field: company_name_ar_norm`,
   `identity_field: name`, `code_field: null`.
2. `Company` carries two narrative fields: `company_description` (Tier 2, HTML/Text Editor) and
   `sales_monthly_history` (Tier 1, Small Text). Both must be sanitized on save against Bidi
   and control character injection, while strictly excluded from `search.fields`.
3. Finding **F1 dual-hook**: `doc_events["Company"]` must register **both**
   `enforce_bilingual_arabic_policy` and `narrative_sanitizer.validate_narrative_fields`.
4. Measurement fixtures use prefix `CT-COMP-` and are deleted after the run; zero leftover
   fixtures verified on cleanup.

---

## 2. Decisions (approved 2026-10-04)

### C1 — Harness-local ephemeral fixtures
Fixtures are created with prefix `CT-COMP-`, measured, and deleted on teardown.
No permanent site records are modified or retained. Cleanup verifies 0 leftover rows.

### C2 — `field:company_name` identity pattern
Autoname sets `name == company_name`. Renaming a `Company` via `frappe.rename_doc` updates
the document name and preserves `company_name_ar` and `company_name_ar_norm`. Empty
`company_name` fails autoname validation.

### C3 — Finding F1 dual-hook registration
Because `Company` carries narrative fields (`company_description`, `sales_monthly_history`),
`doc_events["Company"]` attaches both the bilingual policy hook and the narrative sanitizer hook,
conforming to the F1 specification.

---

## 3. Deliverables

1. `construction/patches/v9_14/add_company_arabic_fields.py` + `patches.txt` entry —
   adds `company_name_ar` (Data) and `company_name_ar_norm` (Data, read-only/hidden) after
   `company_name`, idempotent, with `revert()`; backfills `_norm` for existing non-empty Arabic.
2. Registry entry `"Company"` → `state: active`, `search.fields = ["company_name", "company_name_ar"]`.
3. `construction/hooks.py` `doc_events` dual-hook registration (C3).
4. `construction/tests/test_bilingual_company_pilot.py` — 8 tests: zero-service-edit guard,
   patch idempotence/reversibility, registry resolution, fail-closed on missing field,
   norm derivation + poison overwrite, BIDI rejection, identity invariant & rename
   preservation (C2), search across Alef/tatweel/diacritics.
5. P95 harness `evidence/scripts/measure_company_p95.py` + measurement JSON + log, two-tier SLA
   (governed ≤1.50 ms; Tier 2A ≥1.0 ms → ≤1.15×; Tier 2B <1.0 ms → ≤1.50×),
   **5 rounds × n=100 min-of-rounds**, ephemeral fixtures.
6. Matrix integration: module added to `scripts/run_bilingual_regression_matrix.sh`
   (18 modules, 217 tests) and all evidence pinned in `evidence/MANIFEST.json`.

---

## 4. Invariants

- **D1 / code diad**: `bilingual_service.py` and `search.py` stay byte-identical to all seven
  reference commits; **D5**: registry grows monotonically (additive `Company` entry only, 23 active masters).
- Narrative fields (`company_description`, `sales_monthly_history`) are strictly excluded from
  `search.fields`; search fields are exactly `["company_name", "company_name_ar"]`.
- All SQL parameterized; vendor repos untouched.

---

## 5. Out of scope

- Historical company renames or data backfills beyond Arabic custom fields.
- Wiring `SearchableDropdownEnhancer` / D4 remediation (deferred per `search-query-convention/SCOPE.md`).

---

## 6. Evidence causal order

```
final test run -> capture log (2>&1) -> git add -f the .log -> compute SHA-256 digests
-> MANIFEST.json -> commit
```

Verify digests against `git show HEAD:<path>` (or `:path` for the index), never `os.walk`.
`.gitignore:27` ignores `*.log`.

---

## 7. Results (2026-10-04, evidence pinned in `evidence/MANIFEST.json`)

| Check | Result |
|---|---|
| Pilot module `test_bilingual_company_pilot` | **8/8 OK** |
| Regression matrix `run_bilingual_regression_matrix.sh` | **217/217 across 18 modules** |
| ADR vs evidence reconciler | **19/19 PASS** |
| Invariant guard (D5 split) | code diad byte-identical to 7 refs; registry monotonic growth over 19 baseline masters; `test_transaction_link_search` **20/20** |
| Site migration | `v9_14` executed and recorded in `Patch Log`; all 23 registry masters resolve their `arabic_field` |
| P95 / two-tier SLA | baseline 0.531 ms, bilingual 0.781 ms, ratio **1.4708×** → Tier 2B (≤1.50×) and universal ceiling (≤1.50 ms) → `COMPLIANT_WITH_TWO_TIER_SLA` |
| Decision C1 (ephemeral fixtures) | verified — 12 created, 0 leftover |
| Decision C2 (identity invariant) | verified — `name == company_name`; autoname non-empty enforcement; rename preserved Arabic & norm |
| Decision C3 (F1 dual-hook) | verified — `doc_events["Company"]` registers both `enforce_bilingual_arabic_policy` and `narrative_sanitizer.validate_narrative_fields` |

**Cleanup:** zero `CT-COMP-*` fixtures remain (verified after run).

---

## 8. Amendments (post-completion)

### 8.1 Re-pin by bilingual-desk-link-dispatch (2026-10-04)

Digests are recorded as `amendments[]` entries in `evidence/MANIFEST.json`;
this work item's own evidence logs are unchanged.

| Artefact | Why it moved |
|---|---|
| `construction/hooks.py` | living file; Tier-4 `override_whitelisted_methods` binding added — `frappe.desk.search.search_link` → `construction.api.desk_link_search.search_link` (A1, `bilingual-desk-link-dispatch`) |
| `scripts/run_bilingual_regression_matrix.sh` | shared runner expanded to **19 modules / 234 tests** |
