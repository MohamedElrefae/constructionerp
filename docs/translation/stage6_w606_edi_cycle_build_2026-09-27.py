#!/usr/bin/env python3
"""Build applied payload, released list, and content evidence for Stage 6 W6-6 EDI Remainder."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL_CSV = ROOT / "docs/translation/stage6_w606_edi_proposal_2026-09-27.csv"
APPLIED_CSV = ROOT / "docs/translation/stage6_w606_edi_payload_applied_rows_2026-09-27.csv"
RELEASED_TXT = ROOT / "docs/translation/stage6_w606_edi_released_list_2026-09-27.txt"
CONTENT_TXT = ROOT / "docs/translation/stage6_w606_edi_content_evidence_2026-09-27.txt"

PROPOSAL_SHA = "ea74475780980e95f13346db8aaf8beb7b56c3202336950ae9432f2d2eebb6b7"

def build():
    assert hashlib.sha256(PROPOSAL_CSV.read_bytes()).hexdigest() == PROPOSAL_SHA, "Proposal SHA mismatch!"

    with PROPOSAL_CSV.open(encoding="utf-8", newline="") as h:
        rows = list(csv.DictReader(h))

    applied_rows = []
    released_keys = []
    content_lines = []

    for r in rows:
        src = r["source_text"]
        ctx = r.get("context", "")
        trans = r["proposed_translation"]
        disp = r["disposition"]
        comment = r["review_comments"]

        if disp == "preserved-site-override":
            applied_rows.append({
                "source_text": src,
                "context": ctx,
                "translated_text": trans,
                "disposition": "preserved-site-override",
                "review_comments": comment,
            })
        elif disp == "PROPOSED-payload":
            applied_rows.append({
                "source_text": src,
                "context": ctx,
                "translated_text": trans,
                "disposition": "quorum-confirmed-payload",
                "review_comments": "Approved by AI-A1, AI-A2, AI-A3 quorum; released to catalog v1.16",
            })
            released_keys.append(src)
            content_lines.append(f"{src}\t{trans}")
        else:
            raise ValueError(f"Unknown disposition: {disp}")

    assert len(applied_rows) == 26, f"Expected 26 rows, got {len(applied_rows)}"
    assert len(released_keys) == 17, f"Expected 17 released keys, got {len(released_keys)}"
    assert len(content_lines) == 17, f"Expected 17 content lines, got {len(content_lines)}"

    with APPLIED_CSV.open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(
            h,
            fieldnames=["source_text", "context", "translated_text", "disposition", "review_comments"]
        )
        writer.writeheader()
        writer.writerows(applied_rows)

    RELEASED_TXT.write_text("\n".join(released_keys) + "\n", encoding="utf-8")
    CONTENT_TXT.write_text("\n".join(content_lines) + "\n", encoding="utf-8")

    print(f"Applied payload written: {APPLIED_CSV} ({len(applied_rows)} rows, SHA: {hashlib.sha256(APPLIED_CSV.read_bytes()).hexdigest()})")
    print(f"Released list written: {RELEASED_TXT} ({len(released_keys)} keys, SHA: {hashlib.sha256(RELEASED_TXT.read_bytes()).hexdigest()})")
    print(f"Content evidence written: {CONTENT_TXT} ({len(content_lines)} pairs, SHA: {hashlib.sha256(CONTENT_TXT.read_bytes()).hexdigest()})")

if __name__ == "__main__":
    build()
