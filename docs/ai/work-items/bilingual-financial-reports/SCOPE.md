# Scope Descriptor — bilingual-financial-reports

**Work item:** `bilingual-financial-reports`
**Branch:** `develop`
**Base commit:** `dd4ea6d`
**Date:** 2026-10-04
**Status:** `COMPLETE` — governance + defect closure + evidence pipeline for the existing bilingual report surface (results in §8)
**Authority:** Plan Tier 5A (financial report wrappers), owner go-ahead in session to establish
this work item after `bilingual-desk-link-dispatch` (`dd4ea6d`) completed the software surface
**Scope:** Formalize the already-shipped bilingual report rendering (Arabic / English / Both for
General Ledger, Trial Balance, Accounts Receivable, with service support for Balance Sheet and
Profit & Loss) under the standard work-item governance: fix the double-execute defect, prove
authorization genuinely, join the canonical matrix, and pin a full evidence manifest — with
zero edits to `apps/frappe` / `apps/erpnext` and zero data mutation.

---

## 1. The gap this closes

The bilingual report surface **exists and works** but is ungoverned:

- `construction/services/report_bilingual_extension.py` (Stage 4 spike, `0d96cdc`/`ef292b7`) —
  pure post-processing of vendor report `execute()` output; 11 tests.
- `construction/api/bilingual_reports.py` (Stage 7 pilot, `0834016`/`0ca6c59`/`80787af`) —
  whitelisted `localized_report`, fail-closed allowlist, role gate; 9 tests.
- Desk page `bilingual-report-viewer` (`construction/construction/page/bilingual_report_viewer/`)
  renders the endpoint's output as an escaped HTML table.

What is missing after nine bilingual work items of precedent:

1. No `SCOPE.md`, no `evidence/MANIFEST.json`, no causal-order capture for this surface.
2. Both test modules (20 tests) are **outside the canonical matrix** (`run_bilingual_regression_matrix.sh`,
   19 modules / 234 tests at probe time) — a regression here would go unnoticed by the same gate that
   protects every other bilingual surface.
3. A live defect: the endpoint executes the vendor report **twice per request**.
4. Authorization is **mocked in every test** (`frappe.only_for` is patched), so the role gate has
   never been exercised genuinely (AGENTS.md §4.7 requires a non-admin proof).

Prior evidence lives only as historical build records:
`erp-arabic-bilingual-data/evidence/stage-4-report-extension-spike.md` (11/11 at `e7be488`),
`scope-context-portability/evidence/stage7-report-pilot-build-2026-09-21.md`, and
`erp-arabic-bilingual-data/evidence/stage8-production-ai-r-verify-0c8057f.md`.

## 2. Verified current state (probed 2026-10-04, base `dd4ea6d`)

| Fact | Value |
|---|---|
| `test_stage4_report_extension` | **11/11 OK** |
| `test_stage7_bilingual_reports` | **9/9 OK** |
| Live Trial Balance, mode `ar` | swaps on real output: `1110 - Cash - E` → `النقدية`, `1310 - Debtors - E` → `المدينون` |
| Arabic account data on site | 81 of 2,102 accounts have `account_name_ar`; Elrefae mapping = 162 entries (keyed by `account_name` and `name`) |
| GL entries on site | 4 (non-empty; the 2026-09-21 "no GL transactions" note is stale) |
| Endpoint | `@frappe.whitelist()`, `frappe.only_for(("Accounts User","Accounts Manager","System Manager"))`, unknown report → `ValidationError`, malformed/non-object filters → `ValidationError` |
| Viewer | calls `construction.api.bilingual_reports.localized_report` with JSON filters; renders with `escape_html`; stale-response guard (`run_seq`) |
| Manifest pins on report files | none — free to edit without hidden re-pins |

**Defect D5A-1 (in scope, R1):** `construction/api/bilingual_reports.py:68-69` executes the
vendor `execute(filters=...)` **twice** — duplicated line. Every API call pays 2× report cost;
`test_object_filters_accepted` asserts `call_count >= 1`, so the defect passes today.

