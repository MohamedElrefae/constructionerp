"""Experimental real-project builder staging and offline validation primitive.

This module is deliberately unwired from Engine/T3. It creates a disposable
full source copy (excluding Git metadata and credential-shaped files), stages
only hash-bound allowed edits, and runs caller-trusted commands with network
isolation. Hashes provide integrity checks, not same-UID provenance or
authentication; the caller must retain the baseline digest in trusted state.
"""

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import time
from pathlib import Path, PurePosixPath

from builder_candidate_prototype import _network_boundary_available
from builder_intake import stage_bundle
from core import WorkflowError
from sandbox import command as sandbox_command

SCHEMA = "engine-builder-project-baseline/v2"
MAX_FILES = 20_000
MAX_TOTAL_BYTES = 256_000_000
MAX_MANIFEST_BYTES = 8_000_000
MAX_COMMANDS = 32
MAX_TIMEOUT = 600
_HEX = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "token",
    "token.json",
    "auth.json",
}
_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _relative(path):
    if (
        not isinstance(path, str)
        or not path
        or "\\" in path
        or "\x00" in path
        or PurePosixPath(path).is_absolute()
        or any(p in ("", ".", "..") for p in path.split("/"))
        or PurePosixPath(path).as_posix() != path
    ):
        raise WorkflowError("Project snapshot contains a non-normalized path")
    return path


def _excluded_path(rel, generated):
    return any(rel == item.rstrip("/") or (item.endswith("/") and rel.startswith(item)) for item in generated)


def _normalize_generated(generated):
    if not isinstance(generated, list | tuple):
        raise WorkflowError("Generated path exclusions must be a bounded list")
    normalized = []
    for item in generated:
        trimmed = item.rstrip("/") if isinstance(item, str) else ""
        canonical_item = trimmed + ("/" if isinstance(item, str) and item.endswith("/") else "")
        if (
            not isinstance(item, str)
            or not item
            or "\\" in item
            or "\x00" in item
            or item != canonical_item
            or PurePosixPath(item).is_absolute()
            or any(part in ("", ".", "..") for part in trimmed.split("/"))
        ):
            raise WorkflowError("Generated path exclusion is not normalized")
        normalized.append(item)
    return sorted(set(normalized))


def _entries(root, generated=()):
    root = Path(root).resolve(strict=True)
    generated = _normalize_generated(generated)
    root_info = root.lstat()
    if not stat.S_ISDIR(root_info.st_mode):
        raise WorkflowError("Project source must be a real directory")
    result = []
    total = 0
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        dirs.sort()
        files.sort()
        kept = []
        for name in dirs:
            path = current_path / name
            info = path.lstat()
            rel_dir = path.relative_to(root).as_posix() + "/"
            if _excluded_path(rel_dir, generated):
                continue
            if name == ".git":
                if not stat.S_ISDIR(info.st_mode):
                    raise WorkflowError("Linked or symlinked Git metadata is refused")
                continue
            if not stat.S_ISDIR(info.st_mode):
                raise WorkflowError(
                    "Project contains symlink or special directory: " + str(path.relative_to(root))
                )
            kept.append(name)
        dirs[:] = kept
        for name in files:
            path = current_path / name
            rel = _relative(path.relative_to(root).as_posix())
            if _excluded_path(rel, generated):
                continue
            if name == ".git":
                # Linked Git worktrees store a gitdir pointer in a regular
                # .git file. Never copy that pointer into the detached
                # candidate: it could expose the source repository's shared
                # Git metadata to validation commands.
                if not stat.S_ISREG(path.lstat().st_mode):
                    raise WorkflowError("Linked Git metadata must be a regular file")
                continue
            lower = name.lower()
            if lower in _SECRET_NAMES or lower.endswith(_SECRET_SUFFIXES):
                raise WorkflowError("Credential-shaped source file is refused: " + rel)
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise WorkflowError("Project contains symlink or special file: " + rel)
            if len(result) >= MAX_FILES or info.st_size > MAX_TOTAL_BYTES - total:
                raise WorkflowError("Project source exceeds snapshot bounds")
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
            try:
                fd = os.open(path, flags)
            except OSError as exc:
                raise WorkflowError("Project changed during snapshot: " + rel) from exc
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
                    info.st_dev,
                    info.st_ino,
                ):
                    raise WorkflowError("Project changed during snapshot: " + rel)
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    data = stream.read(MAX_TOTAL_BYTES - total + 1)
            finally:
                os.close(fd)
            total += len(data)
            if total > MAX_TOTAL_BYTES:
                raise WorkflowError("Project source exceeds snapshot bounds")
            result.append((rel, data, stat.S_IMODE(info.st_mode) & 0o777))
    return root, root_info, result


