"""Local canonical serialization, safe artifact writes and strict root handling."""

import fcntl
import hashlib
import json
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


class WorkflowError(RuntimeError):
    pass


class ProvenNoLaunch(WorkflowError):
    """The launcher proved that no remote or local task was started."""


class PreconditionError(WorkflowError):
    pass


class ValidationError(WorkflowError):
    pass


class DuplicateKeyConflict(WorkflowError):
    pass


class RecoveryError(WorkflowError):
    pass


class GrantReconciliationRequired(WorkflowError):
    pass


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def bytes_hash(value):
    return hashlib.sha256(value).hexdigest()


def relative(path):
    p = PurePosixPath(path)
    if (
        not path
        or p.is_absolute()
        or ".." in p.parts
        or "\\" in path
        or "\x00" in path
        or p.as_posix() != path
        or path == "."
    ):
        raise WorkflowError("Unsafe relative path")
    return p


def within(root, name, allow_leaf_symlink=False):
    root = Path(root).resolve()
    p = root / relative(name)
    cursor = root
    parts = p.relative_to(root).parts
    for index, part in enumerate(parts):
        cursor /= part
        if cursor.is_symlink() and not (allow_leaf_symlink and index == len(parts) - 1):
            raise WorkflowError("Symlink path escape refused")
    return p


def atomic_write(path, content, immutable=False):
    path = Path(path)
    if path.is_symlink():
        raise WorkflowError("Symlink output refused")
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        if path.read_bytes() != content:
            raise WorkflowError("Immutable artifact collision")
        return
    fd, name = tempfile.mkstemp(prefix=".workflow-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        if immutable:
            try:
                os.link(name, path)
            except FileExistsError:
                if path.read_bytes() != content:
                    raise WorkflowError("Immutable artifact collision")
            os.unlink(name)
        else:
            os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_json(path, value, immutable=False):
    atomic_write(path, canonical(value) + b"\n", immutable)


@contextmanager
def execution_lock(path, timeout=0):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise WorkflowError("Another workflow writer holds the lock") from exc
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)

# --- Host-execution guards (fail-closed acknowledgments) -------------------
# Acknowledgment tokens are deliberate operator opt-ins, never containment.
NATIVE_DISPATCH_ENV = "ENGINE_NATIVE_DISPATCH"
NATIVE_DISPATCH_VALUE = "allow-native-host-access"
HOST_EXECUTION_ENV = "ENGINE_HOST_EXECUTION"
HOST_EXECUTION_VALUE = "allow-host-execution"


def native_dispatch_allowed(launcher) -> bool:
    """True only when an isolated launcher is present or the operator acked."""
    return bool(launcher) or (
        os.environ.get(NATIVE_DISPATCH_ENV, "").strip().lower() == NATIVE_DISPATCH_VALUE
    )


def require_native_dispatch(launcher, what="native worker dispatch") -> None:
    """Refuse a native (unisolated) spawn unless explicitly acknowledged."""
    if native_dispatch_allowed(launcher):
        return
    raise WorkflowError(
        f"{what} disabled: refusing to launch a worker on the host. "
        "No isolated backend is installed in this build; export "
        f"{NATIVE_DISPATCH_ENV}={NATIVE_DISPATCH_VALUE} for deliberate "
        "host-risk work (no network containment)."
    )


def host_execution_allowed() -> bool:
    return os.environ.get(HOST_EXECUTION_ENV, "").strip().lower() == HOST_EXECUTION_VALUE


def require_host_execution(what) -> None:
    """Refuse real-bench/host execution unless explicitly acknowledged."""
    if host_execution_allowed():
        return
    raise WorkflowError(
        f"{what} disabled: refusing to execute on the host. Export "
        f"{HOST_EXECUTION_ENV}={HOST_EXECUTION_VALUE} to acknowledge that this "
        "operation executes against a real host (bench/site)."
    )
