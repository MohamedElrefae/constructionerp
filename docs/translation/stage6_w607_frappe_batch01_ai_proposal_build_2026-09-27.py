#!/usr/bin/env python3
"""Build and structurally validate Stage 6 W6-7 Frappe Framework Remainder Batch 01 proposal CSV."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from stage6_w607_frappe_batch01_dict import FRAPPE_BATCH01_TRANSLATIONS

ROOT = Path(__file__).resolve().parents[2]
SCOPE_CSV = ROOT / "docs/translation/stage6_w607_frappe_batch01_rows_2026-09-27.csv"
RECON_JSON = ROOT / "docs/translation/stage6_w607_frappe_batch01_site_recon_2026-09-27.json"
OUT_CSV = ROOT / "docs/translation/stage6_w607_frappe_batch01_proposal_2026-09-27.csv"

SCOPE_SHA = "43abe1b462c47b51c0209a0650511fac2ed32cdb5f3a585cde2e9468bfaab26a"

TECHNICAL_KEYS = {
    "${values.doctype_name} has been added to queue for optimization": "Contains unresolved JS template string interpolation ${values.doctype_name}; technical fragment kept in vendor format",
    "&copy; Frappe Technologies Pvt. Ltd. and contributors": "Vendor copyright and legal trademark entity; kept in vendor format",
}


def extract_placeholders(text: str) -> list[str]:
    return sorted(re.findall(r"\{[0-9]*\}|%[sdf]", text))


def build_proposal():
    raw_scope = SCOPE_CSV.read_bytes()
    scope_sha = hashlib.sha256(raw_scope).hexdigest()
    assert scope_sha == SCOPE_SHA, f"Scope SHA mismatch: expected {SCOPE_SHA}, got {scope_sha}"

    recon = json.loads(RECON_JSON.read_text(encoding="utf-8"))
    site_overrides_map = {
        item["source_text"]: item["translated_text"]
        for item in recon["site_overrides"]
    }

    with SCOPE_CSV.open(encoding="utf-8", newline="") as h:
        scope_rows = list(csv.DictReader(h))

    assert len(scope_rows) == 250, f"Expected 250 scope rows, got {len(scope_rows)}"

    proposal_rows = []
    preserved_count = 0
    technical_count = 0
    payload_count = 0

    for row in scope_rows:
        src = row["source_text"]
        ctx = row.get("context", "")
        assert src in FRAPPE_BATCH01_TRANSLATIONS, f"Missing translation for {src!r}"
        trans = FRAPPE_BATCH01_TRANSLATIONS[src]

        if src in site_overrides_map:
            disposition = "preserved-site-override"
            comment = "Preserved verbatim from live v16.localhost tabTranslation (Plan §12)"
            assert trans == site_overrides_map[src], (
                f"Preserved mismatch for {src!r}: dict={trans!r}, live={site_overrides_map[src]!r}"
            )
            preserved_count += 1
        elif src in TECHNICAL_KEYS:
            disposition = "EXCEPTION-technical"
            comment = TECHNICAL_KEYS[src]
            assert trans == "", f"Technical key {src!r} must have empty translation, got {trans!r}"
            technical_count += 1
        else:
            disposition = "PROPOSED-payload"
            comment = "Candidate payload Arabic translation for Frappe framework UI"
            assert trans != "", f"Payload translation for {src!r} cannot be empty"
            payload_count += 1

            # Parity checks
            src_ph = extract_placeholders(src)
            tr_ph = extract_placeholders(trans)
            assert src_ph == tr_ph, f"Placeholder mismatch for {src!r}: src={src_ph}, tr={tr_ph}"
            assert src.startswith(" ") == trans.startswith(" "), f"Leading whitespace mismatch for {src!r}"
            assert src.endswith(" ") == trans.endswith(" "), f"Trailing whitespace mismatch for {src!r}"
            assert src.endswith(":") == trans.endswith(":"), f"Colon mismatch for {src!r}"
            assert src.endswith("...") == trans.endswith("..."), f"Ellipsis mismatch for {src!r}"

        proposal_rows.append({
            "source_text": src,
            "context": ctx,
            "proposed_translation": trans,
            "disposition": disposition,
            "review_comments": comment,
        })

    assert preserved_count == 1, f"Expected 1 preserved-site-override, got {preserved_count}"
    assert technical_count == 2, f"Expected 2 EXCEPTION-technical, got {technical_count}"
    assert payload_count == 247, f"Expected 247 PROPOSED-payload, got {payload_count}"
    assert len(proposal_rows) == 250, f"Expected 250 proposal rows, got {len(proposal_rows)}"

    with OUT_CSV.open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(
            h,
            fieldnames=["source_text", "context", "proposed_translation", "disposition", "review_comments"],
        )
        writer.writeheader()
        writer.writerows(proposal_rows)

    proposal_bytes = OUT_CSV.read_bytes()
    proposal_sha = hashlib.sha256(proposal_bytes).hexdigest()

    print(f"Generated proposal CSV with {len(proposal_rows)} rows: {OUT_CSV}")
    print(f"Scope CSV SHA-256:    {SCOPE_SHA}")
    print(f"Proposal CSV SHA-256: {proposal_sha}")
    print(f"Disposition partition: {preserved_count} preserved-site-override, {technical_count} EXCEPTION-technical, {payload_count} PROPOSED-payload")
    return proposal_sha


if __name__ == "__main__":
    build_proposal()
