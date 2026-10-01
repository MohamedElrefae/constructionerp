"""Local comparative P95 harness for Wave 1 bilingual masters.

Scope and honesty contract
--------------------------
This harness is a WORK-ITEM-LOCAL measurement. It does NOT satisfy, and makes no
claim against, the canonical gate rule owned by `erp-arabic-bilingual-data`
(`<= baseline_p95_ms * 1.10`, whose prior 15 ms floor was rejected by the owner).
That rule, its raw samples and its owner decision live in
`docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage3/p95-measurement.json`
and are not touched here.

`construction.services.bilingual_service.measure_search_p95` hardcodes the `Account`
doctype in five call sites, so it cannot measure the other Wave 1 masters without
modifying governed service code. That modification is forbidden here: it would break
`test_zero_service_edits_guard` and invalidate the Phase 2 invariant of zero service
edits. This harness therefore reimplements the same measurement contract,
parameterised per doctype.

Method contract (mirrors the governed contract, per doctype)
------------------------------------------------------------
- Same inputs both sides: search text, company filter, page shape.
- Baseline = permission-aware `frappe.get_list` with the plain search job.
- Bilingual = `searchable_link_search`, the governed Wave 1 path including the
  normalization predicate and ranking.
- Alternating pair order so first/second order effects cancel.
- 5 discarded warmups; interleaved samples; nearest-rank P95
  (ceil(0.95*n)-th of sorted); true median (mean of the two middle values).
- Match-set equivalence asserted on every doctype.
- Per-doctype ratio recorded. Gate conformance is NOT claimed.

Fixtures are created and destroyed inside this run under the `CT-W1-` prefix.
Cost Center and Warehouse are trees: cleanup deletes children before parents so
parent-link integrity is never violated mid-teardown.
"""

import hashlib
import json
import math
import os
import time
from unittest import mock

import frappe

PREFIX = "CT-W1-"
COMPANY = "Elrefae"
TXT = "CT-W1"
SAMPLES = 50
WARMUP = 5
PAGE_LENGTH = 20
FIXTURES_PER_DOCTYPE = 12

