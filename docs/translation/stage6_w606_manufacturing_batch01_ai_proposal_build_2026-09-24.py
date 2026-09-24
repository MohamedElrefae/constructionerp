"""Build proposal CSV for W6-6 Manufacturing Batch 01."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from stage6_w606_manufacturing_batch01_dict import MANUFACTURING_BATCH01_TRANSLATIONS

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w606_manufacturing_batch01_rows_2026-09-24.csv"
RECON = ROOT / "docs/translation/stage6_w606_manufacturing_batch01_site_recon_2026-09-24.json"
OUT = ROOT / "docs/translation/stage6_w606_manufacturing_batch01_proposal_2026-09-24.csv"
SCOPE_SHA = "0d5098f61e2f97d26fa40e4e8b5d3b90ab1ec22e9dafd543564cb07ec8d39286"

raw = SCOPE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == SCOPE_SHA
with SCOPE.open(encoding="utf-8", newline="") as handle:
    scope_rows = list(csv.DictReader(handle))
assert len(scope_rows) == 250

recon = json.loads(RECON.read_text(encoding="utf-8"))
site_overrides_map = {row["source_text"]: row["translated_text"] for row in recon["site_overrides"]}
assert len(site_overrides_map) == 167

missing_keys = set(recon["missing_runtime_keys"])
assert len(missing_keys) == 83
assert set(MANUFACTURING_BATCH01_TRANSLATIONS.keys()) == missing_keys

proposal_rows = []
for row in scope_rows:
    src = row["source_text"]
    loc = row.get("locations", "")
    if src in site_overrides_map:
        ar = site_overrides_map[src]
        disp = "preserved-site-override"
        rat = "Preserve the exact live v16.localhost Site Override; do not import or replace."
    else:
        ar = MANUFACTURING_BATCH01_TRANSLATIONS[src]
        disp = "PROPOSED-payload"
        rat = "AI draft; requires independent A1/A2/A3 quorum before release."

    # Verification: check placeholders
    src_ph = sorted(re.findall(r"\{[0-9]*\}", src))
    ar_ph = sorted(re.findall(r"\{[0-9]*\}", ar))
    assert src_ph == ar_ph, f"Placeholder mismatch for {src!r}: {src_ph} vs {ar_ph}"

    proposal_rows.append({
        "source_text": src,
        "proposed_ar": ar,
        "proposed_disposition": disp,
        "disposition_rationale": rat,
        "decision_ref": "stage6-W6-6 Manufacturing Batch 01 owner-approved 2026-09-24",
        "locations": loc,
    })

assert len(proposal_rows) == 250

with OUT.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=[
        "source_text", "proposed_ar", "proposed_disposition",
        "disposition_rationale", "decision_ref", "locations"
    ])
    writer.writeheader()
    writer.writerows(proposal_rows)

out_bytes = OUT.read_bytes()
out_sha = hashlib.sha256(out_bytes).hexdigest()
print(f"Proposal written: {len(proposal_rows)} rows, SHA-256: {out_sha}")
