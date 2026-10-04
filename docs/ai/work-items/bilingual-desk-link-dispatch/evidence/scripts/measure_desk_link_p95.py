"""Local comparative P95 harness for Tier 4 desk Link dispatch.

Scope and honesty contract
--------------------------
This harness is a WORK-ITEM-LOCAL measurement for the desk Link dispatcher
(`construction.api.desk_link_search.search_link`, bound over
`frappe.desk.search.search_link` through `override_whitelisted_methods`).

The dispatcher has two code paths, and Frappe treats a translated doctype
differently from an ordinary one, so four cases are measured - each master is
represented by one translated doctype (UOM) and one ordinary doctype (Company):

* ``latin_passthrough_*`` - a Latin query must return the vendor result object
  unchanged. Both sides issue the identical call, so the ratio isolates
  dispatch overhead (one regex plus the wrapper frame) and the match sets must
  be equal.
* ``arabic_path_*`` - an Arabic query runs the vendor baseline and merges the
  registry half (settled decision A3). Both sides are timed on the same Arabic
  text: the plain side is what the stock endpoint returns for that text, the
  bilingual side is what desk actually calls after the override. The match sets
  differ BY DESIGN (the Arabic rows are the feature), so the harness asserts
  the baseline set is a SUBSET of the bilingual set instead of equality and
  records both counts.

As-designed means the A3 shape is measured unchanged; this harness does not
implement any candidate optimisation (see ``measure_registry_only_candidate``
for the decision input on skipping a redundant vendor baseline).

Method contract (identical to the bilingual master harnesses)
-------------------------------------------------------------
- Same inputs both sides: doctype, query text, page shape.
- Alternating pair order so first/second order effects cancel.
- 5 warmups per round; 5 rounds of n=100 interleaved samples (500 samples per
  side per case); min-of-rounds nearest-rank P95; true median over the best
  round.
- Tier selection per case: baseline min-of-rounds P95 >= 1.0 ms => Tier 2A
  (<= 1.15x), otherwise Tier 2B (<= 1.50x). Universal ceiling applies to both
  tiers.
- Zero leftover fixtures verified upon cleanup.
"""

import hashlib
import json
import math
import os
import time

import frappe

PREFIX = "CT-DISP-"
COMPANY_PREFIX = "CT-DISP-C-"
TXT_LATIN = "CT-DISP"
TXT_ARABIC = "اختبارية"
ARABIC_TEMPLATE = "وحدة قياس اختبارية {index:02d}"
COMPANY_ARABIC_TEMPLATE = "شركة مقاولات اختبارية {index:02d}"
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


def _company_fixture_filter():
    return {"company_name": ["like", COMPANY_PREFIX + "%"]}


def _create_company_fixtures():
    """Create Company fixture rows with Arabic labels (ordinary, non-translated doctype)."""
    created = []
    for i in range(FIXTURES_COUNT):
        doc = frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": f"{COMPANY_PREFIX}{i:02d}",
                "abbr": f"DC{i:02d}",
                "default_currency": "SAR",
                "country": "Saudi Arabia",
                "company_name_ar": COMPANY_ARABIC_TEMPLATE.format(index=i),
            }
        )
        doc.insert(ignore_permissions=True)
        created.append(doc.name)
    frappe.db.commit()
    return created


def _delete_company_fixtures():
    rows = frappe.get_all(
        "Company", filters=_company_fixture_filter(), fields=["name"], limit_page_length=0
    )
    for row in rows:
        if frappe.db.exists("Company", row["name"]):
            frappe.delete_doc("Company", row["name"], force=True, ignore_permissions=True)
    frappe.db.commit()
    return len(rows)


def _create_fixtures():
    """Create UOM fixture rows carrying Arabic labels and 3-char codes."""
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
    """Delete UOM fixtures."""
    rows = frappe.get_all(
        "UOM", filters=_fixture_filter(), fields=["name"], limit_page_length=0
    )
    for row in rows:
        if frappe.db.exists("UOM", row["name"]):
            frappe.delete_doc("UOM", row["name"], force=True, ignore_permissions=True)
    frappe.db.commit()
    return len(rows)


def _vendor(txt, doctype):
    """Plain side: the stock endpoint, called exactly as desk would call it."""
    return frappe.desk.search.search_link(
        doctype, txt, filters=None, page_length=PAGE_LENGTH
    )


def _dispatch(txt, doctype):
    """Bilingual side: the bound override entry point."""
    from construction.api.desk_link_search import search_link as dispatch_search_link

    return dispatch_search_link(
        doctype, txt, filters=None, page_length=PAGE_LENGTH
    )


def _ids(rows):
    return sorted(str(row.get("value")) for row in rows or [])


