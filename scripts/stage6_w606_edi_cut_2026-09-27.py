#!/usr/bin/env python3
"""Deterministic cut script for Stage 6 W6-6 EDI Remainder scope.

Extracts all 26 EDI rows from docs/erpnext_ar_missing_review_filled.csv.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/erpnext_ar_missing_review_filled.csv"
OUT = ROOT / "docs/translation/stage6_w606_edi_rows_2026-09-27.csv"

def cut_edi_scope():
    with LEDGER.open(encoding="utf-8", newline="") as h:
        reader = csv.DictReader(h)
        edi_rows = [
            {
                "source_text": r["msgid"].strip(),
                "context": (r.get("context") or "").strip(),
                "locations": r.get("locations", "").strip(),
            }
            for r in reader
            if any("/edi/" in loc for loc in r.get("locations", "").split("; "))
        ]

    # Deterministic sort
    edi_rows.sort(key=lambda x: x["source_text"])

    assert len(edi_rows) == 26, f"Expected 26 rows, got {len(edi_rows)}"
    unique_keys = set(r["source_text"] for r in edi_rows)
    assert len(unique_keys) == 26, f"Expected 26 unique keys, got {len(unique_keys)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=["source_text", "context", "locations"])
        writer.writeheader()
        writer.writerows(edi_rows)

    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"Wrote {len(edi_rows)} rows to {OUT}")
    print(f"SHA-256: {sha}")

if __name__ == "__main__":
    cut_edi_scope()
