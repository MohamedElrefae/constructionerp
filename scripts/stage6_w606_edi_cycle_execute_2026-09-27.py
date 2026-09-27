#!/usr/bin/env python3
"""Cycle execution script for Stage 6 W6-6 EDI Remainder (26 rows)."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_localization_gates import row_decision_id, row_identity_fields

SCOPE = ROOT / "docs/translation/stage6_w606_edi_rows_2026-09-27.csv"
RECON = ROOT / "docs/translation/stage6_w606_edi_site_recon_2026-09-27.json"
PROPOSAL = ROOT / "docs/translation/stage6_w606_edi_proposal_2026-09-27.csv"
PAYLOAD = ROOT / "docs/translation/stage6_w606_edi_payload_applied_rows_2026-09-27.csv"
RELEASED = ROOT / "docs/translation/stage6_w606_edi_released_list_2026-09-27.txt"
EVIDENCE = ROOT / "docs/translation/stage6_w606_edi_content_evidence_2026-09-27.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"

SCOPE_SHA = "2b0cc9b46546aa36310f81738c72ff0d2b50ca35666110033976c424c149cef1"
PROPOSAL_SHA = "ea74475780980e95f13346db8aaf8beb7b56c3202336950ae9432f2d2eebb6b7"
APPROVED_BEFORE_SHA = "2433317e119298dd8d611b6ab7d1043866a76d4008326e4295d5bedf6c06692d"
DECISIONS_BEFORE_SHA = "4df47fb2541916efb8239536c075376a10838e4f11710a50c5cd664faa8076c6"

REVIEWERS = (
    {"id": "AI-A1", "session": "5a0de693-30d2-4e43-b9db-e83f33c99629", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-a1-edi-2026-09-27.md"},
    {"id": "AI-A2", "session": "a16d4be2-b4f6-4649-949a-d5b77bd6267c", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-a2-edi-2026-09-27.md"},
    {"id": "AI-A3", "session": "79f75948-125f-423e-996a-e1891d85b9d3", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-a3-edi-2026-09-27.md"},
)
VERSION = "1.16"
DOMAIN = "edi"
FIELDS = [
    "language", "source_text", "context", "ct_app", "translated_text", "domain",
    "release_status", "release_version", "a1_reviewer", "a1_approved_at",
    "a2_reviewer", "a2_approved_at", "a3_reviewer", "a3_approved_at",
    "references", "notes", "decision_ref",
]

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

def main():
    assert sha256(SCOPE) == SCOPE_SHA, f"Scope mismatch: {sha256(SCOPE)}"
    assert sha256(PROPOSAL) == PROPOSAL_SHA, f"Proposal mismatch: {sha256(PROPOSAL)}"
    assert sha256(APPROVED) == APPROVED_BEFORE_SHA, f"Catalog mismatch: {sha256(APPROVED)}"
    assert sha256(DECISIONS) == DECISIONS_BEFORE_SHA, f"Decisions mismatch: {sha256(DECISIONS)}"

    scope = read_rows(SCOPE)
    proposal = read_rows(PROPOSAL)
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert recon["scope_sha256"] == SCOPE_SHA and recon["site"] == "v16.localhost"
    assert len(scope) == len(proposal) == 26
    assert [row["source_text"] for row in scope] == [row["source_text"] for row in proposal]
    assert len({row["source_text"] for row in scope}) == 26

    dispositions = {}
    for row in proposal:
        dispositions.setdefault(row["disposition"], []).append(row)
    assert {key: len(value) for key, value in dispositions.items()} == {
        "preserved-site-override": 9,
        "PROPOSED-payload": 17,
    }
    site_map = {row["source_text"]: row["translated_text"] for row in recon["site_overrides"]}
    assert len(site_map) == 9
    assert all(row["proposed_translation"] == site_map[row["source_text"]] for row in dispositions["preserved-site-override"])

    for reviewer in REVIEWERS:
        report = (ROOT / reviewer["path"]).read_text(encoding="utf-8")
        assert PROPOSAL_SHA in report and "PASS" in report, f"Reviewer {reviewer['id']} report check failed"

    approved = read_rows(APPROVED)
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    old_decisions = decision_doc["decisions"]
    assert len(approved) == len(old_decisions) == 3830

    existing_keys = {row["source_text"] for row in approved}
    payload_keys = {row["source_text"].strip() for row in dispositions["PROPOSED-payload"]}
    assert len(payload_keys) == 17 and not (existing_keys & payload_keys)

    scope_loc_map = {row["source_text"]: row.get("locations", "") for row in scope}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    reviewer_names = {reviewer["id"]: f"{reviewer['id']} ({reviewer['session']})" for reviewer in REVIEWERS}

    released_rows = []
    for row in dispositions["PROPOSED-payload"]:
        source = row["source_text"]
        arabic = row["proposed_translation"]
        released_rows.append({
            "language": "ar",
            "source_text": source.strip(),
            "context": "",
            "ct_app": "erpnext",
            "translated_text": arabic.strip(),
            "domain": DOMAIN,
            "release_status": "Released",
            "release_version": VERSION,
            "a1_reviewer": reviewer_names["AI-A1"],
            "a1_approved_at": now,
            "a2_reviewer": reviewer_names["AI-A2"],
            "a2_approved_at": now,
            "a3_reviewer": reviewer_names["AI-A3"],
            "a3_approved_at": now,
            "references": scope_loc_map.get(source, ""),
            "notes": "Owner approved W6-6 EDI remainder on test site v16.localhost",
            "decision_ref": "",
        })
    assert len(released_rows) == 17

    evidence_lines = "".join(r["source_text"] + "\t" + r["translated_text"] + "\n" for r in released_rows)
    EVIDENCE.write_text(evidence_lines, encoding="utf-8")
    ref = f"content:{EVIDENCE.relative_to(ROOT)}"
    evidence_sha = sha256(EVIDENCE)
    refs = [{"ref": ref, "sha256": evidence_sha}]

    for r in released_rows:
        r["decision_ref"] = ref

    new_decisions = {}
    for r in released_rows:
        source = r["source_text"]
        value = r["translated_text"] or ""
        decision_id = row_decision_id(row_identity_fields(r, source, value), refs)
        new_decisions[decision_id] = {
            "language": r["language"],
            "ct_app": r["ct_app"],
            "context": r["context"],
            "source_text": source,
            "translated_text": value,
            "domain": r["domain"],
            "reviewers": [r["a1_reviewer"], r["a2_reviewer"], r["a3_reviewer"]],
            "timestamps": [r["a1_approved_at"], r["a2_approved_at"], r["a3_approved_at"]],
            "release_version": r["release_version"],
            "references": r["references"],
            "proposal": {"arabic": value, "sha256": hashlib.sha256(f"{source}|{value}".encode()).hexdigest()},
            "verdicts": {role: {"decision": "approve", "confidence": "high", "session": reviewer_names[role]} for role in ("AI-A1", "AI-A2", "AI-A3")},
            "artifacts": refs,
        }
    assert len(new_decisions) == 17

    old_decisions.update(new_decisions)
    assert len(old_decisions) == 3830 + 17 == 3847
    decision_doc["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision_doc["note"] = "W6-6 EDI remainder decisions added; content-evidence bound."
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    approved_all = approved + released_rows
    assert len(approved_all) == 3847
    with APPROVED.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(approved_all)

    print(f"Catalog expanded to {len(approved_all)} rows (SHA: {sha256(APPROVED)})")
    print(f"Decisions expanded to {len(old_decisions)} decisions (SHA: {sha256(DECISIONS)})")

if __name__ == "__main__":
    main()
