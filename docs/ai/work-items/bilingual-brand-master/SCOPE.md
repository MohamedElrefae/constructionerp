# Scope Descriptor — bilingual-brand-master

**Work item:** `bilingual-brand-master`
**Branch:** `develop`
**Status:** `COMPLETE` — patch v9_11 applied, registry `Brand` active, D5 guard split landed
**Base commit:** `48f370f` (D4 documented, sidecar route marked NOT WIRED)
**Date:** 2026-10-03
**Authority:** owner selection in session (Brand first of the three deferred ledgers);
D5 ratified by owner in session
**Scope:** patch `v9_11` (Arabic columns on `Brand`), registry onboarding to `active`,
invariant-guard split (D5), pilot test module, P95 measurement, matrix integration.

---

## 1. Field audit (read-only, `v16.localhost`, 2026-10-03)

| Property | Value |
|---|---|
| Registry entry | **ABSENT** |
| Rows | **2** (`_Test Brand`, `_Test Brand With Item Defaults`) |
| `autoname` | `field:brand` |
| `title_field` / `meta.search_fields` | none / none |
| Fields | `brand` (Data, reqd) · `image` (Attach Image, hidden) · `description` (Text) · `defaults` / `brand_defaults` (Table) |
| Index | PRIMARY on `name` only (no separate index on `brand`) |
| Arabic column | **absent** → patch required |
| Narrative tier | `description` → Tier 1 via `narrative_sanitizer.get_narrative_fields_for_doctype("Brand")` |

Consequences carried into design:

1. `field:brand` is the **8th** master with that autoname (precedents: `Payment Terms
   Template`, `Asset Category`, `UOM`, `Territory`, `Customer Group`, `Item Group`,
   `Supplier Group`, `Item`) — registry shape is copied from
   `Payment Terms Template` (`identity_field: name`, `english_field` = autoname field,
   `arabic_field` = `<field>_ar`, `norm_field` = `<field>_ar_norm`).
2. `description` is narrative and therefore **excluded from `search.fields`** by the
   established policy (narrative prose never enters registry search fields).
   Search fields are exactly `["brand", "brand_ar"]`.
3. 2 rows means no zero-row seed contract applies (`seed_required_targets()` unaffected);
   P95 can measure real data plus a fixture prefix.
4. Rows are ERPNext test fixtures (`_Test …`); measurement fixtures use their own prefix
   and are deleted after the run, like prior work items.

---

## 2. Decision D5 — invariant guard split (ratified 2026-10-03)

**Problem.** `test_transaction_link_search.py` byte-freezes all three triad files against
seven reference commits. `bilingual_registry.json` is *data that must grow* — it gained a
master in `7ef9737`, `0809fc2`, `f67133c`, `1f3f36e`, `03d6dba`, `d28dc98` and was frozen
at the 19-master state by `38beb35`. Onboarding `Brand` makes that assertion fail against
all seven refs. This is the first master onboarding since the guard was introduced
(`2e17df5`), so the rule had to be set before any work.

**Resolution — split the guard.**

| File | Rule after D5 |
|---|---|
| `construction/services/bilingual_service.py` | **byte-identical** to all 7 reference commits (unchanged) |
| `construction/searchable_dropdown/api/search.py` | **byte-identical** to all 7 reference commits (unchanged) |
| `construction/data/bilingual/bilingual_registry.json` | **monotonic growth** vs `38beb35`: no doctype removed; no key removed from a surviving entry; `search.fields` only ever a superset; `state` never regresses (`schema_installed` → `active` only); other values unchanged |

This preserves D1's intent — *zero service edits* — exactly as
`test_zero_service_edits_guard` (`test_bilingual_wave1_phase2_pilot.py:52`) has always
expressed it for the code diad, while replacing a freeze that every future master would
have to break with an assertion that catches regressions instead of blocking growth.

Rejected: re-baselining all three refs (silently drops the seven-commit freeze on the code
files) and dropping the registry from the guard entirely (loses automatic regression
protection).

---

## 3. Deliverables

1. `construction/patches/v9_11/add_brand_arabic_fields.py` + `patches.txt` entry —
   adds `brand_ar` (Data) and `brand_ar_norm` (Data, read-only/hidden) after `brand`,
   idempotent, with `revert()`; backfills `_norm` for existing non-empty Arabic.
   Pattern copied from `patches/v9_10/add_payment_terms_template_arabic_fields.py`.
2. Registry entry `"Brand"` → `state: active`, copied from the `Payment Terms Template`
   shape with `search.fields = ["brand", "brand_ar"]`.
3. Invariant guard split per D5 in `test_transaction_link_search.py`.
4. `construction/tests/test_bilingual_brand_pilot.py` — 8 tests mirroring the payment-terms
   pilot: zero-service-edit guard, patch idempotence/reversibility, registry resolution,
   fail-closed on missing field, norm derivation + poison overwrite, BIDI rejection,
   identity/rename preservation, search across Alef/tatweel/diacritics.
5. P95 harness `evidence/scripts/measure_brand_p95.py` + measurement JSON + log, applying
   the two-tier SLA (governed ≤1.50 ms; Tier 2A ≥1.0 ms → ≤1.15×; Tier 2B <1.0 ms → ≤1.50×),
   **5 rounds × n=100 min-of-rounds** (the governed methodology of
   `bilingual-boq-p95-measurement`, superseding the single-round n=50 of
   `bilingual-payment-terms-template-master`).
6. Matrix integration: module added to `scripts/run_bilingual_regression_matrix.sh`
   (14 modules, 181 tests) and all evidence pinned in `evidence/MANIFEST.json`.

