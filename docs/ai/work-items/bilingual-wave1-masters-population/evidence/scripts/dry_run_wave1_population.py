"""Tier 5B dry-run — exact before/after for the approved proposal, ZERO writes.

Read-only: never calls doc.save(), frappe.db.set_value() or any writer.
Writes a private before/after JSON (full values) next to the proposal; the
committed log carries row names + value digests only (SCOPE R4).
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
}


def sha16(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def byte_scan(value):
    problems = []
    if value != value.strip():
        problems.append("leading/trailing whitespace")
    for ch in value:
        cp = ord(ch)
        cat = unicodedata.category(ch)
        if cp in (0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0x200B, 0x200C, 0x200D, 0xFEFF):
            problems.append(f"bidi/zero-width U+{cp:04X}")
        elif cp < 0x20 or cp == 0x7F or (0x80 <= cp <= 0x9F):
            problems.append(f"control U+{cp:04X}")
        elif ch in ("ـ",):
            problems.append("tatweel")
        elif 0x0660 <= cp <= 0x0669:
            problems.append(f"Arabic-Indic digit U+{cp:04X}")
        elif cat in ("Cf", "Co", "Cs"):
            problems.append(f"format/surrogate {cat} U+{cp:04X}")
    return problems


def main():
    path = f"{PRIVATE}/proposal.json"
    raw = open(path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != APPROVED_SHA:
        print(f"FAIL: proposal sha {sha} != approved {APPROVED_SHA} (approval invalidated)")
        sys.exit(1)
    proposal = json.loads(raw)
    from construction.services.bilingual_service import normalize_arabic

    out_rows = []
    failures = []
    for row in proposal["rows"]:
        doctype, name = row["doctype"], row["name"]
        ar_field, norm_field, label_field = FIELDS[doctype]
        value = row["arabic"].strip()
        doc = frappe.get_doc(doctype, name)
        before = doc.get(ar_field)
        if before and before != value:
            failures.append(f"{doctype} {name}: populated with a DIFFERENT value: sha16={sha16(before)}")
            continue
        problems = byte_scan(value)
        if problems:
            failures.append(f"{doctype} {name}: byte-scan {problems}")
            continue
        norm = normalize_arabic(value)
        if not norm:
            failures.append(f"{doctype} {name}: derived norm empty")
            continue
        if doc.get(label_field) != row["english_label"]:
            failures.append(f"{doctype} {name}: english label drift on site")
            continue
        state = "ALREADY_APPLIED" if before == value else "WOULD_WRITE"
        print(
            f"DRY {doctype} {name!r} before={'<empty>' if not before else sha16(before)} "
            f"after={sha16(value)} norm={sha16(norm)} {state}"
        )
        out_rows.append(
            {
                "doctype": doctype, "name": name, "field": ar_field,
                "before": before, "after": value, "norm": norm,
                "state": state,
            }
        )

    # Exceptions must remain untouched (spot-assert: none of them carry Arabic now).
    for doctype, field in (("Item", "item_name_ar"), ("Customer", "customer_name_in_arabic"),
                           ("Supplier", "supplier_name_in_arabic")):
        n = len(
            frappe.get_all(
                doctype,
                filters=[[field, "is", "set"], [field, "!=", ""]],
                fields=["name"],
                limit_page_length=0,
            )
        )
        print(f"POPULATED_NOW {doctype}={n}")

    private = {
        "proposal_sha256": sha,
        "dry_run_utc": frappe.utils.now_datetime().isoformat(),
        "writes_performed": 0,
        "rows": out_rows,
    }
    with open(f"{PRIVATE}/dry-run.json", "w", encoding="utf-8") as fh:
        json.dump(private, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    dry_sha = hashlib.sha256(open(f"{PRIVATE}/dry-run.json", "rb").read()).hexdigest()

    would = sum(1 for r in out_rows if r["state"] == "WOULD_WRITE")
    already = sum(1 for r in out_rows if r["state"] == "ALREADY_APPLIED")
    print(f"SUMMARY rows={len(out_rows)} would_write={would} already_applied={already}")
    print(f"PRIVATE dry-run.json sha256={dry_sha}")
    print("WRITES_PERFORMED: 0")
    if failures:
        for f in failures:
            print("FAIL:", f)
        print("DRY-RUN RESULT: FAIL")
        sys.exit(1)
    if len(out_rows) != 9:
        print(f"FAIL: expected 9 rows, got {len(out_rows)}")
        sys.exit(1)
    print("DRY-RUN RESULT: PASS (9/9 rows validated; approved sha matched; zero writes)")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
