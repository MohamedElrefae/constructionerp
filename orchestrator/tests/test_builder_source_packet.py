import hashlib
import json

import pytest

from builder_source_packet import (
    SOURCE_PACKET_SCHEMA,
    build_bound_builder_bundle,
    build_builder_source_packet,
    builder_output_instructions,
    normalize_builder_artifact_wire,
)
from core import WorkflowError


def test_source_changed_by_transport_redaction_is_refused(tmp_path):
    from builder_source_packet import build_builder_source_packet

    root = tmp_path / "project"
    root.mkdir()
    (root / "app.py").write_text('CACHE_DIR = "/home/user/private/cache"\n')
    with pytest.raises(WorkflowError, match="altered by transport redaction"):
        build_builder_source_packet(root, ["app.py"])


def _job():
    body = {
        "job_id": "job-source-123", "candidate_id": "a" * 64,
        "plan_revision_hash": "b" * 64,
    }
    return {"job_id": body["job_id"], "role": "builder", "spec": {"envelope": body}}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def test_source_packet_contains_only_allowed_public_regular_text(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src/app.py").write_text("value = 1\n")
    (root / ".env").write_text("TOKEN=private\n")
    (root / "src/token.txt").write_text("private\n")
    packet = build_builder_source_packet(root, ["src/"])

    assert packet == {
        "schema": SOURCE_PACKET_SCHEMA,
        "files": [{"path": "src/app.py", "base_sha256": _sha(b"value = 1\n"),
                   "content": "value = 1\n"}],
    }


def test_explicit_new_file_has_no_base_and_is_bound_for_safe_staging(tmp_path):
    from builder_intake import stage_bundle

    root = tmp_path / "source"
    root.mkdir()
    (root / "src").mkdir()
    packet = build_builder_source_packet(root, ["src/new.py"])
    assert packet["files"] == [{"path": "src/new.py", "content": None, "base_sha256": None}]
    bundle = json.loads(build_bound_builder_bundle(
        json.dumps({"files": [{"path": "src/new.py", "content": "answer = 42\n"}]}),
        _job(), packet,
    ))
    assert bundle["files"][0]["base_sha256"] is None
    stage_bundle(root, {"files": bundle["files"]}, tmp_path / "staged", ["src/new.py"])
    assert (tmp_path / "staged/src/new.py").read_text() == "answer = 42\n"
    assert not (root / "src/new.py").exists()


def test_model_return_accepts_larger_practical_source_file(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "app.py").write_text("base\n")
    packet = build_builder_source_packet(root, ["app.py"])
    bundle = json.loads(build_bound_builder_bundle(
        json.dumps({"files": [{"path": "app.py", "content": "x" * 12_000}]}),
        _job(), packet,
    ))
    assert bundle["files"][0]["content_sha256"] == _sha(b"x" * 12_000)


def test_source_packet_refuses_symlink_components_and_control_or_credential_paths(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "app.py").write_text("outside secret\n")
    (root / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(WorkflowError, match="Symlink"):
        build_builder_source_packet(root, ["linked/"])
    for name in (".git/HEAD", "orchestrator/var/checkpoints.db", "src/client_secret.py"):
        with pytest.raises(WorkflowError, match="excluded"):
            build_builder_source_packet(root, [name])


def test_model_return_is_locally_converted_and_outer_wire_stays_compatible(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src/app.py").write_text("value = 1\n")
    packet = build_builder_source_packet(root, ["src/"])
    job = _job()
    files_json = json.dumps({"files": [{"path": "src/app.py", "content": "value = 2\n"}]})
    outer = {
        "result_json": json.dumps(job["spec"]["envelope"]),
        "explanation": "Updated the requested value.",
        "plan_text": "",
        "builder_bundle_json": files_json,
    }
    assistant_text = "ENGINE-T3-RESULT " + job["job_id"] + "\n" + json.dumps(outer)

    normalized = normalize_builder_artifact_wire(assistant_text, job, packet)
    wire = json.loads(normalized.splitlines()[1])
    bundle = json.loads(wire["builder_bundle_json"])
    assert set(wire) == {"result_json", "explanation", "plan_text", "builder_bundle_json"}
    assert bundle["schema"] == "engine-builder-bundle/v1"
    assert bundle["job_id"] == job["job_id"]
    assert bundle["files"][0]["base_sha256"] == _sha(b"value = 1\n")
    assert bundle["files"][0]["content_sha256"] == _sha(b"value = 2\n")
    assert "builder_bundle_json" in builder_output_instructions(job)


@pytest.mark.parametrize("files", [
    [{"path": "src/not-supplied.py", "content": "x"}],
    [{"path": "src/app.py", "content": "x"}, {"path": "src/app.py", "content": "y"}],
    [{"path": "../escape", "content": "x"}],
])
def test_model_return_rejects_unbound_duplicate_and_traversal_paths(tmp_path, files):
    root = tmp_path / "source"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src/app.py").write_text("base\n")
    packet = build_builder_source_packet(root, ["src/"])
    with pytest.raises(WorkflowError):
        build_bound_builder_bundle(json.dumps({"files": files}), _job(), packet)


def test_bundle_conversion_rejects_source_packet_drift_and_size_overflow(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src/app.py").write_text("base\n")
    packet = build_builder_source_packet(root, ["src/"])
    packet["files"][0]["base_sha256"] = "0" * 64
    with pytest.raises(WorkflowError, match="hash mismatch"):
        build_bound_builder_bundle(json.dumps({"files": [{"path": "src/app.py", "content": "x"}]}),
                                  _job(), packet)

    packet = build_builder_source_packet(root, ["src/"])
    with pytest.raises(WorkflowError, match="size bound"):
        build_bound_builder_bundle(
            json.dumps({"files": [{"path": "src/app.py", "content": "x" * 12001}]}),
            _job(), packet,
        )
