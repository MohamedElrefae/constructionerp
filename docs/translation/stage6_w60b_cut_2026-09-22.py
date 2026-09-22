#!/usr/bin/env python3
"""W6-0b exact cut — short UI strings (≤40 chars) from the frappe gap ledger.

Deterministic; regenerates:
  docs/translation/stage6_w60b_short_ui_rows_2026-09-22.csv
  docs/translation/stage6_w60b_dedup_exclusions_2026-09-22.csv

Filters (Owner Annotation 1 / proposal §W6-0b):
  1. ledger app == frappe
  2. source_text.strip() nonempty and len(strip) <= 40
  3. unique by stripped source_text (first wins)
  4. exclude prior-approved a1/a2 rows (approved_ar_overrides.csv source_text)
  5. classify remaining:
       EXCEPTION-technical  — no A-Z/a-z, HTML tag, newline, or JS ${template}
       translation-candidate — otherwise (incl. natural {0}/{1} messages)
  6. location fallback for all rows (no vendor PO location match for this cut)
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs" / "arabic_coverage_gap_report_2026-08-22.csv"
APPROVED = ROOT / "construction" / "data" / "translations" / "approved_ar_overrides.csv"
OUT_ROWS = ROOT / "docs" / "translation" / "stage6_w60b_short_ui_rows_2026-09-22.csv"
OUT_EXCL = ROOT / "docs" / "translation" / "stage6_w60b_dedup_exclusions_2026-09-22.csv"

MAX_LEN = 40
LOC_FALLBACK = "in-ledger (no vendor PO location match)"
SUPPRESS_TECH = (
    "Keep vendor code/symbol/markup content untouched — technical fragment, no translation"
)
SUPPRESS_PRIOR = "Already approved in a1/a2 overrides — excluded to avoid duplicate scope"
AI_R_TECH = "AI-R: confirm technical suppress at W6-0b AI-R pass (stage6-w60b AI-R record)"
AI_R_PRIOR = "AI-R: confirm prior-approved exclusion at W6-0b AI-R pass (stage6-w60b AI-R record)"

RE_HTML = re.compile(r"<[a-zA-Z/][^>]*>")
RE_JS_TMPL = re.compile(r"\$\{")


def is_technical(text: str) -> bool:
    if not re.search(r"[A-Za-z]", text):
        return True
    if RE_HTML.search(text):
        return True
    if "\n" in text or "\r" in text:
        return True
    if RE_JS_TMPL.search(text):
        return True
    return False


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    approved = {r["source_text"] for r in load_csv(APPROVED) if r.get("source_text")}
    seen: set[str] = set()
    rows: list[dict] = []
    excl: list[dict] = []

    for r in load_csv(LEDGER):
        if r.get("app") != "frappe":
            continue
        text = (r.get("source_text") or "").strip()
        if not text or len(text) > MAX_LEN or text in seen:
            continue
        seen.add(text)
        suggested = (r.get("suggested_ar") or "").strip()
        if text in approved:
            excl.append(
                {
                    "source_text": text,
                    "reason": "prior_approved_a1a2",
                    "length": str(len(text)),
                }
            )
            continue
        technical = is_technical(text)
        rows.append(
            {
                "source_text": text,
                "classification": "EXCEPTION-technical"
                if technical
                else "translation-candidate",
                "location": LOC_FALLBACK,
                "suppression_rationale": SUPPRESS_TECH if technical else "",
                "ai_r_ref": AI_R_TECH if technical else AI_R_PRIOR,
                "length": str(len(text)),
                "app": "frappe",
                "suggested_ar": suggested,
            }
        )

    OUT_ROWS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_ROWS.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "source_text",
                "classification",
                "location",
                "suppression_rationale",
                "ai_r_ref",
                "length",
                "app",
                "suggested_ar",
            ],
        )
        w.writeheader()
        w.writerows(rows)
    with OUT_EXCL.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["source_text", "reason", "length"])
        w.writeheader()
        w.writerows(excl)

    tech = sum(1 for r in rows if r["classification"] == "EXCEPTION-technical")
    print(f"scope={len(rows)} candidates={len(rows) - tech} technical={tech}")
    print(f"excluded={len(excl)} unique_short={len(seen)}")
    print(f"wrote {OUT_ROWS}")
    print(f"wrote {OUT_EXCL}")


if __name__ == "__main__":
    main()
