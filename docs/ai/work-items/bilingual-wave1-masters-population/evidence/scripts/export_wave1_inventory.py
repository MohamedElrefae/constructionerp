"""Tier 5B inventory export — wave-1 masters, fixture classification, coverage.

Read-only. Run: python3 .../export_wave1_inventory.py
Asserts the R1 in-scope allowlist matches the live site before any proposal work.
"""

import json
import sys

import frappe

IN_SCOPE_ITEMS = [
    "138-CMS Shoe",
    "Consulting",
    "LAB-MASON-001`",
    "Macbook Pro",
    "OH-SITE-ADMIN-001",
    "Photocopier",
    "PLANT-MIXER-001",
    "SUBCONCRETE-001",
]
IN_SCOPE_CUSTOMERS = ["Prestiga-Biz"]
IN_SCOPE_SUPPLIERS = []

# Scaffolding rows: not vendor _Test*, but recorded test material (R1 exceptions).
SCAFFOLD_ITEMS = {
    "Loyal Item",
    "Stock-Reco-batch-Item-1",
    "Stock-Reco-Serial-Item-1",
    "Stock-Reco-Serial-Item-2",
    "Test Asset Item",
    "Test Esstimate",
}
SCAFFOLD_CUSTOMERS = {"Test Loyalty Customer"}


def fixture(name):
    return name.startswith("_Test") or name.startswith("TEST-CONC-")


def rows(doctype, arabic_field, label_field):
    data = frappe.get_all(
        doctype,
        fields=["name", label_field, arabic_field],
        limit_page_length=0,
    )
    non_fixture = [r for r in data if not fixture(r["name"])]
    return data, non_fixture


def main():
    fail = []
    print("WAVE1_INVENTORY_EXPORT v1 site=%s" % frappe.local.site)

    items, items_nf = rows("Item", "item_name_ar", "item_name")
    customers, customers_nf = rows("Customer", "customer_name_in_arabic", "customer_name")
    suppliers, suppliers_nf = rows("Supplier", "supplier_name_in_arabic", "supplier_name")

    for label, all_rows, nf, in_scope, scaffold, arabic_field, label_field in (
        ("ITEM", items, items_nf, IN_SCOPE_ITEMS, SCAFFOLD_ITEMS, "item_name_ar", "item_name"),
        ("CUSTOMER", customers, customers_nf, IN_SCOPE_CUSTOMERS, SCAFFOLD_CUSTOMERS,
         "customer_name_in_arabic", "customer_name"),
        ("SUPPLIER", suppliers, suppliers_nf, IN_SCOPE_SUPPLIERS, set(),
         "supplier_name_in_arabic", "supplier_name"),
    ):
        nf_names = {r["name"] for r in nf}
        missing = [n for n in in_scope if n not in nf_names]
        if missing:
            fail.append(f"{label}: in-scope rows absent from site: {missing}")
        unexpected_nf = sorted(
            n
            for n in nf_names
            if n not in in_scope and n not in scaffold
        )
        populated_nf = sorted(
            r["name"] for r in nf if r[arabic_field]
        )
        print(f"{label}_TOTAL {len(all_rows)}")
        print(f"{label}_NON_FIXTURE {len(nf)}")
        print(f"{label}_IN_SCOPE {len(in_scope)}")
        print(f"{label}_SCAFFOLD_EXCEPTIONS {sorted(nf_names & scaffold)}")
        print(f"{label}_UNCLASSIFIED_NON_FIXTURE {unexpected_nf}")
        if unexpected_nf:
            fail.append(f"{label}: non-fixture rows missing from R1 lists: {unexpected_nf}")
        print(f"{label}_NON_FIXTURE_ALREADY_POPULATED {populated_nf}")
        for r in sorted(nf, key=lambda x: x["name"]):
            ar_val = r[arabic_field]
            marker = "IN_SCOPE" if r["name"] in in_scope else (
                "SCAFFOLD" if r["name"] in scaffold else "OTHER"
            )
            print(
                f"ROW {label} {marker} name={r['name']!r} label={r[label_field]!r} "
                f"arabic={ar_val!r}"
            )

    # Pre-state: every in-scope row must currently be empty (nothing to overwrite).
    for r in items_nf:
        if r["name"] in IN_SCOPE_ITEMS and r["item_name_ar"]:
            fail.append(f"ITEM {r['name']}: already populated before cycle: {r['item_name_ar']!r}")
    for r in customers_nf:
        if r["name"] in IN_SCOPE_CUSTOMERS and r["customer_name_in_arabic"]:
            fail.append(
                f"CUSTOMER {r['name']}: already populated before cycle: {r['customer_name_in_arabic']!r}"
            )

    print(
        "SUMMARY "
        + json.dumps(
            {
                "items": [len(items), len(items_nf), len(IN_SCOPE_ITEMS)],
                "customers": [len(customers), len(customers_nf), len(IN_SCOPE_CUSTOMERS)],
                "suppliers": [len(suppliers), len(suppliers_nf), len(IN_SCOPE_SUPPLIERS)],
            },
            sort_keys=True,
        )
    )
    if fail:
        for f in fail:
            print("FAIL:", f)
        print("INVENTORY RESULT: FAIL")
        sys.exit(1)
    print("INVENTORY RESULT: PASS (R1 allowlist matches live site; pre-state empty)")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