**Defect D5A-2 (in scope, R2):** every authorization assertion mocks `frappe.only_for`; no test
ever proves a real user without Accounts roles is rejected.

**Defect D5A-3 (found during R2/R7 work, in scope, R2b):** the stage7 mode tests patched
`mock.patch.object(report_bilingual_extension, "load_account_arabic_mapping", ...)` — but the API
binds that name into its own module globals at import, so the patch never reached the endpoint
(probe: `patch intercepted API name: False`). The tests passed only by import-order luck (the API
module was first imported inside the first patch context, and later tests reused an identical
mock return value). Any earlier import of the API module in the matrix would have broken them.

## 3. Decisions

### R1 — the vendor report executes exactly once per request

Remove the duplicated `execute(...)` call so the endpoint runs
`execute → transform → return` once. Regression guard: tighten
`test_stage7_bilingual_reports.test_object_filters_accepted` from
`assertGreaterEqual(call_count, 1)` to `assertEqual(call_count, 1)` — the existing Mock then
fails on any reintroduced double execution.

### R2 — genuine non-admin authorization proof (AGENTS.md §4.7)

Add a test that creates a real user with **no Accounts roles** (`roles: []`,
`send_welcome_email: 0`), switches to it, and asserts `localized_report` on an allowlisted
report raises `PermissionError` from `frappe.only_for` **before** any vendor `execute` runs
(spy proves zero calls), then restores Administrator and asserts the same call succeeds as an
admin control. Existing tests keep their `only_for` mocks (they test other contracts and
should not become user-management heavy).

### R3 — canonical matrix integration

Add both modules to `scripts/run_bilingual_regression_matrix.sh`:

- `construction.tests.test_stage4_report_extension` (14 tests after R5/R7)
- `construction.tests.test_stage7_bilingual_reports` (10 tests after R2)

Header moves to **21 modules / 258 tests**. This re-opens the established re-pin obligation for
every manifest pinning the runner (7 manifests) and, via R7, every manifest pinning
`construction/hooks.py` (7 manifests) — union of 8 manifests re-pinned in §8.

### R4 — evidence pipeline (causal order, standard)

final test runs → capture logs (`2>&1`) → `git add -f` → SHA-256 digests → `MANIFEST.json` →
commit. Artefacts: both pilot logs, a reproducible live-execution probe (GL/TB/AR Aging
read-only runs + the ar-mode swap proof), the 21-module matrix log, the reconciler log, the P95
run + confirmation + measurement JSON, and the harness scripts.

### R5 — report latency: Two-Tier **ratio** limbs, absolute ceiling disclosed not enforced

Reports are measured with the established harness discipline (5 rounds × n interleaved,
alternating order, 5 warmups/round, GC paused in the timed region, min-of-rounds nearest-rank
P95) over four cases — Trial Balance and General Ledger, each as *stock baseline*
(`module.execute(filters)` with fully-specified filters) vs *bilingual endpoint*
(`localized_report(..., mode="ar")` with the same filters as JSON).

- **Acceptance = ratio only:** baseline for reports is inherently ≫ 1 ms, so the tier is always
  2A ⇒ **≤ 1.15×**. The 1.50 ms **absolute** ceiling of the search-path SLA
  (`bilingual-performance-sla.md`) is defined for interactive search and does not apply here;
  absolute P95 values are still recorded and disclosed.
- Optimization is allowed **only after** a non-compliant measurement is disclosed, in this order:
  skip fiscal-year bound resolution when the caller already supplied date bounds; slim the
  mapping query to rows that actually carry `account_name_ar`; then the owner-selected cache
  (R7). Each step is re-measured; every run (pre- and post-fix) is disclosed like Tier 4 did.
