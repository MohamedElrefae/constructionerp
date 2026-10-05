# Handover & Briefing Letter: Production Cutover Runbook & Rehearsal Playbook

**To:** OpenCode Autonomous Agent / Subagent Session (Session D)  
**From:** Antigravity Engineering Lane (Lead Verifier & Committer)  
**Date:** 2026-10-05  
**Subject:** Mission Briefing: Production Cutover Operational Runbook & Rehearsal Playbook  
**Target Repository:** `/home/mohamed/frappe-bench/apps/construction`  
**Target Site:** Staging / Production Environments  
**Base Commit:** `234c024` (`develop` branch)  
**Work Item Path:** `docs/ai/work-items/production-cutover-runbook/`  

---

## 1. Executive Summary & Objective

You are tasked with assembling the **Production Cutover Operational Runbook and Rehearsal Automation**.

In Tier 5J (`5933c0d`), the core production migration automation was constructed:
- Consolidated apply runner: [`run_production_bilingual_migration.py`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/production-migration-readiness/evidence/scripts/run_production_bilingual_migration.py)
- Migration verifier: [`verify_production_bilingual_migration.py`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/production-migration-readiness/evidence/scripts/verify_production_bilingual_migration.py)
- Fail-closed governance gate: `production_mutation_authorized: false`.

Before production deployment authorization is granted, engineering operations requires an immutable, step-by-step **Production Cutover Runbook & Staging Rehearsal Suite** that can be executed flawlessly during the cutover maintenance window.

---

## 2. Invariants & Governance Rules

1. **Role Division:**
   - OpenCode drafts the runbook, helper scripts, rehearsal runner, and validation logs.
   - Antigravity independently audits, verifies gates, and executes the local commit.
2. **Strict Governance Gate Adherence:**
   - The production mutation gate (`production_mutation_authorized`) must remain `false` on `v16.localhost`. Rehearsals run in `--dry-run` or against designated staging test sites.
3. **Owner Confidentiality Policy (`docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`):**
   - Strictly local execution. Never push to remote git repositories or trigger public CI.
4. **Zero Vendor Code Edits:**
   - Do NOT edit any files under `apps/frappe` or `apps/erpnext`.
5. **Fail-Closed Backup Requirement:**
   - The runbook must strictly mandate an active, verified database snapshot ($\le 24\text{ hours}$ old) before any migration step begins.
6. **Ephemeral Redis Protocol:**
   - Terminate Redis ports 11000/13000 immediately after test execution.

---

## 3. Scope of Work

### Step 1: Production Cutover Runbook (`PRODUCTION_CUTOVER_RUNBOOK.md`)
Create a comprehensive, step-by-step operational document covering:
1. **Pre-Cutover Checklist (T minus 24h):**
   - Site maintenance mode activation (`bench --site <site> set-maintenance-mode on`).
   - Database full backup command and validation (`bench --site <site> backup --with-files`).
   - Backup file verification (existence in `private/backups`, non-zero byte size, gzip integrity check).
2. **Dry-Run Validation (T minus 1h):**
   - Execute `run_production_bilingual_migration.py --site <site> --dry-run`.
   - Assert 0 writes, 0 conflicts, and expected `WOULD_WRITE` or `ALREADY_APPLIED` counts.
3. **Cutover Execution (T 0):**
   - Enable `production_mutation_authorized: true` in `site_config.json` (or via `--allow-sites`).
   - Execute `run_production_bilingual_migration.py --site <site>`.
   - Immediate verification with `verify_production_bilingual_migration.py --site <site>`.
4. **Post-Cutover Smoke Tests:**
   - Link search latency probe ($\le 1.50\text{ ms}$).
   - Financial report generation test (`Balance Sheet`, `P&L`).
   - Print format preview test on active transaction documents.
   - Deactivate maintenance mode (`bench --site <site> set-maintenance-mode off`).
5. **Emergency Rollback Protocol:**
   - Step-by-step restoration commands from the verified pre-cutover backup if any step fails.

### Step 2: Automated Pre-Flight & Post-Flight Wrapper Script
Create `scripts/cutover_orchestrator.py` (or within work item scripts) that automates the verification sequence:
- Validates backup file presence.
- Verifies database connection and schema prerequisites.
- Runs dry-run and asserts return code 0.
- Provides interactive confirmations for operational engineers.

---

## 4. Required Deliverables

Inside `docs/ai/work-items/production-cutover-runbook/`:
1. `SCOPE.md` — scope descriptor and rehearsal verification record.
2. `PRODUCTION_CUTOVER_RUNBOOK.md` — complete operational runbook.
3. `evidence/scripts/cutover_smoke_tests.py` — post-cutover verification smoke test script.
4. `evidence/rehearsal-dry-run.log` — execution log of simulated rehearsal on `v16.localhost`.
5. `evidence/gates.log` — 6 lints + reconciler (19/19) execution log.
6. `evidence/MANIFEST.json` — manifest #35 pinning all artefacts.

---

## 5. Handover Instructions

Once your runbook and rehearsal scripts are verified:
- Terminate all Redis processes.
- Leave git working tree unstaged for Antigravity verification.
