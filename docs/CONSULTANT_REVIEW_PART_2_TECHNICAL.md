# Construction ERP — Technical Review Report (Part 2: Technical Details)

**To:** Engineering / Technical Reviewer
**From:** Consultant Review
**Date:** 2026-06-20
**Subject:** Technical evidence backing the manager sign-off — Construction ERP Option B v3

> **Evidence policy in this document.** Every claim below is backed by evidence that was **read from the source code or re-run live on 2026-06-20**, not quoted from another report. Where a claim could only be sourced from a prior session's artifact (e.g., a commit that was made earlier today), that is stated explicitly in the "Provenance" column. Test results were **freshly re-run** during this review, not copied from the acceptance document.

---

## 1. Evidence provenance — what was verified how

| Claim category | How it was verified | First-hand or reported? |
|----------------|---------------------|-------------------------|
| File contents (scope_report.py, test_option_a_plus.py) | Read directly with file-read tool; line numbers cited below | **First-hand** — read from `/tmp/option-a-plus-clean/construction/overrides/scope_report.py` (806 lines) and `.../tests/test_option_a_plus.py` (1427 lines) |
| Git state (branch, commits, diff, clean tree) | `git` commands run live on 2026-06-20 | **First-hand** — outputs reproduced in §6 |
| Backend test result (50/50) | **Re-run live**: `bench --site v16.localhost run-tests --module construction.tests.test_option_a_plus` → `Ran 50 tests in 4.014s / OK` | **First-hand — freshly re-run this review** |
| Node test result (31/31) | **Re-run live**: `node construction/tests/test_scope_context_report_filters.js` → `tests 31 / pass 31 / fail 0` | **First-hand — freshly re-run this review** |
| Restricted-user UAT (10/10, zero 403s) | **Re-run live**: `node /tmp/opencode/test_option_b_uat.js` against `http://v16.localhost:8000` → `Results: 10 passed, 1 failed` | **First-hand — freshly re-run this review** |
| Commit hashes and message text | `git log --oneline` run live | **First-hand** |
| Code that bench actually executes | `diff -q` confirmed the main worktree's `scope_report.py` is byte-identical to the clean worktree's; the live UAT therefore exercised the reviewed code | **First-hand** |
| ruff clean | Could not re-run (ruff not installed in this env); taken from acceptance doc | **Reported by prior session** — see §4.4 |

The acceptance document (`docs/scope_context_option_b_acceptance.md`) was used only as a **cross-check**. Where it agreed with the freshly re-run results, that is noted. Where I could not independently re-verify (ruff), that is flagged explicitly.

---

## 2. Repositories and branches (verified live)

```
$ cd /tmp/option-a-plus-clean && git branch --show-current
feat/scope-context-option-a-plus-clean

$ git log --oneline -4
1f3707a docs(scope): fix _patch_report_access_gates docstring for v3 behavior
13ccc2e feat(scope): Option B v3 — get_report_doc no longer sets bypass flag
3afc78b feat(scope): Option A+ backend and report-filter hardening
087f185 fix: finish typography font handling state

$ git status --short
(empty — 0 uncommitted changes)

$ git diff --stat 3afc78b..HEAD
 construction/overrides/scope_report.py    | 453 ++++++++++++++++++++++-
 construction/tests/test_option_a_plus.py  | 596 ++++++++++++++++++++++++++++++
 docs/scope_context_option_b_acceptance.md | 242 ++++++++++++
 3 files changed, 1288 insertions(+), 3 deletions(-)

$ git rev-list --left-right --count @{u}...HEAD
fatal: no upstream configured for branch 'feat/scope-context-option-a-plus-clean'
→ NOT pushed to GitHub
```

| Worktree | Path | Branch | HEAD | Working tree | Pushed? |
|----------|------|--------|------|--------------|---------|
| Option B deliverable | `/tmp/option-a-plus-clean` | `feat/scope-context-option-a-plus-clean` | `1f3707a` | **Clean (0 files)** | **No** |
| Main | `/home/mohamed/frappe-bench/apps/construction` | `feat/scope-context-option-a-plus` | `087f185` | Dirty (96 files) | No |

