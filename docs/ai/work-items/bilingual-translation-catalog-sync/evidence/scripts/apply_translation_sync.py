"""Governed apply — bilingual-translation-catalog-sync.

Applies the owner-approved glossary harmonisation, fail-closed:

1. recompute the proposal sha256 and abort unless it equals APPROVED_SHA;
2. abort unless the live glossary sha256 equals the proposal's before-sha;
3. patch the glossary JSON in memory, assert the serialised result equals the
   proposal's predicted after-sha, then (and only then) write the file;
4. assert the released payload CSV is byte-identical (zero payload edits);
5. assert the `Translation` doctype is byte-identical before/after
   (zero Translation writes).

Privacy R4: no Arabic value is printed; only sha16 digests and counts.
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

META_VERSION = "2.1"
META_DATE = "2026-10-05"


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def translation_digest():
    """Stable digest of every Arabic Translation row (proves zero writes)."""
    rows = frappe.get_all(
        "Translation",
        filters={"language": "ar"},
        fields=["name", "translated_text", "ct_origin", "ct_is_catalog_entry", "modified"],
        order_by="name asc",
        limit_page_length=0,
    )
    payload = json.dumps(
        [[r["name"], r.get("translated_text"), r.get("ct_origin"),
          r.get("ct_is_catalog_entry"), str(r.get("modified"))] for r in rows],
        ensure_ascii=False, sort_keys=True,
    )
    return sha256_bytes(payload.encode("utf-8")), len(rows)


def main():
    print("=" * 78)
    print("APPLY bilingual-translation-catalog-sync")
    print("=" * 78)

    prop_path = PRIVATE / "proposal.json"
    raw_prop = prop_path.read_bytes()
    prop_sha = sha256_bytes(raw_prop)
    print(f"proposal sha256         : {prop_sha}")
    if prop_sha != APPROVED_SHA:
        print(f"FAIL: proposal sha != approved {APPROVED_SHA} (fail-closed abort)")
        sys.exit(1)
    print("APPROVED_SHA matched    : yes")
    proposal = json.loads(raw_prop)

    raw_before = GLOSSARY.read_bytes()
    gloss_before = sha256_bytes(raw_before)
    if gloss_before != proposal["glossary_sha256_before"]:
        print(f"FAIL: live glossary sha {gloss_before} != before-sha "
              f"{proposal['glossary_sha256_before']} (fail-closed abort)")
        sys.exit(1)
    print(f"glossary sha256 before  : {gloss_before}")

    payload_before = sha256_bytes(PAYLOAD.read_bytes())
    if payload_before != proposal["payload_sha256_before"]:
        print("FAIL: live payload sha != before-sha (fail-closed abort)")
        sys.exit(1)
    print(f"payload sha256 (frozen) : {payload_before}")

    tdigest_before, tcount = translation_digest()
    print(f"Translation rows        : {tcount}")
    print(f"Translation digest before: {tdigest_before}")

    data = json.loads(raw_before.decode("utf-8"))
    if json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8") != raw_before:
        print("FAIL: cannot reproduce current glossary bytes (format drift); abort")
        sys.exit(1)

    meta = data["meta"]
    meta["previous_checksum"] = gloss_before
    meta["previous_version"] = meta.get("version")
    meta["version"] = META_VERSION
    meta["date"] = META_DATE

    by_src = {p["source_text"]: p for p in proposal["glossary_term_patches"]}
    patched = 0
    for term in data["terms"]:
        p = by_src.get(term.get("source_text"))
        if not p:
            continue
        before_val = term.get("approved_ar") or ""
        if hashlib.sha256(before_val.encode("utf-8")).hexdigest()[:16] != \
                p["field_changes"]["approved_ar"]["before_sha16"]:
            print(f"FAIL: {term['source_text']!r} live value diverged; abort")
            sys.exit(1)
        after = p["after"]
        term.clear()
        term.update(after)
        patched += 1
        print(f"PATCHED {term['source_text']!r} "
              f"approved_ar -> {p['field_changes']['approved_ar']['after_sha16']} "
              f"version -> {after.get('version')}")

    if patched != len(by_src):
        print(f"FAIL: patched {patched} of {len(by_src)} proposed terms; abort")
        sys.exit(1)
    print(f"meta version            : {meta['version']} (previous {meta['previous_version']})")

    raw_after = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    gloss_after = sha256_bytes(raw_after)
    print(f"glossary sha256 after   : {gloss_after}")
    print(f"glossary sha256 expected: {proposal['glossary_sha256_after']}")
    if gloss_after != proposal["glossary_sha256_after"]:
        print("FAIL: serialised after-sha != proposal prediction; abort WITHOUT writing")
        sys.exit(1)

    GLOSSARY.write_bytes(raw_after)
    print(f"WROTE {GLOSSARY.relative_to(REPO)}")

    if sha256_bytes(PAYLOAD.read_bytes()) != proposal["payload_sha256_after"]:
        print("FAIL: payload changed after apply; abort")
        sys.exit(1)
    print("payload sha256 after    : unchanged (byte-identical)")

    tdigest_after, tcount_after = translation_digest()
    if tdigest_after != tdigest_before or tcount_after != tcount:
        print("FAIL: Translation rows changed (digest mismatch); this cycle must not write them")
        sys.exit(1)
    print(f"Translation digest after : {tdigest_after} (identical)")
    print("TRANSLATION_DB_WRITES_PERFORMED: 0")

    private = proposal
    out = PRIVATE / "apply.json"
    apply_record = {
        "work_item": proposal["work_item"],
        "applied_utc": frappe.utils.now_datetime().isoformat(),
        "proposal_sha256": prop_sha,
        "glossary_sha256_before": gloss_before,
        "glossary_sha256_after": gloss_after,
        "payload_sha256": payload_before,
        "translation_digest_before": tdigest_before,
        "translation_digest_after": tdigest_after,
        "translation_row_count": tcount,
        "translation_db_writes": 0,
        "patched_terms": sorted(by_src),
    }
    out.write_bytes(json.dumps(apply_record, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    print(f"private apply.json sha256: {sha256_bytes(out.read_bytes())}")
    print("APPLY RESULT: PASS (1 glossary file edit; 0 Translation writes; payload frozen)")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site=SITE, sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
