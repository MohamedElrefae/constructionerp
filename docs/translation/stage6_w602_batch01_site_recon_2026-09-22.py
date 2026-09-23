#!/usr/bin/env python3
"""W6-2 batch-1 site recon: list ar Translation rows for scope keys with ct_origin."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import frappe

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w602_batch01_rows_2026-09-22.csv"
OUT = ROOT / "docs/translation/stage6_w602_batch01_site_recon_2026-09-22.json"

frappe.init("v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

with SCOPE.open(encoding="utf-8") as fh:
    keys = [r["source_text"] for r in csv.DictReader(fh)]
assert len(keys) == 270, len(keys)
assert len(set(keys)) == 270

lower_keys = {k.lower() for k in keys}
rows = frappe.get_all(
    "Translation",
    filters={"language": "ar"},
    fields=["source_text", "translated_text", "ct_origin", "owner", "ct_is_catalog_entry"],
    limit_page_length=0,
)

matches = []
for r in rows:
    if (r.source_text or "").lower() not in lower_keys:
        continue
    matches.append(
        {
            "source_text": r.source_text,
            "translated_text": r.translated_text or "",
            "ct_origin": r.ct_origin or "",
            "ct_is_catalog_entry": int(r.ct_is_catalog_entry or 0),
            "owner": r.owner or "",
        }
    )

exact_keys = set(keys)
exact_matches = [m for m in matches if m["source_text"] in exact_keys]
missing = sorted(set(keys) - {m["source_text"] for m in exact_matches})
site_overrides = [m for m in matches if (m["ct_origin"] or "").lower() == "site override"]
nonempty = [m for m in matches if (m.get("translated_text") or "").strip()]

result = {
    "batch": "w602-01",
    "site": "v16.localhost",
    "generated": "2026-09-22",
    "scope_rows": len(keys),
    "runtime_rows_scanned": len(rows),
    "match_count": len(matches),
    "exact_case_matches": len(exact_matches),
    "missing_count": len(missing),
    "missing_keys": missing,
    "matched_nonempty_values": len(nonempty),
    "site_override_origin_rows": len(site_overrides),
    "site_overrides": site_overrides,
    "preserved": [
        {"source_text": m["source_text"], "translated_text": m["translated_text"]}
        for m in site_overrides
    ],
    "nonempty_matches": nonempty,
    "matches": matches,
    "note": (
        "Authoritative dump of ar Translation rows. Site-override preserves "
        "are rows with ct_origin='Site Override' among scope keys."
    ),
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: result[k] for k in (
    "scope_rows", "runtime_rows_scanned", "match_count", "exact_case_matches",
    "missing_count", "matched_nonempty_values", "site_override_origin_rows")}, ensure_ascii=False))
print("SITE_OVERRIDES", len(site_overrides))
for m in site_overrides:
    print("  PRESERVE", repr(m["source_text"]), "->", (m["translated_text"] or "")[:60], "|", m["ct_origin"])
print("NONEMPTY other:")
for m in nonempty:
    if (m["ct_origin"] or "").lower() != "site override":
        print("  VAL", repr(m["source_text"]), "->", (m["translated_text"] or "")[:60], "|", repr(m["ct_origin"]), "| cat", m["ct_is_catalog_entry"])
frappe.destroy()
