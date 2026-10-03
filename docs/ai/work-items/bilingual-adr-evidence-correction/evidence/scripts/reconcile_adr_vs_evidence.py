#!/usr/bin/env python3
"""Reconcile every row of bilingual-performance-sla.md §4 against its cited evidence.

Run from the app root (apps/construction):

    python3 docs/ai/work-items/bilingual-adr-evidence-correction/evidence/scripts/reconcile_adr_vs_evidence.py

Walks the §4 table, locates a source artefact for each DocType across every work item's
evidence tree (including nested raw-logs/ paths), recomputes the ratio from the artefact
and reports any row that does not match its own evidence.

Exit code 0 when all rows reconcile, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[6]
ADR = APP_ROOT / "docs" / "ai" / "work-items" / "bilingual-performance-sla.md"
EVIDENCE_ROOT = APP_ROOT / "docs" / "ai" / "work-items"
ROW_RE = re.compile(r"^\|\s*(?P<doctype>[^|]+?)\s*\|\s*(?P<base>[0-9.]+)\s*ms\s*\|")
SECTION4 = "## 4. Measured state"
RATIO_TOLERANCE = 5e-4


def normalise_doctype(cell: str) -> str:
    return re.sub(r"\s*\(\d+ rows\)\s*$", "", cell).strip()


def artefacts() -> list[Path]:
    return sorted(
        p
        for p in EVIDENCE_ROOT.rglob("*.json")
        if p.name != "MANIFEST.json" and p.is_file()
    )


def doctype_result(payload: object) -> dict[str, tuple[float, float]]:
    """Map doctype -> (baseline_p95_ms, bilingual_p95_ms) found in one artefact."""
    found: dict[str, tuple[float, float]] = {}
    if not isinstance(payload, dict):
        return found

    if {"measured_baseline_p95_ms", "measured_bilingual_p95_ms"} <= payload.keys():
        found["Account"] = (
            float(payload["measured_baseline_p95_ms"]),
            float(payload["measured_bilingual_p95_ms"]),
        )

    result = payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("baseline"), dict):
        bilingual = result.get("bilingual") or result.get("governed") or {}
        base = result["baseline"].get("p95_ms")
        gov = bilingual.get("p95_ms")
        if isinstance(base, (int, float)) and isinstance(gov, (int, float)):
            name = result.get("doctype")
            if isinstance(name, str) and name:
                found[name] = (float(base), float(gov))

    results = payload.get("results")
    if isinstance(results, dict):
        for name, entry in results.items():
            if not isinstance(entry, dict):
                continue
            baseline = entry.get("baseline") or {}
            bilingual = entry.get("bilingual") or entry.get("governed") or {}
            base = baseline.get("p95_ms")
            gov = bilingual.get("p95_ms")
            if isinstance(base, (int, float)) and isinstance(gov, (int, float)):
                found[name] = (float(base), float(gov))

    return found


def load_index() -> dict[str, tuple[float, float, Path]]:
    index: dict[str, tuple[float, float, Path]] = {}
    for path in artefacts():
        try:
            payload = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        for name, (base, gov) in doctype_result(payload).items():
            # First artefact wins: §7 lists sources in the order they bind rows.
            index.setdefault(name, (base, gov, path))
    return index


def section4_rows() -> list[tuple[str, float, float, float]]:
    text = ADR.read_text()
    start = text.index(SECTION4)
    rows = []
    for line in text[start:].splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        match = ROW_RE.match(line)
        if not match:
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        rows.append(
            (
                normalise_doctype(cells[0]),
                float(cells[1].replace(" ms", "")),
                float(cells[2].replace(" ms", "")),
                float(cells[3]),
            )
        )
    return rows


def main() -> int:
    index = load_index()
    rows = section4_rows()
    print(f"ADR: {ADR.relative_to(APP_ROOT)}")
    print(f"§4 rows parsed: {len(rows)}")
    print(f"artefacts indexed: {len(artefacts())}")
    print()

    missing, mismatched, reconciled = [], [], []
    for doctype, adr_base, adr_gov, adr_ratio in rows:
        if doctype not in index:
            missing.append(doctype)
            print(f"  MISSING  {doctype}: no evidence artefact found")
            continue
        base, gov, source = index[doctype]
        ratio = gov / base
        problems = []
        if abs(adr_base - base) > 1e-9:
            problems.append(f"baseline {adr_base} != evidence {base}")
        if abs(adr_gov - gov) > 1e-9:
            problems.append(f"governed {adr_gov} != evidence {gov}")
        if abs(adr_ratio - ratio) > RATIO_TOLERANCE:
            problems.append(f"ratio {adr_ratio} != evidence {ratio:.4f}")
        if problems:
            mismatched.append(doctype)
            print(f"  MISMATCH {doctype}: {'; '.join(problems)}")
            print(f"           source: {source.relative_to(APP_ROOT)}")
        else:
            reconciled.append(doctype)
            print(f"  OK       {doctype}: {adr_base}/{adr_gov}/{adr_ratio} == {base}/{gov}/{ratio:.4f}")

    print()
    print(f"reconciled: {len(reconciled)}/{len(rows)}")
    print(f"mismatched: {len(mismatched)}")
    print(f"unsourced : {len(missing)}")
    if mismatched or missing:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS - every §4 row matches the evidence artefact it cites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