### 3.1 Finding F1 — a new master needs three registrations, not two

First onboarding since the guard was introduced exposed that registry onboarding alone is
insufficient. `hooks.py` `doc_events` is a **per-doctype enumeration** of
`enforce_bilingual_arabic_policy` (plus `narrative_sanitizer.validate_narrative_fields`
where the master has a narrative field). Without it a master gets no server-side
norm-derivation on save and no BIDI rejection — the first pilot run failed 4/8 for exactly
this reason while registry mapping and patch tests passed. `Brand` is therefore registered
in `doc_events` alongside the other 20 masters.

Consequence: `construction/hooks.py` is digest-pinned by two closed work items
(`bilingual-boq-title-ar-wiring`, `bilingual-narrative-sanitizer`), so this change forces a
re-pin of both, recorded as amendments in their manifests and §8 notes in their SCOPEs.
`scripts/run_bilingual_regression_matrix.sh` and `construction/tests/test_transaction_link_search.py`
are likewise re-pinned (matrix expansion and D5 guard edit).

## 4. Invariants

- **D1 intent unchanged**: `bilingual_service.py` and `search.py` stay byte-identical to
  all seven reference commits; D5 touches only *how the registry is guarded*.
- Registry entry is additive; no existing master's entry, `unicode_policy`, `governance`
  or `schema` block is modified.
- `description` (narrative Tier 1) never enters `search.fields`.
- All SQL parameterized (AGENTS.md §4.1); `?v=` bumps for any modified JS (none expected).

## 5. Out of scope

- `Asset` and `Terms and Conditions` (sequenced after this work item).
- `Company` (GATED on statutory/legal/tax review).
- Wiring `SearchableDropdownEnhancer` / D4 remediation (deferred per
  `search-query-convention/SCOPE.md` §3).
- Any change to identity-field policy or to the narrative sanitizer.

## 6. Evidence causal order

```
final test run -> capture log (2>&1) -> git add -f the .log -> compute SHA-256 digests
-> MANIFEST.json -> commit
```

Verify digests against `git show HEAD:<path>`, never `os.walk`. `.gitignore:27` ignores
`*.log`.

## 7. Results (2026-10-03, evidence pinned in `evidence/MANIFEST.json`)

| Check | Result |
|---|---|
| Pilot module `test_bilingual_brand_pilot` | **8/8 OK** |
| Regression matrix `run_bilingual_regression_matrix.sh` | **181/181 across 14 modules** |
| ADR vs evidence reconciler | **19/19 PASS** |
| Invariant guard (D5 split) | code diad byte-identical to 7 refs; registry monotonic growth over 19 baseline masters; `test_transaction_link_search` **20/20** |
| Site migration | `v9_11` executed and recorded in `Patch Log`; all 20 registry masters resolve their `arabic_field` |
| P95 / two-tier SLA | baseline 0.458 ms, bilingual 0.665 ms, ratio **1.452×** → Tier 2B (≤1.50×) and universal ceiling (≤1.50 ms) → `COMPLIANT_WITH_TWO_TIER_SLA` |

Latency disclosure: the confirmation series in `evidence/brand-p95-confirm.log` records five
sequential runs — 1.4354, 1.3297, 1.4528, 1.4758, 1.4520 — all compliant. A preliminary run
(`evidence/brand-p95-run.log`) returned **1.5066**, i.e. 0.44 % above the Tier 2B band, with
bilingual P95 0.684 ms still under the universal ceiling; it is retained as evidence rather
than discarded. Confirmation run 5 aborted on its first attempt with
`QueueOverloaded: Too many queued background jobs (600)` (the harness's insert/delete cycles
enqueue `delete_dynamic_links`); the queue was flushed and the retry succeeded — the failure
and the retry are both in the confirmation log. Match-set equivalence and zero leftover
fixtures held on every successful run.

**Cleanup:** `_Test Brand.brand_ar` / `brand_ar_norm` restored to NULL and no `CT-BRAND-`
or `Brand <hex>` fixtures remain (both verified after the final run).


## 8. Amendments (post-completion)

Digests are recorded as `amendments[]` entries in `evidence/MANIFEST.json`;
this work item's own evidence logs are unchanged.

| Artefact | Why it moved |
|---|---|
| `construction/data/bilingual/bilingual_registry.json` | living data; additive `Asset` entry (**22 masters**) by `bilingual-asset-master` |
| `construction/patches.txt` | living file; `v9_13` entry appended by `bilingual-asset-master` |
| `construction/hooks.py` | living file; `Asset` `doc_events` single-hook registration added |
| `scripts/run_bilingual_regression_matrix.sh` | shared runner expanded to **16 modules / 197 tests** |

### 8.1 Re-pin by canonical matrix integration (2026-10-04)

| Artefact | Why it moved |
|---|---|
| `scripts/run_bilingual_regression_matrix.sh` | shared runner expanded to **17 modules / 209 tests** (`test_boq_link_queries` promoted into the runner) |

### 8.2 Re-pin by bilingual-company-master (2026-10-04)

| Artefact | Why it moved |
|---|---|
| `construction/data/bilingual/bilingual_registry.json` | living data; additive `Company` entry (**23 masters**) by `bilingual-company-master` |
| `construction/patches.txt` | living file; `v9_14` entry appended by `bilingual-company-master` |
| `construction/hooks.py` | living file; `Company` `doc_events` dual-hook registration added (F1) |
| `scripts/run_bilingual_regression_matrix.sh` | shared runner expanded to **18 modules / 217 tests** |

