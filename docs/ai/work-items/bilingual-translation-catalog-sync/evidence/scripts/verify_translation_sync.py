"""Post-sync verification — bilingual-translation-catalog-sync.

Proves the harmonisation outcome on the live site:
- live glossary sha equals the approved after-sha; payload byte-identical;
- effective rendered output (`get_all_translations('ar')`) matches the glossary
  for 47/47 terms, with zero forbidden-term violations at term keys;
- `assert_translation_health()` reports loader installed and drift false;
- the `Translation` digest is unchanged since apply (zero writes).

Privacy R4: sha16 digests and counts only; no Arabic value is printed.
"""

import hashlib
import json
import re
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


def translate_digest():
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
    failures = []
    print("=" * 78)
    print("POST-SYNC VERIFICATION bilingual-translation-catalog-sync")
    print("=" * 78)

    raw_prop = (PRIVATE / "proposal.json").read_bytes()
    if sha256_bytes(raw_prop) != APPROVED_SHA:
        failures.append("proposal sha != APPROVED_SHA")
    proposal = json.loads(raw_prop)
    apply_rec = json.loads((PRIVATE / "apply.json").read_bytes())

    gloss_sha = sha256_bytes(GLOSSARY.read_bytes())
    print(f"glossary sha256         : {gloss_sha}")
    print(f"glossary sha256 expected: {proposal['glossary_sha256_after']}")
    if gloss_sha != proposal["glossary_sha256_after"]:
        failures.append("glossary sha != approved after-sha")

    payload_sha = sha256_bytes(PAYLOAD.read_bytes())
    print(f"payload sha256          : {payload_sha}")
    if payload_sha != proposal["payload_sha256_after"]:
        failures.append("payload sha changed (must be frozen)")

    glossary = json.loads(GLOSSARY.read_bytes().decode("utf-8"))
    terms = glossary["terms"]
    print(f"glossary meta version   : {glossary['meta']['version']} "
          f"(previous {glossary['meta'].get('previous_version')})")
    print(f"glossary terms          : {len(terms)}")

    import construction.translation_loader  # noqa: F401
    import frappe.translate as frappe_translate

    frappe_translate.clear_cache()
    merged = frappe_translate.get_all_translations("ar")
    print(f"loader installed        : {construction.translation_loader.is_translation_loader_installed()}")
    print(f"rendered dict size      : {len(merged)}")

    match = divergent = absent = 0
    forbidden = 0
    wb = re.compile
    for t in terms:
        src = t["source_text"]
        appr = t.get("approved_ar") or ""
        got = merged.get(src)
        if not got:
            absent += 1
            print(f"  ABSENT/EMPTY {src!r} expected_sha16={s16(appr)}")
            failures.append(f"term {src!r} not rendered")
            continue
        if got != appr:
            divergent += 1
            print(f"  DIVERGENT    {src!r} rendered_sha16={s16(got)} expected_sha16={s16(appr)}")
            failures.append(f"term {src!r} divergent")
        else:
            match += 1
        for tok in (t.get("forbidden_ar") or []):
            if tok and re.search(r"(?<![\u0600-\u06FF])" + re.escape(tok) + r"(?![\u0600-\u06FF])", got):
                forbidden += 1
                failures.append(f"forbidden token in {src!r}")
    print(f"rendered match          : {match}/{len(terms)}")
    print(f"rendered divergent      : {divergent}")
    print(f"rendered absent/empty   : {absent}")
    print(f"forbidden violations    : {forbidden}")

    from construction import translation_service as ts
    health = ts.get_translation_health()
    print(f"health.loader_installed : {health['loader_installed']}")
    print(f"health.has_drift        : {health['has_drift']}")
    print(f"health.has_duplicates   : {health['has_duplicates']}")
    if not health["loader_installed"]:
        failures.append("loader not installed")
    if health["has_drift"]:
        failures.append("drift detected")

    tdigest, tcount = translate_digest()
    print(f"Translation rows        : {tcount}")
    print(f"Translation digest      : {tdigest}")
    print(f"apply-time digest       : {apply_rec['translation_digest_after']}")
    if tdigest != apply_rec["translation_digest_after"]:
        failures.append("Translation digest changed since apply")
    if apply_rec["translation_db_writes"] != 0:
        failures.append("apply recorded non-zero Translation writes")

    out = {
        "work_item": proposal["work_item"],
        "verified_utc": frappe.utils.now_datetime().isoformat(),
        "glossary_sha256": gloss_sha,
        "payload_sha256": payload_sha,
        "rendered_match": match,
        "rendered_divergent": divergent,
        "rendered_absent": absent,
        "forbidden_violations": forbidden,
        "health": {k: health[k] for k in ("loader_installed", "has_drift", "has_duplicates")},
        "translation_digest": tdigest,
        "translation_db_writes": 0,
        "result": "PASS" if not failures else "FAIL",
    }
    vp = PRIVATE / "post-sync-verification.json"
    vp.write_bytes(json.dumps(out, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    print(f"private verification sha: {sha256_bytes(vp.read_bytes())}")

    if failures:
        for f in failures:
            print("FAIL:", f)
        print("POST-SYNC RESULT: FAIL")
        sys.exit(1)
    print("POST-SYNC RESULT: PASS (47/47 rendered; drift false; payload frozen; 0 Translation writes)")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site=SITE, sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
