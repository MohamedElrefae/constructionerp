"""Tier 5B apply — import the approved proposal through standard doc.save().

Fail-closed gates before any write:
  1. proposal.json sha256 == the owner-approved sha (R2 approval binding);
  2. private dry-run.json exists, references the same proposal sha, and every
     row is in a non-conflicting state (empty before / already-applied);
  3. byte-scan of each value (bidi, controls, tatweel, digits, whitespace).

All nine rows are pre-validated before the first write; any failure rolls the
transaction back. Norm keys are derived server-side by the existing
enforce_bilingual_arabic_policy validate hook — this script never writes a
_norm field itself.
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
    # Gate 1: approved proposal bytes.
    raw = open(f"{PRIVATE}/proposal.json", "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != APPROVED_SHA:
        print(f"FAIL: proposal sha {sha} != approved {APPROVED_SHA} — approval invalidated")
        sys.exit(1)
    proposal = json.loads(raw)

    # Gate 2: completed dry-run bound to the same proposal.
    dry_raw = open(f"{PRIVATE}/dry-run.json", "rb").read()
    dry = json.loads(dry_raw)
    if dry.get("proposal_sha256") != APPROVED_SHA:
        print("FAIL: dry-run is not bound to the approved proposal sha")
        sys.exit(1)
    dry_by = {(r["doctype"], r["name"]): r for r in dry.get("rows", [])}
    if len(dry_by) != 9:
        print(f"FAIL: dry-run row set has {len(dry_by)} rows, expected 9")
        sys.exit(1)

    from construction.services.bilingual_service import normalize_arabic

    # Pre-validate EVERY row before the first write.
    plan = []
    for row in proposal["rows"]:
        doctype, name = row["doctype"], row["name"]
        ar_field, norm_field, label_field = FIELDS[doctype]
        value = row["arabic"].strip()
        problems = byte_scan(value)
        if problems:
            print(f"FAIL pre-validate {doctype} {name}: {problems}")
            sys.exit(1)
        d = frappe.get_doc(doctype, name)
        if d.get(label_field) != row["english_label"]:
            print(f"FAIL pre-validate {doctype} {name}: english label drift")
            sys.exit(1)
        current = d.get(ar_field)
        if current and current != value:
            print(f"FAIL pre-validate {doctype} {name}: conflicting existing value {sha16(current)}")
            sys.exit(1)
        if (doctype, name) not in dry_by:
            print(f"FAIL pre-validate {doctype} {name}: absent from dry-run")
            sys.exit(1)
        plan.append(
            {
                "doctype": doctype, "name": name, "field": ar_field,
                "norm_field": norm_field, "label_field": label_field,
                "value": value, "already": bool(current),
                "label_before": d.get(label_field),
            }
        )
    print(f"PREVALIDATE_OK rows={len(plan)}")

    # Apply through the standard document lifecycle (validate hook derives _norm).
    results = []
    try:
        for item in plan:
            d = frappe.get_doc(item["doctype"], item["name"])
            if item["already"]:
                print(f"SKIP {item['doctype']} {item['name']!r} already applied")
                results.append({**{k: item[k] for k in ("doctype", "name")},
                                "action": "skip-already-applied"})
                continue
            d.set(item["field"], item["value"])
            d.save()  # enforce_bilingual_arabic_policy: bidi gate + server-derived norm
            if d.get(item["label_field"]) != item["label_before"]:
                raise RuntimeError(f"{item['doctype']} {item['name']}: english identity changed")
            if d.get(item["field"]) != item["value"]:
                raise RuntimeError(f"{item['doctype']} {item['name']}: value not stored")
            expected_norm = normalize_arabic(item["value"])
            if d.get(item["norm_field"]) != expected_norm:
                raise RuntimeError(f"{item['doctype']} {item['name']}: norm not server-derived")
            print(
                f"WRITE {item['doctype']} {item['name']!r} value={sha16(item['value'])} "
                f"norm={sha16(expected_norm)} identity=unchanged"
            )
            results.append({**{k: item[k] for k in ("doctype", "name")},
                            "action": "written", "value": item["value"],
                            "norm": expected_norm})
        frappe.db.commit()
    except Exception as exc:  # noqa: BLE001 - fail-closed rollback
        frappe.db.rollback()
        print(f"FAIL during apply, transaction rolled back: {exc}")
        sys.exit(1)

    private = {
        "proposal_sha256": APPROVED_SHA,
        "dry_run_sha256": hashlib.sha256(dry_raw).hexdigest(),
        "apply_utc": frappe.utils.now_datetime().isoformat(),
        "written": sum(1 for r in results if r["action"] == "written"),
        "skipped": sum(1 for r in results if r["action"] != "written"),
        "results": results,
    }
    with open(f"{PRIVATE}/apply.json", "w", encoding="utf-8") as fh:
        json.dump(private, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    apply_sha = hashlib.sha256(open(f"{PRIVATE}/apply.json", "rb").read()).hexdigest()
    print(f"SUMMARY written={private['written']} skipped={private['skipped']} failed=0")
    print(f"PRIVATE apply.json sha256={apply_sha}")
    print("APPLY RESULT: PASS")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
