"""Tier 5H apply — import the approved Company proposal via standard doc.save().

Fail-closed gates before any write:
  1. proposal.json sha256 == owner-approved v2 sha;
  2. private dry-run.json bound to the same proposal sha, writes_performed == 0;
  3. byte-scan of the value; the row pre-validated (exists, identity/abbr/currency/
     country/shape match, Arabic empty-or-equal) BEFORE the write;
  4. pre-state: site Arabic total 0, total 21, excluded set still 20;
  5. queue redis (port 11000) reachable — F-5H-2 (Company.save() enqueues; without the
     queue a save raises ConnectionError mid-flight, probe P1).

Apply path: 1 plain doc.save() through the registered validate hooks (bidi gate +
server-derived _norm). After the save, the queues:* payloads on 11000 are dumped so
apply.log records the enqueued job name(s) — F-5H-2 mechanism, recorded not inferred
(review NOTE).

On any exception: full transaction rollback, APPLY RESULT: FAIL, exit 1.
"""

import hashlib
import json
import sys
import unicodedata

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/company-phase1-population"
APPROVED_SHA = "b5fcc02a6854ebb27b71082b71c1b3f9d4ac43f737b013809697c2a23e79478a"
AR_FIELD, NORM_FIELD, LABEL_FIELD = "company_name_ar", "company_name_ar_norm", "company_name"
TOTAL_EXPECTED = 21
EXCLUDED_EXPECTED = 20
QUEUE_HOST, QUEUE_PORT = "127.0.0.1", 11000


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


def queue_snapshot():
    """Lengths + payloads of every queues:* list on the queue redis."""
    import redis as _redis
    r = _redis.StrictRedis(host=QUEUE_HOST, port=QUEUE_PORT, decode_responses=True)
    snap = {}
    for key in sorted(r.keys("queues:*")):
        snap[key] = r.lrange(key, 0, -1)
    return snap


def queue_delta(before, after):
    out = {}
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key, []), after.get(key, [])
        if a != b:
            out[key] = {"before": len(b), "after": len(a), "added": a[len(b):]}
    return out


