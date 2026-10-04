"""Local comparative P95 harness for the Tier 5A bilingual report endpoint.

Scope and honesty contract
--------------------------
WORK-ITEM-LOCAL measurement for `construction.api.bilingual_reports.localized_report`
compared against the stock vendor report path it wraps. Two pilot reports are
measured (Trial Balance and General Ledger), one case per report:

* ``baseline`` - the vendor module's own ``execute(filters=...)`` with
  fully-specified filters: what a stock report run costs.
* ``bilingual`` - the governed endpoint with the same filters as a JSON
  string (exactly what the viewer sends): whitelist check, filter parsing,
  required-filter defaulting, one vendor execute (R1), account-name mapping
  load, and the ar-mode transform.

No fixtures are created: both sides run on existing site data, and Account /
GL Entry row counts are recorded before and after as a mutation guard.

Method contract (identical to the bilingual master harnesses)
-------------------------------------------------------------
- Same inputs on both sides (report + filters); alternating pair order so
  first/second order effects cancel; GC paused during the timed region.
- 5 warmups per round; 5 rounds of n=100 interleaved samples; min-of-rounds
  nearest-rank P95; true median over the best round.
- Tier selection per case: baseline min-of-rounds P95 >= 1.0 ms => Tier 2A
  (<= 1.15x), otherwise Tier 2B (<= 1.50x).
- DECISION R5: the 1.50 ms ABSOLUTE ceiling of the search-path SLA does not
  apply to reports (a financial report baseline is inherently tens of ms);
  acceptance is the tier RATIO limb only. Absolute P95 values are recorded
  and disclosed either way.
- Structural contract: the bilingual payload must return exactly the same
  number of rows and columns as the baseline (the transform localizes cells,
  never adds or drops rows).
"""

import gc
import hashlib
import json
import math
import os
import time

import frappe

SAMPLES = 100
ROUNDS = 5
WARMUP = 5
COMPANY = "Elrefae"

TIER_2A_CEILING = 1.15
TIER_2B_CEILING = 1.50
TIER_THRESHOLD_MS = 1.0

REPORTS = {
    "trial_balance": {
        "report_name": "Trial Balance",
        "module": "erpnext.accounts.report.trial_balance.trial_balance",
        "filters": {"company": COMPANY},  # fiscal_year defaulted identically on both sides
    },
    "general_ledger": {
        "report_name": "General Ledger",
        "module": "erpnext.accounts.report.general_ledger.general_ledger",
        "filters": {
            "company": COMPANY,
            "from_date": "2000-01-01",
            "to_date": "2100-12-31",
        },
    },
}


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _code_hashes():
    app = frappe.get_app_path("construction")
    return {
        "bilingual_reports.py": _sha(os.path.join(app, "api/bilingual_reports.py")),
        "report_bilingual_extension.py": _sha(
            os.path.join(app, "services/report_bilingual_extension.py")
        ),
        "hooks.py": _sha(os.path.join(app, "hooks.py")),
    }


def _nearest_rank_p95(values):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _true_median(values):
    ordered = sorted(values)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def _unpack(out):
    if isinstance(out, tuple):
        return out[0], out[1]
    return out.columns, out.data


def _baseline(report_key, filters):
    """Stock path: the vendor execute, fresh filter dict each call."""
    cfg = REPORTS[report_key]
    mod = frappe.get_module(cfg["module"])
    return mod.execute(filters=frappe._dict(dict(filters)))


def _bilingual(report_key, filters):
    """Bilingual path: the governed endpoint, filters exactly as the viewer sends."""
    from construction.api.bilingual_reports import localized_report

    return localized_report(
        REPORTS[report_key]["report_name"],
        filters=json.dumps(filters),
        mode="ar",
    )


