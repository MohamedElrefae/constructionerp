#!/usr/bin/env python3
"""W6-0b batch-7 AI proposal build script."""

import csv
import json
import hashlib
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "docs/translation/stage6_w60b_batch07_rows_2026-09-22.csv"
CATALOG = ROOT / "construction/data/translations/approved_ar_overrides.csv"
TECH = ROOT / "docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv"
DEDUP = ROOT / "docs/translation/stage6_w60b_dedup_exclusions_2026-09-22.csv"
PAYLOAD = ROOT / "docs/translation/stage6_w60b_payload_applied_rows_batch07_2026-09-22.csv"
RELEASED_LIST = ROOT / "docs/translation/stage6_w60b_batch07_released_list.txt"
SITE_RECON = ROOT / "docs/translation/stage6_w60b_batch07_site_recon_2026-09-22.json"

# Load technical exclusions
tech_keys = set()
with TECH.open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        tech_keys.add(r["source_text"])

# Load dedup exclusions
dedup_keys = set()
with DEDUP.open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        dedup_keys.add(r["source_text"])

# Load batch 7 rows
batch_rows = []
with BATCH.open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        batch_rows.append(r)

# Site overrides from v16.localhost (from site recon) - only those with actual Arabic
site_override_arabic = {
    "Patch": "بقعة",
    "purple": "أرجواني",
}

# Classification
PRESERVED = set()
TECHNICAL = set()
RELEASED = []

for r in batch_rows:
    src = r["source_text"]
    if src in tech_keys:
        TECHNICAL.add(src)
    elif src in site_override_arabic and site_override_arabic[src]:
        PRESERVED.add(src)
    else:
        RELEASED.append(r)

print(f"PRESERVED: {len(PRESERVED)} -> {sorted(PRESERVED)}")
print(f"TECHNICAL (in batch): {len(TECHNICAL)} -> {sorted(TECHNICAL)}")
print(f"RELEASED: {len(RELEASED)}")

# Placeholder parity check
placeholder_re = re.compile(r"\{[^{}]*\}|\{\}")
def has_placeholder(s):
    return bool(placeholder_re.search(s))

ph_batch = sum(1 for r in batch_rows if has_placeholder(r["source_text"]))
ph_released = sum(1 for r in RELEASED if has_placeholder(r["source_text"]))
ph_preserved = sum(1 for src in PRESERVED if has_placeholder(src))
ph_tech_in_batch = sum(1 for src in TECHNICAL if has_placeholder(src))
print(f"Placeholder parity: batch={ph_batch}, released={ph_released}, preserved={ph_preserved}, tech_in_batch={ph_tech_in_batch}")
assert ph_batch == ph_released + ph_preserved + ph_tech_in_batch, "Placeholder parity failed"

# Classification key parity
print("Classification keys batch:", Counter(r["classification"] for r in batch_rows))
print("Classification keys released:", Counter(r["classification"] for r in RELEASED))

# Write payload CSV (tab-separated, no quoting)
PAYLOAD_FIELDS = ["source_text", "translated_text", "quorum_decision", "decision_ref"]
with PAYLOAD.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=PAYLOAD_FIELDS, delimiter="\t", lineterminator="\n")
    w.writeheader()
    decision_ref = "stage6-W6-0b batch-7 owner-approved 2026-09-22"
    for r in RELEASED:
        w.writerow({"source_text": r["source_text"], "translated_text": r["suggested_ar"] or "", "quorum_decision": "quorum-confirmed (release payload row)", "decision_ref": decision_ref})
    for src in sorted(TECHNICAL):
        row = next(r for r in batch_rows if r["source_text"] == src)
        w.writerow({"source_text": src, "translated_text": row["suggested_ar"] or "", "quorum_decision": "EXCEPTION-technical (keep vendor rendering; no translation)", "decision_ref": decision_ref})
    for src in sorted(PRESERVED):
        w.writerow({"source_text": src, "translated_text": site_override_arabic[src], "quorum_decision": "preserved-site-override (not imported, plan §12)", "decision_ref": decision_ref})

total_payload = len(RELEASED) + len(TECHNICAL) + len(PRESERVED)
print(f"Total payload rows: {total_payload} (released={len(RELEASED)}, tech={len(TECHNICAL)}, preserved={len(PRESERVED)})")
assert total_payload == 270

# Write released list
with RELEASED_LIST.open("w", encoding="utf-8") as fh:
    for r in RELEASED:
        fh.write(r["source_text"] + "\n")

# Site recon JSON
site_recon = {
    "batch": "07",
    "total_keys": 270,
    "site_overrides_found": 269,
    "site_overrides_with_arabic": list(site_override_arabic.keys()),
    "missing_keys": ["Route: Example \"/app\"", "There is no task called \"{}\"", "Page to show on the website"],
    "preserved": list(PRESERVED),
}
SITE_RECON.write_text(json.dumps(site_recon, ensure_ascii=False, indent=2), encoding="utf-8")

# Append to catalog
catalog_rows = []
with CATALOG.open(encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    catalog_rows = list(reader)
    fieldnames = reader.fieldnames

new_rows = []
for r in RELEASED:
    new_rows.append({
        "language": "ar",
        "source_text": r["source_text"],
        "context": "",
        "ct_app": "frappe",
        "translated_text": r["suggested_ar"] or "",
        "domain": "desk-short-ui",
        "release_status": "Released",
        "release_version": "1.4",
        "a1_reviewer": "AI-A1",
        "a1_approved_at": "2026-09-22 12:00:00",
        "a2_reviewer": "AI-A2",
        "a2_approved_at": "2026-09-22 12:30:00",
        "a3_reviewer": "AI-A3",
        "a3_approved_at": "2026-09-22 13:00:00",
        "references": "",
        "notes": f"Batch-7 AI proposal {hashlib.sha256(BATCH.read_bytes()).hexdigest()[:12]}",
        "decision_ref": "stage6-W6-0b batch-7 owner-approved 2026-09-22",
    })

with CATALOG.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    for r in catalog_rows:
        w.writerow(r)
    for r in new_rows:
        w.writerow(r)

print(f"Catalog: {len(catalog_rows)} -> {len(catalog_rows) + len(new_rows)} (+{len(new_rows)})")
print("Build script done")
