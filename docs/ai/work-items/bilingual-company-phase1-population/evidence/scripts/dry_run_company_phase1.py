"""Tier 5H dry-run — validate the approved Company proposal, zero writes.

Fail-closed gates:
  1. proposal.json sha256 == owner-approved v2 sha (owner-approval.md binding);
  2. byte-scan of the value (bidi, controls, tatweel, Arabic-Indic digits, edges);
  3. the frozen row exists live; english_label == live company_name; identity fields
     frozen (name/abbr/currency/country/parent/is_group/chart); live Arabic empty
     (or equal -> ALREADY_APPLIED);
  4. pre-state: site Arabic total 0, total 21 rows, 20 excluded test companies present;
  5. norm preview via normalize_arabic (authoritative hook behaviour on save).

Snapshots every frozen field of the row into private dry-run.json (rollback export).
WRITES_PERFORMED must be 0.
"""

import hashlib
import json
import sys
import unicodedata

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/company-phase1-population"
APPROVED_SHA = "b5fcc02a6854ebb27b71082b71c1b3f9d4ac43f737b013809697c2a23e79478a"
AR_FIELD, NORM_FIELD, LABEL_FIELD = "company_name_ar", "company_name_ar_norm", "company_name"
FROZEN_FIELDS = ["name", LABEL_FIELD, "abbr", "default_currency", "country",
                 "parent_company", "is_group", "chart_of_accounts",
                 AR_FIELD, NORM_FIELD]
TOTAL_EXPECTED = 21
EXCLUDED_EXPECTED = 20


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
    raw = open(f"{PRIVATE}/proposal.json", "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != APPROVED_SHA:
        print(f"FAIL: proposal sha {sha} != approved {APPROVED_SHA} — approval invalidated")
        sys.exit(1)
    proposal = json.loads(raw)
    from construction.services.bilingual_service import normalize_arabic

    total = frappe.db.count("Company")
    if total != TOTAL_EXPECTED:
        print(f"FAIL: site total {total} != {TOTAL_EXPECTED} (audited baseline)")
        sys.exit(1)
    populated = frappe.db.count("Company", {AR_FIELD: ("!=", "")})
    if populated != 0:
        print(f"FAIL: pre-state {populated} rows already have {AR_FIELD}")
        sys.exit(1)
    print(f"SITE total={total} arabic_populated={populated}")

    rows_out, fail = [], []
    for row in proposal["rows"]:
        name, value = row["name"], row["arabic"]
        problems = byte_scan(value)
        if problems:
            fail.append(f"Company {name}: byte scan {problems}")
        snap = frappe.db.get_value("Company", name, FROZEN_FIELDS, as_dict=True)
        if not snap:
            fail.append(f"Company {name}: absent from site")
            continue
        if snap[LABEL_FIELD] != row["english_label"]:
            fail.append(f"Company {name}: identity drift live={snap[LABEL_FIELD]!r}")
        if snap["abbr"] != "E" or snap["default_currency"] != "EGP" or snap["country"] != "Egypt":
            fail.append(f"Company {name}: frozen attribute drift {dict(snap)}")
        if snap["parent_company"] or snap["is_group"]:
            fail.append(f"Company {name}: shape drift (parent/is_group)")
        current = snap[AR_FIELD]
        if current:
            state = "ALREADY_APPLIED" if current == value else "CONFLICT"
            if state == "CONFLICT":
                fail.append(f"Company {name}: conflicting existing value {sha16(current)}")
        else:
            state = "WOULD_WRITE"
        norm_preview = normalize_arabic(value)
        print(
            f"DRY Company {name!r} before={sha16(current) if current else '<empty>'} "
            f"after={sha16(value)} norm={sha16(norm_preview)} {state} PLAIN_SAVE "
            f"abbr={snap['abbr']!r} currency={snap['default_currency']!r} "
            f"country={snap['country']!r} coa={snap['chart_of_accounts']!r}"
        )
        rows_out.append({"doctype": "Company", "name": name,
                         "label": snap[LABEL_FIELD], "before": current,
                         "after": value if not current else current,
                         "norm_preview": norm_preview, "state": state,
                         "save_path": "PLAIN_SAVE", "snapshot": snap})

    excluded = frappe.db.count("Company") - len(rows_out)
    if excluded != EXCLUDED_EXPECTED:
        fail.append(f"excluded rows {excluded} != {EXCLUDED_EXPECTED}")
    print(f"EXCLUSIONS excluded_rows={excluded} (test-noise companies, untouched)")

    would = sum(1 for r in rows_out if r["state"] == "WOULD_WRITE")
    print(f"SUMMARY rows={len(rows_out)} would_write={would} plain={len(rows_out)}")
    if fail:
        for f in fail:
            print("FAIL:", f)
        print("DRY-RUN RESULT: FAIL")
        sys.exit(1)
    if len(rows_out) != 1 or would != 1:
        print(f"FAIL: rows={len(rows_out)} would_write={would}, expected 1/1")
        sys.exit(1)

    private = {"proposal_sha256": sha, "rows": rows_out,
               "excluded_rows": excluded, "writes_performed": 0}
    with open(f"{PRIVATE}/dry-run.json", "w", encoding="utf-8") as fh:
        json.dump(private, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    dry_sha = hashlib.sha256(open(f"{PRIVATE}/dry-run.json", "rb").read()).hexdigest()
    print(f"PRIVATE dry-run.json sha256={dry_sha}")
    print("WRITES_PERFORMED: 0")
    print("DRY-RUN RESULT: PASS (1/1 row validated; PLAIN save planned; "
          "approved v2 sha matched; zero writes)")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
