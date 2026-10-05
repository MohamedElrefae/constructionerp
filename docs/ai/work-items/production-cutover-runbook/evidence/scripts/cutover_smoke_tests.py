"""Post-cutover smoke tests — Tier 5K / Session D deliverable (read-only, fail-closed).

Run from the bench root with bench python:

    /home/mohamed/frappe-bench/env/bin/python \
        docs/ai/work-items/production-cutover-runbook/evidence/scripts/cutover_smoke_tests.py \
        --site v16.localhost --baseline <latency-baseline.json>

Checks (gating unless marked ADVISORY):

  S1  Site bootstrap: registry loads, the 15 cutover doctypes carry their
      `*_arabic` + `*_norm` columns, every one of those tables is utf8mb4.
  S2  Governance gate: `production_mutation_authorized` in site_config.json is
      reported and asserted against `--expect-gate closed|open`.
  S3  Link search latency on the governed desk path
      (`searchable_dropdown.searchable_link_search` — the surface ADR
      `bilingual-performance-sla.md` Tier 1 pins, and the path a desk link field
      actually calls through `desk_link_search.dispatcher`):
        * correctness: every probe must return the row it queried;
        * absolute ceiling: nearest-rank P95 <= `--budget-ms` (1.50 ms),
          min-of-rounds over `--rounds` rounds;
        * regression: against `--baseline`, a doctype that was compliant at
          baseline must stay <= `--budget-ms`; a doctype already BREACHING at
          baseline may not regress beyond `baseline_p95 * --regression-tolerance`.
      `--write-baseline` establishes the pin (sanity-capped by
      `--baseline-cap-ms`, retried up to `--establish-attempts` times while the
      bench is contended) and reports absolute compliance as ADVISORY for that
      one run; every later run compares against it.
  S4  Transactional link sidecar (`transaction_link_search.search_transactions`)
      latency — measured and reported per target as ADVISORY: that surface has
      no separately ratified latency budget, so it never blocks a cutover on its
      own; the numbers are surfaced for the owner.
  S5  Financial report generation: `Balance Sheet` + `Profit and Loss Statement`
      through the governed `localized_report` endpoint, `en` mode, on the
      ledger-bearing company, asserted read-only (Account and GL Entry counts
      unchanged).
  S6  Print format preview: render a recent document of every active
      transaction doctype through `frappe.get_print`; doctypes with no documents
      are disclosed as SKIPPED, never silently passed.
  S7  Maintenance mode is `0` after cutover (override with
      `--allow-maintenance` while the window is still open).
  S8  Redis queue (11000) and cache (13000) answer PING.

Environment note: the process chdirs into `sites/` because Frappe resolves
`assets/assets.json` relative to the working directory — that is where bench
runs every server-side job.

Privacy: no Arabic value, no document payload and no report cell is ever printed
or written — only counts, verdicts and latencies.

Exit 0 = PASS, 1 = FAIL. Read-only: one transaction is opened and rolled back.
"""

import argparse
import json
import math
import os
import socket
import sys
import time

BENCH = "/home/mohamed/frappe-bench"
APPS = os.path.join(BENCH, "apps")
SITES = os.path.join(BENCH, "sites")
sys.path.insert(0, os.path.join(APPS, "construction"))

import frappe  # noqa: E402

TOPO = [
    "Company", "Account", "Cost Center", "Warehouse", "Project",
    "Item Group", "Customer Group", "Supplier Group", "Territory",
    "Department", "Task", "UOM", "Item", "Customer", "Terms and Conditions",
]
TX_TARGETS = ("Sales Order", "Purchase Order", "Material Request", "Sales Invoice")
REPORTS = ("Balance Sheet", "Profit and Loss Statement")
PRINT_DOCTYPES = ("Purchase Order", "Sales Invoice", "Stock Entry", "Material Request")
REDIS_PORTS = (("queue", 11000), ("cache", 13000))
SURFACE = "searchable_dropdown.searchable_link_search"

fails = []
advisories = []
passes = []


def log(msg):
    print(msg, flush=True)


def ok(check, msg):
    passes.append(check)
    log(f"{check} PASS: {msg}")


def fail(check, msg):
    fails.append(check)
    log(f"{check} FAIL: {msg}")


def advise(check, msg):
    advisories.append(check)
    log(f"{check} ADVISORY: {msg}")


def nearest_rank_p95(samples):
    """Nearest-rank P95 (the ADR Tier-1 statistic), no interpolation."""
    ordered = sorted(samples)
    rank = max(1, math.ceil(0.95 * len(ordered)))
    return ordered[rank - 1]


