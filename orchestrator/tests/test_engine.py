import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from candidates import git
from core import ValidationError as CoreValidationError
from core import WorkflowError, bytes_hash, canonical, digest, utc, write_json
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


def plan_token(engine, token_id="owner-plan"):
    v = engine.view()
    roles_hash = v.get("roles_hash") or digest(engine.config.get("roles", {}))
    return dict(
        schema_version=2,
        token_id=token_id,
        work_item=v["work_item"],
        gate_id=v["gate"]["gate_id"],
        issuer="owner",
        issued_utc=utc(),
        status="ISSUED",
        scope="PLAN",
        plan_revision_hash=v["plan_revision_hash"],
        scope_hash=v["scope_hash"],
        roles_hash=roles_hash,
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

    # Reconfiguring reviewer (not builder/proposer) must ALSO revoke plan_granted and reset gate to PLAN!
    v = e.reconfigure_role("reviewer", "codex", "gpt-6-astra", effort="low")
    assert v["plan_granted"] is False
    assert v["status"] == "PAUSED"
    assert v["prior"]["gate"]["scope"] == "PLAN"

    events2 = [ev for ev in e.store.events() if ev["kind"] == "role_reconfigured"]
    assert len(events2) == 2
    assert events2[1]["payload"]["role"] == "reviewer"
    assert events2[1]["payload"]["plan_grant_revoked"] is True

    # When resumed, the gate is PLAN and plan must be approved again before build
    e.store.event("resume-2", "resume", {"reason": "continue", "reset_budget": False})
    v = e.run()
    assert v["gate"]["scope"] == "PLAN"
    assert v["plan_granted"] is False

    e.close()


def test_offline_plan_token_rejected_after_second_role_change(configured):
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    e.initialize(config)
    v0 = e.run()
    assert v0["gate"]["scope"] == "PLAN"
    initial_roles_hash = v0["roles_hash"]
    token_initial = plan_token(e, token_id="offline-token-initial")

    # Pause workflow
    e.store.event("pause-1", "pause", {"reason": "OWNER:pause"})
    v1 = e.run()
    assert v1["status"] == "PAUSED"

    # First role change while plan_granted is False
    v1 = e.reconfigure_role("reviewer", "codex", "gpt-6-astra", effort="high")
    assert v1["status"] == "PAUSED"
    assert v1["plan_granted"] is False

    # Resume to PLAN gate
    e.store.event("resume-1", "resume", {"reason": "continue", "reset_budget": False})
    v1 = e.run()
    assert v1["gate"]["scope"] == "PLAN"
    gate_id_first_change = v1["gate"]["gate_id"]
    roles_hash_first_change = v1["roles_hash"]
    assert roles_hash_first_change != initial_roles_hash
    assert gate_id_first_change != token_initial["gate_id"]

    # Initial offline token prepared before the first change is rejected
    with pytest.raises(WorkflowError):
        e.approve(token_initial)

    # Prepare an offline token for gate_id_first_change with roles_hash_first_change
    token_first = plan_token(e, token_id="offline-token-first-change")

    # Pause workflow again WITHOUT approving plan (plan_granted remains False)
    e.store.event("pause-2", "pause", {"reason": "OWNER:pause"})
    v2 = e.run()
    assert v2["status"] == "PAUSED"
    assert v2["plan_granted"] is False

    # Second role change while plan_granted is False
    v2 = e.reconfigure_role("reviewer", "codex", "gpt-6-astra", effort="low")
    assert v2["status"] == "PAUSED"
    assert v2["plan_granted"] is False

    # Resume to PLAN gate
    e.store.event("resume-2", "resume", {"reason": "continue", "reset_budget": False})
    v2 = e.run()
    assert v2["gate"]["scope"] == "PLAN"
    gate_id_second_change = v2["gate"]["gate_id"]
    roles_hash_second_change = v2["roles_hash"]

    # Assert that gate rotated even though plan_granted was already False!
    assert gate_id_second_change != gate_id_first_change
    assert roles_hash_second_change != roles_hash_first_change

    # Stale offline token from first change is rejected because gate_id doesn't match
    with pytest.raises(WorkflowError, match="Approval does not match pending gate"):
        e.approve(token_first)

    # Even if attacker forges gate_id to match current gate, roles_hash mismatch is rejected
    forged_token = deepcopy(token_first)
    forged_token["gate_id"] = gate_id_second_change
    forged_token["token_id"] = "forged-stale-roles-hash"
    with pytest.raises(WorkflowError, match="PLAN binding mismatch"):
        e.approve(forged_token)

    # Fresh offline token with current gate_id and roles_hash succeeds
    token_second = plan_token(e, token_id="offline-token-second-change")
    v_approved = e.approve(token_second)
    assert v_approved["plan_granted"] is True

    e.close()


def test_roles_mirror_recovery_from_sqlite(configured):
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    e.initialize(config)
    v = e.run()
    roles_file = root / "orchestrator/roles.json"
    assert roles_file.exists()
    original_roles = json.loads(roles_file.read_text())
    assert canonical(original_roles) == canonical(e.config["roles"])
    e.close()

    # Simulate roles.json deletion
    roles_file.unlink()
    assert not roles_file.exists()

    # New Engine initialization must automatically recover roles.json from SQLite config
    e2 = Engine(root, launcher=stub)
    assert roles_file.exists()
    recovered_roles = json.loads(roles_file.read_text())
    assert canonical(recovered_roles) == canonical(e2.config["roles"])
    e2.close()

    # Corrupt roles.json and test recovery on Engine init
    roles_file.write_text('{"corrupted": true}')
    e3 = Engine(root, launcher=stub)
    recovered_roles3 = json.loads(roles_file.read_text())
    assert canonical(recovered_roles3) == canonical(e3.config["roles"])
    e3.close()


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


def test_legacy_plan_token_contract_and_historical_checkpoint_migration(configured, tmp_path):
    import hashlib
    from copy import deepcopy

    from core import canonical, digest
    from routing import gate_id
    from store import Store
    from validate import validate_document

    root, config = configured
    scope_hash = digest(config["scope"])

    mock_private = tmp_path / "mock_private"
    blobs = mock_private / "blobs"
    blobs.mkdir(parents=True)
    catalog_bytes = b"{}"
    catalog_sha = hashlib.sha256(catalog_bytes).hexdigest()
    (blobs / f"{catalog_sha}.json").write_bytes(catalog_bytes)

    candidate = {
        "kind": "stage4-proposal",
        "candidate_id": digest(
            {
                "kind": "stage4-proposal",
                "export_sha256": catalog_sha,
                "proposal_sha256": "0" * 64,
            }
        ),
        "export_sha256": catalog_sha,
        "proposal_sha256": "0" * 64,
    }

    # 1. Historical legacy sequence-1 token contract validation
    legacy_token = {
        "schema_version": 1,
        "token_id": "plan-token-plan-257525eeb45afcf9a81f7c11",
        "work_item": config["work_item"],
        "gate_id": "plan-257525eeb45afcf9a81f7c11",
        "issuer": "project-owner",
        "issued_utc": "2026-09-12T19:51:01.880486Z",
        "status": "ISSUED",
        "scope": "PLAN",
        "plan_revision_hash": config["plan_revision_hash"],
        "scope_hash": scope_hash,
        "repository_id": str(root),
        "branch": config["branch"],
        "stages": ["0", "1", "2", "3", "4"],
    }
    assert legacy_token["schema_version"] == 1
    assert "roles_hash" not in legacy_token
    assert legacy_token["scope"] == "PLAN"
    validate_document("approval-token", legacy_token)

    # 2. Setup self-contained temporary legacy database & checkpoint
    runtime = tmp_path / "legacy_runtime"
    runtime.mkdir()
    store = Store(runtime / "checkpoints.db")

    # Historical config deliberately lacks roles_hash to verify migration
    hist_config = deepcopy(config)
    hist_config["stage"] = "4"
    hist_config["stages"] = ["4"]
    hist_config["scope_hash"] = scope_hash
    hist_config["candidate"] = candidate
    hist_config["private_root"] = str(mock_private)
    hist_config["generated"] = ["orchestrator/roles.json", "orchestrator/var/"]
    hist_config["roles"]["proposer"] = {
        "tool": "opencode",
        "binary": "opencode",
        "model": "opencode/muse-spark-1.3-contributor-free",
    }
    hist_config.pop("roles_hash", None)
    expected_roles_hash = digest(hist_config["roles"])
    store.set_meta("config", hist_config)

    # Historical event lineage
    store.event("grant-" + legacy_token["token_id"], "grant", legacy_token)
    store.event(
        "reconcile-job-0e0d4d73f8732d43186d1a13",
        "reconcile_job",
        {
            "job_id": "job-0e0d4d73f8732d43186d1a13",
            "role": "proposer",
            "owner_evidence_sha256": "cf1a60cc0c20946ede9eec04ab519ce258c86dd3165162d6755942c2507257aa",
            "decision": "ABANDONED_AFTER_OWNER_REVIEW",
        },
    )
    store.event(
        "owner-5e7c8920a7794739bfe0e4cf6295dc0c",
        "resume",
        {
            "reason": "Switch proposer to opencode/muse-spark-1.3-contributor-free",
            "reset_budget": False,
        },
    )
    store.event(
        "reconcile-job-26261b6a46e9d461b869f6bd",
        "reconcile_job",
        {
            "job_id": "job-26261b6a46e9d461b869f6bd",
            "role": "proposer",
            "owner_evidence_sha256": "f6cdb7a328b5b43841bc3b124907ac73a61e41f1d72bc986661da7224ae6cf16",
            "decision": "ABANDONED_AFTER_OWNER_REVIEW",
        },
    )

    # Historical jobs and grants
    store.create_job("proposer-1", {"job_id": "job-0e0d4d73f8732d43186d1a13", "role": "proposer"})
    store.update_job("job-0e0d4d73f8732d43186d1a13", "OWNER_RECONCILED")
    store.create_job("proposer-2", {"job_id": "job-26261b6a46e9d461b869f6bd", "role": "proposer"})
    store.update_job("job-26261b6a46e9d461b869f6bd", "OWNER_RECONCILED")
    store.grant(legacy_token)
    store.consume(legacy_token["gate_id"])
    store.close()

    # Pre-populate LangGraph checkpoint with historical parked state (roles_hash omitted from view)
    e_init = Engine(root, runtime=runtime)
    computed_gate = gate_id(
        {
            "work_item": config["work_item"],
            "stage": "4",
            "plan_revision_hash": config["plan_revision_hash"],
            "scope_hash": scope_hash,
            "roles_hash": expected_roles_hash,
        },
        "PLAN",
    )

    legacy_view = {
        "work_item": config["work_item"],
        "stage": "4",
        "status": "DRAFT",
        "sub_status": "PROPOSAL_PENDING",
        "gate": {"scope": "PLAN", "gate_id": computed_gate},
        "plan_granted": False,
        "active_jobs": [],
        "next_roles": [],
        "round": 0,
        "attempt": 2,
        "cursor": 4,
        "revision": 4,
        "approval_refs": [legacy_token["token_id"]],
        "plan_revision_hash": config["plan_revision_hash"],
        "scope_hash": scope_hash,
        "candidate": candidate,
        "stages": {"4": {"sub_status": "PROPOSAL_PENDING", "historical": False, "evidence_refs": []}},
        "findings": [],
        "backlog": [],
        "completed_dependencies": [],
        "review_results": {},
        "unsuccessful_cycles": 0,
        "unchanged_rounds": 0,
        "previous_snapshots": [],
        "pause_reason": None,
        "resume_to": None,
        "prior": None,
        "committed": False,
    }
    e_init.graph.update_state(e_init.graph_config, {"view": legacy_view}, as_node="collect")
    e_init.close()

    # Ensure config in store lacks roles_hash so Engine.__init__ migration can be asserted
    store = Store(runtime / "checkpoints.db")
    c = store.meta("config")
    c.pop("roles_hash", None)
    store.set_meta("config", c)
    store.close()

    # 3. Boot Engine on the legacy runtime and verify automatic migration
    stub = Stub(delayed=True)
    e = Engine(root, runtime=runtime, launcher=stub)
    try:
        assert "roles_hash" in e.config
        assert e.config["roles_hash"] == expected_roles_hash
        assert e.store.meta("config")["roles_hash"] == expected_roles_hash

        v = e.view()
        assert v["roles_hash"] == expected_roles_hash
        assert v["status"] == "DRAFT"
        assert v["sub_status"] == "PROPOSAL_PENDING"
        assert v["plan_granted"] is False
        assert v["active_jobs"] == []
        assert v["next_roles"] == []
        assert v["gate"]["scope"] == "PLAN"
        assert v["gate"]["gate_id"] == computed_gate
        assert v["approval_refs"] == [legacy_token["token_id"]]
        assert v["cursor"] == 4
        assert v["revision"] == 4

        # 4. Token validation: consumed legacy token is rejected as used
        with pytest.raises(WorkflowError, match="Token already used or recorded"):
            e.approve(legacy_token)

        # Fresh unrecorded v1 token is rejected
        fresh_v1 = dict(legacy_token, token_id="fresh-v1-token", gate_id=v["gate"]["gate_id"])
        with pytest.raises(WorkflowError, match="Legacy schema_version 1 PLAN tokens cannot be reused"):
            e.approve(fresh_v1)

        # Valid v2 token with roles_hash is accepted and grants plan
        v2_token = dict(
            schema_version=2,
            token_id="valid-v2-token",
            work_item=v["work_item"],
            gate_id=v["gate"]["gate_id"],
            issuer="owner",
            issued_utc="2026-09-14T20:00:00Z",
            status="ISSUED",
            scope="PLAN",
            plan_revision_hash=v["plan_revision_hash"],
            scope_hash=v["scope_hash"],
            roles_hash=v["roles_hash"],
            repository_id=str(root),
            branch=config["branch"],
            stages=["4"],
        )
        assert e.approve(v2_token)["plan_granted"] is True
    finally:
        e.close()


def test_resume_rejected_against_parked_draft_plan_state(configured, tmp_path):
    from routing import apply_event, gate_id
    from store import Store

    root, config = configured
    scope_hash = digest(config["scope"])
    runtime = tmp_path / "parked_runtime"
    runtime.mkdir()
    store = Store(runtime / "checkpoints.db")

    candidate = {
        "kind": "stage4-proposal",
        "candidate_id": digest(
            {
                "kind": "stage4-proposal",
                "export_sha256": "0" * 64,
                "proposal_sha256": "0" * 64,
            }
        ),
        "export_sha256": "0" * 64,
        "proposal_sha256": "0" * 64,
    }

    hist_config = deepcopy(config)
    hist_config["stage"] = "4"
    hist_config["scope_hash"] = scope_hash
    hist_config["candidate"] = candidate
    roles_hash = digest(config["roles"])
    hist_config["roles_hash"] = roles_hash
    store.set_meta("config", hist_config)
    store.close()

    e = Engine(root, runtime=runtime)
    try:
        computed_gate = gate_id(
            {
                "work_item": config["work_item"],
                "stage": "4",
                "plan_revision_hash": config["plan_revision_hash"],
                "scope_hash": scope_hash,
                "roles_hash": roles_hash,
            },
            "PLAN",
        )

        parked_view = {
            "work_item": config["work_item"],
            "stage": "4",
            "status": "DRAFT",
            "sub_status": "PROPOSAL_PENDING",
            "gate": {"scope": "PLAN", "gate_id": computed_gate},
            "plan_granted": False,
            "active_jobs": [],
            "next_roles": [],
            "round": 0,
            "attempt": 2,
            "cursor": 4,
            "revision": 4,
            "approval_refs": ["plan-token-plan-257525eeb45afcf9a81f7c11"],
            "plan_revision_hash": config["plan_revision_hash"],
            "scope_hash": scope_hash,
            "roles_hash": roles_hash,
            "candidate": candidate,
            "stages": {"4": {"sub_status": "PROPOSAL_PENDING", "historical": False, "evidence_refs": []}},
            "findings": [],
            "backlog": [],
            "completed_dependencies": [],
            "review_results": {},
            "unsuccessful_cycles": 0,
            "unchanged_rounds": 0,
            "previous_snapshots": [],
            "pause_reason": None,
            "resume_to": None,
            "prior": None,
            "committed": False,
        }
        e.graph.update_state(e.graph_config, {"view": parked_view}, as_node="collect")

        # 1. Pure router check: resume against parked DRAFT state is rejected
        with pytest.raises(WorkflowError, match="Cannot resume"):
            apply_event(
                parked_view, {"seq": 5, "kind": "resume", "payload": {"reason": "router bypass"}}, hist_config
            )
        assert parked_view["plan_granted"] is False
        assert parked_view["next_roles"] == []
        assert parked_view["gate"]["scope"] == "PLAN"
        assert parked_view["gate"]["gate_id"] == computed_gate
        assert parked_view["status"] == "DRAFT"

        # 2. Engine owner_decision check: resume against parked DRAFT state is rejected
        with pytest.raises(WorkflowError, match="Cannot resume"):
            e.owner_decision("resume", {"reason": "engine bypass"})

        v = e.view()
        assert v["plan_granted"] is False
        assert v["next_roles"] == []
        assert v["gate"]["scope"] == "PLAN"
        assert v["gate"]["gate_id"] == computed_gate
        assert v["status"] == "DRAFT"
        assert len(e.store.events()) == 0
    finally:
        e.close()


# ---------------------------------------------------------------------------
# DECISION approval scope (work item: owner-decision-scope-support)
# ---------------------------------------------------------------------------

OPERATOR_PAUSE = "OPERATOR-PAUSE"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def decision_gate(configured):
    """Park a real workflow on a DECISION gate via the sanctioned owner_decision API."""
    root, config = configured
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
        e.run()
        e.approve(plan_token(e))
        v = e.owner_decision("pause", {"reason": "OWNER_DECISION"})
        assert v["status"] == "PAUSED", v["status"]
        assert v["gate"]["scope"] == "DECISION", v["gate"]
        return e
    except Exception:
        e.close()
        raise


def decision_token(engine, token_id="owner-decision", digests=(OPERATOR_PAUSE,), **overrides):
    v = engine.view()
    token = dict(
        schema_version=1,
        token_id=token_id,
        work_item=v["work_item"],
        gate_id=v["gate"]["gate_id"],
        issuer="owner",
        issued_utc=utc(),
        status="ISSUED",
        scope="DECISION",
        disposition="RATIFIED",
        decision_hash="d" * 64,
        candidate_id=v["candidate"]["candidate_id"],
        plan_revision_hash=v["plan_revision_hash"],
        scope_hash=v["scope_hash"],
        resolved_finding_digests=list(digests),
        repository_id=str(engine.root),
        branch=engine.config["branch"],
        expected_parent_sha=engine.config["base_commit"],
    )
    token.update(overrides)
    return token


def test_decision_scope_acceptance_clears_gate(configured):
    """T1: a fully-bound DECISION token clears the gate and records the grant."""
    e = decision_gate(configured)
    try:
        token = decision_token(e)
        v = e.approve(token)
        assert v["gate"] is None, v["gate"]
        assert v["status"] != "PAUSED", v["status"]
        assert v["pause_reason"] is None, v["pause_reason"]
        grants = [g["payload"] for g in e.store.events() if g["kind"] == "grant"]
        assert any(g["scope"] == "DECISION" for g in grants)
        assert v["decision_refs"][0]["token_id"] == token["token_id"]
        assert v["decision_refs"][0]["resolved_finding_digests"] == [OPERATOR_PAUSE]
    finally:
        e.close()


@pytest.mark.parametrize("field", ["gate_id", "work_item"])
def test_decision_scope_rejected_when_gate_mismatch(configured, field):
    """T2: gate/work-item mismatch is refused before any scope-specific check."""
    e = decision_gate(configured)
    try:
        with pytest.raises(WorkflowError):
            e.approve(decision_token(e, **{field: "not-the-pending-gate"}))
        assert e.view()["gate"]["scope"] == "DECISION"
    finally:
        e.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("candidate_id", "0" * 64),
        ("plan_revision_hash", "0" * 64),
        ("scope_hash", "0" * 64),
        ("repository_id", "/elsewhere"),
        ("branch", "other-branch"),
        ("expected_parent_sha", "0" * 40),
    ],
)
def test_decision_scope_rejected_on_content_hash_mismatch(configured, field, value):
    """T3: any content-binding drift is refused and writes no grant."""
    e = decision_gate(configured)
    try:
        token = decision_token(e, **{field: value})
        with pytest.raises(WorkflowError, match="DECISION binding mismatch"):
            e.approve(token)
        assert not e.store.grant_for(token["gate_id"])
        assert e.view()["gate"]["scope"] == "DECISION"
    finally:
        e.close()


