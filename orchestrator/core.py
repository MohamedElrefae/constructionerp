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
