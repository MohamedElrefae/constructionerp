# OpenCode Instruction: Release Candidate Finalization & Worktree Cleanup

> **Role:** OpenCode Worker  
> **Lead Auditor & Committer:** Antigravity  
> **Base Branch:** `develop` (HEAD: `9c34cdf`)  
> **Working Directory:** `/home/mohamed/frappe-bench/apps/construction`  
> **Standing Policy:** Local execution only under `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md` (Zero Remote Push)

---

## 1. Context & Operational Invariants

Sessions 3A (G10), 3B (G12, G15), and 3C (G14, G16) have been audited, regression-tested against `v16.localhost`, and merged cleanly into `develop` at commit `9c34cdf`. All 16 release gates (G01 through G16) are now satisfied with code, tests, and evidence. 

Before final handover to the owner, you are instructed to execute the following administrative, documentation, and cleanup actions:

1. **Zero Push to Remotes:** Strictly local Git operations.
2. **Hook Bypass:** Use `git -c core.hooksPath=/dev/null commit -m "..."`.
3. **Vendor Immutability:** Strictly ZERO modifications to `apps/frappe` or `apps/erpnext`.
4. **Redis Safety:** Never touch system Redis (port 6379). Ephemeral Redis (11000/13000) only if running tests, and shut down after. Never track `dump.rdb`.

---

## 2. Action Plan

### Task 1: Clean Up Temporary Parallel Worktrees
The three parallel worker worktrees are fully merged and no longer needed. Remove them and prune their merged local branches:

```bash
cd /home/mohamed/frappe-bench/apps/construction

# 1. Remove worktrees
git worktree remove /home/mohamed/frappe-bench/worktrees/session-3a-security
git worktree remove /home/mohamed/frappe-bench/worktrees/session-3b-cutover
git worktree remove /home/mohamed/frappe-bench/worktrees/session-3c-uat

# 2. Delete merged local branches
git branch -d opencode/session-3a-security
git branch -d opencode/session-3b-cutover
git branch -d opencode/session-3c-uat

# 3. Verify clean worktree list
git worktree list
```

---

### Task 2: Update Master Release Documentation & Ledger
Update the persistent memory and status files to reflect the unified, qualified status of all 16 gates:

1. **`docs/ai/work-items/customer-release-gap-fixes/STATUS.md`**:
   - Update the status narrative to record that Track 1 (commercial integrity G01/G02/G04, CI Run 11 G07) and Track 2 (Sessions 3A, 3B, 3C) are merged on `develop`.
   - Update the 16-gate table:
     - **G10**: SATISFIED. Frappe v16.36.1 alignment, 70 GHSA identities reconciled, application-level compensating controls (`security.py`), 33 unit tests PASS.
     - **G12**: SATISFIED. Multi-site coordinated cutover runbook (`orchestrate_cutover.py`) 44 steps PASS, zero data loss, multi-site schema sync verified.
     - **G14**: SATISFIED. End-to-end commercial UAT suite (`test_e2e_bilingual_commercial_workflow.py`) 10/10 tests PASS, 4 bilingual print formats rendered, 7 financial reports localized.
     - **G15**: SATISFIED. Native backup verification (8.62s restore timing), fail-closed rollback drill, production deployment operating profiles (`Procfile`, `supervisord.conf.template`, `redis_queue.conf`).
     - **G16**: SATISFIED. All 16 gates verified green; repo-wide 40 manifests across 423 files 100% verified with zero drift.

2. **`SESSION_MEMORY.md`**:
   - Add a new section summarizing the completion and landing of Sessions 3A, 3B, and 3C, and the unification of all 16 customer release gates on `develop` (`9c34cdf`).
   - Record the repo-wide manifest integrity status (40 manifests, 423 file entries, 0 drift).

3. **`docs/ai/CONTEXT_INDEX.md`**:
   - Update the status of active work-items to indicate that customer release gap remediation and UAT tracks are completed on `develop`.

---

### Task 3: Create Master Customer Release Candidate Summary
Create `docs/ai/CUSTOMER_RELEASE_CANDIDATE_SUMMARY.md` as an executive, audit-ready handover report covering:
1. **Release Candidate Identity**: Git commit `9c34cdf` on branch `develop`.
2. **Financial & Commercial Integrity Architecture**:
   - Additive direct-cost pricing (120% rule with overhead, profit, and tender tax).
   - Permanent approval immutability (`APPROVAL_FROZEN_FIELDS` enforced on server save).
   - Positive-factor enforcement (`factor > 0`).
   - Automatic contract value and budget rollup on leaf item deletion.
3. **Automated Test & Qualification Coverage**:
   - Provider CI Run 11 green (17 modules, 234 Python tests, 35 JS property tests).
   - Bilingual Regression Matrix (21 modules, 283+ tests clean).
   - End-to-End Commercial UAT Suite (10 tests in `test_e2e_bilingual_commercial_workflow.py`).
   - Dependency Security Unit Suite (33 tests in `test_dependency_security_guards.py`).
4. **Security Hardening & Upstream Compatibility**:
   - Frappe v16.36.1 dependency alignment (`cryptography`, `pyOpenSSL`, `Pillow`, `sqlparse`, `sql_metadata`).
   - Application-level compensating controls for SSRF, file upload sniffing, PDF page caps, SVG sanitization, and rich-text bleach filters.
5. **Multi-Site Cutover Runbook & Operating Profile**:
   - Automated 44-step cutover orchestrator CLI (`orchestrate_cutover.py --dry-run`).
   - Multi-site backup validation and timed synthetic recovery (8.62s restore timing).
   - Fail-closed rollback mechanism.
   - Dedicated production operating profiles (`Procfile`, `supervisord.conf.template`, `redis_queue.conf`).
6. **Manifest & Governance Integrity**:
   - 40 manifests across 423 files 100% verified with zero drift.
   - 4 repository linters passing clean.

---

### Task 4: Verification & Local Commit
1. Run repository linters:
   ```bash
   python3 scripts/lint_scope_metadata.py
   python3 scripts/ai_context_check.py
   python3 scripts/schema_drift_checker.py
   python3 scripts/lint_translation_writes.py
   ```
2. Verify repo manifests:
   Ensure all 40 manifests continue to self-verify with 0 missing files and 0 mismatched digests.
3. Commit locally:
   ```bash
   git add docs/ai/ SESSION_MEMORY.md
   git -c core.hooksPath=/dev/null commit -m "docs(release): finalize customer release candidate ledger, summary, and worktree cleanup"
   ```
4. Present your handover report to Antigravity for final review and sign-off.
