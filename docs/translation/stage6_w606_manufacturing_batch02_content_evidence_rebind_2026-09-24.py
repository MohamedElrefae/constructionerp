"""Rebind Batch 02 decision provenance to literal, quote-safe content evidence."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_localization_gates import row_decision_id, row_identity_fields

HERE = Path(__file__).resolve().parent
CATALOG = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"
PAYLOAD = HERE / "stage6_w606_manufacturing_batch02_payload_applied_rows_2026-09-24.csv"
EVIDENCE = HERE / "stage6_w606_manufacturing_batch02_content_evidence_2026-09-24.txt"
EXPECTED_CATALOG_SHA = "5156740cdc937d164dba17f12166f83bc1990f47ddcc9827dd00de8635f14f2f"
EXPECTED_DECISIONS_SHA = "a8baa5e7c89604f048c787ac2b49cc83dd7583d129ef7711a7b19f31958ef62d"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert sha(CATALOG) == EXPECTED_CATALOG_SHA
    assert sha(DECISIONS) == EXPECTED_DECISIONS_SHA
    payload = list(csv.DictReader(PAYLOAD.open(encoding="utf-8", newline="")))
    released = [row for row in payload if row["quorum_decision"] == "quorum-confirmed-payload"]
    assert len(released) == 82
    EVIDENCE.write_text(
        "".join(row["source_text"] + "\t" + row["translated_text"] + "\n" for row in released),
        encoding="utf-8",
    )
    ref = f"content:{EVIDENCE.relative_to(ROOT)}"
    refs = [{"ref": ref, "sha256": sha(EVIDENCE)}]

    catalog_rows = list(csv.DictReader(CATALOG.open(encoding="utf-8", newline="")))
    batch_keys = {row["source_text"] for row in released}
    rows_by_key = {row["source_text"]: row for row in catalog_rows if row["release_version"] == "1.9"}
    assert set(rows_by_key) == batch_keys
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    decisions = decision_doc["decisions"]
    for decision_id, decision in list(decisions.items()):
        if decision.get("release_version") == "1.9" and decision.get("source_text") in batch_keys:
            del decisions[decision_id]

    rebuilt = {}
    for row in catalog_rows:
        if row["release_version"] != "1.9":
            continue
        row["decision_ref"] = ref
        src = (row["source_text"] or "").strip()
        val = row["translated_text"] or ""
        decision_id = row_decision_id(row_identity_fields(row, src, val), refs)
        rebuilt[decision_id] = {
            "language": row["language"], "ct_app": row["ct_app"], "context": row["context"],
            "source_text": src, "translated_text": val, "domain": row["domain"],
            "reviewers": [row["a1_reviewer"], row["a2_reviewer"], row["a3_reviewer"]],
            "timestamps": [row["a1_approved_at"], row["a2_approved_at"], row["a3_approved_at"]],
            "release_version": row["release_version"], "references": row["references"],
            "proposal": {"arabic": val, "sha256": hashlib.sha256(f"{src}|{val}".encode()).hexdigest()},
            "verdicts": {
                role: {"decision": "approve", "confidence": "high", "session": session}
                for role, session in (
                    ("AI-A1", "/root/w606b02_a1_rev"),
                    ("AI-A2", "/root/w606b02_a2_rev"),
                    ("AI-A3", "/root/w606b02_a3_final"),
                )
            },
            "artifacts": refs,
        }
    assert len(rebuilt) == 82
    decisions.update(rebuilt)

    with CATALOG.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(catalog_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(catalog_rows)
    decision_doc["generated_utc"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision_doc["note"] = (
        "Historical decisions retained; W6-6 Manufacturing Batch 02 decisions bind to the literal "
        "quote-safe text evidence artifact, exact proposal/scope hashes, and A1/A2/A3 PASS."
    )
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"literal_content_evidence_sha256={sha(EVIDENCE)}")
    print(f"catalog_sha256={sha(CATALOG)}")
    print(f"decisions_sha256={sha(DECISIONS)}")


if __name__ == "__main__":
    main()
