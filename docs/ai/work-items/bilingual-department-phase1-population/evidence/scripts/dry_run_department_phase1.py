"""Tier 5G dry-run — validate the approved v2 Department proposal, zero writes.

Fail-closed gates:
  1. proposal.json sha256 == owner-approved v2 sha (owner-approval.md binding);
  2. byte-scan of every value (bidi, controls, tatweel, Arabic-Indic digits, edges);
  3. every frozen row exists live; english_label == live department_name; company matches;
     live Arabic empty (or equal -> ALREADY_APPLIED); tree shape matches expectations
     (root parent empty + is_group, children under root);
  4. pre-state: site Arabic total 0; excluded rows present (262);
  5. norm preview via normalize_arabic (authoritative hook behaviour on save).

Snapshots every frozen field of the 14 rows into private dry-run.json (rollback export).
WRITES_PERFORMED must be 0.
"""

import hashlib
import json
import sys
import unicodedata
from pathlib import Path

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/department-phase1-population"
APPROVED_SHA = "dba85a4ceba5826094c1c7b6e25117afe8e0a696bcb1c3564699b0d736bf64a4"
AR_FIELD, NORM_FIELD, LABEL_FIELD = "department_name_ar", "department_name_ar_norm", "department_name"
FROZEN_FIELDS = ["name", LABEL_FIELD, "parent_department", "company", "is_group",
                 "disabled", "lft", "rgt", AR_FIELD, NORM_FIELD]


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

    total = frappe.db.count("Department")
    if total != 276:
        print(f"FAIL: site total {total} != 276 (audited baseline)")
        sys.exit(1)
    populated = frappe.db.count("Department", {AR_FIELD: ("!=", "")})
    if populated != 0:
        print(f"FAIL: pre-state {populated} rows already have {AR_FIELD}")
        sys.exit(1)
    print(f"SITE total={total} arabic_populated={populated}")

    rows_out, fail = [], []
    for row in proposal["rows"]:
        name, value = row["name"], row["arabic"]
        problems = byte_scan(value)
        if problems:
            fail.append(f"Department {name}: byte scan {problems}")
        snap = frappe.db.get_value("Department", name, FROZEN_FIELDS, as_dict=True)
        if not snap:
            fail.append(f"Department {name}: absent from site")
            continue
        if snap[LABEL_FIELD] != row["english_label"]:
            fail.append(f"Department {name}: identity drift live={snap[LABEL_FIELD]!r}")
        if (snap["company"] or None) != (row["company"] or None):
            fail.append(f"Department {name}: company drift {snap['company']!r}")
        is_root = name == "All Departments"
        if is_root:
            if snap["parent_department"] or not snap["is_group"] or snap["company"]:
                fail.append(f"Department {name}: root shape drift")
            state_root = "R3B_ROOT_SAVE"
        else:
            if snap["parent_department"] != "All Departments" or snap["is_group"]:
                fail.append(f"Department {name}: child shape drift")
            state_root = "PLAIN_SAVE"
        current = snap[AR_FIELD]
        if current:
            state = "ALREADY_APPLIED" if current == value else "CONFLICT"
            if state == "CONFLICT":
                fail.append(f"Department {name}: conflicting existing value {sha16(current)}")
        else:
            state = "WOULD_WRITE"
        norm_preview = normalize_arabic(value)
        print(
            f"DRY Department {name!r} before={sha16(current) if current else '<empty>'} "
            f"after={sha16(value)} norm={sha16(norm_preview)} {state} {state_root} "
            f"lft={snap['lft']} rgt={snap['rgt']} parent={snap['parent_department']!r}"
        )
        rows_out.append({"doctype": "Department", "name": name,
                         "label": snap[LABEL_FIELD], "before": current,
                         "after": value if not current else current,
                         "norm_preview": norm_preview, "state": state,
                         "save_path": state_root, "snapshot": snap})

    excluded = frappe.db.count("Department") - len(rows_out)
    if excluded != 262:
        fail.append(f"excluded rows {excluded} != 262")
    print(f"EXCLUSIONS excluded_rows={excluded} (test-company noise, untouched)")

    would = sum(1 for r in rows_out if r["state"] == "WOULD_WRITE")
    root_saves = sum(1 for r in rows_out if r["save_path"] == "R3B_ROOT_SAVE")
    print(f"SUMMARY rows={len(rows_out)} would_write={would} plain={len(rows_out) - root_saves} r3b_root={root_saves}")
    if fail:
        for f in fail:
            print("FAIL:", f)
        print("DRY-RUN RESULT: FAIL")
        sys.exit(1)
    if len(rows_out) != 14 or root_saves != 1:
        print(f"FAIL: rows={len(rows_out)} root_saves={root_saves}, expected 14/1")
        sys.exit(1)

    private = {"proposal_sha256": sha, "rows": rows_out,
               "excluded_rows": excluded, "writes_performed": 0}
    with open(f"{PRIVATE}/dry-run.json", "w", encoding="utf-8") as fh:
        json.dump(private, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    dry_sha = hashlib.sha256(open(f"{PRIVATE}/dry-run.json", "rb").read()).hexdigest()
    print(f"PRIVATE dry-run.json sha256={dry_sha}")
    print("WRITES_PERFORMED: 0")
    print("DRY-RUN RESULT: PASS (14/14 rows validated; 13 plain + 1 R3B root planned; "
          "approved v2 sha matched; zero writes)")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
