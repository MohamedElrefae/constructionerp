# Scope Descriptor — bilingual-financial-reports-expansion

**Work item:** `bilingual-financial-reports-expansion`
**Branch:** `develop`
**Base commit:** `234c024`
**Date:** 2026-10-05
**Status:** `COMPLETE` — `Accounts Receivable Summary`, `Accounts Payable Summary` and `Cash
Flow` added to the fail-closed bilingual report allowlist end to end (API + read-only
report-specific defaults + viewer + localized column headers) under the unchanged Tier-5A
contract, with all five briefing statements proven live (results in §8)
**Authority:** Session B mission briefing `docs/ai/BRIEFING_FINANCIAL_REPORTS_EXPANSION.md`
(owner, 2026-10-05, "Stage 7 Extension"), executed as an independent session alongside
Sessions A / C / D in the shared working tree
**Scope:** Expand `PILOT_REPORTS` in `construction/api/bilingual_reports.py` by exactly three
names, supply their read-only vendor-required filter defaults, expose them in the
`bilingual-report-viewer` page (with date-range vs fiscal-year filter display), localize
column headers for **every** allowlisted report in `ar`/`both` modes from a governed
`COLUMN_LABELS` map, and prove the full Tier-5A contract (fail-closed rejection, single
execute, genuine authorization, zero writes, matrix integration) still holds — with zero
edits to `apps/frappe` / `apps/erpnext`, zero data mutation, and exactly two disclosed
manifest re-pins.

---

## 1. The gap this closes

Tier 5E (`bilingual-report-statements-allowlist`, `890ae14`) proved the statement expansion
pattern for `Balance Sheet` and `Profit and Loss Statement` and recorded in its §6 that
"any third report (Accounts Payable, Cash Flow, …) — separate proposal". This item is that
separate proposal, extended by the owner's briefing to the accounting statements accountants
actually asked for:

