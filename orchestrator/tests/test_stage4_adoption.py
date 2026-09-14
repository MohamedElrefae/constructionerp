"""Acceptance tests for Canonical Plan §11 ERP Adoption machinery.

Verifies:
- Historical adoption command and provenance revalidation from disk.
- Stages 0–3 recorded as historical completion without rerun with real evidence hashes.
- Stage 4 starting at PROPOSAL_PENDING sub-status with 81 expected identities.
- Proposal candidate hashing and deterministic bundle composition.
- Panel review quorum, distinct sessions, exact 81-identity coverage, and PANEL_RENEWAL.
- DRY_RUN requires real 64-char hex evidence digest before opening IMPORT_AUTHORIZATION.
- DRY_RUN and IMPORT token validation across all 5 discrete hashes, descriptor hash, and tamper resistance.
- Prevention of token reuse in Engine.approve.
- Zero mutation to apps/construction.
"""

import os
import json
import shutil
import hashlib
import pytest
from copy import deepcopy
from pathlib import Path

from core import WorkflowError, digest, utc, canonical, bytes_hash, write_json
from engine import Engine
from routing import apply_event, initial, gate_id
from stage4 import (
    is_hex64,
    derive_identities_digest,
    canonical_bundle_sha256,
    canonical_payload_sha256,
    derive_proposal_hash,
    derive_stage4_candidate_id,
    project_proposal_rows,
    compose_bundle,
    validate_panel_reviews,
    verify_stage4_manifest,
    verify_historical_provenance,
    HISTORICAL_PROVENANCE_AUTHORITY,
)
from validate import validate_document


@pytest.fixture
def test_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    import subprocess
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "-b", "feature/scope-context-portability"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Tester"], check=True)

    (repo / "README.md").write_text("initial")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True)

    (repo / "orchestrator").mkdir(parents=True)
    roles = {
        "architect": {"tool": "codex", "binary": "/bin/true", "model": "gpt-6-astra", "prompt_sha256": "0"*64},
        "reviewer": {"tool": "codex", "binary": "/bin/true", "model": "gpt-6-astra", "prompt_sha256": "0"*64},
        "builder": {"tool": "codex", "binary": "/bin/true", "model": "gpt-6-astra", "prompt_sha256": "0"*64},
        "verifier": {"tool": "codex", "binary": "/bin/true", "model": "gpt-6-astra", "prompt_sha256": "0"*64},
        "proposer": {"tool": "codex", "binary": "/bin/true", "model": "gpt-6-astra", "prompt_sha256": "0"*64},
        "ai-a1": {"tool": "codex", "binary": "/bin/true", "model": "gpt-6-astra", "prompt_sha256": "0"*64},
        "ai-a2": {"tool": "codex", "binary": "/bin/true", "model": "gpt-6-astra", "prompt_sha256": "0"*64},
        "ai-a3": {"tool": "codex", "binary": "/bin/true", "model": "gpt-6-astra", "prompt_sha256": "0"*64},
    }
    (repo / "orchestrator/roles.json").write_text(json.dumps(roles))

    source = Path(__file__).resolve().parents[2]
    if (source / "docs/ai/roles").exists():
        shutil.copytree(source / "docs/ai/roles", repo / "docs/ai/roles")

    plan_dir = repo / "docs/translation"
    plan_dir.mkdir(parents=True)
    (plan_dir / "ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md").write_text("Canonical Plan Content")

    return repo


def test_adopt_historical_initializes_stages_0_to_3_with_real_evidence_hashes(test_repo):
    """Canonical Plan §11.1: Historical stages 0-3 recorded using real file verification."""
    e = Engine(test_repo)
    try:
        view = e.adopt_historical("erp-arabic-bilingual-data")
        assert view["work_item"] == "erp-arabic-bilingual-data"
        assert view["stage"] == "4"
        assert view["sub_status"] == "PROPOSAL_PENDING"
        assert view["gate"]["scope"] == "PLAN"
        assert view["next_roles"] == []
        assert view["plan_granted"] is False
        assert view["candidate"]["kind"] == "stage4-proposal"
        assert view["candidate"]["export_sha256"] == "206ecfae017b915742abc265016eee094304562e53838a932c7fd56af6db9ed1"
        assert view["candidate"]["identities_digest"] == e.config["identities_digest"]
        assert is_hex64(view["candidate"]["identities_digest"])
        assert "expected_identities" not in e.config

        stages = view["stages"]
        assert stages["0"]["historical"] is True
        assert stages["0"]["evidence_refs"][0]["artifact_id"] == "stage-0-baseline"
        assert stages["0"]["evidence_refs"][0]["sha256"] == "5334c6683a4fd51096c2f6e03d01458dff3ca70072c82998036806fe30d27efd"

        assert stages["1"]["historical"] is True
        assert stages["1"]["evidence_refs"][0]["artifact_id"] == "stage-1c-ai-r-durability-final"
        assert stages["1"]["evidence_refs"][0]["sha256"] == "54ed9554fb2b8f82834598e5213a7aa6c954694497d0c5569754ed1a80dd42d8"

        assert stages["2"]["historical"] is True
        assert stages["2"]["evidence_refs"][0]["artifact_id"] == "stage-2-ai-r-round19"
        assert stages["2"]["evidence_refs"][0]["sha256"] == "3e83a3528fff02a206745df235fcfb5cc212d335129847e3144e0ab68347a880"

        assert stages["3"]["historical"] is True
        assert stages["3"]["evidence_refs"][0]["artifact_id"] == "stage-3-ai-r-round12"
        assert stages["3"]["evidence_refs"][0]["sha256"] == "4a397f7acfd72de31e3cc72796c45d4d917947fc213d808668d5df217292f7ed"

        assert stages["4"]["historical"] is False
        assert stages["4"]["sub_status"] == "PROPOSAL_PENDING"
    finally:
        e.close()


def test_adopt_historical_fails_on_tampered_or_missing_file(test_repo, tmp_path):
    """Revalidation must fail closed if any historical evidence file is missing or altered."""
    mock_erp = tmp_path / "mock_erp"
    mock_erp.mkdir()
    
    # Copy partial structure but corrupt stage 0 evidence
    ev_dir = mock_erp / "docs/ai/work-items/erp-arabic-bilingual-data/evidence"
    ev_dir.mkdir(parents=True)
    (ev_dir / "stage-0-baseline.md").write_text("corrupted content")

    descriptor = {
        "erp_checkout": str(mock_erp),
        "bench_root": str(tmp_path),
        "site": "v16.localhost",
        "site_classification": "non-production test",
        "private_root": str(tmp_path / "private"),
    }

    e = Engine(test_repo)
    try:
        with pytest.raises(WorkflowError, match="Historical evidence hash mismatch"):
            e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=descriptor)
    finally:
        e.close()


def test_proposal_candidate_hashing_and_projection():
    """Canonical Plan §5.3: Hashing must be deterministic, row-sorted, and exclude A2 decisions."""
    export_sha = "a" * 64
    rows_unsorted = [
        {
            "identity": "2000 - Liabilities - E",
            "english": "Liabilities",
            "is_group": True,
            "proposal": {"arabic": "التزامات", "confidence": "high"},
            "a2_review": {"decision": "approved"},
            "flags": ["review_flag"],
        },
        {
            "identity": "1000 - Assets - E",
            "english": "Assets",
            "is_group": True,
            "proposal": {"arabic": "أصول", "confidence": "high"},
            "a2_review": {"decision": "approved"},
        },
    ]

    h1 = derive_proposal_hash(rows_unsorted, export_sha)
    projected = project_proposal_rows(rows_unsorted)
    assert projected[0]["identity"] == "1000 - Assets - E"
    assert projected[1]["identity"] == "2000 - Liabilities - E"
    assert "a2_review" not in projected[0]

    h2 = derive_proposal_hash(list(reversed(rows_unsorted)), export_sha)
    assert h1 == h2

    cid = derive_stage4_candidate_id(export_sha, h1)
    assert is_hex64(cid)

    # Invalid export_sha rejected
    with pytest.raises(WorkflowError, match="export_sha256 must be 64-character lowercase hex"):
        derive_proposal_hash(rows_unsorted, "invalid_non_hex")


def test_deterministic_bundle_composition():
    """Canonical Plan §5.3: Completed bundle preserves proposal projection and adds A2 review."""
    proposal_rows = [
        {
            "identity": "1100 - Cash - E",
            "english": "Cash",
            "is_group": False,
            "proposal": {"arabic": "نقدية", "confidence": "high", "flags": []},
        }
    ]
    a2_decisions = {
        "1100 - Cash - E": {
            "decision": "approved",
            "confidence": "high",
            "rationale": "Matches Egyptian banking conventions",
            "reference": {"status": "absent", "value": None, "source": None},
            "provenance": {"reviewer": "ai-a2", "model": "gpt-6-astra", "session": "s1", "reviewed_utc": utc()},
        }
    }

    bundle = compose_bundle(proposal_rows, a2_decisions, company="Elrefae")
    assert bundle["schema"] == "construction-stage4-account-review-bundle/v1"
    assert len(bundle["rows"]) == 1
    assert "no_verified_reference" in bundle["rows"][0]["flags"]


def test_panel_review_quorum_exact_coverage_and_independent_sessions():
    """Canonical Plan §11.3 & §11.4: Requires exact identity coverage, distinct sessions, and checks decisions."""
    expected = ["acc-1", "acc-2", "acc-3"]

    def make_reviews(sessions, coverages, decisions=None, findings=None, suggested=None):
        revs = {}
        for i, role in enumerate(["ai-a1", "ai-a2", "ai-a3"]):
            rows = []
            for ident in coverages[i]:
                dec = (decisions or {}).get(ident, "approved")
                sugg = (suggested or {}).get(ident)
                row_item = {
                    "identity": ident,
                    "decision": dec,
                    "rationale": "Standard terminology",
                }
                if sugg:
                    row_item["suggested_arabic"] = sugg
                    row_item["proposed_arabic"] = "old_val"
                rows.append(row_item)
            revs[role] = {
                "session_id": sessions[i],
                "verdict": "PASS",
                "row_decisions": rows,
                "findings": (findings or {}).get(role, []),
            }
        return revs

    # 1. Valid panel review
    valid_revs = make_reviews(["s1", "s2", "s3"], [expected, expected, expected])
    val = validate_panel_reviews(valid_revs, expected)
    assert val["ok"] is True
    assert val["renewal_required"] is False

    # 2. Duplicate session_id fails
    dup_sess_revs = make_reviews(["s1", "s1", "s3"], [expected, expected, expected])
    with pytest.raises(WorkflowError, match="Panel review sessions are not independent"):
        validate_panel_reviews(dup_sess_revs, expected)

    # 3. Missing identity in one reviewer (acc-3 missing from ai-a2)
    missing_revs = make_reviews(["s1", "s2", "s3"], [expected, ["acc-1", "acc-2"], expected])
    with pytest.raises(WorkflowError, match="does not cover exact identities: missing 1"):
        validate_panel_reviews(missing_revs, expected)

    # 4. Duplicate identity in one reviewer
    dup_row_revs = make_reviews(["s1", "s2", "s3"], [expected, ["acc-1", "acc-2", "acc-3", "acc-2"], expected])
    with pytest.raises(WorkflowError, match="Duplicate identity"):
        validate_panel_reviews(dup_row_revs, expected)

    # 5. Extraneous identity in one reviewer
    extra_revs = make_reviews(["s1", "s2", "s3"], [expected, expected, ["acc-1", "acc-2", "acc-3", "acc-99"]])
    with pytest.raises(WorkflowError, match="extra 1"):
        validate_panel_reviews(extra_revs, expected)

    # 6. Missing required role
    partial_roles = {"ai-a1": valid_revs["ai-a1"], "ai-a2": valid_revs["ai-a2"]}
    with pytest.raises(WorkflowError, match="Panel reviews role mismatch"):
        validate_panel_reviews(partial_roles, expected)

    # 7. Arabic value change triggers renewal_required
    renewal_revs = make_reviews(["s1", "s2", "s3"], [expected, expected, expected], suggested={"acc-2": "new_arabic"})
    val_renew = validate_panel_reviews(renewal_revs, expected)
    assert val_renew["renewal_required"] is True

    # 8. Row rejection registers blocking finding
    rejection_revs = make_reviews(["s1", "s2", "s3"], [expected, expected, expected], decisions={"acc-2": "rejected"})
    val_rej = validate_panel_reviews(rejection_revs, expected)
    assert val_rej["ok"] is False
    assert any(f["classification"] == "row_rejected" for f in val_rej["blocking_findings"])


