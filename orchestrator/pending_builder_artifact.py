"""Append-only coordinator records for detached, validated builder artifacts.

Pending artifacts are review references only. This module never modifies the
Engine candidate or creates a native Git candidate. Its dedicated store table is
append-only through the API and separate from workflow events; it is not protection from a same-UID database
editor, so the store and evidence directory remain within the trusted owner
boundary.
"""

import hashlib
import json
import os
from pathlib import Path

from core import WorkflowError


SCHEMA = "engine-pending-builder-artifact/v1"
MAX_EVIDENCE_BYTES = 2_000_000


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _read_evidence(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_EVIDENCE_BYTES:
        raise WorkflowError("Pending builder evidence is missing, symlinked, or oversized")
    return p.read_bytes()


def record_pending_builder_artifact(*, store, result, source_root,
                                    baseline_artifact, evidence_directory):
    """Persist validation evidence and one immutable pending-artifact event."""
    if not isinstance(result, dict) or result.get("validation_status") != "complete" or result.get("validation_passed") is not True:
        raise WorkflowError("Only completely validated builder artifacts may be recorded")
    binding = result.get("builder_binding")
    if (not isinstance(binding, dict)
            or binding.get("model_evidence") not in ("executed", "configured_only")
            or binding.get("model_evidence_source") != "managed_supervisor_receipt"):
        raise WorkflowError("Pending artifact requires explicit supervisor model-evidence metadata")
    candidate_root = Path(result.get("workspace", ""))
    source = Path(source_root).resolve(strict=True)
    evidence_dir = Path(evidence_directory)
    if (not candidate_root.is_absolute() or candidate_root.is_symlink()
            or not candidate_root.is_dir() or not evidence_dir.is_absolute()
            or not evidence_dir.is_dir() or evidence_dir.is_symlink()):
        raise WorkflowError("Pending artifact paths must be existing absolute directories")
    evidence = _canonical(result) + b"\n"
    if len(evidence) > MAX_EVIDENCE_BYTES:
        raise WorkflowError("Pending builder evidence exceeds bound")
    evidence_sha = hashlib.sha256(evidence).hexdigest()
    evidence_path = evidence_dir / ("builder-" + evidence_sha + ".json")
    if evidence_path.exists() or evidence_path.is_symlink():
        if evidence_path.is_symlink() or _read_evidence(evidence_path) != evidence:
            raise WorkflowError("Immutable pending evidence path conflicts")
    else:
        fd = os.open(evidence_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o400)
        with os.fdopen(fd, "wb") as stream:
            stream.write(evidence)
            stream.flush()
            os.fsync(stream.fileno())
    payload = {
        "schema": SCHEMA,
        "status": "PENDING_OWNER_REVIEW",
        "job_id": binding["job_id"],
        "task_id": binding["task_id"],
        "candidate_id": binding["candidate_id"],
        "plan_revision_hash": binding["plan_revision_hash"],
        "executed_model": binding["executed_model"],
        "configured_model": binding["configured_model"],
        "model_evidence": binding["model_evidence"],
        "model_evidence_source": binding["model_evidence_source"],
        "bundle_sha256": binding["bundle_sha256"],
        "source_root": str(source),
        "baseline_artifact": str(Path(baseline_artifact).resolve(strict=True)),
        "baseline_manifest_sha256": binding["baseline_manifest_sha256"],
        "candidate_root": str(candidate_root.resolve(strict=True)),
        "candidate_snapshot_sha256": binding["candidate_snapshot_sha256"],
        "evidence_path": str(evidence_path.resolve(strict=True)),
        "evidence_sha256": evidence_sha,
    }
    store.put_pending_builder_artifact(binding["job_id"], payload)
    return payload


def recheck_pending_builder_artifact(*, store, job_id, expected_task_id,
                                    expected_candidate_id, expected_plan_revision_hash):
    """Re-read immutable store/evidence and recompute baseline/candidate checks."""
    payload = store.pending_builder_artifact(job_id)
    if payload is None:
        raise WorkflowError("Pending builder artifact record is missing or ambiguous")
    if (not isinstance(payload, dict) or payload.get("schema") != SCHEMA
            or payload.get("status") != "PENDING_OWNER_REVIEW"
            or payload.get("job_id") != job_id
            or payload.get("task_id") != expected_task_id
            or payload.get("candidate_id") != expected_candidate_id
            or payload.get("plan_revision_hash") != expected_plan_revision_hash
            or payload.get("model_evidence") not in ("executed", "configured_only")):
        raise WorkflowError("Pending builder artifact identity mismatch")
    evidence_bytes = _read_evidence(payload.get("evidence_path", ""))
    if hashlib.sha256(evidence_bytes).hexdigest() != payload.get("evidence_sha256"):
        raise WorkflowError("Pending builder evidence digest mismatch")
    try:
        evidence = json.loads(evidence_bytes)
    except (UnicodeError, ValueError) as exc:
        raise WorkflowError("Pending builder evidence is malformed") from exc
    from builder_project_candidate import recheck_t3_builder_return

    expected_binding = evidence.get("builder_binding")
    if (not isinstance(expected_binding, dict)
            or expected_binding.get("job_id") != payload["job_id"]
            or expected_binding.get("task_id") != payload["task_id"]
            or expected_binding.get("candidate_id") != payload["candidate_id"]
            or expected_binding.get("plan_revision_hash") != payload["plan_revision_hash"]
            or expected_binding.get("executed_model") != payload["executed_model"]
            or expected_binding.get("configured_model") != payload["configured_model"]
            or expected_binding.get("model_evidence") != payload["model_evidence"]
            or expected_binding.get("bundle_sha256") != payload["bundle_sha256"]):
        raise WorkflowError("Pending evidence provenance differs from coordinator record")
    checked = recheck_t3_builder_return(
        source_root=payload["source_root"],
        baseline_artifact=payload["baseline_artifact"],
        trusted_baseline_sha256=payload["baseline_manifest_sha256"],
        candidate_root=payload["candidate_root"],
        evidence=evidence,
        expected_binding=expected_binding,
    )
    if checked["candidate_snapshot_sha256"] != payload.get("candidate_snapshot_sha256"):
        raise WorkflowError("Pending candidate snapshot differs from coordinator record")
    return payload
