#!/usr/bin/env python3
"""Build and structurally validate Stage 6 W6-6 EDI remainder proposal CSV."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from stage6_w606_edi_dict import EDI_TRANSLATIONS

ROOT = Path(__file__).resolve().parents[2]
SCOPE_CSV = ROOT / "docs/translation/stage6_w606_edi_rows_2026-09-27.csv"
RECON_JSON = ROOT / "docs/translation/stage6_w606_edi_site_recon_2026-09-27.json"
OUT_CSV = ROOT / "docs/translation/stage6_w606_edi_proposal_2026-09-27.csv"

SCOPE_SHA = "2b0cc9b46546aa36310f81738c72ff0d2b50ca35666110033976c424c149cef1"

def extract_placeholders(text: str) -> list[str]:
    return sorted(re.findall(r"\{[0-9]*\}", text))

def extract_html_tags(text: str) -> list[str]:
    return sorted(re.findall(r"</?[a-zA-Z0-9]+>", text))

def build_proposal():
    raw_scope = SCOPE_CSV.read_bytes()
    assert hashlib.sha256(raw_scope).hexdigest() == SCOPE_SHA, "Scope SHA mismatch!"

    recon = json.loads(RECON_JSON.read_text(encoding="utf-8"))
    site_overrides_map = {
        item["source_text"]: item["translated_text"]
        for item in recon["site_overrides"]
    }

    with SCOPE_CSV.open(encoding="utf-8", newline="") as h:
        scope_rows = list(csv.DictReader(h))

    assert len(scope_rows) == 26, f"Expected 26 scope rows, got {len(scope_rows)}"

    proposal_rows = []
    preserved_count = 0
    payload_count = 0

    for row in scope_rows:
        src = row["source_text"]
        ctx = row.get("context", "")
        assert src in EDI_TRANSLATIONS, f"Missing translation for {src!r}"
        trans = EDI_TRANSLATIONS[src]

        if src in site_overrides_map:
            disposition = "preserved-site-override"
            comment = "Preserved verbatim from live v16.localhost tabTranslation (Plan §12)"
            assert trans == site_overrides_map[src], f"Preserved mismatch for {src!r}: dict={trans!r}, live={site_overrides_map[src]!r}"
            preserved_count += 1
        else:
            disposition = "PROPOSED-payload"
            comment = "Candidate payload Arabic translation for ERPNext EDI module"
            payload_count += 1

            # Structural validation for payload
            # 1. Placeholder multiset parity
            src_ph = extract_placeholders(src)
            trans_ph = extract_placeholders(trans)
            assert src_ph == trans_ph, f"Placeholder mismatch for {src!r}: {src_ph} vs {trans_ph}"

            # 2. HTML tag validation
            src_tags = extract_html_tags(src)
            trans_tags = extract_html_tags(trans)
            assert src_tags == trans_tags, f"HTML tag mismatch for {src!r}: {src_tags} vs {trans_tags}"

            # 3. Whitespace affix parity
            assert (src.startswith(" ") == trans.startswith(" ")), f"Leading space mismatch for {src!r}"
            assert (src.endswith(" ") == trans.endswith(" ")), f"Trailing space mismatch for {src!r}"
            assert (src.endswith(":") == trans.endswith(":")), f"Colon affix mismatch for {src!r}"
            assert (src.endswith("...") == trans.endswith("...")), f"Ellipsis affix mismatch for {src!r}"

            # 4. No newlines / carriage returns
            assert "\n" not in trans and "\r" not in trans, f"Newline in translation for {src!r}"

        proposal_rows.append({
            "source_text": src,
            "context": ctx,
            "proposed_translation": trans,
            "disposition": disposition,
            "review_comments": comment,
        })

    assert preserved_count == 9, f"Expected 9 preserved site overrides, got {preserved_count}"
    assert payload_count == 17, f"Expected 17 proposed payload rows, got {payload_count}"
    assert len(proposal_rows) == 26, f"Expected 26 proposal rows, got {len(proposal_rows)}"

    with OUT_CSV.open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(
            h,
            fieldnames=["source_text", "context", "proposed_translation", "disposition", "review_comments"]
        )
        writer.writeheader()
        writer.writerows(proposal_rows)

    sha = hashlib.sha256(OUT_CSV.read_bytes()).hexdigest()
    print(f"Proposal written to {OUT_CSV}")
    print(f"Total rows: {len(proposal_rows)} (Preserved: {preserved_count}, Payload: {payload_count})")
    print(f"Proposal SHA-256: {sha}")

if __name__ == "__main__":
    build_proposal()
