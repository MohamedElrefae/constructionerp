import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from candidates import git
from core import WorkflowError, bytes_hash, utc, write_json
from engine import Engine


class Stub:
    """Explicitly synthetic; never counted as native acceptance."""

    def __init__(self, outcomes=None, delayed=False):
        self.starts = []
        self.outcomes = outcomes or {}
        self.delayed = delayed

    def __call__(self, job):
        self.starts.append(job["job_id"])
        if not self.delayed:
            self.complete(job)

    def complete(self, job):
        body = deepcopy(job["spec"]["envelope"])
        body.update(self.outcomes.get(job["role"], {}))
        body["session_id"] = "synthetic-" + job["job_id"]
        payload = {
            "body": body,
            "wire": {
                "plan_text": "Synthetic plan with explicit requirements",
                "explanation": "SYNTHETIC fixture result",
            },
        }
        destination = Path(job["runtime"])
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


def plan_token(engine):
    v = engine.view()
    return dict(
        schema_version=1,
        token_id="owner-plan",
        work_item=v["work_item"],
        gate_id=v["gate"]["gate_id"],
        issuer="owner",
        issued_utc=utc(),
        status="ISSUED",
        scope="PLAN",
        plan_revision_hash=v["plan_revision_hash"],
        scope_hash=v["scope_hash"],
        repository_id=str(engine.root),
        branch=engine.config["branch"],
        stages=["1"],
    )


def test_happy_path_owner_gate_exports_not_authority(configured):
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    e.initialize(config)
    v = e.run()
    assert v["gate"]["scope"] == "PLAN"
    assert len(stub.starts) == 2
    export = root / "docs/ai/work-items/test-work/STATE.json"
    export.write_text('{"status":"RELEASED"}')
    assert e.run()["status"] == "PLAN_SUBMITTED"
    v = e.approve(plan_token(e))
    assert v["status"] == "VERIFIED_FOR_RELEASE"
    assert v["gate"]["scope"] == "COMMIT"
    assert len(stub.starts) == 4
    count = len(e.store.events())
    assert e.run()["status"] == "VERIFIED_FOR_RELEASE"
    assert len(e.store.events()) == count
    assert len(stub.starts) == 4
    e.close()


def test_restart_reattaches_without_redispatch_and_duplicate_result(configured):
    root, config = configured
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    e.initialize(config)
    v = e.run()
    job = e.store.job(v["active_jobs"][0])
    assert len(stub.starts) == 1
    e.close()
    e = Engine(root, launcher=stub)
    e.run()
    assert len(stub.starts) == 1
    stub.complete(job)
    v = e.run()
    assert len(stub.starts) == 2  # next independent reviewer only
    assert len([x for x in e.store.events() if x["event_id"] == "result-" + job["job_id"]]) == 1
    e.run()
    assert len(stub.starts) == 2
    e.close()


def test_uncertain_launch_pauses_without_retry(configured):
    root, config = configured
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    e.initialize(config)
    v = e.run()
    job_id = v["active_jobs"][0]
    e.store.update_job(job_id, "LAUNCH_INTENT")
    e.launcher = None
    v = e.run()
    assert v["status"] == "PAUSED"
    assert v["pause_reason"] == "RECONCILIATION_REQUIRED"
    assert len(stub.starts) == 1
    e.close()


def test_quorum_requires_all_independent_responses(configured):
    root, config = configured
    config["quorum"] = ["ai-a1", "ai-a2", "ai-a3"]
    stub = Stub()
    e = Engine(root, launcher=stub)
    e.initialize(config)
    e.run()
    v = e.approve(plan_token(e))
    assert v["status"] == "VERIFIED_FOR_RELEASE"
    assert len(stub.starts) == 7
    e.close()


def test_stale_grant_rejected(configured):
    root, config = configured
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    e.run()
    token = plan_token(e)
    token["scope_hash"] = "f" * 64
    with pytest.raises(WorkflowError):
        e.approve(token)
    assert e.view()["gate"]["scope"] == "PLAN"
    e.close()


def test_database_restore_cannot_resurrect_old_grants(configured, tmp_path):
    root, config = configured
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    e.run()
    backup = tmp_path / "backup.db"
    e.store.backup(backup)
    e.approve(plan_token(e))
    e.close()
    db = root / "orchestrator/var/checkpoints.db"
    shutil.copyfile(backup, db)
    e = Engine(root, launcher=Stub())
    with pytest.raises(WorkflowError, match="Backup restore"):
        e.run()
    e.close()


