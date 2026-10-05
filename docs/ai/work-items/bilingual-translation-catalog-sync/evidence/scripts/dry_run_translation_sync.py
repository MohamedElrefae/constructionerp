"""Zero-write dry run — bilingual-translation-catalog-sync.

Recomputes the approved proposal digest, validates the bound before-state, and
prints the exact planned glossary edit using sha16 digests only. Performs ZERO
database writes and ZERO file edits. Writes only the private dry-run record.

Privacy R4: no Arabic value is printed; the private record holds full values.
"""

import hashlib
import json
import sys
from pathlib import Path

import frappe

SITE = "v16.localhost"
REPO = Path("/home/mohamed/frappe-bench/apps/construction")
PRIVATE = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/translation-catalog-sync")
GLOSSARY = REPO / "construction" / "data" / "glossary" / "egyptian_construction_glossary.json"
PAYLOAD = REPO / "construction" / "data" / "translations" / "approved_ar_overrides.csv"
APPROVED_SHA = "a23a7dceb6cf4b794af47155317be63267fbab46a7334618bf05dfbceec9b9a0"


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def s16(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def main():
    print("=" * 78)
    print("DRY RUN bilingual-translation-catalog-sync")
    print("=" * 78)

    prop_path = PRIVATE / "proposal.json"
    raw_prop = prop_path.read_bytes()
    prop_sha = sha256_bytes(raw_prop)
    print(f"proposal sha256         : {prop_sha}")
    if prop_sha != APPROVED_SHA:
        print(f"FAIL: proposal sha != approved {APPROVED_SHA} (approval invalidated)")
        sys.exit(1)
    print("APPROVED_SHA matched    : yes")

    proposal = json.loads(raw_prop)
    gloss_before = sha256_bytes(GLOSSARY.read_bytes())
    payload_before = sha256_bytes(PAYLOAD.read_bytes())
    print(f"glossary sha256 (live)  : {gloss_before}")
    print(f"glossary sha256 expected: {proposal['glossary_sha256_before']}")
    if gloss_before != proposal["glossary_sha256_before"]:
        print("FAIL: live glossary sha != proposal before-sha")
        sys.exit(1)
    if payload_before != proposal["payload_sha256_before"]:
        print("FAIL: live payload sha != proposal before-sha")
        sys.exit(1)

    glossary = json.loads(GLOSSARY.read_bytes().decode("utf-8"))
    terms_by_src = {t["source_text"]: t for t in glossary["terms"]}

    patches = proposal["glossary_term_patches"]
    print(f"planned glossary patches: {len(patches)}")
    print(f"planned payload edits   : 0 (payload must stay byte-identical)")

    ok = True
    rows = []
    for p in patches:
        src = p["source_text"]
        term = terms_by_src.get(src)
        if term is None:
            print(f"FAIL: source {src!r} not found in glossary")
            ok = False
            continue
        cur_val = term.get("approved_ar") or ""
        want_before = p["field_changes"]["approved_ar"]["before_sha16"]
        want_after = p["field_changes"]["approved_ar"]["after_sha16"]
        after_val = p["after"]["approved_ar"]
        if s16(cur_val) != want_before:
            print(f"FAIL: {src!r} live value sha16 {s16(cur_val)} != expected before {want_before}")
            ok = False
            continue
        if s16(after_val) != want_after:
            print(f"FAIL: {src!r} proposed value sha16 {s16(after_val)} != recorded after {want_after}")
            ok = False
            continue
        forbidden = [t for t in (term.get("forbidden_ar") or []) if t and t in after_val]
        if forbidden:
            print(f"FAIL: {src!r} proposed value contains a forbidden term")
            ok = False
            continue
        print(f"PLANNED_GLOSSARY_EDIT {src!r} approved_ar {want_before} -> {want_after} "
              f"version {p['field_changes']['version']['before']} -> "
              f"{p['field_changes']['version']['after']}")
        print(f"                      usage_notes -> {p['field_changes']['usage_notes']['after_sha16']} "
              f"references -> {p['field_changes']['references']['after_sha16']}")
        rows.append({"source_text": src, "before_sha16": want_before, "after_sha16": want_after,
                     "after_value_private": after_val})

    print(f"predicted glossary sha256 after: {proposal['glossary_sha256_after']}")

    private = {
        "work_item": proposal["work_item"],
        "proposal_sha256": prop_sha,
        "dry_run_utc": frappe.utils.now_datetime().isoformat(),
        "db_writes_performed": 0,
        "file_edits_performed": 0,
        "planned_glossary_sha256_after": proposal["glossary_sha256_after"],
        "planned_rows": rows,
    }
    out = PRIVATE / "dry-run.json"
    out.write_bytes(json.dumps(private, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    print(f"private dry-run.json sha256    : {sha256_bytes(out.read_bytes())}")
    print("DB_WRITES_PERFORMED: 0")
    print("FILE_EDITS_PERFORMED: 0")
    if not ok or not patches:
        print("DRY-RUN RESULT: FAIL")
        sys.exit(1)
    print("DRY-RUN RESULT: PASS (proposal sha matched; before-state bound; zero writes)")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site=SITE, sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