def test_decision_scope_rejected_on_finding_not_open(configured):
    """T4: a digest that is not open on this gate is refused."""
    e = decision_gate(configured)
    try:
        with pytest.raises(WorkflowError, match="not open on this gate"):
            e.approve(decision_token(e, digests=[DIGEST_A]))
        assert e.view()["gate"]["scope"] == "DECISION"
    finally:
        e.close()


def test_open_finding_digests_uses_reproduction_digest():
    """T4b: open-finding identity is the content-addressed reproduction_digest.

    Raw result events record finding_id as null; routing.finding_identity() uses
    reproduction_digest, so the decision binding must use the same identity.
    """
    e = Engine.__new__(Engine)
    empty = {"findings": []}
    assert e._open_finding_digests(empty) == {OPERATOR_PAUSE}
    view = {
        "findings": [
            {
                "finding_id": "SCP-006",
                "blocking": True,
                "snapshot": {"reproduction_digest": DIGEST_A},
            },
            {
                "finding_id": "SCP-009",
                "blocking": False,
                "snapshot": {"reproduction_digest": DIGEST_B},
            },
            {"finding_id": "SCP-010", "blocking": True, "snapshot": None},
        ]
    }
    assert e._open_finding_digests(view) == {DIGEST_A}


def test_decision_scope_token_schema_rejects_bad_payloads(configured):
    """T5: the schema itself refuses malformed DECISION tokens."""
    from jsonschema import ValidationError

    from validate import validate_document

    e = decision_gate(configured)
    try:
        base = decision_token(e)
        validate_document("approval-token", base)
        validate_document("approval-token", decision_token(e, digests=[DIGEST_A]))
        bad = {
            "missing decision_hash": {k: v for k, v in base.items() if k != "decision_hash"},
            "non-hex decision_hash": {**base, "decision_hash": "zz"},
            "empty resolved_finding_digests": {**base, "resolved_finding_digests": []},
            "malformed digest entry": {**base, "resolved_finding_digests": ["SCP-006!"]},
            "duplicate digests": {**base, "resolved_finding_digests": [OPERATOR_PAUSE] * 2},
            "bad disposition": {**base, "disposition": "APPROVED"},
            "unknown extra property": {**base, "rogue": "x"},
            "bad expected_parent_sha": {**base, "expected_parent_sha": "nothex"},
        }
        for name, payload in bad.items():
            with pytest.raises(ValidationError):
                validate_document("approval-token", payload)
    finally:
        e.close()


