"""Bounded builder file-bundle return contract for the T3 text transport.

T3 currently returns assistant text, not downloadable workspace artifacts. This
contract therefore permits only a small, explicit JSON bundle in a builder
wire field and is not a dispatch enablement. Intake remains test-only because
the workspace validator accepts only marked synthetic roots and requires a
working OS-enforced no-network boundary.
"""

import hashlib
import json
import re
import base64
import binascii
from pathlib import Path, PurePosixPath

from builder_candidate_prototype import prepare_and_validate
from core import WorkflowError
from t3_result import (BUILDER_BUNDLE_KEY, MAX_BUILDER_ASSISTANT_CHARS,
                       T3ResultError, decode_t3_result)


BUNDLE_SCHEMA = "engine-builder-bundle/v1"
MAX_BUNDLE_JSON_CHARS = 50_000
MAX_BUNDLE_FILES = 8
MAX_BUNDLE_FILE_BYTES = 12_000
MAX_BUNDLE_TOTAL_BYTES = 24_000
_HASH = re.compile(r"^[0-9a-f]{64}$")
_FILE_KEYS = {"path", "base_sha256", "content_base64", "content_sha256"}
_BUNDLE_KEYS = {"schema", "job_id", "candidate_id", "plan_revision_hash", "files", "bundle_sha256"}


class BuilderArtifactError(ValueError):
    """Builder response does not satisfy the bounded artifact contract."""


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _is_hash(value):
    return isinstance(value, str) and _HASH.fullmatch(value) is not None


def _validate_bundle_object(bundle, body):
    if not isinstance(bundle, dict) or set(bundle) != _BUNDLE_KEYS:
        raise BuilderArtifactError("builder bundle has an invalid shape")
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise BuilderArtifactError("unsupported builder bundle schema")
    for field in ("job_id", "candidate_id", "plan_revision_hash"):
        if bundle.get(field) != body.get(field):
            raise BuilderArtifactError("builder bundle binding mismatch: " + field)
    files = bundle.get("files")
    if not isinstance(files, list) or not files or len(files) > MAX_BUNDLE_FILES:
        raise BuilderArtifactError("builder bundle file count outside bounds")
    if not _is_hash(bundle.get("bundle_sha256")):
        raise BuilderArtifactError("builder bundle digest is malformed")
    if hashlib.sha256(_canonical(files)).hexdigest() != bundle["bundle_sha256"]:
        raise BuilderArtifactError("builder bundle digest mismatch")

    seen = set()
    total = 0
    for item in files:
        if not isinstance(item, dict) or set(item) != _FILE_KEYS:
            raise BuilderArtifactError("builder bundle file entry has an invalid shape")
        path = item.get("path")
        if (not isinstance(path, str) or not path or len(path) > 240
                or "\\" in path or "\x00" in path
                or PurePosixPath(path).is_absolute()
                or any(part in ("", ".", "..") for part in path.split("/"))
                or PurePosixPath(path).as_posix() != path
                or path in seen):
            raise BuilderArtifactError("builder bundle path is empty or duplicated")
        seen.add(path)
        base_hash = item.get("base_sha256")
        if base_hash is not None and not _is_hash(base_hash):
            raise BuilderArtifactError("builder bundle base hash is malformed")
        if not _is_hash(item.get("content_sha256")):
            raise BuilderArtifactError("builder bundle content hash is malformed")
        encoded = item.get("content_base64")
        if not isinstance(encoded, str):
            raise BuilderArtifactError("builder bundle content is not base64 text")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise BuilderArtifactError("builder bundle content is invalid base64") from exc
        if len(content) > MAX_BUNDLE_FILE_BYTES:
            raise BuilderArtifactError("builder bundle file exceeds size bound")
        total += len(content)
        if total > MAX_BUNDLE_TOTAL_BYTES:
            raise BuilderArtifactError("builder bundle total exceeds size bound")
        if hashlib.sha256(content).hexdigest() != item["content_sha256"]:
            raise BuilderArtifactError("builder bundle content hash mismatch")
    return files