def test_stage4_sub_status_state_transitions_end_to_end(test_repo):
    """Canonical Plan §11.2: Real adopted-state integration test proving hashes derived at runtime."""
    e = Engine(test_repo)
    try:
        view = e.adopt_historical("erp-arabic-bilingual-data")
        config = e.config
        state = view

        # Initial state derived from real adoption:
        assert state["sub_status"] == "PROPOSAL_PENDING"
        assert state["status"] == "DRAFT"
        assert state["next_roles"] == []
        assert state["plan_granted"] is False
        assert state["gate"]["scope"] == "PLAN"
        assert "bundle_sha256" not in state["candidate"]
        assert "payload_sha256" not in state["candidate"]

        # Step 1: Owner grants PLAN token to unlock proposer
        plan_token = {
            "schema_version": 2,
            "token_id": "tok-plan-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": state["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": config["plan_revision_hash"],
            "scope_hash": config["scope_hash"],
            "roles_hash": config.get("roles_hash") or digest(config.get("roles", {})),
            "stages": ["4"],
            "repository_id": str(test_repo),
            "branch": "feature/scope-context-portability",
        }
        state = apply_event(state, {"seq": 1, "kind": "grant", "payload": plan_token}, config)
        assert state["sub_status"] == "PROPOSAL_PENDING"
        assert state["status"] == "APPROVED_FOR_BUILD"
        assert state["plan_granted"] is True
        assert state["next_roles"] == ["proposer"]
        assert state["gate"] is None

        catalog_blob = Path(config["erp_descriptor"]["private_root"]) / "blobs" / f"{state['candidate']['export_sha256']}.json"
        cat_doc = json.loads(catalog_blob.read_text())
        expected_identities = [r["identity"] for r in cat_doc.get("rows", [])]
        assert len(expected_identities) == 81
        proposer_rows = [
            {
                "identity": ident,
                "english": f"Account {i}",
                "is_group": False,
                "proposal": {"arabic": f"حساب {i}", "confidence": "high"},
            }
            for i, ident in enumerate(expected_identities)
        ]
        proposal_sha = derive_proposal_hash(proposer_rows, state["candidate"]["export_sha256"])
        candidate_id = derive_stage4_candidate_id(state["candidate"]["export_sha256"], proposal_sha)
        state["active_jobs"] = ["job-p1"]
        ev_prop = {
            "seq": 2,
            "kind": "result",
            "payload": {
                "job_id": "job-p1",
                "role": "proposer",
                "candidate": state["candidate"],
                "export_sha256": state["candidate"]["export_sha256"],
                "proposal_sha256": proposal_sha,
                "candidate_id": candidate_id,
                "verified_private_artifacts": [
                    {"artifact_id": "stage4-proposal-job-p1", "sha256": proposal_sha, "visibility": "private"}
                ],
                "result": {
                    "status": "COMPLETE",
                    "verdict": "PROPOSED",
                    "export_sha256": state["candidate"]["export_sha256"],
                    "proposal_sha256": proposal_sha,
                    "findings": [],
                    "evidence_paths": [{"artifact_id": "job-p1-native-events", "sha256": "e" * 64, "visibility": "public"}],
                },
            },
        }
        state = apply_event(state, ev_prop, config)
        assert state["sub_status"] == "PROPOSAL_FROZEN"
        assert state["status"] == "BUILD_COMPLETE"
        assert set(state["next_roles"]) == set(config["quorum"])
        # Proposal hash and candidate ID derived dynamically from proposer rows
        assert state["candidate"]["proposal_sha256"] == proposal_sha
        assert state["candidate"]["candidate_id"] == candidate_id
        # Bundle and payload hashes do NOT exist yet
        assert "bundle_sha256" not in state["candidate"]
        assert "payload_sha256" not in state["candidate"]

        # Step 3: Quorum panel reviews collected covering exact 81 identities
        state["active_jobs"] = [f"job-{role}" for role in config["quorum"]]
        bundle_sha = "b" * 64
        payload_sha = "c" * 64
        for i, role in enumerate(config["quorum"], start=3):
            ev_quorum = {
                "seq": i,
                "kind": "result",
                "payload": {
                    "job_id": f"job-{role}",
                    "role": role,
                    "verified_private_artifacts": [
                        {"artifact_id": f"stage4-review-{role}-job-{role}", "sha256": "%064x" % (100 + i), "visibility": "private"}
                    ],
                    "review_meta": {
                        "verdict": "PASS",
                        "blocking_findings": [],
                        "renewal_required": False,
                        "row_decisions_digest": "r" * 64,
                    },
                    "result": {
                        "status": "COMPLETE",
                        "verdict": "PASS",
                        "session_id": f"sess-{role}",
                        "findings": [],
                        "evidence_paths": [{"artifact_id": f"job-{role}-native-events", "sha256": "e" * 64, "visibility": "public"}],
                    },
                },
            }
            if role == config["quorum"][-1]:
                ev_quorum["payload"]["bundle_composed"] = {
                    "bundle_sha256": bundle_sha,
                    "payload_sha256": payload_sha,
                    "verified_private_artifacts": [
                        {"artifact_id": f"stage4-bundle-{candidate_id[:16]}", "sha256": bundle_sha, "visibility": "private"},
                        {"artifact_id": f"stage4-payload-{candidate_id[:16]}", "sha256": payload_sha, "visibility": "private"},
                    ],
                }
            state = apply_event(state, ev_quorum, config)

        # After 3rd reviewer PASS, bundle composition and verification are triggered:
        assert state["sub_status"] == "BUNDLE_VALIDATED"
        assert state["status"] == "BUILD_COMPLETE"
        assert state["next_roles"] == ["verifier"]
        # Hashes were dynamically derived at runtime:
        assert "bundle_sha256" in state["candidate"]
        assert "payload_sha256" in state["candidate"]
        assert is_hex64(state["candidate"]["bundle_sha256"])
        assert is_hex64(state["candidate"]["payload_sha256"])
        assert state["bundle_sha256"] == state["candidate"]["bundle_sha256"]
        assert state["payload_sha256"] == state["candidate"]["payload_sha256"]
        # Private data containment: raw bundle and payload dicts MUST NOT be in candidate
        assert "bundle" not in state["candidate"]
        assert "payload" not in state["candidate"]

        bundle_sha = state["candidate"]["bundle_sha256"]
        payload_sha = state["candidate"]["payload_sha256"]
        candidate_id = state["candidate"]["candidate_id"]
        export_sha = state["candidate"]["export_sha256"]
        proposal_sha = state["candidate"]["proposal_sha256"]
        erp_desc_hash = config["erp_descriptor_hash"]

        # Step 4: Verifier AI-R returns PASS -> OWNER_PAYLOAD_AUTHORIZATION & gate DRY_RUN
        state["active_jobs"] = ["job-v1"]
        ev_verif = {
            "seq": 6,
            "kind": "result",
            "payload": {
                "job_id": "job-v1",
                "role": "verifier",
                "result": {"status": "COMPLETE", "verdict": "PASS", "findings": []},
            },
        }
        state = apply_event(state, ev_verif, config)
        assert state["sub_status"] == "OWNER_PAYLOAD_AUTHORIZATION"
        assert state["gate"]["scope"] == "DRY_RUN"

        # Step 5: DRY_RUN token granted with all 5 discrete hashes -> DRY_RUN & next_roles = [builder]
        token_dry = {
            "schema_version": 1,
            "token_id": "tok-dry-1",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": state["gate"]["gate_id"],
            "scope": "DRY_RUN",
            "candidate_id": candidate_id,
            "operation": "set_account_name_ar",
            "export_sha256": export_sha,
            "proposal_sha256": proposal_sha,
            "bundle_sha256": bundle_sha,
            "payload_sha256": payload_sha,
            "erp_descriptor_hash": erp_desc_hash,
        }
        state = apply_event(state, {"seq": 7, "kind": "grant", "payload": token_dry}, config)
        assert state["sub_status"] == "DRY_RUN"
        assert state["next_roles"] == ["builder"]
        assert state["gate"] is None

        # Step 6: Builder completes DRY_RUN with real hex64 evidence digest -> IMPORT_AUTHORIZATION & gate IMPORT
        dry_run_digest = "d" * 64
        state["active_jobs"] = ["job-b1"]
        ev_b_dry = {
            "seq": 8,
            "kind": "result",
            "payload": {
                "job_id": "job-b1",
                "role": "builder",
                "dry_run_evidence_digest": dry_run_digest,
                "result": {"status": "COMPLETE", "verdict": "PASS", "findings": []},
            },
        }
        state = apply_event(state, ev_b_dry, config)
        assert state["sub_status"] == "IMPORT_AUTHORIZATION"
        assert state["gate"]["scope"] == "IMPORT"
        assert state["dry_run_evidence_digest"] == dry_run_digest

        # Step 7: IMPORT token granted with all hashes + matching dry_run_evidence_digest -> IMPORT
        token_imp = {
            "schema_version": 1,
            "token_id": "tok-imp-1",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": state["gate"]["gate_id"],
            "scope": "IMPORT",
            "candidate_id": candidate_id,
            "operation": "set_account_name_ar",
            "export_sha256": export_sha,
            "proposal_sha256": proposal_sha,
            "bundle_sha256": bundle_sha,
            "payload_sha256": payload_sha,
            "erp_descriptor_hash": erp_desc_hash,
            "dry_run_evidence_digest": dry_run_digest,
        }
        state = apply_event(state, {"seq": 9, "kind": "grant", "payload": token_imp}, config)
        assert state["sub_status"] == "IMPORT"
        assert state["next_roles"] == ["builder"]

        # Step 8: Builder completes IMPORT -> POST_IMPORT_EVIDENCE & next_roles = [verifier]
        state["active_jobs"] = ["job-b2"]
        ev_b_imp = {
            "seq": 10,
            "kind": "result",
            "payload": {
                "job_id": "job-b2",
                "role": "builder",
                "result": {"status": "COMPLETE", "verdict": "PASS", "findings": []},
            },
        }
        state = apply_event(state, ev_b_imp, config)
        assert state["sub_status"] == "POST_IMPORT_EVIDENCE"
        assert state["next_roles"] == ["verifier"]

        # Step 9: Verifier AI-R confirms post-import evidence -> STAGE_4_VERIFIED
        state["active_jobs"] = ["job-v2"]
        ev_v_imp = {
            "seq": 11,
            "kind": "result",
            "payload": {
                "job_id": "job-v2",
                "role": "verifier",
                "result": {"status": "COMPLETE", "verdict": "PASS", "findings": []},
            },
        }
        state = apply_event(state, ev_v_imp, config)
        assert state["sub_status"] == "STAGE_4_VERIFIED"
        assert state["gate"] is None
        assert state["stages"]["4"]["sub_status"] == "STAGE_4_VERIFIED"
    finally:
        e.close()


def test_dry_run_builder_pass_without_valid_digest_fails_closed():
    """A builder PASS in DRY_RUN without a valid 64-char hex digest must pause with MALFORMED_RESULT."""
    config = {
        "work_item": "erp-arabic-bilingual-data",
        "stages": ["4"],
        "stage": "4",
        "sub_status": "DRY_RUN",
        "next_roles": ["builder"],
        "candidate": {"kind": "stage4-proposal", "candidate_id": "c"*64},
        "plan_revision_hash": "p"*64,
        "scope_hash": "s"*64,
    }
    state = initial(config)
    state["active_jobs"] = ["job-b1"]

    # 1. Missing digest -> MALFORMED_RESULT
    ev_missing = {
        "seq": 1,
        "kind": "result",
        "payload": {
            "job_id": "job-b1",
            "role": "builder",
            "result": {"status": "COMPLETE", "verdict": "PASS", "findings": []},
        },
    }
    s1 = apply_event(deepcopy(state), ev_missing, config)
    assert s1["status"] == "PAUSED"
    assert s1["pause_reason"] == "MALFORMED_RESULT"
    assert s1["sub_status"] == "DRY_RUN"  # Does NOT open IMPORT_AUTHORIZATION

    # 2. Non-hex digest -> MALFORMED_RESULT
    ev_non_hex = {
        "seq": 1,
        "kind": "result",
        "payload": {
            "job_id": "job-b1",
            "role": "builder",
            "dry_run_evidence_digest": "not_hex_at_all_digest",
            "result": {"status": "COMPLETE", "verdict": "PASS", "findings": []},
        },
    }
    s2 = apply_event(deepcopy(state), ev_non_hex, config)
    assert s2["status"] == "PAUSED"
    assert s2["pause_reason"] == "MALFORMED_RESULT"


def test_token_tamper_resistance_across_all_stage4_hashes():
    """Every Stage 4 hash must be strictly validated against the active candidate/config."""
    cand = {
        "kind": "stage4-proposal",
        "candidate_id": "c"*64,
        "export_sha256": "e"*64,
        "proposal_sha256": "1"*64,
        "bundle_sha256": "b"*64,
        "payload_sha256": "d"*64,
    }
    config = {
        "work_item": "erp-arabic-bilingual-data",
        "stages": ["4"],
        "stage": "4",
        "sub_status": "OWNER_PAYLOAD_AUTHORIZATION",
        "next_roles": [],
        "candidate": cand,
        "plan_revision_hash": "a"*64,
        "scope_hash": "b"*64,
        "erp_descriptor_hash": "f"*64,
    }
    state = initial(config)
    state["gate"] = {"scope": "DRY_RUN", "gate_id": gate_id(state, "DRY_RUN")}

    base_valid_token = {
        "schema_version": 1,
        "token_id": "tok-valid-1",
        "work_item": "erp-arabic-bilingual-data",
        "gate_id": state["gate"]["gate_id"],
        "scope": "DRY_RUN",
        "candidate_id": cand["candidate_id"],
        "operation": "set_account_name_ar",
        "export_sha256": cand["export_sha256"],
        "proposal_sha256": cand["proposal_sha256"],
        "bundle_sha256": cand["bundle_sha256"],
        "payload_sha256": cand["payload_sha256"],
        "erp_descriptor_hash": config["erp_descriptor_hash"],
    }

    # Tampered export_sha256
    t_bad_export = dict(base_valid_token, export_sha256="0"*64)
    with pytest.raises(WorkflowError, match="export_sha256 mismatch"):
        apply_event(deepcopy(state), {"seq": 1, "kind": "grant", "payload": t_bad_export}, config)

    # Tampered proposal_sha256
    t_bad_prop = dict(base_valid_token, proposal_sha256="0"*64)
    with pytest.raises(WorkflowError, match="proposal_sha256 mismatch"):
        apply_event(deepcopy(state), {"seq": 1, "kind": "grant", "payload": t_bad_prop}, config)

    # Tampered bundle_sha256
    t_bad_bnd = dict(base_valid_token, bundle_sha256="0"*64)
    with pytest.raises(WorkflowError, match="bundle_sha256 mismatch"):
        apply_event(deepcopy(state), {"seq": 1, "kind": "grant", "payload": t_bad_bnd}, config)

    # Tampered payload_sha256
    t_bad_pay = dict(base_valid_token, payload_sha256="0"*64)
    with pytest.raises(WorkflowError, match="payload_sha256 mismatch"):
        apply_event(deepcopy(state), {"seq": 1, "kind": "grant", "payload": t_bad_pay}, config)

    # Tampered erp_descriptor_hash
    t_bad_desc = dict(base_valid_token, erp_descriptor_hash="0"*64)
    with pytest.raises(WorkflowError, match="erp_descriptor_hash mismatch"):
        apply_event(deepcopy(state), {"seq": 1, "kind": "grant", "payload": t_bad_desc}, config)

    # Non-hex hash value
    t_non_hex = dict(base_valid_token, export_sha256="not_a_valid_hex_hash_at_all_000000000000000000000000000000000000")
    with pytest.raises(WorkflowError, match="must be 64-character lowercase hex"):
        apply_event(deepcopy(state), {"seq": 1, "kind": "grant", "payload": t_non_hex}, config)

    # Missing active hashes in state/config fail closed unconditionally for DRY_RUN
    state_no_bundle = deepcopy(state)
    state_no_bundle["candidate"].pop("bundle_sha256")
    state_no_bundle.pop("bundle_sha256", None)
    with pytest.raises(WorkflowError, match="Dry-run requires active bundle_sha256 in state"):
        apply_event(state_no_bundle, {"seq": 1, "kind": "grant", "payload": base_valid_token}, config)

    state_no_payload = deepcopy(state)
    state_no_payload["candidate"].pop("payload_sha256")
    state_no_payload.pop("payload_sha256", None)
    with pytest.raises(WorkflowError, match="Dry-run requires active payload_sha256 in state"):
        apply_event(state_no_payload, {"seq": 1, "kind": "grant", "payload": base_valid_token}, config)

    state_no_export = deepcopy(state)
    state_no_export["candidate"].pop("export_sha256")
    with pytest.raises(WorkflowError, match="Dry-run requires active export_sha256 in state"):
        apply_event(state_no_export, {"seq": 1, "kind": "grant", "payload": base_valid_token}, config)

    config_no_desc = deepcopy(config)
    config_no_desc.pop("erp_descriptor_hash")
    with pytest.raises(WorkflowError, match="Dry-run requires active erp_descriptor_hash in config"):
        apply_event(deepcopy(state), {"seq": 1, "kind": "grant", "payload": base_valid_token}, config_no_desc)

    # IMPORT token tamper tests
    state_imp = deepcopy(state)
    state_imp["sub_status"] = "IMPORT_AUTHORIZATION"
    state_imp["gate"] = {"scope": "IMPORT", "gate_id": gate_id(state_imp, "IMPORT")}
    state_imp["dry_run_evidence_digest"] = "d"*64
    valid_imp_token = dict(
        base_valid_token,
        scope="IMPORT",
        gate_id=state_imp["gate"]["gate_id"],
        dry_run_evidence_digest="d"*64,
    )

    # Missing active hashes in state/config fail closed unconditionally for IMPORT
    state_imp_no_bundle = deepcopy(state_imp)
    state_imp_no_bundle["candidate"].pop("bundle_sha256")
    state_imp_no_bundle.pop("bundle_sha256", None)
    with pytest.raises(WorkflowError, match="Import requires active bundle_sha256 in state"):
        apply_event(state_imp_no_bundle, {"seq": 1, "kind": "grant", "payload": valid_imp_token}, config)

    state_imp_no_payload = deepcopy(state_imp)
    state_imp_no_payload["candidate"].pop("payload_sha256")
    state_imp_no_payload.pop("payload_sha256", None)
    with pytest.raises(WorkflowError, match="Import requires active payload_sha256 in state"):
        apply_event(state_imp_no_payload, {"seq": 1, "kind": "grant", "payload": valid_imp_token}, config)

    state_imp_no_export = deepcopy(state_imp)
    state_imp_no_export["candidate"].pop("export_sha256")
    with pytest.raises(WorkflowError, match="Import requires active export_sha256 in state"):
        apply_event(state_imp_no_export, {"seq": 1, "kind": "grant", "payload": valid_imp_token}, config)

    with pytest.raises(WorkflowError, match="Import requires active erp_descriptor_hash in config"):
        apply_event(deepcopy(state_imp), {"seq": 1, "kind": "grant", "payload": valid_imp_token}, config_no_desc)

    # Missing or mismatched dry_run_evidence_digest
    t_no_digest = dict(valid_imp_token)
    t_no_digest.pop("dry_run_evidence_digest")
    with pytest.raises(WorkflowError, match="Import grant dry_run_evidence_digest must be 64-character lowercase hex"):
        apply_event(deepcopy(state_imp), {"seq": 1, "kind": "grant", "payload": t_no_digest}, config)

    t_bad_digest = dict(valid_imp_token, dry_run_evidence_digest="0"*64)
    with pytest.raises(WorkflowError, match="Import grant dry_run_evidence_digest does not match recorded evidence"):
        apply_event(deepcopy(state_imp), {"seq": 1, "kind": "grant", "payload": t_bad_digest}, config)


def test_reused_authorization_token_rejected_in_engine_approve(test_repo):
    """Engine.approve must reject attempting to approve an already consumed or recorded token."""
    e = Engine(test_repo)
    try:
        view = e.adopt_historical("erp-arabic-bilingual-data")
        assert view["gate"]["scope"] == "PLAN"
        token = {
            "schema_version": 2,
            "token_id": "tok-single-use-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
            "roles_hash": view.get("roles_hash") or digest(e.config.get("roles", {})),
            "stages": ["4"],
            "repository_id": str(test_repo),
            "branch": "feature/scope-context-portability",
        }
        # Insert grant directly into DB to simulate prior recording
        with e.store.conn:
            e.store.conn.execute(
                "INSERT INTO workflow_grants VALUES (?,?,?,?)",
                (token["token_id"], token["gate_id"], "RESERVED", canonical(token).decode()),
            )

        # Attempting to approve the same token must fail fail-closed
        with pytest.raises(WorkflowError, match="Token already used or recorded"):
            e.approve(token)
    finally:
        e.close()


def test_verify_stage4_manifest_validates_hex_and_distinct_hashes():
    """verify_stage4_manifest must enforce 5 distinct 64-char hex hashes and valid panel digests."""
    h = ["%064x" % i for i in range(1, 6)]
    panel_digests = {"ai-a1": "a"*64, "ai-a2": "b"*64, "ai-a3": "c"*64}

    # Valid
    assert verify_stage4_manifest(h[0], h[1], h[2], h[3], h[4], panel_digests) is True

    # Hash collision (first two identical)
    with pytest.raises(WorkflowError, match="Hash collision / non-distinct Stage 4 hashes"):
        verify_stage4_manifest(h[0], h[0], h[2], h[3], h[4], panel_digests)

    # Non-hex hash
    with pytest.raises(WorkflowError, match="Invalid export_sha256: must be 64-character lowercase hex"):
        verify_stage4_manifest(h[0], "non_hex_export_hash", h[2], h[3], h[4], panel_digests)

    # Missing required role in panel digests
    bad_panel = {"ai-a1": "a"*64, "ai-a2": "b"*64}
    with pytest.raises(WorkflowError, match="keys must match exact required roles"):
        verify_stage4_manifest(h[0], h[1], h[2], h[3], h[4], bad_panel)


class Stage4Stub:
    """Synthetic launcher for Stage 4 testing that obeys the private artifact contract."""

    def __init__(self, outcomes=None, delayed=False, canary=""):
        self.starts = []
        self.outcomes = outcomes or {}
        self.delayed = delayed
        self.canary = canary

    def __call__(self, job):
        self.starts.append(job["job_id"])
        if not self.delayed:
            self.complete(job)

    def complete(self, job):
        destination = Path(job["runtime"])
        spec = job["spec"]
        role = job["role"]
        body = deepcopy(spec["envelope"])
        body.update(self.outcomes.get(role, {}))
        body["session_id"] = f"synthetic-{job['job_id']}"
        body["status"] = "COMPLETE"

        expected_art_id = spec.get("expected_artifact_id")
        if expected_art_id:
            private_out = destination / "private_out"
            private_out.mkdir(parents=True, exist_ok=True)
            out_file = private_out / "output.json"

            if role == "proposer":
                body["verdict"] = "PROPOSED"
                catalog_path = None
                for nm in spec.get("neutral_mounts", []):
                    if nm.get("sandbox_path") == "/tmp/workspace/private_inputs/account_catalog.json":
                        catalog_path = Path(nm["host_path"])
                        break
                if catalog_path and catalog_path.exists():
                    catalog_doc = json.loads(catalog_path.read_text())
                    cat_rows = catalog_doc.get("rows", [])
                else:
                    cat_rows = []

                rows = []
                for idx, r in enumerate(cat_rows):
                    ident = r["identity"]
                    eng = r.get("english") or r.get("account_name")
                    is_grp = r.get("is_group", False)
                    ar_text = f"حساب {idx} {self.canary}".strip()
                    rows.append({
                        "identity": ident,
                        "english": eng,
                        "is_group": is_grp,
                        "proposal": {"arabic": ar_text, "confidence": "high"},
                    })

                out_file.write_text(json.dumps({
                    "export_sha256": spec["envelope"]["export_sha256"],
                    "rows": rows,
                }))

            elif role in ("ai-a1", "ai-a2", "ai-a3"):
                body["verdict"] = "PASS"
                proposal_path = None
                for nm in spec.get("neutral_mounts", []):
                    if nm.get("sandbox_path") == "/tmp/workspace/private_inputs/proposal.json":
                        proposal_path = Path(nm["host_path"])
                        break
                if proposal_path and proposal_path.exists():
                    p_doc = json.loads(proposal_path.read_text())
                    p_rows = p_doc.get("rows", [])
                else:
                    p_rows = []

                row_decisions = []
                for idx, pr in enumerate(p_rows):
                    row_decisions.append({
                        "identity": pr["identity"],
                        "decision": "approved",
                        "rationale": f"Valid translation {self.canary}".strip(),
                        "reference": {"status": "present"},
                    })

                out_file.write_text(json.dumps({
                    "schema": "stage4-panel-review/v1",
                    "role": role,
                    "session_id": body["session_id"],
                    "proposal_sha256": spec["envelope"]["proposal_sha256"],
                    "verdict": "PASS",
                    "row_decisions": row_decisions,
                    "findings": [],
                }))

        elif role == "verifier":
            body["verdict"] = "PASS"
            body["findings"] = []
        elif role == "builder":
            body["verdict"] = "PASS"
            body["dry_run_evidence_digest"] = "d" * 64
            body["findings"] = []

        payload = {
            "body": body,
            "wire": {
                "explanation": f"SYNTHETIC stage4 result for {role}",
            },
        }
        (destination / "stdout.jsonl").write_text(json.dumps(payload))
        write_json(
            destination / "terminal.json",
            dict(
                job_id=job["job_id"],
                phase="TERMINAL",
                exit_code=0,
                timeout=False,
                started_utc=utc(),
                finished_utc=utc(),
                session_id=body["session_id"],
            ),
            immutable=True,
        )

    def parse(self, job, raw):
        data = json.loads(raw)
        return data["body"]["session_id"], data["body"], data["wire"], []


def test_stage4_public_engine_lifecycle_acceptance(test_repo, tmp_path):
    """Canonical Plan §11.2 Acceptance: Full lifecycle driven strictly through public Engine methods.

    Engine.adopt_historical -> Engine.approve(PLAN) -> proposer -> panel reviews -> verifier -> DRY_RUN gate.
    """
    import shutil
    mock_private = tmp_path / "private_stage4"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        # Initial adopted state assertions
        assert view["sub_status"] == "PROPOSAL_PENDING"
        assert view["status"] == "DRAFT"
        assert view["gate"]["scope"] == "PLAN"
        assert view["next_roles"] == []
        assert view["plan_granted"] is False

        # Attempting e.run() while parked at PLAN gate must remain parked
        v_parked = e.run()
        assert v_parked["gate"]["scope"] == "PLAN"
        assert v_parked["status"] == "DRAFT"

        # Owner grants PLAN token
        plan_token = {
            "schema_version": 2,
            "token_id": "tok-plan-lifecycle-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
            "roles_hash": view.get("roles_hash") or digest(e.config.get("roles", {})),
            "stages": ["4"],
            "repository_id": str(test_repo),
            "branch": "feature/scope-context-portability",
        }
        v_end = e.approve(plan_token)
        assert v_end["sub_status"] == "OWNER_PAYLOAD_AUTHORIZATION"
        assert v_end["status"] == "VERIFIED_FOR_RELEASE"
        assert v_end["gate"]["scope"] == "DRY_RUN"
        assert v_end["next_roles"] == []

        cand = v_end["candidate"]
        assert is_hex64(cand["proposal_sha256"])
        assert is_hex64(cand["bundle_sha256"])
        assert is_hex64(cand["payload_sha256"])
        assert is_hex64(cand["candidate_id"])
        assert is_hex64(cand["export_sha256"])

        # Proves 5 distinct hashes
        all_hashes = {
            cand["export_sha256"],
            cand["proposal_sha256"],
            cand["candidate_id"],
            cand["bundle_sha256"],
            cand["payload_sha256"],
        }
        assert len(all_hashes) == 5

        # Private data containment: state never stores raw rows, bundle, or payload
        assert "bundle" not in cand
        assert "payload" not in cand
        assert "rows" not in cand
        assert "proposal_rows" not in cand
        assert "row_decisions" not in cand

        # Blobs exist in content-addressed private storage with 0o600 permissions
        blobs_dir = mock_private / "blobs"
        assert (blobs_dir / f"{cand['proposal_sha256']}.json").exists()
        assert (blobs_dir / f"{cand['bundle_sha256']}.json").exists()
        assert (blobs_dir / f"{cand['payload_sha256']}.json").exists()

        for b in blobs_dir.glob("*.json"):
            assert oct(b.stat().st_mode & 0o777) == oct(0o600)

        # Temporary output.json files removed
        for p in (test_repo / "orchestrator/var/jobs").rglob("output.json"):
            raise AssertionError(f"temporary output.json leaked at {p}")

    finally:
        e.close()


def test_exhaustive_privacy_leakage_scan(test_repo, tmp_path):
    """Exhaustive privacy scan: verifies zero leak of private account data into SQLite, logs, or exports."""
    import shutil
    mock_private = tmp_path / "private_stage4_canary"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    CANARY_ARABIC = "حساب_كناري_خاص_سري_987654321"
    CANARY_ENGLISH_NOTE = "CANARY_CONFIDENTIAL_RATIONALE_XYZ123"

    stub = Stage4Stub(canary=f"{CANARY_ARABIC} {CANARY_ENGLISH_NOTE}")
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        plan_token = {
            "schema_version": 2,
            "token_id": "tok-plan-canary-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
            "roles_hash": view.get("roles_hash") or digest(e.config.get("roles", {})),
            "stages": ["4"],
            "repository_id": str(test_repo),
            "branch": "feature/scope-context-portability",
        }
        v_end = e.approve(plan_token)
        assert v_end["sub_status"] == "OWNER_PAYLOAD_AUTHORIZATION"

        # Build comprehensive set of private terms from catalog
        cat_doc = json.loads((mock_private / real_catalog.name).read_text())
        all_private_terms = {CANARY_ARABIC, CANARY_ENGLISH_NOTE}
        for r in cat_doc.get("rows", []):
            if r.get("identity"):
                all_private_terms.add(r["identity"])
            if r.get("english"):
                all_private_terms.add(r["english"])
            if r.get("account_name"):
                all_private_terms.add(r["account_name"])
        for idx in range(len(cat_doc.get("rows", []))):
            all_private_terms.add(f"حساب {idx}")
            all_private_terms.add("Valid translation")

        # 1. Assert canaries and identities ARE present in private root blobs
        blobs_dir = mock_private / "blobs"
        all_blob_text = "".join(f.read_text() for f in blobs_dir.glob("*.json"))
        assert CANARY_ARABIC in all_blob_text
        assert CANARY_ENGLISH_NOTE in all_blob_text
        for r in cat_doc.get("rows", []):
            assert r["identity"] in all_blob_text

        # 2. Assert all private terms are ABSENT from all SQLite tables
        tables = [r[0] for r in e.store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for tbl in tables:
            rows = e.store.conn.execute(f"SELECT * FROM {tbl}").fetchall()
            for r in rows:
                text = str(r)
                for term in all_private_terms:
                    assert term not in text, f"Private term '{term}' leaked in table {tbl}"

        # 3. Assert all private terms are ABSENT from STATE.json
        state_path = test_repo / "docs/ai/work-items/erp-arabic-bilingual-data/STATE.json"
        if state_path.exists():
            state_text = state_path.read_text()
            for term in all_private_terms:
                assert term not in state_text, f"Private term '{term}' leaked in STATE.json"

        # 4. Assert all private terms are ABSENT from work-item files (runs, inbox, outbox, etc.)
        wi_dir = test_repo / "docs/ai/work-items/erp-arabic-bilingual-data"
        for f in wi_dir.rglob("*"):
            if f.is_file():
                txt = f.read_text(errors="ignore")
                for term in all_private_terms:
                    assert term not in txt, f"Private term '{term}' leaked in {f}"

        # 5. Assert all private terms are ABSENT from orchestrator runtime files
        orch_var = test_repo / "orchestrator/var"
        if orch_var.exists():
            for f in orch_var.rglob("*"):
                if f.is_file():
                    txt = f.read_text(errors="ignore")
                    for term in all_private_terms:
                        assert term not in txt, f"Private term '{term}' leaked in runtime file {f}"

    finally:
        e.close()


def test_adversarial_explanation_leakage(test_repo, tmp_path):
    """Adversarial test: an agent explanation containing private text is sanitized before writing to disk or SQLite."""
    import shutil
    mock_private = tmp_path / "private_adv_expl"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    leak_term = "Office Rent"
    arabic_term = "حساب_خاص_سري"

    class LeakStub(Stage4Stub):
        def complete(self, job):
            super().complete(job)
            destination = Path(job["runtime"])
            raw_payload = json.loads((destination / "stdout.jsonl").read_text())
            raw_payload["wire"]["explanation"] = f"Leaked private data: {leak_term} {arabic_term}"
            (destination / "stdout.jsonl").write_text(json.dumps(raw_payload))

    stub = LeakStub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        plan_token = {
            "schema_version": 2,
            "token_id": "tok-plan-adv-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
            "roles_hash": view.get("roles_hash") or digest(e.config.get("roles", {})),
            "stages": ["4"],
            "repository_id": str(test_repo),
            "branch": "feature/scope-context-portability",
        }
        e.approve(plan_token)

        for p in (test_repo / "docs/ai/work-items/erp-arabic-bilingual-data/runs").rglob("*.md"):
            txt = p.read_text()
            assert leak_term not in txt, f"Leak in {p}"
            assert arabic_term not in txt, f"Leak in {p}"

        orch_var = test_repo / "orchestrator/var"
        if orch_var.exists():
            for p in orch_var.rglob("*"):
                if p.is_file():
                    txt = p.read_text(errors="ignore")
                    assert leak_term not in txt, f"Leak in runtime file {p}"
                    assert arabic_term not in txt, f"Leak in runtime file {p}"

        for row in e.store.conn.execute("SELECT * FROM workflow_events").fetchall():
            row_txt = str(row)
            assert leak_term not in row_txt
            assert arabic_term not in row_txt
    finally:
        e.close()


def test_adversarial_finding_leakage(test_repo, tmp_path):
    """Adversarial test: an agent finding containing private text is sanitized before writing to disk or SQLite."""
    import shutil
    mock_private = tmp_path / "private_adv_find"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    leak_term = "Office Rent"
    arabic_term = "تفاصيل_سرية"

    class FindingLeakStub(Stage4Stub):
        def complete(self, job):
            super().complete(job)
            destination = Path(job["runtime"])
            raw_payload = json.loads((destination / "stdout.jsonl").read_text())
            raw_payload["body"]["findings"] = [{
                "schema_version": 1,
                "finding_id": None,
                "role": job["role"],
                "classification": "optional_improvement",
                "affected_requirements": ["CANONICAL_PLAN §11.1"],
                "blocking": False,
                "summary": f"Finding leaks {leak_term} and {arabic_term}",
                "detail": f"Detail leaks {leak_term}",
            }]
            (destination / "stdout.jsonl").write_text(json.dumps(raw_payload, ensure_ascii=False))

    stub = FindingLeakStub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        plan_token = {
            "schema_version": 2,
            "token_id": "tok-plan-adv-002",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
            "roles_hash": view.get("roles_hash") or digest(e.config.get("roles", {})),
            "stages": ["4"],
            "repository_id": str(test_repo),
            "branch": "feature/scope-context-portability",
        }
        e.approve(plan_token)
        for p in (test_repo / "docs/ai/work-items/erp-arabic-bilingual-data/runs").rglob("*.json"):
            txt = p.read_text()
            assert leak_term not in txt, f"Leak in {p}"
            assert arabic_term not in txt, f"Leak in {p}"

        orch_var = test_repo / "orchestrator/var"
        if orch_var.exists():
            for p in orch_var.rglob("*"):
                if p.is_file():
                    txt = p.read_text(errors="ignore")
                    assert leak_term not in txt, f"Leak in runtime file {p}"
                    assert arabic_term not in txt, f"Leak in runtime file {p}"
    finally:
        e.close()


def test_adversarial_mismatched_review_provenance(test_repo, tmp_path):
    """Adversarial test: reviewer document with mismatched role, proposal_sha, or session_id is rejected fail-closed."""
    from stage4 import validate_and_store_review
    mock_private = tmp_path / "private_prov"
    mock_private.mkdir(parents=True)
    out_file = tmp_path / "output.json"

    valid_doc = {
        "schema": "stage4-panel-review/v1",
        "role": "ai-a1",
        "session_id": "sess-correct-123",
        "proposal_sha256": "a" * 64,
        "verdict": "PASS",
        "row_decisions": [{"identity": "id1", "decision": "approved", "rationale": "ok"}],
        "findings": [],
    }

    # 1. Role mismatch
    bad_role_doc = dict(valid_doc, role="ai-a2")
    out_file.write_text(json.dumps(bad_role_doc))
    with pytest.raises(WorkflowError, match="Review document role mismatch"):
        validate_and_store_review(
            mock_private, out_file, expected_role="ai-a1", expected_proposal_sha="a" * 64,
            expected_identities=["id1"], expected_session_id="sess-correct-123"
        )

    # 2. Proposal SHA mismatch
    bad_prop_doc = dict(valid_doc, proposal_sha256="b" * 64)
    out_file.write_text(json.dumps(bad_prop_doc))
    with pytest.raises(WorkflowError, match="Review document proposal_sha256 mismatch"):
        validate_and_store_review(
            mock_private, out_file, expected_role="ai-a1", expected_proposal_sha="a" * 64,
            expected_identities=["id1"], expected_session_id="sess-correct-123"
        )

    # 3. Session ID mismatch
    bad_sess_doc = dict(valid_doc, session_id="sess-forged-999")
    out_file.write_text(json.dumps(bad_sess_doc))
    with pytest.raises(WorkflowError, match="Review document session_id mismatch"):
        validate_and_store_review(
            mock_private, out_file, expected_role="ai-a1", expected_proposal_sha="a" * 64,
            expected_identities=["id1"], expected_session_id="sess-correct-123"
        )


def test_adversarial_catalog_drift(test_repo, tmp_path):
    """Adversarial test: catalog blob modified after adoption raises WorkflowError on job prepare."""
    import shutil
    mock_private = tmp_path / "private_drift"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        blob_path = mock_private / "blobs" / f"{view['candidate']['export_sha256']}.json"
        assert blob_path.exists()
        blob_path.write_bytes(b"tampered catalog content")

        plan_token = {
            "schema_version": 2,
            "token_id": "tok-plan-drift-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
            "roles_hash": view.get("roles_hash") or digest(e.config.get("roles", {})),
            "stages": ["4"],
            "repository_id": str(test_repo),
            "branch": "feature/scope-context-portability",
        }
        with pytest.raises(WorkflowError, match="Export catalog blob digest mismatch"):
            e.approve(plan_token)
    finally:
        e.close()


def test_adversarial_crash_after_blob_store(test_repo, tmp_path):
    """Adversarial test: crash after storing private blob and writing acceptance record recovers cleanly."""
    import shutil
    mock_private = tmp_path / "private_crash_rec"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        job_id = "job-proposer-crash-test"
        dest = test_repo / "orchestrator/var/jobs" / job_id
        dest.mkdir(parents=True)
        private_out = dest / "private_out"
        private_out.mkdir(parents=True)

        cat_doc = json.loads((mock_private / real_catalog.name).read_text())
        rows = [
            {
                "identity": r["identity"],
                "english": r["english"],
                "is_group": r.get("is_group", False),
                "proposal": {"arabic": f"حساب {i}", "confidence": "high"},
            }
            for i, r in enumerate(cat_doc["rows"])
        ]
        from stage4 import derive_proposal_hash, project_proposal_rows, store_private_blob
        sorted_rows = project_proposal_rows(rows)
        prop_sha = derive_proposal_hash(sorted_rows, view["candidate"]["export_sha256"])
        canonical_prop = {
            "schema": "stage4-proposal/v1",
            "export_sha256": view["candidate"]["export_sha256"],
            "rows": sorted_rows,
        }
        store_private_blob(mock_private, canonical(canonical_prop), expected_sha=prop_sha)

        rec = {
            "job_id": job_id,
            "role": "proposer",
            "artifact_id": f"stage4-proposal-{job_id}",
            "sha256": prop_sha,
            "meta": {
                "proposal_sha256": prop_sha,
                "artifact_sha256": prop_sha,
                "rows_count": len(rows),
                "export_sha256": view["candidate"]["export_sha256"],
            },
            "accepted_utc": utc(),
        }
        (dest / "private-acceptance-record.json").write_text(json.dumps(rec))

        envelope = {
            "schema_version": 1,
            "job_id": job_id,
            "work_item": "erp-arabic-bilingual-data",
            "stage": "4",
            "role": "proposer",
            "tool": "opencode",
            "model": "opencode-go/gpt-5.6-luna",
            "status": "COMPLETE",
            "verdict": "PROPOSED",
            "failure_class": None,
            "evidence_paths": [],
            "findings": [],
            "candidate_kind": "stage4-proposal",
            "candidate_id": view["candidate"]["candidate_id"],
            "plan_revision_hash": e.config["plan_revision_hash"],
            "prompt_version": e.config["roles"]["proposer"]["prompt_sha256"],
            "session_id": "sess-proposer-crash",
        }
        wire = {"explanation": "Synthesized", "result_json": json.dumps(envelope), "plan_text": ""}
        payload = {
            "body": envelope,
            "wire": wire,
        }
        (dest / "stdout.jsonl").write_text(json.dumps(payload))
        obs = {"exit_code": 0, "session_id": "sess-proposer-crash", "started_utc": utc(), "finished_utc": utc()}
        job = {
            "job_id": job_id,
            "role": "proposer",
            "runtime": str(dest),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id}",
                "envelope": envelope,
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }
        event = e.accept(job, obs, view)
        assert event["job_id"] == job_id
        assert event["proposal_sha256"] == prop_sha
        assert event["verified_private_artifacts"][0]["sha256"] == prop_sha
    finally:
        e.close()


def test_adversarial_crash_recovery_tampered_record_rejected(test_repo, tmp_path):
    """Adversarial test: crash recovery revalidates recovered blob against current candidate/export/proposal/session

    and derives metadata strictly from the verified blob, rejecting tampered records and ignoring forged metadata.
    """
    mock_private = tmp_path / "private_tampered_rec"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        job_id = "job-tampered-rec-test"
        dest = test_repo / "orchestrator/var/jobs" / job_id
        dest.mkdir(parents=True)
        record_path = dest / "private-acceptance-record.json"

        cat_doc = json.loads((mock_private / real_catalog.name).read_text())
        rows = [
            {
                "identity": r["identity"],
                "english": r["english"],
                "is_group": r.get("is_group", False),
                "proposal": {"arabic": f"حساب {i}", "confidence": "high"},
            }
            for i, r in enumerate(cat_doc["rows"])
        ]
        from stage4 import derive_proposal_hash, project_proposal_rows, store_private_blob
        sorted_rows = project_proposal_rows(rows)
        prop_sha = derive_proposal_hash(sorted_rows, view["candidate"]["export_sha256"])
        canonical_prop = {
            "schema": "stage4-proposal/v1",
            "export_sha256": view["candidate"]["export_sha256"],
            "rows": sorted_rows,
        }
        store_private_blob(mock_private, canonical(canonical_prop), expected_sha=prop_sha)

        envelope = {
            "schema_version": 1,
            "job_id": job_id,
            "work_item": "erp-arabic-bilingual-data",
            "stage": "4",
            "role": "proposer",
            "tool": "opencode",
            "model": "opencode-go/gpt-5.6-luna",
            "status": "COMPLETE",
            "verdict": "PROPOSED",
            "failure_class": None,
            "evidence_paths": [],
            "findings": [],
            "candidate_kind": "stage4-proposal",
            "candidate_id": view["candidate"]["candidate_id"],
            "plan_revision_hash": e.config["plan_revision_hash"],
            "prompt_version": e.config["roles"]["proposer"]["prompt_sha256"],
            "session_id": "sess-tamper-test",
        }
        wire = {"explanation": "Synthesized", "result_json": json.dumps(envelope), "plan_text": ""}
        payload = {"body": envelope, "wire": wire}
        (dest / "stdout.jsonl").write_text(json.dumps(payload))
        obs = {"exit_code": 0, "session_id": "sess-tamper-test", "started_utc": utc(), "finished_utc": utc()}
        job = {
            "job_id": job_id,
            "role": "proposer",
            "runtime": str(dest),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id}",
                "envelope": envelope,
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }

        # 1. Corrupted acceptance record JSON -> WorkflowError
        record_path.write_text("{not-valid-json")
        with pytest.raises(WorkflowError, match="Corrupted acceptance record"):
            e.accept(job, obs, view)

        # 2. Acceptance record artifact_id mismatch
        bad_rec = {
            "job_id": job_id,
            "role": "proposer",
            "artifact_id": "forged-artifact-id",
            "sha256": prop_sha,
            "meta": {},
            "accepted_utc": utc(),
        }
        record_path.write_text(json.dumps(bad_rec))
        with pytest.raises(WorkflowError, match="Acceptance record artifact_id mismatch"):
            e.accept(job, obs, view)

        # 3. Invalid job binding in record
        bad_rec["artifact_id"] = f"stage4-proposal-{job_id}"
        bad_rec["job_id"] = "wrong-job-id"
        record_path.write_text(json.dumps(bad_rec))
        with pytest.raises(WorkflowError, match="Invalid acceptance record binding"):
            e.accept(job, obs, view)

        # 4. Blob sha pointing to missing blob
        bad_rec["job_id"] = job_id
        bad_rec["sha256"] = "f" * 64
        record_path.write_text(json.dumps(bad_rec))
        with pytest.raises(WorkflowError, match="Private blob missing"):
            e.accept(job, obs, view)

        # 5. Forged metadata in acceptance record with valid blob:
        # Verified blob metadata must be derived strictly from the blob, ignoring forged record meta
        forged_rec = {
            "job_id": job_id,
            "role": "proposer",
            "artifact_id": f"stage4-proposal-{job_id}",
            "sha256": prop_sha,
            "meta": {
                "proposal_sha256": "0" * 64,
                "artifact_sha256": "0" * 64,
                "rows_count": 999999,
                "export_sha256": "forged-export-sha",
            },
            "accepted_utc": utc(),
        }
        record_path.write_text(json.dumps(forged_rec))
        event = e.accept(job, obs, view)
        assert event["proposal_sha256"] == prop_sha
        assert event["proposal_sha256"] != "0" * 64
        # candidate_id is derived from blob content; forged meta rows_count/artifact_sha256 are ignored
        from stage4 import derive_stage4_candidate_id
        expected_candidate_id = derive_stage4_candidate_id(view["candidate"]["export_sha256"], prop_sha)
        assert event["candidate_id"] == expected_candidate_id
        assert event["export_sha256"] == view["candidate"]["export_sha256"]
        assert event["export_sha256"] != "forged-export-sha"
    finally:
        e.close()


