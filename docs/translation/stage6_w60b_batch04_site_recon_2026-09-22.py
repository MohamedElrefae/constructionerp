#!/usr/bin/env python3
"""W6-0b batch-4 site recon: list ar Translation rows for scope keys with ct_origin."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import frappe

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w60b_batch04_rows_2026-09-22.csv"
OUT = ROOT / "docs/translation/stage6_w60b_batch04_site_recon_2026-09-22.json"

frappe.init("v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

with SCOPE.open(encoding="utf-8") as fh:
    keys = [r["source_text"] for r in csv.DictReader(fh)]
assert len(keys) == 271, len(keys)

# Case-insensitive match on source_text for ar language (read-only via ORM)
lower_keys = {k.lower() for k in keys}
rows = frappe.get_all(
    "Translation",
    filters={"language": "ar"},
    fields=["source_text", "translated_text", "ct_origin", "owner"],
    limit_page_length=0,
)

matches = []
for r in rows:
    if (r.source_text or "").lower() not in lower_keys:
        continue
    matches.append(
        {
            "source_text": r.source_text,
            "translated_text": r.translated_text,
            "ct_origin": r.ct_origin or "",
            "owner": r.owner or "",
        }
    )

# Also check enabled languages
langs = frappe.db.sql(
    "SELECT name, enabled FROM `tabLanguage` WHERE name IN ('ar','en')",
    as_dict=True,
)

result = {
    "site": "v16.localhost",
    "scope_rows": len(keys),
    "languages": [{"name": x.name, "enabled": x.enabled} for x in langs],
    "match_count": len(matches),
    "site_overrides": [m for m in matches if (m["ct_origin"] or "").lower() == "site override"],
    "other_matches": [m for m in matches if (m["ct_origin"] or "").lower() != "site override"],
    "matches": matches,
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: result[k] for k in ("scope_rows", "match_count", "languages")}, ensure_ascii=False))
print("SITE_OVERRIDES", len(result["site_overrides"]))
for m in result["site_overrides"]:
    print("  PRESERVE", repr(m["source_text"]), "->", m["translated_text"], "|", m["ct_origin"])
print("OTHER_MATCHES", len(result["other_matches"]))
for m in result["other_matches"]:
    print("  OTHER", repr(m["source_text"]), "->", m["translated_text"], "|", m["ct_origin"], "|", m["owner"])
frappe.destroy()
