#!/usr/bin/env python3
"""W6-3 Stock deterministic sub-batch split — proposal only (2026-09-23).

Splits the owner-approved 734-row candidate universe into contiguous
sorted slices of ≤300 rows (target ~200–300). Fail-closed against the
committed universe sha256.

Inputs (read-only):
  docs/translation/stage6_w603_stock_rows_2026-09-23.csv
    sha256 a60b1c8ec3bae8977826ed9101ee59a9206c699425e921da3f3d7341a7604535

Outputs (only these; never catalog/decisions/manifests/pins/evidence):
  docs/translation/stage6_w603_batch01_rows_2026-09-23.csv
  docs/translation/stage6_w603_batch02_rows_2026-09-23.csv
  docs/translation/stage6_w603_batch03_rows_2026-09-23.csv

Split rule (deterministic):
  1. Load universe CSV; assert sha256 and row count 734.
  2. Rows are already unique and sorted by (area, source_text).
  3. Contiguous slices in that order: BATCH_SIZE=250 for batches 1..n-1;
     final batch takes the remainder (must be in [200, 300]).
  4. Union of batch keys == universe; pairwise intersections empty.
  5. Per-batch disposition uses the same is_technical_token rule as the
     cut builder (PROPOSED-payload / PROPOSED-EXCEPTION-technical).
  6. Per-batch overlap proof vs released catalog and prior Stage-6 keys.

Does NOT run quorum, import, DRY, freshness, inventory, evidence, or browser.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE = ROOT / "docs" / "translation" / "stage6_w603_stock_rows_2026-09-23.csv"
APPROVED = ROOT / "construction" / "data" / "translations" / "approved_ar_overrides.csv"
TECH_EXCL = ROOT / "docs" / "translation" / "stage6_w60b_technical_exclusions_2026-09-22.csv"
DEDUP_EXCL = ROOT / "docs" / "translation" / "stage6_w60b_dedup_exclusions_2026-09-22.csv"
BATCH01_W602 = ROOT / "docs" / "translation" / "stage6_w602_batch01_rows_2026-09-22.csv"
BATCH02_W602 = ROOT / "docs" / "translation" / "stage6_w602_batch02_rows_2026-09-23.csv"
W61 = ROOT / "docs" / "translation" / "stage6_w61_accounting_subset_rows_2026-09-21.csv"

UNIVERSE_SHA = "a60b1c8ec3bae8977826ed9101ee59a9206c699425e921da3f3d7341a7604535"
UNIVERSE_ROWS = 734
BATCH_SIZE = 250
MIN_BATCH, MAX_BATCH = 200, 300
N_BATCHES = 3
FIELDNAMES = ["source_text", "suggested_ar", "locations", "area", "has_pre_filled"]
RE_TECH = re.compile(r"[A-Za-z0-9]+(?:[-.][A-Za-z0-9]+)*")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
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


def prior_stage6_keys(exclude_w603_batches: bool = True) -> set[str]:
    keys: set[str] = set()
    for pat in (
        "docs/translation/stage6_w60*.csv",
        "docs/translation/stage6_w61*.csv",
    ):
        for f in ROOT.glob(pat):
            rel = str(f.relative_to(ROOT))
            if exclude_w603_batches and "w603" in rel:
                continue
            if f.resolve() == UNIVERSE.resolve():
                continue
            keys |= load_keys(f)
    return keys


def is_technical_token(text: str) -> bool:
    if " " in text or not RE_TECH.fullmatch(text):
        return False
    return any(c.isdigit() for c in text) or "-" in text or text.isupper()


def write_batch(path: Path, rows: list[dict]) -> tuple[str, int]:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDNAMES, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    payload = buf.getvalue().encode("utf-8")
    path.write_bytes(payload)
    return sha256_bytes(payload), len(rows)


def main() -> None:
    raw = UNIVERSE.read_bytes()
    u_sha = sha256_bytes(raw)
    assert u_sha == UNIVERSE_SHA, f"universe sha drift: {u_sha}"

    with UNIVERSE.open(encoding="utf-8", newline="") as fh:
        universe = list(csv.DictReader(fh))
    assert len(universe) == UNIVERSE_ROWS, f"expected {UNIVERSE_ROWS}, got {len(universe)}"

    keys = [r["source_text"] for r in universe]
    assert len(set(keys)) == len(keys), "universe keys not unique"
    # deterministic order already in file; re-assert sort
    assert keys == sorted(keys) or all(
        (universe[i]["area"], universe[i]["source_text"])
        <= (universe[i + 1]["area"], universe[i + 1]["source_text"])
        for i in range(len(universe) - 1)
    ), "universe not sorted by (area, source_text)"

    # contiguous slices: 250 + 250 + 234
    sizes = [BATCH_SIZE] * (N_BATCHES - 1)
    rest = UNIVERSE_ROWS - sum(sizes)
    sizes.append(rest)
    assert len(sizes) == N_BATCHES
    assert sum(sizes) == UNIVERSE_ROWS
    for s in sizes:
        assert MIN_BATCH <= s <= MAX_BATCH, f"batch size {s} outside [{MIN_BATCH},{MAX_BATCH}]"

    catalog = load_keys(APPROVED)
    tech_excl = load_keys(TECH_EXCL)
    dedup_excl = load_keys(DEDUP_EXCL)
    w602_b1 = load_keys(BATCH01_W602)
    w602_b2 = load_keys(BATCH02_W602)
    w61 = load_keys(W61)
    prior = prior_stage6_keys()

    batches: list[list[dict]] = []
    idx = 0
    for n, sz in enumerate(sizes, start=1):
        chunk = universe[idx : idx + sz]
        idx += sz
        batches.append(chunk)

    assert idx == UNIVERSE_ROWS

    # partition integrity
    all_batch_keys: list[set[str]] = []
    for n, chunk in enumerate(batches, start=1):
        bkeys = [r["source_text"] for r in chunk]
        assert len(set(bkeys)) == len(bkeys), f"batch {n} internal dups"
        all_batch_keys.append(set(bkeys))

    union: set[str] = set()
    for n, ks in enumerate(all_batch_keys, start=1):
        assert not (ks & union), f"batch {n} overlaps earlier batches"
        union |= ks
    assert union == set(keys), "batch union != universe"
    assert len(union) == UNIVERSE_ROWS

    print(f"universe sha256 : {u_sha}")
    print(f"universe rows   : {UNIVERSE_ROWS}")
    print(f"split rule      : contiguous slices of sorted (area, source_text); sizes={sizes}")
    print()

    out_paths: list[Path] = []
    for n, chunk in enumerate(batches, start=1):
        path = ROOT / "docs" / "translation" / f"stage6_w603_batch0{n}_rows_2026-09-23.csv"
        b_sha, b_n = write_batch(path, chunk)
        out_paths.append(path)

        bkeys = [r["source_text"] for r in chunk]
        ks = set(bkeys)
        tech = [k for k in bkeys if is_technical_token(k)]
        payload_n = b_n - len(tech)
        prefilled = sum(1 for r in chunk if (r.get("suggested_ar") or "").strip())

        # overlap proof
        ov_cat = len(ks & catalog)
        ov_prior = len(ks & prior)
        ov_tech = len(ks & tech_excl)
        ov_dedup = len(ks & dedup_excl)
        ov_w1 = len(ks & w602_b1)
        ov_w2 = len(ks & w602_b2)
        ov_w61 = len(ks & w61)
        # other batches
        ov_other = 0
        for m, oks in enumerate(all_batch_keys, start=1):
            if m != n:
                ov_other += len(ks & oks)

        assert ov_cat == 0 and ov_prior == 0 and ov_tech == 0 and ov_dedup == 0
        assert ov_w1 == 0 and ov_w2 == 0 and ov_w61 == 0 and ov_other == 0

        print(f"=== batch 0{n} ===")
        print(f"  file              : {path.relative_to(ROOT)}")
        print(f"  rows              : {b_n}")
        print(f"  sha256            : {b_sha}")
        print(f"  disposition       : PROPOSED-payload={payload_n}  "
              f"PROPOSED-EXCEPTION-technical={len(tech)}  already-released=0  "
              f"total={b_n}")
        print(f"  pre-filled        : {prefilled}  unfilled={b_n - prefilled}")
        print(f"  overlap vs catalog(2319)     : {ov_cat}")
        print(f"  overlap vs prior stage6      : {ov_prior}")
        print(f"  overlap vs tech(21)/dedup(302): {ov_tech}/{ov_dedup}")
        print(f"  overlap vs w602 b1/b2, w61   : {ov_w1}/{ov_w2}/{ov_w61}")
        print(f"  overlap vs other batches     : {ov_other}")
        print(f"  internal dups                : {len(bkeys) - len(ks)}")
        print()

    # cross-batch totals
    total_payload = 0
    total_tech = 0
    for chunk in batches:
        for r in chunk:
            if is_technical_token(r["source_text"]):
                total_tech += 1
            else:
                total_payload += 1
    assert total_payload + total_tech == UNIVERSE_ROWS
    print("=== split totals ===")
    print(f"  batches                   : {N_BATCHES} sizes={sizes}")
    print(f"  union rows                : {len(union)} (== universe {UNIVERSE_ROWS})")
    print(f"  PROPOSED-payload          : {total_payload}")
    print(f"  PROPOSED-EXCEPTION-technical: {total_tech}")
    print(f"  pairwise batch overlap    : 0 (all)")
    print(f"  catalog/prior overlap     : 0 (all batches)")
    print()
    for p in out_paths:
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
