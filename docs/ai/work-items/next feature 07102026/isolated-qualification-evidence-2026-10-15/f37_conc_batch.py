"""F37 concurrency: writes, approvals, imports, reports on lab fresh site."""

import sys
import threading
import time
import traceback

sys.path.insert(0, "/tmp/opencode")
import frappe
from lab_console import connect

SITE = "f31fresh-clean.localhost"
RESULTS = []
LOCK = threading.Lock()


def log(msg):
    with LOCK:
        RESULTS.append(msg)
        print(msg, flush=True)


def fresh_connect(user):
    import frappe as F

    F.init(site=SITE, sites_path="/tmp/construction-foundation-lab-20261014/sites")
    F.connect()
    F.set_user(user)
    return F


def t_report():
    try:
        F = fresh_connect("f31-pm@qualification.invalid")
        from construction.api import construction_reports as R

        t0 = time.time()
        d = R.report_view("missing_analysis", company="ACC Acceptance Co", boq_header="BOQ-2026-0008")
        log(f"report: rows={d['row_count']} in {time.time()-t0:.2f}s")
    except Exception as e:
        log(f"report FAILED {type(e).__name__}: {str(e)[:100]}")
    finally:
        try:
            frappe.destroy()
        except Exception:
            pass


def t_approve(idx):
    try:
        F = fresh_connect("f31-pm@qualification.invalid")
        item = F.db.get_value("BOQ Item", {"boq_header": "BOQ-2026-0008"}, "name")
        a = F.new_doc("BOQ Cost Analysis")
        a.update(
            {
                "title": f"ACC conc approval {idx}",
                "boq_item": item,
                "boq_header": "BOQ-2026-0008",
                "project": F.db.get_value("BOQ Header", "BOQ-2026-0008", "project"),
                "company": "ACC Acceptance Co",
                "analysis_uom": "Nos",
                "currency": "EGP",
            }
        )
        a.append(
            "details",
            {
                "cost_stream": "M",
                "item_code": "ACC-Cement",
                "resource_uom": "Nos",
                "qty_per_boq_unit": 1,
                "cost_rate": 200 + idx,
                "wastage_pct": 0,
            },
        )
        a.insert()
        t0 = time.time()
        try:
            a.submit()
            F.db.commit()
            log(f"approve[{idx}]: SUBMITTED in {time.time()-t0:.2f}s")
        except Exception as e:
            F.db.rollback()
            F.delete_doc("BOQ Cost Analysis", a.name, ignore_permissions=True, force=True)
            F.db.commit()
            log(f"approve[{idx}]: refused-or-rolled-back {type(e).__name__}")
    except Exception as e:
        log(f"approve[{idx}] FAILED {type(e).__name__}: {str(e)[:100]}")
    finally:
        try:
            frappe.destroy()
        except Exception:
            pass


def t_write(idx):
    try:
        F = fresh_connect("f31-pm@qualification.invalid")
        t0 = time.time()
        st = F.new_doc("BOQ Item Stage")
        st.update(
            {
                "boq_header": "BOQ-2026-0001",
                "boq_item": F.db.get_value("BOQ Item", {"boq_header": "BOQ-2026-0001"}, "name"),
                "boq_structure": F.db.get_value("BOQ Item", {"boq_header": "BOQ-2026-0001"}, "structure"),
                "project": F.db.get_value("BOQ Header", "BOQ-2026-0001", "project"),
                "stage_name": f"ACC conc stage {idx}",
                "planned_qty": 5,
                "stage_status": "In Progress",
            }
        )
        st.insert()
        F.db.commit()
        log(f"write[{idx}]: stage {st.name} in {time.time()-t0:.2f}s")
    except Exception as e:
        log(f"write[{idx}] FAILED {type(e).__name__}: {str(e)[:100]}")
    finally:
        try:
            frappe.destroy()
        except Exception:
            pass


threads = []
for fn, args, n in (
    (t_report, (), 2),
    (t_approve, (0,), 1),
    (t_approve, (1,), 1),
    (t_write, (0,), 1),
    (t_write, (1,), 1),
):
    for _ in range(n):
        th = threading.Thread(target=fn, args=args if isinstance(args, tuple) else (args,))
        threads.append(th)
t0 = time.time()
for th in threads:
    th.start()
for th in threads:
    th.join()
print(f"concurrency batch wall: {time.time()-t0:.2f}s")
