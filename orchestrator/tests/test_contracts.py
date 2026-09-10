import copy
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError
from schema_source import CLASSES, FAILURES, documents
from validate import SCHEMA_ROOT, validate_document, validate_structure

H = "a" * 64
REF = {"artifact_id": "evidence-1", "sha256": H, "visibility": "public"}


def finding(classification="implementation_defect", identifier=None):
    return dict(
        schema_version=1,
        finding_id=identifier,
        classification=classification,
        blocking=classification != "optional_improvement",
        summary="Scope filter requirement fails",
        affected_requirements=["SCP-R1"],
        evidence_refs=[REF],
        snapshot=None,
    )


def result():
    return dict(
        schema_version=1,
        job_id="job-1",
        work_item="scope-context-portability",
        stage="1",
        role="verifier",
        tool="codex",
        model="observed-model",
        session_id="observed-session",
        dispatch_mode="native",
        candidate_kind="code",
        candidate_id=H,
        plan_revision_hash=H,
        prompt_version=H,
        status="COMPLETE",
        verdict="PASS",
        failure_class=None,
        findings=[],
        evidence_paths=[REF],
        started_utc="2026-09-11T00:00:00Z",
        finished_utc="2026-09-11T00:01:00Z",
    )


def token(scope):
    common = dict(
        schema_version=1,
        token_id="token-1",
        work_item="scope-context-portability",
        gate_id="gate-1",
        issuer="owner",
        issued_utc="2026-09-11T00:00:00Z",
        status="ISSUED",
        scope=scope,
    )
    if scope == "PLAN":
        common.update(
            plan_revision_hash=H, scope_hash=H, repository_id="repo-1", branch="feature/pilot", stages=["1"]
        )
    elif scope == "COMMIT":
        common.update(
            candidate_id=H,
            manifest_hash=H,
            repository_id="repo-1",
            branch="feature/pilot",
            expected_parent_sha="a" * 40,
            expected_tree_oid="b" * 40,
            job_id="commit-1",
        )
    else:
        common.update(
            erp_descriptor_hash=H,
            candidate_id=H,
            export_sha256=H,
            bundle_sha256=H,
            payload_sha256=H,
            operation="set_account_name_ar",
            job_id="import-1",
        )
        if scope == "IMPORT":
            common["dry_run_evidence_digest"] = H
    return common


def state():
    return dict(
        schema_version=1,
        authority="sqlite-checkpoint-export-only",
        work_item="scope-context-portability",
        stage="1",
        status="DRAFT",
        revision=0,
        plan_revision_hash=None,
        candidate_id=None,
        active_jobs=[],
        completed_dependencies=[],
        approval_refs=[],
        escalation=dict(unsuccessful_cycles=0, unchanged_rounds=0, last_snapshot_digest=None),
        pause_reason=None,
        resume_to=None,
        stages={},
        exported_utc="2026-09-11T00:00:00Z",
    )


def repair():
    return dict(
        schema_version=1,
        work_item="scope-context-portability",
        stage="1",
        job_id="repair-1",
        candidate_id=H,
        plan_revision_hash=H,
        scope_hash=H,
        review_round=2,
        contract_refs=[REF],
        unresolved_findings=[finding(identifier="SCP-001")],
        backlog=[finding("optional_improvement")],
    )


@pytest.mark.parametrize("name,schema", documents().items())
def test_published_schemas_are_valid_and_match_source(name, schema):
    Draft202012Validator.check_schema(schema)
    assert json.loads((SCHEMA_ROOT / (name + ".json")).read_text()) == schema


@pytest.mark.parametrize(
    "name,value", [("result-envelope", result()), ("state-export", state()), ("repair-packet", repair())]
)
def test_positive_samples(name, value):
    validate_document(name, value)


@pytest.mark.parametrize("classification", CLASSES)
def test_all_finding_routes_have_valid_contracts(classification):
    validate_document("finding", finding(classification))


@pytest.mark.parametrize("scope", ["PLAN", "COMMIT", "DRY_RUN", "IMPORT"])
def test_scope_specific_grants(scope):
    validate_document("approval-token", token(scope))