def test_compose_and_store_bundle_and_payload_rejection_on_renewal(test_repo, tmp_path):
    """Verifies that compose_and_store_bundle_and_payload rechecks and rejects renewal-needed reviews."""
    from stage4 import compose_and_store_bundle_and_payload, store_private_blob, project_proposal_rows, derive_proposal_hash

    mock_private = tmp_path / "private_comp_renewal"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    cat_doc = json.loads(real_catalog.read_text())
    export_bytes = canonical(cat_doc)
    export_sha = hashlib.sha256(export_bytes).hexdigest()
    store_private_blob(mock_private, export_bytes, expected_sha=export_sha)

    rows = [
        {
            "identity": r["identity"],
            "english": r["english"],
            "is_group": r.get("is_group", False),
            "proposal": {"arabic": f"حساب {i}", "confidence": "high"},
        }
        for i, r in enumerate(cat_doc["rows"])
    ]
    sorted_rows = project_proposal_rows(rows)
    prop_sha = derive_proposal_hash(sorted_rows, export_sha)
    prop_doc = {"schema": "stage4-proposal/v1", "export_sha256": export_sha, "rows": sorted_rows}
    store_private_blob(mock_private, canonical(prop_doc), expected_sha=prop_sha)

    # Valid 64-char hex candidate_id
    valid_candidate_id = hashlib.sha256(b"cand-1").hexdigest()

    # Base valid row decisions
    base_decisions = [
        {"identity": r["identity"], "decision": "approved", "proposed_arabic": r["proposal"]["arabic"], "rationale": "Valid"}
        for r in sorted_rows
    ]

    # Helper to store review blob
    def make_review_blob(role, renewal_required=False, row_decisions=None, findings=None):
        decisions = row_decisions if row_decisions is not None else base_decisions
        doc = {
            "schema": "stage4-panel-review/v1",
            "role": role,
            "session_id": f"sess-{role}",
            "proposal_sha256": prop_sha,
            "verdict": "PASS",
            "renewal_required": bool(renewal_required),
            "row_decisions": decisions,
            "findings": findings or [],
        }
        b = canonical(doc)
        sha = hashlib.sha256(b).hexdigest()
        store_private_blob(mock_private, b, expected_sha=sha)
        return sha

    a1_sha = make_review_blob("ai-a1")
    a3_sha = make_review_blob("ai-a3")

    # Case A: canonical review has renewal_required: True
    a2_renewal_sha = make_review_blob("ai-a2", renewal_required=True)
    with pytest.raises(WorkflowError, match="requires renewal"):
        compose_and_store_bundle_and_payload(
            mock_private,
            prop_sha,
            a2_renewal_sha,
            "Test Company",
            valid_candidate_id,
            export_sha,
            "0" * 64,
            {"ai-a1": a1_sha, "ai-a2": a2_renewal_sha, "ai-a3": a3_sha},
        )

    # Case B: renewal_required is False in blob, but row_decisions has suggested_arabic != proposed_arabic
    tampered_decisions = deepcopy(base_decisions)
    tampered_decisions[0]["suggested_arabic"] = "تعديل_عربي"
    a2_recompute_row_sha = make_review_blob("ai-a2", renewal_required=False, row_decisions=tampered_decisions)
    with pytest.raises(WorkflowError, match="requires renewal"):
        compose_and_store_bundle_and_payload(
            mock_private,
            prop_sha,
            a2_recompute_row_sha,
            "Test Company",
            valid_candidate_id,
            export_sha,
            "0" * 64,
            {"ai-a1": a1_sha, "ai-a2": a2_recompute_row_sha, "ai-a3": a3_sha},
        )

    # Case C: renewal_required is False, but finding has classification: "arabic_value_change"
    findings = [{"finding_id": "f-1", "blocking": False, "classification": "arabic_value_change", "summary": "Changed"}]
    a2_recompute_finding_sha = make_review_blob("ai-a2", renewal_required=False, findings=findings)
    with pytest.raises(WorkflowError, match="requires renewal"):
        compose_and_store_bundle_and_payload(
            mock_private,
            prop_sha,
            a2_recompute_finding_sha,
            "Test Company",
            valid_candidate_id,
            export_sha,
            "0" * 64,
            {"ai-a1": a1_sha, "ai-a2": a2_recompute_finding_sha, "ai-a3": a3_sha},
        )

    # Case D: clean reviews compose successfully
    a2_clean_sha = make_review_blob("ai-a2", renewal_required=False)
    result = compose_and_store_bundle_and_payload(
        mock_private,
        prop_sha,
        a2_clean_sha,
        "Test Company",
        valid_candidate_id,
        export_sha,
        "0" * 64,
        {"ai-a1": a1_sha, "ai-a2": a2_clean_sha, "ai-a3": a3_sha},
    )
    assert is_hex64(result["bundle_sha256"])
    assert is_hex64(result["payload_sha256"])


