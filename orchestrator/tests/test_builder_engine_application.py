import base64
import hashlib
import subprocess
import sys

import pytest
from core import WorkflowError, canonical
from engine import Engine


def _git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _task_checkout(root):
    primary = root.with_name(root.name + "-primary")
    primary.mkdir(mode=0o700)
    _git(primary, "init", "-q")
    _git(primary, "config", "user.email", "test@example.invalid")
    _git(primary, "config", "user.name", "Test")
    (primary / "src").mkdir()
    (primary / "src/app.py").write_text("VALUE = 'base'\n")
    work = primary / "docs/ai/work-items/test-builder"
    work.mkdir(parents=True)
    _git(primary, "add", "src/app.py", "docs/ai/work-items/test-builder")
    _git(primary, "commit", "-qm", "base")
    _git(primary, "worktree", "add", "-qb", "engine-task", str(root), "HEAD")
    root.chmod(0o700)
    return _git(root, "rev-parse", "HEAD"), _git(root, "branch", "--show-current")


def _empty_engine(root, tmp_path):
    engine = Engine.__new__(Engine)
    engine.root = root
    engine.runtime = tmp_path / "runtime"
    engine.runtime.mkdir()
    engine.config = {
        "base_commit": _git(root, "rev-parse", "HEAD"),
        "branch": _git(root, "branch", "--show-current"),
        "scope": {"allowed_paths": ["src/"], "validation_commands": [["/usr/bin/python3", "-c", "pass"]]},
        "generated": [],
        "work_item": "test-builder",
        "builder_validation_timeout": 30,
    }
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir(mode=0o700)
    engine._builder_artifact_directory = lambda: artifact_dir
    return engine


def test_dirty_engine_task_checkout_is_preserved_and_rejected_before_pending_lookup(tmp_path):
    root = tmp_path / "task-worktree"
    _task_checkout(root)
    engine = _empty_engine(root, tmp_path)
    original = "VALUE = 'owner-change'\n"
    (root / "src/app.py").write_text(original)
    engine.review_pending_builder_artifact = lambda *_args: (_ for _ in ()).throw(
        AssertionError("dirty checkout must be rejected before reading pending evidence")
    )

    with pytest.raises(WorkflowError, match="must be clean"):
        engine.apply_pending_builder_candidate("job-1", "task-1", "c" * 64, "p" * 64)

    assert (root / "src/app.py").read_text() == original
    assert not list((tmp_path / "artifacts").rglob("application-plan.json"))


def test_primary_checkout_is_rejected_without_modifying_live_files(tmp_path):
    root = tmp_path / "live-checkout"
    root.mkdir(mode=0o700)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    (root / "src").mkdir()
    original = b"VALUE = 'live'\n"
    (root / "src/app.py").write_bytes(original)
    _git(root, "add", "src/app.py")
    _git(root, "commit", "-qm", "live")
    root.chmod(0o700)
    engine = _empty_engine(root, tmp_path)

    with pytest.raises(WorkflowError, match="linked Git task worktree"):
        engine.apply_pending_builder_candidate("job-1", "task-1", "c" * 64, "p" * 64)

    assert (root / "src/app.py").read_bytes() == original
    assert _git(root, "status", "--porcelain") == ""


def test_engine_generated_changes_are_ignored_but_staged_changes_are_rejected(tmp_path):
    root = tmp_path / "task-worktree"
    _task_checkout(root)
    engine = _empty_engine(root, tmp_path)
    generated = "docs/ai/work-items/test-builder/runs/"
    engine.config["generated"] = [generated]
    generated_file = root / generated / "job/output.json"
    generated_file.parent.mkdir(parents=True)
    generated_file.write_text("engine-owned\n")

    _root, _head, _branch, user_changes = engine._builder_application_checkout_state()
    assert user_changes == []

    (root / "src/app.py").write_text("VALUE = 'staged-change'\n")
    _git(root, "add", "src/app.py")
    with pytest.raises(WorkflowError, match="staged changes"):
        engine._builder_application_checkout_state()