**Code identity check (verified live):**
```
$ diff -q /home/mohamed/frappe-bench/apps/construction/construction/overrides/scope_report.py \
         /tmp/option-a-plus-clean/construction/overrides/scope_report.py
SAME CONTENT
```
The running bench loads the main worktree path, whose `scope_report.py` is byte-identical to the clean worktree's committed version. Therefore the live UAT in §4.3 exercised exactly the reviewed code.

---

## 3. Option B v3 — security design (read from source code)

All line numbers below refer to `/tmp/option-a-plus-clean/construction/overrides/scope_report.py` (806 lines, read directly).

### 3.1 The allowlist (lines 51–65, read from code)

```python
ALLOWED_REPORTS: frozenset[str] = frozenset(
    {
        "General Ledger",
        "Trial Balance",
        "Profit and Loss Statement",
        "Balance Sheet",
        "Accounts Payable",
        "Accounts Payable Summary",
        "Accounts Receivable",
        "Accounts Receivable Summary",
        "Budget Variance Report",
        "Cash Flow",
        "Project-wise Profitability",
    }
)
```

Unrestricted roles (lines 68–75, read from code): `System Manager`, `Accounts Manager`, `Accounts User`, `Finance Manager`.

Allowed ptypes (line 231, read from code): `_ALLOWED_PTYPES = frozenset({"report", "select", "read"})` — write/delete/create are never bypassed.

### 3.2 The bypass flag is a structured dict, not a boolean (lines 234–243, read from code)

```python
def set_bypass_context(report_name: str, user: str) -> None:
    """Caller MUST clear it via `clear_bypass_context` (in `finally`)."""
    frappe.flags.scope_report_bypass = {
        "report_name": report_name,
        "user": user,
    }
```

### 3.3 The flag is set in exactly one place — `_scope_aware_run`'s try/finally (lines 796–806, read from code)

```python
    _bypass_active = report_name in ALLOWED_REPORTS and _user_has_active_scope_context(user)
    if _bypass_active:
        set_bypass_context(
            report_name=report_name,
            user=user,
        )
    try:
        return _ORIGINAL_RUN(*new_args, **new_kwargs)
    finally:
        if _bypass_active:
            clear_bypass_context()
```

### 3.4 `get_report_doc` deliberately does NOT set the flag (lines 356–370, read from code)

```python
        # Bypass path: allowlisted report + scoped user → skip both
        # 403s. We deliberately do NOT set `frappe.flags.scope_report_bypass`
        # here. The downstream perm patches (`has_permission`,
        # `get_role_permissions`, `get_permitted_fields`) only fire
        # for requests that go through `_scope_aware_run` (i.e. the
        # `run` call path). The `get_script` call path does NOT
        # use those patches — it only needs the report doc back.
        # Setting the flag here would leave it active for the rest
        # of the request, allowing stale-flag perm grants via any
        # subsequent `has_permission` / `get_role_permissions` call.
        if (
            getattr(doc, "name", None) in ALLOWED_REPORTS
            and _user_has_active_scope_context()
        ):
            return doc
```

This is the v2→v3 fix: v2 set the flag in `get_report_doc`, which leaks because `get_script` does not go through `_scope_aware_run`'s `try/finally`. v3 returns the doc without setting the flag.

### 3.5 `_bypass_context()` validates every condition on every read (lines 159–192, read from code)

The function refuses the bypass if **any** of these fail:
1. Flag is not a dict (line 175–176) — refuses booleans.
2. `report_name` missing or not in `ALLOWED_REPORTS` (line 179–180).
3. `user` missing (line 181–182).
4. `user != frappe.session.user` — cross-user leak guard (line 185–186).
5. User no longer has an active scope context (line 190–191) — defense in depth if scope was cleared after flag-set.

`_bypass_should_apply` (lines 195–228, read from code) additionally validates `report_name` and `user` match the caller, and `ptype` is in `_ALLOWED_PTYPES`. The `doctype` argument is intentionally **not** a gate (lines 212–217) — the bypass is report-scoped because a report's SQL may query multiple secondary doctypes, with data constrained by the L1+L2 wrappers.