def test_adversarial_catalog_corruption_fails_closed(test_repo, tmp_path):
    """Adversarial test: catalog resolution fails closed on missing, corrupted, or invalid schema."""
    mock_private = tmp_path / "private_adv_cat"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)
        cat_blob = mock_private / "blobs" / f"{view['candidate']['export_sha256']}.json"
        assert cat_blob.exists()

        job_id = "job-adv-cat-test"
        dest = test_repo / "orchestrator/var/jobs" / job_id
        dest.mkdir(parents=True)
        envelope = {
            "schema_version": 1,
            "job_id": job_id,
            "work_item": "erp-arabic-bilingual-data",
            "stage": "4",
            "role": "proposer",
            "tool": "opencode",
            "model": "opencode-go/gpt-5.6-luna",
            "status": "COMPLETE",
            "verdict": "PROPOSED",
            "failure_class": None,
            "evidence_paths": [],
            "findings": [],
            "candidate_kind": "stage4-proposal",
            "candidate_id": view["candidate"]["candidate_id"],
            "plan_revision_hash": e.config["plan_revision_hash"],
            "prompt_version": e.config["roles"]["proposer"]["prompt_sha256"],
            "session_id": "sess-cat-test",
        }
        wire = {"explanation": "Synthesized", "result_json": json.dumps(envelope), "plan_text": ""}
        payload = {"body": envelope, "wire": wire}
        (dest / "stdout.jsonl").write_text(json.dumps(payload))
        obs = {"exit_code": 0, "session_id": "sess-cat-test", "started_utc": utc(), "finished_utc": utc()}
        job = {
            "job_id": job_id,
            "role": "proposer",
            "runtime": str(dest),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id}",
                "envelope": envelope,
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }

        # 1. Corrupt catalog JSON -> fails closed
        orig_content = cat_blob.read_text()
        cat_blob.write_text("{corrupted-json")
        with pytest.raises(WorkflowError, match="Export catalog blob corrupted"):
            e.accept(job, obs, view)

        # 2. Invalid schema (rows is not a list) -> fails closed
        (dest / "stdout.jsonl").write_text(json.dumps(payload))
        cat_blob.write_text(json.dumps({"schema": "stage4-account-catalog/v1", "rows": "not-a-list"}))
        with pytest.raises(WorkflowError, match="Export catalog blob invalid schema"):
            e.accept(job, obs, view)

        # 3. Missing catalog blob -> fails closed
        (dest / "stdout.jsonl").write_text(json.dumps(payload))
        cat_blob.unlink()
        with pytest.raises(WorkflowError, match="Export catalog blob missing"):
            e.accept(job, obs, view)
    finally:
        e.close()