def test_interrupted_detached_intake_discards_unverified_workspace_and_rechecks_receipt(
    tmp_path, monkeypatch
):
    from t3_supervisor_client import ManagedSupervisorLauncher

    root = tmp_path / "task-worktree"
    _task_checkout(root)
    engine = _empty_engine(root, tmp_path)
    private_artifacts = tmp_path / "private-artifacts"
    private_artifacts.mkdir(mode=0o700)
    candidate_parent = tmp_path / "detached-candidates"
    candidate_parent.mkdir(mode=0o700)
    engine._builder_artifact_directory = lambda: private_artifacts
    engine._builder_candidate_parent = lambda: candidate_parent
    receipt = {"job_id": "job-crash", "task_id": "t3-1", "summary": "receipt-body"}

    class Launcher(ManagedSupervisorLauncher):
        def receipt_for(self, _job):
            return self.receipt

    launcher = object.__new__(Launcher)
    launcher.receipt = receipt
    engine.launcher = launcher
    job = {
        "job_id": "job-crash",
        "spec": {
            "envelope": {"candidate_id": "c" * 64, "plan_revision_hash": "p" * 64},
            "builder_baseline": {
                "artifact": str(private_artifacts / "baseline.json"),
                "manifest_sha256": "b" * 64,
            },
        },
    }
    observation = {"supervisor_receipt": receipt}
    attempts = []

    def interrupted_accept(**kwargs):
        destination = kwargs["destination"]
        assert not destination.exists(), "unverified prior workspace was trusted on replay"
        destination.mkdir(mode=0o700)
        marker = "attempt-" + str(len(attempts) + 1)
        (destination / "unverified-marker").write_text(marker)
        attempts.append((destination, marker))
        raise WorkflowError("simulated interruption after workspace creation")

    monkeypatch.setattr("builder_project_candidate.accept_t3_builder_return", interrupted_accept)
    for _ in range(2):
        with pytest.raises(WorkflowError, match="simulated interruption"):
            engine._intake_managed_builder_return(job, observation, "t3-1")
    assert len(attempts) == 2
    assert attempts[0][0] == attempts[1][0]
    assert (attempts[1][0] / "unverified-marker").read_text() == "attempt-2"

    launcher.receipt = {**receipt, "summary": "changed receipt"}
    observation["supervisor_receipt"] = launcher.receipt
    with pytest.raises(WorkflowError, match="durable receipt binding"):
        engine._intake_managed_builder_return(job, observation, "t3-1")
    assert (attempts[-1][0] / "unverified-marker").read_text() == "attempt-2"

    launcher.receipt = receipt
    observation["supervisor_receipt"] = receipt
    import shutil

    shutil.rmtree(attempts[-1][0])
    outside = tmp_path / "outside-residue"
    outside.mkdir()
    (outside / "keep").write_text("untouched")
    attempts[-1][0].symlink_to(outside, target_is_directory=True)
    with pytest.raises(WorkflowError, match="residue is unsafe"):
        engine._intake_managed_builder_return(job, observation, "t3-1")
    assert (outside / "keep").read_text() == "untouched"


def test_blocked_builder_retains_previous_candidate_without_validation():
    engine = Engine.__new__(Engine)
    retained = {"kind": "code", "candidate_id": "prior"}
    engine._recheck_candidate = lambda candidate: candidate is retained
    candidate, validation = engine._retain_blocked_builder_candidate({"candidate": retained})
    assert candidate is retained
    assert validation == {"complete": False, "passed": False, "mode": "builder-blocked"}


