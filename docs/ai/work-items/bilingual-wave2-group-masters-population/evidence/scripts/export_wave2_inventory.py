"""Tier 5D inventory export — wave-2 group masters (Item Group, Customer Group, Supplier Group, Territory).

Read-only. Fixture classification (R1), single rule (these four are global trees — no company field):
  vendor fixture: name or label starts with `_Test` (the only fixture family present on these trees).
In-scope = every non-fixture row of the four trees (expected 6 + 5 + 8 + 4 = 23).
Asserts the frozen R1 allowlist matches the live site before any proposal work.
Also asserts all four parent_* fields are optional (R3a expected dormant) and pre-state is empty.
"""

import json
import sys

import frappe

IN_SCOPE = {
    "Item Group": [
        "All Item Groups",
        "Consumable",
        "Products",
        "Raw Material",
        "Services",
        "Sub Assemblies",
    ],
    "Customer Group": [
        "All Customer Groups",
        "Commercial",
        "Government",
        "Individual",
        "Non Profit",
    ],
    "Supplier Group": [
        "All Supplier Groups",
        "Distributor",
        "Electrical",
        "Hardware",
        "Local",
        "Pharmaceutical",
        "Raw Material",
        "Services",
    ],
    "Territory": [
        "All Territories",
        "Egypt",
        "India",
        "Rest Of The World",
    ],
}

TREES = {
    "Item Group": ("item_group_name", "item_group_name_ar", "parent_item_group"),
    "Customer Group": ("customer_group_name", "customer_group_name_ar", "parent_customer_group"),
    "Supplier Group": ("supplier_group_name", "supplier_group_name_ar", "parent_supplier_group"),
    "Territory": ("territory_name", "territory_name_ar", "parent_territory"),
}


def vendor_fixture(name, label):
    probes = (name, label or "")
    return any(p.startswith("_Test") for p in probes)


def main():
    fail = []
    print(f"WAVE2_GROUP_INVENTORY_EXPORT v1 site={frappe.local.site}")
    summary = {}

    for doctype, (label_field, ar_field, parent_field) in TREES.items():
        rows = frappe.get_all(
            doctype,
            fields=["name", label_field, ar_field, parent_field, "is_group"],
            limit_page_length=0,
        )
        in_scope_expected = set(IN_SCOPE[doctype])
        classified = {"in_scope": [], "vendor_fixture": []}
        for r in rows:
            if vendor_fixture(r["name"], r[label_field]):
                classified["vendor_fixture"].append(r)
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

        root_rows = [r for r in classified["in_scope"] if not r[parent_field]]
        print(
            f"{doctype.replace(' ', '_').upper()} total={len(rows)} "
            f"in_scope={len(classified['in_scope'])} "
            f"vendor_fixture={len(classified['vendor_fixture'])} "
            f"roots_without_parent={len(root_rows)}"
        )
        for r in sorted(classified["in_scope"], key=lambda x: x["name"]):
            print(
                f"  ROW IN_SCOPE name={r['name']!r} label={r[label_field]!r} "
                f"arabic={r[ar_field]!r} parent={r[parent_field]!r} is_group={r['is_group']}"
            )
        for r in sorted(classified["vendor_fixture"], key=lambda x: x["name"]):
            print(
                f"  ROW VENDOR_FIXTURE name={r['name']!r} label={r[label_field]!r} "
                f"arabic={r[ar_field]!r}"
            )
        summary[doctype] = [
            len(rows),
            len(classified["in_scope"]),
            len(classified["vendor_fixture"]),
        ]

    # R3 precondition: all four parent_* fields must be optional (R3a stays dormant).
    import glob
    import os

    import erpnext

    erpnext_pkg = os.path.dirname(erpnext.__file__)
    parent_fields = ("parent_item_group", "parent_customer_group", "parent_supplier_group", "parent_territory")
    seen_meta = set()
    for path in sorted(glob.glob(os.path.join(erpnext_pkg, "**", "doctype", "*", "*.json"), recursive=True)):
        meta_name = os.path.basename(path).rsplit(".", 1)[0]
        if meta_name not in ("item_group", "customer_group", "supplier_group", "territory"):
            continue
        seen_meta.add(meta_name)
        meta = json.load(open(path))
        for field in meta.get("fields", []):
            if field.get("fieldname") in parent_fields and field.get("reqd"):
                fail.append(
                    f"{meta['name']}.{field['fieldname']} is required — R3a retry expected "
                    f"(update SCOPE R3 before apply)"
                )
    if seen_meta != {"item_group", "customer_group", "supplier_group", "territory"}:
        fail.append(f"doctype metadata not all found: {sorted(seen_meta)}")
    print("PARENT_FIELDS_OPTIONAL " + ("yes" if not any("is required" in f for f in fail) else "NO"))

    # No pre-existing Arabic anywhere on the four trees (clean pre-state).
    pre_populated = []
    for doctype, (label_field, ar_field, parent_field) in TREES.items():
        for r in frappe.get_all(doctype, fields=["name", label_field, ar_field], limit_page_length=0):
            if r[ar_field]:
                pre_populated.append((doctype, r["name"], r[ar_field]))
    for doctype, name, ar in pre_populated:
        tag = "VENDOR_FIXTURE" if vendor_fixture(name, None) else "IN_SCOPE!"
        print(f"PRE_EXISTING_ARABIC {doctype} {name!r} value={ar!r} tag={tag}")
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
        "pre-state of all in-scope rows empty; parent fields optional; all rows classified)"
    )


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
