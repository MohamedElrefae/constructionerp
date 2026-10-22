# Scope Descriptor — bilingual-report-statements-allowlist

**Work item:** `bilingual-report-statements-allowlist`
**Branch:** `develop`
**Base commit:** `890ae14`
**Date:** 2026-10-05
**Status:** `COMPLETE` — `Balance Sheet` + `Profit and Loss Statement` added to the fail-closed
bilingual report allowlist end to end (API + viewer + period defaults) under the unchanged
Tier-5A contract (results in §8)
**Authority:** Plan Tier 5E — owner's in-session choice after Tier 5D (`890ae14`) closed the
wave-2 taxonomy ("5E: BS/P&L report allowlist (Recommended)" selected 2026-10-05)
**Scope:** Add `Balance Sheet` and `Profit and Loss Statement` to the `localized_report`
fail-closed allowlist (`construction/api/bilingual_reports.py`), supply their read-only
vendor-required period defaults, expose both in the `bilingual-report-viewer` page, and prove
the full Tier-5A contract (single execute, genuine authorization, fail-closed rejection,
matrix integration) still holds — with zero edits to `apps/frappe` / `apps/erpnext`, zero data
mutation, and exactly one disclosed manifest re-pin.

---

## 1. The gap this closes

Tier 5A (`bilingual-financial-reports`, `7839e67`) governed the report surface and its SCOPE
already records that the **service layer supports Balance Sheet and Profit & Loss**
(`REPORT_LABEL_FIELDS` carries both label-field entries since the Stage-4 spike) — but the
**endpoint allowlist never grew**:

- `PILOT_REPORTS` still holds exactly three names (General Ledger, Trial Balance, Accounts
  Receivable); `localized_report` therefore **fail-closed rejects** both statements ("Unsupported
  report") — the R1 fail-closed design working as intended, just with an incomplete list.
- The viewer page's report Select hardcodes the same three names
  (`bilingual_report_viewer.js:8`).
- `_ensure_required` supplies fiscal/date defaults only for the pilot trio; the statements need
  their own period defaults (`filter_based_on` / `periodicity` / period dates) or vendor
  `get_period_list` fails.
- Desk-level scope enforcement already covers both names
  (`overrides/report_guard.py` `FINANCIAL_REPORTS`), and the Stage-4 extension tests already
  assert the label-field entries (`test_stage4_report_extension.py:65,163`) — only the API +
  viewer + defaults gap remains.

This item closes exactly that gap: **two names, three files, one re-pin.**

## 2. Verified current state (probed 2026-10-05, base `890ae14`)

| Fact | Value |
|---|---|
| `PILOT_REPORTS` | 3 entries: General Ledger, Trial Balance, Accounts Receivable — both statements absent |
| Vendor module paths | `erpnext.accounts.report.balance_sheet.balance_sheet` (returns 6-tuple `columns, data, message, chart, report_summary, primitive_summary`), `erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement` (returns 6-tuple with `None` message) — both readable, never edited |
| Vendor filter contract | both call `get_period_list(from_fiscal_year, to_fiscal_year, period_start_date, period_end_date, filter_based_on, periodicity, company=…)`; `periodicity` must be a key of `{Yearly, Half-Yearly, Quarterly, Monthly}`; `Date Range` mode needs `period_start_date`/`period_end_date` |
| `REPORT_LABEL_FIELDS` | both statements already present (`["account", "account_name"]`) — service layer needs **no change** |
| `report_guard.FINANCIAL_REPORTS` | both already present — desk scope enforcement needs **no change** |
| Viewer | `reports = ["Trial Balance", "General Ledger", "Accounts Receivable"]`, sends `company`, `from_date`, `to_date`, `report_date` in every call — sufficient payload for the statements |
| Re-pin surface | `bilingual-financial-reports/evidence/MANIFEST.json` pins `construction/api/bilingual_reports.py` + `construction/tests/test_stage7_bilingual_reports.py` (both change here); viewer JS is pinned nowhere; `report_bilingual_extension.py`, stage4 tests, `hooks.py`, matrix script unchanged |
| Tests | stage7 module 10 tests (includes the genuine non-admin authorization proof from 5A), stage4 module 14 — both in the 21-module / 258-test matrix |

## 3. Decisions

### R1 — allowlist expands by exactly two names; fail-closed stays universal

`PILOT_REPORTS` gains `"Balance Sheet"` and `"Profit and Loss Statement"` with their vendor
module paths (importable, `.execute` never in the path — 5A contract). Every other name
remains rejected before any vendor import/execute; the existing `test_unknown_report_fails_closed`
must keep passing byte-identical. No third name, no pattern matching, no user-supplied module
paths.

### R2 — single-execute invariant carries to the statements (5A R1)

Each request runs the vendor `execute` **exactly once**; post-processing stays pure on the
returned tuple (the statements' 6-tuples flow through the existing tuple handler: transform
`[0]`/`[1]`, `tail[:3]` keeps message/chart/report_summary for future use, viewer renders
`columns`/`data`). A per-report `call_count == 1` assertion covers both statements.

### R3 — genuine authorization unchanged (5A R2)

`frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))` stays in front of
the filter defaulting and execution; the existing real-user proof keeps guarding the endpoint,
extended with an assertion that a statement name is rejected for the non-admin user **before**
execute runs.

### R4 — period defaults are read-only filter filling, not report behavior

`_ensure_required` gains a statements branch using only `setdefault`:

- default `filter_based_on = "Date Range"` with `period_start_date`/`period_end_date` taken
  from the viewer's `from_date`/`to_date`, falling back to `_fy_bounds(company)` (so the
  viewer's visible date fields keep driving the statements — no silent fiscal-year switch);
- if the caller explicitly passes `filter_based_on = "Fiscal Year"`: default
  `from_fiscal_year`/`to_fiscal_year` from `filters.fiscal_year` or `_resolve_fy(company)`;
- default `periodicity = "Yearly"` (single yearly column for a bounded range; the vendor clips
  to the range end) and `accumulated_values = 0`.

Caller-supplied values are always respected (`setdefault` only). No vendor file edit, no
Report DocType, no filter mutation beyond the defaults, no data write.

### R5 — viewer exposes both statements; page JS needs no `?v=` bump

The page Select gains `Balance Sheet` and `Profit and Loss Statement` (options list only —
render path, default report, and payload shape untouched). The file is a Frappe **page**
bundle and is **not** registered in `hooks.py` `app_include_js` (verified by grep) — AGENTS
§4.4's `?v=` rule applies to hook-registered JS; desk build hashes the page bundle. Recorded so
the absence of a bump is a checked decision, not an oversight.

### R6 — exactly one disclosed manifest re-pin

Changed tracked files: `construction/api/bilingual_reports.py` and
`construction/tests/test_stage7_bilingual_reports.py` (both pinned by
`bilingual-financial-reports/evidence/MANIFEST.json`), plus the unpinned viewer JS.
Therefore **exactly one manifest, two digests re-pinned** — disclosed in both manifests'
amendment notes at commit time (same authorization model as 5A's "8 manifests re-pinned").
Every other manifest must verify byte-unchanged. (A matrix-script comment correction was
attempted and reverted — see A1: the script is pinned by 8 manifests.)

### R7 — no display/config/governance changes beyond the three files

No `report_guard` / `scope_report` edits (already cover both), no `report_bilingual_extension`
edits (label fields already present), no `hooks.py` edits, no registry edits, no matrix-script
edits (module list unchanged — the suite grows to 264 tests; the script's stale `258` comment
is deferred under A1), no Account/translation writes.

## 4. Invariants preserved

- **Vendor boundary:** zero files under `apps/frappe` / `apps/erpnext` change.
- **D5 triad / registry:** `bilingual_service.py`, `searchable_dropdown/api/search.py`,
  `bilingual_registry.json` untouched (call-only).
- **Read-only reports:** vendor `execute` output post-processed in memory only; no Report
  DocType, no runtime-data mutation; mapping served from the R7 redis cache unchanged.
- **Fail-closed:** unknown names still rejected before import; role gate unchanged.
- **Scope enforcement:** both statements already in `FINANCIAL_REPORTS` — desk path untouched.
- **Matrix:** module list (21) unchanged ⇒ no matrix-script digest change ⇒ no re-pin from
  the gate itself.

## 5. Tests and evidence gates

Additions to `test_stage7_bilingual_reports` (module stays in the 21-module matrix):

1. `test_statement_reports_in_allowlist` — both names in `PILOT_REPORTS`, module importable,
   `execute` callable, path contains no `.execute` (existing smoke loop also auto-covers them);
2. `test_statement_execute_runs_exactly_once` — R2 single-execute per statement, ar mode
   transforms through the label fields;
3. `test_statement_ar_mode_localizes_account_name` — `account` + `account_name` rows swap
   under the mapping (synthetic mapping key);
4. `test_statement_period_defaults_date_range` — viewer `from_date`/`to_date` fill the
   Date Range window, R4 defaults present for both statements;
5. `test_statement_period_defaults_fiscal_year_and_fallback` — explicit Fiscal Year mode
   resolves fiscal years; omitted dates fall back to company FY bounds (ordered);
6. `test_statement_caller_values_win` — caller `periodicity`/period dates/`accumulated_values`
   preserved verbatim;
7. auth extension — the real non-admin rejection (5A R2) now also asserted for
   `"Balance Sheet"`, still before any vendor resolution.

**Test-harness hardening (disclosed during implementation):** the historical blanket
`mock.patch("frappe.get_module")` interception breaks frappe internals once
`_ensure_required` touches DB/meta paths (hook `frappe.get_attr` → patched importer →
`AttributeError`), and it also broke the auth test's controller import whenever a leftover
test user skipped the insert (a residue failure mode this cycle's first failed cleanup
created). The suite now uses `_patched_report_modules(mapping)`: it intercepts **only**
`PILOT_REPORTS` module paths and delegates every other resolution to the real importer —
same fail-closed semantics, `resolved == []` replaces the old `gm.call_count == 0`
assertion. Existing mode tests in `TestBilingualReportsAPI` keep their historical binding
(they pass unchanged; R2b precedent).

Evidence gates: `probe-statements-execution.log` (live unmocked run of both statements
through `localized_report` on `v16.localhost`, ar + en, read-only), stage4 + stage7 standalone
runs, canonical matrix (21 modules / 264 tests), reconciler 19/19, lints
(`lint_scope_metadata`, `ai_context_check`, `lint_translation_writes`, `schema_drift_checker`,
`py_compile`, `bash -n`, `node --check` on the viewer page JS), `MANIFEST.json`, digest
verification (24 pre-existing manifests minus the one disclosed re-pin, plus this item's).

Causal order (mandatory): implement → tests → probe + standalone runs → matrix + reconciler +
lints → capture logs (`2>&1`) → `git add -f` the `.log` → SHA-256 digests → re-pin the one
manifest → `MANIFEST.json` → commit.

## 6. Out of scope

- **Any third report** (Accounts Payable, Cash Flow, Budget Variance, Project-wise
  Profitability) — separate proposal.
- **Filter UI additions** to the viewer (fiscal-year/periodicity selectors) — defaults only;
  the viewer's existing date fields drive Date Range mode.
- **Stage-8 / production:** `production_mutation_authorized: false`.
- **P95 latency re-measurement** (5A R5 contract stays as recorded; statements join the same
  ratio limbs only if re-measured later under separate approval).
- **`report_bilingual_extension` / guard / hooks / registry edits.**
- **Row-level scope-filter rewriting for the statements** — the API path executes vendor
  reports directly under caller permissions, as GL/TB/AR already do.

## 7. Evidence causal order

implement → tests → live probe (both statements, ar + en) → standalone stage4/stage7 runs →
matrix + reconciler + lints → capture logs (`2>&1`) → `git add -f` the `.log` files →
SHA-256 digests → disclosed re-pin of the one affected manifest → this item's
`evidence/MANIFEST.json` → commit.

## 8. Results (2026-10-05, base `890ae14`, COMPLETE)

| Gate | Result |
|---|---|
| `test_stage7_bilingual_reports` (standalone) | **16/16 OK** (10 existing + 6 statement tests; auth test extended to Balance Sheet) |
| `test_stage4_report_extension` (standalone) | **14/14 OK** (unchanged) |
| Canonical regression matrix | **21/21 modules OK, 264 tests** (258 + 6 new) |
| ADR reconciler | **19/19 PASS** (mismatched 0, unsourced 0) |
| `lint_scope_metadata` / `ai_context_check` / `lint_translation_writes` / `schema_drift_checker` | **PASS** (ai_context 11/11) |
| `py_compile` / `bash -n` / `node --check` (viewer JS) | **PASS** |
| Live probe (unmocked, both statements × ar/en) | **PASS** — BS 5 cols/10 rows, P&L 5 cols/6 rows, 6-tuple `tail` present, R4 defaults applied, BS `account` ar-swap True, `account_name` mapped-swap/ passthrough correct, Account/GL-Entry counts 2102/4 unchanged |
| Manifests | 25 manifests / 235 digests verified staged (224 baseline + 11 new, 0 bad); exactly **1 manifest re-pinned** (`bilingual-financial-reports`: 2 digests, disclosed) |

Amendments disclosed during implementation:

- **A1 (matrix comment, reverted):** `run_bilingual_regression_matrix.sh` line 3 says "258
  total tests" while the suite now runs 264. A comment-only correction was staged, then
  **reverted to HEAD byte-identical** when digest verification showed the script is pinned
  by **8 manifests** (the 5A re-pin set) — an 8-manifest re-pin blast radius for a cosmetic
  comment is outside disclosed R6 scope. Deferred to the next authorized matrix-script
  change; the authoritative count lives in the matrix log and this item's manifest (264).
  R6/R7 amended accordingly before commit (2 digests, not 3).
- **A2 (test-harness hardening):** `_patched_report_modules` guarded interception replaces
  the blanket `frappe.get_module` patch in the statement tests and the auth test (details
  in §5) — required because the new R4 defaults touch DB/meta paths the blanket patch broke,
  and it removes the residue-user failure mode of the 5A auth test.

Operational notes: the first failed test cycle left the auth test's throwaway user
(`ct-finance-noperm@example.com`) + contact behind (cleanup rolled back because redis
`11000` was down); both were removed manually, the test now self-heals under the guarded
patch, and redis `11000`/`13000` were started for the matrix run (torn down after commit
verification). Zero vendor files, zero registry/triad files, zero data writes — probe
mutation guard PASS is the evidence.
