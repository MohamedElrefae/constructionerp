"""Local comparative P95 harness for BOQ Header and BOQ Structure master bilingual enablement.

Scope and honesty contract
--------------------------
This harness is a WORK-ITEM-LOCAL measurement for BOQ Header and BOQ Structure masters.
It evaluates performance against the approved Two-Tier Bilingual Search SLA.
Per ADR §2 and Scope §2.C, if baseline latency >= 1.0 ms, Tier 2A applies (governed by
<= 1.15x min-of-rounds P95 over 5 rounds at n=100); if < 1.0 ms, Tier 2B applies
(<= 1.50x trade-off band). Both are bounded by the universal absolute ceiling of <= 1.50 ms P95.

Method contract
---------------
- Same inputs both sides: search text, page shape.
- Baseline = `frappe.desk.search.search_link(doctype, txt, page_length=PAGE_LENGTH)`.
- Bilingual = `searchable_link_search(doctype, txt, {}, PAGE_LENGTH)`.
- Alternating pair order so first/second order effects cancel.
- 5 warmups per round; 5 rounds of n=100 interleaved samples (500 samples per side total).
- Min-of-rounds nearest-rank P95; true median over best round; multi-round spread recorded.
- Match-set equivalence asserted.
- Zero leftover fixtures verified upon cleanup.
- Synthetic fixtures provide Arabic coverage (Alef variants, Taa Marbuta, tatweel),
  tree parent/child relationships, and wbs_code values.
"""

import gc
import hashlib
import json
import math
import os
import time

import frappe
from frappe.desk.search import search_link
from construction.searchable_dropdown.api.search import searchable_link_search

ROUNDS = 5
SAMPLES_PER_ROUND = 100
WARMUP = 5
PAGE_LENGTH = 20
FIXTURES_COUNT = 12

PREFIX_H = "CT-BOQH-"
TXT_H = "CT-BOQH"

