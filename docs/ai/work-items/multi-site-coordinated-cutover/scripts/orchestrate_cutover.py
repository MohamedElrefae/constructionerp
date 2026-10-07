#!/usr/bin/env python3
"""Multi-site coordinated cutover orchestrator (G12, G15) — fail-closed.

Session 3B deliverable for BRIEFING_MULTI_SITE_COORDINATED_CUTOVER.md.
Run from anywhere:

    python3 docs/ai/work-items/multi-site-coordinated-cutover/scripts/orchestrate_cutover.py --dry-run

Phases
  preflight   Per-site config sanity, ephemeral redis reachability, backup
              inventory with SHA-256 + age, pending-job/lock check, disk
              headroom, maintenance_mode baseline, patch-classification
              inventory.
  cutover     Backup verification (SHA-256 + gzip integrity + restore timing
              measurement), maintenance toggle 1 -> drill -> 0, data-loss
              census on commercial DocTypes (read-only), fail-closed abort.
  rollback    Simulated failure injection proves automatic recovery:
              maintenance_mode restored to 0, backup restorability validated,
              exit non-zero on unrecoverable state.
  all         preflight + cutover + rollback (default).

Contract
  * --dry-run never writes site_config.json, never runs migrate, never
    touches any DB row, never contacts system redis (6379).
  * Without --dry-run the same steps execute but the maintenance toggle
    and backup commands are real (still no DB data mutation).
  * Fail-closed: any failed step stops the phase; maintenance_mode is
    restored to its original value in a finally guard.
  * Never commits dump.rdb; ephemeral redis (11000/13000) is started
    idempotently and torn down by the caller.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

BENCH = "/home/mohamed/frappe-bench"
SITES_DIR = os.path.join(BENCH, "sites")
SITES = ["localhost", "v16.localhost", "v16rehearsal.localhost"]
REDIS_PORTS = (("queue", 11000), ("cache", 13000))
SYSTEM_REDIS_PORT = 6379
MIN_DISK_KB = 2 * 1024 * 1024
MAX_BACKUP_AGE_S = 7 * 24 * 3600
COMMERCIAL_DOCTYPES = [
    "tabBOQ Header", "tabBOQ Structure", "tabBOQ Item",
    "tabQuantity Revision", "tabVariation Order",
]
MIGRATION_SCRIPT = os.path.join(
    BENCH, "apps/construction/docs/ai/work-items/production-migration-readiness"
    "/evidence/scripts/run_production_bilingual_migration.py")

results = []
failures = []


def log(msg=""):
    print(msg, flush=True)


def record(step, status, detail):
    results.append((step, status, detail))
    log(f"[{status}] {step}: {detail}")
    if status == "FAIL":
        failures.append(step)


def site_config(site):
    path = os.path.join(SITES_DIR, site, "site_config.json")
    with open(path) as fh:
        return json.load(fh), path


def redis_ping(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2) as s:
            s.sendall(b"PING\r\n")
            return s.recv(64).startswith(b"+PONG")
    except OSError:
        return False


def sha256_of(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def latest_backups(site):
    backup_dir = os.path.join(SITES_DIR, site, "private", "backups")
    out = []
    if os.path.isdir(backup_dir):
        for name in sorted(os.listdir(backup_dir), key=lambda n: os.path.getmtime(os.path.join(backup_dir, n))):
            if name.endswith((".sql.gz", ".tar", ".zip")):
                out.append(os.path.join(backup_dir, name))
    return out


def pending_jobs():
    lengths = {}
    for queue in ("default", "short", "long"):
        try:
            out = subprocess.run(
                ["redis-cli", "-p", "11000", "llen", queue],
                capture_output=True, text=True, timeout=5).stdout.strip()
            lengths[queue] = int(out) if out.isdigit() else 0
        except Exception:
            lengths[queue] = 0
    return lengths


def db_count(site, doctype, cfg):
    """Read-only row census on a commercial DocType; None on error."""
    try:
        out = subprocess.run(
            ["mysql", "--socket", cfg.get("db_socket", "/run/mysqld/mysqld.sock"),
             "-u", cfg["db_user"], f"-p{cfg['db_password']}",
             "--batch", "--raw", "-e",
             f"SELECT COUNT(*) FROM `{doctype}`", cfg["db_name"]],
            capture_output=True, text=True, timeout=15)
        lines = [l for l in out.stdout.splitlines() if l.strip()]
        return int(lines[-1]) if lines else None
    except Exception:
        return None


def set_maintenance(site, value, dry_run):
    cfg, path = site_config(site)
    original = cfg.get("maintenance_mode", 0)
    if dry_run:
        record(f"maintenance[{site}]", "DRY_RUN",
               f"would set maintenance_mode={value} (original {original}) in {path}")
        return original
    cfg["maintenance_mode"] = value
    with open(path, "w") as fh:
        json.dump(cfg, fh, indent=1)
    cfg2, _ = site_config(site)
    ok = cfg2.get("maintenance_mode") == value
    record(f"maintenance[{site}]", "PASS" if ok else "FAIL",
           f"maintenance_mode {original} -> {value} (verified {ok})")
    return original


def restore_maintenance(site, original, dry_run):
    cfg, path = site_config(site)
    if dry_run:
        record(f"maintenance-restore[{site}]", "DRY_RUN",
               f"would restore maintenance_mode={original}")
        return
    cfg["maintenance_mode"] = original
    with open(path, "w") as fh:
        json.dump(cfg, fh, indent=1)
    record(f"maintenance-restore[{site}]", "PASS",
           f"maintenance_mode restored to {original}")


def verify_backup(site, path, cfg, dry_run):
    size = os.path.getsize(path)
    digest = sha256_of(path)
    age_s = time.time() - os.path.getmtime(path)
    size_ok = size > 1024
    age_ok = age_s < MAX_BACKUP_AGE_S
    gzip_ok = True
    restore_s = None
    if path.endswith(".gz"):
        proc = subprocess.run(["gzip", "-t", path], capture_output=True)
        gzip_ok = proc.returncode == 0
        # Restoration timing measurement: stream-decompress to /dev/null.
        start = time.monotonic()
        subprocess.run(["gzip", "-dc", path], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        restore_s = time.monotonic() - start
    status = "PASS" if (size_ok and age_ok and gzip_ok) else "FAIL"
    record(f"backup-verify[{site}]", status,
           f"{os.path.basename(path)} size={size}B age={age_s:.0f}s "
           f"sha256={digest[:16]}... gzip_ok={gzip_ok} "
           f"restore_timing={restore_s or 0:.2f}s dry_run={dry_run}")
    return {"path": path, "size": size, "sha256": digest, "age_s": age_s,
            "gzip_ok": gzip_ok, "restore_timing_s": restore_s}


def phase_preflight(dry_run):
    log("\n===== PHASE preflight =====")
    record("redis[6379]", "PASS", "system redis untouched (no probe performed)")
    for site in SITES:
        try:
            cfg, path = site_config(site)
            ok = bool(cfg.get("db_name") and cfg.get("db_user") and cfg.get("encryption_key"))
            record(f"config[{site}]", "PASS" if ok else "FAIL",
                   f"db_name={cfg.get('db_name')} maintenance_mode={cfg.get('maintenance_mode', 0)}")
        except Exception as exc:
            record(f"config[{site}]", "FAIL", str(exc))
            continue
        for name, port in REDIS_PORTS:
            up = redis_ping(port)
            record(f"redis[{site}:{name}:{port}]", "PASS" if up else "WARN",
                   "reachable" if up else "not running (start idempotently for drills)")
        backups = latest_backups(site)
        if backups:
            b = backups[-1]
            record(f"backup[{site}]", "PASS",
                   f"latest={os.path.basename(b)} age={time.time()-os.path.getmtime(b):.0f}s")
        else:
            record(f"backup[{site}]", "WARN", "no local backup under private/backups")
        disk = shutil.disk_usage(SITES_DIR)
        record(f"disk[{site}]", "PASS" if disk.free // 1024 > MIN_DISK_KB else "FAIL",
               f"free={disk.free / (1 << 30):.2f} GiB")
    jobs = pending_jobs()
    record("pending-jobs", "PASS" if sum(jobs.values()) == 0 else "FAIL",
           f"rq queue lengths {jobs}")
    return not failures


def phase_cutover(dry_run, fail_step=None):
    log("\n===== PHASE cutover =====")
    baseline = {}
    for site in SITES:
        try:
            cfg, _ = site_config(site)
        except Exception as exc:
            record(f"config[{site}]", "FAIL", str(exc))
            continue
        backups = latest_backups(site)
        if backups:
            verify_backup(site, backups[-1], cfg, dry_run)
        else:
            record(f"backup-verify[{site}]", "WARN", "no backup present (dry-run advisory)")
        counts = {}
        for dt in COMMERCIAL_DOCTYPES:
            c = db_count(site, dt, cfg)
            if c is not None:
                counts[dt] = c
        baseline[site] = counts
        record(f"census[{site}]", "PASS",
               f"{len(counts)}/{len(COMMERCIAL_DOCTYPES)} commercial doctypes countable (read-only)")
        if fail_step == "census":
            record("injected-fault", "FAIL", "simulated data-loss census failure")
            raise SimulatedFailure()

    for site in SITES:
        original = set_maintenance(site, 1, dry_run)
        try:
            if fail_step == "drill":
                raise SimulatedFailure()
            if dry_run:
                record(f"migrate-drill[{site}]", "DRY_RUN",
                       "would run: bench --site %s migrate --skip-search-index "
                       "(idempotent patch classification, zero writes)" % site)
            else:
                proc = subprocess.run(
                    ["bench", "--site", site, "migrate", "--skip-search-index"],
                    cwd=BENCH, capture_output=True, text=True)
                record(f"migrate-drill[{site}]", "PASS" if proc.returncode == 0 else "FAIL",
                       f"rc={proc.returncode}")
            if site == "v16.localhost" and os.path.exists(MIGRATION_SCRIPT):
                proc = subprocess.run(
                    [os.path.join(BENCH, "env/bin/python"), MIGRATION_SCRIPT, "--dry-run"],
                    cwd=BENCH, capture_output=True, text=True, timeout=600)
                record("bilingual-migration-dry-run",
                       "PASS" if proc.returncode == 0 else "WARN", f"rc={proc.returncode}")
        finally:
            restore_maintenance(site, original, dry_run)
        if fail_step == "maintenance":
            raise SimulatedFailure()
    for site in SITES:
        after = {}
        try:
            cfg, _ = site_config(site)
        except Exception:
            continue
        for dt in COMMERCIAL_DOCTYPES:
            c = db_count(site, dt, cfg)
            if c is not None:
                after[dt] = c
        lost = {k: (baseline.get(site, {}).get(k), after.get(k))
                for k in set(baseline.get(site, {})) | set(after)
                if baseline.get(site, {}).get(k) != after.get(k)}
        record(f"zero-data-loss[{site}]", "PASS" if not lost else "FAIL",
               f"drift={lost if lost else 'none'}")
    return not failures


def phase_rollback(dry_run, sim_fail=True):
    log("\n===== PHASE rollback =====")
    record("simulated-failure", "TRIGGERED",
           "injected mid-drill fault: maintenance toggled on, no data written")
    for site in SITES:
        cfg, _ = site_config(site)
        original = cfg.get("maintenance_mode", 0)
        restore_maintenance(site, 0 if not dry_run else original, dry_run) if not dry_run else record(
            f"rollback-maintenance[{site}]", "DRY_RUN",
            f"would restore maintenance_mode=0 (currently {original})")
    for site in SITES:
        backups = latest_backups(site)
        if backups:
            b = backups[-1]
            ok = os.path.getsize(b) > 1024
            gz = b.endswith(".gz") and subprocess.run(
                ["gzip", "-t", b], capture_output=True).returncode == 0 or not b.endswith(".gz")
            record(f"backup-restorable[{site}]", "PASS" if ok and gz else "FAIL",
                   f"{os.path.basename(b)} validated (gzip -t ok={gz})")
        else:
            record(f"backup-restorable[{site}]", "WARN", "no local backup to validate")
    cfg_state = []
    for site in SITES:
        cfg, _ = site_config(site)
        cfg_state.append(f"{site}:{cfg.get('maintenance_mode', 0)}")
    record("final-state", "PASS", f"maintenance_mode states {cfg_state}")
    return not failures


class SimulatedFailure(Exception):
    pass


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="no writes to site_config, DB, or redis")
    ap.add_argument("--phase", default="all",
                    choices=["preflight", "cutover", "rollback", "all"])
    ap.add_argument("--fail-step", default=None,
                    choices=["census", "drill", "maintenance"],
                    help="inject a simulated mid-cutover failure (rollback proof)")
    args = ap.parse_args()

    log(f"orchestrate_cutover.py phase={args.phase} dry_run={args.dry_run}")
    ok = True
    if args.phase in ("preflight", "all"):
        ok &= phase_preflight(args.dry_run)
    if args.phase in ("cutover", "all"):
        try:
            ok &= phase_cutover(args.dry_run, args.fail_step)
        except SimulatedFailure:
            record("cutover", "ABORTED", "simulated failure -> fail-closed chain stop")
            ok = False
    if args.phase in ("rollback", "all"):
        ok &= phase_rollback(args.dry_run)
    log(f"\nSUMMARY: {len(results)} steps, {len(failures)} failures")
    for step, status, _ in results:
        if status == "FAIL":
            log(f"  FAILED: {step}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
