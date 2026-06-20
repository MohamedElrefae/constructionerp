# Option A+ — Baseline Audit

**Branch:** `feat/scope-context-option-a-plus`
**Date:** 2026-06-20
**Site:** `v16.localhost`
**Scope context flag:** `enable_scope_context = 1` (already on)

This document records the state of the workspace before any Option A+ work was started on the new branch. It is intentionally a snapshot — anything marked **DONE** here was already merged on the `feat/edge-typography-fix-v16` base and is being verified, not newly introduced.

---

## 1. Branch state at start

```text
branch:   feat/scope-context-option-a-plus (new)
base:     feat/edge-typography-fix-v16 @ 087f185
unrelated dirty files (BOQ + theme work — kept untouched):
  construction/api/boq_api.py
  construction/api/boq_link_queries.py
  construction/api/scope_context_api.py
  construction/construction/doctype/boq_*/** (multiple)
  construction/public/css/theme_*.css
  construction/public/js/scope_context.js
  construction/public/js/boq_filters.js
  construction/public/js/overrides/ct_link_control.js
  construction/public/js/vfc_layout_engine.js
  construction/patches/v6_0/set_default_new_theme_fields.py
  construction/patches/v7_0_migrate_quantity_revisions.py
  construction/scratch_test.py
```

These dirty files are **out of scope** for Option A+ and are not modified by this workstream.

---

## 2. Operational DocType metadata (in_standard_filter)

Captured live from `frappe.get_meta()` + `tabProperty Setter`:

| DocType           | Field    | Fieldtype | Options  | `in_standard_filter` (meta) | Property Setter value | Action        |
|-------------------|----------|-----------|----------|-----------------------------|------------------------|---------------|
| Sales Invoice     | company  | Link      | Company  | 0                           | 0                      | already hidden |
| Purchase Invoice  | company  | Link      | Company  | 0                           | 0                      | already hidden |
| Journal Entry     | company  | Link      | Company  | 0                           | 0                      | already hidden |
| Purchase Order    | company  | Link      | Company  | 0                           | 0                      | already hidden |
| Delivery Note     | company  | Link      | Company  | 0                           | 0                      | already hidden |
| Material Request  | company  | Link      | Company  | 0                           | 0                      | already hidden |
| Purchase Receipt  | company  | Link      | Company  | 0                           | 0                      | already hidden |
| Payment Entry     | company  | Link      | Company  | 0                           | — (no PS — native)     | already hidden |
| Stock Entry       | company  | Link      | Company  | 0                           | — (no PS — native)     | already hidden |
| Timesheet         | company  | Link      | Company  | 0                           | — (no PS — native)     | already hidden |

**Conclusion:** Phase 1 (Property Setters for the 7 flagged ERPNext operational DocTypes) is already in place from commit `b891518`. The idempotent helper at `construction/patches/v7_2/set_erpnext_standard_filters.py` is wired into both `after_install` and `after_migrate` in `construction/hooks.py`. Patch is registered in `patches.txt`.

The plan calls for the patch at `v6_8/set_erpnext_scope_standard_filter_property_setters.py`. The shipped patch is at `v7_2/set_erpnext_standard_filters.py`. The semantics are identical (idempotent, DocField-typed, value="0", same 7 doctypes). This branch does **not** rename the path because the patch is already shipped on the base.

---

## 3. Property Setter count for the 7 flagged DocTypes

Live count after the helper has run (the live site was migrated post-`b891518`):

- 7 records, one per flagged DocType × `company.in_standard_filter = 0`.
- No conflicting `in_standard_filter` Property Setters found on `Payment Entry`, `Stock Entry`, `Timesheet`. Their `in_standard_filter = 0` resolves from the underlying DocField JSON (Frappe ships them this way for v15/v16), so no override is required.

---

## 4. Financial report filter + backend matrix

Source: live read of `apps/erpnext/erpnext/accounts/report/<report>/<report>.{js,py}`. Verbatim from the audit run on this branch.

