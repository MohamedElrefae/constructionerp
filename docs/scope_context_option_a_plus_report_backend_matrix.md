# Option A+ — Report Filter / Backend Matrix

**Branch:** `feat/scope-context-option-a-plus`
**Audit date:** 2026-06-20
**Source files:** `apps/erpnext/erpnext/accounts/report/<report>/<report>.{js,py}`

This is the matrix the Option A+ plan requires before any report UI changes. It is the source of truth for whether each report needs UI hardening and what its server-side filter contract is.

---

## 1. Master matrix

| # | Report | company filter (JS) | project filter (JS) | cost_center filter (JS) | account filter (JS) | Backend scope status | UI action for restricted user |
|---|--------|-----------|------------|----------------|------------|----------------------|--------------------------------|
| 1 | General Ledger | Link / Company, reqd | MultiSelectList / Project | MultiSelectList / Cost Center | MultiSelectList / Account | **enforced** (L2 rewrites all 3 + dims) | lock Link company + MultiSelectList project/cost_center; pre-fill from scope |
| 2 | Trial Balance | Link / Company, reqd | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | **enforced** | same as #1 |
| 3 | Profit and Loss Statement | Link / Company, reqd (shared) | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | **enforced** | same as #1 |
| 4 | Balance Sheet | Link / Company, reqd (shared) | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | **enforced** | same as #1 |
| 5 | Accounts Payable | Link / Company, reqd | MultiSelectList / Project | MultiSelectList / Cost Center | `party_account` Link / Account | **enforced** | same as #1; do not touch `party_account` (User Permission handles it) |
| 6 | Accounts Payable Summary | Link / Company, **not reqd** | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | **partial** (L2 needs company in scope) | same as #1; L2 will inject scope.company if missing |
| 7 | Accounts Receivable | Link / Company, reqd | MultiSelectList / Project | MultiSelectList / Cost Center | `party_account` Link / Account | **enforced** | same as #1 |
| 8 | Accounts Receivable Summary | Link / Company, **not reqd** | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | **partial** | same as #1 |
| 9 | Budget Variance Report | Link / Company, reqd | n/a (uses `budget_against` Select defaulting to "Cost Center" + `budget_against_filter` MultiSelectList; `get_data` does **not** pass company) | same — selected via `budget_against` | n/a | **partial** (L2 rewrites `filters.company` and `filters.budget_against_filter`) | lock `company`; replace `budget_against_filter.get_data` with scope hierarchy data |
| 10 | Cash Flow | Link / Company, reqd (shared) | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | **partial** (L2 rewrites; per-account-type SQL applies `cost_center` only) | same as #1 |
| 11 | Project-wise Profitability | Link / Company, reqd | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | **enforced** if installed | same as #1 |

---

## 2. Filter value shapes

All four critical dimensions are **list-shaped** when they reach the Python `execute()`:

- `company` is a **string** (Link field → scalar).
- `project`, `cost_center`, `account` are **lists** (MultiSelectList → `frappe.parse_json`).
- `budget_against_filter` is a **list** of dimension values.

L2 (`scope_report._enforce_scope_filters_strict`) handles both shapes:

```python
if scoped_value:
    if dimension == "cost_center":
        # Build list of [scoped, ...descendants via lft/rgt]
        return descendants
    elif dimension == "company":
        return scoped_value  # scalar
    else:
        return [scoped_value]  # list
```

**The UI must not change the shape** — converting a MultiSelectList to a plain `Data` field would break the report's `.isin(filters.cost_center)` clauses and cause silent data loss.

---

## 3. Reports that fire `get_link_options` on open

All 10 reports fire `frappe.db.get_link_options(...)` against one or more dimension DocTypes the moment the filter row is mounted. The UI hardening module prevents the input from being focusable/clickable, which stops the auto-fetch and therefore eliminates the 403.

| Report | Account | Project | Cost Center | Party | party_account |
|--------|---------|---------|-------------|-------|----------------|
| General Ledger | yes | yes | yes | yes (when party_type set) | n/a |
| Trial Balance | n/a | yes | yes | n/a | n/a |
| Profit and Loss Statement | n/a | yes | yes | n/a | n/a |
| Balance Sheet | n/a | yes | yes | n/a | n/a |
| Accounts Payable | n/a | yes | yes | yes | yes |
| Accounts Payable Summary | n/a | yes | yes | yes | n/a |
| Accounts Receivable | n/a | yes | yes | yes | yes |
| Accounts Receivable Summary | n/a | yes | yes | yes | n/a |
| Budget Variance Report | n/a | n/a (dynamic) | n/a (dynamic) | n/a | n/a |
| Cash Flow | n/a | yes | yes | n/a | n/a |

**Budget Variance Report is special**: the dimension is dynamic via `budget_against`. When set to "Cost Center" or "Project", `get_data` fires `get_link_options` against that DocType **without** passing the company argument. The JS hardening module replaces `get_data` with scope-hierarchy rows when the user cannot read the dimension.

---

## 4. UI hardening rules per dimension

### Company (Link)

- Restricted user: `field.df.read_only = 1`, DOM disabled, value forced to `scope.company`.
- Finance / permitted user: Link unchanged, default from scope, may select another Company.

### Project (MultiSelectList)

- Restricted user: list value shape preserved, value forced to `[scope.project]`, input disabled.
- Finance user: MultiSelectList unchanged, optional pre-fill.

### Cost Center (MultiSelectList)

- Restricted user: list value shape preserved, value forced to `getCostCenterDescendants(scope.cost_center)`, input disabled.
- Finance user: MultiSelectList unchanged, optional pre-fill.

### Account (MultiSelectList, GL only)

- Restricted user: list value shape preserved, pre-filtered to scoped company's chart of accounts, input disabled.
- Finance user: MultiSelectList unchanged.

### `budget_against_filter` (Budget Variance Report only)

- Restricted user: replace `get_data` with closure over scope hierarchy rows, lock filter.
- Finance user: keep original `get_data`, optional pre-fill.

---

## 5. Server-side fallback per report

L2 already rewrites the filter dict for **all** report executions. This is the safety net behind the UI hardening. Even if a restricted user manages to set a value via devtools, L2 intersects it with the allowed hierarchy and falls back to the active scope.

Reports with raw `frappe.db.sql` blocks (Budget Variance Report, Cash Flow) get a partial L2 contract — see `scope_context_option_a_plus_server_enforcement.md` §4. These are accepted as residual risk in Option A+.

---

## 6. Acceptance criteria for "report is done"

A report is considered hardened iff **all** are true:

- [x] The report name is in the JS allowlist (`ALLOWLISTED_REPORTS` in `scope_context_report_filters.js`).
- [x] For a restricted user, the Link `company` filter and the MultiSelectList `project` / `cost_center` filters are locked and disabled in the DOM.
- [x] The filter value shape is preserved (no Data ↔ MultiSelectList conversion).
- [x] For a finance user, the original Link / MultiSelectList behavior is preserved.
- [x] L2 (`_enforce_scope_filters_strict`) intersects submitted filter values with the allowed hierarchy.
- [x] A test asserts that a restricted user with a non-allowed project gets the project cleared/forced to the scope value.