- No run may be discarded.
- Lever outcomes: lever (a) run1→run2 (GL 1.4402× → 1.2805×), lever (b) run2→run3
  (GL 1.2805× → 1.2864×, within baseline drift; it removed the ~1 ms `get_all` but the fixed
  endpoint overhead still dominated the 4-entry GL baseline), simulated cache predicted
  1.0554×, R7 measured run4/run5 GL 1.0296×/1.0585×. Runs 1–5 in §8.

### R7 — mapping cache (owner-approved Option A, replaces the memoize lever)

The endpoint loaded the Arabic-name mapping from MariaDB on every render (measured ~0.6–1.4 ms
P95), which kept General Ledger at 1.28× against the ≤1.15× limb. With the owner's explicit
approval (session choice: "Redis cache + hook bust"), `load_account_arabic_mapping` now:

- serves from `frappe.cache`, one key per company plus the global key
  (`construction:account_ar_mapping:{company|*}`), TTL 300 s;
- busts those keys through new `Account` doc_events (`on_update`, `on_trash`, `after_rename` →
  `bust_account_mapping_cache`) in `construction/hooks.py` — normal saves/renames/deletes are
  reflected immediately; the TTL only covers writes that bypass doc_events (e.g.
  `frappe.db.set_value`, direct SQL), disclosed in §8;
- fails open to the parameterized SQL path on any redis error.

The D5 triad stays untouched: the pre-existing `Account` `validate` hook
(`enforce_account_arabic_policy`) is left exactly as-is; only new event keys were added.
Steady-state (warm) behavior is what the harness measures after warmups — production renders on
warm workers; a cold worker's first render pays the SQL load (disclosed).

### R2b — the stage7 mode tests patch the API's own binding

Per D5A-3, the three mode tests now `mock.patch.object(construction.api.bilingual_reports, ...)`
instead of the service module attribute, so interception is deterministic regardless of import
order. The `ar`/`both` assertions (`Rent` → `إيجار`) can only pass when the mock is genuinely
intercepted — the real mapping contains no `Rent` key (verified: `real mapping has 'Rent': None`).

### R6 — read-only vendor boundary and pure transform

The wrapper continues to treat vendor `execute()` as a read-only function: only the returned
`columns`/`data` are localized into **new structures** (`transform_report` purity is already
unit-tested: sources not mutated). No Report DocType, no vendor file edit, no Account or
translation write, no schema change, no patch.

## 4. Invariants preserved

- **Vendor boundary:** zero files under `apps/frappe` / `apps/erpnext` change (only
  `construction/`-owned code and docs).
- **D5 triad / registry:** `bilingual_service.py`, `searchable_dropdown/api/search.py`,
  `bilingual_registry.json`, `bilingual_registry.py` untouched (this item consumes none of them).
- **Fail-closed allowlist:** `PILOT_REPORTS` stays exactly GL / Trial Balance / Accounts
  Receivable; Balance Sheet and Profit & Loss remain service-supported but endpoint-rejected —
  widening the allowlist is a separate owner decision.
- **No data mutation:** the endpoint and the harness are read-only; no fixtures are created, so
  cleanup is structurally zero (asserted in the probe and every P95 run: Account/GL counts
  unchanged). The one exception is stage4's R7 round-trip, which uses the governed edit
  (`set_account_name_ar`, the only admitted writer path) and restores `account_name_ar` —
  net-zero data change, disclosed in the module docstring.
- **Authorization:** role gate genuine (R2), never weakened or mocked in the new test.
- **No JS changes:** the viewer is untouched ⇒ no `?v=` bump (AGENTS.md §4.4). Residual viewer
  issues are disclosed in §6, not silently fixed.

## 5. Tests

`test_stage4_report_extension` — **14 tests** (11 existing + 3):

- pure transform matrix (en/ar/both, unknown-label identity, source purity, columnar rows,
  label-field config); read-only GL/TB integration runs; rollback note.
