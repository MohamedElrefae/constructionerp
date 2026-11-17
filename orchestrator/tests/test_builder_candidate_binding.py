import base64
import hashlib
import shutil
import sys

import builder_candidate_prototype as prototype
import pytest
from builder_candidate_binding import (
    capture_baseline_snapshot,
    load_baseline_snapshot,
    recheck_baseline,
    recheck_candidate,
    verify_isolated_validation,
)
from core import WorkflowError


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _source(path):
    path.mkdir()
    (path / prototype.SYNTHETIC_MARKER).write_bytes(prototype.SYNTHETIC_MARKER_VALUE)
    (path / "src").mkdir()
    (path / "src/base.py").write_bytes(b"VALUE = 1\n")
    (path / "README.txt").write_bytes(b"baseline context\n")
    return path


def _bundle(base=b"VALUE = 1\n", content=b"VALUE = 2\n"):
    return {
        "files": [
            {
                "path": "src/base.py",
                "base_sha256": _sha(base),
                "content_base64": base64.b64encode(content).decode("ascii"),
                "content_sha256": _sha(content),
            }
        ]
    }


def test_baseline_manifest_is_immutable_and_rechecks_exact_tree(tmp_path):
    source = _source(tmp_path / "source")
    artifact = tmp_path / "baseline.json"
    baseline = capture_baseline_snapshot(source, artifact)
    assert artifact.stat().st_mode & 0o777 == 0o400
    assert load_baseline_snapshot(artifact) == baseline
    assert recheck_baseline(source, artifact) == baseline["tree_sha256"]
    with pytest.raises(WorkflowError, match="already exists"):
        capture_baseline_snapshot(source, artifact)


def test_baseline_recheck_detects_source_drift_and_digest_tampering(tmp_path):
    source = _source(tmp_path / "source")
    artifact = tmp_path / "baseline.json"
    baseline = capture_baseline_snapshot(source, artifact)
    (source / "README.txt").write_bytes(b"changed\n")
    with pytest.raises(WorkflowError, match="content or mode changed"):
        recheck_baseline(source, baseline)

    import json

    document = json.loads(artifact.read_text())
    document["tree_sha256"] = "0" * 64
    artifact.chmod(0o600)
    artifact.write_text(json.dumps(document))
    with pytest.raises(WorkflowError, match="digest mismatch"):
        load_baseline_snapshot(artifact)


def test_candidate_recheck_detects_staged_artifact_drift(tmp_path, monkeypatch):
    source = _source(tmp_path / "source")
    baseline = capture_baseline_snapshot(source, tmp_path / "baseline.json")
    monkeypatch.setattr(prototype, "_network_boundary_available", lambda: False)
    result = prototype.prepare_and_validate(
        source,
        _bundle(),
        tmp_path / "candidate",
        ["src/"],
        [[sys.executable, "-c", "raise SystemExit(0)"]],
    )
    assert result["validation_status"] == "refused"
    digest = result["candidate_snapshot_sha256"]
    assert recheck_candidate(tmp_path / "candidate", digest) == digest
    with pytest.raises(WorkflowError, match="not complete and passing"):
        verify_isolated_validation(
            baseline=baseline,
            source_root=source,
            candidate_root=tmp_path / "candidate",
            validation=result,
        )
    (tmp_path / "candidate/src/base.py").write_bytes(b"changed after staging\n")
    with pytest.raises(WorkflowError, match="changed after validation"):
        recheck_candidate(tmp_path / "candidate", digest)


def test_refuses_symlinked_baseline_and_candidate_entries(tmp_path):
    source = _source(tmp_path / "source")
    (source / "src/link").symlink_to("base.py")
    with pytest.raises(WorkflowError, match="symlink or special"):
        capture_baseline_snapshot(source, tmp_path / "baseline.json")


def test_binds_real_isolated_validation_when_kernel_boundary_exists(tmp_path):
    if not shutil.which("bwrap") or not prototype._network_boundary_available():
        pytest.skip("kernel denies bubblewrap network namespace creation")
    source = _source(tmp_path / "source")
    baseline = capture_baseline_snapshot(source, tmp_path / "baseline.json")
    result = prototype.prepare_and_validate(
        source,
        _bundle(),
        tmp_path / "candidate",
        ["src/"],
        [
            [
                "/usr/bin/python3",
                "-c",
                "from pathlib import Path; assert Path('src/base.py').read_text() == 'VALUE = 2\\n'",
            ]
        ],
    )
    binding = verify_isolated_validation(
        baseline=baseline,
        source_root=source,
        candidate_root=tmp_path / "candidate",
        validation=result,
    )
    assert binding["baseline_sha256"] == baseline["tree_sha256"]
    assert binding["candidate_sha256"] == result["candidate_snapshot_sha256"]
    assert binding["validation_passed"] is True


