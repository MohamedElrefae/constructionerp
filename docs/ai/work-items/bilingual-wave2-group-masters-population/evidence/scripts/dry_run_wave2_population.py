"""Tier 5D dry-run — validate the approved proposal against the live site, zero writes.

Fail-closed gates:
  1. proposal.json sha256 == owner-approved sha;
  2. byte-scan of every value (bidi, controls, tatweel, Arabic-Indic digits, edges);
  3. every row exists live, identity label matches the proposal, current Arabic empty;
  4. preview of the server-derived norm via normalize_arabic (the hook will do this
     authoritatively on save).

Writes private dry-run.json (before-state = rollback export). WRITES_PERFORMED must be 0.
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

    rows_out = []
    fail = []
    for row in proposal["rows"]:
        doctype, name = row["doctype"], row["name"]
        ar_field, norm_field, label_field = FIELDS[doctype]
        value = row["arabic"]
        problems = byte_scan(value)
        if problems:
            fail.append(f"{doctype} {name}: byte scan {problems}")
        try:
            d = frappe.get_doc(doctype, name)
        except frappe.DoesNotExistError:
            fail.append(f"{doctype} {name}: absent from site")
            continue
        live_label = d.get(label_field)
        if live_label != row["english_label"]:
            fail.append(f"{doctype} {name}: identity drift live={live_label!r} approved={row['english_label']!r}")
        current = d.get(ar_field)
        if current:
            if current != value:
                fail.append(f"{doctype} {name}: conflicting existing value {sha16(current)}")
            state = "ALREADY_APPLIED"
        else:
            state = "WOULD_WRITE"
        norm_preview = normalize_arabic(value)
        print(
            f"DRY {doctype} {name!r} before={sha16(current) if current else '<empty>'} "
            f"after={sha16(value)} norm={sha16(norm_preview)} {state}"
        )
        rows_out.append({
            "doctype": doctype, "name": name, "label": live_label,
            "before": current, "after": value if not current else current,
            "norm_preview": norm_preview, "state": state,
        })

    for doctype, (ar_field, _nf, _lf) in FIELDS.items():
        populated_now = len(
            frappe.get_all(doctype, filters={ar_field: ("!=", "")}, fields=["name"], limit_page_length=0)
        )
        print(f"POPULATED_NOW {doctype}={populated_now}")

    would = sum(1 for r in rows_out if r["state"] == "WOULD_WRITE")
    already = sum(1 for r in rows_out if r["state"] == "ALREADY_APPLIED")
    print(f"SUMMARY rows={len(rows_out)} would_write={would} already_applied={already}")
    if fail:
        for f in fail:
            print("FAIL:", f)
        print("DRY-RUN RESULT: FAIL")
        sys.exit(1)
    if len(rows_out) != 23:
        print(f"FAIL: {len(rows_out)} rows validated, expected 23")
        sys.exit(1)

    private = {
        "proposal_sha256": sha,
        "rows": rows_out,
        "writes_performed": 0,
    }
    with open(f"{PRIVATE}/dry-run.json", "w", encoding="utf-8") as fh:
        json.dump(private, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    dry_sha = hashlib.sha256(open(f"{PRIVATE}/dry-run.json", "rb").read()).hexdigest()
    print(f"PRIVATE dry-run.json sha256={dry_sha}")
    print("WRITES_PERFORMED: 0")
    print(f"DRY-RUN RESULT: PASS ({len(rows_out)}/23 rows validated; approved sha matched; zero writes)")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
