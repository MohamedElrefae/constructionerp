# Session 3B Briefing — Coordinated Multi-Site Cutover Runbook & Bench Isolation (G12, G15)

## Authority & Operational Posture
- **Standing Policy:** Local execution only under `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`. Zero push to public remotes.
- **Transmitting Hooks:** Disabled per command (`git -c core.hooksPath=/dev/null ...`).
- **Vendor Code Invariant:** Strictly ZERO modifications to `apps/frappe` or `apps/erpnext`.
- **Database Safety:** All migration rehearsals and rollback drills must run with `--dry-run` or isolated disposable rollback savepoints. NEVER mutate live production data.
- **Port Invariant:** Ephemeral Redis (11000/13000) started on-demand, torn down immediately after testing. Never touch port 6379 (system Redis). Never commit `dump.rdb`.

---

## 1. Objective & Scope
Build an automated, fail-safe cutover orchestration runner that coordinates migration and service transitions across the multi-site Bench (`localhost`, `v16.localhost`, `v16rehearsal.localhost`) or creates a dedicated production isolation profile:

1. **Pre-Cutover Verification & Backup Validation:**
   - Automated native database backup (`bench backup --with-files`) with SHA-256 integrity validation and restoration timing measurement.
   - Verification that no pending long-running background jobs or locks exist prior to cutover.
2. **Maintenance Mode & Fail-Closed Rollback:**
   - Dynamic maintenance mode toggle (`maintenance_mode = 1`) during migration with automatic rollback to `0` and restore from pre-cutover backup if any step fails.
3. **Multi-Site Migration Synchronization Drill:**
   - Execute dry-run schema sync and patch execution across sites to prove idempotence and verify zero unintended schema drift.
   - Assert zero data loss on commercial DocTypes (BOQ Header, Structure, Item, Quantity Revision, VO).
4. **Production Bench Operating Profile (`Procfile`, worker allocations, systemd templates):**
   - Provide concrete isolation configuration files for production operations (Gunicorn workers, Background queue workers, Redis socket config).

---

## 2. Directory & Deliverables
Work in isolated directory:
`docs/ai/work-items/multi-site-coordinated-cutover/`

Deliverables required:
1. `SCOPE.md`: Authority, multi-site topology, cutover steps, rollback criteria, timing targets (RTO/RPO), evidence manifest reference.
2. `scripts/orchestrate_cutover.py`: Executable Python CLI script implementing the end-to-end rehearsal, health check, maintenance toggle, and rollback logic.
3. `evidence/multi-site-preflight.log`: Output of preflight checks across all bench sites.
4. `evidence/cutover-drill.log`: Output of the automated migration dry-run and backup verification.
5. `evidence/rollback-drill.log`: Proof of automated recovery on simulated failure.
6. `evidence/operating-profile/`: Isolated production deployment templates (`Procfile`, `supervisord.conf.template`, `redis_queue.conf`).
7. `evidence/MANIFEST.json`: Self-verifying manifest pinning all evidence and scripts by SHA-256.

---

## 3. Allowed Code Modifications
- `docs/ai/work-items/multi-site-coordinated-cutover/*`
- Optional helper script under `scripts/` (e.g., `scripts/bench_cutover_orchestrator.py`).
- **Prohibited:** Any in-place write to live customer database rows, vendor code edits, or touching git remotes.

---

## 4. Verification & Handover
1. Run preflight and dry-run drill: `python3 docs/ai/work-items/multi-site-coordinated-cutover/scripts/orchestrate_cutover.py --dry-run`.
2. Run standard repository linters (`python3 scripts/lint_scope_metadata.py`, `ai_context_check.py`, `schema_drift_checker.py`).
3. Compute SHA-256 digests and write `evidence/MANIFEST.json`.
4. Tear down ephemeral Redis (11000/13000). Leave working tree unstaged for Antigravity audit and commit.
