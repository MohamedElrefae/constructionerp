"""Apply a hash-bound builder bundle to a clean dedicated Git checkout.

Standalone integration helper. It invokes the repository's native candidate
freeze and offline validation runner, but does not create Engine authority or
make Engine recheck a candidate rooted somewhere other than ``Engine.root``.
Callers must provide a disposable dedicated checkout and a trusted validation
command list; builder data never supplies commands.

This is an integration primitive, not a production safety boundary. It reduces
cross-user races by requiring caller-owned, non-group/world-writable checkout
directories, but it cannot defend against a concurrent process running as the
same user. If native validation fails or refuses to run, applied files remain
in the disposable checkout for inspection or removal; no PASS is synthesized.
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path, PurePosixPath

from builder_intake import stage_bundle
from candidates import recheck
from core import WorkflowError
from validation_runner import run as run_validation


def _git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), "-c", "core.fsmonitor=false",
         "-c", "core.hooksPath=/dev/null", *args], capture_output=True, check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1",
             "GIT_CONFIG_GLOBAL": "/dev/null"},
    )
    if result.returncode:
        raise WorkflowError("Git checkout precondition failed: " + args[0])
    return result.stdout.decode("utf-8", "strict").strip()


def _checkout_state(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise WorkflowError("Dedicated checkout must be an existing real directory")
    info = root.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
        raise WorkflowError("Dedicated checkout must be caller-owned and not writable by others")
    top = Path(_git(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != root.resolve(strict=True):
        raise WorkflowError("Dedicated checkout path must be the Git worktree root")
    git_meta = root / ".git"
    if git_meta.is_symlink() or not (git_meta.is_dir() or git_meta.is_file()):
        raise WorkflowError("Dedicated checkout Git metadata is missing or unsafe")
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise WorkflowError("Dedicated checkout must be clean before builder intake")
    return _git(root, "rev-parse", "HEAD"), _git(root, "branch", "--show-current")


def _apply_staged(checkout, staged_root, paths):
    """Atomically replace only preflighted regular files in the clean worktree."""
    targets = []
    for relative in paths:
        path = PurePosixPath(relative)
        if (not relative or "\\" in relative or "\x00" in relative
                or path.is_absolute() or path.as_posix() != relative
                or any(part in ("", ".", "..", ".git") for part in relative.split("/"))):
            raise WorkflowError("Unsafe builder artifact path")
        target = checkout.joinpath(*path.parts)
        cursor = checkout
        for part in path.parts[:-1]:
            cursor = cursor / part
            if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()):
                raise WorkflowError("Builder artifact parent is not a real directory: " + relative)
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise WorkflowError("Builder artifact target is not a regular file: " + relative)
        targets.append((relative, target))

    for relative, target in targets:
        source = staged_root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
        fd, temporary = tempfile.mkstemp(prefix=".builder-intake-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as output, source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(temporary, mode)
            # os.replace replaces a leaf symlink itself; it never follows it.
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def apply_builder_artifact(*, artifact, checkout, expected_base_commit,
                           expected_branch, allowed_paths, validation_commands,
                           evidence_directory, work_item_root, control_root,
                           timeout_seconds=600, generated=()):
    """Apply verified bundle files and run native freeze/validation.

    ``artifact`` is the decoded ``engine-builder-bundle/v1`` result (the object
    returned by ``decode_builder_artifact_return``). The checkout must already
    be a clean disposable Git worktree at the exact expected commit and branch.
    This function leaves the staged changes in that checkout for review even
    when native validation refuses or fails; inspect ``validation`` and never
    infer acceptance from the returned candidate binding alone.
    """
    checkout_input = Path(checkout)
    if checkout_input.is_symlink():
        raise WorkflowError("Dedicated checkout must not be a symlink")
    root = checkout_input.resolve(strict=True)
    base, branch = _checkout_state(root)
    if base != expected_base_commit or branch != expected_branch:
        raise WorkflowError("Dedicated checkout base or branch binding mismatch")
    if not isinstance(artifact, dict) or artifact.get("verdict") != "PASS":
        raise WorkflowError("A completed passing builder artifact is required")
    files = artifact.get("files")
    if not isinstance(files, list) or not files:
        raise WorkflowError("Builder artifact contains no file changes")
    if (not isinstance(validation_commands, list | tuple) or not validation_commands
            or len(validation_commands) > 32):
        raise WorkflowError("Trusted native validation commands are required")
    if generated:
        raise WorkflowError("Builder artifact application does not permit generated-path exclusions")
    # Intake recomputes content hashes, base hashes, allowlist membership and
    # no-follow source-path checks before any checkout file is modified.
    parent = Path(evidence_directory)
    if not parent.is_absolute() or not parent.is_dir() or parent.is_symlink():
        raise WorkflowError("Evidence directory must be an existing real directory")
    parent = parent.resolve(strict=True)
    if parent == root or parent.is_relative_to(root) or root.is_relative_to(parent):
        raise WorkflowError("Evidence directory must be separate from the checkout")
    expected_paths = {item.get("path") for item in files if isinstance(item, dict)}
    if len(expected_paths) != len(files) or None in expected_paths:
        raise WorkflowError("Builder artifact file list is malformed")
    with tempfile.TemporaryDirectory(prefix="builder-artifact-", dir=parent) as temporary:
        staged = Path(temporary) / "bundle"
        stage_bundle(root, {"files": files}, staged, allowed_paths)
        _apply_staged(root, staged, [item["path"] for item in files])
    actual_paths = set(_git(root, "diff", "--name-only", "-z", base).split("\0"))
    actual_paths.discard("")
    untracked = set(_git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    untracked.discard("")
    if actual_paths | untracked != expected_paths:
        raise WorkflowError("Checkout changes differ from the declared builder artifact scope")

    # Capture the exact native freeze and run the established offline runner.
    # It fails closed when bubblewrap network isolation is unavailable.
    spec = {
        "root": str(root), "base_commit": base, "branch": branch,
        "allowed_paths": list(allowed_paths), "generated": list(generated),
        "validation_commands": [list(argv) for argv in validation_commands],
        "work_item_root": str(Path(work_item_root).resolve(strict=True)),
        "control_root": str(Path(control_root).resolve(strict=True)),
    }
    if not isinstance(timeout_seconds, int | float) or not 0 < timeout_seconds <= 600:
        raise WorkflowError("Validation timeout outside bounds")
    validation = run_validation(spec, parent, time.monotonic() + timeout_seconds)
    binding_path = parent / "tested-candidate" / "binding.json"
    if not binding_path.is_file() or binding_path.is_symlink():
        raise WorkflowError("Native candidate binding was not created")
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    if not isinstance(binding, dict) or binding.get("manifest", {}).get("base_commit") != base:
        raise WorkflowError("Native candidate binding does not match the checkout base")
    recheck(root, binding["manifest"], generated)
    return {"checkout": str(root), "base_commit": base, "branch": branch,
            "candidate_binding": str(binding_path), "validation": validation,
            "engine_recheck_root": str(root),
            "engine_acceptance": "not_wired; Engine rechecks against Engine.root"}