def _tree_hash(entries):
    payload = [
        {"path": p, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "mode": mode}
        for p, data, mode in entries
    ]
    return hashlib.sha256(_canonical(payload)).hexdigest(), payload


def capture_baseline(source_root, artifact_path, generated=()):
    """Create a write-once baseline manifest; return its digest for trusted state."""
    generated = _normalize_generated(generated)
    root, info, entries = _entries(source_root, generated)
    tree_sha, rows = _tree_hash(entries)
    artifact = Path(artifact_path)
    if not artifact.is_absolute() or not artifact.parent.is_dir():
        raise WorkflowError("Baseline artifact requires an absolute path and existing parent")
    parent = artifact.parent.resolve(strict=True)
    target = parent / artifact.name
    if target.exists() or target.is_symlink() or target.is_relative_to(root):
        raise WorkflowError("Baseline artifact must be new and outside project source")
    doc = {
        "schema": SCHEMA,
        "excluded_generated": generated,
        "source_identity": {"device": info.st_dev, "inode": info.st_ino},
        "tree_sha256": tree_sha,
        "entries": rows,
    }
    doc["manifest_sha256"] = hashlib.sha256(_canonical(doc)).hexdigest()
    encoded = _canonical(doc) + b"\n"
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise WorkflowError("Baseline manifest exceeds size bound")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o400)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {
        "manifest_sha256": doc["manifest_sha256"],
        "tree_sha256": tree_sha,
        "source_identity": doc["source_identity"],
        "artifact": str(target),
    }


def _load_baseline(path, expected_digest):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_MANIFEST_BYTES:
        raise WorkflowError("Baseline artifact is missing, symlinked, or oversized")
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise WorkflowError("Baseline artifact is malformed") from exc
    if not isinstance(doc, dict) or set(doc) != {
        "schema",
        "excluded_generated",
        "source_identity",
        "tree_sha256",
        "entries",
        "manifest_sha256",
    }:
        raise WorkflowError("Baseline artifact schema mismatch")
    claimed = doc["manifest_sha256"]
    unsigned = dict(doc)
    del unsigned["manifest_sha256"]
    if (
        doc["schema"] != SCHEMA
        or claimed != expected_digest
        or hashlib.sha256(_canonical(unsigned)).hexdigest() != claimed
        or not isinstance(doc["entries"], list)
        or not _HEX.fullmatch(doc["tree_sha256"])
        or doc["excluded_generated"] != _normalize_generated(doc["excluded_generated"])
    ):
        raise WorkflowError("Baseline artifact digest or binding mismatch")
    return doc


def _recheck_source(root, baseline):
    actual_root, info, entries = _entries(root, baseline["excluded_generated"])
    tree_sha, rows = _tree_hash(entries)
    if (
        baseline["source_identity"] != {"device": info.st_dev, "inode": info.st_ino}
        or tree_sha != baseline["tree_sha256"]
        or rows != baseline["entries"]
    ):
        raise WorkflowError("Project source changed since trusted baseline")
    return actual_root, entries, tree_sha


