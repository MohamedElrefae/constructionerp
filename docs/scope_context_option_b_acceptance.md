# Option B — Final Acceptance Checklist (Evidence-Backed, v3)

**Branch:** `feat/scope-context-option-a-plus-clean` (clean worktree at `/tmp/option-a-plus-clean`)
**Built on top of:** `3afc78b feat(scope): Option A+ backend and report-filter hardening`
**Last updated:** 2026-06-20
**Status:** All review-requested changes applied across v1 → v2 → v3. 50/50 backend tests pass + 31/31 Node tests pass + ruff clean. Restricted-user UAT shows 10/10 installed allowlisted reports load with **zero 403s** and real scope-filtered data. Project-wise Profitability returns 404 (not installed).

---

## 1. Review history

| Version | Commit | Reviewer verdict | Action |
|---------|--------|------------------|--------|
| v1 | `d031d58` | **Request changes** — bypass too broad (boolean flag, doctype-agnostic, get_report_doc left flag set, no negative tests as restricted user). | Reverted. |
| v2 | `87fdc8a` | **Request changes** — v2 narrowing was correct, but `get_report_doc` still set the flag and left it active for the rest of the request (the `get_script` path doesn't go through `_scope_aware_run`, so the flag was never cleared). | Reverted. |
| v3 | (this commit) | **Awaiting review** | — |

---

## 2. v3 changes vs v2

| # | Finding (v2) | Fix in v3 | Evidence |
|---|--------------|-----------|----------|
| 1 | **P0**: `_scope_aware_get_report_doc()` called `set_bypass_context(...)` and returned the doc without clearing the flag. For the `get_script` path (which doesn't go through `_scope_aware_run`), the flag would remain active for the rest of the request, allowing stale-flag perm grants via any subsequent `has_permission` / `get_role_permissions` call. | `get_report_doc` no longer sets the flag. The bypass path simply returns the doc. Only `_scope_aware_run` (the `run` path) sets the flag, in `try/finally` that always clears it. | `scope_report.py:351–364` (simplified bypass path) |
| 2 | **P0 regression test**: The existing `test_flag_cleared_after_get_report_doc_finally` only tested `clear_bypass_context()` directly, not the actual `get_report_doc()` behavior. | New `test_get_report_doc_does_not_set_bypass_flag`: calls `get_report_doc("General Ledger")` as the restricted user, asserts the flag is NOT set, then asserts `has_permission("Project", "read")` returns False. | `test_option_a_plus.py:test_get_report_doc_does_not_set_bypass_flag` |
| 3 | **Cleanup**: Duplicate definition of `_is_allowlisted_report_for_user()` in `scope_report.py`. | Removed the second copy. | `scope_report.py:495` (single definition) |

---

## 3. Design — the single signal

The bypass is a structured dict:

```python
frappe.flags.scope_report_bypass = {
    "report_name": "General Ledger",   # must be in ALLOWED_REPORTS
    "user": "test_user2@example.com",   # must match session.user
}
```

The flag is set in **exactly one place**: inside `_scope_aware_run`'s `try/finally`, only when the report is allowlisted AND the user has an active scope. The flag is cleared in the matching `finally` block.

`_bypass_context()` reads the flag and validates every condition on every call:

1. Flag is a dict (not a boolean, not None).
2. `report_name` is in `ALLOWED_REPORTS`.
3. `user` matches `frappe.session.user` (no cross-user leak).
4. The user still has an active scope context (defense in depth).

If any condition fails, the bypass is refused and Frappe's normal perm logic runs.

`_bypass_should_apply(...)` then validates additional per-call conditions:

- `report_name` (if provided) matches the caller's report.
- `user` (if provided) matches the caller's user.
- `ptype` (if provided) is in `_ALLOWED_PTYPES = {"report", "select", "read"}`.

`doctype` is NOT a gate: the bypass is **report-scoped**, not doctype-scoped. A report's SQL builder may query multiple secondary doctypes (e.g. AP queries Purchase Invoice, GL Entry, Journal Entry), and the data is constrained by the L1+L2 wrappers.

---

## 4. Where the flag is set vs cleared

| Code path | Sets flag? | Clears flag? |
|-----------|-----------|--------------|
| `get_report_doc("General Ledger")` (used by `get_script`) | **NO** (v3 fix) | N/A |
| `_scope_aware_run(...)` (used by `run`) | YES (in `try`) | YES (in `finally`) |
| `get_doc_permissions` (called internally by `has_permission` after a non-bypass result) | NO | N/A |
| Any other code | NO | N/A |

Because `get_report_doc` does NOT set the flag, the `get_script` path can never leave a stale flag. The only path that sets the flag is `_scope_aware_run`, which is wrapped in `try/finally` and always clears it.

---

## 5. Files changed (Option B v3)

```text
$ cd /tmp/option-a-plus-clean
$ git status --short
 M construction/overrides/scope_report.py      (Option B patches: structured flag, narrowed)
 M construction/tests/test_option_a_plus.py    (Option B tests + regression test)

$ git diff --stat
 construction/overrides/scope_report.py   | 350 ++++++++++++++++++++++++++-
 construction/tests/test_option_a_plus.py | 430 ++++++++++++++++++++++++++++-
 2 files changed, ~775 insertions, ~5 deletions
```

No changes to:
- `construction/api/scope_context_api.py` (Option A+)
- `construction/public/js/scope_context_report_filters.js` (Option A+ JS hardening)
- Any `hooks.py`, `construction_settings.json`, or other metadata file
- Any ERPNext / Frappe core file

---

## 6. Test coverage — 50/50 pass

### 6.1 `TestOptionBReportAccessGate` — 25 tests (all pass)

```text
TestOptionBReportAccessGate
  ✔ test_user_has_active_scope_context_returns_true_with_scope
  ✔ test_user_has_active_scope_context_returns_false_without_scope
  ✔ test_user_has_active_scope_context_returns_false_for_admin
  ✔ test_user_has_active_scope_context_returns_false_when_flag_off
  ✔ test_report_is_permitted_bypassed_for_allowlisted_with_scope
  ✔ test_report_is_permitted_not_bypassed_without_scope
  ✔ test_report_is_permitted_not_bypassed_for_non_allowlisted
  ✔ test_get_report_doc_bypassed_for_allowlisted_with_scope
  ✔ test_get_report_doc_not_bypassed_without_scope
  ✔ test_get_report_doc_not_bypassed_for_non_allowlisted_without_scope
  ✔ test_get_report_doc_does_not_set_bypass_flag  ← v3 regression test
  ✔ test_has_permission_bypassed_for_report_perm
  ✔ test_has_permission_bypassed_for_select_perm
  ✔ test_has_permission_bypassed_for_read_perm
  ✔ test_has_permission_bypassed_for_secondary_doctype_select
  ✔ test_has_permission_not_bypassed_without_flag
  ✔ test_has_permission_not_bypassed_for_disallowed_ptype
  ✔ test_has_permission_not_bypassed_for_unrelated_ptype_on_secondary_doctype
  ✔ test_has_permission_not_bypassed_for_cross_user_leak
  ✔ test_has_permission_not_bypassed_with_bool_flag
  ✔ test_has_permission_not_bypassed_when_scope_cleared
  ✔ test_has_permission_not_bypassed_for_non_allowlisted_report
  ✔ test_get_role_permissions_bypassed_with_scope
  ✔ test_get_role_permissions_overrides_only_allowlisted_ptypes
  ✔ test_get_permitted_fields_bypassed_with_scope
  ✔ test_get_permitted_fields_bypassed_for_secondary_doctype
```

The v3 regression test is the critical addition: it proves that `get_report_doc("General Ledger")` as a restricted user returns the doc without leaving the bypass flag set, and that the very next `has_permission("Project", "read")` correctly returns False (no stale-flag perm grant).

### 6.2 Full test module — 50 / 50 pass

```text
TestOptionAPlusPropertySetters        (3 tests)
TestScopeDimensionPermissionsAPI      (2 tests)
TestScopeReportEnforcement            (5 tests)
TestScopeReportAllowlist              (3 tests)
TestScopeReportPositionalArgs         (2 tests)
TestStrictSignature                   (7 tests)
TestFinanceRoleBypass                 (2 tests)
TestOptionBReportAccessGate          (25 tests)  ← Option B v3

Total: 50 / 50 pass
```

### 6.3 Node tests — 31 / 31 pass

`construction/tests/test_scope_context_report_filters.js` — unchanged by Option B, all 31 pass.

### 6.4 Ruff clean

```text
$ ruff check construction/overrides/scope_report.py construction/tests/test_option_a_plus.py
All checks passed!
```

---

## 7. Browser UAT — restricted user (site.engineer.ob@example.com)

Test script: `/tmp/opencode/test_option_b_uat.js`

```text
=== Option B UAT: restricted user (site.engineer.ob) ===
  enabled_scope_context: 1
  active scope: Elrefae / Main - E

  OK General Ledger: get_script=200, run=200, rows=4
  OK Trial Balance: get_script=200, run=200, rows=1
  OK Profit and Loss Statement: get_script=200, run=200, rows=0
  OK Balance Sheet: get_script=200, run=200, rows=0
  OK Accounts Payable: get_script=200, run=200, rows=0
  OK Accounts Payable Summary: get_script=200, run=200, rows=0
  OK Accounts Receivable: get_script=200, run=200, rows=0
  OK Accounts Receivable Summary: get_script=200, run=200, rows=0
  OK Budget Variance Report: get_script=200, run=200, rows=0
  OK Cash Flow: get_script=200, run=200, rows=17
  FAIL Project-wise Profitability: get_script=404, run=404, rows=?
    (Report not installed in this DB — not a permission issue)

Results: 10 passed, 1 failed (of 11)
```

### Analysis

- **All 10 installed allowlisted reports**: `get_script=200` (no 403), `run=200` (report ran, no permission error).
- **Real data returned**: GL=4, TB=1, CF=17 rows; P&L/BS/AP/AR/BV=0 rows (no matching data in scope).
- **Project-wise Profitability**: 404 (not installed, not a perm issue).
- **Zero 403s** anywhere in the UAT.

---

## 8. Acceptance

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Restricted user can open all 10 installed allowlisted reports | **PASS** | UAT shows 10/10 with `get_script=200` |
| Zero 403s for restricted user on allowlisted reports | **PASS** | UAT shows no 403 status codes |
| Real scope-filtered data returned | **PASS** | GL=4 rows, TB=1, CF=17 |
| `get_report_doc` does NOT set the bypass flag | **PASS** | `test_get_report_doc_does_not_set_bypass_flag` |
| `has_permission("Project", "read")` returns False after `get_report_doc` | **PASS** | `test_get_report_doc_does_not_set_bypass_flag` (assertion) |
| Non-allowlisted reports unaffected | **PASS** | `test_report_is_permitted_not_bypassed_for_non_allowlisted`, `test_has_permission_not_bypassed_for_non_allowlisted_report` |
| Unscoped users unaffected | **PASS** | `test_get_report_doc_not_bypassed_without_scope`, `test_user_has_active_scope_context_returns_false_without_scope`, `test_has_permission_not_bypassed_when_scope_cleared` |
| Administrator unaffected (still bypasses) | **PASS** | `_user_has_active_scope_context` returns False for Administrator |
| Flag-off state unaffected | **PASS** | `test_user_has_active_scope_context_returns_false_when_flag_off` |
| Cross-user flag is refused | **PASS** | `test_has_permission_not_bypassed_for_cross_user_leak` |
| Boolean flag is refused | **PASS** | `test_has_permission_not_bypassed_with_bool_flag` |
| Non-allowlisted report in flag is refused | **PASS** | `test_has_permission_not_bypassed_for_non_allowlisted_report` |
| Non-allowlisted ptype (write/delete) is refused | **PASS** | `test_has_permission_not_bypassed_for_disallowed_ptype`, `test_has_permission_not_bypassed_for_unrelated_ptype_on_secondary_doctype` |
| All 4 access-gate functions patched | **PASS** | `is_permitted`, `get_report_doc`, `has_permission`, `get_role_permissions`, `get_permitted_fields` |
| `frappe.flags.scope_report_bypass` only set in `_scope_aware_run` | **PASS** | `scope_report.py:_scope_aware_run`; L2 wrapper `try/finally`; v3 regression test |
| No changes to ERPNext/Frappe core | **PASS** | Only `construction/overrides/scope_report.py` is modified |
| All 50 backend tests pass | **PASS** | `bench run-tests` shows 50/50 OK |
| All 31 Node tests pass | **PASS** | `node test_scope_context_report_filters.js` shows 31/31 |
| Ruff clean | **PASS** | `ruff check` shows All checks passed |
| Clean worktree isolation | **PASS** | Only 2 source files changed in `/tmp/option-a-plus-clean` |
| No duplicate function definitions | **PASS** | `_is_allowlisted_report_for_user` defined once |

---

## 9. Rollback

Revert the two-file diff:

```bash
cd /tmp/option-a-plus-clean
git checkout 3afc78b -- construction/overrides/scope_report.py construction/tests/test_option_a_plus.py
```

This restores the Option A+ state.

---

## 10. Followups (out of scope for this delivery)

1. **Project-wise Profitability report** is not installed. If it needs to be enabled, add the report JSON and re-run UAT.
2. **Admin Settings page** should expose "Allow restricted users to open allowlisted reports" so admins can toggle Option B without direct DB access.
3. **Audit log** should record when a restricted user opens a financial report.

These are deferred to a future sprint.
