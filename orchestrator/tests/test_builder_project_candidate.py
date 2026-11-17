import base64
import hashlib
import sys

import builder_project_candidate as candidate
import pytest
from core import WorkflowError
from engine import Engine
from pending_builder_artifact import recheck_pending_builder_artifact
from test_builder_artifact_contract import MODEL, TASK_ID, _bundle, _job, _response


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _file(path, base, content):
    return {
        "path": path,
        "base_sha256": _sha(base) if base is not None else None,
        "content_base64": base64.b64encode(content).decode("ascii"),
        "content_sha256": _sha(content),
    }


def _project(path):
    path.mkdir()
    (path / ".git").mkdir()
    (path / ".git/config").write_text("metadata must not enter candidate\n")
    (path / "src").mkdir()
    (path / "src/app.py").write_text("VALUE = 'base'\n")
    (path / "README.md").write_text("project context\n")
    return path


def test_project_bundle_is_staged_validated_and_rechecked(tmp_path):
    source = _project(tmp_path / "project")
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    baseline = candidate.capture_baseline(source, evidence_dir / "baseline.json")
    original = (source / "src/app.py").read_bytes()
    proposal = b"VALUE = 'candidate'\n"
    bundle = {"files": [_file("src/app.py", original, proposal)]}
    dest = tmp_path / "candidate"

    if not candidate._network_boundary_available():
        pytest.skip("bubblewrap network namespace unavailable")
    code = (
        "from pathlib import Path; "
        "assert Path('src/app.py').read_text() == \"VALUE = 'candidate'\\n\"; "
        "assert Path('README.md').read_text() == 'project context\\n'; "
        "assert not Path('.git').exists()"
    )
    evidence = candidate.prepare_and_validate(
        source_root=source,
        baseline_artifact=baseline["artifact"],
        trusted_baseline_sha256=baseline["manifest_sha256"],
        bundle=bundle,
        destination=dest,
        allowed_paths=["src/"],
        trusted_commands=[[sys.executable, "-c", code]],
    )
    assert evidence["validation_status"] == "complete"
    assert evidence["validation_passed"] is True
    assert (source / "src/app.py").read_bytes() == original
    assert not (dest / ".git").exists()
    rechecked = candidate.recheck_validation(
        source_root=source,
        baseline_artifact=baseline["artifact"],
        trusted_baseline_sha256=baseline["manifest_sha256"],
        candidate_root=dest,
        evidence=evidence,
    )
    assert rechecked["validation_passed"] is True


def test_linked_worktree_git_pointer_is_not_copied_into_candidate(tmp_path):
    import shutil

    source = _project(tmp_path / "project")
    shutil.rmtree(source / ".git")
    (source / ".git").write_text("gitdir: /private/shared/repository\n")
    baseline = candidate.capture_baseline(source, tmp_path / "baseline.json")
    if not candidate._network_boundary_available():
        pytest.skip("bubblewrap network namespace unavailable")
    result = candidate.prepare_and_validate(
        source_root=source,
        baseline_artifact=baseline["artifact"],
        trusted_baseline_sha256=baseline["manifest_sha256"],
        bundle={"files": [_file("src/new.py", None, b"x = 1\n")]},
        destination=tmp_path / "candidate",
        allowed_paths=["src/"],
        trusted_commands=[
            [sys.executable, "-c", "from pathlib import Path; assert not Path('.git').exists()"]
        ],
    )
    assert result["validation_passed"] is True
    assert not (tmp_path / "candidate/.git").exists()
    assert (source / ".git").is_file()


def test_project_baseline_digest_and_source_drift_fail_closed(tmp_path):
    source = _project(tmp_path / "project")
    baseline = candidate.capture_baseline(source, tmp_path / "baseline.json")
    args = dict(
        source_root=source,
        baseline_artifact=baseline["artifact"],
        trusted_baseline_sha256=baseline["manifest_sha256"],
        bundle={"files": [_file("src/new.py", None, b"x\n")]},
        destination=tmp_path / "candidate",
        allowed_paths=["src/"],
        trusted_commands=[[sys.executable, "-c", "pass"]],
    )
    with pytest.raises(WorkflowError, match="digest or binding"):
        candidate.prepare_and_validate(**{**args, "trusted_baseline_sha256": "0" * 64})
    (source / "README.md").write_text("changed after baseline")
    with pytest.raises(WorkflowError, match="source changed"):
        candidate.prepare_and_validate(**args)


@pytest.mark.parametrize("path", ["../escape", ".git/config", "src//bad"])
def test_project_bundle_cannot_escape_or_mutate_git_metadata(tmp_path, path):
    source = _project(tmp_path / "project")
    baseline = candidate.capture_baseline(source, tmp_path / "baseline.json")
    entry = _file(path, None, b"x")
    with pytest.raises(WorkflowError):
        candidate.prepare_and_validate(
            source_root=source,
            baseline_artifact=baseline["artifact"],
            trusted_baseline_sha256=baseline["manifest_sha256"],
            bundle={"files": [entry]},
            destination=tmp_path / "candidate",
            allowed_paths=["/"],
            trusted_commands=[[sys.executable, "-c", "pass"]],
        )


