"""Tier 5C inventory export — phase-2 trio (Cost Center, Warehouse, Project).

Read-only. Fixture classification (R1), two rules applied in order:
  1. vendor fixture: name/label starts with `_Test` / `Test` / `CT-TEST` / `TEST-`;
  2. non-operating-company row: `company != Elrefae` (the site's only real company —
     every other Company row was created 2026-06-10 by ERPNext test records).
In-scope = every row of the trio whose company is Elrefae and is not a vendor fixture.
Asserts the frozen R1 allowlist matches the live site before any proposal work.
"""

import json
import sys

import frappe

OPERATING_COMPANY = "Elrefae"

IN_SCOPE = {
    "Cost Center": [
        "Elrefae - E",
        "Main - E",
        "Stage 8 Pilot - E",
    ],
    "Warehouse": [
        "All Warehouses - E",
        "Finished Goods - E",
        "Goods In Transit - E",
        "Stores - E",
        "Work In Progress - E",
    ],
    "Project": [
        "PROJ-0001",
        "PROJ-0002",
        "PROJ-0003",
        "PROJ-0008",
        "PROJ-0009",
    ],
}

TRIO = {
    "Cost Center": ("cost_center_name", "cost_center_name_ar"),
    "Warehouse": ("warehouse_name", "warehouse_name_ar"),
    "Project": ("project_name", "project_name_ar"),
}


def vendor_fixture(name, label):
    probes = (name, label or "")
    return any(
        p.startswith(("_Test", "Test", "CT-TEST", "TEST-"))
        for p in probes
    )


def main():
    fail = []
    print(f"PHASE2_INVENTORY_EXPORT v1 site={frappe.local.site} operating_company={OPERATING_COMPANY!r}")
    summary = {}

    companies = {c["name"] for c in frappe.get_all("Company", fields=["name"], limit_page_length=0)}
    if OPERATING_COMPANY not in companies:
        fail.append(f"operating company {OPERATING_COMPANY!r} missing from site")

    for doctype, (label_field, ar_field) in TRIO.items():
        rows = frappe.get_all(
            doctype,
            fields=["name", label_field, ar_field, "company"],
            limit_page_length=0,
        )
        in_scope_expected = set(IN_SCOPE[doctype])
        classified = {"in_scope": [], "vendor_fixture": [], "other_company": []}
        for r in rows:
            company = r.get("company")
            if vendor_fixture(r["name"], r[label_field]):
                classified["vendor_fixture"].append(r)
            elif company != OPERATING_COMPANY:
                classified["other_company"].append(r)
            else:
                classified["in_scope"].append(r)

        names_in_scope = {r["name"] for r in classified["in_scope"]}
        if names_in_scope != in_scope_expected:
            fail.append(
                f"{doctype}: rule-derived in-scope {sorted(names_in_scope)} != "
                f"frozen allowlist {sorted(in_scope_expected)}"
            )

        already = [r["name"] for r in classified["in_scope"] if r[ar_field]]
        if already:
            fail.append(f"{doctype}: in-scope rows already populated pre-cycle: {already}")

        missing_company = [
            r["name"] for r in rows if r.get("company") is None
        ]
        print(
            f"{doctype.replace(' ', '_').upper()} total={len(rows)} "
            f"in_scope={len(classified['in_scope'])} "
            f"vendor_fixture={len(classified['vendor_fixture'])} "
            f"other_company={len(classified['other_company'])}"
        )
        if missing_company:
            print(f"  rows_without_company_field {missing_company}")
        for r in sorted(classified["in_scope"], key=lambda x: x["name"]):
            print(
                f"  ROW IN_SCOPE name={r['name']!r} label={r[label_field]!r} "
                f"arabic={r[ar_field]!r} company={r.get('company')!r}"
            )
        for r in sorted(classified["vendor_fixture"], key=lambda x: x["name"]):
            print(
                f"  ROW VENDOR_FIXTURE name={r['name']!r} label={r[label_field]!r} "
                f"arabic={r[ar_field]!r}"
            )
        others = sorted(
            (r["company"], r["name"]) for r in classified["other_company"]
        )
        by_company = {}
        for company, name in others:
            by_company.setdefault(company, []).append(name)
        for company in sorted(by_company):
            print(
                f"  OTHER_COMPANY {company!r} rows={len(by_company[company])} "
                f"names={by_company[company]}"
            )
        summary[doctype] = [
            len(rows),
            len(classified["in_scope"]),
            len(classified["vendor_fixture"]),
            len(classified["other_company"]),
        ]

    # The only pre-existing Arabic value anywhere in the trio must be a fixture row.
    pre_populated = []
    for doctype, (label_field, ar_field) in TRIO.items():
        for r in frappe.get_all(
            doctype, fields=["name", label_field, ar_field, "company"], limit_page_length=0
        ):
            if r[ar_field]:
                pre_populated.append((doctype, r["name"], r[ar_field], r.get("company")))
    for doctype, name, ar, company in pre_populated:
        tag = "VENDOR_FIXTURE" if vendor_fixture(name, None) or company != OPERATING_COMPANY else "IN_SCOPE!"
        print(f"PRE_EXISTING_ARABIC {doctype} {name!r} value={ar!r} company={company!r} tag={tag}")
        if tag == "IN_SCOPE!":
            fail.append(f"{doctype} {name}: pre-existing Arabic on an in-scope row")
    if not pre_populated:
        print("PRE_EXISTING_ARABIC none")

    print("SUMMARY " + json.dumps(summary, sort_keys=True))
    if fail:
        for f in fail:
            print("FAIL:", f)
        print("INVENTORY RESULT: FAIL")
        sys.exit(1)
    print(
        "INVENTORY RESULT: PASS (R1 rule-derived in-scope matches frozen allowlist; "
        "pre-state of in-scope rows empty; all non-Elrefae rows classified as exceptions)"
    )


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
