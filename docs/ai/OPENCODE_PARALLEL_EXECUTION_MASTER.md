# OpenCode Master Guide: Parallel Release Execution (Sessions 3A, 3B, 3C)

> **Execution Protocol:** Parallel Autonomous OpenCode Sessions  
> **Target Base:** `develop` (HEAD: `78b7094`)  
> **Lead Verifier & Committer:** Antigravity  
> **Confidentiality:** Strictly Local Execution per `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md` (Zero Push to Remotes)

---

## 1. Executive Strategy & Workspace Isolation

To complete the remaining release gates without serial blocking, three parallel OpenCode worker sessions are deployed concurrently. To eliminate Git index collisions, file stomping, and race conditions, **each session runs in its own dedicated Git worktree on an isolated local branch**.

### Master Topology

| Session | Focus Gate | Git Worktree Path | Local Branch | Isolated Work-Item Directory |
|---|---|---|---|---|
| **Session 3A** | **G10** (Dependency Security & Upstream Alignment) | `/home/mohamed/frappe-bench/worktrees/session-3a-security` | `opencode/session-3a-security` | `docs/ai/work-items/dependency-security-remediation/` |
| **Session 3B** | **G12, G15** (Multi-Site Coordinated Cutover & Bench Isolation) | `/home/mohamed/frappe-bench/worktrees/session-3b-cutover` | `opencode/session-3b-cutover` | `docs/ai/work-items/multi-site-coordinated-cutover/` |
| **Session 3C** | **G14, G16** (End-to-End Bilingual Commercial UAT) | `/home/mohamed/frappe-bench/worktrees/session-3c-uat` | `opencode/session-3c-uat` | `docs/ai/work-items/e2e-bilingual-commercial-uat/` |

---

## 2. Universal Operational Invariants

Every OpenCode session **must strictly abide by the following invariants**:

1. **Zero Push to Remotes:** Strictly zero network push (`git push`).
2. **Local Commit Security:** If committing locally, transmitting hooks must be bypassed:
   ```bash
   git -c core.hooksPath=/dev/null commit -m "..."
   ```
3. **Vendor Code Immutability:** Strictly **ZERO** edits to `apps/frappe/` or `apps/erpnext/`. All logic must live within `apps/construction` or its worktree equivalent.
4. **Redis Port Rules:**
   - **System Redis (port 6379)**: **STRICTLY UNTOUCHED**. Do not ping, configure, restart, or kill.
   - **Ephemeral Redis (ports 11000 & 13000)**: Start idempotently before tests if not running:
     ```bash
     redis-cli -p 11000 ping 2>/dev/null || redis-server --port 11000 --daemonize yes
     redis-cli -p 13000 ping 2>/dev/null || redis-server --port 13000 --daemonize yes
     ```
   - Never commit `dump.rdb`.
5. **Database Mutation Safety:**
   - Dry-run only (`--dry-run`) or automatic rollback via test `tearDown()` / transaction rollbacks.
   - Never permanently modify or delete existing database rows on `v16.localhost`.
6. **Manifest Integrity:** Every session must generate a self-verifying `evidence/MANIFEST.json` containing SHA-256 digests of all deliverables and modified files.

---

## 3. Worktree Bootstrap Setup (Run Once Before Launching Sessions)

Run this block from `/home/mohamed/frappe-bench/apps/construction` to create all three parallel worktrees branched from `develop`:

```bash
cd /home/mohamed/frappe-bench/apps/construction

# 1. Session 3A Worktree
git worktree add /home/mohamed/frappe-bench/worktrees/session-3a-security -b opencode/session-3a-security develop

# 2. Session 3B Worktree
git worktree add /home/mohamed/frappe-bench/worktrees/session-3b-cutover -b opencode/session-3b-cutover develop

# 3. Session 3C Worktree
git worktree add /home/mohamed/frappe-bench/worktrees/session-3c-uat -b opencode/session-3c-uat develop
```

---

## 4. Session 3A: Dependency Security Remediation (G10)

- **Detailed Briefing:** [BRIEFING_DEPENDENCY_SECURITY_REMEDIATION.md](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/BRIEFING_DEPENDENCY_SECURITY_REMEDIATION.md)
- **Working Directory:** `/home/mohamed/frappe-bench/worktrees/session-3a-security`
- **Output Directory:** `docs/ai/work-items/dependency-security-remediation/`

### Objectives
1. Reconcile against the 70 GHSA advisories documented in `SECURITY_UPGRADE_PATH.md`.
2. Align upstream-compatible library pins (`cryptography~=50.0.0`, `pyOpenSSL~=26.4.0`, `Pillow~=12.3.0`, `sqlparse~=0.6.0`, `sql_metadata~=3.0.1`).
3. Implement application-level compensating controls for unfixable upstream packages:
   - Create `construction/utils/security.py` or enhance boundary guards to validate user uploads (PDF, SVG), enforce local-asset protocol, and block SSRF vectors.
4. Add unit test suite `construction/tests/test_dependency_security_guards.py`.

### Required Deliverables
- `SCOPE.md`
- `evidence/dependency-reconciliation.log`
- `evidence/clean-build.log`
- `evidence/security-guards.log`
- `evidence/gates.log`
- `evidence/MANIFEST.json`

### Verification Command
```bash
cd /home/mohamed/frappe-bench
bench --site v16.localhost run-tests --module construction.tests.test_dependency_security_guards
```

---

