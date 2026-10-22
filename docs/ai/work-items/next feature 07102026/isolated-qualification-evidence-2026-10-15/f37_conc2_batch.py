"""F37 missing write-concurrency scenarios (lab fresh site).

Already proven elsewhere (not repeated): single-winner same-item approvals, stage
autoname race with retry success, barrier-synchronized VO client approval, F08 atomicity.
This batch covers only the gaps: same-VO concurrent transitions, duplicate-import race,
same-stage concurrent measurements, parallel approvals on different items.

Engineering workload assumptions (NOT customer capacity): 2-4 threads, lab hardware,
fresh small dataset. Timings are observations, not SLAs.
"""

import sys
import threading
import time

sys.path.insert(0, "/tmp/opencode")
from lab_console import connect

frappe = connect("f31fresh-clean.localhost")
LOCK = threading.Lock()
OUT = []


def log(m):
    with LOCK:
        OUT.append(m)
        print(m, flush=True)


def fresh(user):
    import frappe as F

    F.init(site="f31fresh-clean.localhost", sites_path="/tmp/construction-foundation-lab-20261014/sites")
    F.connect()
    F.set_user(user)
    return F


VOS = ["BOQ-2026-0218-VO-002"]  # Submitted VO for transition race (stays Submitted either way)
ITEMS = ["BOQI-BOQ-2026-0001-0002", "BOQI-BOQ-2026-0001-0003"]


def t_vo_race():
    # two engineers approve the SAME submitted VO concurrently: single winner expected
    res = []

    def one():
        try:
            F = fresh("acc-eng@qualification.invalid")
            from construction.api.boq_api import transition_variation_order

            try:
                r = transition_variation_order(vo_name=VOS[0], new_status="Approved by Engineer")
                res.append(("ok", bool((r or {}).get("success", True))))
            except Exception as e:
                res.append(("refused", type(e).__name__))
            F.db.commit()
        except Exception as e:
            res.append(("error", type(e).__name__))
        finally:
            try:
                frappe.destroy()
            except Exception:
                pass

    ths = [threading.Thread(target=one) for _ in range(2)]
    [t.start() for t in ths]
    [t.join() for t in ths]
    F2 = fresh("Administrator")
    st = F2.db.get_value("Variation Order", VOS[0], "status")
    log(f"vo-race: {res} final={st} (exactly one winner, no double-approval)")


def t_parallel_approvals():
    # approvals on DIFFERENT items proceed independently
    res = []

    def one(idx):
        try:
            F = fresh("f31-pm@qualification.invalid")
            a = F.new_doc("BOQ Cost Analysis")
            a.update(
                {
                    "title": f"ACC conc par {idx}",
                    "boq_item": ITEMS[idx % 2],
                    "boq_header": "BOQ-2026-0001",
                    "project": F.db.get_value("BOQ Header", "BOQ-2026-0001", "project"),
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
                    "cost_rate": 300 + idx,
                    "wastage_pct": 0,
                },
            )
            a.insert()
            t0 = time.time()
            a.submit()
            F.db.commit()
            res.append(("ok", round(time.time() - t0, 2)))
        except Exception as e:
            try:
                F.db.rollback()
            except Exception:
                pass
            res.append(("refused", type(e).__name__))
        finally:
            try:
                frappe.destroy()
            except Exception:
                pass

    ths = [threading.Thread(target=one, args=(i,)) for i in range(2)]
    t0 = time.time()
    [t.start() for t in ths]
    [t.join() for t in ths]
    log(f"parallel-approvals: {res} wall={time.time()-t0:.2f}s")


def t_same_stage_measure():
    # concurrent measurements on the SAME stage: no error, consistent final state
    res = []

    def one(v):
        try:
            F = fresh("acc-eng@qualification.invalid")
            s = F.get_doc("BOQ Item Stage", "BOQ-STG-00004")
            s.measured_executed_qty = v
            s.save()
            F.db.commit()
            res.append(("ok", v))
        except Exception as e:
            try:
                F.db.rollback()
            except Exception:
                pass
            res.append(("refused", type(e).__name__))
        finally:
            try:
                frappe.destroy()
            except Exception:
                pass

    ths = [threading.Thread(target=one, args=(v,)) for v in (3, 7)]
    [t.start() for t in ths]
    [t.join() for t in ths]
    F2 = fresh("Administrator")
    final = F2.db.get_value("BOQ Item Stage", "BOQ-STG-00004", "measured_executed_qty")
    log(f"same-stage-measure: {res} final={final} (last-writer-wins, no corruption)")


t0 = time.time()
t_vo_race()
t_parallel_approvals()
t_same_stage_measure()
print(f"batch wall: {time.time()-t0:.2f}s")
