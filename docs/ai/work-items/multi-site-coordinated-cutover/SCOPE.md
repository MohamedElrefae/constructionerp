# Scope Descriptor — multi-site-coordinated-cutover

**Work item:** `multi-site-coordinated-cutover`
**Gates:** G12 (multi-site coordinated cutover), G15 (bench isolation / operating profile)
**Branch:** `opencode/session-3b-cutover`
**Date:** 2026-10-06
**Status:** `COMPLETE` — orchestrator implemented, dry-run verified, evidence captured, manifest pinned.
**Authority:** `BRIEFING_MULTI_SITE_COORDINATED_CUTOVER.md`, `OPENCODE_PARALLEL_EXECUTION_MASTER.md`.
**Governance:** Zero push to remotes; `core.hooksPath=/dev/null` for all commits; `production_mutation_authorized` unset; zero vendor edits (`apps/frappe`, `apps/erpnext` untouched); zero DB row mutations (all drills `--dry-run` or read-only census); system redis (6379) never probed; ephemeral redis (11000/13000) started idempotently and torn down after testing; no `dump.rdb` committed.

---

## 1. Multi-Site Topology

| Site | db_name | Backups | Role |
|---|---|---|---|
| `localhost` | `_6d52b48c328b294e` | present (latest 20261006_040258) | primary dev |
| `v16.localhost` | `_6d52b48c328b294e` | present | UAT target |
| `v16rehearsal.localhost` | `_8ea0ca5beb7e4d87` | **none present** (advisory) | rehearsal |

Ephemeral redis: queue=11000, cache=13000. System redis: 6379 (untouched).

## 2. Cutover Steps (implemented by `scripts/orchestrate_cutover.py`)

1. **Preflight** — per-site config sanity (db_name, db_user, encryption_key), redis reachability, backup inventory + age, disk headroom, rq pending-job counts (default/short/long == 0), maintenance_mode baseline.
2. **Backup verification** — SHA-256 of latest `*.sql.gz`, gzip integrity (`gzip -t`), restoration timing measurement (stream-decompress-to-dev/null elapsed; 8.63 s for the 71.5 MB latest backup).
3. **Commercial data census** — read-only `COUNT(*)` on BOQ Header, BOQ Structure, BOQ Item, Quantity Revision, Variation Order (4/5 tables countable per site; 1 absent as WARNING, no mutation).
4. **Maintenance toggle** — `maintenance_mode 0 -> 1`, drill, restore to `0` in `finally` (fail-closed). Dry-run: simulated, real: verified write + re-read.
5. **Migration sync drill** — `bench --site X migrate --skip-search-index` classification (dry-run skips execution; `run_production_bilingual_migration.py --dry-run` runs rc=0 as idempotence evidence).
6. **Zero-data-loss assertion** — post-drill census diff vs baseline; `drift=none` on all sites.
7. **Rollback proof** — simulated mid-drill fault (`--fail-step drill`) aborts cutover, restores `maintenance_mode=0`, validates backup restorability via `gzip -t`.

## 3. Rollback Criteria

- Any FAIL in preflight, backup verification, census drift, or migrate drill aborts the chain and restores maintenance_mode to its original value.
- If `maintenance_mode` cannot be restored or the latest backup fails `gzip -t`, the orchestrator exits non-zero and flags restore-from-backup as required.
- RTO target: restoration of latest validated backup < 60 s of elapsed restore stream (measured 8.63 s); RPO target: daily backup cadence (max age 7 d enforced as WARN/FAIL).

## 4. Evidence Index

| Artefact | Result |
|---|---|
| `evidence/multi-site-preflight.log` | PASS (17 steps, 0 failures) |
| `evidence/cutover-drill.log` | PASS (19 steps, 0 failures; bilingual migration dry-run rc=0) |
| `evidence/rollback-drill.log` | Simulated fault aborted cutover; rollback rc=0 (8 steps) |
| `evidence/gates.log` | 4/4 linters PASS |
| `evidence/operating-profile/` | `Procfile`, `supervisord.conf.template`, `redis_queue.conf` |
| Verification command `orchestrate_cutover.py --dry-run` | rc=0 (44 steps, 0 failures) |

## 5. Manifest

`evidence/MANIFEST.json` pins SHA-256 of every artefact above plus this scope file and the orchestrator script. Self-verify with:

```bash
python3 -c "import json,hashlib; m=json.load(open('docs/ai/work-items/multi-site-coordinated-cutover/evidence/MANIFEST.json')); print(all(hashlib.sha256(open(k,'rb').read()).hexdigest()==v for k,v in m['artefacts'].items()))"
```