- mapping equivalence guard, now with an explicit cache bust so the SQL path is exercised.
- **new:** cache hit serves an identical mapping and populates the key (R7).
- **new:** `Account` doc_events registration + governed-edit round-trip proving save → bust →
  fresh mapping → restore (R7, net-zero).

`test_stage7_bilingual_reports` — **10 tests** (9 existing + R2):

- fail-closed unknown report; malformed / non-object JSON and native filters rejected;
  object filters accepted with **`execute.call_count == 1`** (R1 guard).
- ar / both / en mode localization through the endpoint with a stub vendor module — mocks
  now patch the API namespace (R2b).
- real-module smoke: every `PILOT_REPORTS` path imports and exposes callable `execute`.
- **new:** genuine non-admin `PermissionError` + zero vendor executions + admin control (R2).

Evidence gates (as in every prior item): both pilot logs, probe PASS, matrix 21/258,
reconciler 19/19, digest verification over all manifests, lints (`lint_scope_metadata`,
`ai_context_check`, `lint_translation_writes`), `py_compile`, `bash -n`.

## 6. Out of scope

- **Tier 5B** — production Arabic data population (the 81 populated accounts are test-site
  content; live-population evidence stays in `erp-arabic-bilingual-data`).
- **BOQ print/export surface** and any print-format work (tracked separately since Stage 7).
- **Widening the allowlist** to Balance Sheet / Profit & Loss (service supports them; endpoint
  stays fail-closed until the owner expands the pilot).
- **Viewer JS changes:** disclosed residuals — unused `__seq` variable
  (`bilingual_report_viewer.js:61`), AR-specific filter keys sent for every report type, and no
  automated JS test coverage for the page. Untouched ⇒ no cache-buster churn.
- **Account-level Arabic naming work** (`account_name_ar` population/mapping quality) — Tier 1–3
  territory, already governed elsewhere.
- `bilingualize_report` legacy wrapper: retained as the Stage-4 public API and covered by its
  existing tests; not modified by R1 (the defect is in the API module, not the service).

## 7. Evidence causal order

final test run → capture log (`2>&1`) → `git add -f` the `.log` → compute SHA-256 digests →
`evidence/MANIFEST.json` → commit. Verify against `git show HEAD:<path>` (or `:path` for the
staged index), never via `os.walk`.

## 8. Results (2026-10-04, base `dd4ea6d`, COMPLETE)

### 8.1 Defect closure and code changes

| Ref | Change | File |
|---|---|---|
| R1 | removed the duplicated `execute(...)`; guard tightened to `execute.call_count == 1` | `construction/api/bilingual_reports.py`, stage7 test |
| R2 | genuine non-admin `PermissionError` + zero vendor executions + admin control | stage7 test (`TestGenuineAuthorization`) |
| R2b | mode-test mocks patch the API's own binding (D5A-3 closure) | stage7 test |
| R5 (a) | General Ledger FY bounds resolved only when dates are missing (dead `_resolve_fy` removed) | `construction/api/bilingual_reports.py` |
| R5 (b) | mapping loaded by parameterized SQL over Arabic-bearing rows (dead `_raw_map` removed) | `construction/services/report_bilingual_extension.py` |
| R7 | per-company redis mapping cache (TTL 300 s), fail-open to SQL; `Account` `on_update`/`on_trash`/`after_rename` bust — triad `validate` hook untouched | `report_bilingual_extension.py`, `construction/hooks.py` |
| R3 | matrix runner expanded to 21 modules / 258 tests | `scripts/run_bilingual_regression_matrix.sh` |

D5 triad, `bilingual_registry.json`, viewer JS, vendor trees: byte-identical, untouched.
No `?v=` bump (AGENTS.md §4.4 — no JS modified).

### 8.2 Evidence gates