def test_decision_token_cannot_authorize_commit(configured):
    """T6: a DECISION grant confers no commit authority (SPEC principle 2)."""
    e = decision_gate(configured)
    try:
        e.approve(decision_token(e))
        assert e.view()["gate"] is None
        grants = [g["payload"] for g in e.store.events() if g["kind"] == "grant"]
        assert not any(g["scope"] == "COMMIT" for g in grants)
        with pytest.raises(WorkflowError):
            e.record_owner_commit()
    finally:
        e.close()


def test_decision_grant_is_not_an_operation_intent(configured):
    """T7: a DECISION approval writes no operation intent document."""
    e = decision_gate(configured)
    try:
        e.approve(decision_token(e))
        assert list((e.runtime / "operations").rglob("intent.json")) == []
    finally:
        e.close()


def test_decision_token_single_use(configured):
    """T8: a consumed DECISION token cannot be replayed."""
    e = decision_gate(configured)
    try:
        token = decision_token(e)
        e.approve(token)
        assert e.store.grant_for(token["gate_id"])
        replay = dict(token, issued_utc=utc())
        with pytest.raises(WorkflowError):
            e.approve(replay)
    finally:
        e.close()


def test_decision_disposition_routing(configured):
    """Disposition determines the resume target, asserted on the pure state transition.

    Exercised through routing.apply_event rather than a full run so the result does not
    race the graph's subsequent dispatch.
    """
    from routing import apply_event

    for disposition, status, next_roles in (
        ("RATIFIED", "CHANGES_REQUESTED", ["builder"]),
        ("WAIVED", "CHANGES_REQUESTED", ["builder"]),
        ("REJECTED", "NEEDS_REVISION", ["architect"]),
    ):
        state = {
            "status": "PAUSED",
            "gate": {"scope": "DECISION", "gate_id": "decision-99"},
            "pause_reason": "OWNER_DECISION",
            "prior": {"status": "CHANGES_REQUESTED", "next_roles": ["builder"], "gate": None},
            "resume_to": "CHANGES_REQUESTED",
            "cursor": 0,
            "roles_hash": "0" * 64,
            "candidate": {"candidate_id": "0" * 64},
            "approval_refs": [],
            "decision_refs": [],
            "revision": 0,
            "attempt": 1,
        }
        event = {
            "seq": 1,
            "kind": "grant",
            "payload": {
                "token_id": "t-" + disposition,
                "gate_id": "decision-99",
                "scope": "DECISION",
                "disposition": disposition,
                "decision_hash": "d" * 64,
                "resolved_finding_digests": [OPERATOR_PAUSE],
            },
        }
        out = apply_event(state, event, {})
        assert out["gate"] is None, disposition
        assert out["status"] == status, (disposition, out["status"])
        assert out["next_roles"] == next_roles, (disposition, out["next_roles"])
        assert out["decision_refs"][-1]["disposition"] == disposition


