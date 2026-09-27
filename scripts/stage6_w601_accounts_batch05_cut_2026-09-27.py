"""Deterministically cut the proposal-only W6-1 Accounts batch 05 (final 56 rows)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/erpnext_ar_missing_review_filled.csv"
TECH = ROOT / "docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv"
DEDUP = ROOT / "docs/translation/stage6_w60b_dedup_exclusions_2026-09-22.csv"
OUTPUT = ROOT / "docs/translation/stage6_w601_accounts_batch05_rows_2026-09-27.csv"
START = 1000
CAP = 56
MAX_LEN = 120
RE_HTML = re.compile(r"<[a-zA-Z/][^>]*>")
FIELDS = ("source_text", "suggested_ar", "locations", "area", "has_pre_filled")


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


def keys_from_text(text: str) -> set[str]:
    reader = csv.DictReader(text.splitlines())
    return {
        (r.get("source_text") or r.get("msgid") or "").strip()
        for r in reader
        if (r.get("source_text") or r.get("msgid") or "").strip()
    }


def keys(path: Path) -> set[str]:
    return {
        (r.get("source_text") or r.get("msgid") or "").strip()
        for r in read_rows(path)
        if (r.get("source_text") or r.get("msgid") or "").strip()
    }


def main() -> None:
    raw_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    raw_count = 0
    for row in read_rows(LEDGER):
        if area_of(row) != "accounts":
            continue
        raw_count += 1
        source = (row.get("msgid") or "").strip()
        if source and source not in seen:
            seen.add(source)
            raw_rows.append(row)

    assert raw_count == 1265, f"Expected 1265 ledger rows, got {raw_count}"
    assert len(raw_rows) == 1265, f"Expected 1265 unique source keys, got {len(raw_rows)}"
    skip = [row for row in raw_rows if (row.get("skip") or "").strip().lower() == "yes"]
    assert len(skip) == 3, f"Expected 3 skipped rows, got {len(skip)}"
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
    assert len(eligible) == 1198, f"Expected 1198 eligible rows, got {len(eligible)}"

    catalog_raw = subprocess.check_output(
        ["git", "show", "ea553f2:construction/data/translations/approved_ar_overrides.csv"],
        cwd=ROOT,
    ).decode("utf-8")
    decisions_raw = subprocess.check_output(
        ["git", "show", "ea553f2:construction/data/translations/release_decisions.json"],
        cwd=ROOT,
    ).decode("utf-8")

    catalog = keys_from_text(catalog_raw)
    decisions_doc = json.loads(decisions_raw)
    decision_keys = {
        (entry.get("source_text") or "").strip()
        for entry in decisions_doc["decisions"].values()
        if entry.get("source_text")
    }

    prior: set[str] = set()
    rows_paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "ea553f2", "docs/translation"],
        cwd=ROOT,
    ).decode("utf-8").splitlines()
    for p in rows_paths:
        if "rows" in p and p.endswith(".csv") and "accounts" not in p:
            content = subprocess.check_output(["git", "show", f"ea553f2:{p}"], cwd=ROOT).decode("utf-8")
            prior |= keys_from_text(content)

    blocked = catalog | decision_keys | prior | keys(TECH) | keys(DEDUP)
    overlap = {row["msgid"] for row in eligible} & blocked
    fresh = sorted(
        (row for row in eligible if row["msgid"] not in blocked),
        key=lambda row: row["msgid"],
    )
    assert len(overlap) == 142, f"Expected 142 already-covered keys, got {len(overlap)}"
    assert len(fresh) == 1056, f"Expected 1056 fresh rows, got {len(fresh)}"
    batch = fresh[START:START + CAP]
    assert len(batch) == CAP, f"Expected {CAP} rows, got {len(batch)}"

    output_rows = []
    for row in batch:
        suggested = row.get("msgstr") or ""
        output_rows.append({
            "source_text": row["msgid"],
            "suggested_ar": suggested,
            "locations": row.get("locations") or "",
            "area": "accounts",
            "has_pre_filled": "1" if suggested.strip() else "0",
        })
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(output_rows)
    payload = buffer.getvalue().encode("utf-8")
    OUTPUT.write_bytes(payload)
    print(f"raw={raw_count} unique={len(raw_rows)} skipped={len(skip)}")
    print(f"excluded_html={len(html)} excluded_newline={len(newline)} excluded_overlong={len(overlong)} already_covered={len(overlap)}")
    print(f"fresh_total={len(fresh)} batch05={len(batch)} remaining_after_batch05={len(fresh) - (START + len(batch))}")
    print(
        "batch05_prefilled="
        f"{sum(row['has_pre_filled'] == '1' for row in output_rows)} "
        "batch05_unfilled="
        f"{sum(row['has_pre_filled'] == '0' for row in output_rows)}"
    )
    print(f"sha256={hashlib.sha256(payload).hexdigest()}")
    print(f"output={OUTPUT}")


if __name__ == "__main__":
    main()
