"""Decision-input measurement: Arabic path WITHOUT the vendor baseline (candidate).

Scope and honesty contract
--------------------------
This is NOT the as-designed measurement (that is
`measure_desk_link_p95.py`, cases ``latin_passthrough`` and ``arabic_path``,
which reflects settled decision A3: vendor baseline first, then the registry
half merged on top).

This harness answers one question for the owner's decision record: what would
the Arabic path cost if the vendor baseline were skipped when it is provably
redundant (candidate decision A6)?

* baseline = `frappe.desk.search.search_link` on the same Arabic text
  (what the stock endpoint costs for that input).
* candidate = the registry half alone, formatted exactly as the dispatcher
  formats it (`dispatcher(...)` + `build_for_autosuggest`), which is the work
  the candidate path would perform minus the skipped vendor call.

Match-set contract is the same subset contract as the as-designed Arabic case:
the baseline set must be a subset of the candidate set (no plain result may be
lost). Equality is not expected - the Arabic rows are the feature.

Method contract is identical to the other bilingual harnesses: 5 warmups, 5
rounds of n=100 interleaved samples with alternating order, GC paused during
the timed region, min-of-rounds nearest-rank P95, true median of the best
round, two-tier SLA with the universal 1.50 ms ceiling.
"""

import hashlib
import json
import math
import os
import time

import frappe

PREFIX = "CT-DISP-"
TXT_ARABIC = "اختبارية"
ARABIC_TEMPLATE = "وحدة قياس اختبارية {index:02d}"
SAMPLES = 100
ROUNDS = 5
WARMUP = 5
PAGE_LENGTH = 20
FIXTURES_COUNT = 12

