"""Tier 5D post-import verification — independent read-back after apply.

Checks (all read-only):
  1. every approved row carries exactly the approved value (byte equality);
  2. stored _norm == normalize_arabic(stored value) for each row;
  3. stored values pass the byte/bidi scan;
  4. identity fields unchanged vs the approved proposal;
  5. completeness: 6 Item Group + 5 Customer Group + 8 Supplier Group + 4 Territory
     populated, norm-key search resolves every row;
  6. exception integrity: all 21 fixture rows still empty (pre-cycle state was empty
     for every row on these four trees);
  7. global totals unchanged (19 / 7 / 9 / 9) and prior-tier surfaces frozen:
     Account Arabic 81, wave-1 trio populated 3/6/5, wave-1 items 8, customers 1,
     suppliers 0, Company.company_name_ar untouched.
"""

import hashlib
import json
import sys
import unicodedata

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/wave2-group-masters-population"
APPROVED_SHA = "08dba90a8134c238d2e2e74b69081c0ec0c879ddecb82b2b7bb3a0ed2f6ea47e"
FIELDS = {
    "Item Group": ("item_group_name_ar", "item_group_name_ar_norm", "item_group_name"),
    "Customer Group": ("customer_group_name_ar", "customer_group_name_ar_norm", "customer_group_name"),
    "Supplier Group": ("supplier_group_name_ar", "supplier_group_name_ar_norm", "supplier_group_name"),
    "Territory": ("territory_name_ar", "territory_name_ar_norm", "territory_name"),
}
EXPECTED_TOTALS = {"Item Group": 19, "Customer Group": 7, "Supplier Group": 9, "Territory": 9}
EXPECTED_IN_SCOPE = {"Item Group": 6, "Customer Group": 5, "Supplier Group": 8, "Territory": 4}
# Prior-tier surfaces, frozen at pre-apply baseline (re-verified 2026-10-05).
FROZEN_PRIOR = {
    "items_ar": 8,
    "customers_ar": 1,
    "suppliers_ar": 0,
    "cost_centers_ar": 3,
    "warehouses_ar": 6,
    "projects_ar": 5,
    "accounts_ar": 81,
}


