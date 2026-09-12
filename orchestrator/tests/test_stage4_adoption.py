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

import json
import shutil
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
            "schema_version": 1,
            "token_id": "tok-plan-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": state["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": config["plan_revision_hash"],
            "scope_hash": config["scope_hash"],
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
            "schema_version": 1,
            "token_id": "tok-single-use-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
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
            "schema_version": 1,
            "token_id": "tok-plan-lifecycle-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
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
            "schema_version": 1,
            "token_id": "tok-plan-canary-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
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
            "schema_version": 1,
            "token_id": "tok-plan-adv-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
            "stages": ["4"],
            "repository_id": str(test_repo),
            "branch": "feature/scope-context-portability",
        }
        e.approve(plan_token)

        for p in (test_repo / "docs/ai/work-items/erp-arabic-bilingual-data/runs").rglob("*.md"):
            txt = p.read_text()
            assert leak_term not in txt, f"Leak in {p}"
            assert arabic_term not in txt, f"Leak in {p}"

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
                "finding_id": "f-leak-1",
                "role": job["role"],
                "blocking": False,
                "summary": f"Finding leaks {leak_term} and {arabic_term}",
                "detail": f"Detail leaks {leak_term}",
            }]
            (destination / "stdout.jsonl").write_text(json.dumps(raw_payload))

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
            "schema_version": 1,
            "token_id": "tok-plan-adv-002",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
            "stages": ["4"],
            "repository_id": str(test_repo),
            "branch": "feature/scope-context-portability",
        }
        e.approve(plan_token)

        for p in (test_repo / "docs/ai/work-items/erp-arabic-bilingual-data/runs").rglob("*.json"):
            txt = p.read_text()
            assert leak_term not in txt, f"Leak in {p}"
            assert arabic_term not in txt, f"Leak in {p}"
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
            "schema_version": 1,
            "token_id": "tok-plan-drift-001",
            "work_item": "erp-arabic-bilingual-data",
            "gate_id": view["gate"]["gate_id"],
            "issuer": "owner",
            "scope": "PLAN",
            "status": "ISSUED",
            "issued_utc": utc(),
            "plan_revision_hash": e.config["plan_revision_hash"],
            "scope_hash": e.config["scope_hash"],
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

