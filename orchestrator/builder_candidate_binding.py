"""Unwired artifact-backed baseline/candidate recheck prototype.

This is deliberately not an Engine acceptance API. It binds the existing
synthetic-only builder workspace prototype's snapshots and isolated-validation
records to an immutable baseline manifest. A same-user hash is integrity
metadata, not an identity/signature or security boundary.
"""

import hashlib
import json
import os
import stat
from pathlib import Path

from builder_candidate_prototype import _digest_snapshot, _snapshot
from core import WorkflowError, relative

SCHEMA = "engine-builder-baseline/v1"
MAX_MANIFEST_BYTES = 2_000_000
SYNTHETIC_MARKER = ".builder-intake-synthetic-source"
SYNTHETIC_MARKER_VALUE = b"builder-intake-test-source/v1\n"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _require_synthetic_root(root):
    marker = root / SYNTHETIC_MARKER
    marker_info = marker.lstat() if marker.exists() or marker.is_symlink() else None
    if (marker_info is None or not stat.S_ISREG(marker_info.st_mode)
            or marker.is_symlink() or marker.read_bytes() != SYNTHETIC_MARKER_VALUE):
        raise WorkflowError("Artifact candidate accepts marked synthetic roots only")
    git_dir = root / ".git"
    if git_dir.exists() or git_dir.is_symlink():
        raise WorkflowError("Artifact candidate refuses repository roots")


def _tree_entries(root):
    root = Path(root).resolve(strict=True)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise WorkflowError("Baseline root must be a real directory")
    entries = _snapshot(root)
    rows = []
    for name, data, mode in entries:
        relative(name)
        rows.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(),
                     "size": len(data), "mode": mode})
    return root, info, rows, _digest_snapshot(entries)


def capture_baseline_snapshot(source_root, artifact_path):
    """Write a create-once manifest of the synthetic prototype source tree."""
    root, info, rows, tree_sha = _tree_entries(source_root)
    _require_synthetic_root(root)

    target_input = Path(artifact_path)
    if not target_input.is_absolute() or not target_input.parent.is_dir():
        raise WorkflowError("Baseline artifact path must be absolute with an existing parent")
    target_parent = target_input.parent.resolve(strict=True)
    target = target_parent / target_input.name
    if target == root or target in root.parents or root in target.parents:
        raise WorkflowError("Baseline artifact must be outside the source tree")

    document = {
        "schema": SCHEMA,
        "root_identity": {"device": info.st_dev, "inode": info.st_ino},
        "tree_sha256": tree_sha,
        "entries": rows,
    }
    document["manifest_sha256"] = hashlib.sha256(_canonical(document)).hexdigest()
    encoded = _canonical(document) + b"\n"
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise WorkflowError("Baseline manifest exceeds size bound")
    # O_EXCL prevents replacement and symlink following. 0400 discourages
    # accidental edits; digest checks still detect tampering.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(target, flags, 0o400)
    except FileExistsError as exc:
        raise WorkflowError("Baseline artifact already exists") from exc
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return document