def median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def registry():
    path = os.path.join(APPS, "construction", "construction", "data",
                        "bilingual", "bilingual_registry.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# ------------------------------------------------------------------ S1

def check_bootstrap(reg):
    schema = frappe.conf.db_name
    missing = []
    bad_collation = []
    for doctype in TOPO:
        meta = reg["doctypes"].get(doctype)
        if not meta:
            missing.append(f"{doctype}:absent-from-registry")
            continue
        table = "tab" + doctype
        cols = {r.COLUMN_NAME for r in frappe.db.sql(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
            (schema, table), as_dict=True)}
        for field in (meta["arabic_field"], meta["norm_field"]):
            if field not in cols:
                missing.append(f"{table}.{field}")
        coll = frappe.db.sql(
            "SELECT TABLE_COLLATION FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
            (schema, table), as_dict=True)
        if not coll or not (coll[0].TABLE_COLLATION or "").startswith("utf8mb4"):
            bad_collation.append(table)
    if missing:
        fail("S1", f"schema columns missing (custom-field patch not applied): {missing}")
    elif bad_collation:
        fail("S1", f"non-utf8mb4 tables: {bad_collation}")
    else:
        ok("S1", f"registry loaded, arabic+norm columns present and utf8mb4 on "
                 f"all {len(TOPO)} cutover doctypes")


# ------------------------------------------------------------------ S2

def check_gate(site, expect_gate):
    cfg_path = os.path.join(SITES, site, "site_config.json")
    if not os.path.isfile(cfg_path):
        fail("S2", f"site_config.json missing for {site}")
        return
    with open(cfg_path, encoding="utf-8") as handle:
        cfg = json.load(handle)
    authorized = cfg.get("production_mutation_authorized")
    state = "open" if authorized is True else "closed"
    if state != expect_gate:
        fail("S2", f"production_mutation_authorized={authorized!r} but this run "
                   f"expects gate={expect_gate}")
    else:
        ok("S2", f"governance gate {state} as expected "
                 f"(production_mutation_authorized={authorized!r})")


# ------------------------------------------------------------------ S3

def _link_search(doctype, query):
    from construction.searchable_dropdown.api.search import searchable_link_search
    return searchable_link_search(doctype=doctype, txt=query, filters={},
                                  page_length=20, searchfield="name")


def check_link_latency(reg, args, baseline):
    """Probe, then gate. Establish mode retries while the bench is contended."""
    establish = args.write_baseline is not None and baseline is None
    attempts = args.establish_attempts if establish else 1
    for attempt in range(1, attempts + 1):
        load = os.getloadavg()
        if attempts > 1:
            log(f"S3 attempt {attempt}/{attempts} "
                f"(load1={load[0]:.2f} load5={load[1]:.2f})")
        measurements, misses = _measure_link_latency(
            reg, args.rounds, args.samples, args.warmup, args.budget_ms)
        if misses:
            fail("S3", f"link search missed the queried row: {misses}")
            return
        verdict = _judge_link_latency(measurements, args, baseline, establish)
        if verdict != "retry" or attempt == attempts:
            if verdict == "retry":
                fail("S3", "baseline still above --baseline-cap-ms after "
                           f"{attempts} attempts on a contended bench "
                           f"(worst {max(v['p95'] for v in measurements.values()):.3f} "
                           "ms) — quiesce concurrent bench/test jobs and rerun")
            return
        log(f"S3 attempt {attempt} unusable "
            f"(worst {max(v['p95'] for v in measurements.values()):.3f} ms, "
            f"cap {args.baseline_cap_ms} ms) — bench contended; waiting "
            f"{args.establish_pause}s")
        time.sleep(args.establish_pause)


def _measure_link_latency(reg, rounds, samples, warmup, budget_ms):
    """Timed probe of every cutover doctype. Returns (measurements, misses)."""
    measurements = {}
    misses = []
    for doctype in TOPO:
        meta = reg["doctypes"][doctype]
        if not (meta.get("search") or {}).get("enabled"):
            fail("S3", f"{doctype}: registry search not enabled")
            return {}, [f"{doctype}: registry search disabled"]
        rows = frappe.get_all(
            doctype, filters={meta["arabic_field"]: ("!=", "")},
            fields=["name", meta["arabic_field"],
                    meta.get("english_field") or "name"],
            limit_page_length=1)
        if not rows:
            fail("S3", f"{doctype}: no populated row to probe")
            return {}, [f"{doctype}: no populated row"]
        row = rows[0]
        probes = [("ar", row[meta["arabic_field"]]),
                  ("en", row.get(meta.get("english_field") or "name") or row["name"])]
        for lang, query in probes:
            result = _link_search(doctype, query)  # correctness, untimed
            values = {r.get("value") for r in (result or []) if isinstance(r, dict)}
            if row["name"] not in values:
                misses.append(f"{doctype}[{lang}]")
            best = None
            times = []
            for _ in range(rounds):
                for _ in range(warmup):
                    _link_search(doctype, query)
                times = []
                for _ in range(samples):
                    start = time.perf_counter()
                    _link_search(doctype, query)
                    times.append((time.perf_counter() - start) * 1000.0)
                round_p95 = nearest_rank_p95(times)
                best = round_p95 if best is None else min(best, round_p95)
            measurements[f"{doctype}/{lang}"] = {
                "p95": round(best, 3),
                "p50": round(median(times), 3),
                "compliant": bool(best <= budget_ms),
            }
    return measurements, misses


def _judge_link_latency(measurements, args, baseline, establish):
    """Apply the S3 contract. Returns 'retry' only while establishing a pin."""
    if not measurements:
        return "done"
    worst_key = max(measurements, key=lambda k: measurements[k]["p95"])
    worst = measurements[worst_key]["p95"]

    if establish:
        over_cap = [f"{k}={v['p95']:.3f}ms" for k, v in measurements.items()
                    if v["p95"] > args.baseline_cap_ms]
        if over_cap:
            return "retry"
        payload = {
            "site": args.site,
            "captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "surface": SURFACE,
            "protocol": (f"min-of-rounds nearest-rank P95, rounds={args.rounds}, "
                         f"samples={args.samples}, warmup={args.warmup}"),
            "budget_ms": args.budget_ms,
            "expect_gate": args.expect_gate,
            "probes": measurements,
        }
        with open(args.write_baseline, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        ok("S3", f"correctness {len(measurements)}/{len(measurements)} probes hit; "
                 f"baseline written to {os.path.basename(args.write_baseline)} "
                 f"(worst {worst:.3f} ms at {worst_key})")
        breach = sorted(k for k, v in measurements.items() if not v["compliant"])
        if breach:
            advise("S3-absolute", f"ADR Tier-1 ceiling {args.budget_ms:.2f} ms breached "
                                  f"at baseline by {len(breach)} probes: {breach} — "
                                  f"recorded in the pin, non-regression enforced from now on")
        else:
            ok("S3-absolute", f"every probe within the ADR Tier-1 ceiling "
                              f"{args.budget_ms:.2f} ms (worst {worst:.3f} ms)")
        return "done"

    hard_failures = []
    for key, value in sorted(measurements.items()):
        if baseline is None:
            budget, why = args.budget_ms, "absolute"
        else:
            base = (baseline.get("probes") or {}).get(key)
            if base is None:
                budget, why = args.budget_ms, "absolute (not in baseline)"
            elif base.get("compliant"):
                budget, why = args.budget_ms, "absolute"
            else:
                budget = round(base["p95"] * args.regression_tolerance, 3)
                why = f"baseline {base['p95']:.3f} x {args.regression_tolerance}"
        if value["p95"] > budget:
            hard_failures.append(f"{key}={value['p95']:.3f}ms>{budget:.3f}ms({why})")
    breach = sorted(k for k, v in measurements.items() if not v["compliant"])
    if hard_failures:
        fail("S3", f"link-search latency gate breached: {hard_failures}")
        return "done"
    ok("S3", f"{len(measurements)} probes correct; every P95 within its gate "
             f"(worst {worst:.3f} ms at {worst_key})")
    if breach:
        advise("S3-absolute", f"ADR Tier-1 ceiling {args.budget_ms:.2f} ms still breached "
                              f"by {len(breach)} probes carried from baseline: {breach} "
                              f"— pre-existing drift, not cutover-induced")
    else:
        ok("S3-absolute", f"every probe within the ADR Tier-1 ceiling "
                          f"{args.budget_ms:.2f} ms (worst {worst:.3f} ms)")
    return "done"

def load_baseline(path):
    if not path:
        return None
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# ------------------------------------------------------------------ S4

def check_transaction_link_latency():
    from construction.services.transaction_link_search import search_transactions
    source = None
    for master, field in (("Customer", "customer_name_in_arabic"),
                          ("Supplier", "supplier_name_in_arabic")):
        found = frappe.get_all(master, filters={field: ("!=", "")},
                               fields=["name", field], limit_page_length=1)
        if found:
            source = (master, field, found[0])
            break
    if source is None:
        advise("S4", "no master row with an Arabic value — sidecar not measured")
        return
    master, _field, doc = source
    query = doc[_field]
    report = []
    for target in TX_TARGETS:
        for _ in range(3):
            search_transactions(target, txt=query, page_length=10)
        times = []
        result = None
        for _ in range(20):
            start = time.perf_counter()
            result = search_transactions(target, txt=query, page_length=10)
            times.append((time.perf_counter() - start) * 1000.0)
        if not isinstance(result, list):
            fail("S4", f"search_transactions({target}) returned {type(result).__name__}")
            return
        report.append(f"{target}: p50={median(times):.3f} "
                      f"p95={nearest_rank_p95(times):.3f} max={max(times):.3f}")
    advise("S4", "transactional link sidecar has no ratified latency budget; "
                 f"measured from a {master} query — " + " | ".join(report))


# ------------------------------------------------------------------ S5

def check_financial_reports():
    """Run on the ledger-bearing company; an empty ledger would be a vacuous pass."""
    companies = frappe.get_all("Company", fields=["name"], limit_page_length=0)
    ranked = []
    for company in companies:
        ranked.append((frappe.db.count("GL Entry", {"company": company.name}),
                       company.name))
    ranked.sort(reverse=True)
    if not ranked or ranked[0][0] == 0:
        fail("S5", "no company carries GL Entry rows — financial reports would "
                   "render empty and prove nothing")
        return
    gl_rows, company = ranked[0]
    today = frappe.utils.today()
    filters = {"company": company,
               "from_date": f"{today[:4]}-01-01",
               "to_date": today}
    before = {"Account": frappe.db.count("Account"),
              "GL Entry": frappe.db.count("GL Entry")}
    for report_name in REPORTS:
        try:
            from construction.api.bilingual_reports import localized_report
            start = time.perf_counter()
            out = localized_report(report_name, filters=json.dumps(filters), mode="en")
            elapsed = (time.perf_counter() - start) * 1000.0
        except Exception as exc:  # noqa: BLE001 - smoke test must surface it
            fail("S5", f"{report_name}: {type(exc).__name__}: {exc}")
            return
        columns, data = out.get("columns"), out.get("data")
        if not isinstance(columns, list) or not isinstance(data, list) or not data:
            fail("S5", f"{report_name}: empty or malformed result "
                       f"(columns={type(columns).__name__}, data={type(data).__name__})")
            return
        ok("S5", f"{report_name}: {len(columns)} columns x {len(data)} rows in "
                 f"{elapsed:.1f} ms (en mode, company with {gl_rows} GL rows)")
    after = {"Account": frappe.db.count("Account"),
             "GL Entry": frappe.db.count("GL Entry")}
    if before != after:
        fail("S5", f"report execution mutated ledger tables: {before} -> {after}")
    else:
        ok("S5", f"report generation read-only (Account={before['Account']}, "
                 f"GL Entry={before['GL Entry']} unchanged)")


# ------------------------------------------------------------------ S6

def check_print_previews():
    rendered = []
    for doctype in PRINT_DOCTYPES:
        recent = frappe.get_all(doctype, fields=["name"],
                                order_by="modified desc", limit_page_length=1)
        if not recent:
            log(f"S6 SKIP: {doctype}: no documents on this site "
                f"(nothing to preview — disclosed, not a pass)")
            continue
        name = recent[0].name
        try:
            html = frappe.get_print(doctype, name)
        except Exception as exc:  # noqa: BLE001
            fail("S6", f"{doctype}: print preview raised {type(exc).__name__}: {exc}")
            return
        if not isinstance(html, str) or len(html) < 200:
            fail("S6", f"{doctype}: print preview too short "
                       f"({0 if not isinstance(html, str) else len(html)} chars)")
            return
        if name not in html:
            fail("S6", f"{doctype}: rendered preview does not contain the "
                       f"document name (wrong document or empty shell)")
            return
        marker = "<table" if "<table" in html else ("<div" if "<div" in html else "none")
        rendered.append(f"{doctype}({len(html)} chars, {marker})")
    if rendered:
        ok("S6", "print previews rendered with document name present: "
                 + ", ".join(rendered))


# ------------------------------------------------------------------ S7 / S8

def check_maintenance(site, allow_maintenance):
    cfg_path = os.path.join(SITES, site, "site_config.json")
    with open(cfg_path, encoding="utf-8") as handle:
        mode = json.load(handle).get("maintenance_mode")
    if mode in (0, None):
        ok("S7", "maintenance_mode is off (site serving traffic)")
    elif allow_maintenance:
        advise("S7", "maintenance_mode is ON — accepted for this run "
                     "(--allow-maintenance)")
    else:
        fail("S7", "maintenance_mode is ON — cutover is not complete until "
                   f"`bench --site {site} set-maintenance-mode off` has been run")


def check_redis():
    down = []
    for label, port in REDIS_PORTS:
        try:
            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
            sock.sendall(b"PING\r\n")
            if not sock.recv(64).startswith(b"+PONG"):
                down.append(f"{label}:{port}(no PONG)")
            sock.close()
        except OSError as exc:
            down.append(f"{label}:{port}({exc})")
    if down:
        fail("S8", "redis unreachable: " + ", ".join(down))
    else:
        ok("S8", "redis reachable on " +
           ", ".join(f"{label}:{port}" for label, port in REDIS_PORTS))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="v16.localhost")
    parser.add_argument("--budget-ms", type=float, default=1.50,
                        help="ADR Tier-1 absolute ceiling for link search (ms)")
    parser.add_argument("--baseline", default=None,
                        help="latency baseline pin to compare against")
    parser.add_argument("--write-baseline", default=None,
                        help="establish the baseline pin (only when no pin exists)")
    parser.add_argument("--regression-tolerance", type=float, default=1.25,
                        help="allowed multiple of a baseline BREACH value")
    parser.add_argument("--baseline-cap-ms", type=float, default=10.0,
                        help="refuse to pin a baseline worse than this")
    parser.add_argument("--establish-attempts", type=int, default=3,
                        help="bounded retries while establishing a pin on a "
                             "contended bench")
    parser.add_argument("--establish-pause", type=float, default=5.0,
                        help="seconds to wait between establish attempts")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--samples", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--expect-gate", choices=("closed", "open"), default="closed")
    parser.add_argument("--allow-maintenance", action="store_true")
    parser.add_argument("--skip-latency", action="store_true")
    args = parser.parse_args()

    if args.baseline:
        args.baseline = os.path.abspath(args.baseline)
    if args.write_baseline:
        args.write_baseline = os.path.abspath(args.write_baseline)
    os.chdir(SITES)  # frappe resolves assets/assets.json relative to cwd
    baseline = load_baseline(args.baseline)
    if args.write_baseline and baseline is not None:
        log(f"NOTE: {args.write_baseline} already exists — comparing against it "
            f"instead of re-pinning (delete it deliberately to re-establish)")
        args.write_baseline = None

    frappe.init(site=args.site, sites_path=SITES)
    frappe.connect()
    frappe.set_user("Administrator")
    started = time.time()
    try:
        load = os.getloadavg()
        log(f"CUTOVER SMOKE TESTS site={args.site} gate={args.expect_gate} "
            f"budget_ms={args.budget_ms} surface={SURFACE}")
        log(f"ENV load1={load[0]:.2f} load5={load[1]:.2f} load15={load[2]:.2f} "
            f"(latency gates are only meaningful on a quiesced bench)")
        reg = registry()
        check_bootstrap(reg)
        check_gate(args.site, args.expect_gate)
        check_redis()
        if args.skip_latency:
            log("S3 SKIP: --skip-latency (diagnostic runs only; a real cutover "
                "must not skip the latency probe)")
        else:
            check_link_latency(reg, args, baseline)
            check_transaction_link_latency()
        check_financial_reports()
        check_print_previews()
        check_maintenance(args.site, args.allow_maintenance)

        if fails:
            log(f"SMOKE RESULT: FAIL ({len(fails)} failed: {', '.join(fails)}); "
                f"{len(passes)} passed, {len(advisories)} advisory "
                f"({time.time() - started:.1f}s)")
            return 1
        log(f"SMOKE RESULT: PASS ({len(passes)} checks passed, "
            f"{len(advisories)} advisory: {', '.join(advisories) or 'none'} "
            f"({time.time() - started:.1f}s)")
        return 0
    finally:
        try:
            frappe.db.rollback()
            frappe.db.close()
        except Exception:  # noqa: BLE001 - close is best-effort
            pass


if __name__ == "__main__":
    sys.exit(main())
