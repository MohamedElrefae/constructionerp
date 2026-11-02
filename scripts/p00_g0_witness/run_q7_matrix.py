"""Q7 matrix execution harness (ephemeral, in-memory ERFs only) — aligned v2.

Alignment per P00_G0_Q7_MATRIX_INTERFACE_RULINGS_2026-11-02.md:
  - Q7-P1-03 / Q7-P6-02 use S4Extractor.assess() (two observations):
    conflicting evidence => INCOMPLETE (conflicting_evidence), no class;
  - Q7-P6-01 unevaluable input => INCOMPLETE (evaluation_ambiguous);
  - Q7-P3-01 / Q7-P3-02 / Q7-BND-02 are vacuous-by-construction (no statement
    channel; handles are internally generated per assessment) => PASS (vacuous).

ERFs are kept in memory only and discarded at exit. No target access.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s4_extract import S4Extractor  # noqa: E402

SOCKET = os.environ["P00G0_SOCKET"]
CLIENT = "/usr/bin/mariadb"


def db_row(readonly: bool):
    """Real transaction in one session; >=150 ms idle before the I_S read."""
    import time as _t
    _t.sleep(0.15)
    stmt = (
        ("START TRANSACTION READ ONLY;" if readonly else "START TRANSACTION;")
        + " SELECT 'COUNT', COUNT(*) FROM p00g0_fixture.t;"
        + " SELECT 'ROW', trx_is_read_only, trx_autocommit_non_locking"
          " FROM information_schema.innodb_trx"
          " WHERE trx_mysql_thread_id = CONNECTION_ID();"
        + " COMMIT;"
    )
    out = subprocess.run(
        [CLIENT, "--no-defaults", "--protocol=socket", f"--socket={SOCKET}",
         "-u", "root", "--batch", "--skip-column-names", "-e", stmt],
        capture_output=True, text=True, timeout=30,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    for ln in out.stdout.splitlines():
        if ln.startswith("ROW\t"):
            vals = ln.split("\t")
            return {"trx_is_read_only": int(vals[1]),
                    "trx_autocommit_non_locking": int(vals[2])}
    return None


def runner_row(row):
    return lambda sql: [] if row is None else [row]


def runner_seq(rows):
    it = iter(rows)
    return lambda sql: [next(it)]


def runner_error(exc):
    def _run(sql):
        raise exc
    return _run


CANARY = "P00G0-CANARY-7f3a9c"
RO = {"trx_is_read_only": 1, "trx_autocommit_non_locking": 0}
RW = {"trx_is_read_only": 0, "trx_autocommit_non_locking": 0}

# mode: "db" | "row" | "seq" | "error" | "vacuous"
CASES = [
    {"id": "Q7-P1-04", "mode": "db", "ro": True, "expected": "UNKNOWN", "note": "control; expected behaviour met (not a pass claim)"},
    {"id": "Q7-P2-04", "mode": "db", "ro": False, "expected": "UNKNOWN", "note": "control"},
    {"id": "Q7-P1-01", "mode": "row", "row": {**RO, "trx_query": "synthetic"}, "expected": "INCOMPLETE"},
    {"id": "Q7-P1-02", "mode": "row", "row": {"trx_is_read_only": 7, "trx_autocommit_non_locking": 0}, "expected": "UNKNOWN"},
    {"id": "Q7-P1-03", "mode": "assess", "rows": [RO, RW], "expected": "INCOMPLETE", "note": "conflicting evidence => conflicting_evidence"},
    {"id": "Q7-P2-01", "mode": "row", "row": {**RO, "trx_query": "synthetic"}, "expected": "INCOMPLETE"},
    {"id": "Q7-P2-02", "mode": "row", "row": {**RO, "trx_mysql_thread_id": 42}, "expected": "INCOMPLETE"},
    {"id": "Q7-P2-03", "mode": "row", "row": {**RO, "object_instance_begin": 1}, "expected": "INCOMPLETE"},
    {"id": "Q7-P3-01", "mode": "vacuous", "expected": "N/A", "note": "no statement output channel exists"},
    {"id": "Q7-P3-02", "mode": "vacuous", "expected": "N/A", "note": "no statement output channel exists"},
    {"id": "Q7-P3-03", "mode": "row", "row": RO, "expected": "UNKNOWN", "note": "control"},
    {"id": "Q7-P4-01", "mode": "row", "row": {**RO, "trx_query": CANARY}, "expected": "INCOMPLETE", "note": "withheld-detail probe: coarse status/class emits no trace of the withheld field or its canary"},
    {"id": "Q7-P4-02", "mode": "vacuous", "expected": "N/A", "note": "R4: no transaction/engine timestamp or wall-clock event time is emitted; idle_gap_ms is harness-only"},
    {"id": "Q7-P4-03", "mode": "row", "row": RO, "expected": "UNKNOWN", "note": "control"},
    {"id": "Q7-P5-01", "mode": "row", "row": {**RO, "trx_query": CANARY}, "expected": "INCOMPLETE", "note": "canary-absence probe: serialized record must contain no trace of the withheld value"},
    {"id": "Q7-P5-02", "mode": "vacuous", "expected": "N/A", "note": "R5: no aggregate classes emitted; combinatorial reconstruction excluded by channel absence"},
    {"id": "Q7-P5-03", "mode": "vacuous", "expected": "N/A", "note": "R6: no staging file/buffer channel; residue excluded by construction"},
    {"id": "Q7-P6-01", "mode": "row", "row": {"trx_autocommit_non_locking": 0}, "expected": "INCOMPLETE", "note": "evaluation_ambiguous"},
    {"id": "Q7-P6-02", "mode": "assess", "rows": [RO, RW], "expected": "INCOMPLETE", "note": "conflicting evidence across observations"},
    {"id": "Q7-P6-03", "mode": "error", "expected": "INCOMPLETE", "note": "evaluation_aborted"},
    {"id": "Q7-BND-01", "mode": "row", "row": RO, "expected": "UNKNOWN", "note": "handle derivation probe; random handle, no derivation path"},
    {"id": "Q7-BND-02", "mode": "vacuous", "expected": "N/A", "note": "handles are generated per assessment; reuse impossible by construction"},
    {"id": "Q7-BND-03", "mode": "vacuous", "expected": "N/A", "note": "no transaction-identifier channel exists in S4 projection"},
]


def coarse_leak_probe(rec: dict) -> str:
    blob = json.dumps(rec)
    if CANARY in blob:
        return "fail"
    for bad in ("trx_query", "trx_mysql_thread_id", "trx_id", "trx_started",
                "object_instance_begin", "gtid", "xid"):
        if bad in blob:
            return "fail"
    if not re.fullmatch(r"[0-9a-f]{32}", rec["correlation"]["handle"]):
        return "fail"
    return "pass"


def run_case(case: dict) -> dict:
    mode = case["mode"]
    if mode == "vacuous":
        return {"case_id": case["id"], "observed": "vacuous", "expected": "N/A",
                "probe": "n/a", "result": "PASS (vacuous)", "note": case.get("note", "")}
    if mode == "db":
        ex = S4Extractor(runner_row(db_row(case["ro"])))
        rec = ex.extract(case_id=case["id"])
    elif mode == "row":
        ex = S4Extractor(runner_row(case["row"]))
        rec = ex.extract(case_id=case["id"])
    elif mode == "assess":
        ex = S4Extractor(runner_seq(case["rows"]))
        rec = ex.assess(case_id=case["id"])
    elif mode == "error":
        ex = S4Extractor(runner_error(RuntimeError("synthetic")))
        rec = ex.extract(case_id=case["id"])
    else:
        raise ValueError(mode)
    obs = rec["class_outcome"]
    probe = coarse_leak_probe(rec)
    match = obs["status"] == case["expected"]
    return {"case_id": case["id"], "observed": f'{obs["code"]}/{obs["status"]}',
            "expected": case["expected"], "probe": probe,
            "result": "PASS" if (match and probe == "pass") else "FAIL",
            "note": case.get("note", "")}


def main() -> int:
    results = []
    stop = None
    for case in CASES:
        res = run_case(case)
        results.append(res)
        if res["result"] == "FAIL":
            stop = {"case": case["id"], "reason": f'observed {res["observed"]} != expected {res["expected"]}'}
            break
    print(json.dumps({"executed": len(results), "total": len(CASES),
                      "stop": stop, "results": results}, indent=2))
    return 0 if stop is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
