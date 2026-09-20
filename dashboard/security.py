"""Security and descriptor-relative traversal utilities for Civil Engineer Dashboard."""

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from dashboard.config import FRAPPE_BENCH_ROOT, STAGE4_AUTHORITATIVE_MANIFEST_PATH


class SecurityError(Exception):
    """Raised when security boundaries, permissions, or isolation rules are violated."""

    pass


def open_descriptor_relative(
    root_dir: Path | str,
    rel_path: Path | str,
    strict_permissions: bool = True,
    is_dir: bool = False,
) -> tuple[int, list[int], dict[str, Any]]:
    """Unified descriptor-relative path traversal using openat with O_NOFOLLOW.

    Validates starting root and each intermediate directory relative to its verified parent.
    In strict_permissions mode, asserts trusted owner (current UID or 0) and (st_mode & 0o022) == 0.
    In non-strict mode, collects integrity warnings for group/world writability without raising.

    If is_dir is True, the final component is opened as a directory and verified with S_ISDIR.
    If is_dir is False, the final component is opened as a regular file and verified with S_ISREG.

    Returns:
        (final_fd, list_of_opened_dir_fds_to_close, integrity_info)
    """
    root_path = Path(root_dir).resolve()
    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts:
        raise SecurityError("Invalid relative path traversal")

    integrity_info: dict[str, Any] = {
        "integrity_status": "verified",
        "integrity_warnings": [],
        "root_permissions": None,
        "file_permissions": None,
        "directory_permissions": {},
    }

    opened_dir_fds: list[int] = []

    # 1. Open starting root descriptor
    try:
        root_fd = os.open(str(root_path), os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0))
    except OSError as e:
        raise SecurityError(f"Cannot open root directory: {e}")
    opened_dir_fds.append(root_fd)

    st_root = os.fstat(root_fd)
    if not stat.S_ISDIR(st_root.st_mode):
        for fd in reversed(opened_dir_fds):
            os.close(fd)
        raise SecurityError(f"Root path '{root_path}' is not a directory")

    if st_root.st_uid not in (os.getuid(), 0):
        for fd in reversed(opened_dir_fds):
            os.close(fd)
        raise SecurityError(f"Root path '{root_path}' owned by untrusted UID {st_root.st_uid}")

    integrity_info["root_permissions"] = oct(stat.S_IMODE(st_root.st_mode))
    if st_root.st_mode & 0o022:
        msg = f"Root directory '{root_path.name}' has unsafe permissions {oct(stat.S_IMODE(st_root.st_mode))}"
        integrity_info["integrity_warnings"].append(msg)
        integrity_info["integrity_status"] = "unverified_permissions"
        if strict_permissions:
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError("evidence unavailable: unsafe permissions")

    curr_fd = root_fd
    parts = rel.parts
    if not parts:
        for fd in reversed(opened_dir_fds):
            os.close(fd)
        raise SecurityError("Empty relative path")

    dir_components = parts[:-1]
    final_name = parts[-1]

    # 2. Traverse child directories descriptor-relatively
    for comp in dir_components:
        if comp in (".", "..") or "/" in comp or "\\" in comp:
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError(f"Invalid directory component: {comp!r}")
        try:
            child_fd = os.open(
                comp,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                dir_fd=curr_fd,
            )
        except OSError as e:
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError(f"Failed to open directory '{comp}': {e}")
        opened_dir_fds.append(child_fd)

        st_comp = os.fstat(child_fd)
        if not stat.S_ISDIR(st_comp.st_mode):
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError(f"Component '{comp}' is not a directory")

        if st_comp.st_uid not in (os.getuid(), 0):
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError(f"Directory '{comp}' owned by untrusted UID {st_comp.st_uid}")

        perm_str = oct(stat.S_IMODE(st_comp.st_mode))
        integrity_info["directory_permissions"][comp] = perm_str
        if st_comp.st_mode & 0o022:
            msg = f"Directory component '{comp}' has unsafe permissions {perm_str}"
            integrity_info["integrity_warnings"].append(msg)
            integrity_info["integrity_status"] = "unverified_permissions"
            if strict_permissions:
                for fd in reversed(opened_dir_fds):
                    os.close(fd)
                raise SecurityError("evidence unavailable: unsafe permissions")

        curr_fd = child_fd

    # 3. Open final descriptor relative to parent directory
    if final_name in (".", "..") or "/" in final_name or "\\" in final_name:
        for fd in reversed(opened_dir_fds):
            os.close(fd)
        raise SecurityError(f"Invalid target name: {final_name!r}")

    if is_dir:
        try:
            target_fd = os.open(
                final_name,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                dir_fd=curr_fd,
            )
        except OSError as e:
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError(f"Failed to open directory '{final_name}': {e}")
        opened_dir_fds.append(target_fd)

        st_final = os.fstat(target_fd)
        if not stat.S_ISDIR(st_final.st_mode):
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError(f"Target '{final_name}' is not a directory")

        if st_final.st_uid not in (os.getuid(), 0):
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError(f"Target directory '{final_name}' owned by untrusted UID {st_final.st_uid}")

        perm_str = oct(stat.S_IMODE(st_final.st_mode))
        integrity_info["directory_permissions"][final_name] = perm_str
        if st_final.st_mode & 0o022:
            msg = f"Target directory '{final_name}' has unsafe permissions {perm_str}"
            integrity_info["integrity_warnings"].append(msg)
            integrity_info["integrity_status"] = "unverified_permissions"
            if strict_permissions:
                for fd in reversed(opened_dir_fds):
                    os.close(fd)
                raise SecurityError("evidence unavailable: unsafe permissions")

        return target_fd, opened_dir_fds, integrity_info

    else:
        try:
            file_fd = os.open(
                final_name,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                dir_fd=curr_fd,
            )
        except OSError as e:
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError(f"Failed to open file '{final_name}': {e}")

        st_file = os.fstat(file_fd)
        if not stat.S_ISREG(st_file.st_mode):
            os.close(file_fd)
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError(f"Target '{final_name}' is not a regular file")

        if st_file.st_uid not in (os.getuid(), 0):
            os.close(file_fd)
            for fd in reversed(opened_dir_fds):
                os.close(fd)
            raise SecurityError(f"Target '{final_name}' owned by untrusted UID {st_file.st_uid}")

        file_perm = oct(stat.S_IMODE(st_file.st_mode))
        integrity_info["file_permissions"] = file_perm
        if st_file.st_mode & 0o022:
            msg = f"Target file '{final_name}' has unsafe permissions {file_perm}"
            integrity_info["integrity_warnings"].append(msg)
            integrity_info["integrity_status"] = "unverified_permissions"
            if strict_permissions:
                os.close(file_fd)
                for fd in reversed(opened_dir_fds):
                    os.close(fd)
                raise SecurityError("evidence unavailable: unsafe permissions")

        return file_fd, opened_dir_fds, integrity_info


