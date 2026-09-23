#!/usr/bin/env python3
"""W6-3 Stock exact scope cut — proposal only (2026-09-23).

Deterministic and fail-closed; regenerates ONLY:
  docs/translation/stage6_w603_stock_rows_2026-09-23.csv

Committed scope sha256 (asserted before write):
  a60b1c8ec3bae8977826ed9101ee59a9206c699425e921da3f3d7341a7604535

Does NOT touch the catalog, release_decisions, manifests, pins, quorum
files, or any evidence. Read-only against all inputs.

Cut rules (same pipeline as W6-2 batch-01/02):
  1. ledger rows with skip not yes; non-empty msgid
  2. first location path under erpnext/stock/  (matrix row W6-3 area)
  3. deduplicate by msgid (first wins)
  4. bound: len(msgid) <= 120
  5. drop HTML/template rows (`<tag>` or embedded newline/CR)
  6. drop rows in technical exclusions (21), a1/a2 dedup exclusions (302),
     released catalog, and any prior W6-0a/W6-0b/W6-1/W6-2 scope,
     payload, or released-list keys
  7. write CSV sorted by area, source_text

Prints: partition identity, overlap proof, proposed disposition breakdown,
sha256 of the written CSV.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "erpnext_ar_missing_review_filled.csv"
APPROVED = ROOT / "construction" / "data" / "translations" / "approved_ar_overrides.csv"
TECH_EXCL = ROOT / "docs" / "translation" / "stage6_w60b_technical_exclusions_2026-09-22.csv"
DEDUP_EXCL = ROOT / "docs" / "translation" / "stage6_w60b_dedup_exclusions_2026-09-22.csv"
BATCH01 = ROOT / "docs" / "translation" / "stage6_w602_batch01_rows_2026-09-22.csv"
BATCH02 = ROOT / "docs" / "translation" / "stage6_w602_batch02_rows_2026-09-23.csv"
W61 = ROOT / "docs" / "translation" / "stage6_w61_accounting_subset_rows_2026-09-21.csv"
OUT = ROOT / "docs" / "translation" / "stage6_w603_stock_rows_2026-09-23.csv"

MAX_LEN = 120
AREA = "stock"
EXPECTED_SHA = "a60b1c8ec3bae8977826ed9101ee59a9206c699425e921da3f3d7341a7604535"
RE_HTML = re.compile(r"<[a-zA-Z/][^>]*>")
RE_TECH = re.compile(r"[A-Za-z0-9]+(?:[-.][A-Za-z0-9]+)*")


def first_location(row: dict) -> str:
    return (row.get("locations") or "").split(",")[0].strip()


def area_of(loc: str) -> str:
    parts = loc.split("/")
    try:
        i = parts.index("erpnext")
    except ValueError:
        return "(none)"
    return parts[i + 1] if i + 1 < len(parts) else "(none)"


def is_technical_token(text: str) -> bool:
    """No-space code/acronym token: digit, hyphen, or all-uppercase."""
    if " " in text or not RE_TECH.fullmatch(text):
        return False
    return any(c.isdigit() for c in text) or "-" in text or text.isupper()


def load_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    if path.suffix == ".txt":
        return {ln.rstrip("\n") for ln in path.read_text(encoding="utf-8").splitlines() if ln}
    with path.open(encoding="utf-8", newline="") as fh:
        header = fh.readline()
        fh.seek(0)
        delim = "\t" if header.count("\t") > header.count(",") else ","
        reader = csv.DictReader(fh, delimiter=delim)
        keys = set()
        for row in reader:
            val = row.get("source_text") or row.get("msgid")
            if val:
                keys.add(val)
        return keys


def prior_stage6_keys() -> tuple[set[str], list[str]]:
    patterns = [
        "docs/translation/stage6_w60*.csv",
        "docs/translation/stage6_w60*.txt",
        "docs/translation/stage6_w61*.csv",
        "docs/translation/stage6_w602*.csv",
        "docs/translation/stage6_w602*.txt",
    ]
    files: list[Path] = []
    for pat in patterns:
        files.extend(ROOT.glob(pat))
    # scope inputs only (never this output)
    files = sorted({f for f in files if f.resolve() != OUT.resolve()})
    keys: set[str] = set()
    names: list[str] = []
    for f in files:
        rel = str(f.relative_to(ROOT))
        if "w603" in rel:
            continue
        keys |= load_keys(f)
        names.append(rel)
    return keys, names


def main() -> None:
    with LEDGER.open(encoding="utf-8", newline="") as fh:
        ledger = list(csv.DictReader(fh))

    live = [
        r
        for r in ledger
        if (r.get("skip") or "").strip().lower() != "yes" and (r.get("msgid") or "").strip()
    ]

    stock_rows: list[dict] = []
    seen: set[str] = set()
    for r in live:
        if area_of(first_location(r)) != AREA:
            continue
        if r["msgid"] in seen:
            continue
        seen.add(r["msgid"])
        stock_rows.append(r)
    raw_unique = len(stock_rows)

    catalog = load_keys(APPROVED)
    tech_excl = load_keys(TECH_EXCL)
    dedup_excl = load_keys(DEDUP_EXCL)
    b1 = load_keys(BATCH01)
    b2 = load_keys(BATCH02)
    w61 = load_keys(W61)
    prior, prior_files = prior_stage6_keys()

    # mutually exclusive buckets (priority: HTML -> newline -> len>120 ->
    # exclusions/catalog/prior -> scope)
    b_html = [r for r in stock_rows if RE_HTML.search(r["msgid"])]
    k_html = {r["msgid"] for r in b_html}
    b_nl = [
        r
        for r in stock_rows
        if r["msgid"] not in k_html and ("\n" in r["msgid"] or "\r" in r["msgid"])
    ]
    k_nl = {r["msgid"] for r in b_nl}
    b_len = [
        r
        for r in stock_rows
        if r["msgid"] not in k_html
        and r["msgid"] not in k_nl
        and len(r["msgid"]) > MAX_LEN
    ]
    k_len = {r["msgid"] for r in b_len}
    rest = [
        r
        for r in stock_rows
        if r["msgid"] not in k_html and r["msgid"] not in k_nl and r["msgid"] not in k_len
    ]

    b_catalog = [r for r in rest if r["msgid"] in catalog]
    k_catalog = {r["msgid"] for r in b_catalog}
    b_excl = [
        r
        for r in rest
        if r["msgid"] not in k_catalog
        and (
            r["msgid"] in tech_excl
            or r["msgid"] in dedup_excl
            or r["msgid"] in b1
            or r["msgid"] in b2
            or r["msgid"] in w61
            or r["msgid"] in prior
        )
    ]
    scope = [
        r
        for r in rest
        if r["msgid"] not in k_catalog
        and not any(
            r["msgid"] in s
            for s in (tech_excl, dedup_excl, b1, b2, w61, prior)
        )
    ]

    # identity
    assert (
        len(b_html) + len(b_nl) + len(b_len) + len(b_catalog) + len(b_excl) + len(scope)
        == raw_unique
    ), "partition identity failed"
    assert raw_unique == 789, f"expected raw 789, got {raw_unique}"
    assert not b_catalog and not b_excl

    scope_keys = [r["msgid"] for r in scope]
    assert len(set(scope_keys)) == len(scope_keys), "scope keys not unique"
    assert not (set(scope_keys) & catalog), "scope overlaps released catalog"
    assert not (set(scope_keys) & (tech_excl | dedup_excl | b1 | b2 | w61 | prior))

    # proposed dispositions (NOT quorum; cycle-time classification only)
    proposed_tech = [r for r in scope if is_technical_token(r["msgid"])]
    proposed_payload = [r for r in scope if r not in proposed_tech]
    assert len(proposed_tech) + len(proposed_payload) == len(scope)

    out_rows = sorted(scope, key=lambda r: (AREA, r["msgid"]))
    fieldnames = ["source_text", "suggested_ar", "locations", "area", "has_pre_filled"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    for r in out_rows:
        msgstr = (r.get("msgstr") or "").strip()
        w.writerow(
            {
                "source_text": r["msgid"],
                "suggested_ar": msgstr,
                "locations": r.get("locations") or "",
                "area": AREA,
                "has_pre_filled": "1" if msgstr else "0",
            }
        )
    payload = buf.getvalue().encode("utf-8")
    sha = hashlib.sha256(payload).hexdigest()
    assert sha == EXPECTED_SHA, f"scope sha drift: {sha} != {EXPECTED_SHA}"
    OUT.write_bytes(payload)
    prefilled = sum(1 for r in scope if (r.get("msgstr") or "").strip())
    placeholders = sum(1 for r in scope if re.search(r"\{[^{}]*\}", r["msgid"]))
    lens = [len(r["msgid"]) for r in scope]

    print(f"raw unique stock msgids        : {raw_unique}")
    print(f"  HTML/template residual       : {len(b_html)}")
    print(f"  newline-template residual    : {len(b_nl)}")
    print(f"  len>{MAX_LEN} residual           : {len(b_len)}")
    print(f"  already-released (catalog)   : {len(b_catalog)}")
    print(f"  tech/dedup/prior residual    : {len(b_excl)}")
    print(f"  SCOPE (proposed)             : {len(scope)}")
    print(
        "identity: "
        f"{len(b_html)}+{len(b_nl)}+{len(b_len)}+{len(b_catalog)}+{len(b_excl)}"
        f"+{len(scope)} = {raw_unique}"
    )
    print()
    print("overlap proof (scope vs released / prior):")
    print(f"  scope keys                         : {len(scope_keys)}")
    print(f"  vs released catalog (2319 Released): {len(set(scope_keys) & catalog)}")
    print(f"  vs W6-2 batch 01 scope (270)       : {len(set(scope_keys) & b1)}")
    print(f"  vs W6-2 batch 02 scope (48)        : {len(set(scope_keys) & b2)}")
    print(f"  vs W6-1 accounting subset ({len(w61)})       : {len(set(scope_keys) & w61)}")
    print(f"  vs technical exclusions (21)       : {len(set(scope_keys) & tech_excl)}")
    print(f"  vs a1/a2 dedup exclusions (302)    : {len(set(scope_keys) & dedup_excl)}")
    print(
        f"  vs all prior stage-6 files ({len(prior)} keys, {len(prior_files)} files): "
        f"{len(set(scope_keys) & prior)}"
    )
    # stripped-form collision watch (batch-01 Address precedent)
    cat_stripped = {k.strip() for k in catalog}
    stripped_hits = sorted(
        {k for k in scope_keys if k != k.strip() and k.strip() in cat_stripped}
    )
    print(f"  stripped-form catalog collisions    : {len(stripped_hits)} {stripped_hits}")
    print()
    print("proposed disposition breakdown (NOT yet quorum):")
    print(f"  PROPOSED-payload                    : {len(proposed_payload)}")
    print(f"  PROPOSED-EXCEPTION-technical        : {len(proposed_tech)}")
    print(f"  preserved-site-override (cycle-time): unknown until site recon")
    print(f"  already-released in scope           : 0")
    print(f"  total scope                         : {len(scope)}")
    print(f"    pre-filled msgstr                 : {prefilled}")
    print(f"    unfilled (AI proposal at cycle)   : {len(scope) - prefilled}")
    print(f"    placeholder rows                  : {placeholders}")
    print(f"    length range                      : {min(lens)}-{max(lens)}")
    print()
    print(f"wrote {OUT}")
    print(f"sha256 {sha}")
    print(f"rows (incl. header) {sum(1 for _ in OUT.open(encoding='utf-8'))}")


if __name__ == "__main__":
    main()
