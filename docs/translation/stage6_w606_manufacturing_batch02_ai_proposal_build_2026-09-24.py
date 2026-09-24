"""Build proposal CSV for W6-6 Manufacturing Batch 02."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from stage6_w606_manufacturing_batch02_dict import TRANSLATIONS, TECHNICAL_EXCEPTIONS

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w606_manufacturing_batch02_rows_2026-09-24.csv"
RECON = ROOT / "docs/translation/stage6_w606_manufacturing_batch02_site_recon_2026-09-24.json"
OUT = ROOT / "docs/translation/stage6_w606_manufacturing_batch02_proposal_2026-09-24.csv"
SCOPE_SHA = "195c789945cf2b069a1620e855b22ad38aa9cb0adf03b9b2342166c47b6e88ff"

raw = SCOPE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == SCOPE_SHA
with SCOPE.open(encoding="utf-8", newline="") as handle:
    scope_rows = list(csv.DictReader(handle))
assert len(scope_rows) == 202

recon = json.loads(RECON.read_text(encoding="utf-8"))
site_overrides_map = {row["source_text"]: row["translated_text"] for row in recon["site_overrides"]}
assert len(site_overrides_map) == 119

missing_keys = set(recon["missing_runtime_keys"])
assert len(missing_keys) == 83
assert (set(TRANSLATIONS.keys()) | set(TECHNICAL_EXCEPTIONS.keys())) == missing_keys

proposal_rows = []
for row in scope_rows:
    src = row["source_text"]
    loc = row.get("locations", "")
    if src in site_overrides_map:
        ar = site_overrides_map[src]
        disp = "preserved-site-override"
        if src != src.strip():
            rat = (
                "PRESERVED-edge-whitespace exception: retain this exact source key and existing "
                "live v16.localhost Site Override verbatim; do not trim, normalize, import, or replace."
            )
        else:
            rat = "Preserve the exact live v16.localhost Site Override; do not import or replace."
    elif src in TECHNICAL_EXCEPTIONS:
        ar = ""
        disp = "EXCEPTION-technical"
        rat = TECHNICAL_EXCEPTIONS[src]
    else:
        ar = TRANSLATIONS[src]
        disp = "PROPOSED-payload"
        rat = "AI draft; requires independent A1/A2/A3 quorum before release."

    # Verification: check placeholders
    if disp != "EXCEPTION-technical":
        src_ph = sorted(re.findall(r"\{[0-9]*\}", src))
        ar_ph = sorted(re.findall(r"\{[0-9]*\}", ar))
        assert src_ph == ar_ph, f"Placeholder mismatch for {src!r}: {src_ph} vs {ar_ph}"

    proposal_rows.append({
        "source_text": src,
        "proposed_ar": ar,
        "proposed_disposition": disp,
        "disposition_rationale": rat,
        "decision_ref": "stage6-W6-6 Manufacturing Batch 02 pending-owner-approval 2026-09-24",
        "locations": loc,
    })

assert len(proposal_rows) == 202

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
