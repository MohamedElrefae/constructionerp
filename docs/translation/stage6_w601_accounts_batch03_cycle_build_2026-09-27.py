"""Cycle build for W6-1 Accounts Batch 03."""
from __future__ import annotations

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
SCOPE = HERE / "stage6_w601_accounts_batch03_rows_2026-09-27.csv"
RECON = HERE / "stage6_w601_accounts_batch03_site_recon_2026-09-27.json"
PROPOSAL = HERE / "stage6_w601_accounts_batch03_proposal_2026-09-27.csv"
PAYLOAD = HERE / "stage6_w601_accounts_batch03_payload_applied_rows_2026-09-27.csv"
RELEASED = HERE / "stage6_w601_accounts_batch03_released_list_2026-09-27.txt"
EVIDENCE = HERE / "stage6_w601_accounts_batch03_content_evidence_2026-09-27.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"

SCOPE_SHA = "dfa6de55bb986c5e7b6fc845ad9b3de7de2a0f6c38c441cf4cf2c8427713d1cb"
PROPOSAL_SHA = "3b0a3ee8d6c9b6a1c59d925aea5c2ed71059c07698e1935c9c65b385c464ef3f"
APPROVED_BEFORE_SHA = "2b6b23b8212ae62227991d1476c31131cc3cefda085bc58f762e87916aa23742"
DECISIONS_BEFORE_SHA = "3ff383df0fe3a22bd1abda85e53ef227272dd866ff6770fbdcf9eb8fc4369a39"

REVIEWERS = (
    {"id": "AI-A1", "session": "a8debbe7-3010-4713-92b1-11cffe5ea669", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a1-accounts-batch03-2026-09-27.md"},
    {"id": "AI-A2", "session": "debd9c14-4113-4c69-a8d3-e2fd95c1758e", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a2-accounts-batch03-2026-09-27.md"},
    {"id": "AI-A3", "session": "7decf874-c2c4-44a6-922d-84c9a574341c", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a3-accounts-batch03-2026-09-27.md"},
)
VERSION = "1.13"
DOMAIN = "accounts"
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
        dispositions.setdefault(row["proposed_disposition"], []).append(row)
    assert {key: len(value) for key, value in dispositions.items()} == {
        "preserved-site-override": 128,
        "PROPOSED-payload": 121,
        "EXCEPTION-technical": 1,
    }
    site_map = {row["source_text"]: row["translated_text"] for row in recon["site_overrides"]}
    assert len(site_map) == 128
    assert all(row["proposed_ar"] == site_map[row["source_text"]] for row in dispositions["preserved-site-override"])

    for reviewer in REVIEWERS:
        report = (ROOT / reviewer["path"]).read_text(encoding="utf-8")
        assert PROPOSAL_SHA in report and "PASS" in report, f"Reviewer {reviewer['id']} report check failed"

    approved = read_rows(APPROVED)
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    old_decisions = decision_doc["decisions"]
    assert len(approved) == len(old_decisions) == 3549

    existing_keys = {row["source_text"] for row in approved}
    payload_keys = {row["source_text"].strip() for row in dispositions["PROPOSED-payload"]}
    assert len(payload_keys) == 121 and not (existing_keys & payload_keys)

    STRIP_COLLISIONS = {
        "Only Deduct Tax On Excess Amount ",
    }

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    reviewer_names = {reviewer["id"]: f"{reviewer['id']} ({reviewer['session']})" for reviewer in REVIEWERS}

    # Prepare released rows
    released_rows = []
    for row in dispositions["PROPOSED-payload"]:
        source = row["source_text"]
        arabic = row["proposed_ar"]
        if source in STRIP_COLLISIONS:
            continue
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
            "references": row.get("locations", ""),
            "notes": "Owner approved W6-1 Accounts Batch 03 on test site v16.localhost",
            "decision_ref": "",  # will be set to content:
        })
    assert len(released_rows) == 120

    # Write content evidence file
    evidence_lines = "".join(r["source_text"] + "\t" + r["translated_text"] + "\n" for r in released_rows)
    EVIDENCE.write_text(evidence_lines, encoding="utf-8")
    ref = f"content:{EVIDENCE.relative_to(ROOT)}"
    evidence_sha = sha256(EVIDENCE)
    refs = [{"ref": ref, "sha256": evidence_sha}]

    for r in released_rows:
        r["decision_ref"] = ref

    # Build decisions
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
    assert len(new_decisions) == 120

    # Update decisions doc
    old_decisions.update(new_decisions)
    assert len(old_decisions) == 3549 + 120 == 3669
    decision_doc["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision_doc["note"] = "W6-1 Accounts Batch 03 decisions added; content-evidence bound."
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Update catalog
    approved_all = approved + released_rows
    assert len(approved_all) == 3669
    with APPROVED.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(approved_all)

    # Write payload applied rows
    applied_rows = []
    for row in proposal:
        source = row["source_text"]
        arabic = row["proposed_ar"]
        disposition = row["proposed_disposition"]
        if source in STRIP_COLLISIONS:
            q_dec = "preserved-site-override (strip-collision)"
            notes = "Reclassified out of Released catalog per Plan §12; strip-collision with runtime Site Override"
            d_ref = row["decision_ref"]
            applied_ar = "خصم الضريبة فقط على المبلغ الزائد"
        elif disposition == "PROPOSED-payload":
            q_dec = "quorum-confirmed-payload"
            notes = "Released and imported into catalog under version 1.13"
            d_ref = ref
            applied_ar = arabic
        elif disposition == "EXCEPTION-technical":
            q_dec = "EXCEPTION-technical"
            notes = "Un-normalized developer column label; untranslated exception"
            d_ref = row["decision_ref"]
            applied_ar = arabic
        else:
            q_dec = "preserved-site-override"
            notes = "Preserved verbatim from live v16.localhost; not imported"
            d_ref = row["decision_ref"]
            applied_ar = arabic
        applied_rows.append({
            "source_text": source,
            "proposed_ar": arabic,
            "translated_text": applied_ar,
            "proposed_disposition": disposition,
            "quorum_decision": q_dec,
            "disposition_rationale": row["disposition_rationale"],
            "decision_ref": d_ref,
            "locations": row.get("locations", ""),
            "notes": notes,
        })
    with PAYLOAD.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(applied_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(applied_rows)

    # Write released list txt
    RELEASED.write_text("\n".join(r["source_text"] for r in released_rows) + "\n", encoding="utf-8")

    print(f"Content evidence written: {EVIDENCE} (SHA: {evidence_sha})")
    print(f"Payload applied rows: {PAYLOAD} (SHA: {sha256(PAYLOAD)})")
    print(f"Released list: {RELEASED} (SHA: {sha256(RELEASED)})")
    print(f"Catalog updated: {APPROVED} (SHA: {sha256(APPROVED)}, total rows: {len(approved_all)})")
    print(f"Decisions updated: {DECISIONS} (SHA: {sha256(DECISIONS)}, total decisions: {len(old_decisions)})")


if __name__ == "__main__":
    main()