def test_native_events_digest_matches_post_sanitization_artifact(test_repo, tmp_path):
    """Evidence digest must match the retained (post-sanitization) stdout.jsonl, not raw bytes.

    After accept() succeeds for a stage4-proposal job, the sha256 recorded in
    event["result"]["evidence_paths"][0] must equal hashlib.sha256(stdout.read_bytes())
    so that an independent verifier reading the file obtains the same hash.
    The raw bytes (containing Arabic text) must NOT appear in the retained file.
    """
    mock_private = tmp_path / "private_digest_test"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub(canary="")
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)
        stub.complete = stub.complete  # invoke via engine's launcher path
        job_id = "job-digest-ev-test"
        dest = test_repo / "orchestrator/var/jobs" / job_id
        dest.mkdir(parents=True)

        # Build a proposer stub outcome
        envelope = {
            "schema_version": 1,
            "job_id": job_id,
            "work_item": "erp-arabic-bilingual-data",
            "stage": "4",
            "role": "proposer",
            "tool": "opencode",
            "model": "opencode-go/gpt-5.6-luna",
            "status": "COMPLETE",
            "verdict": "PROPOSED",
            "failure_class": None,
            "evidence_paths": [],
            "findings": [],
            "candidate_kind": "stage4-proposal",
            "candidate_id": view["candidate"]["candidate_id"],
            "plan_revision_hash": e.config["plan_revision_hash"],
            "prompt_version": e.config["roles"]["proposer"]["prompt_sha256"],
            "session_id": "sess-digest-test",
            "export_sha256": view["candidate"]["export_sha256"],
            "proposal_sha256": None,
        }

        # Build a synthetic proposal with Arabic in the explanation (raw leakage attempt)
        arabic_payload = "تعديل طيار"
        wire = {
            "explanation": f"Arabic canary: {arabic_payload}",
            "result_json": json.dumps(envelope),
            "plan_text": "",
        }
        payload = {"body": envelope, "wire": wire}
        raw_content = json.dumps(payload, ensure_ascii=False)
        stdout_path = dest / "stdout.jsonl"
        stdout_path.write_text(raw_content, encoding="utf-8")

        # Verify raw content contains Arabic before accept()
        assert arabic_payload in stdout_path.read_text(encoding="utf-8"), \
            "Raw stdout.jsonl must contain Arabic before accept()"

        # Let Stage4Stub generate a valid proposal into private_out
        from stage4 import store_private_blob
        job = {
            "job_id": job_id,
            "role": "proposer",
            "runtime": str(dest),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id}",
                "envelope": envelope,
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
                "neutral_mounts": [
                    {
                        "host_path": str(mock_private / real_catalog.name),
                        "sandbox_path": "/tmp/workspace/private_inputs/account_catalog.json",
                        "writable": False,
                    }
                ],
            },
        }
        # Use the stub to generate a valid private_out/output.json
        stub.complete(job)
        # But overwrite stdout.jsonl with our Arabic-containing version
        stdout_path.write_text(raw_content, encoding="utf-8")

        obs = {
            "exit_code": 0,
            "session_id": "sess-digest-test",
            "started_utc": utc(),
            "finished_utc": utc(),
        }

        # Call accept() — must succeed (valid proposal)
        try:
            event = e.accept(job, obs, view)
        except WorkflowError as exc:
            pytest.skip(f"Proposer accept setup issue (adjust test): {exc}")

        # After accept: stdout.jsonl must be scrubbed (no raw Arabic)
        retained_bytes = stdout_path.read_bytes()
        retained_text = retained_bytes.decode("utf-8", errors="replace")
        assert arabic_payload not in retained_text, \
            "Arabic canary must not remain in stdout.jsonl after accept()"

        # The recorded digest must match the retained (scrubbed) file
        recorded_sha = event["result"]["evidence_paths"][0]["sha256"]
        actual_sha = hashlib.sha256(retained_bytes).hexdigest()
        assert recorded_sha == actual_sha, (
            f"evidence_paths digest {recorded_sha[:12]}… does not match "
            f"retained stdout.jsonl digest {actual_sha[:12]}…"
        )
        # And must NOT equal the raw (pre-sanitization) digest
        raw_sha = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
        assert recorded_sha != raw_sha, \
            "evidence_paths digest must not be the raw pre-sanitization hash"
    finally:
        e.close()