def test_roles_model_and_binary_are_pinned():
    """T9: role execution bindings are pinned against a committed second source of truth.

    orchestrator/roles.json is a DERIVED mirror: Engine.sync_roles_mirror() rewrites it from
    SQLite workflow_meta.config on every initialization, so it cannot pin itself. An earlier
    draft of this test asserted only against an in-memory fixture and therefore detected no
    real drift -- exactly the gap that let an off-pin builder/reviewer go unnoticed.

    orchestrator/roles.lock.json is the committed pin. A change to roles.json alone fails
    here; changing a binding is only possible by editing the lock file, which is an explicit
    and reviewable act. See scp007-recheck-and-roles-disposition-2026-09-30.md 2.4.
    """
    root = Path(__file__).resolve().parents[2]
    roles = json.loads((root / "orchestrator/roles.json").read_text())
    locked = json.loads((root / "orchestrator/roles.lock.json").read_text())["roles"]

    assert set(roles) == set(locked), (
        f"role set differs from lock: {sorted(set(roles) ^ set(locked))}"
    )
    for name, expected in locked.items():
        actual = roles[name]
        for field in ("tool", "binary", "model"):
            assert actual[field] == expected[field], (
                f"{name}.{field} drifted from committed pin: "
                f"{actual[field]!r} != {expected[field]!r}"
            )