| # | Report | Company filter (JS) | Project filter (JS) | Cost Center filter (JS) | Account filter (JS) | JS uses get_link_options for… | Backend requires company | Backend applies project / cost_center filters to SQL? | Filter value shape | Backend scope status |
|---|--------|-----------|------------|----------------|------------|------------------------------|--------------------------|----------------------------------------|--------------------|----------------------|
| 1 | General Ledger | Link / Company, reqd | MultiSelectList / Project | MultiSelectList / Cost Center | MultiSelectList / Account | Account, Project, Cost Center, Party | Yes (`validate_filters`) | Yes (`get_conditions` + `apply_additional_conditions`) | List | **enforced** |
| 2 | Trial Balance | Link / Company, reqd | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | Project, Cost Center | Implicit (`reqd=1` JS) | Yes (opening balance + GL aggregation) | List | **enforced** |
| 3 | Profit and Loss Statement | Link / Company, reqd (shared) | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | Project, Cost Center (+ dims) | Implicit | Yes (shared engine) | List | **enforced** |
| 4 | Balance Sheet | Link / Company, reqd (shared) | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | Project, Cost Center (+ dims) | Implicit | Yes (shared engine) | List | **enforced** |
| 5 | Accounts Payable | Link / Company, reqd | MultiSelectList / Project | MultiSelectList / Cost Center | `party_account` Link / Account | Project, Cost Center, Party, party_account | Indirect | Yes (`prepare_conditions`) | List | **enforced** |
| 6 | Accounts Payable Summary | Link / Company, **not reqd** | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | Project, Cost Center, Party | No (Global Defaults fallback) | Yes when present | List | **partial** |
| 7 | Accounts Receivable | Link / Company, reqd | MultiSelectList / Project | MultiSelectList / Cost Center | `party_account` Link / Account | Project, Cost Center, Party, party_account | Indirect | Yes (`prepare_conditions`) | List | **enforced** |
| 8 | Accounts Receivable Summary | Link / Company, **not reqd** | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | Project, Cost Center, Party, etc. | No (Global Defaults fallback) | Yes when present | List | **partial** |
| 9 | Budget Variance Report | Link / Company, reqd | n/a (uses `budget_against`) | n/a (chosen via `budget_against`) | n/a | `budget_against_filter` (NO company arg) | Implicit | **Partial** — dimension enforced; actual-transactions SQL has no `company=` clause | List | **partial** |
| 10 | Cash Flow | Link / Company, reqd (shared) | MultiSelectList / Project | MultiSelectList / Cost Center | n/a | Project, Cost Center (+ dims) | Implicit | **Partial** — shared engine applies; per-account-type SQL applies `cost_center` only | List | **partial** |

### Reports that fire `get_link_options` on open

All 10 reports fire `frappe.db.get_link_options(...)` against one or more dimension DocTypes the moment the filter row is mounted. For a restricted user without `read` on these DocTypes this raises a 403 in the network panel. The UI hardening module **prevents the input from being focusable/clickable**, which stops the auto-fetch and therefore eliminates the 403.

---

## 5. Custom Construction reports (Phase 6 input)

A search of `construction/` for any module that calls `frappe.query_reports` or defines a custom report returns **no matches outside the scope override itself**:

```text
construction/overrides/scope_report.py  (the enforcement wrapper, not a report)
```

The only Construction user-facing reports are Frappe built-ins (e.g. "Construction Settings" not being a report) plus the per-Doctype operational list views. **No new Construction custom reports** require allowlisting. The construction app's `add_dimensions` calls only add accounting-dimension filters, not new report modules.

---

## 6. Restricted roles used for testing

For Phase 8 (browser verification) and Phase 7 tests we use:

- `test_scope@example.com` — exists in `User Scope Context` tests; has no role assignment, therefore bypasses no scope rule but triggers all restricted-user 403s.
- `test_user2@example.com` — same. Scope is set programmatically.
- A "Site Engineer" role user (created fresh) with no read on `Company`/`Project`/`Cost Center` — this is the production-shape restricted user.
- An "Accounts Manager" user (created fresh) for the finance regression scenario.

All four are idempotent — created if missing, removed at teardown.

---

## 7. Summary of pre-existing work reused

| Plan phase | Status at start of this branch | Action on this branch |
|------------|--------------------------------|------------------------|
| Phase 1 — Property Setters | **DONE** (commit `b891518`, patch `v7_2/set_erpnext_standard_filters.py`) | verify, add doc, do not regress |
| Phase 4 — Report filter JS | **DONE** (commit `b891518`, `scope_context_report_filters.js`) | allowlist the 10 reports; harden MultiSelectList to scope hierarchy |
| Phase 5 — Report backend scope | **PARTIAL** (commit `b891518` added monkeypatch of `frappe.desk.query_report.run`) | verify per-report; document partial reports; do not regress |
| Phase 7 — Tests | **PARTIAL** (T-015, T-016, T-017 exist in `test_scope_context.py`) | add per-report filter tests + finance bypass coverage |
| Phase 9 — Docs | **MISSING** (no `option_a_plus_audit.md`) | write this doc + execution log |
| Phase 8 — Browser verification | **MISSING** | schedule restricted + finance user walkthrough |