MAX_MANIFEST_SIZE = 65536  # 64 KB limit


def read_authoritative_stage4_manifest() -> dict[str, Any]:
    """Read the Stage 4 manifest via descriptor-relative traversal and verify integrity."""
    manifest_path = STAGE4_AUTHORITATIVE_MANIFEST_PATH.resolve()
    bench_root = FRAPPE_BENCH_ROOT.resolve()

    # Invariant: containment under validated bench root
    try:
        rel_path = manifest_path.relative_to(bench_root)
    except ValueError as e:
        raise SecurityError(f"Manifest path '{manifest_path}' is outside bench root '{bench_root}'") from e

    file_fd, dir_fds, integrity_info = open_descriptor_relative(
        bench_root, rel_path, strict_permissions=False
    )
    try:
        st = os.fstat(file_fd)
        if st.st_size > MAX_MANIFEST_SIZE:
            raise SecurityError(
                f"Stage 4 manifest size ({st.st_size} bytes) exceeds maximum allowed size of {MAX_MANIFEST_SIZE} bytes"
            )

        chunks = []
        total_read = 0
        max_to_read = MAX_MANIFEST_SIZE + 1
        while total_read < max_to_read:
            chunk = os.read(file_fd, min(8192, max_to_read - total_read))
            if not chunk:
                break
            chunks.append(chunk)
            total_read += len(chunk)
        raw_bytes = b"".join(chunks)

        if len(raw_bytes) > MAX_MANIFEST_SIZE:
            raise SecurityError(f"Stage 4 manifest exceeds maximum allowed size of {MAX_MANIFEST_SIZE} bytes")

        computed_sha = hashlib.sha256(raw_bytes).hexdigest()

        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except Exception as exc:
            raise SecurityError(f"Malformed Stage 4 manifest JSON: {exc}") from exc

        # Strip internal site paths
        site_path = data.get("export_path", "")
        masked_path = re.sub(r"(?<![:/\w])/(?:[\w\.\-]+/)+[\w\.\-]+", "[PATH]", site_path)

        return {
            "status": "PARKED",
            "read_only": True,
            "zero_mutation_guarantee": True,
            "manifest_schema": data.get("schema", "construction-stage4-export-manifest/v1"),
            "manifest_sha256": computed_sha,
            "integrity_status": integrity_info["integrity_status"],
            "integrity_warnings": integrity_info["integrity_warnings"],
            "permissions": integrity_info["file_permissions"],
            "company": data.get("company", ""),
            "domain": data.get("domain", ""),
            "export_file": data.get("export_file", ""),
            "export_sha256": data.get("export_sha256", ""),
            "rows": data.get("rows", 0),
            "groups": data.get("groups", 0),
            "leaves": data.get("leaves", 0),
            "recorded_utc": data.get("recorded_utc", ""),
            "masked_export_path": masked_path,
        }
    finally:
        os.close(file_fd)
        for fd in reversed(dir_fds):
            try:
                os.close(fd)
            except OSError:
                pass