- `PILOT_REPORTS` held five names (GL, TB, AR Aging, BS, P&L) — **Accounts Payable Summary,
  Accounts Receivable Summary and Cash Flow were fail-closed rejected** ("Unsupported
  report"), which is the guard working as designed on an incomplete list.
- The viewer Select hard-coded the same five names, and always offered only a date window —
  `Trial Balance` is fiscal-year driven and had no fiscal-year control.
- The viewer always sent `party_type: "Customer"`, which is wrong for a payables report.
- Column headers were returned in the caller-session vendor language: no governed Arabic
  header map existed anywhere on the report path (the site's approved `tabTranslation` rows
  carry the values, but nothing consumed them for report columns).
- `_ensure_required` had no defaults for the two summary reports (`report_date` window) and
  did not route `Cash Flow` through the `get_period_list` period contract.

Desk-level scope enforcement already covered every name
(`overrides/report_guard.py` `FINANCIAL_REPORTS` contains all three — verified, no change
needed), and the service layer's label-field fallback (`["account", "account_name"]`)
already covers report rows. **The remaining gap was the endpoint allowlist, the defaults,
the viewer, and the header map.**

## 2. Verified current state (probed 2026-10-05, base `234c024`)

| Fact | Value |
|---|---|
| `PILOT_REPORTS` before | 5 entries: General Ledger, Trial Balance, Accounts Receivable, Balance Sheet, Profit and Loss Statement |
| `report_guard.FINANCIAL_REPORTS` | **already contains** `Accounts Payable Summary`, `Accounts Receivable Summary`, `Cash Flow` — desk scope enforcement needs **no change** |
| Vendor module paths (new) | `erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary` (2-tuple `columns, data`), `…accounts_payable_summary.accounts_payable_summary` (2-tuple), `…cash_flow.cash_flow` (**5-tuple** `columns, data, message, chart, report_summary`) — all readable, never edited |
| Vendor filter contract (summaries) | subclass `ReceivablePayableReport`; `__init__` defaults `report_date` to *today* and `range` to `30, 60, 90, 120`; `get_data` needs `report_date`, `company`, and uses `filters.party_type` only for return entries |
| Vendor filter contract (Cash Flow) | calls `get_period_list(from_fiscal_year, to_fiscal_year, period_start_date, period_end_date, filter_based_on, periodicity, company=…)` — the exact Tier-5E statement contract; the `Date Range` branch never reads the fiscal years |
| GL column labels | built as `_("Debit ({0})").format(currency)` → **base-label + suffix** matching is mandatory (`Debit (EGP)`) |
| `approved_ar_overrides.csv` | 4,337 rows, **no exact rows** for the plain column labels — provenance is the site's `tabTranslation` ar rows instead |
| Viewer | page bundle, **not** registered in `hooks.py` `app_include_js` (re-verified by grep) → no `?v=` bump (same checked decision as 5E R5) |
| Re-pin surface | `bilingual-financial-reports` pins `bilingual_reports.py` + `test_stage7_bilingual_reports.py` (+ unchanged service/matrix script); `bilingual-report-statements-allowlist` pins `bilingual_reports.py` + viewer JS + `test_stage7_bilingual_reports.py` → **2 manifests, 5 digests**. `scripts/run_bilingual_regression_matrix.sh` is pinned by 10 manifests and stays byte-identical |
| Baseline manifest integrity | 31 manifests / 328 digests verified against the working tree: **0 bad** (45 legacy work-item-relative artefact paths resolve against the work-item directory — the verifier must handle both conventions) |
| Tests before | stage7 module 16 tests, stage4 14; matrix 21 modules / 264 tests |

## 3. Decisions

### R1 — three names join the allowlist; fail-closed stays universal

`PILOT_REPORTS` gains exactly `Accounts Receivable Summary`, `Accounts Payable Summary` and
`Cash Flow` with their importable vendor module paths (no `.execute` in any path — the 5A
contract). The briefing's `General Ledger` and `Trial Balance` were already present and are
covered by the mission assertions rather than re-added. Every other name remains rejected
before any vendor import/execute; `test_unknown_report_fails_closed` passes byte-identical.

### R2 — report-specific read-only defaults, caller values always win

`_ensure_required` gains two branches (only `setdefault`, no assignment of caller data):

- **AR/AP Summary** — `report_date` / `to_date` default from the viewer's `to_date`, falling
  back to the fiscal-year end (`_fy_bounds`), plus `ageing_based_on = "Posting Date"` and
  `fiscal_year`. This prevents the vendor default of *today* from silently replacing the
  requested window.
- **Cash Flow** — routed into the existing Tier-5E statement branch via the new
  `PERIOD_CONTRACT_REPORTS = STATEMENT_REPORTS + ("Cash Flow",)` tuple: `periodicity
  = "Yearly"`, `accumulated_values = 0`, `filter_based_on = "Date Range"` with
  `period_start_date` / `period_end_date` from the viewer's dates, or the Fiscal-Year
  branch when the caller asks for it.

`STATEMENT_REPORTS` keeps its original meaning for the Tier-5E tests; no existing consumer
is renamed away.

### R3 — governed `COLUMN_LABELS`, deterministic (owner-approved approach)

Column headers are localized from a hardcoded map in `bilingual_reports.py` (R1 of the
session's choices), **not** from a runtime translation lookup, because:

- the site has **competing approved rows** for several labels (`Posting Date` →
  `تاريخ الترحيل` *and* `تاريخ القيد`; `Balance` → `الرصيد` *and* `الموازنة`; `Party`,
  `Section`, `Currency`, `Total` each have 2+ candidates, some empty);
- Session C is harmonizing `tabTranslation` concurrently — a runtime lookup would be
  non-deterministic across a run;
- the report path then needs no translation cache or DB read at all.

Values were harvested **read-only** from `tabTranslation` (`language='ar'`, grouped by
source/translation) on 2026-10-05 and pinned. Recorded resolutions:

| Label | Chosen | Rejected |
|---|---|---|
| Posting Date | تاريخ الترحيل | تاريخ القيد (kept consistent with the reviewed glossary's `Posting Datetime` → `تاريخ ووقت الترحيل`) |
| Balance | الرصيد | الموازنة (statement column convention) |
| Party | الطرف | الطرف المعني (column width) |
| Section | القسم | الجزء |
| Invoiced Amount | قيمة الفواتير | sole approved row |
| Currency / Account Number / Customer Name / Supplier Name / Closing Balance | العملة / رقم الحساب / اسم العميل / اسم المورد / الرصيد الختامي | the empty duplicate row where one exists |

**Deliberately unmapped (fail-open passthrough):** `GL Entry` (`GL الدخول` is a
non-accountant calque), `Age (Days)` (`(العمر (أيام` is malformed), `Against Voucher Type`
(`مقابل إيصال  نوع`, double space), `Transaction Currency` (`عملية العملات`, wrong
meaning), `Opening (Dr)` (`افتتاحي  (Dr)`, double space + untranslated suffix), `Grand
Total` (4 competing approved rows, no recorded resolution).

Matching is on the English **base label** with any `" (...)"` suffix preserved verbatim —
`Debit (EGP)` → `مدين (EGP)` — because the vendor formats currency into the label.
Unmapped bases (e.g. `Age` from `Age (Days)`) pass through untouched.

### R4 — header localization scope: all allowlisted reports, `ar` + `both`

`_localize_columns` runs on every `localized_report` payload: `en` returns the input
unchanged, `ar` swaps mapped bases, `both` mirrors the cell convention
(`Section — القسم`). It builds **new column dicts** (never mutates vendor or transform
structures — asserted by `test_column_headers_pure_source_untouched`). This changes the
header language of the five pre-existing reports in `ar`/`both` mode, which is disclosed
here as the intended improvement (owner-approved scope).

### R5 — viewer: three options, date-range vs fiscal-year display, correct party type

The page Select gains the three statements. A new `fiscal_year` Link field (Fiscal Year) is
shown for `Trial Balance` while the `from_date` / `to_date` fields are hidden, and hidden in
return for every other report — exactly one filter surface is offered per report type
(owner-approved: "configure date-range vs fiscal-year filter display"). The payload adds
`fiscal_year` when set and now sends `party_type: "Supplier"` for `Accounts Payable Summary`
(previously hard-coded `Customer` for every report, which would have filtered payables out
of the return-entries path). Render path, default report and error handling are untouched;
`node --check` gates the file. No `?v=` bump (page bundle, not hook-registered — re-verified).

### R6 — exactly two disclosed manifest re-pins (5 digests)

Changed tracked files: `construction/api/bilingual_reports.py`,
`construction/tests/test_stage7_bilingual_reports.py`,
`construction/construction/page/bilingual_report_viewer/bilingual_report_viewer.js` — pinned
by exactly two manifests (`bilingual-financial-reports`: 2 digests;
`bilingual-report-statements-allowlist`: 3 digests). Both receive amendment entries at
commit time under the same authorization model as 5A/5E. Every other manifest must verify
byte-unchanged. **Not mine, not re-pinned:** `construction/hooks.py` and
`construction/install.py` are modified in the shared working tree by Session A (print-format
install hooks) — outside this item's scope and excluded from this manifest.

### R7 — no service / guard / hooks / registry / matrix-script edits

`report_bilingual_extension.py` (label fields fall back to
`["account", "account_name"]`, which is correct for GL/TB/BS/P&L/Cash-Flow rows and simply
inert for party-centric summary rows), `report_guard`, `scope_report`, `hooks.py`,
`bilingual_registry.json`, the D5 triad and `run_bilingual_regression_matrix.sh` are all
untouched. The matrix script's stale "258 total tests" comment stays stale (5E A1
precedent: it is pinned by 10 manifests); the authoritative count lives in the matrix log
and this manifest (**273**).

### R8 — shared-tree / shared-site coordination

Sessions A, C and D run against the same working tree, the same `v16.localhost` site and the
same ephemeral redis ports. Therefore: no git staging or commits from this session (briefing
§5), `SESSION_MEMORY.md` / `OWNER_CONFIDENTIALITY_POLICY.md` / the briefing files /
`dump.rdb` / `construction/_tmp_probe.py` are left untouched, `bench run-tests` is only
started when no other session's run is active, and redis 11000/13000 is torn down only after
confirming no concurrent run-tests process remains.

## 4. Invariants preserved

- **Vendor boundary:** zero files under `apps/frappe` / `apps/erpnext` change.
- **Fail-closed:** unknown names rejected before import; role gate unchanged
  (`frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))`).
- **Single execute:** one vendor `execute` per request for every report, old and new.
- **Read-only:** defaults are `setdefault` fills of vendor contracts; headers and labels are
  post-processed into **new** structures; no Report DocType, no Account / Translation /
  GL Entry write. Unit guard asserts no `frappe.db.set_value/insert/delete` fires; the live
  probe asserts unchanged row counts.
- **D5 triad / registry / service layer:** byte-identical to base.
- **Matrix module list (21) unchanged** → no matrix-script digest change → no re-pin from
  the gate itself.

## 5. Tests and evidence gates

Nine tests added to `test_stage7_bilingual_reports` (module stays in the 21-module matrix):

1. `test_mission_reports_in_allowlist` — all five briefing names present, importable,
   callable `execute`, no `.execute` in the path (the unmocked smoke loop auto-covers them);
2. `test_expanded_execute_runs_exactly_once` — R2 single-execute per new report;
3. `test_summary_defaults_report_date_window` — `report_date`/`to_date`/
   `ageing_based_on`/`fiscal_year` defaults for both summaries;
4. `test_summary_caller_report_date_wins` — caller `report_date` preserved verbatim;
5. `test_cash_flow_period_defaults` — Date Range window + Fiscal Year branch + caller
   `periodicity` win;
6. `test_column_headers_localized_ar_en_both` — `ar` swap incl. currency suffix, `en`
   byte-identical, `both` combined, unmapped (`Age (Days)`) passthrough;
7. `test_column_headers_pure_source_untouched` — vendor column structures never mutated;
8. `test_localize_column_label_unit` — unit-level label mapping, suffix, `both`, empties;
9. `test_report_path_makes_zero_db_writes` — mutation guard: `frappe.db.set_value`,
   `insert`, `delete` raise if touched while the three new reports render.

Plus the existing `TestGenuineAuthorization` extended: the real non-admin is rejected for
`Accounts Payable Summary` and `Cash Flow` **before** any vendor module resolution
(`resolved == []`).

Evidence gates: `report-execution.log` (live unmocked probe, 5 statements × ar/en on
`v16.localhost`, header diffs + read-only counts), stage4 + stage7 standalone runs, canonical
matrix (21 modules / **273** tests), ADR reconciler **19/19**, `gates.log`
(`lint_scope_metadata`, `ai_context_check` 11/11, `lint_translation_writes`,
`schema_drift_checker`, `py_compile`, `bash -n`, `node --check`, reconciler),
`MANIFEST.json` (#33), digest verification of all 31 pre-existing manifests.

Causal order (mandatory): implement → tests → live probe → standalone stage4/stage7 runs →
matrix + reconciler + lints → capture logs (`2>&1`) → SHA-256 digests → disclose the two
re-pins → `MANIFEST.json` → hand over unstaged.

## 6. Out of scope

- **`Accounts Payable` (aging)** and other vendor reports (Budget Variance, Project-wise
  Profitability) — not in the briefing.
- **Viewer filter UI beyond the fiscal-year/date toggle** (periodicity, party selector).
- **Editing `report_guard` / `scope_report` / `report_bilingual_extension` / `hooks.py` /
  the registry / the matrix script.**
- **Any `tabTranslation` write** — harvesting was read-only; Session C owns catalog writes.
- **P95 latency re-measurement** (5A R5 contract stays as recorded).
- **Stage-8 / production:** `production_mutation_authorized: false`.
- **Session A's `hooks.py` / `install.py` / print-format files** and Session D's runbook
  artefacts — other sessions' scope, verified untouched by this session.

## 7. Evidence causal order

implement → tests → live probe (5 statements × ar/en) → standalone stage4/stage7 runs →
matrix (run only after Session A's concurrent matrix finished) + reconciler + lints → capture
logs (`2>&1`) → SHA-256 digests → disclosed re-pin of the two affected manifests → this
item's `evidence/MANIFEST.json` → leave the tree unstaged for Antigravity.

## 8. Results (2026-10-05, base `234c024`, COMPLETE)

| Gate | Result |
|---|---|
| `test_stage7_bilingual_reports` (standalone) | **25/25 OK** (16 existing + 9 expansion tests; auth test extended to the new names) |
| `test_stage4_report_extension` (standalone) | **14/14 OK** (unchanged) |
| Canonical regression matrix | **21/21 modules OK, 273 tests** (264 + 9), 0 failures |
| ADR reconciler | **19/19 PASS** (mismatched 0, unsourced 0) |
| `lint_scope_metadata` / `ai_context_check` / `lint_translation_writes` / `schema_drift_checker` | **PASS** (ai_context 11/11) |
| `py_compile` / `bash -n` / `node --check` (viewer JS) | **PASS** |
| Live probe (unmocked, 5 statements × ar/en) | **PASS** — GL 15 cols/16 rows, TB 10/3, AR Summary 17/1, AP Summary 16/0, Cash Flow 3/18 (`tail` present); headers swapped for all 5 (`تاريخ الترحيل`, `مدين (EGP)`, `الرصيد (EGP)`, `نوع السند`, `الحساب`, `مدين`, `دائن`, `الطرف`, `المبلغ مقدما`, `قيمة الفواتير`, `المبلغ المدفوع`, `إشعار دائن/مدين`, `القسم`, `العملة`); `en` headers stable across runs; `both` headers combined; `Age (Days)` and `GL Entry` pass through untranslated; Account / GL Entry / Report / Translation counts identical before/after the run |
| Manifests | 31 pre-existing manifests / 328 digests verified (0 bad, legacy relative paths resolved) → **exactly 2 manifests re-pinned (5 digests, disclosed)**; this item's manifest #33 added |

Amendments disclosed during implementation:

- **A1 (concurrent-site account drift):** the live probe's own mutation guard compares
  counts *within* one run and passes (`Account` 2103 → 2103 in the retained log). Across
  separate runs the site count oscillated 2102 ↔ 2103 because Sessions A/C/D were running
  their own suites against the same `v16.localhost` (a `tabAccount` row was modified by a
  concurrent run between probe pass 1 and pass 2). The invariant claimed here is the
  within-run zero-write guard, which is what the probe and the unit guard assert; the
  cross-run oscillation is recorded so a later auditor does not misread it.
- **A2 (serialized test execution):** this session's matrix run was deferred until Session
  A's concurrent `run-tests` process finished, and redis 11000/13000 teardown was deferred
  the same way (R8) — otherwise the shared suite would have failed on a mid-run cache
  teardown (5H gate note G1 precedent). The deferred teardown was then **executed at
  handover (23:50)** after `ps`/`pgrep` confirmed no `run-tests` / `test_runner` / frappe
  test process was active: `redis-cli -p 11000 shutdown nosave` and `-p 13000 shutdown
  nosave` both completed and `ss -ltn` verifies **11000/13000 closed** (Connection refused).
  System redis **6379 is deliberately left up** (project precedent, company-phase1 F-5H-2);
  any session that needs the test-scoped pair restarts it from
  `config/redis_queue.conf` / `config/redis_cache.conf` (daemonized), the documented
  recovery for gate note G1.
- **A3 (column map wider than the briefed eight):** beyond the briefing's enumerated
  `Posting Date`, `Account`, `Debit`, `Credit`, `Voucher Type`, `Voucher No`,
  `Against Account`, `Balance`, five more labels with a single unambiguous approved row were
  added (`Currency`, `Account Number`, `Customer Name`, `Supplier Name`, `Closing Balance`)
  so the AR/AP summary and trial-balance headers are not left half-translated. No label with
  a contested or malformed approved row was added (§3 R3).
- **A4 (viewer `party_type`):** the hard-coded `party_type: "Customer"` is now
  `Supplier` for `Accounts Payable Summary` — a behavior change to the viewer payload that
  the briefing's viewer step implies (the payables report must not be constrained to
  customers). `group_by_party`, dates and the render path are unchanged.