@pytest.mark.parametrize("failure", FAILURES)
def test_prelaunch_failure_does_not_invent_session_or_model(failure):
    value = result()
    value.update(
        status="FAILED",
        verdict="FAILED",
        failure_class=failure,
        session_id=None,
        model=None,
        evidence_paths=[],
    )
    validate_document("result-envelope", value)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda v: v.update(schema_version=2),
        lambda v: v.update(session_id=None),
        lambda v: v.update(candidate_id="wrong"),
        lambda v: v.update(findings=[finding()]),
        lambda v: v.update(evidence_paths=[]),
        lambda v: v.update(finished_utc="2026-09-10T00:00:00Z"),
        lambda v: v.update(verdict="BLOCKED"),
        lambda v: v.update(verdict="PROPOSED"),
        lambda v: v.update(started_utc="yesterdayZ"),
        lambda v: v.update(approval_token="forged"),
        lambda v: v.update(bundle_sha256=H),
    ],
)
def test_invalid_results_cannot_be_accepted(mutation):
    value = result()
    mutation(value)
    with pytest.raises((ValidationError, ValueError)):
        validate_document("result-envelope", value)


def test_optional_suggestion_cannot_block():
    value = finding("optional_improvement")
    value["blocking"] = True
    with pytest.raises(ValidationError):
        validate_document("finding", value)


@pytest.mark.parametrize("mutation", [lambda v: v.update(scope="IMPORT"), lambda v: v.update(candidate_id=H)])
def test_plan_grant_cannot_masquerade_as_operation_grant(mutation):
    value = token("PLAN")
    mutation(value)
    with pytest.raises(ValidationError):
        validate_document("approval-token", value)


def test_import_requires_accepted_dry_run_binding():
    value = token("IMPORT")
    del value["dry_run_evidence_digest"]
    with pytest.raises(ValidationError):
        validate_document("approval-token", value)


def test_stage4_verifier_hashes_are_separate_required_fields():
    value = result()
    value.update(
        candidate_kind="stage4-proposal",
        export_sha256=H,
        proposal_sha256="b" * 64,
        private_artifact_refs=[{**REF, "visibility": "private"}],
    )
    with pytest.raises(ValueError):
        validate_document("result-envelope", value)
    value.update(bundle_sha256="c" * 64, payload_sha256="d" * 64)
    validate_document("result-envelope", value)


def test_duplicate_unresolved_findings_rejected():
    value = repair()
    value["unresolved_findings"] *= 2
    with pytest.raises(ValueError):
        validate_document("repair-packet", value)


def test_stage4_substatus_is_not_a_work_item_status():
    value = state()
    value["status"] = "PROPOSAL_PENDING"
    with pytest.raises(ValidationError):
        validate_document("state-export", value)


def test_pause_requires_reason_and_resume_target():
    value = state()
    value["status"] = "PAUSED"
    with pytest.raises(ValidationError):
        validate_document("state-export", value)
    value.update(pause_reason="ESCALATED", resume_to="BUILD_IN_PROGRESS")
    validate_document("state-export", value)


def test_structure_mode_never_creates_authoritative_state(tmp_path):
    (tmp_path / "inbox").mkdir()
    (tmp_path / "outbox").mkdir()
    assert validate_structure(tmp_path, contracts_only=True).startswith("CONTRACTS_ONLY")
    with pytest.raises(FileNotFoundError):
        validate_structure(tmp_path)
    assert not (tmp_path / "STATE.json").exists()
    (tmp_path / "STATE.json").write_text(json.dumps(state()))
    assert validate_structure(tmp_path).startswith("VALID_EXPORT_STRUCTURE")


def test_structure_rejects_symlinked_state(tmp_path):
    for directory in ("inbox", "outbox"):
        (tmp_path / directory).mkdir()
    target = tmp_path / "target.json"
    target.write_text(json.dumps(state()))
    (tmp_path / "STATE.json").symlink_to(target)
    with pytest.raises(ValueError):
        validate_structure(tmp_path)