def test_candidate_mutation_invalidates_validation_evidence(tmp_path):
    source = _project(tmp_path / "project")
    baseline = candidate.capture_baseline(source, tmp_path / "baseline.json")
    if not candidate._network_boundary_available():
        pytest.skip("bubblewrap network namespace unavailable")
    result = candidate.prepare_and_validate(
        source_root=source,
        baseline_artifact=baseline["artifact"],
        trusted_baseline_sha256=baseline["manifest_sha256"],
        bundle={"files": [_file("src/new.py", None, b"x\n")]},
        destination=tmp_path / "candidate",
        allowed_paths=["src/"],
        trusted_commands=[[sys.executable, "-c", "pass"]],
    )
    (tmp_path / "candidate/src/new.py").write_text("tampered\n")
    with pytest.raises(WorkflowError, match="does not bind"):
        candidate.recheck_validation(
            source_root=source,
            baseline_artifact=baseline["artifact"],
            trusted_baseline_sha256=baseline["manifest_sha256"],
            candidate_root=tmp_path / "candidate",
            evidence=result,
        )


def test_t3_result_is_bound_to_source_and_validated_candidate(tmp_path):
    source = _project(tmp_path / "project")
    baseline = candidate.capture_baseline(source, tmp_path / "baseline.json")
    if not candidate._network_boundary_available():
        pytest.skip("bubblewrap network namespace unavailable")
    job = _job()
    old = (source / "src/app.py").read_bytes()
    bundle = _bundle(job, path="src/app.py", base=old, content=b"VALUE = 't3'\n")
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
    evidence = candidate.accept_t3_builder_return(
        assistant_text=response,
        job=job,
        task_id=TASK_ID,
        supervisor_receipt=receipt,
        source_root=source,
        baseline_artifact=baseline["artifact"],
        trusted_baseline_sha256=baseline["manifest_sha256"],
        destination=tmp_path / "t3-candidate",
        allowed_paths=["src/"],
        trusted_commands=[
            [sys.executable, "-c", "from pathlib import Path; assert 't3' in Path('src/app.py').read_text()"]
        ],
    )
    binding = evidence["builder_binding"]
    assert binding["task_id"] == TASK_ID
    assert binding["job_id"] == job["job_id"]
    assert binding["model_evidence"] == "executed"
    assert binding["model_evidence_source"] == "managed_supervisor_receipt"
    assert evidence["validation_passed"] is True
    candidate.recheck_t3_builder_return(
        source_root=source,
        baseline_artifact=baseline["artifact"],
        trusted_baseline_sha256=baseline["manifest_sha256"],
        candidate_root=tmp_path / "t3-candidate",
        evidence=evidence,
        expected_binding=binding,
    )
    with pytest.raises(WorkflowError, match="provenance binding"):
        candidate.recheck_t3_builder_return(
            source_root=source,
            baseline_artifact=baseline["artifact"],
            trusted_baseline_sha256=baseline["manifest_sha256"],
            candidate_root=tmp_path / "t3-candidate",
            evidence=evidence,
            expected_binding={**binding, "job_id": "job-other"},
        )


def test_model_file_text_is_bound_locally_and_validated(tmp_path):
    """A model need not fabricate hashes; the received text is still scoped."""
    from builder_source_packet import build_builder_source_packet

    source = _project(tmp_path / "project")
    baseline = candidate.capture_baseline(source, tmp_path / "baseline.json")
    if not candidate._network_boundary_available():
        pytest.skip("bubblewrap network namespace unavailable")
    job = _job()
    job["spec"]["builder_source_packet"] = build_builder_source_packet(source, ["src/"])
    # Preserve the existing Engine envelope and return plain source content.
    response = _response(job, {"files": [{"path": "src/app.py", "content": "VALUE = 't3'\n"}]})
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
    result = candidate.accept_t3_builder_return(
        assistant_text=response,
        job=job,
        task_id=TASK_ID,
        supervisor_receipt=receipt,
        source_root=source,
        baseline_artifact=baseline["artifact"],
        trusted_baseline_sha256=baseline["manifest_sha256"],
        destination=tmp_path / "candidate",
        allowed_paths=["src/"],
        trusted_commands=[
            [
                sys.executable,
                "-c",
                "from pathlib import Path; assert Path('src/app.py').read_text() == \"VALUE = 't3'\\n\"",
            ]
        ],
    )
    assert result["validation_passed"] is True
    assert (source / "src/app.py").read_text() == "VALUE = 'base'\n"
    assert (tmp_path / "candidate/src/app.py").read_text() == "VALUE = 't3'\n"


