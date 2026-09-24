"""Build W6-6 Manufacturing Batch 01 release artifacts after unanimous A1/A2/A3 PASS.

This script mutates only the repository catalog, decision bundle, and batch
evidence CSVs. It does not connect to Frappe or touch any site.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_localization_gates import row_decision_id

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w606_manufacturing_batch01_rows_2026-09-24.csv"
RECON = HERE / "stage6_w606_manufacturing_batch01_site_recon_2026-09-24.json"
PROPOSAL = HERE / "stage6_w606_manufacturing_batch01_proposal_2026-09-24.csv"
PAYLOAD = HERE / "stage6_w606_manufacturing_batch01_payload_applied_rows_2026-09-24.csv"
RELEASED = HERE / "stage6_w606_manufacturing_batch01_released_list_2026-09-24.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"

SCOPE_SHA = "0d5098f61e2f97d26fa40e4e8b5d3b90ab1ec22e9dafd543564cb07ec8d39286"
PROPOSAL_SHA = "d64adaa6f9d6d201623dfbd4156dd414c000abd389d3864643994aba3bbfdfb9"
APPROVED_BEFORE_SHA = "b68f75eaee334edde2a8173f459e33fad802578c236e9a5019deb26ebd5daf5a"
DECISIONS_BEFORE_SHA = "72a633b8f2084dfdf0f5f986a7498a9769ec7eba10fc31742d90accdc588c8d7"

REVIEWERS = (
    {
        "id": "AI-A1", "session": "51113ce4-c69b-422f-ab6c-9f6da5ab6147",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch01-ai-a1-2026-09-24.md",
    },
    {
        "id": "AI-A2", "session": "42622638-757d-4ee6-9e38-833fc79d38af",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch01-ai-a2-2026-09-24.md",
    },
    {
        "id": "AI-A3", "session": "5d95d7bc-8806-4df9-a822-4e1f8081d3fe",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch01-ai-a3-2026-09-24.md",
    },
)
VERSION = "1.8"
DOMAIN = "manufacturing"
FIELDS = [
    "language", "source_text", "context", "ct_app", "translated_text", "domain",
    "release_status", "release_version", "a1_reviewer", "a1_approved_at",
    "a2_reviewer", "a2_approved_at", "a3_reviewer", "a3_approved_at",
    "references", "notes", "decision_ref",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert sha256(SCOPE) == SCOPE_SHA
    assert sha256(PROPOSAL) == PROPOSAL_SHA
    assert sha256(APPROVED) == APPROVED_BEFORE_SHA
    assert sha256(DECISIONS) == DECISIONS_BEFORE_SHA

    scope, proposal = read_rows(SCOPE), read_rows(PROPOSAL)
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert recon["site"] == "v16.localhost" and recon["scope_sha256"] == SCOPE_SHA
    assert len(scope) == len(proposal) == 250

    reviewer_names = {
        r["id"]: f"{r['id']} ({r['session']})"
        for r in REVIEWERS
    }
    for reviewer in REVIEWERS:
        p = ROOT / reviewer["path"]
        assert p.exists(), f"missing review record {p}"
        text = p.read_text(encoding="utf-8")
        assert "PASS" in text and reviewer["session"] in text, f"unverified review in {p}"

    approved_rows = read_rows(APPROVED)
    assert len(approved_rows) == 3161
    existing_keys = {row["source_text"] for row in approved_rows}

    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    old_decisions = decision_doc["decisions"]
    assert len(old_decisions) == 3161

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    released, applied = [], []
    for row in proposal:
        source, arabic = row["source_text"], row["proposed_ar"]
        disposition = row["proposed_disposition"]
        if disposition == "PROPOSED-payload":
            assert source not in existing_keys, f"payload collision {source}"
            released.append({
                "language": "ar", "source_text": source, "context": "", "ct_app": "erpnext",
                "translated_text": arabic,
                "domain": DOMAIN, "release_status": "Released", "release_version": VERSION,
                "a1_reviewer": reviewer_names["AI-A1"], "a1_approved_at": now,
                "a2_reviewer": reviewer_names["AI-A2"], "a2_approved_at": now,
                "a3_reviewer": reviewer_names["AI-A3"], "a3_approved_at": now,
                "references": "glossary v2.0; vendor manufacturing PO locations; plan D5; W6-6 manufacturing batch-01",
                "notes": (
                    "AI draft; independent A1/A2/A3 PASS bound to proposal SHA "
                    + PROPOSAL_SHA + "; owner-approved scope SHA " + SCOPE_SHA
                ),
                "decision_ref": f"content:{PAYLOAD.relative_to(ROOT)}",
            })
            applied_disposition = "quorum-confirmed-payload"
        else:
            applied_disposition = "preserved-site-override (not imported, plan §12)"
        applied.append({
            "source_text": source,
            "translated_text": arabic,
            "quorum_decision": applied_disposition,
            "disposition_rationale": row["disposition_rationale"],
            "decision_ref": "stage6-W6-6 Manufacturing Batch 01 owner-approved 2026-09-24",
            "proposal_sha256": PROPOSAL_SHA,
        })

    assert len(released) == 83 and len(applied) == 250
    with PAYLOAD.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(applied[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(applied)
    RELEASED.write_text("".join(row["source_text"] + "\n" for row in released), encoding="utf-8")

    payload_ref = f"content:{PAYLOAD.relative_to(ROOT)}"
    payload_hash = sha256(PAYLOAD)
    refs = [{"ref": payload_ref, "sha256": payload_hash}]
    for row in released:
        src, val = row["source_text"], row["translated_text"]
        proposal_hash = hashlib.sha256(f"{src}|{val}".encode("utf-8")).hexdigest()
        ident_parts = [
            row["language"], row["ct_app"], row["context"], src, val,
            row["a1_reviewer"], row["a1_approved_at"], row["a2_reviewer"], row["a2_approved_at"],
            row["a3_reviewer"], row["a3_approved_at"], row["release_version"], row["domain"],
            row["references"], proposal_hash,
        ]
        decision_id = row_decision_id(ident_parts, refs)
        assert decision_id not in old_decisions
        old_decisions[decision_id] = {
            "language": row["language"], "ct_app": row["ct_app"], "context": row["context"],
            "source_text": src, "translated_text": val, "domain": row["domain"],
            "reviewers": [row["a1_reviewer"], row["a2_reviewer"], row["a3_reviewer"]],
            "timestamps": [row["a1_approved_at"], row["a2_approved_at"], row["a3_approved_at"]],
            "release_version": row["release_version"], "references": row["references"],
            "proposal": {"arabic": val, "sha256": proposal_hash},
            "verdicts": {
                reviewer["id"]: {
                    "decision": "approve", "confidence": "high", "session": reviewer["session"],
                }
                for reviewer in REVIEWERS
            },
            "artifacts": refs,
        }

    with APPROVED.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writerows(released)
    decision_doc["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision_doc["note"] = (
        "Historical decisions retained; W6-6 Manufacturing Batch 01 additions bind 83 released rows to "
        "the exact proposal SHA and independent A1/A2/A3 PASS."
    )
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"scope=250 preserve=167 released={len(released)}")
    print(f"catalog=3161+{len(released)}={len(approved_rows) + len(released)}")
    print(f"payload_sha256={payload_hash}")
    print(f"released_list_sha256={sha256(RELEASED)}")
    print(f"approved_csv_sha256={sha256(APPROVED)}")
    print(f"release_decisions_sha256={sha256(DECISIONS)}")


if __name__ == "__main__":
    main()
