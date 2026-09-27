#!/usr/bin/env python3
"""Cycle execution script for Stage 6 W6-7 Frappe Framework Remainder Batch 01 (250 rows)."""
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

SCOPE = ROOT / "docs/translation/stage6_w607_frappe_batch01_rows_2026-09-27.csv"
RECON = ROOT / "docs/translation/stage6_w607_frappe_batch01_site_recon_2026-09-27.json"
PROPOSAL = ROOT / "docs/translation/stage6_w607_frappe_batch01_proposal_2026-09-27.csv"
PAYLOAD = ROOT / "docs/translation/stage6_w607_frappe_batch01_payload_applied_rows_2026-09-27.csv"
RELEASED = ROOT / "docs/translation/stage6_w607_frappe_batch01_released_list_2026-09-27.txt"
EVIDENCE = ROOT / "docs/translation/stage6_w607_frappe_batch01_content_evidence_2026-09-27.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"

SCOPE_SHA = "43abe1b462c47b51c0209a0650511fac2ed32cdb5f3a585cde2e9468bfaab26a"
PROPOSAL_SHA = "f7de77ef4bbacb4385af64c89972b1e6c1b472bce0e00c8fcab30cc06763f54c"
APPROVED_BEFORE_SHA = "d8dd39618b980bb1d92a7ab9f030e7d0080889efc78635a6b7f1a6cf1714c980"
DECISIONS_BEFORE_SHA = "7474fc1314ca031fa3d461898718e38f70bb2fe279d58aa3d3ecc681f9454c51"

REVIEWERS = (
    {"id": "AI-A1", "session": "587ab6c8-7f50-4429-aa68-1eaa4577cc29", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w607-ai-a1-frappe-batch01-2026-09-27.md"},
    {"id": "AI-A2", "session": "94a20e4c-f986-47ca-bc06-624f0cdfd642", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w607-ai-a2-frappe-batch01-2026-09-27.md"},
    {"id": "AI-A3", "session": "23b5b2db-a2e8-44b6-966b-d2eb63a7ddaf", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w607-ai-a3-frappe-batch01-2026-09-27.md"},
)
VERSION = "1.17"
DOMAIN = "frappe"
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
    assert len(scope) == len(proposal) == 250
    assert [row["source_text"] for row in scope] == [row["source_text"] for row in proposal]
    assert len({row["source_text"] for row in scope}) == 250

    dispositions = {}
    for row in proposal:
        dispositions.setdefault(row["disposition"], []).append(row)
    assert {key: len(value) for key, value in dispositions.items()} == {
        "preserved-site-override": 1,
        "EXCEPTION-technical": 2,
        "PROPOSED-payload": 247,
    }
    site_map = {row["source_text"]: row["translated_text"] for row in recon["site_overrides"]}
    assert len(site_map) == 1
    assert all(row["proposed_translation"] == site_map[row["source_text"]] for row in dispositions["preserved-site-override"])

    for reviewer in REVIEWERS:
        report = (ROOT / reviewer["path"]).read_text(encoding="utf-8")
        assert PROPOSAL_SHA in report and "PASS" in report, f"Reviewer {reviewer['id']} report check failed"

    approved = read_rows(APPROVED)
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    old_decisions = decision_doc["decisions"]
    assert len(approved) == len(old_decisions) == 3847

    existing_keys = {row["source_text"] for row in approved}
    payload_keys = {row["source_text"].strip() for row in dispositions["PROPOSED-payload"]}
    assert len(payload_keys) == 247 and not (existing_keys & payload_keys)

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
            "context": (row.get("context") or "").strip(),
            "ct_app": "frappe",
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
            "references": scope_loc_map.get(source, "").strip(),
            "notes": "Owner approved W6-7 Frappe framework Batch 01 on test site v16.localhost",
            "decision_ref": "",
        })
    assert len(released_rows) == 247

    # Applied payload rows (exact 250 rows matching scope)
    applied_rows = []
    for row in proposal:
        disp = row["disposition"]
        if disp == "PROPOSED-payload":
            final_disp = "quorum-confirmed (release payload row)"
            arabic = row["proposed_translation"]
            applied = "YES (released to catalog)"
        elif disp == "preserved-site-override":
            final_disp = "preserved-site-override (not imported, plan §12)"
            arabic = row["proposed_translation"]
            applied = "PRESERVED (site override untouched)"
        else:
            final_disp = "EXCEPTION-technical (keep vendor rendering; no translation)"
            arabic = ""
            applied = "NO (technical exclusion)"

        applied_rows.append({
            "source_text": row["source_text"],
            "context": row.get("context", ""),
            "proposed_translation": row["proposed_translation"],
            "final_translation": arabic,
            "final_disposition": final_disp,
            "applied": applied,
            "review_comments": row.get("review_comments", ""),
        })

    with PAYLOAD.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(applied_rows[0].keys()))
        writer.writeheader()
        writer.writerows(applied_rows)

    RELEASED.write_text("\n".join(row["source_text"] for row in released_rows) + "\n", encoding="utf-8")
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
    assert len(new_decisions) == 247

    old_decisions.update(new_decisions)
    assert len(old_decisions) == 3847 + 247 == 4094
    decision_doc["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision_doc["note"] = "W6-7 Frappe framework Batch 01 decisions added; content-evidence bound."
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    approved_all = approved + released_rows
    assert len(approved_all) == 4094
    with APPROVED.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(approved_all)

    print(f"Cycle execution complete:")
    print(f"  Payload rows: {PAYLOAD} ({len(applied_rows)} rows, sha256: {sha256(PAYLOAD)})")
    print(f"  Released list: {RELEASED} ({len(released_rows)} rows, sha256: {sha256(RELEASED)})")
    print(f"  Content evidence: {EVIDENCE} ({len(released_rows)} rows, sha256: {evidence_sha})")
    print(f"  Catalog: {APPROVED} ({len(approved_all)} rows, sha256: {sha256(APPROVED)})")
    print(f"  Decisions: {DECISIONS} ({len(old_decisions)} decisions, sha256: {sha256(DECISIONS)})")


if __name__ == "__main__":
    main()
