"""Tier 5F dry-run — validate the approved v2 proposal against the live site, zero writes.

Fail-closed gates:
  1. proposal.json sha256 == owner-approved v2 sha (owner-approval.md binding);
  2. byte-scan of every value (bidi, controls, tatweel, Arabic-Indic digits, edges);
  3. every row exists live, identity (uom_name) matches the proposal, current Arabic empty;
  4. enablement pre-state: 12 fixture rows currently enabled=0 (F1), 3 in-use rows enabled=1;
  5. fixture file pre-state: construction/fixtures/uom.json has no enabled/uom_name_ar keys
     yet (records the sha that the bilingual edit will change);
  6. norm preview of server-derived value via normalize_arabic (authoritative on save).

Writes private dry-run.json (before-state = rollback export). WRITES_PERFORMED must be 0.
"""

import hashlib
import json
import sys
import unicodedata
from pathlib import Path

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/uom-phase1-population"
APPROVED_SHA = "18a16a953ebbaad704acc7982ed96de71808235c7fc5b258b6825fbd80598bbf"
UOM_JSON = Path("/home/mohamed/frappe-bench/apps/construction/construction/fixtures/uom.json")
FIXTURE_NAMES = {"M3", "M2", "M", "TON", "KG", "PCS", "LS", "DAY", "HR", "BAG", "LTR", "SET"}
AR_FIELD, NORM_FIELD, LABEL_FIELD = "uom_name_ar", "uom_name_ar_norm", "uom_name"


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

    # Fixture file pre-state (F5): bilingual edit not yet applied.
    fx_raw = UOM_JSON.read_bytes()
    fx = json.loads(fx_raw)
    fx_pre_sha = hashlib.sha256(fx_raw).hexdigest()
    fx_names = {r["name"] for r in fx}
    if fx_names != FIXTURE_NAMES:
        print(f"FAIL: fixture file names drifted: {sorted(fx_names ^ FIXTURE_NAMES)}")
        sys.exit(1)
    if any("enabled" in r or "uom_name_ar" in r for r in fx):
        print("FAIL: uom.json already carries enabled/uom_name_ar before the edit step")
        sys.exit(1)
    print(f"FIXTURE_FILE_PRE rows={len(fx)} bilingual_edit_applied=no sha256={fx_pre_sha}")

    rows_out = []
    fail = []
    for row in proposal["rows"]:
        name = row["name"]
        value = row["arabic"]
        problems = byte_scan(value)
        if problems:
            fail.append(f"UOM {name}: byte scan {problems}")
        try:
            d = frappe.get_doc("UOM", name)
        except frappe.DoesNotExistError:
            fail.append(f"UOM {name}: absent from site")
            continue
        if row["doctype"] != "UOM":
            fail.append(f"UOM {name}: unexpected doctype {row['doctype']}")
        live_label = d.get(LABEL_FIELD)
        if live_label != row["english_label"]:
            fail.append(f"UOM {name}: identity drift live={live_label!r} approved={row['english_label']!r}")
        current = d.get(AR_FIELD)
        if current:
            if current != value:
                fail.append(f"UOM {name}: conflicting existing value {sha16(current)}")
            state = "ALREADY_APPLIED"
        else:
            state = "WOULD_WRITE"
        is_fixture = name in FIXTURE_NAMES
        enabled = int(d.get("enabled") or 0)
        if is_fixture and enabled:
            fail.append(f"UOM {name}: fixture expected enabled=0 pre-apply (F1 pre-state drift)")
        if not is_fixture and not enabled:
            fail.append(f"UOM {name}: in-use row unexpectedly disabled")
        enable_state = "WOULD_ENABLE" if is_fixture else "ALREADY_ENABLED"
        norm_preview = normalize_arabic(value)
        print(
            f"DRY UOM {name!r} before={sha16(current) if current else '<empty>'} "
            f"after={sha16(value)} norm={sha16(norm_preview)} {state} {enable_state}"
        )
        rows_out.append({
            "doctype": "UOM", "name": name, "label": live_label,
            "before": current, "after": value if not current else current,
            "norm_preview": norm_preview, "state": state,
            "fixture": is_fixture, "enabled_before": enabled, "enable_state": enable_state,
        })

    populated_now = frappe.db.sql(
        "SELECT COUNT(*) FROM `tabUOM` WHERE uom_name_ar IS NOT NULL AND uom_name_ar != ''"
    )[0][0]
    print(f"POPULATED_NOW UOM={populated_now}")
    if populated_now != 0:
        fail.append(f"pre-state: {populated_now} rows already have uom_name_ar")

    would = sum(1 for r in rows_out if r["state"] == "WOULD_WRITE")
    already = sum(1 for r in rows_out if r["state"] == "ALREADY_APPLIED")
    enable = sum(1 for r in rows_out if r["enable_state"] == "WOULD_ENABLE")
    print(f"SUMMARY rows={len(rows_out)} would_write={would} already_applied={already} would_enable={enable}")
    if fail:
        for f in fail:
            print("FAIL:", f)
        print("DRY-RUN RESULT: FAIL")
        sys.exit(1)
    if len(rows_out) != 15:
        print(f"FAIL: {len(rows_out)} rows validated, expected 15")
        sys.exit(1)
    if enable != 12:
        print(f"FAIL: {enable} rows would be enabled, expected 12")
        sys.exit(1)

    private = {
        "proposal_sha256": sha,
        "fixture_json_sha256_before": fx_pre_sha,
        "rows": rows_out,
        "writes_performed": 0,
    }
    with open(f"{PRIVATE}/dry-run.json", "w", encoding="utf-8") as fh:
        json.dump(private, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    dry_sha = hashlib.sha256(open(f"{PRIVATE}/dry-run.json", "rb").read()).hexdigest()
    print(f"PRIVATE dry-run.json sha256={dry_sha}")
    print("WRITES_PERFORMED: 0")
    print(f"DRY-RUN RESULT: PASS (15/15 rows validated; 12 enables planned; approved v2 sha matched; zero writes)")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
