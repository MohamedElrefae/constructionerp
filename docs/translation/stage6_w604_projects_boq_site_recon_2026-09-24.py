"""Read-only live Translation reconciliation for approved W6-4 scope."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import frappe

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SITE = "v16.localhost"
SCOPE = ROOT / "docs/translation/stage6_w604_projects_boq_rows_2026-09-24.csv"
OUT = ROOT / "docs/translation/stage6_w604_projects_boq_site_recon_2026-09-24.json"
SCOPE_SHA = "93fbf16b14940ce2d477f346c1777865bf008b22df943625e7de84f27e8f4abe"

raw = SCOPE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == SCOPE_SHA
with SCOPE.open(encoding="utf-8", newline="") as handle:
    scope = list(csv.DictReader(handle))
keys = [row["source_text"] for row in scope]
assert len(keys) == 147 and len(set(keys)) == 147
normalized_keys = {key.strip() for key in keys}

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
    matches = [
        row for row in rows
        if (row.source_text or "").strip() in normalized_keys
        and not (row.context or "")
    ]
    by_key: dict[str, list] = {key: [] for key in keys}
    for row in matches:
        norm = (row.source_text or "").strip()
        for key in keys:
            if key.strip() == norm:
                by_key[key].append(row)
    missing_runtime = [key for key, found in by_key.items() if not found]
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
            if (row.ct_origin or "").lower() == "site override":
                site_overrides.append(item)
            elif (row.translated_text or "").strip():
                nonempty_other.append(item)

    result = {
        "batch": "w604-projects-boq",
        "site": SITE,
        "scope_sha256": SCOPE_SHA,
        "scope_rows": len(keys),
        "runtime_rows_scanned": len(rows),
        "matched_runtime_rows": len(matches),
        "keys_with_runtime_match": sum(bool(found) for found in by_key.values()),
        "missing_runtime_keys": missing_runtime,
        "site_override_row_count": len(site_overrides),
        "site_overrides": site_overrides,
        "nonempty_non_site_override_row_count": len(nonempty_other),
        "nonempty_non_site_overrides": nonempty_other,
        "duplicate_runtime_keys": {
            key: [row.name for row in found]
            for key, found in by_key.items() if len(found) > 1
        },
        "note": (
            "Read-only exact normalized runtime lookup reconciliation for the approved "
            "scope on the test site. Site Override rows are preservation-only; this "
            "script performs no writes and does not commit."
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "site": SITE,
        "scope_rows": result["scope_rows"],
        "runtime_rows_scanned": result["runtime_rows_scanned"],
        "matched_runtime_rows": result["matched_runtime_rows"],
        "keys_with_runtime_match": result["keys_with_runtime_match"],
        "missing_runtime_keys": len(missing_runtime),
        "site_override_rows": len(site_overrides),
        "nonempty_non_site_override_rows": len(nonempty_other),
        "duplicate_runtime_keys": len(result["duplicate_runtime_keys"]),
    }, ensure_ascii=False))
finally:
    frappe.destroy()
