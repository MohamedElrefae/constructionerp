# Option A+ — Server-Side Scope Enforcement Audit

**Branch:** `feat/scope-context-option-a-plus`
**Audit date:** 2026-06-20
**Scope context flag:** `enable_scope_context = 1`

This document inventories every enforcement point that protects the 10 in-scope operational DocTypes and the 10 in-scope financial reports at the **server** layer.

---

## 1. Enforcement layers in use

| Layer | Module | Mechanism | What it catches |
|-------|--------|-----------|-----------------|
| L1 | `construction.overrides.scope_query.add_scope_conditions` | `permission_query_conditions` hook (wildcard `*`) | Every DatabaseQuery / Engine SELECT for any DocType — adds `company`, `cost_center` (with NestedSet children), `project`, `department` WHERE clauses derived from session defaults |
| L2 | `construction.overrides.scope_report._scope_aware_run` | Monkey-patches `frappe.desk.query_report.run` | Every Frappe query report (script reports + query reports) — rewrites `kwargs["filters"]` to intersect with user scope before delegation |
| L3 | `construction.overrides.scope_enforcement.validate` | `doc_events["*"]["validate"]` | Every INSERT/UPDATE — branch ↔ company integrity (always) + scope drift warning (when feature on) |
| L4 | `construction.services.boq_transaction_validation.validate_document` | `doc_events[<doctype>]["validate"]` for the 9 BOQ-touching DocTypes | Project ↔ BOQ structure integrity (separate concern, not scope) |

L1 + L2 are the two layers that defend the report list 403s and the financial-report 403s. L3 is independent and is out of scope for Option A+.

---

## 2. Operational DocTypes (the 10 list views)

| DocType | L1 covers list query? | L1 has scope columns? | Notes |
|---------|------------------------|------------------------|-------|
| Sales Invoice | yes | `company`, `cost_center`, `project` | Cost-center is NestedSet-expanded |
| Purchase Invoice | yes | same | same |
| Journal Entry | yes | `company`, `cost_center` only — no `project` | Project filter not added because column does not exist |
| Purchase Order | yes | same as Sales Invoice | same |
| Delivery Note | yes | `company` only on header | L1 silently skips dimensions it cannot filter on |
| Material Request | yes | `company` only on header | same caveat as Delivery Note |
| Purchase Receipt | yes | `company` only on header | same |
| Payment Entry | yes | `company` | same |
| Stock Entry | yes | `company` | same |
| Timesheet | yes | `company` only on header | L1 adds only `company` if it is in scope |

### List-view 403 root cause

The 403s reported in the field are raised by `frappe.desk.search_link` when the list view auto-opens the standard filter dropdown for `Company`. The standard filter UI is rendered by Frappe from `in_standard_filter = 1` on the DocField, which causes the list view to mount a Link field and trigger a search.

Phase 1 of the plan fixes this at metadata level (idempotent Property Setters, see audit doc §2). After `bench migrate`, all 7 flagged DocTypes show `in_standard_filter = 0` in `frappe.get_meta().get_field('company').in_standard_filter`. The list view therefore does not mount a Link filter and no search_link call is made.

For `Payment Entry`, `Stock Entry`, `Timesheet` the underlying DocField already ships with `in_standard_filter = 0` (Frappe v15/v16 default), so no override is needed.

### L1 SKIP_DOCTYPES correctness

`scope_query.SKIP_DOCTYPES` contains `Project`. This is **correct** — the Project DocType is the *browse* target, not a transaction, and skipping it lets a restricted user see their assigned projects (driven by User Permissions, not by scope_query). It does not affect transactional DocTypes.

### Test coverage for L1

`test_server_side_injection` (T-013) in `construction/tests/test_scope_context.py` covers:
- Administrator always bypasses.
- System doctype (User) is skipped.
- Doctype missing a scope column (Employee) is handled.
- Doctype with no scope columns (Country) returns `''`.
- Unscoped user gets no clauses.

---

## 3. Financial reports (the 10 report entries)

