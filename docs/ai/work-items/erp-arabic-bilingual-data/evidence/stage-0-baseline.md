# Stage 0 — Reproducible Baseline (2026-09-04)

Branch: `feature/erp-arabic-bilingual-data` (from `develop` @ `e7be48855bde540464ea302e53c9bfca62b7c462`)
Plan SHA-256: `f25cc5950dc8f675f7d54b5428d0efae9f67dfd5aa09c8c9e818f416f7cd2b2b` — MATCHES handoff.
Worktree: only `?? docs/ai/work-items/` + `?? docs/translation/ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md` (both belong to this work item).
TARGET_SITE: `v16.localhost` (test DB, no production data per site owner 2026-09-04; shares DB with `localhost`).

## PO catalogs (recomputed 2026-09-04, header msgid excluded)

| App | Total | Translated | Empty |
|---|---|---:|---:|
| Frappe `apps/frappe/frappe/locale/ar.po` (`cc353e76…`) | 5,902 | 2,943 | 2,959 |
| ERPNext `apps/erpnext/erpnext/locale/ar.po` (`2dfe0a5d…`) | 8,997 | 4,688 | 4,309 |
| Construction `construction/locale/ar.po` (`eb80514a…`) | 206 | 206 | 0 |

Handoff baseline was 5,902/2,905/2,997 + 8,997/4,655/4,342 + 207/207/0 — small drift (+38/+33 Frappe/ERPNext translated, Construction 206 vs 207) consistent with later commits, not a blocker.
No `.mo` files exist on disk (`find` over locale + assets + site dirs returns nothing) — v16 runtime resolves via `tabTranslation`/built JS cache, not file `.mo`. Screenshot-string MO check from handoff is N/A as stated; runtime proof must come from Arabic-session DOM evidence (deferred to Stage 1C, needs browser session).

## Translation health (`bench --site v16.localhost execute construction.translation_service.get_translation_health`, exit 0)

`loader_installed=true, using_safe_fallback=false, has_duplicates=false, has_null_digests=false, constraint_present=true (ct_translation_key_digest), has_drift=false, has_orphan_site_overrides=false`.

## Tests (all exit 0 except noted infra workaround)

- `test_translation_stabilization_gates`: 8/8 OK.
- `test_translation_catalog`: 3/3 OK (after `touch ./v16.localhost/.test_records.jsonl` to work around harness `FileNotFoundError`; infra issue, not code failure).
- `searchable_dropdown.tests.test_search_api`: 12/12 OK. `test_integration`: 6/6 OK.
- `schema_drift_checker.py`: EXIT 1 — `docs/ai/SCHEMA_FACTS.md` drift vs live DocType JSON (pre-existing; SCHEMA_FACTS last verified 2026-08-19). Recorded, not modified in Stage 0.
- `ai_context_check.py`: 39 pass / 1 fail (same SCHEMA_FACTS drift).
- `lint_scope_metadata.py`: PASS. `lint_translation_writes.py`: PASS.

## Live schema / data

- `tabAccount` columns: no `account_name_ar` — ABSENT confirmed.
- `Account where company=Elrefae`: 81 rows total (55 leaf). Matches pilot scope D4.
- Arabic in Elrefae account names: 0 (not re-queried; no writes occurred in Stage 0; carried from plan evidence).

## Search source/asset map

- ACTIVE (loaded via `hooks.py` `app_include_js`): `construction/public/js/searchable_dropdown/searchable_dropdown.js`, `.../utils.js`, `.../config/*.js`.
- LEGACY (not hook-loaded, still referenced by some imports/docs): `construction/searchable_dropdown/public/js/*.js`. No deletion in this work item without separate justification.
- ACTIVE API: `construction/searchable_dropdown/api/search.py::searchable_link_search`. JS configs request `account_name_ar` (absent column) — see Stage 1A.
- BUG CONFIRMED BY CODE INSPECTION: `search.py:95` filters `or_filters` by `has_field`, but `search.py:105` builds `fields=["name"]+search_fields` unfiltered → `frappe.get_list` raises on missing column, generic `except` returns `[]`. Regression test + fix in Stage 1A.

## Stage 0 gate

Evidence exists and is reproducible. No behavior changes made in Stage 0. Proceed to Stage 1A.
Deviations from canonical plan: none in Stage 0 (MO-file check N/A — no `.mo` artifacts in v16 checkout; will prove via runtime/DOM in Stage 1C).
