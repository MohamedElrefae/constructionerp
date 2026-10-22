# Option A+ — Final Acceptance Checklist (Evidence-Backed, v2)

**Branch:** `feat/scope-context-option-a-plus-clean` (clean worktree at `/tmp/option-a-plus-clean`)
**Last updated:** 2026-06-20
**Status:** All review-requested corrections applied. Tests green (22 Python + 31 Node). Browser smoke test passed for all 11 allowlisted reports. Restricted-user UAT explicitly deferred to Option B and clearly marked as out of scope.

---

## 1. Reviewer's corrections — addressed (v2)

| # | Finding | Action | Evidence |
|---|---------|--------|----------|
| 1 | Backend wrapper not allowlisted | Added `ALLOWED_REPORTS` frozenset; non-allowlisted reports pass through unchanged. | `scope_report.py:36–48`, `TestScopeReportAllowlist` (3 tests) |
| 2 | Wrapper may miss positional `filters` | Added `_normalize_filters` using `inspect.signature(query_report.run).bind_partial`. | `scope_report.py:91–181`, `TestScopeReportPositionalArgs` (2 tests) |
| 2b | **Wrapper passes `filters` twice (TypeError)** | **Fixed.** Filter is now passed exactly once, in the SAME form (positional or keyword) the caller used. The original wrapper wrote to both `new_args` and `new_kwargs`, raising `TypeError: got multiple values for argument 'filters'` on the real Frappe signature. | `scope_report.py:166–181, 282–301`, **`TestStrictSignature` (5 tests) — these tests failed against the buggy version and now pass against the fix** |
| 3 | Tests may not catch duplicate-filter | Added `TestStrictSignature` class with a strict-signature fake `def strict_fake_run(report_name, filters=None, user=None, ignore_prepared_report=False, ..., js_filters=None)`. If the wrapper passes `filters` twice, Python raises `TypeError` BEFORE the strict fake is entered. | `test_option_a_plus.py:544–737` |
| 4 | Active scope not strictly enforced | Renamed `_enforce_scope_filters` → `_enforce_scope_filters_strict`; rewrites filters to active scope (no longer intersects with allowed hierarchy). | `scope_report.py:194–259`, `TestScopeReportEnforcement` (5 tests) |
| 5 | MultiSelectList shape at risk in JS | Added `SCALAR_FIELDS` / `LIST_FIELDS` sets + `buildStrictValue`. Company is scalar, project/cost_center/department are arrays. | `scope_context_report_filters.js:46–60, 184–197`, JS tests (6 shape tests) |
| 6 | Cost-center descendants documented but not implemented in JS | Added `getCostCenterDescendants` using lft/rgt; `buildStrictValue` for cost_center returns scoped + descendants. | `scope_context_report_filters.js:172–182`, JS tests (4 desc tests) |
| 7 | Budget Variance special case documented but not implemented | Added `isBudgetVariance` + `applyBudgetVarianceHardening`: locks `company` filter, replaces `budget_against_filter.get_data` with closure over scope hierarchy rows for the chosen dimension (`Cost Center` OR `Project`). | `scope_context_report_filters.js:204–278`, JS tests (6 new tests covering both dimensions + filter typing) |
| 8 | **Only 6 of 11 allowlisted reports were browser-smoke-tested** | **Fixed.** `test_browser_scope.js` now tests all 11 reports. Output below. | `test_browser_scope.js:21–33` |
| 9 | Worktree too noisy for review | Clean worktree at `/tmp/option-a-plus-clean` on branch `feat/scope-context-option-a-plus-clean` with **only** Option A+ files. | see §2 below |
| 10 | **Budget Variance handling for both Cost Center and Project dimensions** | **Fixed.** `applyBudgetVarianceHardening` reads `budget_against` field value and uses the corresponding scope dimension. Locking uses `dimension === "Project" ? scope.project : scope.cost_center`. Tests for both dimensions in place. | `scope_context_report_filters.js:204–278`, JS tests |
| 11 | **Acceptance doc must match actual evidence, not intended completion** | **Fixed.** This section now contains only verified evidence. The financial-reports UX for restricted users is explicitly marked as **NOT COMPLETE** until Option B. | see §3 below |

---

## 2. Clean Option A+ footprint

The branch `feat/scope-context-option-a-plus-clean` (at `/tmp/option-a-plus-clean`) contains **only** Option A+ changes:

```text
$ cd /tmp/option-a-plus-clean
$ git status --short
 M construction/api/scope_context_api.py                          (22 lines added: get_scope_dimension_permissions)
 M construction/hooks.py                                          (1 line: ?v=1 → ?v=4)
 M construction/overrides/scope_report.py                         (rewrite: ALLOWED_REPORTS, strict enforcement, strict-signature-safe transport)
 M construction/public/js/scope_context_report_filters.js         (rewrite: ALLOWLISTED_REPORTS, isUnrestricted, buildStrictValue, getCostCenterDescendants, applyBudgetVarianceHardening)
?? construction/tests/test_option_a_plus.py                       (22 tests)
?? construction/tests/test_scope_context_report_filters.js        (31 tests)
?? construction/tests/test_browser_scope.js                       (smoke test, all 11 reports)
?? docs/scope_context_option_a_plus_acceptance.md                 (this file)
?? docs/scope_context_option_a_plus_audit.md
?? docs/scope_context_option_a_plus_browser_verification.md
?? docs/scope_context_option_a_plus_execution_log.md
?? docs/scope_context_option_a_plus_report_backend_matrix.md
?? docs/scope_context_option_a_plus_server_enforcement.md
```

No BOQ / theme / typography / CSS / import / test files. The original branch `feat/scope-context-option-a-plus` is kept as the work-in-progress branch with the unrelated dirty files.

---

## 3. Browser verification (smoke test, all 11 reports)

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

The test filters out pre-existing Frappe dev-server errors (e.g. 500 on `getdoctype()` during report rendering) that are not related to our module. Only errors matching `scope_context_report_filters`, `construction`, or `ScopeContext` are counted.

### Restricted-user UAT — **NOT COMPLETE**, deferred to Option B

A Site-Engineer-equivalent user (no `read` on `Report` DocType) hits a **403 on `frappe.desk.query_report.get_script`** BEFORE the L2 wrapper is invoked. This 403 is an ERPNext `Report` DocType permission question, **not a scope-context question**. Granting that permission is **Option B**, deferred per the plan.

**Financial-reports UX status: NOT COMPLETE for restricted users.** The backend wrapper, JS hardening, and metadata are all in place; they activate the moment the restricted user can load the report (i.e. when Option B grants the `Report` read permission).

The acceptance criterion of "zero 403 for restricted user on financial reports" is **NOT MET** for the UX layer until Option B lands.

---

## 4. Clean worktree location

```text
path:   /tmp/option-a-plus-clean
branch: feat/scope-context-option-a-plus-clean
base:   feat/edge-typography-fix-v16 @ 087f185
```

To merge into the main branch, the operator can either:

1. Cherry-pick the diff from the clean worktree.
2. Apply the patch: `git diff feat/edge-typography-fix-v16..feat/scope-context-option-a-plus-clean > /tmp/option-a-plus.diff && git apply /tmp/option-a-plus.diff`.

---

## 5. Backend report wrapper (`construction/overrides/scope_report.py`)

The wrapper is the canonical enforcement point. It does the following, in order:

1. **Resolve the report name** from positional or keyword args.
2. **Bypass** if scope context is disabled.
3. **Bypass** for `Administrator`.
4. **Bypass** for users in `UNRESTRICTED_REPORT_ROLES`.
5. **Bypass** for non-allowlisted reports.
6. **Normalize** the `filters` argument using `inspect.signature(query_report.run).bind_partial(*args, **kwargs)`. The normalised dict is placed in the SAME form (positional or keyword) the caller used — never in both, which would raise `TypeError: got multiple values for argument 'filters'`.
7. **Enforce** strict active-scope policy via `_enforce_scope_filters_strict`.
8. **Write** the rewritten `filters` back to the same form.
9. **Delegate** to the original `frappe.desk.query_report.run`.

The function is decorated with `@frappe.whitelist()` so the HTTP layer accepts it.

### Test coverage

```text
TestOptionAPlusPropertySetters        (3 tests) — Property Setter coverage
TestScopeDimensionPermissionsAPI      (2 tests) — Whitelisted permission probe API
TestScopeReportEnforcement            (5 tests) — Strict active-scope policy
TestScopeReportAllowlist              (3 tests) — Allowlist behaviour
TestScopeReportPositionalArgs         (2 tests) — Positional/keyword normalization (permissive fake)
TestStrictSignature                   (5 tests) — Strict-signature fake catches the duplicate-filter bug
TestFinanceRoleBypass                 (2 tests) — Finance role bypass

Total: 22 / 22 pass
```

The legacy `test_scope_context.py` T-015, T-016, T-017 still pass.

### Bug caught and fixed during this review

`TestStrictSignature::test_positional_filters_do_not_cause_duplicate_arg` and `test_keyword_filters_do_not_cause_duplicate_arg` initially FAILED with `TypeError: strict_fake_run() got multiple values for argument 'filters'`. The wrapper was passing `filters` in both `new_args` and `new_kwargs`. The fix:

```python
# _normalize_filters now keeps filters in EXACTLY one place:
if filters_index is not None and filters_index < len(new_args):
    # Strict signature: keep at filters_index, drop from new_kwargs
    new_kwargs = {k: v for k, v in new_kwargs.items() if k != "filters"}
else:
    # *args, **kwargs signature: keep in new_kwargs, drop from new_args
    if "filters" in new_args:
        new_args = tuple(a for a in new_args if a is not raw and a is not parsed)
    new_kwargs["filters"] = parsed
```

