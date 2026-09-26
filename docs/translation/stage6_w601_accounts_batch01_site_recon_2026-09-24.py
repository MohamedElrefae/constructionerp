"""Read-only live Translation reconciliation for proposed W6-1 Accounts Batch 01 scope."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import frappe

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SITE = "v16.localhost"
SCOPE = ROOT / "docs/translation/stage6_w601_accounts_batch01_rows_2026-09-24.csv"
OUT = ROOT / "docs/translation/stage6_w601_accounts_batch01_site_recon_2026-09-24.json"
SCOPE_SHA = "4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd"

raw = SCOPE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == SCOPE_SHA
with SCOPE.open(encoding="utf-8", newline="") as handle:
    scope = list(csv.DictReader(handle))
keys = [row["source_text"] for row in scope]
assert len(keys) == 250 and len(set(keys)) == 250

frappe.init(SITE, sites_path="/home/mohamed/frappe-bench/sites")
frappe.connect()
try:
    frappe.set_user("Administrator")
    rows = frappe.get_all(
        "Translation",
        filters={"language": "ar", "ct_is_catalog_entry": 0},
        fields=[
            "name", "source_text", "translated_text", "context", "ct_origin",
            "ct_app", "ct_release_version", "ct_is_catalog_entry",
        ],
        limit_page_length=0,
    )
    exact_matches = [
        row for row in rows
        if row.source_text in keys
        and not (row.context or "")
    ]
    by_key: dict[str, list] = {key: [] for key in keys}
    for row in exact_matches:
        by_key[row.source_text].append(row)

    missing_runtime = [key for key, found in by_key.items() if not found or not any((r.translated_text or "").strip() for r in found)]
    site_overrides = []
    nonempty_other = []
    for key, found in by_key.items():
        for row in found:
            item = {
                "source_text": key,
                "matched_runtime_source": row.source_text,
                "translated_text": row.translated_text or "",
                "context": row.context or "",
                "ct_origin": row.ct_origin or "",
                "ct_app": row.ct_app or "",
                "ct_release_version": row.ct_release_version or "",
                "name": row.name,
            }
            if row.ct_origin == "Site Override" and (row.translated_text or "").strip():
                site_overrides.append(item)
            elif (row.translated_text or "").strip():
                nonempty_other.append(item)
    dup_keys = {key: [r.name for r in found] for key, found in by_key.items() if len(found) > 1}
    payload = {
        "scope_csv": str(SCOPE.relative_to(ROOT)),
        "scope_sha256": SCOPE_SHA,
        "site": SITE,
        "total_scope_rows": len(keys),
        "missing_runtime_keys_count": len(missing_runtime),
        "missing_runtime_keys": missing_runtime,
        "site_overrides_count": len(site_overrides),
        "site_overrides": site_overrides,
        "nonempty_non_site_count": len(nonempty_other),
        "nonempty_non_site": nonempty_other,
        "duplicate_runtime_keys": dup_keys,
        "note": "Read-only exact runtime lookup reconciliation for proposed W6-1 Accounts Batch 01 scope on the test site.",
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Recon complete: total={len(keys)}, site_overrides={len(site_overrides)}, nonempty_other={len(nonempty_other)}, missing={len(missing_runtime)}")
    print(f"Output: {OUT}")
finally:
    frappe.destroy()
