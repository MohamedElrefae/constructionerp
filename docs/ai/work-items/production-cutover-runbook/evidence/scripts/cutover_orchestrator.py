"""Production cutover orchestrator — pre-flight / dry-run / smoke wrapper (fail-closed).

Session D deliverable for `docs/ai/BRIEFING_PRODUCTION_CUTOVER_RUNBOOK.md` §3 step 2.
Run from the bench root with bench python:

    /home/mohamed/frappe-bench/env/bin/python \
        docs/ai/work-items/production-cutover-runbook/evidence/scripts/cutover_orchestrator.py \
        --site v16.localhost --phase rehearsal --yes

Phases
  preflight   P1 site + governance gate, P2 backup (presence/size/gzip/age),
              P3 disk headroom, P4 redis, P5 database connection + schema
              prerequisites, P6 maintenance mode state.
  dry-run     D1 `run_production_bilingual_migration.py --dry-run` (asserts rc=0,
              zero CONFLICT, zero ABSENT), D2 post-migration verifier.
  smoke       S1 `cutover_smoke_tests.py`.
  rehearsal   preflight + dry-run + smoke, plus the optional maintenance-mode
              demonstration and the optional T-24h backup step.

Contract
  * Fail-closed: any failed gate stops the phase and the process exits 1.
  * This orchestrator never writes to the database and never flips
    `production_mutation_authorized`. The T-0 flag flip stays a human,
    separately-governed act performed directly in site_config.json.
  * `--take-backup` is the only step that writes to the site, and it writes a
    backup, never data.
  * Interactive by default: the apply-facing steps wait for an explicit `y`
    unless `--yes` is given.
"""

import argparse
import gzip
import json
import os
import shutil
import socket
import subprocess
import sys
import time

BENCH = "/home/mohamed/frappe-bench"
APPS = os.path.join(BENCH, "apps")
SITES = os.path.join(BENCH, "sites")
WORK_ITEM = os.path.join(APPS, "construction", "docs", "ai", "work-items",
                         "production-cutover-runbook")
SCRIPTS = os.path.join(WORK_ITEM, "evidence", "scripts")
T5J_SCRIPTS = os.path.join(APPS, "construction", "docs", "ai", "work-items",
                           "production-migration-readiness", "evidence", "scripts")
PY = os.path.join(BENCH, "env", "bin", "python")
BENCH_BIN = os.path.join(os.path.expanduser("~"), ".local", "bin", "bench")

TOPO = [
    "Company", "Account", "Cost Center", "Warehouse", "Project",
    "Item Group", "Customer Group", "Supplier Group", "Territory",
    "Department", "Task", "UOM", "Item", "Customer", "Terms and Conditions",
]
BACKUP_MAX_AGE_S = 24 * 3600
MIN_BACKUP_BYTES = 1024
MIN_DISK_KB = 2 * 1024 * 1024
REDIS_PORTS = (("queue", 11000), ("cache", 13000))

results = []


def log(msg=""):
    print(msg, flush=True)


def record(step, status, detail):
    results.append((step, status, detail))
    log(f"[{status}] {step}: {detail}")