def _measure_case(report_key, filters):
    def timed(fn):
        gc.disable()
        try:
            start = time.perf_counter()
            out = fn()
            return out, (time.perf_counter() - start) * 1000.0
        finally:
            gc.enable()

    rounds_base_samples, rounds_bilin_samples = [], []
    rounds_base_p95, rounds_bilin_p95 = [], []
    first_base, first_bilin = None, None

    for _round in range(ROUNDS):
        for _ in range(WARMUP):
            _baseline(report_key, filters)
            _bilingual(report_key, filters)

        base_times, bilin_times = [], []
        for i in range(SAMPLES):
            if i % 2 == 0:
                base, b_ms = timed(lambda: _baseline(report_key, filters))
                bilin, bl_ms = timed(lambda: _bilingual(report_key, filters))
            else:
                bilin, bl_ms = timed(lambda: _bilingual(report_key, filters))
                base, b_ms = timed(lambda: _baseline(report_key, filters))
            base_times.append(b_ms)
            bilin_times.append(bl_ms)
            if first_base is None:
                first_base, first_bilin = base, bilin

        base_round = [round(m, 3) for m in base_times]
        bilin_round = [round(m, 3) for m in bilin_times]
        rounds_base_samples.append(base_round)
        rounds_bilin_samples.append(bilin_round)
        rounds_base_p95.append(round(_nearest_rank_p95(base_round), 3))
        rounds_bilin_p95.append(round(_nearest_rank_p95(bilin_round), 3))

    base_min_p95 = min(rounds_base_p95)
    bilin_min_p95 = min(rounds_bilin_p95)
    best_base_round = rounds_base_p95.index(base_min_p95)
    best_bilin_round = rounds_bilin_p95.index(bilin_min_p95)

    base_cols, base_data = _unpack(first_base)
    bilin_cols, bilin_data = first_bilin["columns"], first_bilin["data"]
    contract_pass = len(base_data) == len(bilin_data) and len(base_cols) == len(bilin_cols)

    ratio = round(bilin_min_p95 / base_min_p95, 4) if base_min_p95 else None
    tier = "2A" if base_min_p95 >= TIER_THRESHOLD_MS else "2B"
    ceiling = TIER_2A_CEILING if tier == "2A" else TIER_2B_CEILING
    ratio_pass = ratio is not None and ratio <= ceiling

    return {
        "case": report_key,
        "report_name": REPORTS[report_key]["report_name"],
        "filters": filters,
        "baseline": {
            "p95_ms": base_min_p95,
            "round_p95_ms": rounds_base_p95,
            "median_ms": round(_true_median(rounds_base_samples[best_base_round]), 3),
            "best_round": best_base_round + 1,
            "row_count": len(base_data),
            "column_count": len(base_cols),
        },
        "bilingual": {
            "p95_ms": bilin_min_p95,
            "round_p95_ms": rounds_bilin_p95,
            "median_ms": round(_true_median(rounds_bilin_samples[best_bilin_round]), 3),
            "best_round": best_bilin_round + 1,
            "row_count": len(bilin_data),
            "column_count": len(bilin_cols),
        },
        "structural_contract": {
            "rows_equal": len(base_data) == len(bilin_data),
            "columns_equal": len(base_cols) == len(bilin_cols),
            "contract_pass": contract_pass,
        },
        "bilingual_p95_ratio_of_baseline": ratio,
        "order_balance": "alternating (even pair baseline-first, odd pair bilingual-first); GC paused during timed region",
        "statistic": "min-of-rounds nearest-rank P95 over 5 rounds; median = true median of the best round",
        "sla_evaluation": {
            "tier": tier,
            "tier_rule": (
                "baseline P95 >= 1.0 ms => Tier 2A <= 1.15x; "
                "baseline P95 < 1.0 ms => Tier 2B <= 1.50x"
            ),
            "tier_ratio_ceiling": ceiling,
            "ratio": ratio,
            "ratio_pass": ratio_pass,
            "absolute_ceiling_applicable": False,
            "absolute_ceiling_note": (
                "the search-path 1.50 ms absolute ceiling does not apply to reports "
                "(decision R5); bilingual absolute P95 is recorded for disclosure"
            ),
            "bilingual_p95_ms": bilin_min_p95,
            "verdict": (
                "COMPLIANT_WITH_TWO_TIER_SLA"
                if (ratio_pass and contract_pass)
                else "NON_COMPLIANT"
            ),
        },
        "per_round_samples": {
            "baseline": rounds_base_samples,
            "bilingual": rounds_bilin_samples,
        },
    }