def test_roles_lock_detects_model_and_binary_drift():
    """T9b: the comparison is sensitive to model and binary drift, not just key presence."""
    root = Path(__file__).resolve().parents[2]
    roles = json.loads((root / "orchestrator/roles.json").read_text())
    locked = json.loads((root / "orchestrator/roles.lock.json").read_text())["roles"]

    drifted = deepcopy(roles)
    drifted["builder"]["model"] = "opencode/off-pin-model"
    drifted["reviewer"]["binary"] = "/tmp/other-codex"
    for name, expected in locked.items():
        for field in ("tool", "binary", "model"):
            if name == "builder" and field == "model":
                assert drifted[name][field] != expected[field]
            if name == "reviewer" and field == "binary":
                assert drifted[name][field] != expected[field]
            if not (name == "builder" and field == "model") and not (
                name == "reviewer" and field == "binary"
            ):
                assert drifted[name][field] == expected[field]


def test_roles_json_is_derived_mirror_not_authority():
    """T9c: roles.json must equal the canonical serialization of the locked bindings.

    Documents that sync_roles_mirror() regenerates this file, which is why the lock file
    exists. If a future refactor made roles.json authoritative, this test states the
    assumption that would need revisiting.
    """
    root = Path(__file__).resolve().parents[2]
    roles = json.loads((root / "orchestrator/roles.json").read_text())
    locked = json.loads((root / "orchestrator/roles.lock.json").read_text())["roles"]
    for name, expected in locked.items():
        assert roles[name]["tool"] == expected["tool"]
        assert roles[name]["binary"] == expected["binary"]
        assert roles[name]["model"] == expected["model"]
    # Every locked role must be a governed role, not an ad-hoc addition.
    assert set(locked) <= set(roles)


