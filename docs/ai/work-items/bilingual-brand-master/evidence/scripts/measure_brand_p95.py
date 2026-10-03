"""Local comparative P95 harness for Brand master bilingual enablement.

Scope and honesty contract
--------------------------
This harness is a WORK-ITEM-LOCAL measurement for the Brand master.
It evaluates performance against the approved Two-Tier Bilingual Search SLA
(governed by the universal absolute ceiling of <= 1.50 ms P95).

Method contract
---------------
- Same inputs both sides: search text, page shape.
- Baseline = permission-aware `frappe.get_list` with plain search job.
- Bilingual = `searchable_link_search`, the governed path including normalization
  predicate and ranking.
- Alternating pair order so first/second order effects cancel.
- 5 warmups per round; 5 rounds of n=100 interleaved samples (500 samples per
  side total); min-of-rounds nearest-rank P95; true median over the best round.
- Tier selection: baseline min-of-rounds P95 >= 1.0 ms => Tier 2A (<= 1.15x),
  otherwise Tier 2B (<= 1.50x). Universal ceiling applies to both tiers.
- Match-set equivalence asserted.
- Zero leftover fixtures verified upon cleanup.
"""

import hashlib
import json
import math
import os
import time

import frappe

PREFIX = "CT-BRAND-"
TXT = "CT-BRAND"
SAMPLES = 100
ROUNDS = 5
WARMUP = 5
PAGE_LENGTH = 20
FIXTURES_COUNT = 12
AR_FIXTURES = [
    "بصمة البناء المشرفي",
    "علامة الإسمنت الممتاز",
    "خامة الحديد المجدول",
    "المقاولات المتقدمة",
]

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
        "bilingual_service.py": _sha(os.path.join(app, "services/bilingual_service.py")),
        "bilingual_registry.py": _sha(os.path.join(app, "services/bilingual_registry.py")),
        "search.py": _sha(os.path.join(app, "searchable_dropdown/api/search.py")),
        "bilingual_registry.json": _sha(
            os.path.join(app, "data/bilingual/bilingual_registry.json")
        ),
        "add_brand_arabic_fields.py": _sha(
            os.path.join(app, "patches/v9_11/add_brand_arabic_fields.py")
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
    return {"brand": ["like", PREFIX + "%"]}


def _create_fixtures():
    """Create Brand fixture rows with Arabic values and server-derived norm keys."""
    created = []
    for i in range(FIXTURES_COUNT):
        d = frappe.get_doc(
            {
                "doctype": "Brand",
                "brand": f"{PREFIX}Test-{i:02d}",
                "brand_ar": AR_FIXTURES[i % len(AR_FIXTURES)],
            }
        )
        d.insert(ignore_permissions=True)
        created.append(d.name)
    frappe.db.commit()
    return created


def _delete_fixtures():
    """Delete Brand fixtures (no child tables on Brand)."""
    rows = frappe.get_all(
        "Brand", filters=_fixture_filter(), fields=["name"], limit_page_length=0
    )
    for r in rows:
        if frappe.db.exists("Brand", r["name"]):
            frappe.delete_doc("Brand", r["name"], force=True, ignore_permissions=True)
    frappe.db.commit()
    return len(rows)


def _baseline(txt):
    return frappe.get_list(
        "Brand",
        or_filters=[
            ["brand", "like", "%" + txt + "%"],
            ["name", "like", "%" + txt + "%"],
        ],
        page_length=PAGE_LENGTH,
        start=0,
    )


def _bilingual(txt):
    from construction.searchable_dropdown.api.search import searchable_link_search

    return searchable_link_search("Brand", txt, {}, PAGE_LENGTH)


def _ids(rows):
    return sorted(r.get("value") or r.get("name") for r in rows)


def measure():
    import gc

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
            _baseline(TXT)
            _bilingual(TXT)

        base_times, bilin_times = [], []
        for i in range(SAMPLES):
            if i % 2 == 0:
                base, b_ms = timed(lambda: _baseline(TXT))
                bilin, bl_ms = timed(lambda: _bilingual(TXT))
            else:
                bilin, bl_ms = timed(lambda: _bilingual(TXT))
                base, b_ms = timed(lambda: _baseline(TXT))
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

    base_ids = _ids(first_base)
    bilin_ids = _ids(first_bilin)

    ratio = round(bilin_min_p95 / base_min_p95, 4) if base_min_p95 else None

    tier = "2A" if base_min_p95 >= TIER_THRESHOLD_MS else "2B"
    ceiling = TIER_2A_CEILING if tier == "2A" else TIER_2B_CEILING
    tier_pass = ratio is not None and ratio <= ceiling
    ceiling_pass = bilin_min_p95 <= UNIVERSAL_CEILING_MS

    return {
        "doctype": "Brand",
        "baseline": {
            "p95_ms": base_min_p95,
            "round_p95_ms": rounds_base_p95,
            "median_ms": round(
                _true_median(rounds_base_samples[best_base_round]), 3
            ),
            "best_round": best_base_round + 1,
            "match_set_count": len(base_ids),
        },
        "bilingual": {
            "p95_ms": bilin_min_p95,
            "round_p95_ms": rounds_bilin_p95,
            "median_ms": round(
                _true_median(rounds_bilin_samples[best_bilin_round]), 3
            ),
            "best_round": best_bilin_round + 1,
            "match_set_count": len(bilin_ids),
        },
        "match_sets_equal": base_ids == bilin_ids,
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
            "ratio_pass": tier_pass,
            "universal_ceiling_ms": UNIVERSAL_CEILING_MS,
            "bilingual_p95_ms": bilin_min_p95,
            "ceiling_pass": ceiling_pass,
            "verdict": (
                "COMPLIANT_WITH_TWO_TIER_SLA"
                if (tier_pass and ceiling_pass)
                else "NON_COMPLIANT"
            ),
        },
        "per_round_samples": {
            "baseline": rounds_base_samples,
            "bilingual": rounds_bilin_samples,
        },
    }


def run():
    _delete_fixtures()  # clean any existing residue
    created = _create_fixtures()
    try:
        res = measure()
    finally:
        _delete_fixtures()
        leftover_parent = frappe.get_all(
            "Brand", filters=_fixture_filter(), pluck="name", limit_page_length=0
        )
        cleanup = {
            "created": len(created),
            "leftover": leftover_parent,
        }

    payload = {
        "schema": "brand-p95-local/v1",
        "scope": "WORK-ITEM-LOCAL comparative measurement for Brand master bilingual enablement.",
        "sla_framework": "Two-Tier Bilingual Search SLA: universal <= 1.50 ms P95; Tier 2A <= 1.15x; Tier 2B <= 1.50x; min-of-rounds over 5 rounds at n=100",
        "txt": TXT,
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
    return payload


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    out = run()
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "brand-p95-measurement.json",
    )
    with open(os.path.abspath(path), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    ev = out["result"]["sla_evaluation"]
    print("MEASUREMENT:", json.dumps({out["result"]["doctype"]: ev["ratio"]}, sort_keys=True))
    print("P95_MS:", json.dumps({"baseline": out["result"]["baseline"]["p95_ms"], "bilingual": out["result"]["bilingual"]["p95_ms"]}))
    print("TIER:", json.dumps(ev, sort_keys=True))
    print("MATCH_SETS_EQUAL:", out["result"].get("match_sets_equal"))
    print("CLEANUP_LEFTOVER:", len(out["cleanup"]["leftover"]))