def decode_builder_artifact_return(*, assistant_text, job, task_id, executed_model):
    """Validate a builder result wire and return its bound file bundle.

    The result envelope itself remains the existing strict Engine schema. The
    separate ``builder_bundle_json`` member carries only small file changes;
    source hashes and allowed paths are rechecked by bundle intake later.
    """
    if (not isinstance(assistant_text, str)
            or len(assistant_text) > MAX_BUILDER_ASSISTANT_CHARS):
        raise BuilderArtifactError("builder response exceeds T3 summary bound")
    try:
        session, body, wire, _events = decode_t3_result(
            assistant_text=assistant_text,
            job=job,
            task_id=task_id,
            executed_model=executed_model,
        )
    except T3ResultError as exc:
        raise BuilderArtifactError(str(exc)) from exc
    if job.get("role") != "builder" or body.get("role") != "builder":
        raise BuilderArtifactError("builder artifact return requires a builder job")
    if body.get("status") != "COMPLETE" or body.get("verdict") not in ("PASS", "BLOCKED"):
        raise BuilderArtifactError("builder artifact return has no valid completed verdict")
    raw = wire.get(BUILDER_BUNDLE_KEY)
    if not isinstance(raw, str) or not raw or len(raw) > MAX_BUNDLE_JSON_CHARS:
        raise BuilderArtifactError("builder bundle is missing or exceeds text bound")
    try:
        bundle = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise BuilderArtifactError("builder bundle JSON is malformed") from exc
    files = _validate_bundle_object(bundle, body)
    return {
        "task_id": session,
        "job_id": body["job_id"],
        "candidate_id": body["candidate_id"],
        "plan_revision_hash": body["plan_revision_hash"],
        "verdict": body["verdict"],
        "bundle_sha256": bundle["bundle_sha256"],
        "files": files,
    }


def intake_and_validate_builder_return(*, assistant_text, job, task_id, executed_model,
                                       base_root, destination, allowed_paths,
                                       trusted_validation_commands, timeout_seconds=60):
    """Decode and pass an actual builder text bundle to the isolated prototype.

    On unavailable network isolation, the returned candidate remains staged
    with validation refused. This helper deliberately cannot accept a live
    repository root because the underlying prototype requires its test marker.
    """
    decoded = decode_builder_artifact_return(
        assistant_text=assistant_text,
        job=job,
        task_id=task_id,
        executed_model=executed_model,
    )
    result = prepare_and_validate(
        base_root,
        {"files": decoded["files"]},
        destination,
        allowed_paths,
        trusted_validation_commands,
        timeout_seconds=timeout_seconds,
    )
    result.update({key: decoded[key] for key in (
        "task_id", "job_id", "candidate_id", "plan_revision_hash", "bundle_sha256"
    )})
    return result


def accept_synthetic_t3_builder_candidate(*, launcher, assistant_text, job, task_id,
                                          executed_model, base_root, destination,
                                          allowed_paths, trusted_validation_commands,
                                          timeout_seconds=60):
    """Test-only synthetic T3-to-Engine artifact candidate acceptance path.

    The launcher class must explicitly opt into the test seam. Production T3
    launchers do not satisfy this check. The source and candidate are both
    checked by the synthetic-only snapshot prototype; validation refusal or
    failure raises instead of creating an Engine candidate binding.
    """
    from builder_candidate_binding import (
        capture_baseline_snapshot,
        create_engine_candidate_binding,
    )

    from t3_supervisor_client import SupervisorLauncher
    if (not isinstance(launcher, SupervisorLauncher)
            or getattr(type(launcher), "allow_builder_for_tests", None) is not True
            or getattr(type(launcher), "accept_builder_artifacts_for_tests", None) is not True):
        raise WorkflowError("T3 builder artifact acceptance requires an opted-in test supervisor fixture")
    if not isinstance(job, dict) or job.get("role") != "builder":
        raise WorkflowError("T3 builder artifact acceptance requires a builder job")
    destination = Path(destination)
    if not destination.is_absolute() or not destination.is_dir() or destination.is_symlink():
        raise WorkflowError("Builder artifact job directory must be an existing real directory")
    baseline_path = destination / "builder-baseline.json"
    capture_baseline_snapshot(base_root, baseline_path)
    validation = intake_and_validate_builder_return(
        assistant_text=assistant_text,
        job=job,
        task_id=task_id,
        executed_model=executed_model,
        base_root=base_root,
        destination=destination / "builder-candidate",
        allowed_paths=allowed_paths,
        trusted_validation_commands=trusted_validation_commands,
        timeout_seconds=timeout_seconds,
    )
    if (validation.get("validation_status") != "complete"
            or validation.get("validation_complete") is not True
            or validation.get("validation_passed") is not True):
        raise WorkflowError("Builder candidate validation did not complete successfully")
    candidate = create_engine_candidate_binding(
        source_root=base_root,
        baseline_artifact=baseline_path,
        candidate_root=validation["workspace"],
        validation=validation,
        evidence_directory=destination,
    )
    return candidate, validation
