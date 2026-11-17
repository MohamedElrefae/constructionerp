"""Test-only full-workspace bundle prototype with fail-closed offline validation.

This module is intentionally not wired to Engine, T3, or production dispatch.
It accepts only marked synthetic roots, stages into a new sibling workspace,
and reports validation as refused unless bubblewrap proves network isolation.
"""

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from builder_intake import stage_bundle
from core import WorkflowError
from sandbox import command as sandbox_command


SYNTHETIC_MARKER = ".builder-intake-synthetic-source"
SYNTHETIC_MARKER_VALUE = b"builder-intake-test-source/v1\n"
MAX_SOURCE_FILES = 10_000
MAX_SOURCE_BYTES = 64_000_000
MAX_COMMANDS = 32
MAX_TIMEOUT_SECONDS = 120
SANDBOX_BINARY = Path("/usr/bin/bwrap")


def _digest_snapshot(entries):
    payload = [{"path": path, "sha256": hashlib.sha256(data).hexdigest(), "mode": mode}
               for path, data, mode in entries]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _snapshot(root):
    entries = []
    total = 0
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        dirs.sort()
        files.sort()
        for name in list(dirs):
            path = current_path / name
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise WorkflowError("Synthetic source contains a non-directory entry")
        for name in files:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise WorkflowError("Synthetic source contains a symlink or special file: " + relative)
            if info.st_size > MAX_SOURCE_BYTES - total:
                raise WorkflowError("Synthetic source exceeds workspace bounds")
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
            except OSError:
                raise WorkflowError("Synthetic source changed during snapshot: " + relative) from None
            try:
                opened = os.fstat(fd)
                if (not stat.S_ISREG(opened.st_mode)
                        or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)):
                    raise WorkflowError("Synthetic source changed during snapshot: " + relative)
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    data = stream.read(MAX_SOURCE_BYTES - total + 1)
            finally:
                os.close(fd)
            total += len(data)
            if len(entries) >= MAX_SOURCE_FILES or total > MAX_SOURCE_BYTES:
                raise WorkflowError("Synthetic source exceeds workspace bounds")
            entries.append((relative, data, stat.S_IMODE(info.st_mode) & 0o777))
    return entries


