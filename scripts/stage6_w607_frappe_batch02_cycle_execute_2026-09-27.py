#!/usr/bin/env python3
"""Cycle execution script for Stage 6 W6-7 Frappe Framework Remainder Batch 02 (244 rows)."""
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

SCOPE = ROOT / "docs/translation/stage6_w607_frappe_batch02_rows_2026-09-27.csv"
RECON = ROOT / "docs/translation/stage6_w607_frappe_batch02_site_recon_2026-09-27.json"
PROPOSAL = ROOT / "docs/translation/stage6_w607_frappe_batch02_proposal_2026-09-27.csv"
PAYLOAD = ROOT / "docs/translation/stage6_w607_frappe_batch02_payload_applied_rows_2026-09-27.csv"
RELEASED = ROOT / "docs/translation/stage6_w607_frappe_batch02_released_list_2026-09-27.txt"
EVIDENCE = ROOT / "docs/translation/stage6_w607_frappe_batch02_content_evidence_2026-09-27.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"

SCOPE_SHA = "cd6536bc0cb0b9db14214e55500ebadf3a525b2a1250147b9ad9b402e1e70be3"
PROPOSAL_SHA = "ec58c9c43f6708ae821e1eee404fd2207d4b5d65d323c14f14d93a7c69555b4a"
APPROVED_BEFORE_SHA = "f3910fb4dd4433ce583e92b710d987ce0cb2329b6d48aed1ea4895f51c8c24b2"
DECISIONS_BEFORE_SHA = "37150b52f9614241a104ddc173d79074e88fee1ba93792b19e66a3aa33bdc3b4"

REVIEWERS = (
    {"id": "AI-A1", "session": "2084d87f-bf94-4c45-8eae-b167b3a80d25", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w607-ai-a1-frappe-batch02-2026-09-27.md"},
    {"id": "AI-A2", "session": "99cc583c-8b64-45f0-8efe-8d7b1c0fe54c", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w607-ai-a2-frappe-batch02-2026-09-27.md"},
    {"id": "AI-A3", "session": "d37160b9-a204-4c6d-847f-76ac6548ca02", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w607-ai-a3-frappe-batch02-2026-09-27.md"},
)
VERSION = "1.18"
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
    assert len(scope) == len(proposal) == 244
    assert [row["source_text"] for row in scope] == [row["source_text"] for row in proposal]
    assert len({row["source_text"] for row in scope}) == 244

    dispositions = {}
    for row in proposal:
        dispositions.setdefault(row["disposition"], []).append(row)
    assert {key: len(value) for key, value in dispositions.items()} == {
        "EXCEPTION-technical": 1,
        "PROPOSED-payload": 243,
    }

    for reviewer in REVIEWERS:
        report = (ROOT / reviewer["path"]).read_text(encoding="utf-8")
        assert PROPOSAL_SHA in report and "PASS" in report, f"Reviewer {reviewer['id']} report check failed"

    approved = read_rows(APPROVED)
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    old_decisions = decision_doc["decisions"]
    assert len(approved) == len(old_decisions) == 4094

    existing_keys = {row["source_text"] for row in approved}
    payload_keys = {row["source_text"].strip() for row in dispositions["PROPOSED-payload"]}
    assert len(payload_keys) == 243 and not (existing_keys & payload_keys)

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
            "notes": "Owner approved W6-7 Frappe framework Batch 02 on test site v16.localhost",
            "decision_ref": "",
        })
    assert len(released_rows) == 243

    # Applied payload rows (exact 244 rows matching scope)
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
    assert len(new_decisions) == 243

    old_decisions.update(new_decisions)
    assert len(old_decisions) == 4094 + 243 == 4337
    decision_doc["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision_doc["note"] = "W6-7 Frappe framework Batch 02 decisions added; content-evidence bound."
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    approved_all = approved + released_rows
    assert len(approved_all) == 4337
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
