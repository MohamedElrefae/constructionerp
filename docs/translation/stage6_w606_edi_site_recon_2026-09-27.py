"""Read-only live Translation reconciliation for proposed Stage 6 W6-6 EDI remainder scope."""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
from pathlib import Path

import frappe

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SITE = "v16.localhost"
SCOPE = ROOT / "docs/translation/stage6_w606_edi_rows_2026-09-27.csv"
OUT = ROOT / "docs/translation/stage6_w606_edi_site_recon_2026-09-27.json"
SCOPE_SHA = "2b0cc9b46546aa36310f81738c72ff0d2b50ca35666110033976c424c149cef1"

raw = SCOPE.read_bytes()
actual_sha = hashlib.sha256(raw).hexdigest()
assert actual_sha == SCOPE_SHA, f"Expected {SCOPE_SHA}, got {actual_sha}"

with SCOPE.open(encoding="utf-8", newline="") as handle:
    scope = list(csv.DictReader(handle))
keys = [row["source_text"] for row in scope]
assert len(keys) == 26, f"Expected 26 rows, got {len(keys)}"
assert len(set(keys)) == 26, f"Expected 26 unique keys, got {len(set(keys))}"

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
                    "ct_release_version": row.ct_release_version or "",
                    "docname": row.name,
                }
                site_overrides.append(item)

    payload = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "site": SITE,
        "scope_file": str(SCOPE.relative_to(ROOT)),
        "scope_sha256": SCOPE_SHA,
        "scope_rows": len(keys),
        "site_overrides_count": len(site_overrides),
        "missing_runtime_count": len(missing_runtime),
        "site_overrides": site_overrides,
        "missing_runtime": missing_runtime,
    }

    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Reconciliation written to {OUT}")
    print(f"Site Overrides: {len(site_overrides)}, Missing runtime (candidates): {len(missing_runtime)}")
finally:
    frappe.destroy()
