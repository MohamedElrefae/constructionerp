"""F37 dataset completion: 2nd project, 50 analyses, 5 VOs, 6-month history (lab fresh)."""

import sys
import time

sys.path.insert(0, "/tmp/opencode")
from lab_console import connect

frappe = connect("f31fresh-clean.localhost")
CO = "ACC Acceptance Co"
t0 = time.time()

# --- 2nd project ---
proj2 = frappe.db.get_value("Project", {"project_name": "ACC-002"}, "name")
if not proj2:
    proj2 = (
        frappe.get_doc({"doctype": "Project", "project_name": "ACC-002", "company": CO})
        .insert(ignore_permissions=True)
        .name
    )
    frappe.db.commit()
print("project2:", proj2)

# --- 50 analyses across workload items (approved, deterministic rates) ---
items = frappe.get_all(
    "BOQ Item", filters={"boq_header": "BOQ-2026-0008"}, fields=["name"], limit_page_length=50
)
made = 0
for i, it in enumerate(items):
    a = frappe.new_doc("BOQ Cost Analysis")
    a.update(
        {
            "title": f"ACC workload analysis {i:02d}",
            "boq_item": it.name,
            "boq_header": "BOQ-2026-0008",
            "project": frappe.db.get_value("BOQ Header", "BOQ-2026-0008", "project"),
            "company": CO,
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
            "cost_rate": 100 + i,
            "wastage_pct": 0,
        },
    )
    a.insert(ignore_permissions=True)
    a.submit()
    made += 1
frappe.db.commit()
print(f"approved analyses: {made} in {time.time()-t0:.1f}s")

# --- 6-month price history (backdated RPH rows, seeded history) ---
import datetime

base = datetime.date(2026, 4, 15)
n_rph = 0
for m in range(6):
    d = (base + datetime.timedelta(days=30 * m)).isoformat()
    r = frappe.get_doc(
        {
            "doctype": "Resource Price History",
            "naming_series": "RPH-.YYYY.-",
            "item_code": "ACC-Cement",
            "price_date": d,
            "rate": 100 + m,
            "currency": "EGP",
            "uom": "Nos",
            "company": CO,
            "status": "Active",
        }
    )
    r.insert(ignore_permissions=True)
    n_rph += 1
frappe.db.commit()
print(f"history rows: {n_rph} spanning 2026-04..2026-09")
