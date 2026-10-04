"""Tier 5B post-import verification — independent read-back after apply.

Checks (all read-only):
  1. every approved row carries exactly the approved value (byte equality);
  2. stored _norm == normalize_arabic(stored value) for each row;
  3. stored values pass the byte/bidi scan;
  4. english identities unchanged vs the approved proposal;
  5. completeness + exception report: in-scope 9/9 populated, exception rows
     still empty, Supplier zero-population exception holds;
  6. global counts unchanged (no rows created/deleted anywhere);
  7. Account surface untouched (81 Arabic accounts before and after);
  8. bilingual search mapping resolves the new values (norm key path).
"""

import hashlib
import json
import sys
import unicodedata

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/wave1-population"
APPROVED_SHA = "a00cfb432ed6680eefb20f22cc852923f059ff9320533569cdb57791e1cd1c77"
FIELDS = {
    "Item": ("item_name_ar", "item_name_ar_norm", "item_name"),
    "Customer": ("customer_name_in_arabic", "customer_name_in_arabic_norm", "customer_name"),
    "Supplier": ("supplier_name_in_arabic", "supplier_name_in_arabic_norm", "supplier_name"),
}
SCAFFOLD = {
    "Item": ["Loyal Item", "Stock-Reco-batch-Item-1", "Stock-Reco-Serial-Item-1",
             "Stock-Reco-Serial-Item-2", "Test Asset Item", "Test Esstimate"],
    "Customer": ["Test Loyalty Customer"],
}
EXPECTED_TOTALS = {"Item": 43, "Customer": 12, "Supplier": 10}


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


def populated(doctype, field):
    return len(
        frappe.get_all(
            doctype,
            filters={field: ("!=", "")},
            fields=["name"],
            limit_page_length=0,
        )
    )


def main():
    fails = []
    raw = open(f"{PRIVATE}/proposal.json", "rb").read()
    if hashlib.sha256(raw).hexdigest() != APPROVED_SHA:
        print("FAIL: approved proposal bytes changed after import")
        sys.exit(1)
    proposal = json.loads(raw)
    from construction.services.bilingual_service import get_mapping, normalize_arabic

    # 1-4: per-row read-back.
    for row in proposal["rows"]:
        doctype, name = row["doctype"], row["name"]
        ar_field, norm_field, label_field = FIELDS[doctype]
        d = frappe.get_doc(doctype, name)
        stored = d.get(ar_field)
        if stored != row["arabic"]:
            fails.append(f"{doctype} {name}: stored value != approved (sha16={sha16(stored or '')})")
            continue
        if d.get(norm_field) != normalize_arabic(stored):
            fails.append(f"{doctype} {name}: stored norm inconsistent")
        problems = byte_scan(stored)
        if problems:
            fails.append(f"{doctype} {name}: byte scan {problems}")
        if d.get(label_field) != row["english_label"]:
            fails.append(f"{doctype} {name}: english identity changed")
        print(
            f"ROW_OK {doctype} {name!r} value={sha16(stored)} norm={sha16(d.get(norm_field) or '')} "
            f"identity=unchanged"
        )

    # 5: completeness + exceptions.
    counts = {}
    for doctype in FIELDS:
        counts[doctype] = populated(doctype, FIELDS[doctype][0])
    print(f"COMPLETENESS items={counts['Item']}/8 customers={counts['Customer']}/1 "
          f"suppliers={counts['Supplier']}/0 (zero-population exception)")
    if counts["Item"] != 8:
        fails.append(f"Item populated {counts['Item']} != 8")
    if counts["Customer"] != 1:
        fails.append(f"Customer populated {counts['Customer']} != 1")
    if counts["Supplier"] != 0:
        fails.append(f"Supplier populated {counts['Supplier']} != 0 (exception violated)")

    for doctype, names in SCAFFOLD.items():
        ar_field = FIELDS[doctype][0]
        for n in names:
            val = frappe.db.get_value(doctype, n, ar_field)
            if val:
                fails.append(f"EXCEPTION ROW WRITTEN: {doctype} {n}")
    fixture_written = [
        r["name"]
        for r in frappe.get_all("Item", fields=["name", "item_name_ar"], limit_page_length=0)
        if r["name"].startswith("_Test") and r["item_name_ar"]
    ]
    if fixture_written:
        fails.append(f"_Test* items carry Arabic (fixture protection violated): {fixture_written}")
    print(f"EXCEPTIONS_OK scaffold=7 fixture_items_written={len(fixture_written)}")

    # 6-7: global counts + Account untouched.
    for doctype, expected in EXPECTED_TOTALS.items():
        actual = frappe.db.count(doctype)
        if actual != expected:
            fails.append(f"{doctype} total {actual} != {expected} (rows created/deleted)")
    accounts_ar = frappe.db.sql(
        "SELECT COUNT(*) FROM `tabAccount` WHERE account_name_ar IS NOT NULL AND account_name_ar != ''"
    )[0][0]
    if accounts_ar != 81:
        fails.append(f"Account Arabic count {accounts_ar} != 81 (Account surface touched)")
    print(f"COUNTS_OK items={EXPECTED_TOTALS['Item']} customers={EXPECTED_TOTALS['Customer']} "
          f"suppliers={EXPECTED_TOTALS['Supplier']} accounts_arabic={accounts_ar}")

    # 8: registry mapping resolves against live schema + norm-key search path.
    for doctype in ("Item", "Customer"):
        cfg = get_mapping(doctype)
        if not cfg or cfg.get("state") != "active":
            fails.append(f"{doctype}: registry mapping not active/resolved")
    norm_hits = 0
    for row in proposal["rows"]:
        doctype, name = row["doctype"], row["name"]
        norm_field = FIELDS[doctype][1]
        key = normalize_arabic(row["arabic"])
        hit = frappe.get_all(
            doctype,
            filters={norm_field: key},
            fields=["name"],
            limit_page_length=5,
        )
        if any(h["name"] == name for h in hit):
            norm_hits += 1
        else:
            fails.append(f"{doctype} {name}: norm-key search did not resolve the row")
    print(f"NORM_KEY_SEARCH resolved={norm_hits}/9 mapping_states=active")

    if fails:
        for f in fails:
            print("FAIL:", f)
        print("VERIFICATION RESULT: FAIL")
        sys.exit(1)
    print("SUMMARY in_scope=9 populated=9 norm_consistent=9 identity_unchanged=9 exceptions=0")
    print("ROLLBACK_REF dry-run.json (before-values: all empty) sha256="
          + hashlib.sha256(open(f"{PRIVATE}/dry-run.json", "rb").read()).hexdigest())
    print("VERIFICATION RESULT: PASS")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
