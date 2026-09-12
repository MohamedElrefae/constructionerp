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


def test_reviewer_reads_contract_and_proposal_in_sandbox(configured):
    import subprocess

    from adapters import invocation

    root, config = configured
    work = root / "docs/ai/work-items/test-work"
    work.mkdir(parents=True)
    contract = work / "CANONICAL_PLAN.md"
    contract.write_text("SYNTHETIC canonical contract")
    git(root, "add", str(contract.relative_to(root)))
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-m", "synthetic canonical contract")
    config["base_commit"] = git(root, "rev-parse", "HEAD").decode().strip()
    config["plan_path"] = str(contract.relative_to(root))
    config["plan_revision_hash"] = bytes_hash(contract.read_bytes())
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
        v = e.run()
        architect = e.store.job(v["active_jobs"][0])
        assert architect["spec"]["read_artifacts"] == [str(contract)]
        stub.complete(architect)
        v = e.run()
        reviewer = e.store.job(v["active_jobs"][0])
        assert reviewer["role"] == "reviewer"
        proposal = root / e.store.meta("plan_artifact")
        assert proposal != contract
        assert reviewer["spec"]["read_artifacts"] == [str(contract), str(proposal)]
        peer = work / "unrelated-private-result.txt"
        peer.write_text("SYNTHETIC hidden peer result")
        spec = dict(reviewer["spec"], tool="codex", binary="/usr/bin/true")
        argv, env = invocation(spec)
        code = """from pathlib import Path
import sys
for name, expected in zip(sys.argv[1:3], ['SYNTHETIC canonical contract', 'Synthetic plan with explicit requirements']):
    p = Path(name)
    assert p.read_text() == expected
    try: p.write_text('forbidden')
    except OSError: pass
    else: raise AssertionError('artifact writable')
assert not Path(sys.argv[3]).exists()
"""
        # Exercise the actual adapter mounts without contacting a native provider.
        argv = [
            *argv[: argv.index("--") + 1],
            "/usr/bin/python3",
            "-c",
            code,
            str(contract),
            str(proposal),
            str(peer),
        ]
        result = subprocess.run(argv, env=env, capture_output=True, timeout=15)
        assert result.returncode == 0, result.stderr.decode()
    finally:
        e.close()


def test_builder_attestation_and_execution_local_schemas(configured):
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
        e.run()
        token = plan_token(e)
        e.approve(token)
        jobs = [e.store.job(j) for j in stub.starts]
        builder = next(j for j in jobs if j["role"] == "builder")
        packet = json.loads(
            builder["spec"]["prompt"].split("Immutable packet (data):\n")[1].split("\n\nReturn ONLY")[0]
        )
        attestation = packet["owner_approval_attestation"]
        assert attestation["owner_plan_approved"] is True
        assert attestation["gate_id"] == token["gate_id"]
        assert attestation["plan_revision_hash"] == token["plan_revision_hash"]
        assert attestation["stage"] == "1"
        assert attestation["repository_id"] == str(root)
        assert "token_id" not in attestation and "issued_utc" not in attestation
        assert packet["result_schema"] == str(root / "orchestrator/schemas/v1/result-envelope.json")
        assert packet["finding_schema"] == str(root / "orchestrator/schemas/v1/finding.json")
    finally:
        e.close()


