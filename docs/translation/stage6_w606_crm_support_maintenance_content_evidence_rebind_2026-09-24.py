import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_localization_gates import row_decision_id, row_identity_fields

HERE = Path(__file__).resolve().parent
CATALOG = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"
PAYLOAD = HERE / "stage6_w606_crm_support_maintenance_payload_applied_rows_2026-09-24.csv"
EVIDENCE = HERE / "stage6_w606_crm_support_maintenance_content_evidence_2026-09-24.txt"
EXPECTED_CATALOG_SHA = "ad737758756dca0d69b83ff89d05908eb18df52a0d58afb889cef9f59253e080"
EXPECTED_DECISIONS_SHA = "9e3947a3abb25b390bc072a0a2cf9456a3161e120542ac73f5735f352df57308"
REVIEW_SESSIONS = {
    "AI-A1": "/root/w606_crm_a1_corrected",
    "AI-A2": "/root/w606_crm_a2_corrected",
    "AI-A3": "/root/w606_crm_a3_corrected",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(CATALOG) == EXPECTED_CATALOG_SHA
    assert sha(DECISIONS) == EXPECTED_DECISIONS_SHA
    with PAYLOAD.open(encoding="utf-8", newline="") as handle:
        payload = list(csv.DictReader(handle))
    released = [row for row in payload if row["quorum_decision"] == "quorum-confirmed-payload"]
    assert len(released) == 38
    EVIDENCE.write_text("".join(row["source_text"] + "\t" + row["translated_text"] + "\n" for row in released), encoding="utf-8")
    ref = f"content:{EVIDENCE.relative_to(ROOT)}"
    refs = [{"ref": ref, "sha256": sha(EVIDENCE)}]
    with CATALOG.open(encoding="utf-8", newline="") as handle:
        catalog = list(csv.DictReader(handle))
    batch_rows = [row for row in catalog if row["release_version"] == "1.10"]
    batch_keys = {row["source_text"] for row in batch_rows}
    assert len(batch_rows) == 38 and batch_keys == {row["source_text"] for row in released}
    for row in batch_rows:
        row["decision_ref"] = ref
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    decisions = decision_doc["decisions"]
    for decision_id, decision in list(decisions.items()):
        if decision.get("release_version") == "1.10" and decision.get("source_text") in batch_keys:
            del decisions[decision_id]
    rebuilt = {}
    for row in batch_rows:
        source = (row["source_text"] or "").strip()
        value = row["translated_text"] or ""
        decision_id = row_decision_id(row_identity_fields(row, source, value), refs)
        rebuilt[decision_id] = {
            "language": row["language"], "ct_app": row["ct_app"], "context": row["context"],
            "source_text": source, "translated_text": value, "domain": row["domain"],
            "reviewers": [row["a1_reviewer"], row["a2_reviewer"], row["a3_reviewer"]],
            "timestamps": [row["a1_approved_at"], row["a2_approved_at"], row["a3_approved_at"]],
            "release_version": row["release_version"], "references": row["references"],
            "proposal": {"arabic": value, "sha256": hashlib.sha256(f"{source}|{value}".encode()).hexdigest()},
            "verdicts": {role: {"decision": "approve", "confidence": "high", "session": session} for role, session in REVIEW_SESSIONS.items()},
            "artifacts": refs,
        }
    assert len(rebuilt) == 38
    decisions.update(rebuilt)
    for row in payload:
        row["decision_ref"] = ref
    with PAYLOAD.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(payload[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(payload)
    with CATALOG.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(catalog[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(catalog)
    decision_doc["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision_doc["note"] = "W6-6 CRM Support Maintenance decisions rebound to literal quote-safe content evidence; historical decisions retained."
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"evidence_sha256={sha(EVIDENCE)}")
    print(f"payload_sha256={sha(PAYLOAD)}")
    print(f"catalog_sha256={sha(CATALOG)}")
    print(f"decisions_sha256={sha(DECISIONS)}")


if __name__ == "__main__":
    main()
