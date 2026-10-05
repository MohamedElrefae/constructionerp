"""Tier 5J / V1 — build the private consolidated production values bundle (R4).

Sources (all private, owner-approved):
  1. seven proposal.json bundles (105 rows; uom-phase2 under `units`);
  2. site export for the three surfaces whose approvals predate the proposal pattern:
     Account (81, Stage-4 bundle provenance), Task (1), Terms and Conditions (1).

Fail-closed assertions:
  * every proposal row's Arabic value is byte-identical to the verified live site value;
  * populated-but-unapproved site rows == exactly the frozen 5C fixture
    `CT-TEST-P2-WH-01 - TQC`;
  * bundle row count == frozen 188, doctype set == frozen 15;
  * no Arabic value is printed or written outside the private bundle.

Writes: only sites/v16.localhost/private/production-migration/consolidated_values.json
Prints: counts, digests, verdict only (committed-evidence safe).
"""

import hashlib
import json
import sys

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private"
OUT_DIR = f"{PRIVATE}/production-migration"
OUT = f"{OUT_DIR}/consolidated_values.json"

SOURCES = [
    ("wave1-population", "rows"),                    # Item 8 + Customer 1 = 9
    ("wave1-phase2-population", "rows"),             # Cost Center 3 + Warehouse 5 + Project 5 = 13
    ("wave2-group-masters-population", "rows"),      # 4 groups = 23
    ("department-phase1-population", "rows"),        # 14
    ("company-phase1-population", "rows"),           # 1
    ("uom-phase1-population", "rows"),               # 15
    ("uom-phase2-triage", "units"),                  # 30 (units, UOM)
]
SITE_EXPORT = {
    "Account": "account_name_ar",
    "Task": "subject_ar",
    "Terms and Conditions": "title_ar",
}
EXPECTED_ROWS = 188
EXPECTED_DOCTYPES = {"Account", "Item", "Customer", "Cost Center", "Warehouse", "Project",
                     "Item Group", "Customer Group", "Supplier Group", "Territory",
                     "Department", "Company", "UOM", "Task", "Terms and Conditions"}
FIXTURE_EXCLUSION = ("Warehouse", "CT-TEST-P2-WH-01 - TQC")


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    fails = []
    rows = []          # {doctype, name, arabic, source}
    sources = {}

    # 1+2: proposal bundles, cross-checked against the live site byte-for-byte.
    for label, key in SOURCES:
        path = f"{PRIVATE}/{label}/proposal.json"
        digest = sha256_file(path)
        sources[label] = digest
        prop = json.loads(open(path, encoding="utf-8").read())
        got = prop.get("rows") if key == "rows" else prop.get("units")
        if not got:
            fails.append(f"{label}: no rows under {key!r}")
            continue
        for r in got:
            dt = r.get("doctype") or "UOM"
            name, arabic = r["name"], r["arabic"]
            live = None
            try:
                live = frappe.db.get_value(dt, name, _ar_field(dt))
            except Exception as exc:  # noqa: BLE001
                fails.append(f"{label}: lookup {dt} {name!r}: {exc}")
                continue
            if live != arabic:
                fails.append(f"{label}: site value != approved for {dt} {name!r} "
                             f"(site sha16={hashlib.sha256((live or '').encode()).hexdigest()[:16]})")
                continue
            rows.append({"doctype": dt, "name": name, "arabic": arabic, "source": label})
        print(f"SOURCE {label} rows={len(got)} sha256={digest}")

    # 3: site-export surfaces (approval predates proposal pattern).
    registry = json.load(open(
        "/home/mohamed/frappe-bench/apps/construction/construction/data/bilingual/bilingual_registry.json"))
    for dt, ar in SITE_EXPORT.items():
        n = 0
        for r in frappe.get_all(dt, filters={ar: ("!=", "")}, fields=["name"], limit_page_length=0):
            rows.append({"doctype": dt, "name": r["name"],
                         "arabic": frappe.db.get_value(dt, r["name"], ar),
                         "source": f"site-export(stage/legacy tier, {dt} provenance)"})
            n += 1
        print(f"SOURCE site-export {dt} rows={n}")

    # Assertions.
    populated, approved = {}, set()
    for dt, meta in registry["doctypes"].items():
        ar = meta.get("arabic_field")
        if not ar:
            continue
        try:
            names = {r["name"] for r in frappe.get_all(
                dt, filters={ar: ("!=", "")}, fields=["name"], limit_page_length=0)}
        except Exception:
            continue
        if names:
            populated[dt] = names
    for r in rows:
        approved.add((r["doctype"], r["name"]))

    if len(rows) != EXPECTED_ROWS:
        fails.append(f"bundle rows {len(rows)} != {EXPECTED_ROWS}")
    dts = {r["doctype"] for r in rows}
    if dts != EXPECTED_DOCTYPES:
        fails.append(f"doctype set drift: {sorted(dts ^ EXPECTED_DOCTYPES)}")
    populated_flat = {(dt, n) for dt, ns in populated.items() for n in ns}
    unapproved = populated_flat - approved
    if unapproved != {FIXTURE_EXCLUSION}:
        fails.append(f"populated-but-unapproved drift: {sorted(unapproved)}")
    if approved - populated_flat:
        fails.append(f"approved rows missing on site: {sorted(approved - populated_flat)[:5]}")

    if fails:
        for f in fails:
            print("FAIL:", f)
        print("CONSOLIDATE RESULT: FAIL")
        sys.exit(1)

    bundle = {
        "work_item": "production-migration-readiness",
        "site": "v16.localhost",
        "generated_utc": frappe.utils.now_datetime().isoformat(),
        "row_count": len(rows),
        "doctype_counts": {dt: sum(1 for r in rows if r["doctype"] == dt)
                           for dt in sorted(dts)},
        "source_sha256": sources,
        "site_export_doctypes": sorted(SITE_EXPORT),
        "excluded_fixture": {"doctype": FIXTURE_EXCLUSION[0], "name": FIXTURE_EXCLUSION[1],
                             "reason": "pre-existing test-site pilot row (5C frozen-excluded), "
                                       "does not exist on production"},
        "rows": rows,
    }
    raw = json.dumps(bundle, indent=2, ensure_ascii=False) + "\n"
    open(OUT, "w", encoding="utf-8").write(raw)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    print(f"BUNDLE rows={len(rows)} doctypes={len(dts)} "
          f"counts={json.dumps(bundle['doctype_counts'], sort_keys=True)}")
    print(f"UNAPPROVED_POPULATED == fixture-only: yes")
    print(f"PRIVATE consolidated_values.json sha256={digest}")
    print("CONSOLIDATE RESULT: PASS")


def _ar_field(doctype):
    registry = json.load(open(
        "/home/mohamed/frappe-bench/apps/construction/construction/data/bilingual/bilingual_registry.json"))
    return registry["doctypes"][doctype]["arabic_field"]


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