def _counts():
    return {
        "Account": frappe.db.count("Account"),
        "GL Entry": frappe.db.count("GL Entry"),
    }


def measure():
    cases = {}
    for key, cfg in REPORTS.items():
        filters = dict(cfg["filters"])
        if key == "trial_balance":
            fy = frappe.get_all(
                "Fiscal Year",
                filters={"disabled": 0},
                fields=["name"],
                order_by="year_start_date desc",
                limit=1,
            )
            filters["fiscal_year"] = fy[0]["name"] if fy else None
        cases[key] = _measure_case(key, filters)
    return {
        "cases": cases,
        "all_cases_compliant": all(
            case["sla_evaluation"]["verdict"] == "COMPLIANT_WITH_TWO_TIER_SLA"
            for case in cases.values()
        ),
        "call_signature": (
            "baseline = <vendor module>.execute(filters=<dict>); "
            "bilingual = construction.api.bilingual_reports.localized_report("
            "report_name, filters=<json string identical to the viewer>, mode='ar')"
        ),
    }


def run():
    before = _counts()
    res = measure()
    after = _counts()
    payload = {
        "schema": "report-p95-local/v1",
        "scope": "WORK-ITEM-LOCAL comparative measurement for the Tier 5A bilingual report endpoint.",
        "sla_framework": (
            "Two-Tier ratio limbs only (decision R5): Tier 2A <= 1.15x, Tier 2B <= 1.50x, "
            "min-of-rounds over 5 rounds at n=100; absolute 1.50 ms search ceiling NOT applied "
            "to reports, absolute P95 disclosed; mapping served from its normal redis cache "
            "after warmups (R7: TTL 300 s, busted by Account doc_events) — steady-state "
            "production behaviour, cold first render per worker pays the SQL load (disclosed)"
        ),
        "samples_per_round": SAMPLES,
        "rounds": ROUNDS,
        "warmup_per_round": WARMUP,
        "fixtures_count": 0,
        "fixture_prefix": None,
        "recorded_utc": frappe.utils.now_datetime().isoformat() + "Z",
        "environment": {
            "frappe_version": frappe.__version__,
            "db_version": frappe.db.sql("SELECT version()")[0][0],
            "site": frappe.local.site,
            "user": frappe.session.user,
        },
        "code_hashes": _code_hashes(),
        "result": res,
        "mutation_guard": {"before": before, "after": after, "pass": before == after},
        "cleanup": {"created": 0, "leftover_account": [], "leftover_gl": []},
    }
    return payload


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    out = run()
    path = os.path.join(os.path.dirname(__file__), "..", "report-p95-measurement.json")
    with open(os.path.abspath(path), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    cases = out["result"]["cases"]
    print(
        "MEASUREMENT:",
        json.dumps(
            {name: case["bilingual_p95_ratio_of_baseline"] for name, case in cases.items()},
            sort_keys=True,
        ),
    )
    print(
        "P95_MS:",
        json.dumps(
            {
                name: {
                    "baseline": case["baseline"]["p95_ms"],
                    "bilingual": case["bilingual"]["p95_ms"],
                }
                for name, case in cases.items()
            },
            sort_keys=True,
        ),
    )
    print(
        "TIER:",
        json.dumps(
            {name: case["sla_evaluation"]["verdict"] for name, case in cases.items()},
            sort_keys=True,
        ),
    )
    print(
        "CONTRACT:",
        json.dumps(
            {
                name: {
                    "rows_equal": case["structural_contract"]["rows_equal"],
                    "columns_equal": case["structural_contract"]["columns_equal"],
                    "baseline_rows": case["baseline"]["row_count"],
                    "bilingual_rows": case["bilingual"]["row_count"],
                }
                for name, case in cases.items()
            },
            sort_keys=True,
        ),
    )
    print("ALL_CASES_COMPLIANT:", out["result"]["all_cases_compliant"])
    print("MUTATION_GUARD:", "PASS" if out["mutation_guard"]["pass"] else "FAIL")