def test_owner_pause_resume_keeps_inflight_job(configured):
    root, config = configured
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    e.initialize(config)
    e.run()
    jobs = e.view()["active_jobs"][:]
    e.store.event("pause", "pause", {"reason": "OWNER:inspection"})
    assert e.run()["status"] == "PAUSED"
    e.store.event("resume", "resume", {"reason": "continue", "reset_budget": False})
    assert e.run()["active_jobs"] == jobs and len(stub.starts) == 1
    e.close()


def test_owner_reconciliation_allows_new_attempt_after_unknown_launch(configured, tmp_path):
    root, config = configured
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    e.initialize(config)
    e.run()
    job_id = e.view()["active_jobs"][0]
    e.store.update_job(job_id, "LAUNCH_INTENT")
    e.launcher = None
    e.run()
    evidence = tmp_path / "inspection.md"
    evidence.write_text("SYNTHETIC owner inspection: no child exists and no source effects.")
    e.reconcile_job(job_id, evidence)
    e.refresh_candidate("owner inspected source")
    e.launcher = stub
    e.store.event("resume", "resume", {"reason": "owner reconciled", "reset_budget": False})
    e.run()
    assert len(stub.starts) == 2 and stub.starts[0] != stub.starts[1]
    e.close()


def test_stage_advance_requires_reconciled_owner_commit(configured):
    root, config = configured
    config["stages"] = ["1", "2"]
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    e.run()
    e.approve(plan_token(e))
    with pytest.raises(WorkflowError):
        e.advance_stage()
    v = e.view()
    c = v["candidate"]
    token = dict(
        schema_version=1,
        token_id="owner-commit-1",
        work_item=v["work_item"],
        gate_id=v["gate"]["gate_id"],
        scope="COMMIT",
        issuer="owner",
        issued_utc=utc(),
        status="ISSUED",
        candidate_id=c["candidate_id"],
        manifest_hash=c["manifest_hash"],
        repository_id=str(root),
        branch="test",
        expected_parent_sha=config["base_commit"],
        expected_tree_oid=c["tree_oid"],
        job_id="commit-1",
    )
    e.approve(token)
    with pytest.raises(WorkflowError):
        e.record_owner_commit()
    git(
        root,
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "--allow-empty",
        "-m",
        "synthetic owner commit\n\nWorkflow-Job: commit-1",
    )
    v = e.record_owner_commit()
    assert v["status"] == "VERIFIED_FOR_RELEASE" and v["committed"]
    assert e.store.grant_for(token["gate_id"])["status"] == "CONSUMED"
    v = e.advance_stage()
    assert v["stage"] == "2" and v["gate"]["scope"] == "PLAN"
    assert "1" in v["stages"]
    e.close()


def test_recovery_requires_owner_review_and_invalidates_all_old_grants(configured, tmp_path):
    root, config = configured
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    e.run()
    backup = tmp_path / "backup.db"
    e.store.backup(backup)
    old_token = plan_token(e)
    e.approve(old_token)
    e.close()
    shutil.copyfile(backup, root / "orchestrator/var/checkpoints.db")
    e = Engine(root, launcher=Stub())
    with pytest.raises(WorkflowError):
        e.approve(old_token)
    evidence = tmp_path / "owner-review.md"
    evidence.write_text("SYNTHETIC owner recovery review; no external operations occurred.")
    with pytest.raises(WorkflowError):
        e.recover_backup(evidence, False)
    v = e.recover_backup(evidence, True)
    assert v["gate"]["scope"] == "PLAN" and not v["plan_granted"]
    assert not e.store.meta("recovery_required")
    e.close()


def test_unknown_finding_id_is_rejected_before_authoritative_acceptance(configured):
    root, config = configured
    finding = {
        "schema_version": 1,
        "finding_id": "SCP-999",
        "classification": "implementation_defect",
        "blocking": True,
        "summary": "Unallocated ID",
        "affected_requirements": ["R1"],
        "evidence_refs": [],
        "snapshot": None,
    }
    stub = Stub(outcomes={"verifier": {"verdict": "BLOCKED", "findings": [finding]}})
    e = Engine(root, launcher=stub)
    e.initialize(config)
    e.run()
    v = e.approve(plan_token(e))
    assert v["status"] == "PAUSED"
    assert not any(x["kind"] == "result" and x["payload"]["role"] == "verifier" for x in e.store.events())
    e.close()


def test_consumed_token_document_cannot_be_issued_again(configured):
    root, config = configured
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    e.run()
    token = plan_token(e)
    token["status"] = "CONSUMED"
    with pytest.raises(WorkflowError):
        e.approve(token)
    assert not e.store.grant_for(token["gate_id"])
    e.close()
