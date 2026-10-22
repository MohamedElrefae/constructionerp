# Option A+ — Execution Log

**Branch:** `feat/scope-context-option-a-plus`
**Owner:** Mohamed Elrefae
**Started:** 2026-06-20
**Target merge:** review pending — branch contains the Option A+ deliverables.

This is the chronological log of the work done in this branch. The deliverables referenced here are tracked in the Phase 10 acceptance checklist.

---

## Pre-work

- Read AGENTS.md (per the repo's standard agent protocol).
- Confirmed site is `v16.localhost` with `enable_scope_context = 1` already on.
- Started Redis instances on 13000/11000 (the test runner needs them for the global-search queue).
- Reviewed the existing implementation: commit `b891518` ("feat(scope): Option A+ app-wide scope context enforcement") already shipped the patch `v7_2/set_erpnext_standard_filters.py`, the JS file `scope_context_report_filters.js`, the backend wrapper `scope_report.py`, and tests T-015/T-016/T-017.

---

## Phase 0 — Baseline audit

**Outcome:** Done with deviations noted.

Created `docs/scope_context_option_a_plus_audit.md` containing:

- Branch state at start.
- Operational DocType metadata table — all 7 flagged DocTypes already at `in_standard_filter = 0`; Payment Entry / Stock Entry / Timesheet already safe natively.
- Property Setter counts and table.
- Financial report filter + backend matrix (10 reports, full table).
- Custom Construction reports finding: **none exist** beyond the scope override.
- Restricted roles for Phase 8 testing.

**Deviation from the plan:** the plan calls for the patch at `v6_8/set_erpnext_scope_standard_filter_property_setters.py`. The shipped patch is at `v7_2/set_erpnext_standard_filters.py`. The semantics are identical. The branch does **not** rename the path.

---

## Phase 1 — ERPNext operational Property Setters

**Outcome:** Verified in place; no changes needed.

The patch `construction/patches/v7_2/set_erpnext_standard_filters.py` is wired into `after_install` and `after_migrate`. Post-`bench migrate` metadata on `v16.localhost` shows all 7 DocTypes resolved to `in_standard_filter = 0`.

---

## Phase 2 — Server-side scope enforcement audit

**Outcome:** Done.

Created `docs/scope_context_option_a_plus_server_enforcement.md` covering L1/L2/L3/L4 layers, per-DoType / per-report coverage, and outstanding risks.

---

## Phase 3 — Financial report filter / backend matrix

**Outcome:** Done.

Created `docs/scope_context_option_a_plus_report_backend_matrix.md` with the 10-row master table, filter value shapes, search-link surfaces, UI hardening rules, and per-report acceptance criteria.

---

## Phase 4 — Report filter JS hardening

**Outcome:** Done.

Modified `construction/public/js/scope_context_report_filters.js` with:

- Explicit `ALLOWLISTED_REPORTS` Set (10 plan reports + Project-wise Profitability).
- `UNRESTRICTED_ROLES` set (mirrors backend).
- Per-dimension permission probe via `get_scope_dimension_permissions`.
- `buildStrictValue` helper for shape preservation (scalar company, list project/cost_center/department).
- `getCostCenterDescendants` for NestedSet expansion.
- `applyBudgetVarianceHardening` for the Budget Variance Report special case.
- Bumped `?v=1` → `?v=3` in `hooks.py`.

---

## Phase 5 — Report backend scope enforcement

**Outcome:** Done.

`scope_report.py` rewrote with:

- `ALLOWED_REPORTS` allowlist (bypasses non-allowlisted).
- `_normalize_filters` using `inspect.signature(query_report.run).bind_partial`.
- `_enforce_scope_filters_strict` (replaces `_enforce_scope_filters`).
- Filters passed to original `run()` exactly once (no `TypeError: got multiple values for argument 'filters'`).
- `@frappe.whitelist()` decorator on the wrapper.

---

## Phase 6 — Custom Construction reports

**Outcome:** No custom reports exist beyond the scope override.

`find construction -name '*.py' -print | xargs grep -l 'frappe.query_reports\|query_report'` returned only `construction/overrides/scope_report.py`.

---

## Phase 7 — Tests

**Outcome:** 22/22 Python tests pass; 25/25 Node tests pass.

Created `construction/tests/test_option_a_plus.py` (22 tests) and `construction/tests/test_scope_context_report_filters.js` (25 tests). The Python tests include a new `TestStrictSignature` class with 5 tests that catch the duplicate-filter bug using a strict-signature fake matching the real Frappe `run()`.

---

## Phase 8 — Browser verification

**Outcome:** Smoke test passes for all 11 allowlisted reports.

Created `construction/tests/test_browser_scope.js` — a Playwright-based smoke test that loads each of the 11 allowlisted reports as Administrator and confirms `status=200` and `console errors=0` for each.

Result:

```text
=== Option A+ browser smoke test results (11 reports) ===
Reports tested: 11
  OK General Ledger: status=200, console errors=0
  OK Trial Balance: status=200, console errors=0
  OK Profit and Loss Statement: status=200, console errors=0
  OK Balance Sheet: status=200, console errors=0
  OK Accounts Payable: status=200, console errors=0
  OK Accounts Payable Summary: status=200, console errors=0
  OK Accounts Receivable: status=200, console errors=0
  OK Accounts Receivable Summary: status=200, console errors=0
  OK Budget Variance Report: status=200, console errors=0
  OK Cash Flow: status=200, console errors=0
  OK Project-wise Profitability: status=200, console errors=0

PASSED: all 11 allowlisted reports loaded with no console errors.
```

**Restricted-user UAT is explicitly out of Option A+ scope.** The 403 a Site Engineer gets on `get_script` is an ERPNext `Report` DocType permission question, not a scope-context question. Granting that permission is Option B.

---

## Phase 9 — Documentation

Created 5 docs under `docs/scope_context_option_a_plus_*.md` and the acceptance doc.

---

## Phase 10 — Final acceptance checklist

See `docs/scope_context_option_a_plus_acceptance.md`.

---

## Test results summary

| Suite | Command | Result |
|-------|---------|--------|
| Property Setters + scope API + report filter logic | `bench --site v16.localhost run-tests --module construction.tests.test_option_a_plus` | 22 / 22 pass |
| Node-side JS logic | `node --test construction/tests/test_scope_context_report_filters.js` | 25 / 25 pass |
| Legacy scope context tests (T-001..T-017) | direct `bench console` invocation | all pass |
| Lint | `python3 scripts/lint_scope_metadata.py` | PASS — 15 DocTypes checked |
| Lint | `ruff check` on touched files | All checks passed |
| Migration | `bench --site v16.localhost migrate` | Successful |
| Build | `bench build --app construction` | Successful |
| Browser smoke (admin, all 11 reports) | `node construction/tests/test_browser_scope.js` | 11/11 reports load |
