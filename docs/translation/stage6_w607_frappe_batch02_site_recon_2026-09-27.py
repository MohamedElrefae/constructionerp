"""Read-only live Translation reconciliation for proposed Stage 6 W6-7 Frappe Framework Remainder Batch 02 scope."""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
from pathlib import Path

import frappe

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SITE = "v16.localhost"
SCOPE = ROOT / "docs/translation/stage6_w607_frappe_batch02_rows_2026-09-27.csv"
OUT = ROOT / "docs/translation/stage6_w607_frappe_batch02_site_recon_2026-09-27.json"
SCOPE_SHA = "cd6536bc0cb0b9db14214e55500ebadf3a525b2a1250147b9ad9b402e1e70be3"

raw = SCOPE.read_bytes()
actual_sha = hashlib.sha256(raw).hexdigest()
assert actual_sha == SCOPE_SHA, f"Expected {SCOPE_SHA}, got {actual_sha}"

with SCOPE.open(encoding="utf-8", newline="") as handle:
    scope = list(csv.DictReader(handle))
keys = [row["source_text"] for row in scope]
assert len(keys) == 244, f"Expected 244 rows, got {len(keys)}"
assert len(set(keys)) == 244, f"Expected 244 unique keys, got {len(set(keys))}"

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
    for key, found in by_key.items():
        for row in found:
            if (row.translated_text or "").strip():
                item = {
                    "source_text": key,
                    "matched_runtime_source": row.source_text,
                    "translated_text": row.translated_text or "",
                    "context": row.context or "",
                    "ct_origin": row.ct_origin or "",
                    "ct_app": row.ct_app or "",
                    "name": row.name,
                }
                site_overrides.append(item)

    payload = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "site": SITE,
        "scope_csv": str(SCOPE.relative_to(ROOT)),
        "scope_sha256": actual_sha,
        "scope_row_count": len(keys),
        "exact_site_overrides_count": len(site_overrides),
        "missing_runtime_count": len(missing_runtime),
        "site_overrides": site_overrides,
        "missing_runtime_keys": missing_runtime,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Recon complete: {len(site_overrides)} site overrides, {len(missing_runtime)} missing runtime.")
finally:
    frappe.destroy()
