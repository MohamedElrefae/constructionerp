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
SCOPE = HERE / "stage6_w606_crm_support_maintenance_rows_2026-09-24.csv"
RECON = HERE / "stage6_w606_crm_support_maintenance_site_recon_2026-09-24.json"
PROPOSAL = HERE / "stage6_w606_crm_support_maintenance_proposal_2026-09-24.csv"
PAYLOAD = HERE / "stage6_w606_crm_support_maintenance_payload_applied_rows_2026-09-24.csv"
RELEASED = HERE / "stage6_w606_crm_support_maintenance_released_list_2026-09-24.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"
SCOPE_SHA = "a77b43a908859c0aea3e2c58525ec3765772c09af8617f1f17fb8c8bf12833f9"
PROPOSAL_SHA = "d8a2a8df2c040434b82d4d813f96e510e454b0f11114a31cf709db62bf60f266"
APPROVED_BEFORE_SHA = "ab2350759c9bbeda8d637442ef756b3e28229b1bebae8d76e95ec31c655fa749"
DECISIONS_BEFORE_SHA = "2cef685c7ded52d83fdd3e1e504f4175495f01d12563079d8a3f1f72cfea178b"
REVIEWERS = (
    {"id": "AI-A1", "session": "/root/w606_crm_a1_corrected", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-a1-crm-support-maintenance-corrected-2026-09-24.md"},
    {"id": "AI-A2", "session": "/root/w606_crm_a2_corrected", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-a2-crm-support-maintenance-corrected-2026-09-24.md"},
    {"id": "AI-A3", "session": "/root/w606_crm_a3_corrected", "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-a3-crm-support-maintenance-corrected-2026-09-24.md"},
)
AI_R_REPORT = "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-r-crm-support-maintenance-final-2026-09-24.md"
VERSION = "1.10"
DOMAIN = "crm-support-maintenance"
FIELDS = [
    "language", "source_text", "context", "ct_app", "translated_text", "domain",
    "release_status", "release_version", "a1_reviewer", "a1_approved_at",
    "a2_reviewer", "a2_approved_at", "a3_reviewer", "a3_approved_at",
    "references", "notes", "decision_ref",
]


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha256(SCOPE) == SCOPE_SHA
    assert sha256(PROPOSAL) == PROPOSAL_SHA
    assert sha256(APPROVED) == APPROVED_BEFORE_SHA
    assert sha256(DECISIONS) == DECISIONS_BEFORE_SHA
    scope = read_rows(SCOPE)
    proposal = read_rows(PROPOSAL)
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert recon["scope_sha256"] == SCOPE_SHA and recon["site"] == "v16.localhost"
    assert len(scope) == len(proposal) == 119
    assert [row["source_text"] for row in scope] == [row["source_text"] for row in proposal]
    assert len({row["source_text"] for row in scope}) == 119
    dispositions = {}
    for row in proposal:
        dispositions.setdefault(row["proposed_disposition"], []).append(row)
    assert {key: len(value) for key, value in dispositions.items()} == {
        "preserved-site-override": 76,
        "PROPOSED-payload": 38,
        "DEFERRED-source-defect": 4,
        "EXCEPTION-technical": 1,
    }
    site_map = {row["source_text"]: row["translated_text"] for row in recon["site_overrides"]}
    assert len(site_map) == 76
    assert all(row["proposed_ar"] == site_map[row["source_text"]] for row in dispositions["preserved-site-override"])
    for reviewer in REVIEWERS:
        report = (ROOT / reviewer["path"]).read_text(encoding="utf-8")
        assert PROPOSAL_SHA in report and "PASS" in report
    ai_r = (ROOT / AI_R_REPORT).read_text(encoding="utf-8")
    assert PROPOSAL_SHA in ai_r and "PASS" in ai_r

    approved = read_rows(APPROVED)
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    old_decisions = decision_doc["decisions"]
    assert len(approved) == len(old_decisions) == 3326
    existing_keys = {row["source_text"] for row in approved}
    payload_keys = {row["source_text"] for row in dispositions["PROPOSED-payload"]}
    assert len(payload_keys) == 38 and not (existing_keys & payload_keys)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    reviewer_names = {reviewer["id"]: f"{reviewer['id']} ({reviewer['session']})" for reviewer in REVIEWERS}
    applied = []
    released = []
    for row in proposal:
        source = row["source_text"]
        arabic = row["proposed_ar"]
        disposition = row["proposed_disposition"]
        if disposition == "PROPOSED-payload":
            assert source not in existing_keys and arabic.strip()
            released.append({
                "language": "ar", "source_text": source, "context": "", "ct_app": "erpnext",
                "translated_text": arabic, "domain": DOMAIN, "release_status": "Released",
                "release_version": VERSION,
                "a1_reviewer": reviewer_names["AI-A1"], "a1_approved_at": now,
                "a2_reviewer": reviewer_names["AI-A2"], "a2_approved_at": now,
                "a3_reviewer": reviewer_names["AI-A3"], "a3_approved_at": now,
                "references": "Glossary v2.0; vendor ERPNext CRM/Support/Maintenance PO locations; W6-6 CRM Support Maintenance",
                "notes": f"Renewed A1/A2/A3 PASS bound to proposal SHA {PROPOSAL_SHA}; owner-approved corrected scope SHA {SCOPE_SHA}",
                "decision_ref": f"content:{PAYLOAD.relative_to(ROOT)}",
            })
            applied_disposition = "quorum-confirmed-payload"
        elif disposition == "preserved-site-override":
            assert site_map[source] == arabic
            applied_disposition = "preserved-site-override (not imported, plan §12)"
        elif disposition == "DEFERRED-source-defect":
            assert not arabic
            applied_disposition = "DEFERRED-source-defect"
        elif disposition == "EXCEPTION-technical":
            assert not arabic
            applied_disposition = "EXCEPTION-technical (empty, vendor rendering retained)"
        else:
            raise AssertionError(disposition)
        applied.append({
            "source_text": source,
            "translated_text": arabic,
            "quorum_decision": applied_disposition,
            "disposition_rationale": row["disposition_rationale"],
            "decision_ref": f"content:{PAYLOAD.relative_to(ROOT)}",
            "scope_sha256": SCOPE_SHA,
            "proposal_sha256": PROPOSAL_SHA,
        })
    assert len(applied) == 119 and len(released) == 38
    with PAYLOAD.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(applied[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(applied)
    RELEASED.write_text("".join(row["source_text"] + "\n" for row in released), encoding="utf-8")
    payload_hash = sha256(PAYLOAD)
    refs = [{"ref": f"content:{PAYLOAD.relative_to(ROOT)}", "sha256": payload_hash}]
    for row in released:
        source, value = row["source_text"], row["translated_text"]
        proposal_hash = hashlib.sha256(f"{source}|{value}".encode("utf-8")).hexdigest()
        ident = [
            row["language"], row["ct_app"], row["context"], source, value,
            row["a1_reviewer"], row["a1_approved_at"], row["a2_reviewer"], row["a2_approved_at"],
            row["a3_reviewer"], row["a3_approved_at"], row["release_version"], row["domain"],
            row["references"], proposal_hash,
        ]
        decision_id = row_decision_id(ident, refs)
        assert decision_id not in old_decisions
        old_decisions[decision_id] = {
            "language": row["language"], "ct_app": row["ct_app"], "context": row["context"],
            "source_text": source, "translated_text": value, "domain": row["domain"],
            "reviewers": [row["a1_reviewer"], row["a2_reviewer"], row["a3_reviewer"]],
            "timestamps": [row["a1_approved_at"], row["a2_approved_at"], row["a3_approved_at"]],
            "release_version": row["release_version"], "references": row["references"],
            "proposal": {"arabic": value, "sha256": proposal_hash},
            "verdicts": {reviewer["id"]: {"decision": "approve", "confidence": "high", "session": reviewer["session"]} for reviewer in REVIEWERS},
            "artifacts": refs,
        }
    with APPROVED.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writerows(released)
    decision_doc["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision_doc["note"] = "W6-6 CRM Support Maintenance corrected bundle; 38 released rows bound to renewed A1/A2/A3 PASS; historical decisions retained."
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"scope=119 preserve=76 deferred=4 technical=1 released={len(released)}")
    print(f"catalog={len(approved)}+{len(released)}={len(approved) + len(released)}")
    print(f"payload_sha256={payload_hash}")
    print(f"approved_csv_sha256={sha256(APPROVED)}")
    print(f"release_decisions_sha256={sha256(DECISIONS)}")


if __name__ == "__main__":
    main()