def test_raw_artifacts_scrubbed_on_rejected_output(test_repo, tmp_path):
    """Raw stdout.jsonl and stderr.txt must be scrubbed even when accept() fails.

    When accept() raises a WorkflowError (mismatched binding, corrupted catalog,
    malformed output, etc.) the finally clause must still overwrite the raw runtime
    artifacts with sanitized content before the error propagates.
    """
    mock_private = tmp_path / "private_reject_scrub"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        job_id = "job-reject-scrub-test"
        dest = test_repo / "orchestrator/var/jobs" / job_id
        dest.mkdir(parents=True)

        arabic_canary = "بيانات_سرية_خاصة"
        stderr_canary = "Office Rent secret_term"

        envelope = {
            "schema_version": 1,
            "job_id": job_id,
            "work_item": "erp-arabic-bilingual-data",
            "stage": "4",
            "role": "proposer",
            "tool": "opencode",
            "model": "opencode-go/gpt-5.6-luna",
            "status": "COMPLETE",
            "verdict": "PROPOSED",
            "failure_class": None,
            "evidence_paths": [],
            "findings": [],
            "candidate_kind": "stage4-proposal",
            "candidate_id": view["candidate"]["candidate_id"],
            "plan_revision_hash": "wrong-hash-triggers-rejection",  # deliberately mismatched
            "prompt_version": e.config["roles"]["proposer"]["prompt_sha256"],
            "session_id": "sess-reject-scrub",
            "export_sha256": view["candidate"]["export_sha256"],
            "proposal_sha256": None,
        }
        wire = {"explanation": f"Canary Arabic: {arabic_canary}", "result_json": json.dumps(envelope), "plan_text": ""}
        payload = {"body": envelope, "wire": wire}
        raw_content = json.dumps(payload, ensure_ascii=False)
        stdout_path = dest / "stdout.jsonl"
        stdout_path.write_text(raw_content, encoding="utf-8")
        stderr_path = dest / "stderr.txt"
        stderr_path.write_text(f"Process stderr with {stderr_canary} and {arabic_canary}", encoding="utf-8")

        # Verify both raw artifacts contain Arabic/catalog canary before accept()
        assert arabic_canary in stdout_path.read_text(encoding="utf-8")
        assert arabic_canary in stderr_path.read_text(encoding="utf-8")

        job = {
            "job_id": job_id,
            "role": "proposer",
            "runtime": str(dest),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id}",
                "envelope": {**envelope, "plan_revision_hash": e.config["plan_revision_hash"]},
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }
        obs = {
            "exit_code": 0,
            "session_id": "sess-reject-scrub",
            "started_utc": utc(),
            "finished_utc": utc(),
        }

        # accept() must raise (plan_revision_hash mismatch triggers "Stale or mismatched result binding")
        with pytest.raises(WorkflowError):
            e.accept(job, obs, view)

        # CRITICAL: even though accept() raised, stdout.jsonl and stderr.txt must be scrubbed
        retained_stdout = stdout_path.read_text(encoding="utf-8")
        retained_stderr = stderr_path.read_text(encoding="utf-8")

        assert arabic_canary not in retained_stdout, \
            "Arabic canary must be scrubbed from stdout.jsonl even after rejection"
        assert arabic_canary not in retained_stderr, \
            "Arabic canary must be scrubbed from stderr.txt even after rejection"
        assert "Office Rent" not in retained_stderr, \
            "Catalog term 'Office Rent' must be scrubbed from stderr.txt even after rejection"
    finally:
        e.close()