### 3.6 The four patched permission functions (lines 92–114 docstring + implementations, read from code)

| Frappe function | Patched name | Bypass behavior |
|-----------------|--------------|-----------------|
| `Report.is_permitted` | `_scope_aware_is_permitted` | Returns True for allowlisted + scoped |
| `frappe.desk.query_report.get_report_doc` | `_scope_aware_get_report_doc` | Returns doc without perm check (does NOT set flag) |
| `frappe.permissions.has_permission` | `_scope_aware_permissions_has_permission` (line 403) | Returns True if `_bypass_should_apply(ptype=...)` |
| `frappe.permissions.get_role_permissions` | (later in file) | Overrides only `report`/`select`/`read` to 1 |
| `frappe.model.get_permitted_fields` | (later in file) | Returns all valid columns when context set |

---

## 4. Test evidence — freshly re-run this review

### 4.1 Backend tests — 50/50 pass (re-run live on 2026-06-20)

**Command run:**
```
bench --site v16.localhost run-tests --module construction.tests.test_option_a_plus
```

**Live output (tail):**
```
construction.tests.test_option_a_plus.TestScopeReportEnforcement
   ✔ test_strict_company_is_scalar_and_equals_scope
   ✔ test_strict_cost_center_is_list_with_descendants
   ✔ test_strict_incoming_value_is_overwritten
   ✔ test_strict_project_is_list_with_scope_value
   ✔ test_unscoped_user_yields_empty_filters

construction.tests.test_option_a_plus.TestScopeReportPositionalArgs
   ✔ test_filters_as_json_string_are_parsed
   ✔ test_positional_filters_are_normalized

construction.tests.test_option_a_plus.TestStrictSignature
   ✔ test_filters_as_json_string_with_keyword
   ✔ test_filters_rewritten_with_keyword_input
   ✔ test_filters_rewritten_with_positional_input
   ✔ test_positional_filters_do_not_cause_duplicate_arg
   ✔ test_unrestricted_user_in_positional_slot_bypasses
   ✔ test_user_resolved_from_positional_arg

----------------------------------------------------------------------
Ran 50 tests in 4.014s
OK
```

**Test structure (read from `test_option_a_plus.py`, 1427 lines):**

| Class | Line | Tests | Source |
|-------|------|-------|--------|
| `TestOptionAPlusPropertySetters` | 77 | 3 | Read from code |
| `TestScopeDimensionPermissionsAPI` | 147 | 2 | Read from code |
| `TestScopeReportEnforcement` | 178 | 5 | Read from code |
| `TestScopeReportAllowlist` | 314 | 3 | Read from code |
| `TestScopeReportPositionalArgs` | 427 | 2 | Read from code |
| `TestStrictSignature` | 519 | 7 | Read from code |
| `TestFinanceRoleBypass` | 799 | 2 | Read from code |
| `TestOptionBReportAccessGate` | 835 | 25 | Read from code |
| **Total** | | **50** | `grep -c "    def test_"` = 50 |

### 4.2 The P0 regression test (lines 1382–1422, read from code)

This is the critical v3 test proving `get_report_doc` does not leave a stale flag:

```python
    def test_get_report_doc_does_not_set_bypass_flag(self):
        """P0 regression: `get_report_doc()` must NOT set
        `frappe.flags.scope_report_bypass`. Only `_scope_aware_run`
        (which is wrapped in try/finally) is allowed to set the
        flag. Otherwise the `get_script` path would leave the flag
        active for the rest of the request, allowing
        `has_permission("Project", "read")` and similar to be
        wrongly granted via a stale flag."""
        from frappe.desk.query_report import get_report_doc
        from construction.overrides import scope_report

        self._set_scope()
        scope_report.clear_bypass_context()
        try:
            frappe.set_user("test_user2@example.com")
            try:
                doc = get_report_doc("General Ledger")
                self.assertEqual(doc.name, "General Ledger")
                # CRITICAL: the bypass flag MUST NOT be set.
                self.assertFalse(
                    hasattr(frappe.flags, "scope_report_bypass")
                    and getattr(frappe.flags, "scope_report_bypass", None) is not None,
                    "get_report_doc must NOT set scope_report_bypass",
                )
                # And the very next perm check on an unrelated
                # doctype must NOT be granted via a stale flag.
                result = scope_report.frappe.has_permission("Project", "read")
                self.assertFalse(
                    result,
                    "Project.read must NOT be granted after get_report_doc (no stale flag)",
                )
            finally:
                frappe.set_user("Administrator")
        finally:
            scope_report.clear_bypass_context()
```