def test_pending_native_application_uses_real_offline_validator(tmp_path):
    from builder_project_candidate import (
        _network_boundary_available,
        accept_t3_builder_return,
        capture_baseline,
    )
    from pending_builder_artifact import record_pending_builder_artifact
    from test_builder_artifact_contract import MODEL, TASK_ID, _bundle, _job, _response

    if not _network_boundary_available():
        pytest.skip("native offline validation requires working bubblewrap network isolation")
    root = tmp_path / "task-worktree"
    base, branch = _task_checkout(root)
    engine = _empty_engine(root, tmp_path)
    generated_path = "docs/ai/work-items/test-builder/runs/"
    engine.config["generated"] = [generated_path]
    generated_file = root / generated_path / "preexisting-engine-state.json"
    generated_file.parent.mkdir(parents=True)
    generated_file.write_text("generated before baseline\n")
    artifacts = tmp_path / "artifacts"
    candidate_parent = tmp_path / "detached-candidates"
    candidate_parent.mkdir(mode=0o700)
    engine._builder_candidate_parent = lambda: candidate_parent
    baseline_dir = artifacts / "baselines"
    baseline_dir.mkdir(mode=0o700)
    job = _job()
    baseline = capture_baseline(root, baseline_dir / "baseline.json", generated=engine.config["generated"])
    generated_file.write_text("generated after baseline\n")
    old = (root / "src/app.py").read_bytes()
    proposed = b"VALUE = 'builder'\n"
    bundle = _bundle(job, path="src/app.py", base=old, content=proposed)
    response = _response(job, bundle)
    receipt = {
        "state": "completed",
        "job_id": job["job_id"],
        "task_id": TASK_ID,
        "model_evidence": "executed",
        "executed_model": MODEL,
        "configured_model": MODEL,
        "validated_utc": "2026-11-16T00:00:01Z",
        "summary": response,
    }
    result = accept_t3_builder_return(
        assistant_text=response,
        job=job,
        task_id=TASK_ID,
        supervisor_receipt=receipt,
        source_root=root,
        baseline_artifact=baseline["artifact"],
        trusted_baseline_sha256=baseline["manifest_sha256"],
        destination=candidate_parent / "validated-detached",
        allowed_paths=["src/"],
        trusted_commands=[
            [
                "/usr/bin/python3",
                "-c",
                "from pathlib import Path; assert 'builder' in Path('src/app.py').read_text()",
            ]
        ],
    )
    result["builder_binding"]["supervisor_receipt_sha256"] = hashlib.sha256(canonical(receipt)).hexdigest()
    result["builder_binding_sha256"] = hashlib.sha256(canonical(result["builder_binding"])).hexdigest()

    class MemoryStore:
        def put_pending_builder_artifact(self, job_id, payload):
            self.payload = payload

        def pending_builder_artifact(self, job_id):
            return self.payload if getattr(self, "payload", {}).get("job_id") == job_id else None

    engine.store = MemoryStore()
    evidence_dir = artifacts / "evidence"
    evidence_dir.mkdir(mode=0o700)
    record_pending_builder_artifact(
        store=engine.store,
        result=result,
        source_root=root,
        baseline_artifact=baseline["artifact"],
        evidence_directory=evidence_dir,
    )

    # Exercise the real `_accept_inner` managed branch. The launcher is a
    # ManagedSupervisorLauncher subclass, which also inherits SupervisorLauncher;
    # a successful event proves the branch does not fall through to the legacy
    # synthetic fixture gate. The application call still runs the native
    # validator above, without substituting a PASS result.
    import engine as engine_module
    import stage4
    from t3_supervisor_client import ManagedSupervisorLauncher

    class ManagedLauncher(ManagedSupervisorLauncher):
        def parse(self, _job, _raw):
            body = dict(_job["spec"]["envelope"])
            return TASK_ID, body, {"explanation": "validated builder result", "plan_text": ""}, []

        def receipt_for(self, _job):
            return receipt

    launcher = object.__new__(ManagedLauncher)
    launcher.builder_enabled = True
    engine.launcher = launcher
    engine.store.events = lambda: []
    engine._validate_engineering_job = lambda *_args, **_kwargs: None
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(engine_module, "validate_document", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stage4, "sanitize_public_text", lambda value, **_kwargs: value)
    (engine.root / "docs/ai/work-items/test-builder/runs").mkdir(parents=True, exist_ok=True)
    runtime = tmp_path / "runtime/job-1"
    runtime.mkdir(parents=True)
    (runtime / "stdout.jsonl").write_text("managed result\n")
    accepted_job = dict(job)
    accepted_job.update(job_id=job["job_id"], role="builder", runtime=str(runtime))
    accepted_job["spec"] = dict(job["spec"])
    accepted_job["spec"]["envelope"] = dict(job["spec"]["envelope"])
    accepted_job["spec"]["envelope"].update(
        work_item="test-builder", stage="implementation", prompt_version="c" * 64
    )
    accepted_job["spec"].update(tool="opencode", model=MODEL)
    engine.config["scope"]["requirements"] = []
    view = {
        "candidate": {"kind": "code", "candidate_id": "prior"},
        "findings": [],
        "backlog": [],
        "work_item": "test-builder",
    }
    observation = {
        "exit_code": 0,
        "timeout": False,
        "started_utc": "2026-11-16T00:00:00Z",
        "finished_utc": "2026-11-16T00:00:01Z",
        "supervisor_receipt": receipt,
        "model_evidence": "executed",
    }

    event = engine._accept_inner(accepted_job, observation, view)
    # Replay is safe after persistence: the same receipt-bound pending record
    # and immutable plan are reused, with no second builder intake.
    temp_leaf = (
        ".engine-builder-" + hashlib.sha256((job["job_id"] + "\0src/app.py").encode()).hexdigest()[:24]
    )
    interrupted_temp = root / "src" / temp_leaf
    interrupted_temp.write_bytes(b"partial pre-replace write")
    event_retry = engine._accept_inner(accepted_job, observation, view)
    monkeypatch.undo()

    assert event["validation"]["complete"] is True
    assert event["validation"]["passed"] is True
    assert event["candidate"]["manifest"]["base_commit"] == base
    assert event["candidate"]["manifest"]["branch"] == branch
    assert event["candidate"]["candidate_id"] == event_retry["candidate"]["candidate_id"]
    assert event_retry["validation"]["passed"] is True
    assert not interrupted_temp.exists()
    validation_attempts = list(
        (engine._builder_application_directory(job["job_id"]) / "native-validation").iterdir()
    )
    assert len(validation_attempts) == 2
    assert all((attempt / "tested-candidate" / "tree.tar").is_file() for attempt in validation_attempts)
    assert event["validation"].get("mode") != "SYNTHETIC"
    assert (root / "src/app.py").read_bytes() == proposed
    engine._recheck_candidate(event["candidate"])