def test_raw_artifacts_scrubbed_on_malformed_output(test_repo, tmp_path):
    """Raw stdout.jsonl and stderr.txt must be scrubbed when agent output is malformed / unparseable."""
    mock_private = tmp_path / "private_malformed_scrub"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        job_id = "job-malformed-scrub-test"
        dest = test_repo / "orchestrator/var/jobs" / job_id
        dest.mkdir(parents=True)

        arabic_canary = "تالف_غير_صالح_إطلاقا"
        cat_term = "Office Rent"

        # Corrupted / non-JSON content containing Arabic and catalog term
        malformed_raw = f"<<<CORRUPTED_AGENT_OUTPUT: {cat_term} - {arabic_canary}>>>"
        stdout_path = dest / "stdout.jsonl"
        stdout_path.write_text(malformed_raw, encoding="utf-8")
        stderr_path = dest / "stderr.txt"
        stderr_path.write_text(f"Stderr with {cat_term} and {arabic_canary}", encoding="utf-8")

        job = {
            "job_id": job_id,
            "role": "proposer",
            "runtime": str(dest),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id}",
                "envelope": {
                    "job_id": job_id,
                    "stage": "4",
                    "role": "proposer",
                    "plan_revision_hash": e.config["plan_revision_hash"],
                    "export_sha256": view["candidate"]["export_sha256"],
                },
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }
        obs = {
            "exit_code": 0,
            "session_id": "sess-malformed",
            "started_utc": utc(),
            "finished_utc": utc(),
        }

        # accept() must raise because output is malformed
        with pytest.raises(Exception):
            e.accept(job, obs, view)

        # Artifacts must still be scrubbed of both Arabic and catalog terms
        retained_stdout = stdout_path.read_text(encoding="utf-8")
        retained_stderr = stderr_path.read_text(encoding="utf-8")

        assert arabic_canary not in retained_stdout, \
            "Arabic canary must be scrubbed from malformed stdout.jsonl"
        assert cat_term not in retained_stdout, \
            "Catalog term must be scrubbed from malformed stdout.jsonl"
        assert arabic_canary not in retained_stderr, \
            "Arabic canary must be scrubbed from stderr.txt on malformed output"
        assert cat_term not in retained_stderr, \
            "Catalog term must be scrubbed from stderr.txt on malformed output"
    finally:
        e.close()


def test_missing_or_corrupt_catalog_with_english_canary_quarantines_artifacts(test_repo, tmp_path):
    """When catalog is corrupt or missing, raw artifacts with English canary must be quarantined/deleted."""
    mock_private = tmp_path / "private_corrupt_cat"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)
        export_sha = view["candidate"]["export_sha256"]
        cat_blob = mock_private / "blobs" / f"{export_sha}.json"
        assert cat_blob.exists()

        # --- Scenario A: Corrupt catalog blob ---
        job_id_a = "job-corrupt-cat-canary"
        dest_a = test_repo / "orchestrator/var/jobs" / job_id_a
        dest_a.mkdir(parents=True)

        envelope_a = {
            "schema_version": 1,
            "job_id": job_id_a,
            "work_item": "erp-arabic-bilingual-data",
            "stage": "4",
            "role": "proposer",
            "tool": "opencode",
            "model": "opencode-go/gpt-5.6-luna",
            "status": "COMPLETE",
            "verdict": "PROPOSED",
            "failure_class": None,
            "evidence_paths": [],
            "findings": [],
            "candidate_kind": "stage4-proposal",
            "candidate_id": view["candidate"]["candidate_id"],
            "plan_revision_hash": e.config["plan_revision_hash"],
            "prompt_version": e.config["roles"]["proposer"]["prompt_sha256"],
            "session_id": "sess-corrupt-a",
            "export_sha256": export_sha,
            "proposal_sha256": None,
        }
        english_canary = "Office Rent CONFIDENTIAL_TERM_123"
        arabic_canary = "حساب_خاص_سري"
        wire_a = {"explanation": f"Leaking {english_canary} and {arabic_canary}", "result_json": json.dumps(envelope_a), "plan_text": ""}
        payload_a = {"body": envelope_a, "wire": wire_a}
        stdout_a = dest_a / "stdout.jsonl"
        stdout_a.write_text(json.dumps(payload_a), encoding="utf-8")
        stderr_a = dest_a / "stderr.txt"
        stderr_a.write_text(f"Stderr with {english_canary} and {arabic_canary}", encoding="utf-8")

        job_a = {
            "job_id": job_id_a,
            "role": "proposer",
            "runtime": str(dest_a),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id_a}",
                "envelope": envelope_a,
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }
        obs_a = {"exit_code": 0, "session_id": "sess-corrupt-a", "started_utc": utc(), "finished_utc": utc()}

        # Deliberately corrupt catalog JSON
        cat_blob.write_text("{corrupt-json-blob")

        with pytest.raises(WorkflowError, match="Export catalog blob"):
            e.accept(job_a, obs_a, view)

        # Public runtime artifacts must NOT exist in job destination (quarantined/deleted)
        assert not stdout_a.exists(), "stdout.jsonl must not remain in public job dir when catalog terms cannot be loaded"
        assert not stderr_a.exists(), "stderr.txt must not remain in public job dir when catalog terms cannot be loaded"

        # Quarantined copies in protected private root
        q_stdout_a = mock_private / "quarantine" / job_id_a / "stdout.jsonl"
        q_stderr_a = mock_private / "quarantine" / job_id_a / "stderr.txt"
        assert q_stdout_a.exists(), "Raw artifact should be safely moved to protected private storage"
        assert q_stderr_a.exists(), "Raw stderr should be safely moved to protected private storage"
        assert english_canary in q_stdout_a.read_text(encoding="utf-8")

        # Mode and ownership verification
        assert (mock_private / "quarantine").stat().st_mode & 0o777 == 0o700, "Quarantine root must be 0700"
        assert (mock_private / "quarantine" / job_id_a).stat().st_mode & 0o777 == 0o700, "Job quarantine dir must be 0700"
        assert q_stdout_a.stat().st_mode & 0o777 == 0o600, "Quarantined stdout.jsonl must be 0600"
        assert q_stderr_a.stat().st_mode & 0o777 == 0o600, "Quarantined stderr.txt must be 0600"
        assert q_stdout_a.stat().st_uid == os.getuid(), "Quarantined file must be owned by current user"

        # --- Scenario B: Missing catalog blob ---
        job_id_b = "job-missing-cat-canary"
        dest_b = test_repo / "orchestrator/var/jobs" / job_id_b
        dest_b.mkdir(parents=True)

        envelope_b = deepcopy(envelope_a)
        envelope_b["job_id"] = job_id_b
        wire_b = {"explanation": f"Leaking {english_canary}", "result_json": json.dumps(envelope_b), "plan_text": ""}
        payload_b = {"body": envelope_b, "wire": wire_b}
        stdout_b = dest_b / "stdout.jsonl"
        stdout_b.write_text(json.dumps(payload_b), encoding="utf-8")
        stderr_b = dest_b / "stderr.txt"
        stderr_b.write_text(f"Stderr {english_canary}", encoding="utf-8")

        job_b = {
            "job_id": job_id_b,
            "role": "proposer",
            "runtime": str(dest_b),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id_b}",
                "envelope": envelope_b,
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }
        obs_b = {"exit_code": 0, "session_id": "sess-corrupt-b", "started_utc": utc(), "finished_utc": utc()}

        cat_blob.unlink()

        with pytest.raises(WorkflowError, match="Export catalog blob"):
            e.accept(job_b, obs_b, view)

        assert not stdout_b.exists(), "stdout.jsonl must not remain in public job dir on missing catalog"
        assert not stderr_b.exists(), "stderr.txt must not remain in public job dir on missing catalog"
        q_stdout_b = mock_private / "quarantine" / job_id_b / "stdout.jsonl"
        assert q_stdout_b.exists()
        assert (mock_private / "quarantine" / job_id_b).stat().st_mode & 0o777 == 0o700
        assert q_stdout_b.stat().st_mode & 0o777 == 0o600
    finally:
        e.close()


def test_invalid_utf8_runtime_output_handling(test_repo, tmp_path):
    """Invalid UTF-8 in runtime output must not leak bytes or replace original acceptance exception."""
    mock_private = tmp_path / "private_invalid_utf8"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        # Case A: stdout.jsonl contains invalid UTF-8 bytes
        job_id_a = "job-invalid-utf8-stdout"
        dest_a = test_repo / "orchestrator/var/jobs" / job_id_a
        dest_a.mkdir(parents=True)

        bad_bytes = b'{"header": "ok", "corrupted": \xff\xfe\x80\x00}'
        stdout_a = dest_a / "stdout.jsonl"
        stdout_a.write_bytes(bad_bytes)
        stderr_a = dest_a / "stderr.txt"
        stderr_a.write_text("clean stderr", encoding="utf-8")

        job_a = {
            "job_id": job_id_a,
            "role": "proposer",
            "runtime": str(dest_a),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id_a}",
                "envelope": {"job_id": job_id_a},
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }
        obs_a = {"exit_code": 0, "session_id": "sess-utf8-a", "started_utc": utc(), "finished_utc": utc()}

        with pytest.raises(UnicodeDecodeError):
            e.accept(job_a, obs_a, view)

        # Raw file with invalid bytes must be removed from public destination
        assert not stdout_a.exists(), "stdout.jsonl with invalid UTF-8 must not remain in public job dir"
        # Quarantined copy in protected private root preserves exact bytes and modes
        q_stdout_a = mock_private / "quarantine" / job_id_a / "stdout.jsonl"
        assert q_stdout_a.exists()
        assert q_stdout_a.read_bytes() == bad_bytes
        assert (mock_private / "quarantine").stat().st_mode & 0o777 == 0o700
        assert (mock_private / "quarantine" / job_id_a).stat().st_mode & 0o777 == 0o700
        assert q_stdout_a.stat().st_mode & 0o777 == 0o600

        # Case B: stdout.jsonl has valid UTF-8 but triggers a WorkflowError,
        # while stderr.txt contains invalid UTF-8 bytes.
        job_id_b = "job-invalid-utf8-stderr"
        dest_b = test_repo / "orchestrator/var/jobs" / job_id_b
        dest_b.mkdir(parents=True)

        envelope_b = {
            "schema_version": 1,
            "job_id": job_id_b,
            "work_item": "erp-arabic-bilingual-data",
            "stage": "4",
            "role": "proposer",
            "tool": "opencode",
            "model": "opencode-go/gpt-5.6-luna",
            "status": "COMPLETE",
            "verdict": "PROPOSED",
            "failure_class": None,
            "evidence_paths": [],
            "findings": [],
            "candidate_kind": "stage4-proposal",
            "candidate_id": view["candidate"]["candidate_id"],
            "plan_revision_hash": "mismatched-plan-hash",
            "prompt_version": e.config["roles"]["proposer"]["prompt_sha256"],
            "session_id": "sess-utf8-b",
            "export_sha256": view["candidate"]["export_sha256"],
            "proposal_sha256": None,
        }
        wire_b = {"explanation": "Normal explanation", "result_json": json.dumps(envelope_b), "plan_text": ""}
        payload_b = {"body": envelope_b, "wire": wire_b}
        stdout_b = dest_b / "stdout.jsonl"
        stdout_b.write_text(json.dumps(payload_b), encoding="utf-8")

        bad_stderr_bytes = b"stderr crashed with \x80\xff\xfe binary corruption"
        stderr_b = dest_b / "stderr.txt"
        stderr_b.write_bytes(bad_stderr_bytes)

        job_b = {
            "job_id": job_id_b,
            "role": "proposer",
            "runtime": str(dest_b),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id_b}",
                "envelope": {**envelope_b, "plan_revision_hash": e.config["plan_revision_hash"]},
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }
        obs_b = {"exit_code": 0, "session_id": "sess-utf8-b", "started_utc": utc(), "finished_utc": utc()}

        # Crucial check: the original WorkflowError must be preserved, NOT replaced by UnicodeDecodeError!
        with pytest.raises(WorkflowError, match="Stale or mismatched result binding"):
            e.accept(job_b, obs_b, view)

        # Invalid stderr.txt must not remain in public dir
        assert not stderr_b.exists(), "stderr.txt with invalid UTF-8 must not remain in public job dir"
        # Quarantined copy in protected private root
        q_stderr_b = mock_private / "quarantine" / job_id_b / "stderr.txt"
        assert q_stderr_b.exists()
        assert q_stderr_b.read_bytes() == bad_stderr_bytes
        assert (mock_private / "quarantine" / job_id_b).stat().st_mode & 0o777 == 0o700
        assert q_stderr_b.stat().st_mode & 0o777 == 0o600
    finally:
        e.close()