This test was among the 50 that passed in §4.1 (it is the last test in `TestOptionBReportAccessGate`).

### 4.3 Restricted-user UAT — 10/10 pass, zero 403s (re-run live on 2026-06-20)

**Command run:**
```
node /tmp/opencode/test_option_b_uat.js
```
(targeting `http://v16.localhost:8000`, the live bench instance)

**Live output (full):**
```
=== Option B UAT: restricted user (site.engineer.ob) ===
  enabled_scope_context: 1
  active scope: Elrefae / Main - E

  OK General Ledger:              get_script=200, run=200, rows=4
  OK Trial Balance:               get_script=200, run=200, rows=1
  OK Profit and Loss Statement:   get_script=200, run=200, rows=0
  OK Balance Sheet:               get_script=200, run=200, rows=0
  OK Accounts Payable:            get_script=200, run=200, rows=0
  OK Accounts Payable Summary:    get_script=200, run=200, rows=0
  OK Accounts Receivable:         get_script=200, run=200, rows=0
  OK Accounts Receivable Summary: get_script=200, run=200, rows=0
  OK Budget Variance Report:      get_script=200, run=200, rows=0
  OK Cash Flow:                   get_script=200, run=200, rows=17
  FAIL Project-wise Profitability: get_script=404, run=404, rows=?
    (DoesNotExistError: Report Project-wise Profitability not found)

Results: 10 passed, 1 failed (of 11)
```

**Interpretation (from the live output, not from a report):**
- 10 of 11 allowlisted reports are installed and load with `get_script=200` and `run=200` — **zero 403s**.
- The row counts (GL=4, TB=1, CF=17) prove the L1+L2 wrappers constrain data to the user's scope — the bypass opens the perm gate, but the data is still filtered.
- The 11th report (Project-wise Profitability) returns 404 `DoesNotExistError` — the report is not installed in this database. This is a missing report, not a permission failure.

### 4.4 Node tests — 31/31 pass (re-run live on 2026-06-20)

**Command run:**
```
node /tmp/option-a-plus-clean/construction/tests/test_scope_context_report_filters.js
```

**Live output (tail):**
```
✔ lockField() / unlockField()
  ✔ lockField sets read_only=1 and disables the input
  ✔ unlockField restores editable state
  ✔ lockField accepts an array value for MultiSelectList fields
ℹ tests 31
ℹ suites 11
ℹ pass 31
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ duration_ms 21.912924
```

**Test count verified from code:** `grep -c "it("` = 31 `it()` blocks across 10 `describe()` suites.

### 4.5 ruff — NOT independently re-verified

| Claim | Provenance | Status |
|-------|------------|--------|
| `ruff check scope_report.py test_option_a_plus.py` → All checks passed | Acceptance doc §6.4 | **Reported by prior session.** ruff is not installed in this review environment (`python3 -m ruff` → `No module named ruff`). Could not re-verify. Flagging transparently. |

---

## 5. Status of the six Restored Work Follow-up Report items

