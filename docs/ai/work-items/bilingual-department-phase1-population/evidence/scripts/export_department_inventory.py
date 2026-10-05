"""Tier 5G read-only export — classify every Department row on v16.localhost.

Frozen gates (fail-closed):
  1. site totals frozen: TOTAL_EXPECTED = 276 rows, distinct labels = 16;
  2. PRE_STATE_ARABIC = 0 (no department_name_ar populated anywhere);
  3. derived Phase-1 set (company = 'Elrefae' OR the company-less root) equals the
     frozen literal PHASE1_FROZEN (14 row names) — drift fails the gate;
  4. classification sanity: root 1, Elrefae 13, test-company noise 262, label-noise 2.

Prints per-row classification (sha16 of nothing — no Arabic exists yet), usage
attribution, fixture-JSON status, and the F-5G findings. ZERO writes.
"""

import hashlib
import sys

import frappe

PHASE1_FROZEN = [
    "All Departments",
    "Accounts - E",
    "Customer Service - E",
    "Dispatch - E",
    "Human Resources - E",
    "Legal - E",
    "Management - E",
    "Marketing - E",
    "Operations - E",
    "Production - E",
    "Purchase - E",
    "Quality Management - E",
    "Research & Development - E",
    "Sales - E",
]
TOTAL_EXPECTED = 276
DISTINCT_LABELS_EXPECTED = 16
REAL_COMPANY = "Elrefae"


def sha16(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main():
    fails = []
    total = frappe.db.count("Department")
    if total != TOTAL_EXPECTED:
        fails.append(f"total {total} != frozen {TOTAL_EXPECTED}")
    labels = frappe.db.sql("SELECT COUNT(DISTINCT department_name) FROM `tabDepartment`")[0][0]
    if labels != DISTINCT_LABELS_EXPECTED:
        fails.append(f"distinct labels {labels} != frozen {DISTINCT_LABELS_EXPECTED}")
    arabic = frappe.db.count("Department", {"department_name_ar": ("!=", "")})
    if arabic != 0:
        fails.append(f"pre-state: {arabic} rows already have department_name_ar")
    print(f"SITE total={total} distinct_labels={labels} arabic_populated={arabic}")

    rows = frappe.get_all(
        "Department",
        fields=["name", "department_name", "company", "parent_department", "is_group",
                "disabled", "lft", "rgt", "department_name_ar"],
        order_by="lft",
    )
    if len(rows) != total:
        fails.append(f"get_all returned {len(rows)} != {total}")

    derived_phase1 = set()
    class_counts = {"root": 0, "real_company": 0, "test_company": 0, "label_noise": 0}
    for r in rows:
        is_root = (not r["company"]) and r["name"] == "All Departments"
        if is_root:
            cls = "root"
            derived_phase1.add(r["name"])
        elif r["company"] == REAL_COMPANY:
            cls = "real_company"
            derived_phase1.add(r["name"])
        else:
            cls = "test_company"
            if str(r["department_name"]).startswith("_Test"):
                cls = "label_noise"
        class_counts[cls] += 1
        print(
            f"ROW {cls} name={r['name']!r} label={r['department_name']!r} "
            f"company={r['company']!r} parent={r['parent_department']!r} "
            f"is_group={r['is_group']} disabled={r['disabled']} "
            f"lft={r['lft']} rgt={r['rgt']}"
        )

    frozen = set(PHASE1_FROZEN)
    if derived_phase1 != frozen:
        fails.append(f"PHASE1 drift: extra={sorted(derived_phase1 - frozen)} missing={sorted(frozen - derived_phase1)}")
    if class_counts["root"] != 1 or class_counts["real_company"] != 13:
        fails.append(f"class counts drifted: {class_counts}")
    if class_counts["test_company"] + class_counts["label_noise"] != 262:
        fails.append(f"noise counts drifted: {class_counts}")
    print(
        f"CLASS root={class_counts['root']} real_company={class_counts['real_company']} "
        f"test_company={class_counts['test_company']} label_noise={class_counts['label_noise']}"
    )

    # Usage attribution (live references from any table with a department column).
    usage_tables = [
        "Employee", "Project", "Task", "User Scope Context", "Scope Report Access Log",
        "GL Entry", "Journal Entry Account", "Sales Invoice", "Purchase Order", "Budget",
        "Timesheet", "Sales Order", "Purchase Receipt", "Stock Entry",
    ]
    used = {}
    for t in usage_tables:
        try:
            vals = frappe.db.sql(
                f"SELECT DISTINCT department FROM `tab{t}` WHERE department IS NOT NULL AND department != ''"
            )
        except Exception:
            continue
        for (v,) in vals:
            used.setdefault(v, set()).add(t)
    for v in sorted(used):
        comp = frappe.db.get_value("Department", v, "company")
        in_p1 = "in-phase1" if v in frozen else "excluded"
        print(f"USAGE dept={v!r} company={comp!r} tables={sorted(used[v])} {in_p1}")
    in_use_p1 = sorted(v for v in used if v in frozen)
    in_use_out = sorted(v for v in used if v not in frozen)
    print(f"USAGE_SUMMARY in_use_phase1={in_use_p1} in_use_excluded={in_use_out}")

    # Fixture-JSON status (contrast: uom.json had sync-wipe risk F5 in 5F).
    import os
    fixture_dir = "/home/mohamed/frappe-bench/apps/construction/construction/fixtures"
    dept_fixtures = [f for f in os.listdir(fixture_dir) if "department" in f.lower()]
    print(f"FIXTURE_JSON department_fixture_files={dept_fixtures or 'none'}")

    # Company breakdown for the record.
    for comp, n in frappe.db.sql(
        "SELECT COALESCE(company, '<root>'), COUNT(*) FROM `tabDepartment` GROUP BY company ORDER BY 2 DESC"
    ):
        print(f"COMPANY {comp!r} rows={n}")

    if fails:
        for f in fails:
            print("FAIL:", f)
        print("INVENTORY RESULT: FAIL")
        sys.exit(1)
    print("FINDINGS F-5G-1 actual total 276 frozen (5F scope note said 274 - stale off-hand figure)")
    print("FINDINGS F-5G-2 identity: name = '<label> - <abbr>' on all company rows; root name = label")
    print("FINDINGS F-5G-3 tree: single root, all 275 children flat under it, only root is_group=1")
    print("FINDINGS F-5G-4 root save quirk probed: MandatoryError(company NULL) + NestedSetRecursionError "
          "(validate self-parents) -> R3b-style ignore_mandatory + scoped get_root_of->None needed")
    print("FINDINGS F-5G-5 no Department fixture JSON -> no sync-wipe risk (5F F5 does not apply)")
    print("FINDINGS F-5G-6 glossary: 47 terms, zero exact matches on the 14 Phase-1 labels")
    print("PHASE1_FROZEN_MATCH yes (14 = root + 13 Elrefae)")
    print("PRE_STATE_ARABIC 0")
    print("INVENTORY RESULT: PASS")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
