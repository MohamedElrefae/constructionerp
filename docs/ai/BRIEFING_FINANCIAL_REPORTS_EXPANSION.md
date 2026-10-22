# Handover & Briefing Letter: Financial Reports Allowlist Expansion

**To:** OpenCode Autonomous Agent / Subagent Session (Session B)  
**From:** Antigravity Engineering Lane (Lead Verifier & Committer)  
**Date:** 2026-10-05  
**Subject:** Mission Briefing: Bilingual Financial Reports Expansion (Stage 7 Extension)  
**Target Repository:** `/home/mohamed/frappe-bench/apps/construction`  
**Target Site:** `v16.localhost`  
**Base Commit:** `234c024` (`develop` branch)  
**Work Item Path:** `docs/ai/work-items/bilingual-financial-reports-expansion/`  

---

## 1. Executive Summary & Objective

You are tasked with **expanding the Bilingual Financial Reports Allowlist** in `apps/construction`.

In Tier 5E (`aecef45`), the localized financial report engine was implemented and hardened for two primary statements:
- `Balance Sheet`
- `Profit and Loss Statement`

Accountants and project managers require direct Arabic report views for additional core accounting statements. Your mission is to safely expand the allowlist, column mappings, and UI selectors to support:
1. **`General Ledger`**
2. **`Trial Balance`**
3. **`Accounts Payable Summary`**
4. **`Accounts Receivable Summary`**
5. **`Cash Flow`**

---

## 2. Invariants & Governance Rules

1. **Role Division:**
   - OpenCode implements, tests, and compiles evidence logs.
   - Antigravity independently audits, verifies gates, and executes the local commit.
2. **Fail-Closed Allowlist Guard:**
   - Any report name not explicitly in `PILOT_REPORTS` must fail-closed with `frappe.PermissionError` or `frappe.ValidationError`.
3. **Read-Only Filter Normalization:**
   - Callers' passed filters must win over defaults via `.setdefault()`.
   - Never mutate database records during report generation (zero writes).
4. **Owner Confidentiality Policy (`docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`):**
   - Strictly local execution. Never push to remote git repositories or trigger public CI.
5. **Zero Vendor Code Edits:**
   - Do NOT edit any files under `apps/frappe` or `apps/erpnext`.
6. **Viewer Compatibility:**
   - `bilingual_report_viewer.js` must expose the new statements in its `<select>` dropdown.
7. **Ephemeral Redis Protocol:**
   - Terminate Redis ports 11000/13000 immediately after test execution.

---

## 3. Scope of Work

### Step 1: Extend Backend Allowlist & Period Defaults
In `construction/api/bilingual_reports.py`:
- Add candidate reports to `PILOT_REPORTS` tuple.
- Implement report-specific default filter resolvers (e.g. `company = "Elrefae"`, default fiscal year bounds for `General Ledger` and `Trial Balance`).
- Define localized column header maps (Arabic label mappings for standard vendor report columns: `Posting Date`, `Account`, `Debit`, `Credit`, `Voucher Type`, `Voucher No`, `Against Account`, `Balance`).

### Step 2: Extend Frontend Report Viewer
In `construction/public/js/bilingual_report_viewer.js` (or designated page bundle):
- Add `<option>` entries for the expanded statements.
- Configure date-range vs. fiscal-year filter display for the selected report type.

### Step 3: Expand Automated Test Coverage
In `construction/tests/test_stage7_bilingual_reports.py`:
- Test that each new report executes and returns translated columns and rows without errors.
- Test that unauthenticated / unauthorized requests fail closed.
- Test that mutation guard asserts 0 database writes.

---

## 4. Required Deliverables

Inside `docs/ai/work-items/bilingual-financial-reports-expansion/`:
1. `SCOPE.md` — scope descriptor and verification table.
2. Modified code files:
   - `construction/api/bilingual_reports.py`
   - `construction/public/js/bilingual_report_viewer.js`
   - `construction/tests/test_stage7_bilingual_reports.py`
3. `evidence/report-execution.log` — proof of report runs and column translations across all 5 statements.
4. `evidence/gates.log` — 6 lints + reconciler (19/19) execution log.
5. `evidence/MANIFEST.json` — manifest #33 pinning all modified and evidence files.

---

## 5. Handover Instructions

Once your test suite passes and evidence is captured:
- Terminate all Redis processes.
- Leave git working tree unstaged for Antigravity verification.