TIER_2A_CEILING = 1.15
TIER_2B_CEILING = 1.50
UNIVERSAL_CEILING_MS = 1.50
TIER_THRESHOLD_MS = 1.0


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _code_hashes():
    app = frappe.get_app_path("construction")
    return {
        "desk_link_search.py": _sha(os.path.join(app, "api/desk_link_search.py")),
        "hooks.py": _sha(os.path.join(app, "hooks.py")),
        "search.py": _sha(os.path.join(app, "searchable_dropdown/api/search.py")),
        "bilingual_service.py": _sha(os.path.join(app, "services/bilingual_service.py")),
        "bilingual_registry.json": _sha(
            os.path.join(app, "data/bilingual/bilingual_registry.json")
        ),
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


def _fixture_filter():
    return {"uom_name": ["like", PREFIX + "%"]}


def _create_fixtures():
    created = []
    for i in range(FIXTURES_COUNT):
        doc = frappe.get_doc(
            {
                "doctype": "UOM",
                "uom_name": f"{PREFIX}{i:02d}",
                "uom_name_ar": ARABIC_TEMPLATE.format(index=i),
                "common_code": f"D{i:02d}",
            }
        )
        doc.insert(ignore_permissions=True)
        created.append(doc.name)
    frappe.db.commit()
    return created


def _delete_fixtures():
    rows = frappe.get_all(
        "UOM", filters=_fixture_filter(), fields=["name"], limit_page_length=0
    )
    for row in rows:
        if frappe.db.exists("UOM", row["name"]):
            frappe.delete_doc("UOM", row["name"], force=True, ignore_permissions=True)
    frappe.db.commit()
    return len(rows)


def _vendor(txt):
    """Plain side: the stock endpoint on the same Arabic text."""
    return frappe.desk.search.search_link(
        "UOM", txt, filters=None, page_length=PAGE_LENGTH
    )


def _registry_only(txt):
    """Candidate side: registry half alone, formatted as the dispatcher formats it."""
    from frappe.desk.search import build_for_autosuggest

    from construction.api.desk_link_search import dispatcher

    rows = dispatcher("UOM", txt, None, 0, PAGE_LENGTH, None)
    return build_for_autosuggest(rows, doctype="UOM")


def _ids(rows):
    return sorted(str(row.get("value")) for row in rows or [])


def measure(txt):
    import gc

    def timed(fn):
        gc.disable()
        try:
            start = time.perf_counter()
            out = fn()
            return out, (time.perf_counter() - start) * 1000.0
        finally:
            gc.enable()

    rounds_base_samples, rounds_cand_samples = [], []
    rounds_base_p95, rounds_cand_p95 = [], []
    first_base, first_cand = None, None

    for _round in range(ROUNDS):
        for _ in range(WARMUP):
            _vendor(txt)
            _registry_only(txt)

        base_times, cand_times = [], []
        for i in range(SAMPLES):
            if i % 2 == 0:
                base, b_ms = timed(lambda: _vendor(txt))
                cand, c_ms = timed(lambda: _registry_only(txt))
            else:
                cand, c_ms = timed(lambda: _registry_only(txt))
                base, b_ms = timed(lambda: _vendor(txt))
            base_times.append(b_ms)
            cand_times.append(c_ms)
            if first_base is None:
                first_base, first_cand = base, cand

        base_round = [round(m, 3) for m in base_times]
        cand_round = [round(m, 3) for m in cand_times]
        rounds_base_samples.append(base_round)
        rounds_cand_samples.append(cand_round)
        rounds_base_p95.append(round(_nearest_rank_p95(base_round), 3))
        rounds_cand_p95.append(round(_nearest_rank_p95(cand_round), 3))

    base_min_p95 = min(rounds_base_p95)
    cand_min_p95 = min(rounds_cand_p95)
    best_base_round = rounds_base_p95.index(base_min_p95)
    best_cand_round = rounds_cand_p95.index(cand_min_p95)

    base_ids = _ids(first_base)
    cand_ids = _ids(first_cand)
    subset = set(base_ids).issubset(set(cand_ids))

    ratio = round(cand_min_p95 / base_min_p95, 4) if base_min_p95 else None
    tier = "2A" if base_min_p95 >= TIER_THRESHOLD_MS else "2B"
    ceiling = TIER_2A_CEILING if tier == "2A" else TIER_2B_CEILING
    tier_pass = ratio is not None and ratio <= ceiling
    ceiling_pass = cand_min_p95 <= UNIVERSAL_CEILING_MS

    return {
        "txt": txt,
        "baseline": {
            "p95_ms": base_min_p95,
            "round_p95_ms": rounds_base_p95,
            "median_ms": round(_true_median(rounds_base_samples[best_base_round]), 3),
            "best_round": best_base_round + 1,
            "match_set_count": len(base_ids),
            "match_set": base_ids,
        },
        "candidate": {
            "p95_ms": cand_min_p95,
            "round_p95_ms": rounds_cand_p95,
            "median_ms": round(_true_median(rounds_cand_samples[best_cand_round]), 3),
            "best_round": best_cand_round + 1,
            "match_set_count": len(cand_ids),
            "match_set": cand_ids,
        },
        "baseline_subset_of_candidate": subset,
        "match_sets_equal": base_ids == cand_ids,
        "candidate_p95_ratio_of_baseline": ratio,
        "order_balance": "alternating (even pair baseline-first, odd pair candidate-first); GC paused during timed region",
        "statistic": "min-of-rounds nearest-rank P95 over 5 rounds; median = true median of the best round",
        "sla_evaluation": {
            "tier": tier,
            "tier_rule": (
                "baseline P95 >= 1.0 ms => Tier 2A <= 1.15x; "
                "baseline P95 < 1.0 ms => Tier 2B <= 1.50x"
            ),
            "tier_ratio_ceiling": ceiling,
            "ratio": ratio,
            "ratio_pass": tier_pass,
            "universal_ceiling_ms": UNIVERSAL_CEILING_MS,
            "candidate_p95_ms": cand_min_p95,
            "ceiling_pass": ceiling_pass,
            "verdict_if_adopted": (
                "COMPLIANT_WITH_TWO_TIER_SLA"
                if (tier_pass and ceiling_pass and subset)
                else "NON_COMPLIANT"
            ),
        },
        "per_round_samples": {
            "baseline": rounds_base_samples,
            "candidate": rounds_cand_samples,
        },
    }


def run():
    _delete_fixtures()
    created = _create_fixtures()
    try:
        res = measure(TXT_ARABIC)
    finally:
        _delete_fixtures()
        leftover = frappe.get_all(
            "UOM", filters=_fixture_filter(), pluck="name", limit_page_length=0
        )
        cleanup = {"created": len(created), "leftover": leftover}

    return {
        "schema": "desk-link-registry-only-candidate/v1",
        "scope": "DECISION INPUT (not the as-designed measurement): Arabic path cost if the vendor baseline were skipped when provably redundant (candidate A6).",
        "sla_framework": "Two-Tier Bilingual Search SLA: universal <= 1.50 ms P95; Tier 2A <= 1.15x; Tier 2B <= 1.50x; min-of-rounds over 5 rounds at n=100",
        "txt": TXT_ARABIC,
        "samples_per_round": SAMPLES,
        "rounds": ROUNDS,
        "warmup_per_round": WARMUP,
        "page_length": PAGE_LENGTH,
        "fixtures_count": FIXTURES_COUNT,
        "fixture_prefix": PREFIX,
        "recorded_utc": frappe.utils.now_datetime().isoformat() + "Z",
        "environment": {
            "frappe_version": frappe.__version__,
            "db_version": frappe.db.sql("SELECT version()")[0][0],
            "site": frappe.local.site,
            "user": frappe.session.user,
        },
        "code_hashes": _code_hashes(),
        "result": res,
        "cleanup": cleanup,
    }


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    out = run()
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "registry-only-candidate.json")
    )
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    res = out["result"]
    ev = res["sla_evaluation"]
    print(
        "CANDIDATE_MEASUREMENT:",
        json.dumps({"arabic_registry_only": res["candidate_p95_ratio_of_baseline"]}),
    )
    print(
        "P95_MS:",
        json.dumps(
            {
                "baseline": res["baseline"]["p95_ms"],
                "candidate": res["candidate"]["p95_ms"],
            }
        ),
    )
    print("TIER:", json.dumps(ev, sort_keys=True))
    print(
        "MATCH_SETS:",
        json.dumps(
            {
                "equal": res["match_sets_equal"],
                "baseline_subset_of_candidate": res["baseline_subset_of_candidate"],
                "baseline_count": res["baseline"]["match_set_count"],
                "candidate_count": res["candidate"]["match_set_count"],
            }
        ),
    )
    print("CLEANUP_LEFTOVER:", len(out["cleanup"]["leftover"]))
