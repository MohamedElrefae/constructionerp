"""Tier 5F apply — import the approved v2 proposal through standard doc.save().

Fail-closed gates before any write:
  1. proposal.json sha256 == the owner-approved v2 sha (owner-approval.md binding);
  2. private dry-run.json exists, bound to the same proposal sha, writes_performed == 0;
  3. bilingual fixture file already edited and byte-stable at the recorded post-edit sha
     (construction/fixtures/uom.json carries enabled:1 + uom_name_ar for all 12 rows and
     the Arabic values equal the approved proposal rows);
  4. byte-scan of each value (bidi, controls, tatweel, digits, whitespace).

All 15 rows are pre-validated before the first write; any failure rolls the transaction
back. The 12 fixture rows are saved with uom_name_ar + enabled=1 in ONE save (F1 site
enable); Nos/Tonne/Box get uom_name_ar only (already enabled). Norm keys are derived
server-side by the existing enforce_bilingual_arabic_policy validate hook — this script
never writes a _norm field itself. UOM is a flat doctype: no root/tree workaround applies.
"""

import hashlib
import json
import sys
import unicodedata

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/uom-phase1-population"
APPROVED_SHA = "18a16a953ebbaad704acc7982ed96de71808235c7fc5b258b6825fbd80598bbf"
UOM_JSON = "/home/mohamed/frappe-bench/apps/construction/construction/fixtures/uom.json"
UOM_JSON_POST_SHA = "d6e27a01483c841dccdb090277aa9c59459b270d52d40661bf9934d9e4c33ad2"
AR_FIELD, NORM_FIELD, LABEL_FIELD = "uom_name_ar", "uom_name_ar_norm", "uom_name"
FIXTURE_NAMES = {"M3", "M2", "M", "TON", "KG", "PCS", "LS", "DAY", "HR", "BAG", "LTR", "SET"}


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
    if dry.get("writes_performed") != 0:
        print("FAIL: dry-run did not record zero writes")
        sys.exit(1)
    dry_by = {r["name"]: r for r in dry.get("rows", [])}
    if len(dry_by) != 15:
        print(f"FAIL: dry-run row set has {len(dry_by)} rows, expected 15")
        sys.exit(1)

    # Gate 3: bilingual fixture file edited, byte-stable, consistent with the proposal.
    fx_raw = open(UOM_JSON, "rb").read()
    fx_sha = hashlib.sha256(fx_raw).hexdigest()
    if fx_sha != UOM_JSON_POST_SHA:
        print(f"FAIL: uom.json sha {fx_sha} != recorded post-edit {UOM_JSON_POST_SHA}")
        sys.exit(1)
    fx = json.loads(fx_raw)
    fx_by = {r["name"]: r for r in fx}
    if set(fx_by) != FIXTURE_NAMES:
        print("FAIL: uom.json row set drifted from the 12 fixture names")
        sys.exit(1)
    for r in fx:
        if r.get("enabled") != 1 or not r.get("uom_name_ar"):
            print(f"FAIL: uom.json row {r.get('name')} missing enabled/arabic")
            sys.exit(1)
        if "uom_name_ar_norm" in r:
            print(f"FAIL: uom.json row {r.get('name')} carries a norm key (contract: server-derived)")
            sys.exit(1)
        approved = next((x for x in proposal["rows"] if x["name"] == r["name"]), None)
        if not approved or approved["arabic"] != r["uom_name_ar"]:
            print(f"FAIL: uom.json row {r.get('name')} Arabic != approved proposal value")
            sys.exit(1)
    print(f"FIXTURE_FILE_GATE sha256={fx_sha} rows=12 consistent_with_proposal=yes")

    from construction.services.bilingual_service import normalize_arabic

    # Pre-validate EVERY row before the first write.
    plan = []
    for row in proposal["rows"]:
        name, value = row["name"], row["arabic"].strip()
        problems = byte_scan(value)
        if problems:
            print(f"FAIL pre-validate UOM {name}: {problems}")
            sys.exit(1)
        d = frappe.get_doc("UOM", name)
        if d.get(LABEL_FIELD) != row["english_label"]:
            print(f"FAIL pre-validate UOM {name}: english label drift")
            sys.exit(1)
        current = d.get(AR_FIELD)
        if current and current != value:
            print(f"FAIL pre-validate UOM {name}: conflicting existing value {sha16(current)}")
            sys.exit(1)
        if name not in dry_by:
            print(f"FAIL pre-validate UOM {name}: absent from dry-run")
            sys.exit(1)
        is_fixture = name in FIXTURE_NAMES
        if is_fixture and int(d.get("enabled") or 0):
            print(f"FAIL pre-validate UOM {name}: fixture already enabled (F1 pre-state drift)")
            sys.exit(1)
        plan.append({
            "name": name, "value": value, "already": bool(current),
            "fixture": is_fixture, "label_before": d.get(LABEL_FIELD),
            "enabled_before": int(d.get("enabled") or 0),
        })
    print(f"PREVALIDATE_OK rows={len(plan)} fixtures_to_enable={sum(1 for p in plan if p['fixture'])}")

    # Apply through the standard document lifecycle (validate hook derives _norm).
    results = []
    try:
        for item in plan:
            d = frappe.get_doc("UOM", item["name"])
            if item["already"]:
                print(f"SKIP UOM {item['name']!r} already applied")
                results.append({"name": item["name"], "action": "skip-already-applied"})
                continue
            d.set(AR_FIELD, item["value"])
            if item["fixture"]:
                d.set("enabled", 1)
            d.save()  # enforce_bilingual_arabic_policy: bidi gate + server-derived norm
            if d.get(LABEL_FIELD) != item["label_before"]:
                raise RuntimeError(f"UOM {item['name']}: english identity changed")
            if d.get(AR_FIELD) != item["value"]:
                raise RuntimeError(f"UOM {item['name']}: value not stored")
            expected_norm = normalize_arabic(item["value"])
            if d.get(NORM_FIELD) != expected_norm:
                raise RuntimeError(f"UOM {item['name']}: norm not server-derived")
            if item["fixture"] and int(d.get("enabled") or 0) != 1:
                raise RuntimeError(f"UOM {item['name']}: fixture enable not stored")
            print(
                f"WRITE UOM {item['name']!r} value={sha16(item['value'])} "
                f"norm={sha16(expected_norm)} identity=unchanged"
                + (" enabled=1" if item["fixture"] else "")
            )
            results.append({
                "name": item["name"], "action": "written", "value": item["value"],
                "norm": expected_norm, "fixture": item["fixture"],
                "enabled_after": int(d.get("enabled") or 0),
            })
        frappe.db.commit()
    except Exception as exc:  # noqa: BLE001 - fail-closed rollback
        frappe.db.rollback()
        print(f"FAIL during apply, transaction rolled back: {exc}")
        sys.exit(1)

    private = {
        "proposal_sha256": APPROVED_SHA,
        "dry_run_sha256": hashlib.sha256(dry_raw).hexdigest(),
        "fixture_json_sha256_after": fx_sha,
        "apply_utc": frappe.utils.now_datetime().isoformat(),
        "written": sum(1 for r in results if r["action"] == "written"),
        "skipped": sum(1 for r in results if r["action"] != "written"),
        "enabled": sum(1 for r in results if r.get("enabled_after") == 1 and r.get("fixture")),
        "results": results,
    }
    with open(f"{PRIVATE}/apply.json", "w", encoding="utf-8") as fh:
        json.dump(private, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    apply_sha = hashlib.sha256(open(f"{PRIVATE}/apply.json", "rb").read()).hexdigest()
    print(f"SUMMARY written={private['written']} skipped={private['skipped']} failed=0 "
          f"fixture_enabled={private['enabled']}")
    print(f"PRIVATE apply.json sha256={apply_sha}")
    print("APPLY RESULT: PASS")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