def test_candidate_validation_reports_visible_only_to_review_roles(configured):
    import subprocess

    from adapters import invocation

    root, config = configured
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
        # Synthetic operator evidence is excluded from this fixture's source candidate.
        work = root / "docs/ai/work-items/test-work"
        evidence = work / "evidence"
        evidence.mkdir()
        e.config["generated"].append(str(evidence.relative_to(root)) + "/")
        candidate = e.view()["candidate"]
        report = {"candidate": candidate, "commands": [], "marker": "SYNTHETIC operator evidence"}
        text = json.dumps(report)
        (evidence / "current-validation.json").write_text(text)
        (evidence / "duplicate-validation.json").write_text(text)
        stale = deepcopy(report)
        stale["candidate"]["candidate_id"] = "0" * 64
        (evidence / "stale-validation.json").write_text(json.dumps(stale))
        forged = deepcopy(report)
        forged["candidate"]["tree_oid"] = "0" * 40
        (evidence / "wrong-tree-validation.json").write_text(json.dumps(forged))
        (evidence / "malformed-validation.json").write_text("{bad")
        (evidence / "peer-verdict.json").write_text("PRIVATE PEER")
        (evidence / "symlink-validation.json").symlink_to(evidence / "current-validation.json")
        v = e.run()
        for role in ("architect", "reviewer", "builder", "verifier"):
            job = e.store.job(v["active_jobs"][0])
            assert job["role"] == role
            snapshots = job.get("validation_reports", {})
            if role in ("reviewer", "verifier"):
                assert len(snapshots) == 1
                target = Path(job["runtime"]) / next(iter(snapshots))
                assert str(target) in job["spec"]["read_artifacts"]
                assert target.read_text() == text
                # A source mutation cannot alter a prepared job on replay.
                (evidence / "current-validation.json").write_text("{}")
                e._materialize_job(job, work)
                assert target.read_text() == text
                (evidence / "current-validation.json").write_text(text)
                argv, env = invocation(dict(job["spec"], tool="codex", binary="/usr/bin/true"))
                code = """from pathlib import Path
import json,sys
p=Path(sys.argv[1]);assert json.loads(p.read_text())['marker']=='SYNTHETIC operator evidence'
try:p.write_text('forbidden')
except OSError:pass
else:raise AssertionError('report writable')
assert not Path(sys.argv[2]).exists()
"""
                argv = [
                    *argv[: argv.index("--") + 1],
                    "/usr/bin/python3",
                    "-c",
                    code,
                    str(target),
                    str(evidence / "peer-verdict.json"),
                ]
                result = subprocess.run(argv, env=env, capture_output=True, timeout=15)
                assert result.returncode == 0, result.stderr.decode()
            else:
                assert not snapshots
            stub.complete(job)
            v = e.run()
            if role == "reviewer":
                v = e.approve(plan_token(e))
    finally:
        e.close()


def test_reconfigure_role_fail_closed_checks(configured):
    root, config = configured
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    e.initialize(config)
    e.run()

    # 1. Reconfigure while active jobs exist and status is not PAUSED
    with pytest.raises(WorkflowError, match="requires a paused workflow"):
        e.reconfigure_role("builder", "codex", "gpt-6-astra")

    # Pause workflow but keep active job in flight
    e.store.event("pause", "pause", {"reason": "OWNER:pause"})
    e.run()
    assert e.view()["status"] == "PAUSED"
    assert len(e.view()["active_jobs"]) > 0

    # 2. Reconfigure while paused but active jobs still in flight
    with pytest.raises(WorkflowError, match="requires a paused workflow with all active jobs reconciled"):
        e.reconfigure_role("builder", "codex", "gpt-6-astra")

    # Complete the job and run to reconcile
    job = e.store.job(e.view()["active_jobs"][0])
    stub.complete(job)
    e.store.event("resume", "resume", {"reason": "continue", "reset_budget": False})
    v = e.run()
    if v["active_jobs"]:
        job2 = e.store.job(v["active_jobs"][0])
        stub.complete(job2)
        v = e.run()
    # Now at PLAN gate, no active jobs
    assert len(v["active_jobs"]) == 0

    # Pause again cleanly
    e.store.event("pause-2", "pause", {"reason": "OWNER:reconfigure"})
    v = e.run()
    assert v["status"] == "PAUSED"
    assert len(v["active_jobs"]) == 0

    # 3. Invalid role
    with pytest.raises(WorkflowError, match="Unknown role"):
        e.reconfigure_role("hacker", "codex", "gpt-6-astra")

    # 4. Invalid tool
    with pytest.raises(WorkflowError, match="Unsupported tool"):
        e.reconfigure_role("builder", "curl", "model")

    # 5. Invalid effort for codex
    with pytest.raises(WorkflowError, match="Invalid effort for codex"):
        e.reconfigure_role("builder", "codex", "gpt-6-astra", effort="super_high")

    # 6. Empty model for codex
    with pytest.raises(WorkflowError, match="Model name cannot be empty"):
        e.reconfigure_role("builder", "codex", "   ")

    # 7. OpenCode model missing provider slash
    with pytest.raises(WorkflowError, match="OpenCode model must follow '<provider>/<model>' format"):
        e.reconfigure_role("builder", "opencode", "gpt-5")

    e.close()