| Report | L1 covers backend? | L2 covers backend? | Status |
|--------|--------------------|--------------------|--------|
| General Ledger | partial — raw SQL bypasses hook | yes — `_enforce_scope_filters_strict` rewrites filters | **enforced at L2** |
| Trial Balance | partial | yes | **enforced at L2** |
| Profit and Loss Statement | partial | yes | **enforced at L2** |
| Balance Sheet | partial | yes | **enforced at L2** |
| Accounts Payable | partial | yes | **enforced at L2** |
| Accounts Payable Summary | partial | yes (when company in scope) | **enforced at L2** |
| Accounts Receivable | partial | yes | **enforced at L2** |
| Accounts Receivable Summary | partial | yes (when company in scope) | **enforced at L2** |
| Budget Variance Report | no — `get_actual_transactions` SQL has no `company` clause | yes | **partial at L2** |
| Cash Flow | partial | yes (cost_center only) | **partial at L2** |

### Why we rely on L2 instead of L1 for reports

ERPNext's financial reports build their result sets by composing several `frappe.db.sql` queries against `tabGL Entry`, `tabPayment Ledger Entry`, `tabAccount`, `tabBudget`, etc. The `permission_query_conditions` hook only wraps `frappe.get_all` / `frappe.db.get_list` calls. It does **not** wrap raw `frappe.db.sql` (Frappe deliberately does not parse free-form SQL). The only way to enforce scope on these reports from outside the ERPNext code is the L2 monkey-patch, which rewrites the filters dict that the report's `execute()` consumes.

L2 is the **canonical** enforcement point for reports. The wrapper is restricted to the 10 plan-specified allowlisted reports (plus `Project-wise Profitability` if installed) — non-allowlisted reports pass through unchanged.

### L2 wrapper design

The wrapper applies the following rules in order:

1. **Resolve the report name** from positional or keyword args.
2. **Bypass** if scope context is disabled.
3. **Bypass** for `Administrator`.
4. **Bypass** for users in `UNRESTRICTED_REPORT_ROLES`.
5. **Bypass** for non-allowlisted reports.
6. **Normalize** the `filters` argument via `inspect.signature(...).bind_partial`. The value is parsed if it is a JSON string and placed in the SAME form (positional or keyword) the caller used.
7. **Enforce strict active-scope policy** via `_enforce_scope_filters_strict`. The wrapper reads the value from the caller's form, rewrites it, and writes it back to the SAME form. It never puts `filters` in both `new_args` and `new_kwargs`.
8. **Delegate** to the original `frappe.desk.query_report.run`.

### Test coverage for L2

`test_report_scope_enforcement` (T-016), `test_report_scope_bypass_for_finance_role` (T-017) plus the new `TestScopeReportAllowlist`, `TestScopeReportPositionalArgs`, `TestStrictSignature`, and `TestScopeReportEnforcement` test classes in `construction/tests/test_option_a_plus.py` cover:
- Allowlist behaviour (10 reports are gated; non-allowlisted pass through).
- Positional and keyword args normalization.
- Strict-signature duplicate-filter prevention (catches the original wrapper bug).
- Strict active-scope policy (scalar company, list project/cost_center/department).
- Cost-center descendant expansion.
- Finance role bypass.

---

## 4. Outstanding enforcement risks

The following items are **partial** and are tracked for Option B / future work, **not** in Option A+:

1. **AP/AR Summary `reqd` flag.** JS filter is not `reqd=1`. A restricted user with no scope can still execute these reports and get the Global Defaults company. L2 only kicks in when company is in scope. Acceptable per the plan.
2. **Budget Variance `get_actual_transactions` SQL.** No `company` clause. L2 still rewrites the filter dict; the actual-transactions SQL joins to `tabBudget`, which is User-Permission-gated. Acceptable per the plan.
3. **Cash Flow per-account-type SQL.** Applies `cost_center` but not `project`. Acceptable per the plan.
4. **Scope drift on direct SQL access.** A power user with database access can bypass L1. Out of scope for Option A+.

---

## 5. Conclusion

All 10 list views and all 10 reports are protected by at least one server-side layer. Partial cases are inherent to the ERPNext engine and are accepted by Option A+.