def main():
    # Gate 5 first — no point proceeding without the queue (F-5H-2).
    try:
        q_before = queue_snapshot()
        print(f"QUEUE_GATE reachable at {QUEUE_HOST}:{QUEUE_PORT} snapshot={q_before}")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: queue redis unreachable — {type(exc).__name__}: {exc}")
        sys.exit(1)

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
        print("FAIL: dry-run not bound to the approved proposal sha")
        sys.exit(1)
    if dry.get("writes_performed") != 0:
        print("FAIL: dry-run did not record zero writes")
        sys.exit(1)
    dry_by = {r["name"]: r for r in dry.get("rows", [])}
    if len(dry_by) != 1:
        print(f"FAIL: dry-run row set has {len(dry_by)} rows, expected 1")
        sys.exit(1)

    from construction.services.bilingual_service import normalize_arabic

    # Gate 3: pre-validate the row before the write.
    plan = []
    for row in proposal["rows"]:
        name, value = row["name"], row["arabic"]
        problems = byte_scan(value)
        if problems:
            print(f"FAIL pre-validate {name}: {problems}")
            sys.exit(1)
        snap = frappe.db.get_value(
            "Company", name,
            [LABEL_FIELD, "abbr", "default_currency", "country", "parent_company",
             "is_group", AR_FIELD], as_dict=True)
        if not snap:
            print(f"FAIL pre-validate {name}: absent")
            sys.exit(1)
        if snap[LABEL_FIELD] != row["english_label"]:
            print(f"FAIL pre-validate {name}: label drift")
            sys.exit(1)
        if snap["abbr"] != "E" or snap["default_currency"] != "EGP" or snap["country"] != "Egypt":
            print(f"FAIL pre-validate {name}: frozen attribute drift")
            sys.exit(1)
        if snap["parent_company"] or snap["is_group"]:
            print(f"FAIL pre-validate {name}: shape drift")
            sys.exit(1)
        if snap[AR_FIELD] and snap[AR_FIELD] != value:
            print(f"FAIL pre-validate {name}: conflicting existing value")
            sys.exit(1)
        plan.append({"name": name, "value": value, "already": bool(snap[AR_FIELD])})
    site_ar = frappe.db.count("Company", {AR_FIELD: ("!=", "")})
    total = frappe.db.count("Company")
    excluded = total - len(plan)
    if site_ar != 0 or total != TOTAL_EXPECTED or excluded != EXCLUDED_EXPECTED:
        print(f"FAIL pre-state: arabic={site_ar} total={total} excluded={excluded}")
        sys.exit(1)
    print(f"PREVALIDATE_OK rows={len(plan)} plain={len(plan)} site_arabic=0 "
          f"total={total} excluded={excluded}")

    # Apply through the standard document lifecycle.
    results = []
    try:
        for item in plan:
            if item["already"]:
                print(f"SKIP Company {item['name']!r} already applied")
                results.append({"name": item["name"], "action": "skip-already-applied"})
                continue
            d = frappe.get_doc("Company", item["name"])
            label_before = d.get(LABEL_FIELD)
            abbr_before, cur_before, country_before = d.get("abbr"), d.get("default_currency"), d.get("country")
            parent_before, grp_before = d.get("parent_company"), d.get("is_group")
            coa_before = d.get("chart_of_accounts")
            before_fields = dict(d.as_dict())
            d.set(AR_FIELD, item["value"])
            d.save()
            if d.get(LABEL_FIELD) != label_before:
                raise RuntimeError(f"{item['name']}: company_name changed")
            if (d.get("abbr"), d.get("default_currency"), d.get("country")) != (abbr_before, cur_before, country_before):
                raise RuntimeError(f"{item['name']}: abbr/currency/country changed")
            if d.get("parent_company") != parent_before or d.get("is_group") != grp_before:
                raise RuntimeError(f"{item['name']}: shape changed")
            if d.get("chart_of_accounts") != coa_before:
                raise RuntimeError(f"{item['name']}: chart_of_accounts changed")
            if d.get(AR_FIELD) != item["value"]:
                raise RuntimeError(f"{item['name']}: value not stored")
            expected = normalize_arabic(item["value"])
            if d.get(NORM_FIELD) != expected:
                raise RuntimeError(f"{item['name']}: norm not server-derived")
            after_fields = dict(d.as_dict())
            allowed = {AR_FIELD, NORM_FIELD}
            changed = {k for k in before_fields
                       if before_fields.get(k) != after_fields.get(k)
                       and k not in ("modified", "modified_by", "idx")}
            unexpected = changed - allowed
            if unexpected:
                raise RuntimeError(f"{item['name']}: unexpected field changes {sorted(unexpected)}")
            print(f"WRITE Company {item['name']!r} value={sha16(item['value'])} "
                  f"norm={sha16(expected)} identity=unchanged frozen=unchanged "
                  f"fields_changed={sorted(changed)} PLAIN")
            results.append({"name": item["name"], "action": "written",
                            "value": item["value"], "norm": expected, "path": "PLAIN"})
        frappe.db.commit()
    except Exception as exc:  # noqa: BLE001 - fail-closed rollback
        frappe.db.rollback()
        print(f"FAIL during apply, transaction rolled back: {type(exc).__name__}: {exc}")
        sys.exit(1)

    # F-5H-2 mechanism record: what the save enqueued.
    q_after = queue_snapshot()
    q_added = queue_delta(q_before, q_after)
    print(f"QUEUE_ENQUEUED {json.dumps(q_added, ensure_ascii=False)}")
    if not q_added:
        print("QUEUE_NOTE no new queue entries observed (job may have run inline or been "
              "consumed); P1/P2 remain the empirical evidence for F-5H-2")

    private = {
        "proposal_sha256": APPROVED_SHA,
        "dry_run_sha256": hashlib.sha256(dry_raw).hexdigest(),
        "apply_utc": frappe.utils.now_datetime().isoformat(),
        "written": sum(1 for r in results if r["action"] == "written"),
        "skipped": sum(1 for r in results if r["action"] != "written"),
        "queue_enqueued": q_added,
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
    if frappe.db:
        frappe.db.rollback()