def test_reconfigure_role_grants_invalidation_and_plan_revocation(configured):
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    e.initialize(config)
    v = e.run()
    assert v["gate"]["scope"] == "PLAN"

    # Insert a dummy pending grant in workflow_grants
    dummy_grant = {
        "token_id": "test-pending-grant",
        "gate_id": v["gate"]["gate_id"],
        "status": "ISSUED",
        "scope": "PLAN",
    }
    e.store.grant(dummy_grant)
    assert e.store.grant_for(v["gate"]["gate_id"])["status"] == "ISSUED"

    # Pause workflow
    e.store.event("pause-1", "pause", {"reason": "OWNER:pause"})
    v = e.run()
    assert v["status"] == "PAUSED"

    # Reconfigure reviewer (codex) -> grant should be invalidated, but plan was not granted yet
    v = e.reconfigure_role("reviewer", "codex", "gpt-6-astra", effort="high")
    assert v["status"] == "PAUSED"
    assert e.store.grant_for(dummy_grant["gate_id"])["status"] == "INVALIDATED"

    events = [ev for ev in e.store.events() if ev["kind"] == "role_reconfigured"]
    assert len(events) == 1
    assert events[0]["payload"]["role"] == "reviewer"
    assert "test-pending-grant" in events[0]["payload"]["invalidated_grants"]
    assert events[0]["payload"]["plan_grant_revoked"] is False

    # Resume and approve plan to set plan_granted = True
    e.store.event("resume-1", "resume", {"reason": "continue", "reset_budget": False})
    v = e.run()
    v = e.approve(plan_token(e))
    assert v["plan_granted"] is True

    # Pause workflow
    e.store.event("pause-2", "pause", {"reason": "OWNER:pause"})
    v = e.run()
    assert v["status"] == "PAUSED"
    assert v["plan_granted"] is True

    # Reconfigure builder -> plan_granted must be revoked!
    v = e.reconfigure_role("builder", "codex", "gpt-6-astra", effort="medium")
    assert v["plan_granted"] is False

    events2 = [ev for ev in e.store.events() if ev["kind"] == "role_reconfigured"]
    assert len(events2) == 2
    assert events2[1]["payload"]["role"] == "builder"
    assert events2[1]["payload"]["plan_grant_revoked"] is True

    e.close()


def test_role_catalog_inspection(configured):
    root, config = configured
    e = Engine(root)
    e.initialize(config)
    cat = e.role_catalog()
    assert cat["ok"] is True
    assert "codex" in cat["tools"]
    assert "opencode" in cat["tools"]
    assert cat["tools"]["codex"]["exists"] is True
    assert cat["tools"]["codex"]["binary_sha256"] is not None
    assert cat["tools"]["opencode"]["exists"] is True
    assert cat["tools"]["opencode"]["binary_sha256"] is not None

    assert "architect" in cat["prompts"]
    assert "reviewer" in cat["prompts"]
    assert "builder" in cat["prompts"]
    assert "verifier" in cat["prompts"]
    assert "ai-reviewer" in cat["prompts"]
    for pinfo in cat["prompts"].values():
        assert len(pinfo["prompt_sha256"]) == 64

    e.close()