| Gate | Result | Artefact |
|---|---|---|
| stage4 tests | **14/14 OK** | `evidence/stage4-report-extension.log` |
| stage7 tests | **10/10 OK** | `evidence/stage7-bilingual-reports.log` |
| live probe (GL/TB/AR read-only + ar swap + mutation guard) | **PASS** (TB `1110 - Cash - E` → `النقدية`, `1310 - Debtors - E` → `المدينون`; Account 2,102 / GL 4 unchanged) | `evidence/probe-report-execution.log` |
| canonical matrix | **21 modules / 258 tests, all OK** | `evidence/regression-matrix.log` |
| ADR↔evidence reconciler | **19/19 PASS** | `evidence/reconciliation.log` |
| P95 harness | runs 4–5 compliant (§8.3) | `evidence/report-p95-run{,2,3,4,5}.log`, `report-p95-measurement.json` |
| manifest digests | all 21 manifests verify after the 8 re-pins (§8.4) + this item's manifest | `evidence/MANIFEST.json` |
| pre-commit lints | `lint_scope_metadata`, `ai_context_check`, `lint_translation_writes`, `py_compile`, `bash -n` | pass |

### 8.3 Latency disclosure — all five runs, none discarded

Method (R5): `evidence/scripts/measure_report_p95.py` — 5 rounds × n=100 interleaved,
alternating order, 5 warmups/round, GC paused in the timed region, min-of-rounds nearest-rank
P95; acceptance = ratio limbs only (Tier 2A ≤ 1.15×), absolute P95 disclosed.

| Run | Lever state | GL baseline → bilingual (ms) | GL ratio | TB baseline → bilingual (ms) | TB ratio | Verdict |
|---|---|---|---|---|---|---|
| 1 `report-p95-run.log` | pre R5 (a) | 4.253 → 6.125 | **1.4402×** ✗ | 31.195 → 31.816 | 1.0199× ✓ | disclosed non-compliant |
| 2 `report-p95-run2.log` | post R5 (a) | 4.649 → 5.953 | **1.2805×** ✗ | 31.069 → 32.525 | 1.0469× ✓ | disclosed non-compliant |
| 3 `report-p95-run3.log` | post R5 (b) | 4.878 → 6.275 | **1.2864×** ✗ | 35.822 → 38.023 | 1.0614× ✓ | disclosed non-compliant (baseline drift) |
| 4 `report-p95-run4.log` | post R7 cache | 4.329 → 4.457 | 1.0296× ✓ | 31.154 → 31.600 | 1.0143× ✓ | **COMPLIANT** |
| 5 `report-p95-run5.log` | post R7 cache (confirmation) | 4.203 → 4.449 | 1.0585× ✓ | 31.119 → 31.441 | 1.0103× ✓ | **COMPLIANT** |

Structural contract (row/column parity) and mutation guard PASS in every run.
Root cause of runs 1–3: fixed endpoint overhead (~0.8–1.4 ms, dominated by the pre-R7 mapping
load and in-process glue) against a pathologically small 4-entry GL baseline; a simulated cache
predicted 1.0554×, R7 measured 1.0296×/1.0585×.

**Steady-state cache disclosure (R7):** ratios measure warm-cache steady state (first render per
worker/TTL expiry pays the SQL mapping load). Normal Account saves bust immediately via
doc_events; writes that bypass doc_events (`frappe.db.set_value`, direct SQL) may serve stale
labels for up to 300 s (TTL). Cache contents are derived data, recreatable by one read-only
query; no financial values are cached.

### 8.4 Re-pins performed by this work item

Changed living files: `construction/hooks.py` (7 pinning manifests) and
`scripts/run_bilingual_regression_matrix.sh` (7 pinning manifests); union re-pinned with
`amendments[]` entries + an §8 amendment note in each SCOPE:

`bilingual-asset-master`, `bilingual-boq-title-ar-wiring`, `bilingual-brand-master`,
`bilingual-company-master`, `bilingual-desk-link-dispatch`, `bilingual-narrative-sanitizer`,
`bilingual-terms-conditions-master`, `transactional-link-resolution` — **8 manifests**.
