"""Build proposal CSV for W6-1 Accounts Batch 01."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
import sys

# Ensure docs/translation is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from stage6_w601_accounts_batch01_dict import TRANSLATIONS, TECHNICAL_EXCEPTIONS

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w601_accounts_batch01_rows_2026-09-24.csv"
RECON = ROOT / "docs/translation/stage6_w601_accounts_batch01_site_recon_2026-09-24.json"
OUT = ROOT / "docs/translation/stage6_w601_accounts_batch01_proposal_2026-09-24.csv"
SCOPE_SHA = "4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd"

raw = SCOPE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == SCOPE_SHA
with SCOPE.open(encoding="utf-8", newline="") as handle:
    scope_rows = list(csv.DictReader(handle))
assert len(scope_rows) == 250

recon = json.loads(RECON.read_text(encoding="utf-8"))
site_overrides_map = {row["source_text"]: row["translated_text"] for row in recon["site_overrides"]}
assert len(site_overrides_map) == 147

missing_keys = set(recon["missing_runtime_keys"])
assert len(missing_keys) == 103
assert (set(TRANSLATIONS.keys()) | set(TECHNICAL_EXCEPTIONS.keys())) == missing_keys

proposal_rows = []
for row in scope_rows:
    src = row["source_text"]
    loc = row.get("locations", "")
    if src in site_overrides_map:
        ar = site_overrides_map[src]
        disp = "preserved-site-override"
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

        # Verification: check leading/trailing whitespace affix parity
        src_leading = len(src) - len(src.lstrip())
        ar_leading = len(ar) - len(ar.lstrip())
        assert src_leading == ar_leading, f"Leading whitespace mismatch for {src!r}: {src_leading} vs {ar_leading}"

        src_trailing = len(src) - len(src.rstrip())
        ar_trailing = len(ar) - len(ar.rstrip())
        assert src_trailing == ar_trailing, f"Trailing whitespace mismatch for {src!r}: {src_trailing} vs {ar_trailing}"

        assert "\n" not in ar and "\r" not in ar, f"Newline in translation for {src!r}"
        assert ar != src, f"Source-equal translation for {src!r}"

    proposal_rows.append({
        "source_text": src,
        "proposed_ar": ar,
        "proposed_disposition": disp,
        "disposition_rationale": rat,
        "decision_ref": "stage6-W6-1 Accounts Batch 01 pending-owner-approval 2026-09-24",
        "locations": loc,
    })

assert len(proposal_rows) == 250

with OUT.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=[
        "source_text", "proposed_ar", "proposed_disposition",
        "disposition_rationale", "decision_ref", "locations"
    ], lineterminator="\n")
    writer.writeheader()
    writer.writerows(proposal_rows)

out_bytes = OUT.read_bytes()
out_sha = hashlib.sha256(out_bytes).hexdigest()
print(f"Proposal written: {len(proposal_rows)} rows, SHA-256: {out_sha}")