def _write_copy(entries, dest):
    dest.mkdir(mode=0o700)
    for rel, data, mode in entries:
        target = dest.joinpath(*rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        target.chmod(mode)


def _candidate_hash(root):
    _r, _info, entries = _entries(root)
    return _tree_hash(entries)[0]


def prepare_and_validate(
    *,
    source_root,
    baseline_artifact,
    trusted_baseline_sha256,
    bundle,
    destination,
    allowed_paths,
    trusted_commands,
    timeout_seconds=120,
):
    """Stage verified bundle into a copied project and run trusted offline checks.

    Commands never come from the builder bundle. The source remains untouched;
    candidate output is a new directory outside the source. `.git` metadata is
    omitted, so commands requiring Git history must be adapted or refused.
    """
    baseline = _load_baseline(baseline_artifact, trusted_baseline_sha256)
    root, entries, source_hash = _recheck_source(source_root, baseline)
    if not isinstance(timeout_seconds, int | float) or not 0 < timeout_seconds <= MAX_TIMEOUT:
        raise WorkflowError("Validation timeout outside bounds")
    if (
        not isinstance(trusted_commands, list | tuple)
        or not trusted_commands
        or len(trusted_commands) > MAX_COMMANDS
    ):
        raise WorkflowError("A bounded trusted validation command list is required")
    commands = []
    for argv in trusted_commands:
        if (
            not isinstance(argv, list | tuple)
            or not argv
            or not all(isinstance(part, str) and part and "\x00" not in part for part in argv)
            or not Path(argv[0]).is_absolute()
            or not Path(argv[0]).is_file()
            or not os.access(argv[0], os.X_OK)
        ):
            raise WorkflowError("Validation commands must use available absolute executables")
        commands.append(list(argv))
    dest_input = Path(destination)
    if not dest_input.is_absolute() or not dest_input.parent.is_dir():
        raise WorkflowError("Candidate destination requires an absolute path and existing parent")
    parent = dest_input.parent.resolve(strict=True)
    dest = parent / dest_input.name
    if dest.exists() or dest.is_symlink() or dest == root or dest.is_relative_to(root):
        raise WorkflowError("Candidate destination must be new and outside source")

    overlay = parent / ("." + dest.name + ".bundle")
    for item in bundle.get("files", []) if isinstance(bundle, dict) else []:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            if ".git" in PurePosixPath(item["path"]).parts:
                raise WorkflowError("Builder bundle cannot modify Git metadata")
    staged = stage_bundle(root, bundle, overlay, allowed_paths)
    try:
        _recheck_source(root, baseline)
        _write_copy(entries, dest)
        for rel in staged["staged_paths"]:
            src = overlay.joinpath(*rel.split("/"))
            dst = dest.joinpath(*rel.split("/"))
            dst.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(src.read_bytes())
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(overlay, ignore_errors=True)

    candidate_sha = _candidate_hash(dest)
    evidence = {
        "schema": "engine-builder-project-validation/v1",
        "workspace": str(dest),
        "source_snapshot_sha256": source_hash,
        "candidate_snapshot_sha256": candidate_sha,
        "baseline_manifest_sha256": baseline["manifest_sha256"],
        "staged_paths": staged["staged_paths"],
        "records": [],
        "validation_status": "refused",
        "validation_complete": False,
        "validation_passed": False,
    }
    # Verify real network isolation before running any command.
    if not _network_boundary_available():
        evidence["refusal_reason"] = "bubblewrap network namespace unavailable"
        return evidence
    safe_env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
    }
    deadline = time.monotonic() + timeout_seconds
    for argv in commands:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            evidence["refusal_reason"] = "validation deadline expired"
            return evidence
        wrapped = sandbox_command(
            argv,
            dest,
            dest / "__no_work_item__",
            hidden_roots=[Path.home(), Path("/run/user")],
            writable_source=False,
        )
        wrapped.insert(1, "--unshare-net")
        try:
            completed = subprocess.run(
                wrapped,
                cwd=dest,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=remaining,
                env=safe_env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            evidence["records"].append({"argv": argv, "exit_code": None, "timed_out": True})
            evidence["refusal_reason"] = "validation command timed out"
            return evidence
        evidence["records"].append(
            {
                "argv": argv,
                "exit_code": completed.returncode,
                "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
            }
        )
        if completed.returncode != 0:
            evidence["validation_status"] = "failed"
            evidence["validation_complete"] = True
            return evidence
    _recheck_source(root, baseline)
    if _candidate_hash(dest) != candidate_sha:
        raise WorkflowError("Candidate changed during isolated validation")
    evidence["validation_status"] = "complete"
    evidence["validation_complete"] = True
    evidence["validation_passed"] = bool(evidence["records"])
    return evidence


def recheck_validation(*, source_root, baseline_artifact, trusted_baseline_sha256, candidate_root, evidence):
    """Recompute source/candidate bindings after validation; no Engine authority."""
    baseline = _load_baseline(baseline_artifact, trusted_baseline_sha256)
    _root, _entries0, source_sha = _recheck_source(source_root, baseline)
    candidate_sha = _candidate_hash(candidate_root)
    if (
        not isinstance(evidence, dict)
        or evidence.get("source_snapshot_sha256") != source_sha
        or evidence.get("candidate_snapshot_sha256") != candidate_sha
        or evidence.get("baseline_manifest_sha256") != baseline["manifest_sha256"]
        or evidence.get("validation_status") != "complete"
        or evidence.get("validation_complete") is not True
        or evidence.get("validation_passed") is not True
        or not isinstance(evidence.get("records"), list)
        or not evidence["records"]
        or any(
            not isinstance(r, dict)
            or r.get("exit_code") != 0
            or r.get("timed_out") is True
            or not isinstance(r.get("argv"), list)
            or any(
                not isinstance(r.get(field), str) or not _HEX.fullmatch(r[field])
                for field in ("stdout_sha256", "stderr_sha256")
            )
            for r in evidence["records"]
        )
    ):
        raise WorkflowError("Validation evidence does not bind to current source and candidate")
    return {
        "baseline_manifest_sha256": baseline["manifest_sha256"],
        "source_snapshot_sha256": source_sha,
        "candidate_snapshot_sha256": candidate_sha,
        "validation_records": len(evidence["records"]),
        "validation_status": "complete",
        "validation_passed": True,
    }


def accept_t3_builder_return(
    *,
    assistant_text,
    job,
    task_id,
    supervisor_receipt,
    source_root,
    baseline_artifact,
    trusted_baseline_sha256,
    destination,
    allowed_paths,
    trusted_commands,
    timeout_seconds=120,
    allow_configured_only=False,
):
    """Bind a received T3 builder bundle to a baseline and isolated validation.

    The receipt must come independently from the managed supervisor. A
    configured-only receipt is preserved as such and is accepted for staging
    only when an explicit caller policy enables it; it is never upgraded to
    execution evidence. This helper only returns a pending artifact; callers
    must retain baseline/receipt digests in trusted coordinator state and must
    not apply this candidate to the live checkout.
    """
    from builder_artifact_contract import decode_builder_artifact_return

    spec = job.get("spec", {}) if isinstance(job, dict) else {}
    evidence_kind = supervisor_receipt.get("model_evidence") if isinstance(supervisor_receipt, dict) else None
    configured_model = (
        supervisor_receipt.get("configured_model") if isinstance(supervisor_receipt, dict) else None
    )
    executed_model = (
        supervisor_receipt.get("executed_model") if isinstance(supervisor_receipt, dict) else None
    )
    model_for_wire = executed_model if evidence_kind == "executed" else configured_model
    if (
        not isinstance(job, dict)
        or not isinstance(supervisor_receipt, dict)
        or supervisor_receipt.get("state") != "completed"
        or supervisor_receipt.get("job_id") != job.get("job_id")
        or supervisor_receipt.get("task_id") != task_id
        or supervisor_receipt.get("configured_model") != spec.get("model")
        or not isinstance(supervisor_receipt.get("validated_utc"), str)
        or not _UTC.fullmatch(supervisor_receipt["validated_utc"])
        or supervisor_receipt.get("summary") != assistant_text
        or evidence_kind not in ("executed", "configured_only")
        or (evidence_kind == "executed" and executed_model != spec.get("model"))
        or (evidence_kind == "configured_only" and (executed_model is not None or not allow_configured_only))
    ):
        raise WorkflowError("T3 model evidence is missing, inconsistent, or not permitted by policy")
    source_packet = spec.get("builder_source_packet")
    if source_packet is not None:
        # Preserve the original receipt comparison above. Normalize only
        # after its identity is checked, deriving all hashes locally from
        # the immutable job packet rather than from model assertions.
        from builder_source_packet import normalize_builder_artifact_wire

        assistant_text = normalize_builder_artifact_wire(assistant_text, job, source_packet)
    decoded = decode_builder_artifact_return(
        assistant_text=assistant_text,
        job=job,
        task_id=task_id,
        executed_model=model_for_wire,
    )
    if decoded["verdict"] != "PASS":
        raise WorkflowError("Builder result verdict does not authorize candidate intake")
    evidence = prepare_and_validate(
        source_root=source_root,
        baseline_artifact=baseline_artifact,
        trusted_baseline_sha256=trusted_baseline_sha256,
        bundle={"files": decoded["files"]},
        destination=destination,
        allowed_paths=allowed_paths,
        trusted_commands=trusted_commands,
        timeout_seconds=timeout_seconds,
    )
    if (
        evidence.get("validation_status") != "complete"
        or evidence.get("validation_complete") is not True
        or evidence.get("validation_passed") is not True
    ):
        raise WorkflowError("Builder candidate validation did not complete successfully")
    binding = {
        "schema": "engine-t3-builder-candidate-binding/v1",
        "task_id": decoded["task_id"],
        "job_id": decoded["job_id"],
        "candidate_id": decoded["candidate_id"],
        "plan_revision_hash": decoded["plan_revision_hash"],
        "configured_model": configured_model,
        "executed_model": executed_model,
        "model_evidence": evidence_kind,
        "model_evidence_source": "managed_supervisor_receipt",
        "supervisor_validated_utc": supervisor_receipt["validated_utc"],
        "bundle_sha256": decoded["bundle_sha256"],
        "baseline_manifest_sha256": evidence["baseline_manifest_sha256"],
        "source_snapshot_sha256": evidence["source_snapshot_sha256"],
        "candidate_snapshot_sha256": evidence["candidate_snapshot_sha256"],
    }
    evidence["builder_binding"] = binding
    evidence["builder_binding_sha256"] = hashlib.sha256(_canonical(binding)).hexdigest()
    return evidence


def recheck_t3_builder_return(
    *, source_root, baseline_artifact, trusted_baseline_sha256, candidate_root, evidence, expected_binding
):
    """Recheck artifact, source, candidate and caller-supplied T3 job identity."""
    binding = evidence.get("builder_binding") if isinstance(evidence, dict) else None
    if (
        not isinstance(binding, dict)
        or binding != expected_binding
        or evidence.get("builder_binding_sha256") != hashlib.sha256(_canonical(binding)).hexdigest()
    ):
        raise WorkflowError("T3 builder artifact provenance binding mismatch")
    result = recheck_validation(
        source_root=source_root,
        baseline_artifact=baseline_artifact,
        trusted_baseline_sha256=trusted_baseline_sha256,
        candidate_root=candidate_root,
        evidence=evidence,
    )
    if (
        result["baseline_manifest_sha256"] != binding.get("baseline_manifest_sha256")
        or result["source_snapshot_sha256"] != binding.get("source_snapshot_sha256")
        or result["candidate_snapshot_sha256"] != binding.get("candidate_snapshot_sha256")
    ):
        raise WorkflowError("T3 builder artifact no longer matches validated snapshot")
    return {**result, "builder_binding_sha256": evidence["builder_binding_sha256"]}
