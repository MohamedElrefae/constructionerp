# Option A+ — Browser Verification

**Branch:** `feat/scope-context-option-a-plus`
**Date:** 2026-06-20
**Site:** `v16.localhost` (developer mode)
**Scope context flag:** `enable_scope_context = 1`

This document is the manual verification procedure for the Option A+ plan. The pure-logic checks are covered by the unit / integration tests in `construction/tests/test_option_a_plus.py` (22 tests, all passing) and `construction/tests/test_scope_context_report_filters.js` (25 tests, all passing). The Playwright smoke test in `construction/tests/test_browser_scope.js` covers loading all 11 allowlisted reports as Administrator.

---

## 1. Status (evidence-based)

| Item | Status | Evidence |
|------|--------|----------|
| **All 11** allowlisted reports loaded in headless Chromium smoke test | **DONE** | `test_browser_scope.js` tests all 11; output below |
| Zero console errors from construction module on any of the 11 | **DONE** | smoke test assertion `console errors=0` per report (filtered to construction-only errors; pre-existing Frappe dev-server errors ignored) |
| Restricted user 403 on `get_script` for Report DocType | **NOT DONE** (out of Option A+ scope, deferred to Option B) | see §3 below |
| Full restricted-user UAT | **NOT DONE** (out of Option A+ scope, deferred to Option B) | depends on Report DocType permission grant (Option B) |

### Smoke test results (all 11 reports)

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

---

## 2. Required users

| Role | Email | Permissions | Purpose |
|------|-------|-------------|---------|
| Administrator | `Administrator` | all | bypasses scope enforcement, used to confirm finance user behaviour |
| Restricted user | `site.engineer@example.com` | no read on Company / Project / Cost Center / Account | confirm 403 elimination — REQUIRES OPTION B grant |
| Finance user | `accounts.manager@example.com` | Accounts Manager role, read on all four dimensions | confirm regression-free finance UX |

The restricted and finance users are not created by the patch — they are created on demand by the operator following the steps below.

---

## 3. Restricted user 403 — root cause and resolution

When a Site-Engineer-equivalent user (no `read` on `Report` DocType) opens a financial report, Frappe's JS pre-fetches the report's Python script via `frappe.desk.query_report.get_script`. This call returns **403 PermissionError** because the user lacks `read` on the `Report` DocType for the specific report.

**Why Option A+ does not fix this:**
Option A+ assumes the user already has read on the `Report` DocType. Granting this is an ERPNext-level permission change, deferred to Option B. The L2 wrapper (`scope_report.py`) IS invoked once the report is loaded; the JS pre-fetch 403 happens BEFORE the L2 wrapper is reached.

**Resolution path (Option B):**
Grant `read` on the 11 allowlisted `Report` DocTypes to the restricted user role. This can be done by:
- Adding `Report` read to the `Site Engineer` role.
- Or: adding a `Custom DocPerm` row for each allowlisted Report.
- Or: per-user `User Permission` records.

The implementation of Option B is out of scope for this branch. **Until Option B is implemented, the "zero 403 for restricted user on financial reports" UX goal is NOT achieved.** The backend wrapper, the JS hardening, and the metadata are all in place — they activate the moment the restricted user can load the report.

---

## 4. Operator procedure (for Option B UAT, when Report perm is granted)

1. `cd /home/mohamed/frappe-bench && bench serve --noreload --port 8000 &` (in a separate terminal).
2. `bench --site v16.localhost set-admin-password test123`.
3. Grant `Report` read perm to the restricted user role.
4. Create the test users (admin session):
   - `site.engineer@example.com` with no special roles.
   - `accounts.manager@example.com` with `Accounts Manager` and `Accounts User` roles.
5. Set scope context for each user (admin calls `construction.api.scope_context_api.set_scope_context` on their behalf).
6. Open each of the 11 allowlisted reports in the restricted user's browser.
7. Capture network panel for 403s.
8. Open the same 11 reports in the finance user's browser.
9. Capture evidence in `docs/evidence/option_a_plus/<date>/`.

---

## 5. Rollback

### Property Setters

```python
# bench --site v16.localhost console
from construction.patches.v7_2.set_erpnext_standard_filters import _ensure_property_setter
for dt in ["Sales Invoice", "Purchase Invoice", "Journal Entry",
           "Purchase Order", "Delivery Note", "Material Request",
           "Purchase Receipt"]:
    _ensure_property_setter(dt, "company", "in_standard_filter", 1)
frappe.clear_cache()
frappe.db.commit()
```

### Report filter JS

Revert `construction/public/js/scope_context_report_filters.js` to the pre-Option-A+ version (the one in `feat/edge-typography-fix-v16` commit `b891518`).

### Report backend wrapper

Disable the monkey-patch by setting `enable_scope_context = 0` on `Construction Settings`. The wrapper in `construction/overrides/scope_report.py` short-circuits when the flag is off.

### Tests

Re-run targeted tests to confirm rollback:

```bash
bench --site v16.localhost run-tests --module construction.tests.test_option_a_plus
node --test construction/tests/test_scope_context_report_filters.js
```