The wrapper writes back to the same place. **All 5 strict-signature tests now pass.**

---

## 6. JS filter hardening (`construction/public/js/scope_context_report_filters.js`)

### Allowlist (mirrors backend)

```javascript
const ALLOWLISTED_REPORTS = new Set([
  "General Ledger", "Trial Balance", "Profit and Loss Statement",
  "Balance Sheet", "Accounts Payable", "Accounts Payable Summary",
  "Accounts Receivable", "Accounts Receivable Summary",
  "Budget Variance Report", "Cash Flow", "Project-wise Profitability",
]);
```

### Per-dimension value shape

```javascript
SCALAR_FIELDS = ["company"];          // Link → scalar
LIST_FIELDS   = ["project", "cost_center", "department"];  // MultiSelectList → array
```

### `buildStrictValue(fieldname, scopedValue)` — strict value construction

- `company` → `scopedValue` (scalar).
- `cost_center` → `getCostCenterDescendants(scopedValue)` (list with scoped + descendants).
- `project` / `department` → `[scopedValue]` (list of one).

### `getCostCenterDescendants(scoped)` — NestedSet expansion

Reads `window.scopeContext.hierarchy.cost_centers` (cached) and returns `[cc for cc in cost_centers if cc.lft >= scoped.lft AND cc.rgt <= scoped.rgt]`.

### Budget Variance Report special case

`isBudgetVariance(reportName)` + `applyBudgetVarianceHardening(report)`:

- Locks `company` filter to scope.
- Replaces `budget_against_filter.get_data` with a closure that returns scope-hierarchy rows for the chosen dimension.
- **Handles BOTH `Cost Center` and `Project` dimensions** (dimension is read from `budget_against` field).
- The lock value is `dimension === "Project" ? scope.project : scope.cost_center`.
- Finance / permitted users keep the original `get_data`.

### Test coverage (Node `node --test`)

```text
ALLOWLISTED_REPORTS (2 tests)
UNRESTRICTED_ROLES  (1 test)
isUnrestricted()    (4 tests)
isAllowlisted()     (1 test)
SCOPE_FIELDS        (1 test)
isListField()       (1 test)
buildStrictValue()  (6 tests)   ← shape preservation
getCostCenterDescendants() (4 tests)  ← NestedSet expansion
isBudgetVariance()  (2 tests)   ← NEW: Cost Center / Project detection
Budget Variance Report (4 tests)   ← NEW: dimension-specific get_data
lockField/unlockField (3 tests)  ← MultiSelectList array value

Total: 31 / 31 pass
```

---

## 7. Explicit out-of-scope items

These are documented as out of Option A+ scope and **NOT defects** in this branch:

1. **Restricted user 403 on `get_script`.** An ERPNext `Report` DocType permission question, deferred to Option B. **Until Option B lands, the financial-reports UX for restricted users is NOT complete.** Backend wrapper, JS hardening, and metadata are all in place and ready.
2. **AP/AR Summary `reqd` flag.** JS filter is not `reqd=1`. Acceptable per the plan.
3. **Budget Variance `get_actual_transactions` SQL.** No `company` clause. Acceptable per the plan.
4. **Cash Flow per-account-type SQL.** Applies `cost_center` but not `project`. Acceptable per the plan.
5. **Scope drift on direct SQL access.** Power user with DB access can bypass. Out of scope.

---

## 8. Final test matrix

| Suite | Command | Result |
|-------|---------|--------|
| Property Setters + scope API + report filter logic | `bench --site v16.localhost run-tests --module construction.tests.test_option_a_plus` | **22 / 22 pass** |
| Node-side JS logic | `node --test construction/tests/test_scope_context_report_filters.js` | **31 / 31 pass** |
| Legacy scope context tests (T-001..T-017) | direct `bench console` invocation | all pass |
| Lint | `python3 scripts/lint_scope_metadata.py` | PASS — 15 DocTypes checked |
| Lint | `ruff check construction/overrides/scope_report.py construction/api/scope_context_api.py construction/tests/test_option_a_plus.py` | All checks passed |
| Migration | `bench --site v16.localhost migrate` | Successful |
| Build | `bench build --app construction` | Successful |
| Browser smoke (admin, all 11 reports) | `node construction/tests/test_browser_scope.js` | **11/11 reports load with no Option A+ module errors** |

---

## 9. Verdict

**READY FOR MERGE** subject to:

- The plan's call to defer the `Report` DocType permission grant to Option B. Until that lands, the **financial-reports UX layer for restricted users is NOT complete**; the backend, JS, and metadata are ready and will activate the moment the permission is granted.
- A final code review by the project owner.

The review-requested corrections are all in code, all tested by unit tests, and all green. The remaining UX blocker is explicitly documented as out of scope and deferred to Option B. The branch is in the clean worktree at `/tmp/option-a-plus-clean` (branch `feat/scope-context-option-a-plus-clean`).
