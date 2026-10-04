# Scope Descriptor — bilingual-asset-master

**Work item:** `bilingual-asset-master`
**Branch:** `develop`
**Status:** `COMPLETE` — patch v9_13 applied, registry `Asset` active, 16-module matrix
**Base commit:** `cc3a105` (Terms and Conditions master onboarding complete)
**Date:** 2026-10-04
**Authority:** owner directive in session (Asset third of the deferred ledgers queue;
decisions A1–A3 approved in session)
**Scope:** patch `v9_13` (Arabic columns on `Asset`), registry onboarding to `active`,
F1 single-hook registration, pilot test module, P95 measurement, matrix integration.

---

## 1. Field audit (read-only, `v16.localhost`, 2026-10-04)

| Property | Value |
|---|---|
| Registry entry | **ABSENT** |
| Rows | **0** (empty table) |
| `autoname` | `naming_series:` (series `ACC-ASS-.YYYY.-`) |
| `title_field` / `meta.search_fields` | none / none |
| Flags | `is_submittable = 1`, `track_changes = 1` |
| Required fields | `item_code` (Link→Item) · `asset_name` (Data) · `location` (Link→Location) · `company` (Link→Company) |
| Other fields | `naming_series` (Select) · `item_name` (Read Only, hidden) · `image` · `asset_category` · `asset_type` · `maintenance_required` · `calculate_depreciation` · `purchase_receipt` · `purchase_invoice` · … |
| Arabic column | **absent** → patch required |
| Narrative tier | **none** — `narrative_sanitizer.get_narrative_fields_for_doctype("Asset")` → `{}` |
| Dependencies on site | Company 21 (`_Test Company`, `Elrefae`) · Item 43 · Location 7 · Asset Category 2 (`Computers`, `Equipment`) |

Consequences carried into design:

1. `naming_series:` autoname means `name` is **never** the English value — the identity
   invariant must be asserted the `Employee` way (precedent: `Employee`, also
   `naming_series:`, registered with `english_field: employee_name`,
   `identity_field: name`). Registry shape: `english_field: asset_name`,
   `arabic_field: asset_name_ar`, `norm_field: asset_name_ar_norm`.
2. Every fixture needs three required Link references, all of which already exist on the
   site — no seed fixture is required (decision **A1**).
3. `is_submittable = 1` makes teardown the only real hazard: cancelling a submitted Asset
   can touch depreciation schedules. Fixtures stay **draft** (decision **A1**), and frappe's
   link search filters `docstatus < 2`, so drafts exercise the production query path.
4. No narrative field → F1 applies in **single-hook** form only (decision **A3**), matching
   `Asset Category`, `Department`, `Warehouse`, `Cost Center`.
5. Measurement fixtures use prefix `CT-ASSET-` and are deleted after the run; the table's
   0 rows therefore do not block P95 — the harness never measures pre-existing data.

---

## 2. Decisions (approved 2026-10-04)

### A1 — Option A: harness-local draft fixtures (no seed)

| Option | Verdict |
|---|---|
| **A. Harness-local ephemeral fixtures** (Brand/T&C pattern) referencing existing site records, `docstatus=0`, deleted on cleanup | **approved** |
| B. Committed seed patch creating canonical Assets | rejected — no precedent, pollutes every site, needs a revert path |
| C. Ship `schema_installed` only, defer P95 | rejected — no measurement evidence, leaves the queue item half-done |

Fixture creation asserts its dependencies exist and raises `unittest.SkipTest` if not, so a
bare site degrades to a skip rather than a failure. Cleanup is `force=True` delete on draft
documents: no cancel step, no depreciation/ledger side effects.

### A2 — `naming_series` identity pattern

Copied from the `Employee` pilot: `name` is the generated serial
(`ACC-ASS-2026-00001`), `identity_field: name`, `english_field: asset_name`; the identity
test asserts that (a) `name` differs from `asset_name`, (b) renaming preserves
`asset_name_ar` and `asset_name_ar_norm`, (c) `asset_name` itself is untouched by rename.

### A3 — F1 in single-hook form

`doc_events["Asset"]` registers `enforce_bilingual_arabic_policy` **only** — there is no
narrative field on `Asset`, so `narrative_sanitizer.validate_narrative_fields` is not
attached (the sanitizer reports `{}` for this doctype).

---

## 3. Deliverables

1. `construction/patches/v9_13/add_asset_arabic_fields.py` + `patches.txt` entry —
   adds `asset_name_ar` (Data) and `asset_name_ar_norm` (Data, read-only/hidden) after
   `asset_name`, idempotent, with `revert()`; backfills `_norm` for existing non-empty Arabic.
2. Registry entry `"Asset"` → `state: active`, `search.fields = ["asset_name", "asset_name_ar"]`.
3. `construction/hooks.py` `doc_events` single-hook registration (A3).
4. `construction/tests/test_bilingual_asset_pilot.py` — 8 tests: zero-service-edit guard,
   patch idempotence/reversibility, registry resolution, fail-closed on missing field,
   norm derivation + poison overwrite, BIDI rejection, naming_series identity/rename
   preservation (A2), search across Alef/tatweel/diacritics.