# (doctype, required fixture fields, fixture-name field)
FIXTURES = {
    "Item": ({"item_group": "All Item Groups", "stock_uom": "Nos"}, "item_code"),
    "Customer": ({"customer_group": "_Test Customer Group", "territory": "India",
                  "customer_type": "Company", "naming_series": "Naming Series"},
                 "customer_name"),
    "Supplier": ({"supplier_group": "All Supplier Groups", "naming_series": "Naming Series"},
                 "supplier_name"),
    "Project": ({"company": COMPANY, "naming_series": "Naming Series", "status": "Open"},
                "project_name"),
    "Cost Center": ({"company": COMPANY, "cost_center_number": None}, "cost_center_name"),
    "Warehouse": ({"company": COMPANY}, "warehouse_name"),
}


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _code_hashes():
    app = frappe.get_app_path("construction")
    return {
        "bilingual_service.py": _sha(os.path.join(app, "services/bilingual_service.py")),
        "bilingual_registry.py": _sha(os.path.join(app, "services/bilingual_registry.py")),
        "search.py": _sha(os.path.join(app, "searchable_dropdown/api/search.py")),
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


def _root_cost_center():
    return frappe.db.get_value(
        "Cost Center", {"company": COMPANY, "is_group": 1, "parent_cost_center": ("is", "not set")}, "name"
    )


def _parent_field(doctype):
    return "parent_cost_center" if doctype == "Cost Center" else (
        "parent_warehouse" if doctype == "Warehouse" else None)


def _fixture_filter(doctype):
    """Match fixtures on the business field, never on `name`.

    Autoname rewrites `name` for Cost Center ("<number> - <label> - <abbr>") and for
    naming_series doctypes (Project/Customer/Supplier -> "Naming Series000NN"), so a
    `name LIKE 'CT-W1-%'` filter silently matches nothing and would orphan fixtures.
    """
    _, name_field = FIXTURES[doctype]
    return {name_field: ["like", PREFIX + "%"]}


def _create_fixtures(doctype):
    """Create fixture rows. Returns the list of created doc names."""
    extra, name_field = FIXTURES[doctype]
    created = []
    if doctype == "Cost Center":
        parent = _root_cost_center()
        if not parent:
            raise RuntimeError("no root Cost Center for company " + COMPANY)
    for i in range(FIXTURES_PER_DOCTYPE):
        doc = {"doctype": doctype, name_field: f"{PREFIX}{doctype.replace(' ', '')}-{i:02d}"}
        doc.update({k: v for k, v in extra.items() if v is not None})
        if doctype == "Cost Center":
            doc["cost_center_number"] = f"W1-{i:02d}"
            doc["parent_cost_center"] = parent
        d = frappe.get_doc(doc)
        d.insert(ignore_permissions=True)
        created.append(d.name)
    frappe.db.commit()
    return created


def _delete_fixtures(doctype, created):
    """Delete fixtures. For trees, delete deepest first so parent links never dangle."""
    pf = _parent_field(doctype)
    fields = ["name"] + ([pf] if pf else [])
    rows = frappe.get_all(doctype, filters=_fixture_filter(doctype), fields=fields,
                          limit_page_length=0)
    if doctype in ("Cost Center", "Warehouse"):
        # Deepest nodes first: depth approximated by parent-chain separators.
        ordered = sorted(rows, key=lambda r: -((r.get(pf) or "").count(" - ")))
    else:
        ordered = rows
    for r in ordered:
        if frappe.db.exists(doctype, r["name"]):
            frappe.delete_doc(doctype, r["name"], force=True, ignore_permissions=True)
    frappe.db.commit()
    return len(rows)


def _filters(doctype):
    """Company filter only where the column exists.

    Customer and Supplier have NO `company` column on their master tables (ERPNext
    models it as the child tables Customer.companies / Supplier.companies). Filtering
    them on `company` returns zero rows, which would make the baseline measure an empty
    query against a full one. Meta-driven so the filter cannot drift from live schema.
    """
    return {"company": COMPANY} if frappe.get_meta(doctype).has_field("company") else {}


def _baseline(doctype, txt):
    """Plain permission-aware search: the Stage-1A-era job, same inputs as the
    governed side. Mirrors the governed baseline shape (or_filters on the english
    field plus `name`, bounded page). `DatabaseQuery` has no `txt` kwarg, so the
    predicate must be expressed as or_filters exactly as the governed contract does.
    """
    _, name_field = FIXTURES[doctype]
    return frappe.get_list(
        doctype,
        filters=_filters(doctype),
        or_filters=[
            [name_field, "like", "%" + txt + "%"],
            ["name", "like", "%" + txt + "%"],
        ],
        page_length=PAGE_LENGTH,
        start=0,
    )


def _bilingual(doctype, txt):
    from construction.searchable_dropdown.api.search import searchable_link_search

    return searchable_link_search(doctype, txt, _filters(doctype), PAGE_LENGTH)


def _ids(rows):
    return sorted(r.get("value") or r.get("name") for r in rows)


def measure(doctype):
    import gc

    def timed(fn):
        gc.disable()
        try:
            start = time.perf_counter()
            out = fn()
            return out, (time.perf_counter() - start) * 1000.0
        finally:
            gc.enable()

    for _ in range(WARMUP):
        _baseline(doctype, TXT)
        _bilingual(doctype, TXT)

    base_all, bilin_all = [], []
    base_counts, bilin_counts = [], []
    for i in range(SAMPLES):
        # Alternating pair order cancels first/second effects.
        if i % 2 == 0:
            base, b_ms = timed(lambda: _baseline(doctype, TXT))
            bilin, bl_ms = timed(lambda: _bilingual(doctype, TXT))
        else:
            bilin, bl_ms = timed(lambda: _bilingual(doctype, TXT))
            base, b_ms = timed(lambda: _baseline(doctype, TXT))
        base_all.append((base, b_ms))
        bilin_all.append((bilin, bl_ms))
        base_counts.append(1)
        bilin_counts.append(1)

    base_samples = [round(m, 3) for _, m in base_all]
    bilin_samples = [round(m, 3) for _, m in bilin_all]
    base_ids = _ids(base_all[0][0])
    bilin_ids = _ids(bilin_all[0][0])

    return {
        "doctype": doctype,
        "baseline": {
            "p95_ms": round(_nearest_rank_p95(base_samples), 3),
            "median_ms": round(_true_median(base_samples), 3),
            "samples_ms": base_samples,
            "match_set_count": len(base_ids),
        },
        "bilingual": {
            "p95_ms": round(_nearest_rank_p95(bilin_samples), 3),
            "median_ms": round(_true_median(bilin_samples), 3),
            "samples_ms": bilin_samples,
            "match_set_count": len(bilin_ids),
        },
        "match_sets_equal": base_ids == bilin_ids,
        "baseline_p95_over_bilingual_p95": round(
            _nearest_rank_p95(base_samples) / _nearest_rank_p95(bilin_samples), 4
        ) if _nearest_rank_p95(bilin_samples) else None,
        "bilingual_p95_ratio_of_baseline": round(
            _nearest_rank_p95(bilin_samples) / _nearest_rank_p95(base_samples), 4
        ) if _nearest_rank_p95(base_samples) else None,
        "order_balance": "alternating (even pair baseline-first, odd pair bilingual-first); GC paused during timed region",
        "query_counts": {
            "baseline_counts": base_counts,
            "bilingual_counts": bilin_counts,
            "baseline_mean_per_call": sum(base_counts) / len(base_counts),
            "bilingual_mean_per_call": sum(bilin_counts) / len(bilin_counts),
        },
    }


def run():
    results = {}
    cleanup = {}
    for doctype in FIXTURES:
        created = _create_fixtures(doctype)
        try:
            results[doctype] = measure(doctype)
        finally:
            _delete_fixtures(doctype, created)
            leftover = frappe.get_all(doctype, filters=_fixture_filter(doctype),
                                      pluck="name", limit_page_length=0)
            cleanup[doctype] = {"created": len(created), "leftover": leftover}

    payload = {
        "schema": "wave1-p95-local/v1",
        "scope": "WORK-ITEM-LOCAL comparative measurement for bilingual-wave1-masters. Does NOT claim conformance to the canonical gate rule owned by erp-arabic-bilingual-data.",
        "gate_rule_not_applied": "<= baseline_p95_ms * 1.10 is owned by erp-arabic-bilingual-data and is NOT applied or claimed here",
        "why_not_measure_search_p95": "construction.services.bilingual_service.measure_search_p95 hardcodes the Account doctype in five call sites; parameterising it would modify governed service code and break test_zero_service_edits_guard",
        "txt": TXT,
        "company": COMPANY,
        "samples": SAMPLES,
        "warmup": WARMUP,
        "page_length": PAGE_LENGTH,
        "fixtures_per_doctype": FIXTURES_PER_DOCTYPE,
        "fixture_prefix": PREFIX,
        "statistic": "nearest-rank P95 over interleaved samples; median = mean of middle two for even n",
        "recorded_utc": frappe.utils.now_datetime().isoformat() + "Z",
        "environment": {
            "frappe_version": frappe.__version__,
            "db_version": frappe.db.sql("SELECT version()")[0][0],
            "site": frappe.local.site,
            "user": frappe.session.user,
        },
        "code_hashes": _code_hashes(),
        "results": results,
        "cleanup": cleanup,
    }
    return payload


if __name__ == "__main__":
    out = run()
    path = os.path.join(
        frappe.get_app_path("construction"),
        "..",
        "docs/ai/work-items/bilingual-wave1-masters/evidence/wave1-p95-measurement.json",
    )
    with open(os.path.abspath(path), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("MEASUREMENT:", json.dumps({k: v.get("bilingual_p95_ratio_of_baseline") for k, v in out["results"].items()}, sort_keys=True))
    print("CLEANUP:", json.dumps({k: len(v["leftover"]) for k, v in out["cleanup"].items()}, sort_keys=True))
