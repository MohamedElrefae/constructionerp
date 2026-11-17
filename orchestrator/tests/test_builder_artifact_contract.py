import base64
import hashlib
import json
import sys
from pathlib import Path

import pytest

import builder_candidate_prototype
from core import WorkflowError
from builder_artifact_contract import (
    BUNDLE_SCHEMA,
    BuilderArtifactError,
    decode_builder_artifact_return,
    intake_and_validate_builder_return,
)
from t3_result import T3ResultError, decode_t3_result


MODEL = "opencode-go/deepseek-v4.1-flash"
TASK_ID = "thr-builder-123"
JOB_ID = "job-123abc"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _job(role="builder"):
    body = {
        "schema_version": 1,
        "job_id": JOB_ID,
        "work_item": "prototype-work-item",
        "stage": "1",
        "role": role,
        "tool": "opencode",
        "model": MODEL,
        "session_id": "model-session",
        "dispatch_mode": "manual",
        "candidate_kind": "code",
        "candidate_id": "a" * 64,
        "plan_revision_hash": "b" * 64,
        "prompt_version": "c" * 64,
        "status": "COMPLETE",
        "verdict": "PASS",
        "failure_class": None,
        "findings": [],
        "evidence_paths": [{"artifact_id": "builder-evidence", "sha256": "d" * 64,
                            "visibility": "public"}],
        "started_utc": "2026-11-16T00:00:00Z",
        "finished_utc": "2026-11-16T00:00:01Z",
    }
    return {"job_id": JOB_ID, "role": role, "spec": {
        "model": MODEL, "tool": "opencode", "envelope": body,
    }}


def _bundle(job, *, path="src/example.py", base=None, content=b"value = 2\n"):
    item = {
        "path": path,
        "base_sha256": _sha(base) if base is not None else None,
        "content_base64": base64.b64encode(content).decode("ascii"),
        "content_sha256": _sha(content),
    }
    files = [item]
    body = job["spec"]["envelope"]
    return {
        "schema": BUNDLE_SCHEMA,
        "job_id": body["job_id"],
        "candidate_id": body["candidate_id"],
        "plan_revision_hash": body["plan_revision_hash"],
        "files": files,
        "bundle_sha256": _sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()),
    }


def _response(job, bundle=None):
    body = job["spec"]["envelope"]
    wire = {"result_json": json.dumps(body), "explanation": "Candidate prepared.",
            "plan_text": ""}
    if bundle is not None:
        wire["builder_bundle_json"] = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    return f"ENGINE-T3-RESULT {JOB_ID}\n{json.dumps(wire, separators=(',', ':'))}"


def test_decodes_bounded_bound_builder_bundle_from_text_wire():
    job = _job()
    bundle = _bundle(job)
    result = decode_builder_artifact_return(
        assistant_text=_response(job, bundle), job=job, task_id=TASK_ID,
        executed_model=MODEL,
    )
    assert result["task_id"] == TASK_ID
    assert result["job_id"] == JOB_ID
    assert result["candidate_id"] == job["spec"]["envelope"]["candidate_id"]
    assert result["files"] == bundle["files"]


def test_accepts_12kb_files_and_24kb_total():
    job = _job()
    files = []
    for index, content in enumerate((b"a" * 12_000, b"b" * 12_000)):
        files.append({"path": f"src/file{index}.py", "base_sha256": None,
                      "content_base64": base64.b64encode(content).decode("ascii"),
                      "content_sha256": _sha(content)})
    bundle = {
        "schema": BUNDLE_SCHEMA, "job_id": job["job_id"],
        "candidate_id": job["spec"]["envelope"]["candidate_id"],
        "plan_revision_hash": job["spec"]["envelope"]["plan_revision_hash"],
        "files": files,
        "bundle_sha256": _sha(json.dumps(files, sort_keys=True,
                                          separators=(",", ":")).encode()),
    }
    result = decode_builder_artifact_return(
        assistant_text=_response(job, bundle), job=job, task_id=TASK_ID,
        executed_model=MODEL,
    )
    assert sum(len(base64.b64decode(item["content_base64"]))
               for item in result["files"]) == 24_000


def test_builder_wire_extension_is_role_scoped_and_still_schema_validates_body():
    builder = _job()
    bundle = _bundle(builder)
    decoded = decode_t3_result(
        assistant_text=_response(builder, bundle), job=builder, task_id=TASK_ID,
        executed_model=MODEL,
    )
    assert decoded[2]["builder_bundle_json"]

    reviewer = _job("reviewer")
    with pytest.raises(T3ResultError, match="complete result wire"):
        decode_t3_result(
            assistant_text=_response(reviewer, _bundle(reviewer)), job=reviewer,
            task_id=TASK_ID, executed_model=MODEL,
        )


@pytest.mark.parametrize("change", ["job_id", "candidate_id", "plan_revision_hash", "bundle_sha256"])
def test_rejects_bundle_binding_and_digest_mismatch(change):
    job = _job()
    bundle = _bundle(job)
    bundle[change] = "0" * 64 if change != "job_id" else "job-other"
    with pytest.raises(BuilderArtifactError):
        decode_builder_artifact_return(
            assistant_text=_response(job, bundle), job=job, task_id=TASK_ID,
            executed_model=MODEL,
        )


