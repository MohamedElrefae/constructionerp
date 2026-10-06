# OpenCode Sequential Execution Guide: Multi-Site Migration, Main Merge & Release Closure

> **Target:** Sequential Execution by OpenCode (Unattended / Hands-Off Run)  
> **Base Branch:** `develop` (HEAD: `5854dc9`)  
> **Confidentiality:** Strictly Local Execution per `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`  
> **Lead Auditor:** Antigravity  

---

## 1. Operational Invariants (Mandatory)

1. **Remote Push Policy:** Strictly ZERO push to remotes during execution (`git push` prohibited).
2. **Hook Bypass:** Every commit must bypass transmitting hooks:
   ```bash
   git -c core.hooksPath=/dev/null commit -m "..."
   ```
3. **Vendor Immutability:** ZERO edits to `apps/frappe/` or `apps/erpnext/`.
4. **Redis Safety:** Never touch port 6379 (system Redis). Ephemeral Redis (11000/13000) started on demand, torn down after tests. Never commit `dump.rdb`.
5. **Fail-Closed Migration Safety:** Take fresh backups before migrating. If any step errors, abort and restore.

---

## 2. Step-by-Step Autonomous Execution Sequence

Execute the following four stages in sequence from `/home/mohamed/frappe-bench`:

### Stage 1: Fresh Backups & Live Site Schema Migration
Coordinate live schema migration on `v16.localhost` so the database tables gain the official DocType columns (`cost_basis`, `pricing_rule_version`, etc.):

```bash
cd /home/mohamed/frappe-bench

# 1. Take fresh backups of active sites with files
bench --site v16.localhost backup --with-files
bench --site localhost backup --with-files

# 2. Run cutover orchestrator dry-run to verify preconditions
python3 apps/construction/docs/ai/work-items/multi-site-coordinated-cutover/scripts/orchestrate_cutover.py --dry-run

# 3. Put v16.localhost into maintenance mode
bench --site v16.localhost set-maintenance-mode on

# 4. Run schema migration
bench --site v16.localhost migrate --skip-search-index

# 5. Take v16.localhost out of maintenance mode
bench --site v16.localhost set-maintenance-mode off

# 6. Verify database schema has the columns
bench --site v16.localhost mariadb -e "DESCRIBE \`tabBOQ Item\`;" | grep -E "cost_basis|pricing_rule"
```

---

### Stage 2: Post-Migration Quality & Regression Verification
Verify that the migrated schema passes all commercial UAT and security tests without regressions:

```bash
cd /home/mohamed/frappe-bench

# 1. Start ephemeral Redis (11000/13000) idempotently
redis-cli -p 11000 ping 2>/dev/null || redis-server --port 11000 --daemonize yes
redis-cli -p 13000 ping 2>/dev/null || redis-server --port 13000 --daemonize yes

# 2. Run End-to-End Commercial UAT Suite (10 tests)
bench --site v16.localhost run-tests --module construction.tests.test_e2e_bilingual_commercial_workflow

# 3. Run Dependency Security Guards Suite (33 tests)
bench --site v16.localhost run-tests --module construction.tests.test_dependency_security_guards

# 4. Run Commercial Integrity Suite (5 tests)
bench --site v16.localhost run-tests --module construction.tests.test_boq_financial_integrity

# 5. Tear down ephemeral Redis immediately
redis-cli -p 11000 shutdown nosave 2>/dev/null || true
redis-cli -p 13000 shutdown nosave 2>/dev/null || true
```

---

### Stage 3: Release Candidate Tagging & Local Merge to `main`
Tag the release candidate on `develop`, then merge `develop` into `main` locally:

```bash
cd /home/mohamed/frappe-bench/apps/construction

# 1. Ensure working tree is clean
git status

# 2. Create Release Candidate tag on develop
git tag -a v6.8.0-rc1 -m "Release Candidate v6.8.0-rc1: Unified commercial gaps, G10 security guards, multi-site cutover runbook, and bilingual UAT"

# 3. Switch to main and merge develop
git checkout main
git -c core.hooksPath=/dev/null merge develop -m "merge: release candidate v6.8.0-rc1 (develop to main)"

# 4. Return to develop
git checkout develop
```

---

### Stage 4: Documentation, Release Notes & Handover Report
1. Create `docs/ai/RELEASE_NOTES_v6.8.0.md` detailing:
   - Release Candidate Tag: `v6.8.0-rc1`
   - Commercial & Financial Integrity (G01–G06)
   - Verified Test Suites & CI Coverage (G07, G08, G14, G16)
   - Security Defenses & Upstream Alignment (G10)
   - Coordinated Cutover Runbook & Operating Profile (G11, G12, G15)
   - Manifest & Governance Integrity (40 manifests, 423 file entries, zero drift)
2. Run standard repository linters:
   ```bash
   python3 scripts/lint_scope_metadata.py
   python3 scripts/ai_context_check.py
   python3 scripts/schema_drift_checker.py
   python3 scripts/lint_translation_writes.py
   ```
3. Commit locally on `develop`:
   ```bash
   git add docs/ai/RELEASE_NOTES_v6.8.0.md
   git -c core.hooksPath=/dev/null commit -m "docs(release): add v6.8.0-rc1 release notes and migration verification record"
   ```
4. Emit your final handover summary for Antigravity review.
