# Briefing: Production Cutover Rehearsal & Verification Suite (Session 1)

**Target Work Item:** `docs/ai/work-items/cutover-execution-rehearsal/`  
**Base Commit:** `355936b` on `develop` (`apps/construction`)  
**Target Site:** `v16.localhost`  
**Authority:** Owner approval of the Production Cutover Runbook landed in `6c721b8` (Manifest #35).  
**Role:** Independent OpenCode Agent (Implementation & Evidence Generation)  
**Lead Verifier & Committer:** Antigravity (Lead Verifier Lane)

---

## 1. Objective

Now that the cutover runbook ([`PRODUCTION_CUTOVER_RUNBOOK.md`](docs/ai/work-items/production-cutover-runbook/PRODUCTION_CUTOVER_RUNBOOK.md)) and orchestrator ([`cutover_orchestrator.py`](docs/ai/work-items/production-cutover-runbook/evidence/scripts/cutover_orchestrator.py)) are landed in HEAD (`6c721b8`), execute an end-to-end rehearsal of the operational cutover sequence on `v16.localhost` to validate runtime execution, latency contracts, and disaster recovery readiness before a live maintenance window.

---

## 2. Deliverables (Inside `docs/ai/work-items/cutover-execution-rehearsal/`)

| # | File | Purpose |
|---|---|---|
| 1 | `SCOPE.md` | Scope descriptor: authority, pre-conditions, execution log summary, exit code verification table. |
| 2 | `evidence/preflight.log` | Log of Preflight checks (P1–P6) via `cutover_orchestrator.py --phase preflight`. |
| 3 | `evidence/rehearsal-execution.log` | Verbatim execution log of `--phase rehearsal --take-backup --demo-maintenance`. |
| 4 | `evidence/smoke-tests.log` | Standalone run of `cutover_smoke_tests.py` validating all 8 checks (S1–S8) and link search P95 latencies. |
| 5 | `evidence/gates.log` | Standard repository gates: 6 lints + ADR reconciler (19/19) + matrix (273 tests). |
| 6 | `evidence/MANIFEST.json` | Manifest #36 pinning all generated artefacts by SHA-256 digest. |

---

## 3. Strict Invariants & Prohibitions

1. **Zero Database Mutations**:
   - `production_mutation_authorized` MUST remain `false`/unset.
   - The migration runner must execute in `--dry-run` classification mode only.
   - All smoke checks and orchestrator steps must perform rollback in `finally`.
2. **Zero Vendor Code Edits**:
   - Never modify anything in `apps/frappe` or `apps/erpnext`.
3. **No Direct Staging or Commits**:
   - Do NOT run `git commit`. Leave all evidence files unstaged for Antigravity.
4. **Preserved Working Files**:
   - NEVER stage or modify `SESSION_MEMORY.md`, `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`, or `dump.rdb`.
5. **Ephemeral Redis Discipline**:
   - Start ephemeral Redis (`11000`/`13000`) only during test/orchestrator runs requiring cache/queues.
   - Tear down immediately after (`redis-cli -p 11000 shutdown nosave`, `redis-cli -p 13000 shutdown nosave`).
   - Never kill system Redis on `6379`.

---

## 4. Execution Sequence

1. **Startup Check**:
   - Run `python3 scripts/schema_drift_checker.py` and `python3 scripts/ai_context_check.py`.
   - Confirm git branch is `develop` at base `355936b`.
2. **Execute Preflight**:
   ```bash
   python3 docs/ai/work-items/production-cutover-runbook/evidence/scripts/cutover_orchestrator.py \
       --site v16.localhost \
       --phase preflight \
       --yes 2>&1 | tee docs/ai/work-items/cutover-execution-rehearsal/evidence/preflight.log
   ```
3. **Execute Full Rehearsal**:
   ```bash
   python3 docs/ai/work-items/production-cutover-runbook/evidence/scripts/cutover_orchestrator.py \
       --site v16.localhost \
       --phase rehearsal \
       --take-backup \
       --demo-maintenance \
       --yes 2>&1 | tee docs/ai/work-items/cutover-execution-rehearsal/evidence/rehearsal-execution.log
   ```
4. **Execute Post-Cutover Smoke Tests Standalone**:
   - Start ephemeral Redis (11000/13000).
   ```bash
   python3 docs/ai/work-items/production-cutover-runbook/evidence/scripts/cutover_smoke_tests.py \
       --site v16.localhost 2>&1 | tee docs/ai/work-items/cutover-execution-rehearsal/evidence/smoke-tests.log
   ```
   - Teardown ephemeral Redis.
5. **Run Standard Repository Gates**:
   - Execute the 6 lints + ADR reconciler (`19/19`) + regression matrix (`21 modules / 273 tests`).
6. **Compile Manifest & Handover**:
   - Compute SHA-256 digests for all deliverables, generate `evidence/MANIFEST.json`.
   - Leave tree unstaged and report handover back to Antigravity.