def test_rejects_missing_or_malformed_or_oversized_bundle():
    job = _job()
    with pytest.raises(BuilderArtifactError, match="missing"):
        decode_builder_artifact_return(
            assistant_text=_response(job), job=job, task_id=TASK_ID,
            executed_model=MODEL,
        )
    bundle = _bundle(job)
    bundle["files"][0]["path"] = "../escape"
    bundle["bundle_sha256"] = _sha(json.dumps(bundle["files"], sort_keys=True,
                                                separators=(",", ":")).encode())
    # Reject traversal at decode time, before any staging path is created.
    with pytest.raises(BuilderArtifactError, match="path"):
        decode_builder_artifact_return(
            assistant_text=_response(job, bundle), job=job, task_id=TASK_ID,
            executed_model=MODEL,
        )

    too_large = _bundle(job, content=b"x" * 12_001)
    with pytest.raises(BuilderArtifactError, match="size bound"):
        decode_builder_artifact_return(
            assistant_text=_response(job, too_large), job=job, task_id=TASK_ID,
            executed_model=MODEL,
        )


def test_intake_stages_only_synthetic_candidate_and_keeps_validation_refused(tmp_path, monkeypatch):
    source = tmp_path / "synthetic-source"
    source.mkdir()
    (source / builder_candidate_prototype.SYNTHETIC_MARKER).write_bytes(
        builder_candidate_prototype.SYNTHETIC_MARKER_VALUE
    )
    source_file = source / "src/example.py"
    source_file.parent.mkdir()
    source_file.write_bytes(b"value = 1\n")
    job = _job()
    bundle = _bundle(job, base=b"value = 1\n", content=b"value = 2\n")
    monkeypatch.setattr(builder_candidate_prototype, "_network_boundary_available", lambda: False)

    result = intake_and_validate_builder_return(
        assistant_text=_response(job, bundle), job=job, task_id=TASK_ID,
        executed_model=MODEL, base_root=source,
        destination=tmp_path / "candidate", allowed_paths=["src/"],
        trusted_validation_commands=[[sys.executable, "-c", "raise SystemExit(0)"]],
    )

    assert (tmp_path / "candidate/src/example.py").read_bytes() == b"value = 2\n"
    assert source_file.read_bytes() == b"value = 1\n"
    assert result["validation_status"] == "refused"
    assert result["validation_complete"] is False
    assert result["validation_passed"] is False


def test_test_owned_t3_builder_bundle_becomes_recheckable_candidate(tmp_path):
    import shutil
    from builder_artifact_contract import accept_synthetic_t3_builder_candidate
    from builder_candidate_binding import recheck_engine_candidate

    if not shutil.which("bwrap") or not builder_candidate_prototype._network_boundary_available():
        pytest.skip("kernel denies bubblewrap network namespace creation")

    from t3_supervisor_client import SupervisorLauncher

    class TestOwnedLauncher(SupervisorLauncher):
        allow_builder_for_tests = True
        accept_builder_artifacts_for_tests = True

        def __init__(self):
            pass

    source = tmp_path / "synthetic-source"
    source.mkdir()
    (source / builder_candidate_prototype.SYNTHETIC_MARKER).write_bytes(
        builder_candidate_prototype.SYNTHETIC_MARKER_VALUE
    )
    source_file = source / "src/example.py"
    source_file.parent.mkdir()
    source_file.write_bytes(b"value = 1\n")
    job_dir = tmp_path / "job-runtime"
    job_dir.mkdir()
    job = _job()
    response = _response(job, _bundle(job, base=b"value = 1\n", content=b"value = 2\n"))

    candidate, validation = accept_synthetic_t3_builder_candidate(
        launcher=TestOwnedLauncher(), assistant_text=response, job=job,
        task_id=TASK_ID, executed_model=MODEL, base_root=source,
        destination=job_dir, allowed_paths=["src/"],
        trusted_validation_commands=[[
            "/usr/bin/python3", "-c",
            "from pathlib import Path; assert Path('src/example.py').read_text() == 'value = 2\\n'",
        ]],
    )

    assert validation["validation_status"] == "complete"
    assert validation["validation_passed"] is True
    assert (source / "src/example.py").read_bytes() == b"value = 1\n"
    assert (Path(candidate["artifact_binding"]["candidate_root"]) / "src/example.py").read_bytes() == b"value = 2\n"
    assert recheck_engine_candidate(candidate, source) is candidate


def test_synthetic_builder_candidate_requires_explicit_test_owned_launcher(tmp_path):
    from builder_artifact_contract import accept_synthetic_t3_builder_candidate

    from t3_supervisor_client import SupervisorLauncher

    class ProductionLikeLauncher(SupervisorLauncher):
        allow_builder_for_tests = True
        accept_builder_artifacts_for_tests = False

        def __init__(self):
            pass

    source = tmp_path / "source"
    source.mkdir()
    destination = tmp_path / "job"
    destination.mkdir()
    with pytest.raises(WorkflowError, match="test supervisor fixture"):
        accept_synthetic_t3_builder_candidate(
            launcher=ProductionLikeLauncher(), assistant_text="", job=_job(),
            task_id=TASK_ID, executed_model=MODEL, base_root=source,
            destination=destination, allowed_paths=["src/"],
            trusted_validation_commands=[["/usr/bin/python3", "-c", "pass"]],
        )


def test_t3_dispatch_wire_parser_preserves_builder_extension_only_when_allowed():
    from t3_dispatch import _extract_wire
    from core import WorkflowError

    raw = json.dumps({
        "result_json": "{}", "explanation": "", "plan_text": "",
        "builder_bundle_json": "{}",
    })
    with pytest.raises(WorkflowError, match="invalid wire"):
        _extract_wire(raw)
    assert _extract_wire(raw, allow_builder_bundle=True)["builder_bundle_json"] == "{}"
