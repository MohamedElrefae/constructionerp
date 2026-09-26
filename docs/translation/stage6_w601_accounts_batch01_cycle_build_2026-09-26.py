"""Cycle build for W6-1 Accounts Batch 01."""
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
SCOPE = HERE / "stage6_w601_accounts_batch01_rows_2026-09-24.csv"
RECON = HERE / "stage6_w601_accounts_batch01_site_recon_2026-09-24.json"
PROPOSAL = HERE / "stage6_w601_accounts_batch01_proposal_2026-09-24.csv"
PAYLOAD = HERE / "stage6_w601_accounts_batch01_payload_applied_rows_2026-09-26.csv"
RELEASED = HERE / "stage6_w601_accounts_batch01_released_list_2026-09-26.txt"
EVIDENCE = HERE / "stage6_w601_accounts_batch01_content_evidence_2026-09-26.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"

SCOPE_SHA = "4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd"
PROPOSAL_SHA = "226ff8b158a4a17bca77209d2e452fff9eff75fd6479324f3e020e6b24ab2b4e"
APPROVED_BEFORE_SHA = "ad737758756dca0d69b83ff89d05908eb18df52a0d58afb889cef9f59253e080"
DECISIONS_BEFORE_SHA = "84a6a078f6ef1c5f96b097f6487633178681ed16c1354d2dae1f4efeef89f844"

REVIEWERS = (
    {"id": "AI-A1", "session": "5eac7390-733b-4cf4-b51d-e867da36d63e", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a1-accounts-batch01-2026-09-26.md"},
    {"id": "AI-A2", "session": "c4ff7ac5-46af-4d7d-8307-ef715483a5dd", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a2-accounts-batch01-2026-09-26.md"},
    {"id": "AI-A3", "session": "fee9d8fe-f9f2-4838-9652-3c2d2b7b474e", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a3-accounts-batch01-2026-09-26.md"},
)
VERSION = "1.11"
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
        "preserved-site-override": 147,
        "PROPOSED-payload": 103,
    }
    site_map = {row["source_text"]: row["translated_text"] for row in recon["site_overrides"]}
    assert len(site_map) == 147
    assert all(row["proposed_ar"] == site_map[row["source_text"]] for row in dispositions["preserved-site-override"])

    for reviewer in REVIEWERS:
        report = (ROOT / reviewer["path"]).read_text(encoding="utf-8")
        assert PROPOSAL_SHA in report and "PASS" in report, f"Reviewer {reviewer['id']} report check failed"

    approved = read_rows(APPROVED)
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    old_decisions = decision_doc["decisions"]
    assert len(approved) == len(old_decisions) == 3364

    existing_keys = {row["source_text"] for row in approved}
    payload_keys = {row["source_text"] for row in dispositions["PROPOSED-payload"]}
    assert len(payload_keys) == 103 and not (existing_keys & payload_keys)

    STRIP_COLLISIONS = {
        " Amount",
        " Name",
        " Rate",
        "All Parties ",
        "Apply Tax Withholding Amount ",
        "Customer ",
    }
    ALREADY_RELEASED = {
        "Closing [Opening + Total] ",
    }

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    reviewer_names = {reviewer["id"]: f"{reviewer['id']} ({reviewer['session']})" for reviewer in REVIEWERS}

    # Prepare released rows
    released_rows = []
    for row in dispositions["PROPOSED-payload"]:
        source = row["source_text"]
        arabic = row["proposed_ar"]
        if source in STRIP_COLLISIONS or source in ALREADY_RELEASED:
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
            "notes": "Owner approved W6-1 Accounts Batch 01 on test site v16.localhost",
            "decision_ref": "",  # will be set to content:
        })
    assert len(released_rows) == 96

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
        source = r["source_text"]  # Raw source matches row_identity_fields in check_csv!
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
    assert len(new_decisions) == 96

    # Update decisions doc
    old_decisions.update(new_decisions)
    assert len(old_decisions) == 3364 + 96 == 3460
    decision_doc["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision_doc["note"] = "W6-1 Accounts Batch 01 decisions added; content-evidence bound."
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Update catalog
    approved_all = approved + released_rows
    assert len(approved_all) == 3460
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
        elif source in ALREADY_RELEASED:
            q_dec = "already-released (catalog row retained; not re-appended)"
            notes = "Already present in catalog line 52 (version 1.2); not re-appended"
            d_ref = row["decision_ref"]
        elif disposition == "PROPOSED-payload":
            q_dec = "quorum-confirmed-payload"
            notes = "Released and imported into catalog under version 1.11"
            d_ref = ref
        else:
            q_dec = "preserved-site-override"
            notes = "Preserved verbatim from live v16.localhost; not imported"
            d_ref = row["decision_ref"]
        applied_rows.append({
            "source_text": source,
            "proposed_ar": arabic,
            "translated_text": arabic,
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