def _measure_case(case_name, doctype, txt, expect_equal, expect_subset):
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
            _vendor(txt, doctype)
            _dispatch(txt, doctype)

        base_times, bilin_times = [], []
        for i in range(SAMPLES):
            if i % 2 == 0:
                base, b_ms = timed(lambda: _vendor(txt, doctype))
                bilin, bl_ms = timed(lambda: _dispatch(txt, doctype))
            else:
                bilin, bl_ms = timed(lambda: _dispatch(txt, doctype))
                base, b_ms = timed(lambda: _vendor(txt, doctype))
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
    passthrough_identity = first_base == first_bilin
    subset = set(base_ids).issubset(set(bilin_ids))

    ratio = round(bilin_min_p95 / base_min_p95, 4) if base_min_p95 else None

    tier = "2A" if base_min_p95 >= TIER_THRESHOLD_MS else "2B"
    ceiling = TIER_2A_CEILING if tier == "2A" else TIER_2B_CEILING
    tier_pass = ratio is not None and ratio <= ceiling
    ceiling_pass = bilin_min_p95 <= UNIVERSAL_CEILING_MS

    if expect_equal:
        set_contract_pass = passthrough_identity and base_ids == bilin_ids
        set_contract = "exact equality (dispatcher returns the vendor object unchanged)"
    elif expect_subset:
        set_contract_pass = subset
        set_contract = "baseline set is a subset of the bilingual set (Arabic rows added by design)"
    else:
        set_contract_pass = False
        set_contract = "unspecified"

    return {
        "case": case_name,
        "doctype": doctype,
        "txt": txt,
        "baseline": {
            "p95_ms": base_min_p95,
            "round_p95_ms": rounds_base_p95,
            "median_ms": round(_true_median(rounds_base_samples[best_base_round]), 3),
            "best_round": best_base_round + 1,
            "match_set_count": len(base_ids),
            "match_set": base_ids,
        },
        "bilingual": {
            "p95_ms": bilin_min_p95,
            "round_p95_ms": rounds_bilin_p95,
            "median_ms": round(_true_median(rounds_bilin_samples[best_bilin_round]), 3),
            "best_round": best_bilin_round + 1,
            "match_set_count": len(bilin_ids),
            "match_set": bilin_ids,
        },
        "passthrough_identity": passthrough_identity,
        "baseline_subset_of_bilingual": subset,
        "match_sets_equal": base_ids == bilin_ids,
        "match_set_contract": set_contract,
        "match_set_contract_pass": set_contract_pass,
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
                if (tier_pass and ceiling_pass and set_contract_pass)
                else "NON_COMPLIANT"
            ),
        },
        "per_round_samples": {
            "baseline": rounds_base_samples,
            "bilingual": rounds_bilin_samples,
        },
    }


def measure():
    cases = {
        "latin_passthrough_uom": _measure_case(
            "latin_passthrough_uom", "UOM", TXT_LATIN, expect_equal=True, expect_subset=False
        ),
        "latin_passthrough_company": _measure_case(
            "latin_passthrough_company",
            "Company",
            TXT_LATIN,
            expect_equal=True,
            expect_subset=False,
        ),
        "arabic_path_uom": _measure_case(
            "arabic_path_uom", "UOM", TXT_ARABIC, expect_equal=False, expect_subset=True
        ),
        "arabic_path_company": _measure_case(
            "arabic_path_company",
            "Company",
            TXT_ARABIC,
            expect_equal=False,
            expect_subset=True,
        ),
    }
    return {
        "doctype": "UOM",
        "cases": cases,
        "all_cases_compliant": all(
            case["sla_evaluation"]["verdict"] == "COMPLIANT_WITH_TWO_TIER_SLA"
            for case in cases.values()
        ),
        "call_signature": (
            "both sides: search_link('UOM', txt, filters=None, page_length=20); "
            "baseline = frappe.desk.search.search_link, "
            "bilingual = construction.api.desk_link_search.search_link"
        ),
    }


def run():
    _delete_fixtures()  # clean any existing residue
    _delete_company_fixtures()
    created = _create_fixtures()
    created_companies = _create_company_fixtures()
    try:
        res = measure()
    finally:
        _delete_fixtures()
        _delete_company_fixtures()
        leftover_uom = frappe.get_all(
            "UOM", filters=_fixture_filter(), pluck="name", limit_page_length=0
        )
        leftover_company = frappe.get_all(
            "Company",
            filters=_company_fixture_filter(),
            pluck="name",
            limit_page_length=0,
        )
        cleanup = {
            "created": len(created),
            "leftover": leftover_uom,
            "created_companies": len(created_companies),
            "leftover_companies": leftover_company,
        }

    payload = {
        "schema": "desk-link-p95-local/v1",
        "scope": "WORK-ITEM-LOCAL comparative measurement for the Tier 4 desk Link dispatcher.",
        "sla_framework": "Two-Tier Bilingual Search SLA: universal <= 1.50 ms P95; Tier 2A <= 1.15x; Tier 2B <= 1.50x; min-of-rounds over 5 rounds at n=100",
        "txts": {"latin_cases": TXT_LATIN, "arabic_cases": TXT_ARABIC},
        "cases": [
            "latin_passthrough_uom (translated doctype)",
            "latin_passthrough_company (ordinary doctype)",
            "arabic_path_uom (translated doctype, as-designed A3)",
            "arabic_path_company (ordinary doctype, as-designed A3)",
        ],
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
        "desk-link-p95-measurement.json",
    )
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
            {name: case["sla_evaluation"] for name, case in cases.items()},
            sort_keys=True,
        ),
    )
    print(
        "MATCH_SETS:",
        json.dumps(
            {
                name: {
                    "equal": case["match_sets_equal"],
                    "passthrough_identity": case["passthrough_identity"],
                    "baseline_subset_of_bilingual": case["baseline_subset_of_bilingual"],
                    "contract_pass": case["match_set_contract_pass"],
                    "baseline_count": case["baseline"]["match_set_count"],
                    "bilingual_count": case["bilingual"]["match_set_count"],
                }
                for name, case in cases.items()
            },
            sort_keys=True,
        ),
    )
    print("ALL_CASES_COMPLIANT:", out["result"]["all_cases_compliant"])
    print(
        "CLEANUP_LEFTOVER:",
        json.dumps(
            {
                "uom": len(out["cleanup"]["leftover"]),
                "company": len(out["cleanup"]["leftover_companies"]),
            },
            sort_keys=True,
        ),
    )