## 5. Session 3B: Coordinated Multi-Site Cutover Runbook (G12, G15)

- **Detailed Briefing:** [BRIEFING_MULTI_SITE_COORDINATED_CUTOVER.md](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/BRIEFING_MULTI_SITE_COORDINATED_CUTOVER.md)
- **Working Directory:** `/home/mohamed/frappe-bench/worktrees/session-3b-cutover`
- **Output Directory:** `docs/ai/work-items/multi-site-coordinated-cutover/`

### Objectives
1. Build an automated cutover orchestrator script: `docs/ai/work-items/multi-site-coordinated-cutover/scripts/orchestrate_cutover.py`.
2. Implement preflight checks across all bench sites (`localhost`, `v16.localhost`, `v16rehearsal.localhost`).
3. Implement backup verification with SHA-256 integrity validation and restoration timing measurement.
4. Implement dynamic maintenance mode toggle (`maintenance_mode = 1 -> 0`) with fail-closed automatic rollback.
5. Provide isolated production operating profiles under `evidence/operating-profile/` (`Procfile`, `supervisord.conf.template`, `redis_queue.conf`).

### Required Deliverables
- `SCOPE.md`
- `scripts/orchestrate_cutover.py`
- `evidence/multi-site-preflight.log`
- `evidence/cutover-drill.log`
- `evidence/rollback-drill.log`
- `evidence/operating-profile/`
- `evidence/MANIFEST.json`

### Verification Command
```bash
cd /home/mohamed/frappe-bench/worktrees/session-3b-cutover
python3 docs/ai/work-items/multi-site-coordinated-cutover/scripts/orchestrate_cutover.py --dry-run
```

---

## 6. Session 3C: End-to-End Bilingual Commercial UAT (G14, G16)

- **Detailed Briefing:** [BRIEFING_E2E_BILINGUAL_COMMERCIAL_UAT.md](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/BRIEFING_E2E_BILINGUAL_COMMERCIAL_UAT.md)
- **Working Directory:** `/home/mohamed/frappe-bench/worktrees/session-3c-uat`
- **Output Directory:** `docs/ai/work-items/e2e-bilingual-commercial-uat/`

### Objectives
1. Implement the comprehensive end-to-end commercial test suite: `construction/tests/test_e2e_bilingual_commercial_workflow.py`.
2. Exercise the full commercial lifecycle:
   - **BOQ & Pricing**: Header -> Groups -> Leaves -> Additive Cost Analysis (120% rule, versioned pricing provenance).
   - **Variation Order & Quantity Revision**: Positive factor (`factor > 0`) -> Approval -> Immutability freeze on save -> Item deletion rollup.
   - **Bilingual Transactional Prints**: Render Purchase Order, Sales Invoice, Stock Entry, Material Request in Arabic, English, and Both modes with currency tags and BDI isolation.
   - **Bilingual Financial Reports**: Execute all 7 allowlisted reports (GL, TB, Balance Sheet, P&L, AR Summary, AP Summary, Cash Flow) with header localization and company fallback.

### Required Deliverables
- `SCOPE.md`
- `construction/tests/test_e2e_bilingual_commercial_workflow.py`
- `evidence/e2e-workflow-execution.log`
- `evidence/rendered-samples/`
- `evidence/gates.log`
- `evidence/MANIFEST.json`

### Verification Command
```bash
cd /home/mohamed/frappe-bench
bench --site v16.localhost run-tests --module construction.tests.test_e2e_bilingual_commercial_workflow
```

---

## 7. Handover Checklist for Each OpenCode Worker

When an OpenCode session finishes its stream, it must execute this handover checklist:

1. **Verify Evidence Manifest**:
   Ensure all evidence files, scripts, and modified code are cataloged in `evidence/MANIFEST.json` with correct SHA-256 digests.
2. **Execute Standard Quality Gates**:
   ```bash
   python3 scripts/lint_scope_metadata.py
   python3 scripts/ai_context_check.py
   python3 scripts/schema_drift_checker.py
   python3 scripts/lint_translation_writes.py
   ```
3. **Tear Down Redis (If Started)**:
   ```bash
   redis-cli -p 11000 shutdown nosave 2>/dev/null || true
   redis-cli -p 13000 shutdown nosave 2>/dev/null || true
   ```
4. **Local Branch Commit**:
   Commit all changes locally on the session's branch:
   ```bash
   git add docs/ai/work-items/<session-dir>/ construction/
   git -c core.hooksPath=/dev/null commit -m "feat(<session>): complete deliverables and evidence manifest"
   ```
5. **Report Handover**: Signal completion to the user and Antigravity with the branch name and manifest verification output.

---

## 8. Antigravity Verification & Unified Landing Protocol

Once the sessions complete, Antigravity performs the centralized audit and landing onto `develop`:

1. **Branch Audit & Diff Review**: Inspect `git diff develop...opencode/<branch>`.
2. **Sequential Merge**:
   - Merge `opencode/session-3a-security` -> Run security tests.
   - Merge `opencode/session-3b-cutover` -> Run cutover orchestrator dry-run.
   - Merge `opencode/session-3c-uat` -> Run complete UAT suite.
3. **Full Regression Matrix**: Run 21 modules / 273+ tests against `v16.localhost`.
4. **Repo-Wide Manifest Reconciliation**: Verify 100% digest integrity across all 40+ manifests.
5. **Atomic Final Commit**: Land on `develop` with zero transmitting hooks.
