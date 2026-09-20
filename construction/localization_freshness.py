"""Authenticated runtime-freshness evidence collector (Stage 2).

Runs on an authorized site via bench console (needs frappe runtime, not CI).
Emits JSON binding declared source inputs to live runtime digests.

Usage:
  bench --site <site> console <<'PY'
  import construction.localization_freshness as lf
  print(lf.collect())
  PY
"""

import hashlib
import json

import frappe


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


CRITICAL_KEYS = [
    "Desktop", "Workspaces", "Edit Sidebar", "Toggle Theme", "Toggle Full Width",
    "Typography Settings",
]


def collect():
    import datetime

    app_path = frappe.get_app_path("construction")
    po_sha = _sha_file(f"{app_path}/locale/ar.po")
    csv_path = f"{app_path}/data/translations/approved_ar_overrides.csv"
    csv_sha = _sha_file(csv_path)
    rows = frappe.get_all(
        "Translation",
        filters={"language": "ar", "ct_origin": "Packaged Release"},
        fields=["source_text", "translated_text", "ct_release_version"],
        order_by="source_text, translated_text",
        limit_page_length=0,
    )
    triples = [
        (r.get("source_text"), r.get("translated_text"), r.get("ct_release_version"))
        for r in rows
    ]
    triples.sort(key=lambda t: (t[0] or "", t[1] or ""))
    runtime_digest = hashlib.sha256(repr(triples).encode()).hexdigest()
    from construction.translation_service import (
        get_effective_translation, get_translation_health,
    )

    health = get_translation_health()
    critical = {k: get_effective_translation("ar", k) for k in CRITICAL_KEYS}
    db_now = str(frappe.db.sql("SELECT NOW()")[0][0])
    collected = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return json.dumps({
        "collected_utc": collected,
        "site": frappe.local.site,
        "inputs": {"construction_po_sha": po_sha, "payload_csv_sha": csv_sha},
        "packaged_rows": len(rows),
        "runtime_digest": runtime_digest,
        "critical_keys": critical,
        "critical_pass": all(bool(v) for v in critical.values()),
        "health": health,
        "db_now_at_collection": db_now,
        "db_now_at_collection": db_now,
        "audit_timestamps": {k: health.get(k) for k in
                             ("last_catalog_sync_at", "last_release_import_at",
                              "last_drift_checked_at")},
    }, ensure_ascii=False, sort_keys=True)