@pytest.mark.parametrize(
    "evidence,executed",
    [
        ("configured_only", None),
        (None, None),
        ("executed", "other/model"),
    ],
)
def test_t3_intake_refuses_unverified_execution_model(tmp_path, evidence, executed):
    source = _project(tmp_path / "project")
    baseline = candidate.capture_baseline(source, tmp_path / "baseline.json")
    job = _job()
    response = _response(job, _bundle(job))
    receipt = {
        "state": "completed",
        "job_id": job["job_id"],
        "task_id": TASK_ID,
        "model_evidence": evidence,
        "executed_model": executed if executed is not None else (MODEL if evidence == "executed" else None),
        "configured_model": MODEL,
        "validated_utc": "2026-11-16T00:00:01Z",
        "summary": response,
    }
    with pytest.raises(WorkflowError, match="T3 model evidence"):
        candidate.accept_t3_builder_return(
            assistant_text=response,
            job=job,
            task_id=TASK_ID,
            supervisor_receipt=receipt,
            source_root=source,
            baseline_artifact=baseline["artifact"],
            trusted_baseline_sha256=baseline["manifest_sha256"],
            destination=tmp_path / "candidate",
            allowed_paths=["src/"],
            trusted_commands=[[sys.executable, "-c", "pass"]],
        )


def test_configured_only_is_preserved_when_explicit_policy_allows_staging(tmp_path):
    source = _project(tmp_path / "project")
    baseline = candidate.capture_baseline(source, tmp_path / "baseline.json")
    if not candidate._network_boundary_available():
        pytest.skip("bubblewrap network namespace unavailable")
    job = _job()
    response = _response(job, _bundle(job))
    receipt = {
        "state": "completed",
        "job_id": job["job_id"],
        "task_id": TASK_ID,
        "model_evidence": "configured_only",
        "executed_model": None,
        "configured_model": MODEL,
        "validated_utc": "2026-11-16T00:00:01Z",
        "summary": response,
    }
    result = candidate.accept_t3_builder_return(
        assistant_text=response,
        job=job,
        task_id=TASK_ID,
        supervisor_receipt=receipt,
        source_root=source,
        baseline_artifact=baseline["artifact"],
        trusted_baseline_sha256=baseline["manifest_sha256"],
        destination=tmp_path / "configured-only-candidate",
        allowed_paths=["src/"],
        trusted_commands=[[sys.executable, "-c", "pass"]],
        allow_configured_only=True,
    )
    assert result["validation_passed"] is True
    assert result["builder_binding"]["model_evidence"] == "configured_only"
    assert result["builder_binding"]["executed_model"] is None


def test_pending_artifact_is_append_only_review_record_and_tampering_is_detected(tmp_path):
    source = _project(tmp_path / "project")
    if not candidate._network_boundary_available():
        pytest.skip("bubblewrap network namespace unavailable")
    job = _job()
    old = (source / "src/app.py").read_bytes()
    bundle = _bundle(job, path="src/app.py", base=old, content=b"VALUE = 'pending'\n")
    response = _response(job, bundle)
    receipt = {
        "state": "completed",
        "job_id": job["job_id"],
        "task_id": TASK_ID,
        "model_evidence": "configured_only",
        "executed_model": None,
        "configured_model": MODEL,
        "validated_utc": "2026-11-16T00:00:01Z",
        "summary": response,
    }
    engine = Engine(source, runtime=tmp_path / "engine-runtime")
    engine.config = {
        "scope": {"allowed_paths": ["src/"], "validation_commands": [[sys.executable, "-c", "pass"]]},
        "builder_validation_timeout": 60,
    }
    from t3_supervisor_client import ManagedSupervisorLauncher

    class ReceiptTestLauncher(ManagedSupervisorLauncher):
        def __init__(self, value):
            self.value = value

        def receipt_for(self, _job):
            return self.value

    engine.launcher = ReceiptTestLauncher(receipt)
    engine._builder_candidate_parent = lambda: tmp_path / "builder-candidates"

    def test_artifact_dir():
        path = tmp_path / "builder-artifacts"
        path.mkdir(mode=0o700, exist_ok=True)
        return path

    engine._builder_artifact_directory = test_artifact_dir
    baseline = engine._capture_builder_baseline(job["job_id"])
    job["spec"]["builder_baseline"] = baseline
    result = engine._intake_managed_builder_return(job, {"supervisor_receipt": receipt}, TASK_ID)
    payload = engine.store.pending_builder_artifact(job["job_id"])
    assert payload["status"] == "PENDING_OWNER_REVIEW"
    assert payload["candidate_root"] == result["workspace"]
    assert not payload.get("candidate")
    assert payload["model_evidence"] == "configured_only"
    assert payload["executed_model"] is None
    assert payload["configured_model"] == MODEL
    assert engine.store.events() == []
    reviewed = engine.review_pending_builder_artifact(
        job["job_id"],
        TASK_ID,
        job["spec"]["envelope"]["candidate_id"],
        job["spec"]["envelope"]["plan_revision_hash"],
    )
    assert reviewed["status"] == "PENDING_OWNER_REVIEW"
    evidence_path = payload["evidence_path"]
    import os

    os.chmod(evidence_path, 0o600)
    with open(evidence_path, "ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(WorkflowError, match="evidence digest"):
        recheck_pending_builder_artifact(
            store=engine.store,
            job_id=job["job_id"],
            expected_task_id=TASK_ID,
            expected_candidate_id=job["spec"]["envelope"]["candidate_id"],
            expected_plan_revision_hash=job["spec"]["envelope"]["plan_revision_hash"],
        )
    engine.close()
