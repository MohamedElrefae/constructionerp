# Session 3C Briefing — End-to-End Bilingual Commercial UAT & Workflow Verification (G14, G16)

## Authority & Operational Posture
- **Standing Policy:** Local execution only under `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`. Zero push to public remotes.
- **Transmitting Hooks:** Disabled per command (`git -c core.hooksPath=/dev/null ...`).
- **Vendor Code Invariant:** Strictly ZERO modifications to `apps/frappe` or `apps/erpnext`.
- **Database Safety:** All test fixtures created within tests must roll back or clean up in `tearDown()`. Zero permanent data writes.
- **Port Invariant:** Ephemeral Redis (11000/13000) started on-demand, torn down immediately after testing. Never touch port 6379 (system Redis). Never commit `dump.rdb`.

---

## 1. Objective & Scope
Implement an integrated, automated End-to-End User Acceptance Test (UAT) suite that exercises the entire customer commercial lifecycle across all four unified streams landed on `develop`:

1. **BOQ & Pricing Lifecycle:**
   - Create a BOQ Header, group structures, and leaf items.
   - Attach a BOQ Cost Analysis using versioned additive pricing (`additive-direct-cost/v1`, 120% rule with overhead/profit/tender tax).
   - Approve analysis and verify estimated cost & pricing provenance locked on BOQ Item.
2. **Variation Order & Commercial Integrity Lifecycle:**
   - Create Variation Order and quantity revisions with positive factor (`factor > 0`).
   - Approve revision -> verify `APPROVAL_FROZEN_FIELDS` immutability on server save.
   - Delete a leaf item -> verify automatic `total_contract_value` and budget rollup in `after_delete()`.
3. **Bilingual Document Rendering (Arabic, English, Both):**
   - Render all 4 bilingual transactional print formats: Purchase Order, Sales Invoice, Stock Entry, Material Request.
   - Verify proper Arabic and English labels, currency tags, and BDI isolation.
4. **Bilingual Financial Reporting (7 Allowlisted Reports):**
   - Execute bilingual reports: General Ledger, Trial Balance, Balance Sheet, Profit & Loss, Accounts Receivable Summary, Accounts Payable Summary, Cash Flow.
   - Verify column header localization in `ar` and `both` modes without mutating vendor column structures.
   - Verify company fallback logic and role permission barriers.

---

## 2. Directory & Deliverables
Work in isolated directory:
`docs/ai/work-items/e2e-bilingual-commercial-uat/`

Deliverables required:
1. `SCOPE.md`: Authority, business lifecycle flow diagram, test cases, verification results, manifest reference.
2. `construction/tests/test_e2e_bilingual_commercial_workflow.py`: Comprehensive test case suite executing the end-to-end lifecycle.
3. `evidence/e2e-workflow-execution.log`: Full verbose test output showing 100% PASS across all workflow phases.
4. `evidence/rendered-samples/`: Raw HTML/text captures of the 4 rendered print formats and report column structures.
5. `evidence/gates.log`: Repository linters (`lint_scope_metadata.py`, `ai_context_check.py`, `schema_drift_checker.py`, `lint_translation_writes.py`).
6. `evidence/MANIFEST.json`: Self-verifying manifest pinning all evidence and test files by SHA-256.

---

## 3. Allowed Code Modifications
- `construction/tests/test_e2e_bilingual_commercial_workflow.py` (new test suite).
- `docs/ai/work-items/e2e-bilingual-commercial-uat/*`.
- **Prohibited:** Modifying vendor code, breaking existing tests, or modifying shared configuration files.

---

## 4. Verification & Handover
1. Run the test suite: `bench --site v16.localhost run-tests --module construction.tests.test_e2e_bilingual_commercial_workflow`.
2. Run standard linters (`python3 scripts/lint_scope_metadata.py`, `ai_context_check.py`, `schema_drift_checker.py`).
3. Compute SHA-256 digests and write `evidence/MANIFEST.json`.
4. Tear down ephemeral Redis (11000/13000). Leave working tree unstaged for Antigravity audit and commit.
