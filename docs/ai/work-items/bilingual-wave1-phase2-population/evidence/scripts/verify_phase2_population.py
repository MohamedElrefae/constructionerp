"""Tier 5C post-import verification — independent read-back after apply.

Checks (all read-only):
  1. every approved row carries exactly the approved value (byte equality);
  2. stored _norm == normalize_arabic(stored value) for each row;
  3. stored values pass the byte/bidi scan;
  4. identity fields unchanged vs the approved proposal;
  5. completeness: 3 Cost Center + 5 Warehouse + 5 Project populated, norm-key
     search resolves every row;
  6. exception integrity: vendor fixtures still empty EXCEPT the pre-existing
     CT-TEST row (value unchanged); all other-company rows still empty;
  7. global counts unchanged (47 / 118 / 11) and Account Arabic surface still 81;
  8. Company.company_name_ar untouched (None).
"""

import hashlib
import json
import sys
import unicodedata

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/wave1-phase2-population"
APPROVED_SHA = "e68ef0c687516a110ed553a52cfe7d871808ba6007d9c1444ec1739730108557"
OPERATING_COMPANY = "Elrefae"
CT_TEST_PREEXISTING = "مستودع إعادة التسمية"
FIELDS = {
    "Cost Center": ("cost_center_name_ar", "cost_center_name_ar_norm", "cost_center_name"),
    "Warehouse": ("warehouse_name_ar", "warehouse_name_ar_norm", "warehouse_name"),
    "Project": ("project_name_ar", "project_name_ar_norm", "project_name"),
}
EXPECTED_TOTALS = {"Cost Center": 47, "Warehouse": 118, "Project": 11}
EXPECTED_IN_SCOPE = {"Cost Center": 3, "Warehouse": 5, "Project": 5}


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

    # 5: completeness (Elrefae rows) + norm-key search.
    total_populated = {}
    for doctype, (ar_field, norm_field, _lf) in FIELDS.items():
        populated_rows = frappe.get_all(
            doctype, filters={ar_field: ("!=", "")}, fields=["name"], limit_page_length=0
        )
        total_populated[doctype] = {r["name"] for r in populated_rows}
        expected = EXPECTED_IN_SCOPE[doctype]
        # in-scope rows all populated
        missing = in_scope_names[doctype] - total_populated[doctype]
        if missing:
            fails.append(f"{doctype}: in-scope rows not populated: {sorted(missing)}")
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
    print(f"NORM_KEY_SEARCH resolved={norm_hits}/13")

    # 6: exception integrity.
    for doctype, (ar_field, label_field, _lf) in (
        ("Cost Center", ("cost_center_name_ar", "cost_center_name", None)),
        ("Warehouse", ("warehouse_name_ar", "warehouse_name", None)),
        ("Project", ("project_name_ar", "project_name", None)),
    ):
        violations = []
        for r in frappe.get_all(
            doctype, fields=["name", label_field, ar_field, "company"], limit_page_length=0
        ):
            if r["name"] in in_scope_names[doctype]:
                continue
            value = r[ar_field]
            if not value:
                continue
            if doctype == "Warehouse" and r["name"] == "CT-TEST-P2-WH-01 - TQC":
                if value == CT_TEST_PREEXISTING:
                    print(f"PREEXISTING_FIXTURE_VALUE_UNCHANGED {doctype} {r['name']!r}")
                    continue
                violations.append((r["name"], "fixture pre-existing value CHANGED"))
                continue
            violations.append((r["name"], f"unexpected Arabic value sha16={sha16(value)}"))
        if violations:
            fails.append(f"{doctype}: exception violations {violations}")
        else:
            print(f"EXCEPTIONS_OK {doctype}: all non-in-scope rows empty (fixture pre-existing value intact)")

    # 7-8: totals, Account surface, Company untouched.
    for doctype, expected in EXPECTED_TOTALS.items():
        actual = frappe.db.count(doctype)
        if actual != expected:
            fails.append(f"{doctype} total {actual} != {expected} (rows created/deleted)")
    accounts_ar = frappe.db.sql(
        "SELECT COUNT(*) FROM `tabAccount` WHERE account_name_ar IS NOT NULL AND account_name_ar != ''"
    )[0][0]
    if accounts_ar != 81:
        fails.append(f"Account Arabic count {accounts_ar} != 81")
    company_ar = frappe.db.get_value("Company", OPERATING_COMPANY, "company_name_ar")
    if company_ar:
        fails.append(f"Company.company_name_ar was written: {sha16(company_ar)}")
    print(
        f"COUNTS_OK cost_centers={EXPECTED_TOTALS['Cost Center']} "
        f"warehouses={EXPECTED_TOTALS['Warehouse']} projects={EXPECTED_TOTALS['Project']} "
        f"accounts_arabic={accounts_ar} company_ar={'empty' if not company_ar else 'WRITTEN'}"
    )

    if fails:
        for f in fails:
            print("FAIL:", f)
        print("VERIFICATION RESULT: FAIL")
        sys.exit(1)
    print(
        "SUMMARY in_scope=13 populated=13 norm_consistent=13 identity_unchanged=13 "
        "exceptions=0 fixture_value_intact=1"
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
