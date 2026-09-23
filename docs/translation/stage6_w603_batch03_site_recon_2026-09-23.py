"""Read-only live-site reconciliation for the owner-approved W6-3 batch 03."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import frappe

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SITE = "v16.localhost"
SCOPE = ROOT / "docs/translation/stage6_w603_batch03_rows_2026-09-23.csv"
OUT = ROOT / "docs/translation/stage6_w603_batch03_site_recon_2026-09-24.json"
SCOPE_SHA = "a5f0e9f604ea52d89072d2c744864fdcbc733bc8307fd427a5c2658f4855dbc9"


def execute():
    raw = SCOPE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SCOPE_SHA
    with SCOPE.open(encoding="utf-8", newline="") as fh:
        scope = list(csv.DictReader(fh))
    keys = [row["source_text"] for row in scope]
    assert len(keys) == 234 and len(set(keys)) == 234

    rows = frappe.get_all(
        "Translation",
        filters={"language": "ar"},
        fields=["source_text", "translated_text", "ct_origin", "ct_is_catalog_entry", "ct_app"],
        limit_page_length=0,
    )
    scope_keys = set(keys)
    matches = {key: [row for row in rows if row.source_text == key] for key in keys}
    missing = sorted(key for key, found in matches.items() if not found)
    site_overrides = {
        key: next(row for row in found if (row.ct_origin or "").lower() == "site override")
        for key, found in matches.items()
        if any((row.ct_origin or "").lower() == "site override" for row in found)
    }
    preserved = [
        {"source_text": key, "translated_text": row.translated_text or ""}
        for key, row in sorted(site_overrides.items())
    ]
    result = {
        "batch": "w603-03",
        "site": SITE,
        "scope_rows": len(keys),
        "scope_sha256": SCOPE_SHA,
        "runtime_rows_scanned": len(rows),
        "exact_match_rows": sum(len(found) for found in matches.values()),
        "scope_keys_with_exact_match": len(keys) - len(missing),
        "missing_keys": missing,
        "site_override_key_count": len(site_overrides),
        "site_overrides": preserved,
        "nonempty_non_site_override_keys": sorted(
            key for key, found in matches.items()
            if key not in site_overrides and any((row.translated_text or "").strip() for row in found)
        ),
        "catalog_key_count": sum(
            any(bool(row.ct_is_catalog_entry) for row in found)
            for found in matches.values()
        ),
        "note": "Read-only exact-key snapshot from the authorized test site; Site Overrides are preserve-only under plan §12.",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "scope_rows", "scope_keys_with_exact_match", "missing_keys",
        "site_override_key_count", "catalog_key_count", "runtime_rows_scanned",
    )}, ensure_ascii=False))
