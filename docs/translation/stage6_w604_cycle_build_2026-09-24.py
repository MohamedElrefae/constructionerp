"""Build W6-4 release artifacts after unanimous A1/A2/A3 PASS.

This script mutates only the repository catalog, decision bundle, and batch
evidence CSVs. It does not connect to Frappe or touch any site.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_localization_gates import row_decision_id

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w604_projects_boq_rows_2026-09-24.csv"
RECON = HERE / "stage6_w604_projects_boq_site_recon_2026-09-24.json"
PROPOSAL = HERE / "stage6_w604_proposal_2026-09-24.csv"
PAYLOAD = HERE / "stage6_w604_payload_applied_rows_2026-09-24.csv"
RELEASED = HERE / "stage6_w604_released_list_2026-09-24.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"

SCOPE_SHA = "93fbf16b14940ce2d477f346c1777865bf008b22df943625e7de84f27e8f4abe"
PROPOSAL_SHA = "a9b9abaf3111b5ca0310aa7c3291f4c45e7fc04807242894848c707542694e2c"
APPROVED_BEFORE_SHA = "78ee35b2c0ea322527ccbe6272244794cd8524dd86f5df84a0c4f34f262d0016"
DECISIONS_BEFORE_SHA = "18d6dcecb373d955b759ddb5a4eb0aeb1e413889739851f509f20438232388ee"
PRIOR_OUTPUT_APPROVED_SHA = "323635566f8a983439b49e2e4700ba2433e355c3d4e91970eb414994baa45288"
PRIOR_OUTPUT_DECISIONS_SHA = "0da7bf87fd378d97fe6287fe27a94037f9a75b66b53a8b65c2868b600be85453"
REVIEWERS = (
    {
        "id": "AI-A1", "session": "/root/w603_a1",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w604-ai-a1-2026-09-24.md",
    },
    {
        "id": "AI-A2", "session": "/root/w603_a2",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w604-ai-a2-2026-09-24.md",
    },
    {
        "id": "AI-A3", "session": "/root/w603_a3",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w604-ai-a3-2026-09-24.md",
    },
)
VERSION = "1.7"
DOMAIN = "projects-subcontracting-desk"
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
    if sha256(APPROVED) == PRIOR_OUTPUT_APPROVED_SHA:
        # Replace only the exact prior W6-4 generated output. This allows the
        # reviewed translation correction to be rebuilt without accumulating
        # stale decision identities. Both current outputs and the base Git
        # blobs are pinned before either file is rewritten.
        assert sha256(DECISIONS) == PRIOR_OUTPUT_DECISIONS_SHA
        base_approved = subprocess.run(
            ["git", "show", f"HEAD:{APPROVED.relative_to(ROOT)}"],
            check=True, capture_output=True,
        ).stdout
        base_decisions = subprocess.run(
            ["git", "show", f"HEAD:{DECISIONS.relative_to(ROOT)}"],
            check=True, capture_output=True,
        ).stdout
        assert hashlib.sha256(base_approved).hexdigest() == APPROVED_BEFORE_SHA
        assert hashlib.sha256(base_decisions).hexdigest() == DECISIONS_BEFORE_SHA
        current_rows = read_rows(APPROVED)
        w604_rows = [row for row in current_rows if "W6-4 batch-01" in row.get("references", "")]
        assert len(w604_rows) == 50
        assert all(PROPOSAL_SHA not in row.get("notes", "") for row in w604_rows)
        APPROVED.write_bytes(base_approved)
        DECISIONS.write_bytes(base_decisions)
    assert sha256(APPROVED) == APPROVED_BEFORE_SHA
    assert sha256(DECISIONS) == DECISIONS_BEFORE_SHA
    scope, proposal = read_rows(SCOPE), read_rows(PROPOSAL)
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert recon["site"] == "v16.localhost" and recon["scope_sha256"] == SCOPE_SHA
    assert len(scope) == len(proposal) == 147
    assert [row["source_text"] for row in scope] == [row["source_text"] for row in proposal]
    assert len({row["source_text"] for row in scope}) == 147

    dispositions: dict[str, list[dict[str, str]]] = {}
    for row in proposal:
        dispositions.setdefault(row["proposed_disposition"], []).append(row)
    assert {key: len(value) for key, value in dispositions.items()} == {
        "preserved-site-override": 96,
        "PROPOSED-payload": 48,
        "DEFERRED-format-ambiguity": 1,
        "DEFERRED-runtime-key-normalization": 2,
    }
    live_preserved = {
        (row["source_text"], row["translated_text"])
        for row in recon["site_overrides"]
    }
    assert {
        (row["source_text"], row["proposed_ar"])
        for row in dispositions["preserved-site-override"]
    } == live_preserved
    for reviewer in REVIEWERS:
        review = (ROOT / reviewer["path"]).read_text(encoding="utf-8")
        assert PROPOSAL_SHA in review and "PASS" in review

    approved_rows = read_rows(APPROVED)
    decision_doc = json.loads(DECISIONS.read_text(encoding="utf-8"))
    old_decisions = decision_doc["decisions"]
    assert len(approved_rows) == len(old_decisions) == 2651
    assert all(row["release_status"] == "Released" for row in approved_rows)
    existing_keys = {row["source_text"].strip() for row in approved_rows}
    payload_keys = {row["source_text"] for row in dispositions["PROPOSED-payload"]}
    assert len(existing_keys) == 2651
    assert not (existing_keys & payload_keys)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    reviewer_names = {reviewer["id"]: f"{reviewer['id']} ({reviewer['session']})" for reviewer in REVIEWERS}
    applied: list[dict[str, str]] = []
    released: list[dict[str, str]] = []
    for row in proposal:
        source = row["source_text"]
        arabic = row["proposed_ar"]
        disposition = row["proposed_disposition"]
        if disposition == "PROPOSED-payload":
            released.append({
                "language": "ar", "source_text": source, "context": "",
                "ct_app": "erpnext", "translated_text": arabic,
                "domain": DOMAIN, "release_status": "Released", "release_version": VERSION,
                "a1_reviewer": reviewer_names["AI-A1"], "a1_approved_at": now,
                "a2_reviewer": reviewer_names["AI-A2"], "a2_approved_at": now,
                "a3_reviewer": reviewer_names["AI-A3"], "a3_approved_at": now,
                "references": "glossary v2.0; vendor Projects/Subcontracting PO locations; plan D5; W6-4 batch-01",
                "notes": (
                    "AI draft; independent A1/A2/A3 PASS bound to proposal SHA "
                    + PROPOSAL_SHA + "; owner-approved scope SHA " + SCOPE_SHA
                ),
                "decision_ref": f"content:{PAYLOAD.relative_to(ROOT)}",
            })
            applied_disposition = "quorum-confirmed-payload"
        elif disposition.startswith("DEFERRED-"):
            applied_disposition = disposition
        else:
            applied_disposition = "preserved-site-override (not imported, plan §12)"
        applied.append({
            "source_text": source,
            "translated_text": arabic,
            "quorum_decision": applied_disposition,
            "disposition_rationale": row["disposition_rationale"],
            "decision_ref": "stage6-W6-4 Projects + BOQ owner-approved 2026-09-24",
            "proposal_sha256": PROPOSAL_SHA,
        })

    assert len(released) == 48 and len(applied) == 147
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
        "Historical decisions retained; W6-4 additions bind 48 released rows to "
        "the exact proposal SHA and independent A1/A2/A3 PASS."
    )
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"scope=147 preserve=96 deferred=3 released={len(released)}")
    print(f"catalog=2651+{len(released)}={len(approved_rows) + len(released)}")
    print(f"payload_sha256={payload_hash}")
    print(f"released_list_sha256={sha256(RELEASED)}")
    print(f"approved_csv_sha256={sha256(APPROVED)}")
    print(f"release_decisions_sha256={sha256(DECISIONS)}")
    print(f"decision_root_sha256={hashlib.sha256(json.dumps(old_decisions, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()}")


if __name__ == "__main__":
    main()