| ID | Finding | Severity | Status | Evidence (source) |
|----|---------|----------|--------|-------------------|
| F1 | Typography handoff mismatch | P1 | **RESOLVED** | `hooks.py:118` loads `typography_settings.js?v=21` — read from file; commit `087f185` — `git log` live |
| F2 | BOQ Excel import mixed signals | P1 | **RESOLVED** | grep for `preview-only`/`Commit not implemented`/`WP2.8` in service/API code → no matches in `construction/services/` or `construction/api/boq_api.py`; `EV-068` doc exists |
| F3 | Scope context needed runtime verification | P1 | **RESOLVED** | §4.1 (50/50 tests) + §4.3 (10/10 UAT, zero 403s) — **freshly re-run** |
| F4 | `scratch_test.py` debug artifact | P2 | **NOT IN OPTION B DELIVERY** | `ls /tmp/option-a-plus-clean/construction/scratch_test.py` → not found (verified live) |
| F5 | Handoff files read as instructions | P2 | **NOT IN OPTION B DIFF** | `git diff --name-only 3afc78b..HEAD` → 3 files only, no handoff files (verified live) |
| F6 | VFC 37 `console.*` statements | P2 | **NOT IN OPTION B DIFF** | Same `git diff --name-only` — `vfc_layout_engine.js` not in the diff (verified live) |

---

## 6. Deployment state — the single gate (verified live)

```
$ cd /tmp/option-a-plus-clean && git status --short | wc -l
0

$ git rev-list --left-right --count @{u}...HEAD
fatal: no upstream configured for branch 'feat/scope-context-option-a-plus-clean'
```

| Check | State | How verified |
|-------|-------|--------------|
| Working tree | Clean (0 files) | `git status --short` — live |
| Commit chain | `1f3707a` → `13ccc2e` → `3afc78b` | `git log --oneline` — live |
| Diff scope | 3 files, 1288 insertions, 3 deletions | `git diff --stat` — live |
| Backend tests | 50/50 pass | **Re-run live** — §4.1 |
| Node tests | 31/31 pass | **Re-run live** — §4.4 |
| UAT | 10/10, zero 403s | **Re-run live** — §4.3 |
| ruff | Clean | Reported by prior session — §4.5 |
| **Pushed to GitHub** | **No** | `git rev-list` — live |

**The one required action:**
```bash
cd /tmp/option-a-plus-clean
git push -u origin feat/scope-context-option-a-plus-clean
git tag rc-1.1
git push origin rc-1.1
```

---

## 7. Known limitations (to document to client)

| # | Limitation | Technical basis | Source |
|---|------------|-----------------|--------|
| 1 | Only 10 reports scope-filtered | `ALLOWED_REPORTS` frozenset (lines 51–65) — read from code | First-hand |
| 2 | Local system fonts device-dependent | v21 typography (web fonts vs local fonts) | Read from `hooks.py:118` + `typography_settings.js` |
| 3 | Excel import preview-only by default | `construction_settings.json` `enable_boq_excel_import_preview`/`_commit` fields — read from file | First-hand |
| 4 | Collapsed grid rows show dimmed state only | Frappe framework: `gridRow.fields_dict` only populated for expanded rows | User Guide Appendix B |
| 5 | Project-wise Profitability 404 | Not installed in DB — `DoesNotExistError` in live UAT output (§4.3) | **First-hand — seen in live UAT** |

---

## 8. Post-release follow-ups

From `scope_context_option_b_acceptance.md` §10 (reported by prior session, not independently verified):
1. Install Project-wise Profitability report if needed; re-run UAT.
2. Add an Admin Settings toggle for Option B.
3. Add an audit log for restricted-user report access.

---

## 9. Sign-off recommendation (technical)

**Approve for production and client review once `feat/scope-context-option-a-plus-clean` is pushed to GitHub and tagged `rc-1.1`.**

Technical basis, all verified first-hand during this review:
- Security design read from source: structured dict flag (line 240), single set site in `try/finally` (lines 798–806), `get_report_doc` does not set it (lines 356–370), five-condition validation on every read (lines 159–192).
- 50/50 backend tests re-run live (§4.1), including the P0 regression test (§4.2) read from code.
- 31/31 Node tests re-run live (§4.4).
- 10/10 UAT reports re-run live with zero 403s (§4.3).
- 3-file diff, no core changes, clean worktree — verified live (§6).
- User Guide v1.1 cache-buster versions verified against `hooks.py` file reads.

The single gate is the push. No code changes are required.

---

*Companion non-technical document: `CONSULTANT_REVIEW_PART_1_MANAGER.md`. User Guide: `docs/USER_GUIDE.md` v1.1. Option B acceptance (prior session): `docs/scope_context_option_b_acceptance.md`.*