def test_engine_candidate_binding_rechecks_validation_and_both_trees(tmp_path):
    if not shutil.which("bwrap") or not prototype._network_boundary_available():
        pytest.skip("kernel denies bubblewrap network namespace creation")
    from builder_candidate_binding import (
        create_engine_candidate_binding,
        recheck_engine_candidate,
    )

    source = _source(tmp_path / "source")
    baseline_path = tmp_path / "baseline.json"
    baseline = capture_baseline_snapshot(source, baseline_path)
    result = prototype.prepare_and_validate(
        source,
        _bundle(),
        tmp_path / "candidate",
        ["src/"],
        [
            [
                "/usr/bin/python3",
                "-c",
                "from pathlib import Path; assert Path('src/base.py').read_text() == 'VALUE = 2\\n'",
            ]
        ],
    )
    engine_candidate = create_engine_candidate_binding(
        source_root=source,
        baseline_artifact=baseline_path,
        candidate_root=tmp_path / "candidate",
        validation=result,
        evidence_directory=tmp_path,
    )
    assert engine_candidate["candidate_id"] == engine_candidate["manifest_hash"]
    assert recheck_engine_candidate(engine_candidate, source) is engine_candidate

    # A downstream Engine gate rechecks these same immutable bytes each time.
    (tmp_path / "candidate/src/base.py").write_bytes(b"drifted\n")
    with pytest.raises(WorkflowError, match="Candidate workspace changed"):
        recheck_engine_candidate(engine_candidate, source)


def test_engine_candidate_rejects_changed_validation_evidence(tmp_path):
    if not shutil.which("bwrap") or not prototype._network_boundary_available():
        pytest.skip("kernel denies bubblewrap network namespace creation")
    from builder_candidate_binding import (
        create_engine_candidate_binding,
        recheck_engine_candidate,
    )

    source = _source(tmp_path / "source")
    baseline_path = tmp_path / "baseline.json"
    capture_baseline_snapshot(source, baseline_path)
    result = prototype.prepare_and_validate(
        source,
        _bundle(),
        tmp_path / "candidate",
        ["src/"],
        [["/usr/bin/python3", "-c", "pass"]],
    )
    candidate = create_engine_candidate_binding(
        source_root=source,
        baseline_artifact=baseline_path,
        candidate_root=tmp_path / "candidate",
        validation=result,
        evidence_directory=tmp_path,
    )
    evidence_path = candidate["artifact_binding"]["validation_artifact"]
    with open(evidence_path, "ab") as stream:
        stream.write(b" ")
    with pytest.raises(WorkflowError, match="evidence digest mismatch"):
        recheck_engine_candidate(candidate, source)


def test_engine_recheck_refuses_forged_artifact_binding_on_ordinary_root(tmp_path):
    from builder_candidate_binding import recheck_engine_candidate
    from core import digest

    ordinary = tmp_path / "ordinary-repo"
    ordinary.mkdir()
    (ordinary / ".git").mkdir()
    manifest = {
        "schema": "engine-artifact-candidate/v1",
        "mode": "synthetic-test-only",
        "kind": "code",
        "baseline_sha256": "a" * 64,
        "candidate_sha256": "b" * 64,
        "validation_sha256": "c" * 64,
    }
    identity = digest(manifest)
    forged = {
        "kind": "code",
        "candidate_id": identity,
        "manifest_hash": identity,
        "tree_oid": manifest["candidate_sha256"],
        "manifest": manifest,
        "artifact_binding": {
            "source_root": str(ordinary),
            "candidate_root": str(ordinary),
            "baseline_artifact": str(tmp_path / "missing-baseline.json"),
            "validation_artifact": str(tmp_path / "missing-validation.json"),
        },
    }
    with pytest.raises(WorkflowError, match="marked synthetic roots only"):
        recheck_engine_candidate(forged, ordinary)


def test_engine_recheck_rejects_synthetic_marker_inside_git_repository(tmp_path):
    from builder_candidate_binding import recheck_engine_candidate
    from core import digest

    repository = _source(tmp_path / "marked-repo")
    (repository / ".git").mkdir()
    manifest = {
        "schema": "engine-artifact-candidate/v1",
        "mode": "synthetic-test-only",
        "kind": "code",
        "baseline_sha256": "a" * 64,
        "candidate_sha256": "b" * 64,
        "validation_sha256": "c" * 64,
    }
    identity = digest(manifest)
    forged = {
        "kind": "code",
        "candidate_id": identity,
        "manifest_hash": identity,
        "tree_oid": manifest["candidate_sha256"],
        "manifest": manifest,
        "artifact_binding": {
            "source_root": str(repository),
            "candidate_root": str(repository),
            "baseline_artifact": str(tmp_path / "missing-baseline.json"),
            "validation_artifact": str(tmp_path / "missing-validation.json"),
        },
    }
    with pytest.raises(WorkflowError, match="refuses repository roots"):
        recheck_engine_candidate(forged, repository)


def test_engine_refuses_artifact_binding_without_explicit_test_launcher():
    from engine import Engine

    engine = Engine.__new__(Engine)
    engine.launcher = None
    with pytest.raises(WorkflowError, match="test-only launcher"):
        engine._recheck_candidate({"kind": "code", "artifact_binding": {}})
