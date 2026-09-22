#!/usr/bin/env python3
"""W6-0b batch-2 scope cut — extract batch `02` from the committed batch plan.

Owner approval gate: cut + commit proposal package only (scope CSV +
exclusions reference + proposal note). Does NOT run quorum, import, or any
other batch.

Regenerates (byte-stable given the same plan):
  docs/translation/stage6_w60b_batch02_rows_2026-09-22.csv
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / "stage6_w60b_batch_plan_2026-09-22.csv"
OUT = ROOT / "stage6_w60b_batch02_rows_2026-09-22.csv"
BATCH = "02"
FIELDS = [
    "source_text",
    "classification",
    "location",
    "suppression_rationale",
    "ai_r_ref",
    "length",
    "app",
    "suggested_ar",
]
EXPECTED_ROWS = 271
EXPECTED_SHA = "187361ab36ea2ab75f32355bce0b2b1c274b52bebd339b0c19ea3822436895db"


def main() -> None:
    rows = [r for r in csv.DictReader(PLAN.open(encoding="utf-8")) if r["batch"] == BATCH]
    assert len(rows) == EXPECTED_ROWS, len(rows)
    assert all(r["classification"] == "translation-candidate" for r in rows)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows({k: r[k] for k in FIELDS} for r in rows)
    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"wrote {OUT} ({len(rows)} rows) sha256={sha}")
    if sha != EXPECTED_SHA:
        print(f"NOTE: expected {EXPECTED_SHA} — plan or writer drift; re-pin proposal sha before approval")


if __name__ == "__main__":
    main()
