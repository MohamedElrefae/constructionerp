"""Build proposal CSV for W6-6 CRM, Support & Maintenance."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from stage6_w606_crm_support_maintenance_dict import DEFERRED_SOURCE_DEFECTS, TECHNICAL_EXCEPTIONS, TRANSLATIONS

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w606_crm_support_maintenance_rows_2026-09-24.csv"
RECON = ROOT / "docs/translation/stage6_w606_crm_support_maintenance_site_recon_2026-09-24.json"
OUT = ROOT / "docs/translation/stage6_w606_crm_support_maintenance_proposal_2026-09-24.csv"
SCOPE_SHA = "a77b43a908859c0aea3e2c58525ec3765772c09af8617f1f17fb8c8bf12833f9"

raw = SCOPE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == SCOPE_SHA
with SCOPE.open(encoding="utf-8", newline="") as handle:
    scope_rows = list(csv.DictReader(handle))
assert len(scope_rows) == 119

recon = json.loads(RECON.read_text(encoding="utf-8"))
site_overrides_map = {row["source_text"]: row["translated_text"] for row in recon["site_overrides"]}
assert len(site_overrides_map) == 76

missing_keys = set(recon["missing_runtime_keys"])
assert len(missing_keys) == 43
assert (set(TRANSLATIONS.keys()) | set(TECHNICAL_EXCEPTIONS.keys()) | set(DEFERRED_SOURCE_DEFECTS.keys())) == missing_keys

proposal_rows = []
for row in scope_rows:
    src = row["source_text"]
    loc = row.get("locations", "")
    if src in site_overrides_map:
        ar = site_overrides_map[src]
        disp = "preserved-site-override"
        rat = "Preserve the exact live v16.localhost Site Override; do not import or replace."
    elif src in DEFERRED_SOURCE_DEFECTS:
        ar = ""
        disp = "DEFERRED-source-defect"
        rat = DEFERRED_SOURCE_DEFECTS[src]
    elif src in TECHNICAL_EXCEPTIONS:
        ar = ""
        disp = "EXCEPTION-technical"
        rat = TECHNICAL_EXCEPTIONS[src]
    else:
        ar = TRANSLATIONS[src]
        disp = "PROPOSED-payload"
        rat = "Corrected AI draft; requires renewed independent A1/A2/A3 quorum before release."

    if disp not in {"EXCEPTION-technical", "DEFERRED-source-defect"}:
        src_ph = sorted(re.findall(r"\{[0-9]*\}", src))
        ar_ph = sorted(re.findall(r"\{[0-9]*\}", ar))
        assert src_ph == ar_ph, f"Placeholder mismatch for {src!r}: {src_ph} vs {ar_ph}"

    proposal_rows.append({
        "source_text": src,
        "proposed_ar": ar,
        "proposed_disposition": disp,
        "disposition_rationale": rat,
        "decision_ref": "stage6-W6-6 CRM Support Maintenance corrected-review-pending 2026-09-24",
        "locations": loc,
    })

assert len(proposal_rows) == 119
assert sum(row["proposed_disposition"] == "preserved-site-override" for row in proposal_rows) == 76
assert sum(row["proposed_disposition"] == "PROPOSED-payload" for row in proposal_rows) == 38
assert sum(row["proposed_disposition"] == "EXCEPTION-technical" for row in proposal_rows) == 1
assert sum(row["proposed_disposition"] == "DEFERRED-source-defect" for row in proposal_rows) == 4
assert len({row["source_text"] for row in proposal_rows}) == 119

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
