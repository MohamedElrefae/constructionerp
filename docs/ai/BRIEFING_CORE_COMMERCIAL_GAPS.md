# Briefing: Core Commercial & Financial Integrity Gaps G01, G02, G04 (Session 2)

**Target Work Item:** `docs/ai/work-items/boq-commercial-integrity/`  
**Base Commit:** `355936b` on `develop` (`apps/construction`)  
**Target Site:** `v16.localhost`  
**Authority:** Customer Release Gap Report ([`docs/ai/CUSTOMER_RELEASE_GAPS_2026-10-04.md`](docs/ai/CUSTOMER_RELEASE_GAPS_2026-10-04.md)) §4 Findings G01, G02, G04.  
**Role:** Independent OpenCode Agent (Implementation & Verification)  
**Lead Verifier & Committer:** Antigravity (Lead Verifier Lane)

---

## 1. Objective

Resolve the top 3 confirmed financial correctness and commercial history defects identified in the consultant release audit:
1. **G01 (BOQ Item Deletion Rollup Defect)**: Direct BOQ Item deletion recalculates totals before row deletion, leaving stale header totals.
2. **G02 (Approved Quantity Revision Mutability)**: Server validation allows commercial fields (quantities, rates, values) of an `Approved` revision to be modified post-approval.
3. **G04 (BOQ Factor Arithmetic Unification)**: Unify factor validation and fallback so zero/negative factors are rejected and rollup arithmetic matches line items.

---

## 2. Deliverables & Code Changes

### Files to Modify in `apps/construction`:
1. `construction/construction/doctype/boq_item/boq_item.py`:
   - Fix rollup lifecycle: ensure header rollup executes in `after_delete()` after the row is removed from MariaDB, rather than solely in `on_trash()`.
   - Prevent stale rollups if a deletion fails.
   - Enforce factor > 0 validation on BOQ item.
2. `construction/construction/doctype/boq_quantity_revision/boq_quantity_revision.py`:
   - Update `validate_approval_integrity()`: when `doc_before_save` has `status == "Approved"`, forbid changes to all commercial fields (`boq_item`, `boq_header`, `revised_qty`, `revised_unit_price`, `delta_quantity`, `delta_amount`, `revision_type`, `approved_by`, `approval_date`). Corrections must require a new revision record.
3. `construction/tests/test_boq_financial_integrity.py` (New File):
   - Regression tests for G01: insert items, assert header total, delete an item, assert header total updates correctly to remaining items.
   - Regression tests for G02: create and approve a revision, attempt modifying quantity/rate, assert `frappe.ValidationError` raised.
   - Regression tests for G04: attempt factor = 0 or negative, assert error; verify factor defaults to 1.0 when unset.

### Deliverables Inside `docs/ai/work-items/boq-commercial-integrity/`:
- `SCOPE.md`: Formal scope document, root causes, fix descriptions, and test results.
- `evidence/test-execution.log`: Full run of `test_boq_financial_integrity.py`.
- `evidence/gates.log`: 6 lints + ADR reconciler (`19/19`).
- `evidence/regression-matrix.log`: Matrix verification (`21 modules` + new module).
- `evidence/MANIFEST.json`: Manifest pinning all modified files and evidence artefacts.

---

## 3. Strict Invariants

1. **Zero Vendor Code Edits**:
   - Zero changes to `apps/frappe` or `apps/erpnext`.
2. **Preserve Existing Matrix Pass**:
   - All 273 existing matrix tests must continue to pass without regression.
3. **Preserved Working Files**:
   - NEVER stage or modify `SESSION_MEMORY.md`, `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`, or `dump.rdb`.
4. **Local Execution Only**:
   - Do NOT run `git commit`. Leave all files unstaged for Antigravity to verify and commit.
5. **Ephemeral Redis**:
   - Start Redis 11000/13000 during test execution and kill immediately afterwards. Never touch port 6379.

---

## 4. Execution Sequence

1. **Startup Check**:
   - Run `python3 scripts/schema_drift_checker.py` and `python3 scripts/ai_context_check.py`.
2. **Implement Fixes & Test Suite**:
   - Modify `boq_item.py` and `boq_quantity_revision.py`.
   - Write unit/integration tests in `construction/tests/test_boq_financial_integrity.py`.
3. **Execute Test Suite**:
   - Run: `bench --site v16.localhost run-tests --module construction.tests.test_boq_financial_integrity`.
4. **Execute Full Matrix & Lints**:
   - Run `bash scripts/run_bilingual_regression_matrix.sh`.
   - Run lints and ADR reconciler.
5. **Compile Manifest & Handover**:
   - Generate `MANIFEST.json` and report completion back to Antigravity.
