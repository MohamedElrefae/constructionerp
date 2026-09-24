"""Build W6-6 release artifacts after unanimous A1/A2/A3 PASS.

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
SCOPE = HERE / "stage6_w606_assets_rows_2026-09-24.csv"
RECON = HERE / "stage6_w606_assets_site_recon_2026-09-24.json"
PROPOSAL = HERE / "stage6_w606_proposal_2026-09-24.csv"
PAYLOAD = HERE / "stage6_w606_payload_applied_rows_2026-09-24.csv"
RELEASED = HERE / "stage6_w606_released_list_2026-09-24.txt"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
DECISIONS = ROOT / "construction/data/translations/release_decisions.json"

SCOPE_SHA = "6f142646ae55cf147751e8d751f10638c79420dfa184855985ecd6068ee63a40"
PROPOSAL_SHA = "521f1eb620b6c403f3cce91fd4ec280f86ad46f427ae6c1e194199c0242762ab"
APPROVED_BEFORE_SHA = "fbc40cdc4e4fb36d7ac94c1c08b14a584198e6668c3554caf58a4f2f854073a2"
DECISIONS_BEFORE_SHA = "e77fb439c4f009c5056fd6065fced2ee77598b5374da9868145b46efda374102"

REVIEWERS = (
    {
        "id": "AI-A1", "session": "0e4a99b1-3f8a-44b8-b712-bdbf1979c4c1",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-a1-2026-09-24.md",
    },
    {
        "id": "AI-A2", "session": "a3386362-7179-40b3-b2ac-5078779fc53d",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-a2-2026-09-24.md",
    },
    {
        "id": "AI-A3", "session": "cb33610b-7890-4ebc-acf6-c8af772ae829",
        "path": "docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-a3-2026-09-24.md",
    },
)
VERSION = "1.7"
DOMAIN = "assets"
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
    assert len(scope) == len(proposal) == 211
    assert [row["source_text"] for row in scope] == [row["source_text"] for row in proposal]
    assert len({row["source_text"] for row in scope}) == 211

    dispositions: dict[str, list[dict[str, str]]] = {}
    for row in proposal:
        dispositions.setdefault(row["proposed_disposition"], []).append(row)
    assert {key: len(value) for key, value in dispositions.items()} == {
        "preserved-site-override": 98,
        "PROPOSED-payload": 113,
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
    assert len(approved_rows) == len(old_decisions) == 3048
    assert all(row["release_status"] == "Released" for row in approved_rows)
    existing_keys = {row["source_text"].strip() for row in approved_rows}
    payload_keys = {row["source_text"] for row in dispositions["PROPOSED-payload"]}
    assert len(existing_keys) == 3048
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
                "references": "glossary v2.0; vendor assets PO locations; plan D5; W6-6 batch-01",
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
            "decision_ref": "stage6-W6-6 Assets owner-approved 2026-09-24",
            "proposal_sha256": PROPOSAL_SHA,
        })

    assert len(released) == 113 and len(applied) == 211
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
        "Historical decisions retained; W6-6 additions bind 113 released rows to "
        "the exact proposal SHA and independent A1/A2/A3 PASS."
    )
    DECISIONS.write_text(json.dumps(decision_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"scope=211 preserve=98 released={len(released)}")
    print(f"catalog=3048+{len(released)}={len(approved_rows) + len(released)}")
    print(f"payload_sha256={payload_hash}")
    print(f"released_list_sha256={sha256(RELEASED)}")
    print(f"approved_csv_sha256={sha256(APPROVED)}")
    print(f"release_decisions_sha256={sha256(DECISIONS)}")
    print(f"decision_root_sha256={hashlib.sha256(json.dumps(old_decisions, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()}")


if __name__ == "__main__":
    main()
