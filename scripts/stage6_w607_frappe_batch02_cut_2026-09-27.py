#!/usr/bin/env python3
"""Deterministic cut script for Stage 6 W6-7 Frappe Framework Remainder Batch 02.

Extracts all remaining eligible Frappe framework UI strings from
docs/arabic_coverage_gap_report_2026-08-22.csv, enriches them with locations
and contexts from apps/frappe/frappe/locale/ar.po, and writes:
  docs/translation/stage6_w607_frappe_batch02_rows_2026-09-27.csv
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from babel.messages.pofile import read_po

BENCH_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = Path(__file__).resolve().parents[1]

LEDGER = APP_ROOT / "docs/arabic_coverage_gap_report_2026-08-22.csv"
APPROVED = APP_ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = APP_ROOT / "construction/data/translations/release_decisions.json"
TECH = APP_ROOT / "docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv"
DEDUP = APP_ROOT / "docs/translation/stage6_w60b_dedup_exclusions_2026-09-22.csv"
PO_FILE = BENCH_ROOT / "apps/frappe/frappe/locale/ar.po"

OUTPUT = APP_ROOT / "docs/translation/stage6_w607_frappe_batch02_rows_2026-09-27.csv"
MAX_LEN = 120
RE_HTML = re.compile(r"<[a-zA-Z/][^>]*>")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


def main() -> None:
    catalog = {
        (r.get("source_text") or "").strip()
        for r in read_csv(APPROVED)
        if r.get("source_text")
    }
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    decision_keys = {
        (entry.get("source_text") or "").strip()
        for entry in decision_doc["decisions"].values()
        if entry.get("source_text")
    }

    prior: set[str] = set()
    for path in (APP_ROOT / "docs/translation").glob("stage6_*rows*.csv"):
        if path != OUTPUT:
            for r in read_csv(path):
                k = (r.get("source_text") or r.get("msgid") or "").strip()
                if k:
                    prior.add(k)

    tech_keys = {
        (r.get("source_text") or "").strip()
        for r in read_csv(TECH)
        if r.get("source_text")
    }
    dedup_keys = {
        (r.get("source_text") or "").strip()
        for r in read_csv(DEDUP)
        if r.get("source_text")
    } if DEDUP.exists() else set()

    blocked = catalog | decision_keys | prior | tech_keys | dedup_keys

    # Load PO metadata
    po_map = {}
    if PO_FILE.exists():
        with PO_FILE.open("rb") as f:
            catalog_po = read_po(f, locale="ar")
            for m in catalog_po:
                if m.id:
                    po_map[m.id] = m

    raw = [r for r in read_csv(LEDGER) if r.get("app") == "frappe"]
    seen: set[str] = set()
    uniq: list[dict[str, str]] = []
    for r in raw:
        st = (r.get("source_text") or "").strip().replace(r'\"', '"')
        if st and st not in seen:
            seen.add(st)
            r["source_text"] = st
            uniq.append(r)

    html = {r["source_text"].strip() for r in uniq if RE_HTML.search(r["source_text"])}
    newline = {
        r["source_text"].strip() for r in uniq
        if r["source_text"].strip() not in html and ("\n" in r["source_text"] or "\r" in r["source_text"])
    }
    overlong = {
        r["source_text"].strip() for r in uniq
        if r["source_text"].strip() not in html | newline and len(r["source_text"].strip()) > MAX_LEN
    }

    eligible = [
        r for r in uniq
        if r["source_text"].strip() not in html | newline | overlong
    ]

    fresh = sorted(
        (r for r in eligible if r["source_text"].strip() not in blocked),
        key=lambda r: r["source_text"].strip(),
    )

    output_rows = []
    for r in fresh:
        st = r["source_text"].strip()
        po_entry = po_map.get(st)
        ctx = po_entry.context if (po_entry and po_entry.context) else ""
        if po_entry and po_entry.locations:
            locs = "; ".join(f"{path}:{line}" for path, line in po_entry.locations)
        else:
            locs = "in-ledger (no vendor PO location match)"

        output_rows.append({
            "source_text": st,
            "context": ctx,
            "locations": locs,
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=["source_text", "context", "locations"])
        writer.writeheader()
        writer.writerows(output_rows)

    sha = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(f"Total eligible frappe: {len(eligible)}")
    print(f"Total fresh remaining frappe: {len(fresh)}")
    print(f"Cut batch: {len(output_rows)} rows written to {OUTPUT}")
    print(f"Scope CSV SHA-256: {sha}")


if __name__ == "__main__":
    main()