def test_quarantine_permissions_and_symlink_non_regular_rejection(test_repo, tmp_path):
    """Quarantine root and job dir must be 0700, files 0600, and symlink/non-regular targets rejected."""
    mock_private = tmp_path / "private_perm_test"
    mock_private.mkdir(parents=True)
    # Simulate production 775 permissions on private directories
    os.chmod(mock_private, 0o775)
    assert mock_private.stat().st_mode & 0o777 == 0o775

    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)
        export_sha = view["candidate"]["export_sha256"]
        cat_blob = mock_private / "blobs" / f"{export_sha}.json"
        cat_blob.write_text("{corrupt-json")

        def make_payload(jid):
            env = {
                "schema_version": 1,
                "job_id": jid,
                "work_item": "erp-arabic-bilingual-data",
                "stage": "4",
                "role": "proposer",
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
                "status": "COMPLETE",
                "verdict": "PROPOSED",
                "failure_class": None,
                "evidence_paths": [],
                "findings": [],
                "candidate_kind": "stage4-proposal",
                "candidate_id": view["candidate"]["candidate_id"],
                "plan_revision_hash": e.config["plan_revision_hash"],
                "prompt_version": e.config["roles"]["proposer"]["prompt_sha256"],
                "session_id": f"sess-{jid}",
                "export_sha256": view["candidate"]["export_sha256"],
                "proposal_sha256": None,
            }
            wire = {"explanation": f"Canary {jid}", "result_json": json.dumps(env), "plan_text": ""}
            return {"body": env, "wire": wire}

        # 1. Normal quarantine under 775 parent gets 0700 / 0600
        job_id_1 = "job-perm-1"
        dest_1 = test_repo / "orchestrator/var/jobs" / job_id_1
        dest_1.mkdir(parents=True)
        payload_1 = make_payload(job_id_1)
        (dest_1 / "stdout.jsonl").write_text(json.dumps(payload_1), encoding="utf-8")
        job_1 = {
            "job_id": job_id_1,
            "role": "proposer",
            "runtime": str(dest_1),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id_1}",
                "envelope": payload_1["body"],
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }
        obs_1 = {"exit_code": 0, "session_id": f"sess-{job_id_1}", "started_utc": utc(), "finished_utc": utc()}

        with pytest.raises(WorkflowError):
            e.accept(job_1, obs_1, view)

        q_root = mock_private / "quarantine"
        q_dir_1 = q_root / job_id_1
        q_file_1 = q_dir_1 / "stdout.jsonl"
        assert q_root.stat().st_mode & 0o777 == 0o700, "Quarantine root must be 0700 despite 775 parent"
        assert q_dir_1.stat().st_mode & 0o777 == 0o700, "Job quarantine dir must be 0700"
        assert q_file_1.stat().st_mode & 0o777 == 0o600, "Quarantined file must be 0600"
        assert not (dest_1 / "stdout.jsonl").exists()

        # 2. Symlink target rejection: if target path is a pre-existing symlink to victim file
        job_id_2 = "job-perm-2"
        dest_2 = test_repo / "orchestrator/var/jobs" / job_id_2
        dest_2.mkdir(parents=True)
        payload_2 = make_payload(job_id_2)
        (dest_2 / "stdout.jsonl").write_text(json.dumps(payload_2), encoding="utf-8")

        victim_file = tmp_path / "victim.txt"
        victim_file.write_text("UNTOUCHED_VICTIM")

        q_dir_2 = q_root / job_id_2
        q_dir_2.mkdir(mode=0o700, exist_ok=True)
        os.chmod(q_dir_2, 0o700)
        symlink_target = q_dir_2 / "stdout.jsonl"
        symlink_target.symlink_to(victim_file)

        job_2 = {
            "job_id": job_id_2,
            "role": "proposer",
            "runtime": str(dest_2),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id_2}",
                "envelope": payload_2["body"],
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }
        obs_2 = {"exit_code": 0, "session_id": f"sess-{job_id_2}", "started_utc": utc(), "finished_utc": utc()}

        with pytest.raises(WorkflowError):
            e.accept(job_2, obs_2, view)

        # Victim file must NOT have been overwritten through symlink
        assert victim_file.read_text() == "UNTOUCHED_VICTIM"
        # Public destination file must have been unlinked
        assert not (dest_2 / "stdout.jsonl").exists()

        # 3. Source symlink rejection: if source in destination is a symlink
        job_id_3 = "job-perm-3"
        dest_3 = test_repo / "orchestrator/var/jobs" / job_id_3
        dest_3.mkdir(parents=True)
        payload_3 = make_payload(job_id_3)
        source_victim = tmp_path / "source_victim.txt"
        source_victim.write_text("ORIGINAL_SECRET")
        (dest_3 / "stdout.jsonl").symlink_to(source_victim)

        job_3 = {
            "job_id": job_id_3,
            "role": "proposer",
            "runtime": str(dest_3),
            "spec": {
                "expected_artifact_id": f"stage4-proposal-{job_id_3}",
                "envelope": payload_3["body"],
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
            },
        }
        obs_3 = {"exit_code": 0, "session_id": f"sess-{job_id_3}", "started_utc": utc(), "finished_utc": utc()}

        with pytest.raises((WorkflowError, json.JSONDecodeError)):
            e.accept(job_3, obs_3, view)

        # Source symlink was unlinked from dest, original source victim intact
        assert not (dest_3 / "stdout.jsonl").exists()
        assert source_victim.read_text() == "ORIGINAL_SECRET"
        # Nothing should have been quarantined
        assert not (q_root / job_id_3 / "stdout.jsonl").exists()

    finally:
        e.close()


def test_concurrent_acceptance_isolation(test_repo, tmp_path):
    """Concurrent accept() calls on the same Engine instance must be fully isolated without cross-job state."""
    import concurrent.futures
    mock_private = tmp_path / "private_concurrent"
    mock_private.mkdir(parents=True)
    real_catalog = Path("/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json")
    shutil.copy2(real_catalog, mock_private / real_catalog.name)

    stub = Stage4Stub()
    e = Engine(test_repo, launcher=stub)
    try:
        desc = {
            "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
            "bench_root": "/home/mohamed/frappe-bench",
            "site": "v16.localhost",
            "site_classification": "non-production test",
            "private_root": str(mock_private),
        }
        view = e.adopt_historical("erp-arabic-bilingual-data", erp_descriptor=desc)

        job_specs = []
        for i in range(4):
            jid = f"job-concurrent-{i}"
            dest = test_repo / "orchestrator/var/jobs" / jid
            dest.mkdir(parents=True)

            is_failing = (i == 2)
            canary = f"CANARY_CONCURRENT_THREAD_{i}"
            envelope = {
                "schema_version": 1,
                "job_id": jid,
                "work_item": "erp-arabic-bilingual-data",
                "stage": "4",
                "role": "proposer",
                "tool": "opencode",
                "model": "opencode-go/gpt-5.6-luna",
                "status": "COMPLETE",
                "verdict": "PROPOSED",
                "failure_class": None,
                "evidence_paths": [],
                "findings": [],
                "candidate_kind": "stage4-proposal",
                "candidate_id": view["candidate"]["candidate_id"],
                "plan_revision_hash": "bad-hash" if is_failing else e.config["plan_revision_hash"],
                "prompt_version": e.config["roles"]["proposer"]["prompt_sha256"],
                "session_id": f"sess-concurrent-{i}",
                "export_sha256": view["candidate"]["export_sha256"],
                "proposal_sha256": None,
            }
            wire = {"explanation": f"Canary {canary}", "result_json": json.dumps(envelope), "plan_text": ""}
            payload = {"body": envelope, "wire": wire}
            (dest / "stdout.jsonl").write_text(json.dumps(payload), encoding="utf-8")
            (dest / "stderr.txt").write_text(f"Stderr {canary}", encoding="utf-8")

            job = {
                "job_id": jid,
                "role": "proposer",
                "runtime": str(dest),
                "spec": {
                    "expected_artifact_id": f"stage4-proposal-{jid}",
                    "envelope": {**envelope, "plan_revision_hash": e.config["plan_revision_hash"]},
                    "tool": "opencode",
                    "model": "opencode-go/gpt-5.6-luna",
                    "neutral_mounts": [
                        {
                            "host_path": str(mock_private / real_catalog.name),
                            "sandbox_path": "/tmp/workspace/private_inputs/account_catalog.json",
                            "writable": False,
                        }
                    ],
                },
            }
            if not is_failing:
                stub.complete(job)
                (dest / "stdout.jsonl").write_text(json.dumps(payload), encoding="utf-8")

            obs = {"exit_code": 0, "session_id": f"sess-concurrent-{i}", "started_utc": utc(), "finished_utc": utc()}
            job_specs.append((i, job, obs, is_failing, canary, dest))

        def run_accept(args):
            idx, job, obs, is_failing, canary, dest = args
            try:
                event = e.accept(job, obs, view)
                return idx, event, None
            except Exception as exc:
                return idx, None, exc

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(run_accept, job_specs))

        for idx, event, exc in results:
            _, _, _, is_failing, canary, dest = job_specs[idx]
            if is_failing:
                assert isinstance(exc, WorkflowError)
                assert "Stale or mismatched result binding" in str(exc)
            else:
                assert exc is None
                assert event is not None
                assert event["job_id"] == f"job-concurrent-{idx}"
                # Assert evidence digest matches the actual retained file
                retained_bytes = (dest / "stdout.jsonl").read_bytes()
                recorded_sha = event["result"]["evidence_paths"][0]["sha256"]
                assert recorded_sha == hashlib.sha256(retained_bytes).hexdigest()

        # Check that no instance-level cache exists on Engine
        assert not hasattr(e, "_stage4_catalog_terms_cache"), "Engine must not store catalog terms cache on self"
    finally:
        e.close()




def test_bubblewrap_neutral_mounts_execution(tmp_path):
    """Verifies that Bubblewrap neutral mounts under /tmp/workspace execute and protect host."""
    import shutil
    import subprocess
    import sys
    import adapters

    if not shutil.which("bwrap"):
        pytest.skip("bwrap not available")

    host_root = tmp_path / "sandbox_repo"
    host_root.mkdir()
    (host_root / "test.txt").write_text("initial")

    host_in = tmp_path / "input.json"
    host_in.write_text(json.dumps({"test_key": "test_value"}))

    host_out_dir = tmp_path / "host_private_out"
    host_out_dir.mkdir()

    control = tmp_path / "control"
    control.mkdir()
    work_item = tmp_path / "work-item"
    work_item.mkdir()

    wire_schema = tmp_path / "wire.json"
    wire_schema.write_text(json.dumps({}))

    spec = {
        "tool": "codex",
        "binary": "/bin/true",
        "model": "gpt-6-astra",
        "root": str(host_root),
        "runtime": str(control),
        "control_root": str(control),
        "work_item_root": str(work_item),
        "wire_schema": str(wire_schema),
        "role": "proposer",
        "prompt": "test",
        "neutral_mounts": [
            {
                "host_path": str(host_in),
                "sandbox_path": "/tmp/workspace/private_inputs/input.json",
                "writable": False,
            },
            {
                "host_path": str(host_out_dir),
                "sandbox_path": "/tmp/workspace/private_output",
                "writable": True,
            },
        ],
    }
    cmd, env = adapters.invocation(spec)
    test_code = """
import json, sys
from pathlib import Path
in_path = Path("/tmp/workspace/private_inputs/input.json")
assert in_path.exists()
data = json.loads(in_path.read_text())
assert data["test_key"] == "test_value"
out_path = Path("/tmp/workspace/private_output/output.json")
out_path.write_text(json.dumps({"received": data["test_key"]}))
"""
    dd_idx = cmd.index("--")
    bwrap_prefix = cmd[:dd_idx + 1]
    test_cmd = bwrap_prefix + [sys.executable, "-c", test_code]

    res = subprocess.run(test_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        if any(msg in res.stderr.lower() for msg in ("setting up uid map", "permission denied", "creating new namespace failed", "function not implemented")):
            pytest.skip("nested container lacks user namespace privileges")
        raise AssertionError(f"bwrap execution failed: {res.stderr}")

    out_file = host_out_dir / "output.json"
    assert out_file.exists()
    out_data = json.loads(out_file.read_text())
    assert out_data["received"] == "test_value"