def test_evidence_directory_may_be_read_only_context(configured):
    """A work item's own evidence/ may be registered as read-only context.

    evidence/ is excluded from candidate tracking, and _prepare gates *validation.json
    discovery to reviewer/verifier, so read_only_context_paths is the only channel that
    reaches a builder dispatch. Evidence is immutable reference material rather than
    scratchpad output, so the generated-path intersection guard must not reject it.
    """
    root, config = configured
    (root / "AGENTS.md").write_text("# agent context\n")
    (root / "SESSION_MEMORY.md").write_text("# session memory\n")
    git(root, "add", "AGENTS.md", "SESSION_MEMORY.md")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-m", "mandatory context files")
    config["base_commit"] = git(root, "rev-parse", "HEAD").decode().strip()
    work = root / "docs/ai/work-items" / config["work_item"]
    evidence = work / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    disposition = evidence / "scp006-delta-ratification-disposition.md"
    disposition.write_text("Ratified deltas D1-D3.\n")
    report = evidence / "scp008-base-suite-validation.json"
    report.write_text('{"schema":"v1","commands":[]}\n')

    rels = [str(disposition.relative_to(root)), str(report.relative_to(root))]
    config["read_only_context_paths"] = ["AGENTS.md", "SESSION_MEMORY.md", *rels]

    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
        assert e.config["read_only_context_paths"] == config["read_only_context_paths"]
        assert "AGENTS.md" not in e.config["generated"]
        assert e.config["generated"][3] == "docs/ai/work-items/%s/evidence/" % config["work_item"]
    finally:
        e.close()


