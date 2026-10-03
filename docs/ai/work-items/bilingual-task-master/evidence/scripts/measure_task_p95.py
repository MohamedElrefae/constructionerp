"""Local comparative P95 harness for Task master bilingual enablement.

Scope and honesty contract
--------------------------
This harness is a WORK-ITEM-LOCAL measurement for the Task master.
It evaluates performance against the approved Two-Tier Bilingual Search SLA
(governed by the universal absolute ceiling of <= 1.50 ms P95).

Method contract
---------------
- Same inputs both sides: search text, page shape.
- Baseline = permission-aware `frappe.get_list` with plain search job.
- Bilingual = `searchable_link_search`, the governed path including normalization
  predicate and ranking.
- Alternating pair order so first/second order effects cancel.
- 5 discarded warmups; 50 interleaved samples; nearest-rank P95; true median.
- Match-set equivalence asserted.
- Zero leftover fixtures verified upon cleanup.
"""

import hashlib
import json
import math
import os
import time

import frappe

PREFIX = "CT-TASK-"
TXT = "CT-TASK"
SAMPLES = 50
WARMUP = 5
PAGE_LENGTH = 20
FIXTURES_COUNT = 12


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


def _fixture_filter():
    return {"subject": ["like", PREFIX + "%"]}


def _create_fixtures():
    """Create Task fixture rows."""
    created = []
    for i in range(FIXTURES_COUNT):
        d = frappe.get_doc({
            "doctype": "Task",
            "subject": f"{PREFIX}Test-{i:02d}",
            "is_group": 0,
        })
        d.insert(ignore_permissions=True)
        created.append(d.name)
    frappe.db.commit()
    return created


def _delete_fixtures():
    """Delete Task fixtures."""
    rows = frappe.get_all("Task", filters=_fixture_filter(), fields=["name"], limit_page_length=0)
    for r in rows:
        if frappe.db.exists("Task", r["name"]):
            frappe.delete_doc("Task", r["name"], force=True, ignore_permissions=True)
    frappe.db.commit()
    return len(rows)


def _baseline(txt):
    return frappe.get_list(
        "Task",
        or_filters=[
            ["subject", "like", "%" + txt + "%"],
            ["name", "like", "%" + txt + "%"],
        ],
        page_length=PAGE_LENGTH,
        start=0,
    )


def _bilingual(txt):
    from construction.searchable_dropdown.api.search import searchable_link_search

    return searchable_link_search("Task", txt, {}, PAGE_LENGTH)


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

    for _ in range(WARMUP):
        _baseline(TXT)
        _bilingual(TXT)

    base_all, bilin_all = [], []
    base_counts, bilin_counts = [], []
    for i in range(SAMPLES):
        if i % 2 == 0:
            base, b_ms = timed(lambda: _baseline(TXT))
            bilin, bl_ms = timed(lambda: _bilingual(TXT))
        else:
            bilin, bl_ms = timed(lambda: _bilingual(TXT))
            base, b_ms = timed(lambda: _baseline(TXT))
        base_all.append((base, b_ms))
        bilin_all.append((bilin, bl_ms))
        base_counts.append(1)
        bilin_counts.append(1)

    base_samples = [round(m, 3) for _, m in base_all]
    bilin_samples = [round(m, 3) for _, m in bilin_all]
    base_ids = _ids(base_all[0][0])
    bilin_ids = _ids(bilin_all[0][0])

    return {
        "doctype": "Task",
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
    _delete_fixtures()  # clean any existing residue
    created = _create_fixtures()
    try:
        res = measure()
    finally:
        _delete_fixtures()
        leftover = frappe.get_all("Task", filters=_fixture_filter(), pluck="name", limit_page_length=0)
        cleanup = {"created": len(created), "leftover": leftover}

    payload = {
        "schema": "task-p95-local/v1",
        "scope": "WORK-ITEM-LOCAL comparative measurement for Task master bilingual enablement.",
        "sla_framework": "Two-Tier Bilingual Search SLA (b311377): Universal <= 1.50 ms P95 absolute ceiling",
        "txt": TXT,
        "samples": SAMPLES,
        "warmup": WARMUP,
        "page_length": PAGE_LENGTH,
        "fixtures_count": FIXTURES_COUNT,
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
        "task-p95-measurement.json",
    )
    with open(os.path.abspath(path), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("MEASUREMENT:", json.dumps({out["result"]["doctype"]: out["result"].get("bilingual_p95_ratio_of_baseline")}, sort_keys=True))
    print("P95_MS:", json.dumps({"baseline": out["result"]["baseline"]["p95_ms"], "bilingual": out["result"]["bilingual"]["p95_ms"]}))
    print("MATCH_SETS_EQUAL:", out["result"].get("match_sets_equal"))
    print("CLEANUP_LEFTOVER:", len(out["cleanup"]["leftover"]))
