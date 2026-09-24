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
TECH_EXCLUSIONS = ROOT / "docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv"
DEDUP_EXCLUSIONS = ROOT / "docs/translation/stage6_w60b_dedup_exclusions_2026-09-22.csv"
OUTPUT = ROOT / "docs/translation/stage6_w604_projects_boq_rows_2026-09-24.csv"
MAX_LEN = 120
RAW_SHA = None
EXPECTED_SHA = "93fbf16b14940ce2d477f346c1777865bf008b22df943625e7de84f27e8f4abe"
AREAS = {"projects", "subcontracting"}
RE_HTML = re.compile(r"<[a-zA-Z/][^>]*>")
RE_TECH = re.compile(r"[A-Za-z0-9]+(?:[-.][A-Za-z0-9]+)*")
PRIOR_FILES = (
    "docs/translation/stage6_w60a_desk_shell_rows_2026-09-21.csv",
    "docs/translation/stage6_w60b_short_ui_rows_2026-09-22.csv",
    "docs/translation/stage6_w61_accounting_subset_rows_2026-09-21.csv",
    "docs/translation/stage6_w602_batch01_rows_2026-09-22.csv",
    "docs/translation/stage6_w602_batch02_rows_2026-09-23.csv",
    "docs/translation/stage6_w603_batch01_rows_2026-09-23.csv",
    "docs/translation/stage6_w603_batch02_rows_2026-09-23.csv",
    "docs/translation/stage6_w603_batch03_rows_2026-09-23.csv",
)
FIELDS = ("source_text", "suggested_ar", "locations", "area", "has_pre_filled")


def read_rows(path, delimiter=None):
    with path.open(encoding="utf-8", newline="") as handle:
        if delimiter is None:
            header = handle.readline()
            handle.seek(0)
            delimiter = "\t" if header.count("\t") > header.count(",") else ","
        return list(csv.DictReader(handle, delimiter=delimiter))


def first_location(row):
    return (row.get("locations") or "").split(",")[0].strip()


def area_of(location):
    parts = location.split("/")
    try:
        index = parts.index("erpnext")
    except ValueError:
        return "(none)"
    return parts[index + 1] if index + 1 < len(parts) else "(none)"


def load_keys(path):
    if path.suffix == ".txt":
        return {line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines() if line}
    return {
        (row.get("source_text") or row.get("msgid") or "")
        for row in read_rows(path)
        if row.get("source_text") or row.get("msgid")
    }


def main():
    ledger = read_rows(LEDGER)
    raw = []
    seen = set()
    for row in ledger:
        source = (row.get("msgid") or "").strip()
        if not source or area_of(first_location(row)) not in AREAS or source in seen:
            continue
        seen.add(source)
        raw.append(row)
    assert len(raw) == 151
    assert {area_of(first_location(row)) for row in raw} == AREAS
    live = [row for row in raw if (row.get("skip") or "").strip().lower() != "yes"]
    assert len(live) == 150

    catalog = load_keys(APPROVED)
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))["decisions"]
    decision_keys = {entry["source_text"] for entry in decisions.values()}
    technical = load_keys(TECH_EXCLUSIONS)
    dedup = load_keys(DEDUP_EXCLUSIONS)
    prior = set()
    for relative in PRIOR_FILES:
        prior |= load_keys(ROOT / relative)
    prior.discard("")

    html = {row["msgid"] for row in live if RE_HTML.search(row["msgid"])}
    newline = {
        row["msgid"]
        for row in live
        if row["msgid"] not in html and ("\n" in row["msgid"] or "\r" in row["msgid"])
    }
    long_rows = {
        row["msgid"]
        for row in live
        if row["msgid"] not in html | newline and len(row["msgid"]) > MAX_LEN
    }
    rest = [row for row in live if row["msgid"] not in html | newline | long_rows]
    excluded = {
        row["msgid"]
        for row in rest
        if row["msgid"] in catalog
        or row["msgid"] in decision_keys
        or row["msgid"] in technical
        or row["msgid"] in dedup
        or row["msgid"] in prior
    }
    scope = [row for row in rest if row["msgid"] not in excluded]
    assert len(scope) == 147
    assert len({row["msgid"] for row in scope}) == len(scope)
    assert not ({row["msgid"] for row in scope} & (catalog | decision_keys | technical | dedup | prior))

    output_rows = []
    for row in sorted(scope, key=lambda item: (area_of(first_location(item)), item["msgid"])):
        suggested = (row.get("msgstr") or "").strip()
        output_rows.append(
            {
                "source_text": row["msgid"],
                "suggested_ar": suggested,
                "locations": row.get("locations") or "",
                "area": area_of(first_location(row)),
                "has_pre_filled": "1" if suggested else "0",
            }
        )
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(output_rows)
    payload = buffer.getvalue().encode("utf-8")
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_SHA
    OUTPUT.write_bytes(payload)
    print(f"raw_unique={len(raw)} live_after_skip={len(live)} scope={len(scope)}")
    print(f"projects={sum(row['area'] == 'projects' for row in output_rows)} subcontracting={sum(row['area'] == 'subcontracting' for row in output_rows)}")
    print(f"prefilled={sum(row['has_pre_filled'] == '1' for row in output_rows)} unfilled={sum(row['has_pre_filled'] == '0' for row in output_rows)}")
    print(f"excluded_html={len(html)} excluded_newline={len(newline)} excluded_long={len(long_rows)} excluded_catalog_or_prior={len(excluded)} skipped_yes={len(raw) - len(live)}")
    print(f"sha256={EXPECTED_SHA}")
    print(f"output={OUTPUT}")


if __name__ == "__main__":
    main()
