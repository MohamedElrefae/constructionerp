"""Fail-closed intake for a proposed builder file bundle.

This is a staging primitive only. It does not run validation, apply changes to
the source checkout, or establish that a candidate is safe to merge.
"""

import base64
import binascii
import errno
import hashlib
import os
import shutil
import stat
from pathlib import Path, PurePosixPath

from core import WorkflowError

MAX_FILES = 128
MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 4_000_000
MAX_PATH_LENGTH = 240
_HEX = frozenset("0123456789abcdef")


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _valid_hash(value, *, nullable=False):
    if nullable and value is None:
        return True
    return isinstance(value, str) and len(value) == 64 and all(character in _HEX for character in value)


def _normalize_relative_path(value):
    if not isinstance(value, str) or not value or len(value) > MAX_PATH_LENGTH:
        raise WorkflowError("Invalid bundle path")
    if "\\" in value or "\x00" in value:
        raise WorkflowError("Invalid bundle path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise WorkflowError("Bundle path must be normalized and relative")
    normalized = path.as_posix()
    if normalized != value or normalized.startswith("./"):
        raise WorkflowError("Bundle path must be normalized and relative")
    return normalized


def _source_state(root, relative_path):
    """Hash a bounded regular file through no-follow directory descriptors."""
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise WorkflowError("Safe no-follow path access is unavailable")
    parts = relative_path.split("/")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            if index != len(parts) - 1:
                flags |= os.O_DIRECTORY
            try:
                next_fd = os.open(part, flags, dir_fd=fd)
            except FileNotFoundError:
                return False, None
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise WorkflowError("Symlink or non-directory in source path: " + relative_path) from None
                raise WorkflowError("Source path cannot be opened: " + relative_path) from None
            os.close(fd)
            fd = next_fd
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
            raise WorkflowError("Bundle target is not a bounded regular file: " + relative_path)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            content = stream.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise WorkflowError("Base file exceeds size limit: " + relative_path)
        return True, _sha256(content)
    finally:
        os.close(fd)


def stage_bundle(base_root, bundle, destination, allowed_paths):
    """Validate and stage a synthetic file bundle into a new, separate directory.

    Each file item contains ``path``, ``base_sha256`` (null for a new file),
    ``content_base64`` and ``content_sha256``. ``allowed_paths`` uses exact
    names or slash-terminated directory prefixes. No source files are modified.
    """
    root = Path(base_root).resolve(strict=True)
    dest_input = Path(destination)
    if not dest_input.is_absolute():
        raise WorkflowError("Staging destination must be absolute")
    if not dest_input.parent.exists() or not dest_input.parent.is_dir():
        raise WorkflowError("Staging destination parent must already exist")
    parent = dest_input.parent.resolve(strict=True)
    dest = parent / dest_input.name
    if dest.exists() or dest.is_symlink():
        raise WorkflowError("Staging destination already exists")
    if dest == root or root in dest.parents or dest in root.parents:
        raise WorkflowError("Staging destination must be separate from source root")
    if not isinstance(bundle, dict) or set(bundle) != {"files"}:
        raise WorkflowError("Malformed file bundle")
    files = bundle["files"]
    if not isinstance(files, list) or not files or len(files) > MAX_FILES:
        raise WorkflowError("Bundle file count outside limits")
    if not isinstance(allowed_paths, list | tuple) or not allowed_paths:
        raise WorkflowError("Explicit allowed paths are required")
    allowed = tuple(_normalize_relative_path_prefix(item) for item in allowed_paths)

    validated = []
    seen = set()
    total = 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "base_sha256",
            "content_base64",
            "content_sha256",
        }:
            raise WorkflowError("Malformed bundle file entry")
        path = _normalize_relative_path(item["path"])
        if path in seen:
            raise WorkflowError("Duplicate bundle path: " + path)
        seen.add(path)
        if not any(
            path == prefix or (prefix.endswith("/") and path.startswith(prefix)) for prefix in allowed
        ):
            raise WorkflowError("Bundle path is outside allowed paths: " + path)
        expected_base = item["base_sha256"]
        if not _valid_hash(expected_base, nullable=True):
            raise WorkflowError("Invalid base content hash: " + path)
        encoded = item["content_base64"]
        if not isinstance(encoded, str):
            raise WorkflowError("Bundle content must be base64 text: " + path)
        if len(encoded) > 4 * ((MAX_FILE_BYTES + 2) // 3):
            raise WorkflowError("Bundle file exceeds size limit: " + path)
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise WorkflowError("Invalid base64 content: " + path) from exc
        if len(content) > MAX_FILE_BYTES:
            raise WorkflowError("Bundle file exceeds size limit: " + path)
        total += len(content)
        if total > MAX_TOTAL_BYTES:
            raise WorkflowError("Bundle exceeds total size limit")
        if not _valid_hash(item["content_sha256"]) or _sha256(content) != item["content_sha256"]:
            raise WorkflowError("Content hash mismatch: " + path)
        exists, actual_base = _source_state(root, path)
        if expected_base is None:
            if exists:
                raise WorkflowError("New-file bundle path already exists: " + path)
        elif not exists or actual_base != expected_base:
            raise WorkflowError("Base content hash mismatch: " + path)
        validated.append((path, content))

    # The destination is created only after the entire bundle has passed checks.
    dest.mkdir(mode=0o700)
    try:
        for path, content in validated:
            target = dest.joinpath(*path.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(target, flags, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    return {
        "workspace": str(dest),
        "staged_paths": [path for path, _ in validated],
        "validation_complete": False,
        "validation_passed": False,
        "status": "staged_for_review",
    }


def _normalize_relative_path_prefix(value):
    if not isinstance(value, str) or not value:
        raise WorkflowError("Invalid allowed path")
    is_prefix = value.endswith("/")
    normalized = _normalize_relative_path(value[:-1] if is_prefix else value)
    return normalized + ("/" if is_prefix else "")