def run(argv, step, expect_rc=0):
    """Run a command, streaming its output, return (rc, text)."""
    log(f"\n--- {step}")
    log("$ " + " ".join(argv))
    proc = subprocess.Popen(argv, cwd=BENCH, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    chunks = []
    for line in proc.stdout:
        chunks.append(line)
        sys.stdout.write(line)
    proc.wait()
    rc = proc.returncode
    text = "".join(chunks)
    log(f"rc={rc}")
    if rc != expect_rc:
        record(step, "FAIL", f"exit {rc}, expected {expect_rc}")
    return rc, text


def confirm(question, assume_yes):
    if assume_yes:
        log(f"(auto-confirmed) {question} -> yes")
        return True
    try:
        answer = input(f"{question} [y/N] ").strip().lower()
    except EOFError:
        answer = ""
    return answer in ("y", "yes")


# ------------------------------------------------------------------ P1

def phase_preflight(site, args):
    cfg_path = os.path.join(SITES, site, "site_config.json")
    if not os.path.isdir(os.path.join(SITES, site)) or not os.path.isfile(cfg_path):
        record("P1 site", "FAIL", f"site {site!r} not found under {SITES}")
        return False
    with open(cfg_path, encoding="utf-8") as handle:
        cfg = json.load(handle)
    authorized = cfg.get("production_mutation_authorized")
    record("P1 site", "PASS",
           f"site present; db_name configured="
           f"{'yes' if cfg.get('db_name') else 'no'}; "
           f"production_mutation_authorized={authorized!r} (gate "
           f"{'open' if authorized is True else 'closed'})")
    if authorized is True and not args.allow_open_gate:
        record("P1 governance", "FAIL",
               "production_mutation_authorized is already true — this orchestrator "
               "only rehearses; confirm the T-0 act was intended and re-run with "
               "--allow-open-gate")
        return False
    return True


# ------------------------------------------------------------------ P2

def _newest_dump(site):
    candidates = []
    for sub in (os.path.join("private", "backups"), "backups"):
        directory = os.path.join(SITES, site, sub)
        if not os.path.isdir(directory):
            continue
        for name in os.listdir(directory):
            if name.endswith((".sql", ".sql.gz", ".sql.bz2", ".sql.xz")):
                candidates.append(os.path.join(directory, name))
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def phase_backup(site, args):
    if args.take_backup:
        argv = [BENCH_BIN, "--site", site, "backup", "--with-files", "--compress"]
        rc, _ = run(argv, "P2 take backup (T-24h step)")
        if rc != 0:
            return False
    dump = _newest_dump(site)
    if dump is None:
        record("P2 backup", "FAIL", "no database dump in sites/<site>/private/backups")
        return False
    size = os.path.getsize(dump)
    age_s = time.time() - os.path.getmtime(dump)
    problems = []
    if size < MIN_BACKUP_BYTES:
        problems.append(f"implausibly small ({size} bytes)")
    if age_s > BACKUP_MAX_AGE_S and not args.force:
        problems.append(f"stale ({age_s / 3600:.1f}h old, >24h)")
    if dump.endswith(".gz"):
        try:
            with gzip.open(dump, "rb") as handle:
                while handle.read(1 << 20):
                    pass
        except OSError as exc:
            problems.append(f"gzip integrity check failed: {exc}")
    if problems:
        record("P2 backup", "FAIL",
               f"{os.path.basename(dump)}: " + "; ".join(problems) +
               (" (--force bypasses the age gate only)" if args.force else ""))
        return False
    record("P2 backup", "PASS",
           f"{os.path.basename(dump)} ({size / (1 << 20):.1f} MiB, "
           f"{age_s / 60:.0f} min old, gzip stream verified end-to-end)")
    return True


# ------------------------------------------------------------------ P3 / P4

def phase_resources():
    free_kb = shutil.disk_usage(os.path.join(SITES)).free // 1024
    if free_kb < MIN_DISK_KB:
        record("P3 disk", "FAIL", f"{free_kb / 1024:.0f} MiB free "
                                  f"(<{MIN_DISK_KB // 1024} MiB)")
        return False
    record("P3 disk", "PASS", f"{free_kb / (1 << 20):.2f} GiB free")
    return True


def phase_redis():
    down = []
    for label, port in REDIS_PORTS:
        try:
            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
            sock.sendall(b"PING\r\n")
            if not sock.recv(64).startswith(b"+PONG"):
                down.append(f"{label}:{port} (no PONG)")
            sock.close()
        except OSError as exc:
            down.append(f"{label}:{port} ({exc})")
    if down:
        record("P4 redis", "FAIL", "unreachable: " + ", ".join(down) +
               " — start: redis-server config/redis_queue.conf --daemonize yes; "
               "redis-server config/redis_cache.conf --daemonize yes")
        return False
    record("P4 redis", "PASS", "queue:11000 and cache:13000 answer PING")
    return True


# ------------------------------------------------------------------ P5

def phase_schema(site):
    sys.path.insert(0, os.path.join(APPS, "construction"))
    import frappe

    frappe.init(site=site, sites_path=SITES)
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        schema = frappe.conf.db_name
        missing = []
        non_utf8 = []
        registry = json.load(open(os.path.join(
            APPS, "construction", "construction", "data", "bilingual",
            "bilingual_registry.json"), encoding="utf-8"))
        for doctype in TOPO:
            meta = registry["doctypes"].get(doctype) or {}
            table = "tab" + doctype
            cols = {r.COLUMN_NAME for r in frappe.db.sql(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                (schema, table), as_dict=True)}
            for field in (meta.get("arabic_field"), meta.get("norm_field")):
                if field not in cols:
                    missing.append(f"{table}.{field}")
            coll = frappe.db.sql(
                "SELECT TABLE_COLLATION FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                (schema, table), as_dict=True)
            if not coll or not (coll[0].TABLE_COLLATION or "").startswith("utf8mb4"):
                non_utf8.append(table)
        rows = frappe.db.count("Account")
        if missing or non_utf8:
            record("P5 schema", "FAIL",
                   f"missing columns={missing or 'none'}; "
                   f"non-utf8mb4={non_utf8 or 'none'}")
            return False
        record("P5 schema", "PASS",
               f"connection OK (site db name redacted); arabic+norm columns and "
               f"utf8mb4 on all {len(TOPO)} cutover tables; Account rows={rows}")
        return True
    finally:
        try:
            frappe.db.close()
        except Exception:  # noqa: BLE001 - close is best-effort
            pass


# ------------------------------------------------------------------ P6

def read_maintenance(site):
    with open(os.path.join(SITES, site, "site_config.json"), encoding="utf-8") as handle:
        return json.load(handle).get("maintenance_mode")


def phase_maintenance(site, args):
    state = read_maintenance(site)
    if not args.demo_maintenance:
        record("P6 maintenance", "PASS", f"maintenance_mode={state} (read-only report)")
        return True
    on_rc, _ = run([BENCH_BIN, "--site", site, "set-maintenance-mode", "on"],
                   "P6a maintenance mode ON (demonstration)")
    if on_rc != 0 or read_maintenance(site) != 1:
        run([BENCH_BIN, "--site", site, "set-maintenance-mode", "off"],
            "P6b restore maintenance mode off after failed ON check")
        return False
    off_rc, _ = run([BENCH_BIN, "--site", site, "set-maintenance-mode", "off"],
                    "P6b maintenance mode OFF (restored immediately)")
    if off_rc != 0 or read_maintenance(site) != 0:
        record("P6 maintenance", "FAIL", "could not restore maintenance_mode=0")
        return False
    record("P6 maintenance", "PASS",
           "toggled 0 -> 1 -> 0 with `bench set-maintenance-mode`; site left serving")
    return True


# ------------------------------------------------------------------ D1 / D2 / S1

def phase_dry_run(site, args):
    if not confirm("Run the migration dry-run rehearsal (read-only, zero writes)?",
                   args.yes):
        record("D1 dry-run", "FAIL", "operator declined")
        return False
    argv = [PY, os.path.join(T5J_SCRIPTS, "run_production_bilingual_migration.py"),
            "--site", site, "--dry-run", "--allow-sites", args.allow_sites]
    if args.force:
        argv.append("--force")
    rc, text = run(argv, "D1 migration runner --dry-run")
    if rc != 0:
        return False
    classify = None
    for line in text.splitlines():
        if line.startswith("CLASSIFY "):
            try:
                classify = json.loads(line[len("CLASSIFY "):])
            except ValueError:
                classify = None
    if classify is None:
        record("D1 dry-run", "FAIL", "no CLASSIFY summary in runner output")
        return False
    if classify.get("CONFLICT") or classify.get("ABSENT"):
        record("D1 dry-run", "FAIL",
               f"fail-closed classification: {json.dumps(classify, sort_keys=True)}")
        return False
    total = classify.get("WOULD_WRITE", 0) + classify.get("ALREADY_APPLIED", 0)
    if total != 188:
        record("D1 dry-run", "FAIL", f"classified {total} rows, expected 188")
        return False
    record("D1 dry-run", "PASS",
           f"rc=0, 0 writes, 0 conflicts, 0 absent; "
           f"{json.dumps(classify, sort_keys=True)}")
    return True


def phase_verify(site, args):
    argv = [PY, os.path.join(T5J_SCRIPTS, "verify_production_bilingual_migration.py"),
            "--site", site]
    rc, text = run(argv, "D2 post-migration verifier")
    if rc != 0:
        return False
    if "VERIFY RESULT: PASS" not in text:
        record("D2 verifier", "FAIL", "no PASS verdict in verifier output")
        return False
    record("D2 verifier", "PASS", "counts / norms / frozen fields / trees / probes PASS")
    return True


def phase_smoke(site, args):
    baseline = os.path.join(WORK_ITEM, "evidence", "latency-baseline.json")
    argv = [PY, os.path.join(SCRIPTS, "cutover_smoke_tests.py"),
            "--site", site, "--expect-gate",
            "open" if args.allow_open_gate else "closed",
            "--baseline", baseline]
    if args.establish_baseline:
        argv += ["--write-baseline", baseline]
    if args.allow_maintenance:
        argv.append("--allow-maintenance")
    if args.skip_latency:
        argv.append("--skip-latency")
    rc, text = run(argv, "S1 post-cutover smoke tests")
    if rc != 0:
        return False
    if "SMOKE RESULT: PASS" not in text:
        record("S1 smoke", "FAIL", "no PASS verdict in smoke output")
        return False
    record("S1 smoke", "PASS", "S1-S8 checks green (advisories reported inline)")
    return True


# ------------------------------------------------------------------ driver

def summary(ok_all):
    log("\n" + "=" * 70)
    log("CUTOVER ORCHESTRATOR SUMMARY")
    for step, status, detail in results:
        log(f"  [{status:4}] {step}: {detail}")
    verdict = "PASS" if ok_all else "FAIL"
    log(f"RESULT: {verdict}")
    return 0 if ok_all else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="v16.localhost")
    parser.add_argument("--phase", choices=("preflight", "dry-run", "smoke",
                                            "rehearsal"),
                        default="rehearsal")
    parser.add_argument("--yes", action="store_true",
                        help="skip the interactive confirmations")
    parser.add_argument("--take-backup", action="store_true",
                        help="run `bench backup --with-files` first (T-24h step)")
    parser.add_argument("--demo-maintenance", action="store_true",
                        help="demonstrate set-maintenance-mode on -> off")
    parser.add_argument("--force", action="store_true",
                        help="bypass ONLY the backup age gate")
    parser.add_argument("--allow-sites", default="v16.localhost",
                        help="development allowlist passed to the runner")
    parser.add_argument("--allow-open-gate", action="store_true",
                        help="proceed although production_mutation_authorized is true")
    parser.add_argument("--allow-maintenance", action="store_true",
                        help="accept maintenance_mode=1 during smoke tests")
    parser.add_argument("--establish-baseline", action="store_true",
                        help="let the smoke test create the latency baseline pin "
                             "when none exists yet")
    parser.add_argument("--skip-latency", action="store_true",
                        help="diagnostic only — never use for a real cutover")
    args = parser.parse_args()

    log(f"CUTOVER ORCHESTRATOR site={args.site} phase={args.phase} "
        f"utc={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    log("Invariants: no database write; production_mutation_authorized is never "
        "set by this program; fail-closed on every gate.\n")

    ok_all = True
    if args.phase in ("preflight", "rehearsal"):
        ok_all &= phase_preflight(args.site, args)
        if ok_all:
            ok_all &= phase_backup(args.site, args)
        if ok_all:
            ok_all &= phase_resources()
        if ok_all:
            ok_all &= phase_redis()
        if ok_all:
            ok_all &= phase_schema(args.site)
        if ok_all:
            ok_all &= phase_maintenance(args.site, args)
    if ok_all and args.phase in ("dry-run", "rehearsal"):
        ok_all &= phase_dry_run(args.site, args)
        if ok_all:
            ok_all &= phase_verify(args.site, args)
    if ok_all and args.phase in ("smoke", "rehearsal"):
        ok_all &= phase_smoke(args.site, args)
    return summary(ok_all)


if __name__ == "__main__":
    sys.exit(main())