def load_baseline_snapshot(artifact_path):
    path = Path(artifact_path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise WorkflowError("Baseline artifact is missing, symlinked, or oversized")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise WorkflowError("Baseline artifact is malformed") from exc
    if not isinstance(document, dict) or set(document) != {
        "schema", "root_identity", "tree_sha256", "entries", "manifest_sha256"
    } or document.get("schema") != SCHEMA:
        raise WorkflowError("Baseline artifact has an invalid schema")
    claimed = document["manifest_sha256"]
    unsigned = dict(document)
    del unsigned["manifest_sha256"]
    if (not isinstance(claimed, str) or len(claimed) != 64
            or hashlib.sha256(_canonical(unsigned)).hexdigest() != claimed):
        raise WorkflowError("Baseline manifest digest mismatch")
    return document


def recheck_baseline(source_root, baseline):
    """Require the exact same source directory and tree bytes/modes as baseline."""
    if isinstance(baseline, (str, os.PathLike)):
        baseline = load_baseline_snapshot(baseline)
    if not isinstance(baseline, dict) or baseline.get("schema") != SCHEMA:
        raise WorkflowError("Trusted baseline snapshot is required")
    root, info, rows, tree_sha = _tree_entries(source_root)
    expected_identity = baseline.get("root_identity")
    if expected_identity != {"device": info.st_dev, "inode": info.st_ino}:
        raise WorkflowError("Baseline source directory identity changed")
    if tree_sha != baseline.get("tree_sha256") or rows != baseline.get("entries"):
        raise WorkflowError("Baseline source content or mode changed")
    return tree_sha


def recheck_candidate(candidate_root, expected_tree_sha256):
    """Recompute the complete staged workspace hash and reject drift."""
    if (not isinstance(expected_tree_sha256, str) or len(expected_tree_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in expected_tree_sha256)):
        raise WorkflowError("Expected candidate digest is malformed")
    root, _info, _rows, tree_sha = _tree_entries(candidate_root)
    if tree_sha != expected_tree_sha256:
        raise WorkflowError("Candidate workspace changed after validation")
    return tree_sha


def verify_isolated_validation(*, baseline, source_root, candidate_root, validation):
    """Bind successful prototype validation records to current source/candidate.

    This verifies the prototype's evidence shape and hashes. It does not confer
    Engine authority and cannot prove evidence provenance against a same-UID
    attacker; callers must obtain ``validation`` directly from the trusted
    validator invocation and retain the artifact privately.
    """
    baseline_sha = recheck_baseline(source_root, baseline)
    if not isinstance(validation, dict):
        raise WorkflowError("Validation evidence is missing")
    expected_candidate = validation.get("candidate_snapshot_sha256")
    candidate_sha = recheck_candidate(candidate_root, expected_candidate)
    if (validation.get("source_snapshot_sha256") != baseline_sha
            or validation.get("validation_status") != "complete"
            or validation.get("validation_complete") is not True
            or validation.get("validation_passed") is not True
            or validation.get("refusal_reason")):
        raise WorkflowError("Validation evidence is not complete and passing")
    records = validation.get("records")
    if not isinstance(records, list) or not records:
        raise WorkflowError("Isolated validation has no command records")
    for record in records:
        if (not isinstance(record, dict) or record.get("exit_code") != 0
                or record.get("timed_out") is True):
            raise WorkflowError("Isolated validation contains a failed command")
        for field in ("stdout_sha256", "stderr_sha256"):
            digest = record.get(field)
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(ch not in "0123456789abcdef" for ch in digest)):
                raise WorkflowError("Validation command evidence digest is malformed")
    return {
        "schema": "engine-builder-validation-binding/v1",
        "baseline_sha256": baseline_sha,
        "candidate_sha256": candidate_sha,
        "command_count": len(records),
        "validation_status": "complete",
        "validation_passed": True,
    }