def _network_boundary_available():
    if not SANDBOX_BINARY.is_file() or not os.access(SANDBOX_BINARY, os.X_OK):
        return False
    try:
        result = subprocess.run(
            [str(SANDBOX_BINARY), "--die-with-parent", "--unshare-net", "--ro-bind", "/", "/", "true"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"},
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _command_argv(commands):
    if not isinstance(commands, (list, tuple)) or not commands or len(commands) > MAX_COMMANDS:
        raise WorkflowError("A bounded trusted validation command list is required")
    result = []
    for command in commands:
        if (not isinstance(command, (list, tuple)) or not command
                or not all(isinstance(part, str) and part and "\x00" not in part for part in command)
                or not Path(command[0]).is_absolute()):
            raise WorkflowError("Validation commands must be explicit absolute argv arrays")
        executable = Path(command[0])
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise WorkflowError("Validation executable is unavailable: " + command[0])
        result.append(list(command))
    return result


def prepare_and_validate(base_root, bundle, destination, allowed_paths, trusted_commands,
                         *, timeout_seconds=60):
    """Build a disposable full copy and run supplied trusted commands offline.

    The source must contain the prototype's test-only marker. The bundle itself
    never supplies commands. Existing source bytes and modes are snapshotted,
    checked for drift, and copied; only then are verified bundle files overlaid.
    On unavailable isolation, the function returns a prepared candidate with
    validation explicitly refused and never claims success.
    """
    root = Path(base_root).resolve(strict=True)
    marker = root / SYNTHETIC_MARKER
    if not marker.is_file() or marker.is_symlink() or marker.read_bytes() != SYNTHETIC_MARKER_VALUE:
        raise WorkflowError("Prototype accepts marked synthetic source roots only")
    if (root / ".git").exists():
        raise WorkflowError("Synthetic prototype refuses repository roots")
    commands = _command_argv(trusted_commands)
    if not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise WorkflowError("Validation timeout outside bounds")

    dest_input = Path(destination)
    if not dest_input.is_absolute() or not dest_input.parent.is_dir():
        raise WorkflowError("Workspace destination must be absolute with an existing parent")
    parent = dest_input.parent.resolve(strict=True)
    dest = parent / dest_input.name
    if dest.exists() or dest.is_symlink() or dest == root or root in dest.parents or dest in root.parents:
        raise WorkflowError("Workspace destination must be new and separate from source")

    baseline = _snapshot(root)
    baseline_digest = _digest_snapshot(baseline)
    intermediate = parent / ("." + dest.name + ".bundle-" + uuid.uuid4().hex)
    staged = None
    try:
        staged = stage_bundle(root, bundle, intermediate, allowed_paths)
        if _digest_snapshot(_snapshot(root)) != baseline_digest:
            raise WorkflowError("Synthetic source changed during intake")

        dest.mkdir(mode=0o700)
        try:
            for relative, data, mode in baseline:
                target = dest.joinpath(*relative.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                target.write_bytes(data)
                target.chmod(mode)
            for relative in staged["staged_paths"]:
                source = Path(intermediate).joinpath(*relative.split("/"))
                target = dest.joinpath(*relative.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                target.write_bytes(source.read_bytes())
                target.chmod(0o600)
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)
            raise
    finally:
        if intermediate.exists():
            shutil.rmtree(intermediate, ignore_errors=True)

    candidate_digest = _digest_snapshot(_snapshot(dest))
    result = {
        "workspace": str(dest),
        "source_snapshot_sha256": baseline_digest,
        "candidate_snapshot_sha256": candidate_digest,
        "staged_paths": staged["staged_paths"],
        "validation_complete": False,
        "validation_passed": False,
        "validation_status": "refused",
        "records": [],
    }
    if not _network_boundary_available():
        result["refusal_reason"] = "bubblewrap network namespace unavailable"
        return result

    safe_env = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8", "PYTHONNOUSERSITE": "1"}
    bwrap = SANDBOX_BINARY
    deadline = time.monotonic() + timeout_seconds
    for index, argv in enumerate(commands):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result["refusal_reason"] = "validation deadline expired"
            return result
        wrapped = sandbox_command(
            argv,
            dest,
            dest / "__no_work_item__",
            hidden_roots=[Path.home(), Path("/run/user")],
            writable_source=False,
        )
        wrapped.insert(1, "--unshare-net")
        # The wrapper selected and built the exact executable path; ensure the
        # boundary binary did not change between probe and invocation.
        if not wrapped or Path(wrapped[0]).resolve() != Path(bwrap).resolve():
            raise WorkflowError("Offline sandbox executable changed")
        try:
            completed = subprocess.run(
                wrapped,
                cwd=dest,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=remaining,
                env=safe_env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            result["records"].append({"argv": argv, "exit_code": None, "timed_out": True})
            result["refusal_reason"] = "validation command timed out"
            return result
        result["records"].append({
            "argv": argv,
            "exit_code": completed.returncode,
            "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
        })
        if completed.returncode != 0:
            result["validation_status"] = "failed"
            result["validation_complete"] = True
            result["validation_passed"] = False
            return result

    if _digest_snapshot(_snapshot(root)) != baseline_digest:
        result["validation_status"] = "refused"
        result["refusal_reason"] = "source changed during validation"
        return result
    if _digest_snapshot(_snapshot(dest)) != candidate_digest:
        result["validation_status"] = "refused"
        result["refusal_reason"] = "candidate workspace changed during validation"
        return result
    result["validation_status"] = "complete"
    result["validation_complete"] = True
    result["validation_passed"] = bool(result["records"])
    return result