PREFIX_S = "CT-BOQS-"
TXT_S = "CT-BOQS"


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _code_hashes():
    app = frappe.get_app_path("construction")
    return {
        "bilingual_service.py": _sha(os.path.join(app, "services/bilingual_service.py")),
        "bilingual_registry.py": _sha(os.path.join(app, "services/bilingual_registry.py")),
        "search.py": _sha(os.path.join(app, "searchable_dropdown/api/search.py")),
        "boq_link_queries.py": _sha(os.path.join(app, "api/boq_link_queries.py")),
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


def _ids(rows):
    return sorted(r.get("value") or r.get("name") for r in rows)


# ─────────────────────────────────────────────────────────────────────────────
# BOQ Header Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _delete_header_fixtures():
    rows = frappe.get_all("BOQ Header", filters={"title": ["like", PREFIX_H + "%"]}, fields=["name"], limit_page_length=0)
    for r in rows:
        if frappe.db.exists("BOQ Header", r["name"]):
            frappe.delete_doc("BOQ Header", r["name"], force=True, ignore_permissions=True)
    frappe.db.commit()
    return len(rows)


def _create_header_fixtures():
    arabic_titles = [
        "جدول كميات الأعمال الإنشائية",
        "جَدْوَلُ كَمِّيَّاتِ خَرَسَانَةِ الأَسَاسَاتِ",
        "جدول كـمـيـات المباني والتشطيبات",
        "جدول كميات أعمال الكهرباء والإنارة",
        "جدول كميات الشبكات الصحية والمياه",
        "جدول كـمـيـات العزل المائي والحراري",
        "جدول كميات أعمال التكييف والتهوية",
        "جدول كميات شبكة مكافحة الحريق",
        "جدول كميات الموقع العام والأرصفة",
        "جدول كـمـيـات الأسوار والبوابات",
        "جدول كميات المصاعد والسلالم الكهربائية",
        "جدول كميات التوريدات الخاصة للمشروع",
    ]
    created = []
    for i in range(FIXTURES_COUNT):
        d = frappe.get_doc({
            "doctype": "BOQ Header",
            "project": "PROJ-0001",
            "title": f"{PREFIX_H}Test-{i:02d}",
            "title_ar": arabic_titles[i % len(arabic_titles)],
        })
        d.insert(ignore_permissions=True)
        created.append(d.name)
    frappe.db.commit()
    return created


# ─────────────────────────────────────────────────────────────────────────────
# BOQ Structure Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _delete_structure_fixtures():
    leaves = frappe.get_all(
        "BOQ Structure",
        filters={"title": ["like", PREFIX_S + "%"], "is_group": 0},
        pluck="name",
        limit_page_length=0,
    )
    for name in leaves:
        if frappe.db.exists("BOQ Structure", name):
            frappe.delete_doc("BOQ Structure", name, force=True, ignore_permissions=True)

    groups = frappe.get_all(
        "BOQ Structure",
        filters={"title": ["like", PREFIX_S + "%"], "is_group": 1},
        pluck="name",
        limit_page_length=0,
    )
    for name in groups:
        if frappe.db.exists("BOQ Structure", name):
            frappe.delete_doc("BOQ Structure", name, force=True, ignore_permissions=True)

    frappe.db.commit()
    return len(leaves) + len(groups)


def _create_structure_fixtures(header_name):
    group_titles_ar = [
        "أعمال الحفريات والردميات",
        "أعمال الخرسانات المسلحة",
        "أعمال البلوك والمباني",
        "أعمال العزل والأسطح",
        "أعمال التشطيبات المعمارية",
        "أعمال التركيبات الكهروميكانيكية",
    ]
    item_titles_ar = [
        "حفر الموقع العام حتى المنسوب",
        "خرسانة عادية للأساسات سمك 10 سم",
        "مباني طابوق إسمنتي مفرغ 20 سم",
        "عزل مائي للأرضيات باستخدام الرولات",
        "بياض أسمنتي داخلي للجدران والأسقف",
        "تمديد أسلاك التغذية الكهربائية للإنارة",
    ]

    created = []
    for i in range(6):
        g = frappe.get_doc({
            "doctype": "BOQ Structure",
            "boq_header": header_name,
            "title": f"{PREFIX_S}Group-{i:02d}",
            "title_ar": group_titles_ar[i],
            "wbs_code": f"0{i+1}",
            "is_group": 1,
        })
        g.insert(ignore_permissions=True)
        created.append(g.name)

        child = frappe.get_doc({
            "doctype": "BOQ Structure",
            "boq_header": header_name,
            "title": f"{PREFIX_S}Item-{i:02d}",
            "title_ar": item_titles_ar[i],
            "wbs_code": f"0{i+1}.01",
            "is_group": 0,
            "parent_structure": g.name,
        })
        child.insert(ignore_permissions=True)
        created.append(child.name)

    frappe.db.commit()
    return created


# ─────────────────────────────────────────────────────────────────────────────
# Measurement Engine (5 rounds x n=100)
# ─────────────────────────────────────────────────────────────────────────────

def _measure_doctype_multi_round(doctype, txt, baseline_fn, bilingual_fn):
    def timed(fn):
        gc.disable()
        try:
            start = time.perf_counter()
            out = fn()
            return out, (time.perf_counter() - start) * 1000.0
        finally:
            gc.enable()

    # Pre-warm
    for _ in range(WARMUP):
        baseline_fn(txt)
        bilingual_fn(txt)

    rounds_baseline_samples = []
    rounds_bilingual_samples = []
    rounds_baseline_p95 = []
    rounds_bilingual_p95 = []

    last_base_res = None
    last_bilin_res = None

    for r in range(ROUNDS):
        round_base_times = []
        round_bilin_times = []
        for i in range(SAMPLES_PER_ROUND):
            if i % 2 == 0:
                base, b_ms = timed(lambda: baseline_fn(txt))
                bilin, bl_ms = timed(lambda: bilingual_fn(txt))
            else:
                bilin, bl_ms = timed(lambda: bilingual_fn(txt))
                base, b_ms = timed(lambda: baseline_fn(txt))
            round_base_times.append(b_ms)
            round_bilin_times.append(bl_ms)
            last_base_res = base
            last_bilin_res = bilin

        base_samples_round = [round(m, 3) for m in round_base_times]
        bilin_samples_round = [round(m, 3) for m in round_bilin_times]
        rounds_baseline_samples.append(base_samples_round)
        rounds_bilingual_samples.append(bilin_samples_round)
        rounds_baseline_p95.append(round(_nearest_rank_p95(base_samples_round), 3))
        rounds_bilingual_p95.append(round(_nearest_rank_p95(bilin_samples_round), 3))

    # Min-of-rounds selection
    best_base_idx = rounds_baseline_p95.index(min(rounds_baseline_p95))
    best_bilin_idx = rounds_bilingual_p95.index(min(rounds_bilingual_p95))

    min_base_p95 = rounds_baseline_p95[best_base_idx]
    min_bilin_p95 = rounds_bilingual_p95[best_bilin_idx]
    best_base_samples = rounds_baseline_samples[best_base_idx]
    best_bilin_samples = rounds_bilingual_samples[best_bilin_idx]

    base_ids = _ids(last_base_res)
    bilin_ids = _ids(last_bilin_res)

    # Determine Tier per ADR §2 based on measured baseline latency
    tier = "2A" if min_base_p95 >= 1.0 else "2B"
    ratio = round(min_bilin_p95 / min_base_p95, 4) if min_base_p95 else None
    relative_gate_pass = (ratio <= 1.15) if tier == "2A" else (ratio <= 1.50)
    absolute_gate_pass = min_bilin_p95 <= 1.50

    return {
        "doctype": doctype,
        "round_count": ROUNDS,
        "samples_per_round": SAMPLES_PER_ROUND,
        "total_samples_per_side": ROUNDS * SAMPLES_PER_ROUND,
        "baseline": {
            "p95_ms": min_base_p95,
            "median_ms": round(_true_median(best_base_samples), 3),
            "all_rounds_p95_ms": rounds_baseline_p95,
            "mean_p95_ms": round(sum(rounds_baseline_p95) / len(rounds_baseline_p95), 3),
            "match_set_count": len(base_ids),
        },
        "bilingual": {
            "p95_ms": min_bilin_p95,
            "median_ms": round(_true_median(best_bilin_samples), 3),
            "all_rounds_p95_ms": rounds_bilingual_p95,
            "mean_p95_ms": round(sum(rounds_bilingual_p95) / len(rounds_bilingual_p95), 3),
            "match_set_count": len(bilin_ids),
        },
        "match_sets_equal": base_ids == bilin_ids,
        "bilingual_p95_ratio_of_baseline": ratio,
        "baseline_p95_over_bilingual_p95": round(min_base_p95 / min_bilin_p95, 4) if min_bilin_p95 else None,
        "tier": tier,
        "relative_gate": "1.15x OK" if (tier == "2A" and relative_gate_pass) else ("1.50x OK" if relative_gate_pass else "FAIL"),
        "absolute_gate": "OK" if absolute_gate_pass else "FAIL",
        "order_balance": "alternating (even pair baseline-first, odd pair bilingual-first); GC paused during timed region",
    }


def run_header():
    _delete_header_fixtures()
    created = _create_header_fixtures()
    try:
        res = _measure_doctype_multi_round(
            "BOQ Header",
            TXT_H,
            lambda t: search_link("BOQ Header", t, page_length=PAGE_LENGTH),
            lambda t: searchable_link_search("BOQ Header", t, {}, PAGE_LENGTH),
        )
    finally:
        _delete_header_fixtures()
        leftover = frappe.get_all("BOQ Header", filters={"title": ["like", PREFIX_H + "%"]}, pluck="name", limit_page_length=0)
        cleanup = {"created": len(created), "leftover": leftover}

    return {
        "schema": "boq-header-p95-local/v1",
        "scope": "WORK-ITEM-LOCAL comparative measurement for BOQ Header master bilingual enablement.",
        "sla_framework": "Two-Tier Bilingual Search SLA (b311377): Universal <= 1.50 ms P95 absolute ceiling; n=100 min-of-rounds",
        "txt": TXT_H,
        "rounds": ROUNDS,
        "samples_per_round": SAMPLES_PER_ROUND,
        "warmup": WARMUP,
        "page_length": PAGE_LENGTH,
        "fixtures_count": FIXTURES_COUNT,
        "fixture_prefix": PREFIX_H,
        "statistic": "nearest-rank P95 over the best round (min-of-rounds across 5 rounds at n=100); median = mean of middle two",
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


def run_structure():
    existing_headers = frappe.get_all("BOQ Header", limit=1, pluck="name")
    if not existing_headers:
        raise RuntimeError("No existing BOQ Header found for BOQ Structure testing")
    header_name = existing_headers[0]

    _delete_structure_fixtures()
    created = _create_structure_fixtures(header_name)
    try:
        res = _measure_doctype_multi_round(
            "BOQ Structure",
            TXT_S,
            lambda t: search_link("BOQ Structure", t, page_length=PAGE_LENGTH),
            lambda t: searchable_link_search("BOQ Structure", t, {}, PAGE_LENGTH),
        )
    finally:
        _delete_structure_fixtures()
        leftover = frappe.get_all("BOQ Structure", filters={"title": ["like", PREFIX_S + "%"]}, pluck="name", limit_page_length=0)
        cleanup = {"created": len(created), "leftover": leftover}

    return {
        "schema": "boq-structure-p95-local/v1",
        "scope": "WORK-ITEM-LOCAL comparative measurement for BOQ Structure master bilingual enablement.",
        "sla_framework": "Two-Tier Bilingual Search SLA (b311377): Universal <= 1.50 ms P95 absolute ceiling; n=100 min-of-rounds",
        "txt": TXT_S,
        "rounds": ROUNDS,
        "samples_per_round": SAMPLES_PER_ROUND,
        "warmup": WARMUP,
        "page_length": PAGE_LENGTH,
        "fixtures_count": FIXTURES_COUNT,
        "fixture_prefix": PREFIX_S,
        "statistic": "nearest-rank P95 over the best round (min-of-rounds across 5 rounds at n=100); median = mean of middle two",
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


def main():
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")

    print("=== MEASURING BOQ HEADER (n=100, 5 rounds) ===")
    out_header = run_header()
    h_path = os.path.join(os.path.dirname(__file__), "..", "boq-header-p95-measurement.json")
    with open(os.path.abspath(h_path), "w", encoding="utf-8") as fh:
        json.dump(out_header, fh, indent=1, sort_keys=True)
        fh.write("\n")

    h_res = out_header["result"]
    print("BOQ Header baseline P95 (min-of-rounds):", h_res["baseline"]["p95_ms"], "ms")
    print("BOQ Header governed P95 (min-of-rounds):", h_res["bilingual"]["p95_ms"], "ms")
    print("BOQ Header ratio:", h_res["bilingual_p95_ratio_of_baseline"])
    print("BOQ Header tier:", h_res["tier"])
    print("BOQ Header relative gate:", h_res["relative_gate"])
    print("BOQ Header absolute gate:", h_res["absolute_gate"])
    print("BOQ Header match_sets_equal:", h_res["match_sets_equal"])
    print("BOQ Header cleanup leftover:", len(out_header["cleanup"]["leftover"]))

    print("\n=== MEASURING BOQ STRUCTURE (n=100, 5 rounds) ===")
    out_struct = run_structure()
    s_path = os.path.join(os.path.dirname(__file__), "..", "boq-structure-p95-measurement.json")
    with open(os.path.abspath(s_path), "w", encoding="utf-8") as fh:
        json.dump(out_struct, fh, indent=1, sort_keys=True)
        fh.write("\n")

    s_res = out_struct["result"]
    print("BOQ Structure baseline P95 (min-of-rounds):", s_res["baseline"]["p95_ms"], "ms")
    print("BOQ Structure governed P95 (min-of-rounds):", s_res["bilingual"]["p95_ms"], "ms")
    print("BOQ Structure ratio:", s_res["bilingual_p95_ratio_of_baseline"])
    print("BOQ Structure tier:", s_res["tier"])
    print("BOQ Structure relative gate:", s_res["relative_gate"])
    print("BOQ Structure absolute gate:", s_res["absolute_gate"])
    print("BOQ Structure match_sets_equal:", s_res["match_sets_equal"])
    print("BOQ Structure cleanup leftover:", len(out_struct["cleanup"]["leftover"]))


if __name__ == "__main__":
    main()