def create_engine_candidate_binding(*, source_root, baseline_artifact, candidate_root,
                                    validation, evidence_directory):
    """Create the Engine-shaped code candidate record for an isolated artifact.

    The artifact directory is a private local evidence location. This function
    does not write the source checkout and refuses candidates without completed
    isolation-bound validation. The record is not connected to dispatch.
    """
    source = Path(source_root).resolve(strict=True)
    candidate_dir = Path(candidate_root).resolve(strict=True)
    baseline = load_baseline_snapshot(baseline_artifact)
    validation_binding = verify_isolated_validation(
        baseline=baseline, source_root=source, candidate_root=candidate_dir,
        validation=validation,
    )
    validation_bytes = _canonical(validation) + b"\n"
    evidence_dir = Path(evidence_directory)
    if not evidence_dir.is_absolute() or not evidence_dir.is_dir() or evidence_dir.is_symlink():
        raise WorkflowError("Candidate evidence directory must be an existing real directory")
    evidence_path = evidence_dir / (validation_binding["candidate_sha256"] + ".validation.json")
    from core import atomic_write, digest
    atomic_write(evidence_path, validation_bytes, immutable=True)
    manifest = {
        "schema": "engine-artifact-candidate/v1",
        "mode": "synthetic-test-only",
        "kind": "code",
        "baseline_sha256": validation_binding["baseline_sha256"],
        "candidate_sha256": validation_binding["candidate_sha256"],
        "validation_sha256": hashlib.sha256(validation_bytes).hexdigest(),
    }
    candidate_id = digest(manifest)
    return {
        "kind": "code",
        "candidate_id": candidate_id,
        "manifest_hash": candidate_id,
        "tree_oid": validation_binding["candidate_sha256"],
        "manifest": manifest,
        "artifact_binding": {
            "source_root": str(source),
            "candidate_root": str(candidate_dir),
            "baseline_artifact": str(Path(baseline_artifact).resolve(strict=True)),
            "validation_artifact": str(evidence_path.resolve(strict=True)),
        },
    }


def recheck_engine_candidate(candidate, engine_root):
    """Engine's artifact-backed candidate recheck; any mismatch is a refusal."""
    from core import digest
    if not isinstance(candidate, dict) or candidate.get("kind") != "code":
        raise WorkflowError("Artifact-backed candidate has invalid kind")
    manifest = candidate.get("manifest")
    binding = candidate.get("artifact_binding")
    if (not isinstance(manifest, dict)
            or set(manifest) != {"schema", "mode", "kind", "baseline_sha256", "candidate_sha256", "validation_sha256"}
            or manifest.get("schema") != "engine-artifact-candidate/v1"
            or manifest.get("mode") != "synthetic-test-only"
            or manifest.get("kind") != "code"
            or not isinstance(binding, dict)
            or set(binding) != {"source_root", "candidate_root", "baseline_artifact", "validation_artifact"}):
        raise WorkflowError("Artifact-backed candidate binding is malformed")
    expected_id = digest(manifest)
    if (candidate.get("candidate_id") != expected_id
            or candidate.get("manifest_hash") != expected_id
            or candidate.get("tree_oid") != manifest.get("candidate_sha256")):
        raise WorkflowError("Artifact-backed candidate identity mismatch")

    source = Path(binding["source_root"]).resolve(strict=True)
    root = Path(engine_root).resolve(strict=True)
    if source != root:
        raise WorkflowError("Artifact-backed baseline is not bound to the Engine root")
    # This restriction is repeated at every Engine recheck. A caller cannot
    # convert a production repository into this experimental candidate route
    # merely by supplying a forged artifact_binding object.
    _require_synthetic_root(source)
    baseline = load_baseline_snapshot(binding["baseline_artifact"])
    validation_path = Path(binding["validation_artifact"])
    if validation_path.is_symlink() or not validation_path.is_file():
        raise WorkflowError("Artifact-backed validation evidence is missing or symlinked")
    validation_bytes = validation_path.read_bytes()
    if hashlib.sha256(validation_bytes).hexdigest() != manifest.get("validation_sha256"):
        raise WorkflowError("Artifact-backed validation evidence digest mismatch")
    try:
        validation = json.loads(validation_bytes)
    except (UnicodeError, ValueError) as exc:
        raise WorkflowError("Artifact-backed validation evidence is malformed") from exc
    evidence = verify_isolated_validation(
        baseline=baseline,
        source_root=source,
        candidate_root=binding["candidate_root"],
        validation=validation,
    )
    if (evidence["baseline_sha256"] != manifest["baseline_sha256"]
            or evidence["candidate_sha256"] != manifest["candidate_sha256"]):
        raise WorkflowError("Artifact-backed validation no longer matches candidate")
    return candidate
