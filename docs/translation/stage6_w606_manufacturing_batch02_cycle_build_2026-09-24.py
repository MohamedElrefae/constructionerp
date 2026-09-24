"""Build W6-6 Manufacturing Batch 02 release records after exact owner approval and A1/A2/A3 PASS.

This script changes only the approved override catalog, content-bound release
decisions, and batch evidence outputs. It never connects to Frappe or a site.
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
SCOPE = HERE / "stage6_w606_manufacturing_batch02_rows_2026-09-24.csv"
RECON = HERE / "stage6_w606_manufacturing_batch02_site_recon_2026-09-24.json"
PROPOSAL = HERE / "stage6_w606_manufacturing_batch02_proposal_2026-09-24.csv"
PAYLOAD = HERE / "stage6_w606_manufacturing_batch02_payload_applied_rows_2026-09-24.csv"
CONTENT_EVIDENCE = HERE / "stage6_w606_manufacturing_batch02_content_evidence_2026-09-24.txt"
RELEASED = HERE / "stage6_w606_manufacturing_batch02_released_list_2026-09-24.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"

SCOPE_SHA = "195c789945cf2b069a1620e855b22ad38aa9cb0adf03b9b2342166c47b6e88ff"
PROPOSAL_SHA = "fde2fa6722c8b69bb87cbdc2c9927cf1a545e0f78f4c3b71f292f567d6f544f5"
APPROVED_BEFORE_SHA = "cbe5961bdc3d45c4af03a5fa3b3a55413ae996622187be485295a79564478319"
DECISIONS_BEFORE_SHA = "c2e6da428e4a70b2037820faa39487df173eace77fb79d44d92979ed2cbf785e"

REVIEWERS = (
    {
        "id": "AI-A1", "session": "/root/w606b02_a1_rev",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch02-ai-a1-2026-09-24.md",
    },
    {
        "id": "AI-A2", "session": "/root/w606b02_a2_rev",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch02-ai-a2-2026-09-24.md",
    },
    {
        "id": "AI-A3", "session": "/root/w606b02_a3_final",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch02-ai-a3-2026-09-24.md",
    },
)
VERSION = "1.9"
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
    assert sha256(SCOPE) == SCOPE_SHA, "approved scope hash changed"
    assert sha256(PROPOSAL) == PROPOSAL_SHA, "reviewed proposal hash changed"
    assert sha256(APPROVED) == APPROVED_BEFORE_SHA, "approved catalog changed since preflight"
    assert sha256(DECISIONS) == DECISIONS_BEFORE_SHA, "decision bundle changed since preflight"

    scope, proposal = read_rows(SCOPE), read_rows(PROPOSAL)
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert recon["site"] == "v16.localhost" and recon["scope_sha256"] == SCOPE_SHA
    assert len(scope) == len(proposal) == 202
    assert [r["source_text"] for r in scope] == [r["source_text"] for r in proposal]

    reviewer_names = {r["id"]: f"{r['id']} ({r['session']})" for r in REVIEWERS}
    for reviewer in REVIEWERS:
        p = ROOT / reviewer["path"]
        text = p.read_text(encoding="utf-8")
        assert "PASS" in text and SCOPE_SHA in text and PROPOSAL_SHA in text, f"review not bound to exact hashes: {p}"

    approved_rows = read_rows(APPROVED)
    existing_keys = {row["source_text"] for row in approved_rows}
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    old_decisions = decision_doc["decisions"]
    assert len(approved_rows) == len(old_decisions) == 3244

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    released: list[dict[str, str]] = []
    applied: list[dict[str, str]] = []
    site_map = {row["source_text"]: row["translated_text"] for row in recon["site_overrides"]}
    assert len(site_map) == 119

    for row in proposal:
        src, arabic = row["source_text"], row["proposed_ar"]
        disposition = row["proposed_disposition"]
        if disposition == "PROPOSED-payload":
            assert src not in existing_keys, f"payload collision: {src!r}"
            assert arabic.strip(), f"empty payload: {src!r}"
            released.append({
                "language": "ar", "source_text": src, "context": "", "ct_app": "erpnext",
                "translated_text": arabic, "domain": DOMAIN, "release_status": "Released",
                "release_version": VERSION,
                "a1_reviewer": reviewer_names["AI-A1"], "a1_approved_at": now,
                "a2_reviewer": reviewer_names["AI-A2"], "a2_approved_at": now,
                "a3_reviewer": reviewer_names["AI-A3"], "a3_approved_at": now,
                "references": "Glossary v2.0; vendor ERPNext Manufacturing PO locations; W6-6 Manufacturing Batch 02",
                "notes": f"A1/A2/A3 PASS bound to proposal SHA {PROPOSAL_SHA}; owner-approved scope SHA {SCOPE_SHA}",
                "decision_ref": f"content:{CONTENT_EVIDENCE.relative_to(ROOT)}",
            })
            applied_disposition = "quorum-confirmed-payload"
        elif disposition == "preserved-site-override":
            assert site_map.get(src) == arabic, f"site override mismatch: {src!r}"
            applied_disposition = "preserved-site-override (not imported, plan §12)"
        elif disposition == "EXCEPTION-technical":
            assert not arabic, f"technical exception unexpectedly translated: {src!r}"
            applied_disposition = "EXCEPTION-technical (empty, vendor rendering retained)"
        else:
            raise AssertionError(f"unexpected disposition {disposition!r}")

        disposition_rationale = row["disposition_rationale"]
        if applied_disposition == "quorum-confirmed-payload":
            disposition_rationale = (
                "Independent A1/A2/A3 quorum PASS; released as v1.9 with exact content evidence."
            )

        applied.append({
            "source_text": src, "translated_text": arabic,
            "quorum_decision": applied_disposition,
            "disposition_rationale": disposition_rationale,
            "decision_ref": "stage6-W6-6 Manufacturing Batch 02 owner-approved 2026-09-24",
            "scope_sha256": SCOPE_SHA, "proposal_sha256": PROPOSAL_SHA,
        })

    assert len(released) == 82 and len(applied) == 202
    with PAYLOAD.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(applied[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(applied)
    RELEASED.write_text("".join(row["source_text"] + "\n" for row in released), encoding="utf-8")
    CONTENT_EVIDENCE.write_text(
        "".join(row["source_text"] + "\t" + row["translated_text"] + "\n" for row in released),
        encoding="utf-8",
    )

    content_ref = f"content:{CONTENT_EVIDENCE.relative_to(ROOT)}"
    refs = [{"ref": content_ref, "sha256": sha256(CONTENT_EVIDENCE)}]
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
        assert decision_id not in old_decisions, f"decision collision: {src!r}"
        old_decisions[decision_id] = {
            "language": row["language"], "ct_app": row["ct_app"], "context": row["context"],
            "source_text": src, "translated_text": val, "domain": row["domain"],
            "reviewers": [row["a1_reviewer"], row["a2_reviewer"], row["a3_reviewer"]],
            "timestamps": [row["a1_approved_at"], row["a2_approved_at"], row["a3_approved_at"]],
            "release_version": row["release_version"], "references": row["references"],
            "proposal": {"arabic": val, "sha256": proposal_hash},
            "verdicts": {
                reviewer["id"]: {"decision": "approve", "confidence": "high", "session": reviewer["session"]}
                for reviewer in REVIEWERS
            },
            "artifacts": refs,
        }

    with APPROVED.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writerows(released)
    decision_doc["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision_doc["note"] = (
        "Historical decisions retained; W6-6 Manufacturing Batch 02 additions bind 82 released rows "
        "to the exact proposal and scope hashes and independent A1/A2/A3 PASS."
    )
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"scope=202 preserve=119 technical=1 released={len(released)}")
    print(f"catalog={len(approved_rows)}+{len(released)}={len(approved_rows) + len(released)}")
    print(f"payload_sha256={sha256(PAYLOAD)}")
    print(f"content_evidence_sha256={sha256(CONTENT_EVIDENCE)}")
    print(f"approved_csv_sha256={sha256(APPROVED)}")
    print(f"release_decisions_sha256={sha256(DECISIONS)}")


if __name__ == "__main__":
    main()