def test_generated_scratch_paths_still_reject_read_only_context(configured):
    """The intersection guard still rejects scratchpad output, not just evidence/."""
    root, config = configured
    (root / "AGENTS.md").write_text("# agent context\n")
    (root / "SESSION_MEMORY.md").write_text("# session memory\n")
    work_rel = "docs/ai/work-items/%s" % config["work_item"]
    for forbidden in (work_rel + "/runs/job-1", work_rel + "/inbox/x", work_rel + "/STATE.json"):
        cfg = dict(config)
        cfg["read_only_context_paths"] = ["AGENTS.md", "SESSION_MEMORY.md", forbidden]
        e = Engine(root, launcher=Stub())
        try:
            with pytest.raises(CoreValidationError):
                e.initialize(cfg)
        finally:
            e.close()


def test_read_only_context_is_snapshotted_and_hash_bound(configured):
    """Context artefacts are delivered as content-addressed snapshots, not floating paths."""
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
        work = root / "docs/ai/work-items" / config["work_item"]
        context = work / "evidence"
        context.mkdir(parents=True, exist_ok=True)
        doc = context / "disposition.md"
        doc.write_text("ratified deltas D1-D3\n")
        config["read_only_context_paths"] = [str(doc.relative_to(root))]
        e.config["read_only_context_paths"] = config["read_only_context_paths"]
        v = e.view()
        state = e._prepare({"view": v})
        job = e.store.job(state["view"]["active_jobs"][0])
        refs = job["spec"]["read_artifact_refs"]
        assert len(refs) == 1
        ref = refs[0]
        assert ref["source_path"] == str(root / doc)
        assert ref["snapshot_path"].endswith("context/context-" + ref["sha256"] + ".md")
        assert Path(ref["snapshot_path"]).is_file()
        assert Path(ref["snapshot_path"]).read_text() == "ratified deltas D1-D3\n"
        assert str(ref["snapshot_path"]) in job["spec"]["read_artifacts"]
        assert str(root / doc) not in job["spec"]["read_artifacts"]
    finally:
        e.close()


def test_context_mutation_after_preparation_is_refused(configured):
    """A context file edited after preparation cannot be re-materialised silently."""
    root, config = configured
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
        work = root / "docs/ai/work-items" / config["work_item"]
        context = work / "evidence"
        context.mkdir(parents=True, exist_ok=True)
        doc = context / "disposition.md"
        doc.write_text("original\n")
        config["read_only_context_paths"] = [str(doc.relative_to(root))]
        e.config["read_only_context_paths"] = config["read_only_context_paths"]
        state = e._prepare({"view": e.view()})
        job = e.store.job(state["view"]["active_jobs"][0])
        snapshot = Path(job["spec"]["read_artifact_refs"][0]["snapshot_path"])
        assert snapshot.read_text() == "original\n"

        doc.write_text("mutated after preparation\n")
        with pytest.raises(WorkflowError, match="changed after preparation"):
            e._materialize_job(job, work)
        assert snapshot.read_text() == "original\n"
    finally:
        e.close()
