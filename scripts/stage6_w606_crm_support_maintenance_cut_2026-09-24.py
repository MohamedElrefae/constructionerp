"""Deterministically cut the proposal-only W6-6 CRM, Support & Maintenance batch."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/erpnext_ar_missing_review_filled.csv"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"
TECH = ROOT / "docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv"
DEDUP = ROOT / "docs/translation/stage6_w60b_dedup_exclusions_2026-09-22.csv"
OUTPUT = ROOT / "docs/translation/stage6_w606_crm_support_maintenance_rows_2026-09-24.csv"
MAX_LEN = 120
RE_HTML = re.compile(r"<[a-zA-Z/][^>]*>")
FIELDS = ("source_text", "suggested_ar", "locations", "area", "has_pre_filled")
TARGET_AREAS = {"crm", "support", "maintenance"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def area_of(row: dict[str, str]) -> str:
    first = (row.get("locations") or "").split(",")[0].strip()
    parts = first.split("/")
    try:
        return parts[parts.index("erpnext") + 1]
    except (ValueError, IndexError):
        return "(none)"


def keys(path: Path) -> set[str]:
    result = set()
    for row in read_rows(path):
        key = (row.get("source_text") or row.get("msgid") or "").strip()
        if key:
            result.add(key)
    return result


def main() -> None:
    raw_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    raw_count = 0
    for row in read_rows(LEDGER):
        if area_of(row) not in TARGET_AREAS:
            continue
        raw_count += 1
        source = (row.get("msgid") or "").strip()
        if source and source not in seen:
            seen.add(source)
            raw_rows.append(row)

    assert raw_count == 130, f"Expected 130 ledger rows, got {raw_count}"
    assert len(raw_rows) == 129, f"Expected 129 unique source keys, got {len(raw_rows)}"
    skip = [row for row in raw_rows if (row.get("skip") or "").strip().lower() == "yes"]
    live = [row for row in raw_rows if row not in skip]
    html = {row["msgid"] for row in live if RE_HTML.search(row["msgid"])}
    newline = {
        row["msgid"] for row in live
        if row["msgid"] not in html and ("\n" in row["msgid"] or "\r" in row["msgid"])
    }
    overlong = {
        row["msgid"] for row in live
        if row["msgid"] not in html | newline and len(row["msgid"]) > MAX_LEN
    }
    eligible = [
        row for row in live
        if row["msgid"] not in html | newline | overlong
    ]

    catalog = keys(APPROVED)
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    decision_keys = {
        (entry.get("source_text") or "").strip()
        for entry in decision_doc["decisions"].values()
        if entry.get("source_text")
    }
    prior: set[str] = set()
    for path in (ROOT / "docs/translation").glob("stage6_*rows*.csv"):
        if path != OUTPUT:
            prior |= keys(path)
    blocked = catalog | decision_keys | prior | keys(TECH) | keys(DEDUP)
    overlap = {row["msgid"] for row in eligible} & blocked
    fresh = sorted(
        (row for row in eligible if row["msgid"] not in blocked),
        key=lambda row: row["msgid"],
    )

    output_rows = []
    for row in fresh:
        suggested = row.get("msgstr") or ""
        output_rows.append({
            "source_text": row["msgid"],
            "suggested_ar": suggested,
            "locations": row.get("locations") or "",
            "area": area_of(row),
            "has_pre_filled": "1" if suggested.strip() else "0",
        })
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(output_rows)
    payload = buffer.getvalue().encode("utf-8")
    OUTPUT.write_bytes(payload)
    print(f"raw={raw_count} unique={len(raw_rows)} skipped={len(skip)}")
    print(f"excluded_html={len(html)} excluded_newline={len(newline)} excluded_overlong={len(overlong)}")
    print(f"overlap={len(overlap)} fresh={len(fresh)}")
    print(
        "prefilled="
        f"{sum(row['has_pre_filled'] == '1' for row in output_rows)} "
        "unfilled="
        f"{sum(row['has_pre_filled'] == '0' for row in output_rows)}"
    )
    print(f"sha256={hashlib.sha256(payload).hexdigest()}")
    print(f"output={OUTPUT}")


if __name__ == "__main__":
    main()