5. P95 harness `evidence/scripts/measure_asset_p95.py` + measurement JSON + log, two-tier SLA
   (governed ≤1.50 ms; Tier 2A ≥1.0 ms → ≤1.15×; Tier 2B <1.0 ms → ≤1.50×),
   **5 rounds × n=100 min-of-rounds**, draft fixtures.
6. Matrix integration: module added to `scripts/run_bilingual_regression_matrix.sh`
   (16 modules, 197 tests) and all evidence pinned in `evidence/MANIFEST.json`.

## 4. Invariants

- **D1 / code diad**: `bilingual_service.py` and `search.py` stay byte-identical to all seven
  reference commits; **D5**: registry grows monotonically (additive `Asset` entry only).
- `Asset` has no narrative field, so no narrative field enters `search.fields`; search fields
  are exactly `["asset_name", "asset_name_ar"]`.
- All SQL parameterized; vendor repos untouched; `?v=` bumps only if JS changes (none planned).

## 5. Out of scope

- `Company` (GATED on statutory/legal/tax review) — the last deferred ledger item.
- Depreciation/finance behaviour of fixtures: they are never submitted or cancelled.
- Wiring `SearchableDropdownEnhancer` / D4 remediation (deferred per
  `search-query-convention/SCOPE.md`).

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
| Pilot module `test_bilingual_asset_pilot` | **8/8 OK** |
| Regression matrix `run_bilingual_regression_matrix.sh` | **197/197 across 16 modules** |
| ADR vs evidence reconciler | **19/19 PASS** |
| Invariant guard (D5 split) | code diad byte-identical to 7 refs; registry monotonic growth over 19 baseline masters; `test_transaction_link_search` **20/20** |
| Site migration | `v9_13` executed and recorded in `Patch Log`; all 22 registry masters resolve their `arabic_field` |
| P95 / two-tier SLA | baseline 0.499 ms, bilingual 0.688 ms, ratio **1.3788×** → Tier 2B (≤1.50×) and universal ceiling (≤1.50 ms) → `COMPLIANT_WITH_TWO_TIER_SLA` |
| Decision A1 (draft fixtures) | verified — every fixture asserted `docstatus == 0`; no submit/cancel anywhere; zero leftover Assets **and** zero `Asset Activity` rows after every run |
| Decision A2 (`naming_series` identity) | verified — `ACC-ASS-2026-#####` ≠ `asset_name` (incl. the auto-derived-`asset_name` case); rename preserved `asset_name`, `asset_name_ar`, `asset_name_ar_norm` |
| Decision A3 (F1 single-hook) | verified — `doc_events["Asset"]` registers `enforce_bilingual_arabic_policy` only; the sanitizer reports `{}` for `Asset` so no narrative hook is attached |

Latency disclosure: preliminary run `evidence/asset-p95-run.log` returned **1.4172**;
confirmation series `evidence/asset-p95-confirm.log` recorded **1.4859, 1.3571, 1.3788** —
all four runs compliant, all with match-set equality and zero leftovers. The authoritative
`asset-p95-measurement.json` is the final confirmation run (1.3788) and carries all five
per-round P95 values for each side.

**Implementation notes (worth carrying forward):**
- An Asset fixture needs `purchase_date` and `net_purchase_amount` in addition to the three
  required Links, and `asset_type: "Existing Asset"` (ERPNext's own `test_asset.create_asset`
  recipe) to short-circuit the CWIP purchase-document rule and the net-vs-purchase amount
  comparison. `asset_category` is read-only and derives from the Item, so the fixture prefers
  an Item that carries one.
- `asset_name` is auto-derived from the Item when left blank (server-side), so the identity
  invariant is asserted as "`name` never equals `asset_name`" rather than as a mandatory-field
  rejection.
- Deleting an Asset also deletes its `Asset Activity` audit rows explicitly, since frappe only
  removes dynamic links through a queued job (`delete_dynamic_links`) — the same mechanism that
  produced the `QueueOverloaded` incident disclosed in `bilingual-brand-master`.

**Cleanup:** no `CT-ASSET-` or `ACC-ASS-*` fixtures remain and `Asset Activity` is back to 0
rows (both verified after the final run).

---

## 8. Amendments (post-completion)

| Artefact | Why it moved |
|---|---|
| `scripts/run_bilingual_regression_matrix.sh` | shared runner expanded to **17 modules / 209 tests** after this work item completed (`test_boq_link_queries` promoted into the runner by `bilingual-boq-title-ar-wiring` §8.3). §7's **197/197 across 16 modules** remains the correct historical result for this work item's own completion run. |

### 8.1 Re-pin by bilingual-company-master (2026-10-04)

Digests are recorded as `amendments[]` entries in `evidence/MANIFEST.json`;
this work item's own evidence logs are unchanged.

| Artefact | Why it moved |
|---|---|
| `construction/data/bilingual/bilingual_registry.json` | living data; additive `Company` entry (**23 masters**) by `bilingual-company-master` |
| `construction/patches.txt` | living file; `v9_14` entry appended by `bilingual-company-master` |
| `construction/hooks.py` | living file; `Company` `doc_events` dual-hook registration added (F1) |
| `scripts/run_bilingual_regression_matrix.sh` | shared runner expanded to **18 modules / 217 tests** |

