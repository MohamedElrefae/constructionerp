#!/usr/bin/env python3
"""Read-only live-site reconciliation for W6-3 batch 02."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import frappe

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SITE = "v16.localhost"
SCOPE = ROOT / "docs/translation/stage6_w603_batch02_rows_2026-09-23.csv"
OUT = ROOT / "docs/translation/stage6_w603_batch02_site_recon_2026-09-23.json"
SCOPE_SHA = "701ad13e6b4cc530ebd7dbd95705979b70055c46f39da37d4532a26ba60439ef"

raw = SCOPE.read_bytes()
import hashlib

assert hashlib.sha256(raw).hexdigest() == SCOPE_SHA
with SCOPE.open(encoding="utf-8", newline="") as fh:
    keys = [row["source_text"] for row in csv.DictReader(fh)]
assert len(keys) == 250 and len(set(keys)) == 250

frappe.init(SITE, sites_path="/home/mohamed/frappe-bench/sites")
frappe.connect()
try:
    frappe.set_user("Administrator")
    rows = frappe.get_all(
        "Translation",
        filters={"language": "ar"},
        fields=["source_text", "translated_text", "ct_origin", "ct_is_catalog_entry"],
        limit_page_length=0,
    )
    exact = [row for row in rows if row.source_text in set(keys)]
    by_key = {key: [row for row in exact if row.source_text == key] for key in keys}
    assert all(by_key.values()), "scope key missing from live Translation inventory"
    site_overrides = {
        key: next(
            row for row in matches
            if (row.ct_origin or "").lower() == "site override"
        )
        for key, matches in by_key.items()
        if any((row.ct_origin or "").lower() == "site override" for row in matches)
    }
    preserved = [
        {"source_text": key, "translated_text": row.translated_text or ""}
        for key, row in sorted(site_overrides.items())
    ]
    result = {
        "batch": "w603-02",
        "site": SITE,
        "generated": "2026-09-23",
        "scope_rows": len(keys),
        "scope_sha256": SCOPE_SHA,
        "runtime_rows_scanned": len(rows),
        "exact_match_rows": len(exact),
        "scope_keys_with_exact_match": len(by_key),
        "missing_keys": [],
        "site_override_key_count": len(site_overrides),
        "site_overrides": preserved,
        "nonempty_non_site_override_keys": sorted(
            key for key, matches in by_key.items()
            if key not in site_overrides
            and any((row.translated_text or "").strip() for row in matches)
        ),
        "catalog_key_count": sum(
            any(bool(row.ct_is_catalog_entry) for row in matches)
            for matches in by_key.values()
        ),
        "note": (
            "Read-only exact-key dump of Arabic Translation rows on the test site. "
            "Site Override values are preserved under plan §12."
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "scope_rows": result["scope_rows"],
        "scope_keys_with_exact_match": result["scope_keys_with_exact_match"],
        "site_override_key_count": result["site_override_key_count"],
        "nonempty_non_site_override_keys": len(result["nonempty_non_site_override_keys"]),
        "catalog_key_count": result["catalog_key_count"],
        "runtime_rows_scanned": result["runtime_rows_scanned"],
    }, ensure_ascii=False))
finally:
    frappe.destroy()
