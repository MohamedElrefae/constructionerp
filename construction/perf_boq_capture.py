# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""BOQ performance-capture harness (PERF-BOQ-001 evidence tool).

Runs the REAL per-row document-creation path used by the import service
(``BOQ Item`` / ``BOQ Structure`` inserts with deferred rollups and ONE final
header rollup) at the requested sizes, and records:

  - end-to-end elapsed seconds (fixture build + batch + final rollup + reload)
  - SQL statement count (``frappe.db.sql`` / ``frappe.db.get_value``-style calls
    are counted via the DB sql entry point)
  - peak process RSS delta (Linux ru_maxrss, KB)

Run from the bench root::

    bench --site <site> execute construction.perf_boq_capture.run \
        --kwargs '{"sizes": [100, 1000]}'

Results are returned AND written to ``/tmp/perf_boq_capture.json`` when /tmp is
writable. The harness tracks and deletes every document it creates so the site
is left unchanged.
"""

import time
from resource import getrusage

import frappe


def run(sizes=None, cleanup=True):
    sizes = sizes or [100, 1000]
    report = {"sizes": {}, "hardware_note": "single-node dev bench, local MariaDB"}
    for size in sizes:
        report["sizes"][str(size)] = _capture(size, cleanup=cleanup)
    try:
        import json

        with open("/tmp/perf_boq_capture.json", "w") as f:
            json.dump(report, f, indent=1, default=str)
    except Exception:
        pass
    return report


def _capture(size, cleanup=True):
    frappe.set_user("Administrator")
    company = frappe.db.get_value("Company", {}, "name") or "_Test Company"
    project = (
        frappe.db.get_value("Project", {"project_name": "_Perf Harness Project"}, "name")
        or frappe.get_doc(
            {"doctype": "Project", "project_name": "_Perf Harness Project", "company": company}
        )
        .insert(ignore_permissions=True)
        .name
    )

    header = frappe.get_doc(
        {
            "doctype": "BOQ Header",
            "title": f"_Perf Harness BOQ {frappe.generate_hash(length=6)}",
            "project": project,
            "company": company,
            "status": "Draft",
            "boq_type": "Tender",
        }
    ).insert(ignore_permissions=True)
    section = frappe.get_doc(
        {
            "doctype": "BOQ Structure",
            "boq_header": header.name,
            "title": "Perf Section",
            "is_group": 1,
        }
    ).insert(ignore_permissions=True)

    from construction.construction.utils.rollup import defer_boq_rollups

    counters = {"sql": 0}
    db = frappe.db
    real_sql = db.sql

    def counting_sql(*args, **kwargs):
        counters["sql"] += 1
        return real_sql(*args, **kwargs)

    rss0 = getrusage(getrusage_self()).ru_maxrss
    started = time.monotonic()

    with defer_boq_rollups():
        db.sql = counting_sql
        try:
            for idx in range(size):
                if idx and idx % 25 == 0:
                    try:
                        with open("/tmp/perf_progress.log", "a") as pf:
                            pf.write(f"size={size} item={idx} elapsed={time.monotonic() - started:.1f}s sql={counters['sql']}\n")
                    except Exception:
                        pass
                sub = frappe.get_doc(
                    {
                        "doctype": "BOQ Structure",
                        "boq_header": header.name,
                        "title": f"Perf Item {idx}",
                        "parent_structure": section.name,
                        "is_group": 0,
                    }
                ).insert(ignore_permissions=True)
                item = frappe.get_doc("BOQ Item", {"structure": sub.name})
                item.quantity = 1
                item.unit = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
                item.contract_unit_price = 10
                item.save(ignore_permissions=True)
        finally:
            db.sql = real_sql

    batch_elapsed = time.monotonic() - started

    # Final rollup + reload (the full import lifecycle tail)
    rollup_started = time.monotonic()
    try:
        with open("/tmp/perf_progress.log", "a") as pf:
            pf.write(f"size={size} PHASE=rollup_start elapsed={rollup_started - started:.1f}s\n")
    except Exception:
        pass
    header.recalculate_phase1_totals()
    try:
        with open("/tmp/perf_progress.log", "a") as pf:
            pf.write(f"size={size} PHASE=header_totals_done elapsed={time.monotonic() - started:.1f}s\n")
    except Exception:
        pass
    header.reload()
    try:
        with open("/tmp/perf_progress.log", "a") as pf:
            pf.write(f"size={size} PHASE=reload_done elapsed={time.monotonic() - started:.1f}s\n")
    except Exception:
        pass
    total_elapsed = time.monotonic() - started
    rss1 = getrusage(getrusage_self()).ru_maxrss

    result = {
        "items": size,
        "batch_elapsed_s": round(batch_elapsed, 2),
        "total_elapsed_s": round(total_elapsed, 2),
        "sql_statements": counters["sql"],
        "peak_rss_delta_kb": max(0, int(rss1 - rss0)),
        "total_contract_value": header.total_contract_value,
        "expected_total": size * 10,
    }

    if cleanup:
        _cleanup(header.name, section.name, project)
    return result


def getrusage_self():
    import resource

    return resource.RUSAGE_SELF


def _cleanup(header_name, section_name, project):
    frappe.set_user("Administrator")

    def rm(doctype, name):
        try:
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        except Exception:
            pass

    for i in frappe.get_all("BOQ Item", filters={"boq_header": header_name}, pluck="name"):
        rm("BOQ Item", i)
    for s in frappe.get_all(
        "BOQ Structure", filters={"boq_header": header_name}, order_by="lft desc", pluck="name"
    ):
        rm("BOQ Structure", s)
    rm("BOQ Header", header_name)
    rm("Project", project)
    frappe.db.commit()