def sha16(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def byte_scan(value):
    problems = []
    if value != value.strip():
        problems.append("whitespace")
    for ch in value:
        cp = ord(ch)
        if cp in (0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
                  0x2066, 0x2067, 0x2068, 0x2069, 0x200B, 0x200C, 0x200D, 0xFEFF):
            problems.append(f"bidi/zw U+{cp:04X}")
        elif cp < 0x20 or cp == 0x7F or 0x80 <= cp <= 0x9F:
            problems.append(f"control U+{cp:04X}")
        elif ch == "ـ":
            problems.append("tatweel")
        elif 0x0660 <= cp <= 0x0669:
            problems.append(f"arabic-digit U+{cp:04X}")
        elif unicodedata.category(ch) in ("Cf", "Co", "Cs"):
            problems.append(f"format U+{cp:04X}")
    return problems


def main():
    fails = []
    raw = open(f"{PRIVATE}/proposal.json", "rb").read()
    if hashlib.sha256(raw).hexdigest() != APPROVED_SHA:
        print("FAIL: approved proposal bytes changed after import")
        sys.exit(1)
    proposal = json.loads(raw)
    from construction.services.bilingual_service import normalize_arabic

    # 1-4: per-row read-back.
    in_scope_names = {dt: set() for dt in FIELDS}
    for row in proposal["rows"]:
        doctype, name = row["doctype"], row["name"]
        ar_field, norm_field, label_field = FIELDS[doctype]
        d = frappe.get_doc(doctype, name)
        stored = d.get(ar_field)
        in_scope_names[doctype].add(name)
        if stored != row["arabic"]:
            fails.append(f"{doctype} {name}: stored value != approved (sha16={sha16(stored or '')})")
            continue
        if d.get(norm_field) != normalize_arabic(stored):
            fails.append(f"{doctype} {name}: stored norm inconsistent")
        problems = byte_scan(stored)
        if problems:
            fails.append(f"{doctype} {name}: byte scan {problems}")
        if d.get(label_field) != row["english_label"]:
            fails.append(f"{doctype} {name}: identity changed")
        print(
            f"ROW_OK {doctype} {name!r} value={sha16(stored)} "
            f"norm={sha16(d.get(norm_field) or '')} identity=unchanged"
        )

    # 5: completeness + norm-key search.
    total_populated = {}
    for doctype, (ar_field, norm_field, _lf) in FIELDS.items():
        populated_rows = frappe.get_all(
            doctype, filters={ar_field: ("!=", "")}, fields=["name"], limit_page_length=0
        )
        total_populated[doctype] = {r["name"] for r in populated_rows}
        expected = EXPECTED_IN_SCOPE[doctype]
        missing = in_scope_names[doctype] - total_populated[doctype]
        if missing:
            fails.append(f"{doctype}: in-scope rows not populated: {sorted(missing)}")
        if total_populated[doctype] - in_scope_names[doctype]:
            fails.append(
                f"{doctype}: fixture rows unexpectedly populated: "
                f"{sorted(total_populated[doctype] - in_scope_names[doctype])}"
            )
        print(
            f"COMPLETENESS {doctype} in_scope_populated="
            f"{expected - len(missing)}/{expected} site_arabic_total={len(total_populated[doctype])}"
        )

    norm_hits = 0
    for row in proposal["rows"]:
        doctype, name = row["doctype"], row["name"]
        norm_field = FIELDS[doctype][1]
        key = normalize_arabic(row["arabic"])
        hit = frappe.get_all(
            doctype, filters={norm_field: key}, fields=["name"], limit_page_length=5
        )
        if any(h["name"] == name for h in hit):
            norm_hits += 1
        else:
            fails.append(f"{doctype} {name}: norm-key search did not resolve the row")
    print(f"NORM_KEY_SEARCH resolved={norm_hits}/23")

    # 6: exception integrity — all 21 fixture rows still empty.
    for doctype, (ar_field, label_field, _lf) in (
        ("Item Group", ("item_group_name_ar", "item_group_name", None)),
        ("Customer Group", ("customer_group_name_ar", "customer_group_name", None)),
        ("Supplier Group", ("supplier_group_name_ar", "supplier_group_name", None)),
        ("Territory", ("territory_name_ar", "territory_name", None)),
    ):
        violations = []
        for r in frappe.get_all(
            doctype, fields=["name", label_field, ar_field], limit_page_length=0
        ):
            if r["name"] in in_scope_names[doctype]:
                continue
            if r[ar_field]:
                violations.append((r["name"], f"unexpected Arabic value sha16={sha16(r[ar_field])}"))
        if violations:
            fails.append(f"{doctype}: exception violations {violations}")
        else:
            print(f"EXCEPTIONS_OK {doctype}: all {EXPECTED_TOTALS[doctype] - EXPECTED_IN_SCOPE[doctype]} non-in-scope rows empty")

    # 7: totals unchanged + prior-tier surfaces frozen.
    for doctype, expected in EXPECTED_TOTALS.items():
        actual = frappe.db.count(doctype)
        if actual != expected:
            fails.append(f"{doctype} total {actual} != {expected} (rows created/deleted)")

    prior = {
        "items_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabItem` WHERE item_name_ar IS NOT NULL AND item_name_ar != ''"
        )[0][0],
        "customers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabCustomer` WHERE customer_name_in_arabic IS NOT NULL AND customer_name_in_arabic != ''"
        )[0][0],
        "suppliers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSupplier` WHERE supplier_name_in_arabic IS NOT NULL AND supplier_name_in_arabic != ''"
        )[0][0],
        "cost_centers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabCost Center` WHERE cost_center_name_ar IS NOT NULL AND cost_center_name_ar != ''"
        )[0][0],
        "warehouses_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabWarehouse` WHERE warehouse_name_ar IS NOT NULL AND warehouse_name_ar != ''"
        )[0][0],
        "projects_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabProject` WHERE project_name_ar IS NOT NULL AND project_name_ar != ''"
        )[0][0],
        "accounts_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabAccount` WHERE account_name_ar IS NOT NULL AND account_name_ar != ''"
        )[0][0],
    }
    for key, expected in FROZEN_PRIOR.items():
        if prior[key] != expected:
            fails.append(f"prior surface {key} = {prior[key]} != frozen {expected}")

    company_ar = frappe.db.get_value("Company", "Elrefae", "company_name_ar")
    if company_ar:
        fails.append(f"Company.company_name_ar was written: {sha16(company_ar)}")

    print(
        "FROZEN_SURFACES " + " ".join(f"{k}={prior[k]}" for k in sorted(prior))
        + f" company_ar={'empty' if not company_ar else 'WRITTEN'}"
    )
    print(
        "COUNTS_OK item_groups={} customer_groups={} supplier_groups={} territories={}".format(
            *[EXPECTED_TOTALS[dt] for dt in ("Item Group", "Customer Group", "Supplier Group", "Territory")]
        )
    )

    if fails:
        for f in fails:
            print("FAIL:", f)
        print("VERIFICATION RESULT: FAIL")
        sys.exit(1)
    print(
        "SUMMARY in_scope=23 populated=23 norm_consistent=23 identity_unchanged=23 "
        "exceptions=0 fixtures_untouched=21"
    )
    print(
        "ROLLBACK_REF dry-run.json (before-values: all empty) sha256="
        + hashlib.sha256(open(f"{PRIVATE}/dry-run.json", "rb").read()).hexdigest()
    )
    print("VERIFICATION RESULT: PASS")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
