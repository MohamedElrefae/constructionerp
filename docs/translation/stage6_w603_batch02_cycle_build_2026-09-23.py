"""Build the W6-3 batch-02 disposition and catalog delta after quorum PASS.

This only prepares tracked artifacts. It does not write to the Frappe site.
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
SCOPE = HERE / "stage6_w603_batch02_rows_2026-09-23.csv"
PROPOSAL = HERE / "stage6_w603_proposal_batch02_2026-09-23.csv"
RECON = HERE / "stage6_w603_batch02_site_recon_2026-09-23.json"
PAYLOAD = HERE / "stage6_w603_payload_applied_rows_batch02_2026-09-23.csv"
RELEASED = HERE / "stage6_w603_batch02_released_list_2026-09-23.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"

SCOPE_SHA = "701ad13e6b4cc530ebd7dbd95705979b70055c46f39da37d4532a26ba60439ef"
PROPOSAL_SHA = "aaac0e04b364f63e55dcfbd59bd72a19156952523f500226cb919aa387a8349e"
AI_A1 = "docs/ai/work-items/scope-context-portability/evidence/stage6-w603-ai-a1-batch02-2026-09-23.md"
AI_A2 = "docs/ai/work-items/scope-context-portability/evidence/stage6-w603-ai-a2-batch02-2026-09-23.md"
AI_A3 = "docs/ai/work-items/scope-context-portability/evidence/stage6-w603-ai-a3-batch02-2026-09-23.md"
REVIEWERS = (
    {"id": "AI-A1", "session": "/root/w603_a1", "model": "GPT-6", "path": AI_A1},
    {"id": "AI-A2", "session": "/root/w603_a2", "model": "GPT-6", "path": AI_A2},
    {"id": "AI-A3", "session": "/root/w603_a3", "model": "Codex GPT-6", "path": AI_A3},
)
VERSION = "1.6"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
DECISION_REF = "stage6-W6-3 batch-02 owner-approved 2026-09-23"
FIELDS = [
    "language", "source_text", "context", "ct_app", "translated_text", "domain",
    "release_status", "release_version", "a1_reviewer", "a1_approved_at",
    "a2_reviewer", "a2_approved_at", "a3_reviewer", "a3_approved_at",
    "references", "notes", "decision_ref",
]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    assert hashlib.sha256(SCOPE.read_bytes()).hexdigest() == SCOPE_SHA
    assert hashlib.sha256(PROPOSAL.read_bytes()).hexdigest() == PROPOSAL_SHA
    scope, proposal = rows(SCOPE), rows(PROPOSAL)
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert recon["scope_sha256"] == SCOPE_SHA and recon["site_override_key_count"] == 143
    assert len(scope) == len(proposal) == 250
    assert [r["source_text"] for r in scope] == [r["source_text"] for r in proposal]
    assert len({r["source_text"] for r in scope}) == 250

    site_values = {r["source_text"]: r["translated_text"] for r in recon["site_overrides"]}
    expected_counts = {
        "PROPOSED-payload": 103,
        "preserved-site-override": 143,
        "EXCEPTION-technical": 2,
        "DEFERRED-source-defect": 2,
    }
    actual_counts: dict[str, int] = {}
    for r in proposal:
        actual_counts[r["proposed_disposition"]] = actual_counts.get(r["proposed_disposition"], 0) + 1
    assert actual_counts == expected_counts, actual_counts
    assert all(r["proposed_ar"] == site_values[r["source_text"]] for r in proposal if r["proposed_disposition"] == "preserved-site-override")
    assert all(r["proposed_ar"] == "" for r in proposal if r["proposed_disposition"] in {"EXCEPTION-technical", "DEFERRED-source-defect"})
    for reviewer in REVIEWERS:
        data = (ROOT / reviewer["path"]).read_text(encoding="utf-8")
        assert PROPOSAL_SHA in data and "**PASS**" in data

    applied = []
    released_rows = []
    for r in proposal:
        disp = r["proposed_disposition"]
        if disp == "PROPOSED-payload":
            disp = "quorum-confirmed-payload"
            translated = r["proposed_ar"]
            released_rows.append({
                "language": "ar", "source_text": r["source_text"], "context": "",
                "ct_app": "erpnext", "translated_text": translated,
                "domain": "stock-desk", "release_status": "Released",
                "release_version": VERSION,
                "a1_reviewer": "AI-A1 (/root/w603_a1)", "a1_approved_at": NOW,
                "a2_reviewer": "AI-A2 (/root/w603_a2)", "a2_approved_at": NOW,
                "a3_reviewer": "AI-A3 (/root/w603_a3)", "a3_approved_at": NOW,
                "references": "glossary v2.0; vendor stock PO locations; plan D5; W6-3 batch-02",
                "notes": "AI proposal; independent A1/A2/A3 PASS bound to proposal SHA " + PROPOSAL_SHA,
                "decision_ref": f"content:{PAYLOAD.relative_to(ROOT)}",
            })
        else:
            translated = r["proposed_ar"]
        applied.append({
            "source_text": r["source_text"], "translated_text": translated,
            "quorum_decision": disp,
            "disposition_rationale": r["disposition_rationale"],
            "decision_ref": DECISION_REF,
            "proposal_sha256": PROPOSAL_SHA,
        })

    with PAYLOAD.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(applied[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(applied)
    RELEASED.write_text("".join(r["source_text"] + "\n" for r in released_rows), encoding="utf-8")

    existing = rows(APPROVED)
    existing_keys = {r["source_text"].strip() for r in existing if r.get("release_status") == "Released"}
    new_keys = {r["source_text"].strip() for r in released_rows}
    assert len(existing) == 2437 and len(released_rows) == 103
    assert not (existing_keys & new_keys), sorted(existing_keys & new_keys)
    assert all(r["release_status"] == "Released" for r in existing)
    with APPROVED.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writerows(released_rows)

    doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    old = doc["decisions"]
    payload_ref = f"content:{PAYLOAD.relative_to(ROOT)}"
    payload_bytes = PAYLOAD.read_bytes()
    refs = [{"ref": payload_ref, "sha256": hashlib.sha256(payload_bytes).hexdigest()}]
    for r in released_rows:
        src, val = r["source_text"], r["translated_text"]
        proposal_hash = hashlib.sha256(f"{src}|{val}".encode()).hexdigest()
        ident_parts = [
            r["language"], r["ct_app"], r["context"], src, val,
            r["a1_reviewer"], r["a1_approved_at"], r["a2_reviewer"], r["a2_approved_at"],
            r["a3_reviewer"], r["a3_approved_at"], r["release_version"], r["domain"],
            r["references"], proposal_hash,
        ]
        did = row_decision_id(ident_parts, refs)
        assert did not in old
        old[did] = {
            "language": r["language"], "ct_app": r["ct_app"], "context": r["context"],
            "source_text": src, "translated_text": val, "domain": r["domain"],
            "reviewers": [r["a1_reviewer"], r["a2_reviewer"], r["a3_reviewer"]],
            "timestamps": [r["a1_approved_at"], r["a2_approved_at"], r["a3_approved_at"]],
            "release_version": r["release_version"], "references": r["references"],
            "proposal": {"arabic": val, "sha256": proposal_hash},
            "verdicts": {
                reviewer["id"]: {"decision": "approve", "confidence": "high", "session": reviewer["session"], "model": reviewer["model"]}
                for reviewer in REVIEWERS
            },
            "artifacts": refs,
        }
    doc["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc["note"] = "W6-3 batch-02 additions bind quorum PASS to the exact proposal SHA; existing historical decisions retained."
    DECISIONS.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"scope={len(scope)} dispositions={actual_counts} releases={len(released_rows)}")
    print(f"catalog={len(existing)}+{len(released_rows)}={len(existing)+len(released_rows)}")
    print(f"proposal_sha256={PROPOSAL_SHA}")
    print(f"payload_sha256={hashlib.sha256(payload_bytes).hexdigest()}")
    print(f"catalog_sha256={hashlib.sha256(APPROVED.read_bytes()).hexdigest()}")
    print(f"release_decisions_sha256={hashlib.sha256(DECISIONS.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
