#!/usr/bin/env python3
"""Candidate installer scaffold; installation is deliberately disabled.

This root-only installer refuses existing destination files, requires a
root-owned hash allowlist prepared independently of the user staging tree,
requires pre-provisioned service accounts/groups, and copies no T3 runtime.
It never runs systemctl, creates the dispatch gate, changes dashboard unit
configuration, or calls a provider. Trusted file reads and destination writes
use descriptor-relative traversal. Root-concurrent filesystem mutation and
target-host rollback behavior still need independent review. Do not remove the
hard stop until target-host prerequisites and end-to-end verification have
been reviewed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import grp
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass


EXPECTED_FILES = frozenset({
    "opt/managed-supervisor/orchestrator/managed_supervisor_service.py",
    "opt/managed-supervisor/orchestrator/managed_supervisor_attestation.py",
    "opt/managed-supervisor/orchestrator/t3_supervisor.py",
    "opt/managed-supervisor/orchestrator/t3_supervisor_client.py",
    "opt/managed-supervisor/orchestrator/t3_transport.py",
    "opt/managed-supervisor/orchestrator/systemd/managed_netns.py",
    "opt/managed-supervisor/orchestrator/systemd/https_connect_broker.py",
    "opt/managed-supervisor/orchestrator/systemd/t3_private_proxy_runner.py",
    "opt/managed-supervisor/orchestrator/systemd/verify_managed_host.py",
    "opt/managed-supervisor/orchestrator/systemd/managed_supervisor_attestation_hook.py",
    "opt/managed-supervisor/orchestrator/systemd/managed_attestation_verifier.py",
    "etc/systemd/system/managed-attestation-verifier.service",
    "etc/systemd/system/managed-t3-netns.service",
    "etc/systemd/system/managed-t3-egress.service",
    "etc/systemd/system/managed-t3.service",
    "etc/systemd/system/managed-supervisor.service",
    "etc/tmpfiles.d/managed-supervisor-attestation.conf",
    "etc/tmpfiles.d/managed-attestation-verifier.conf",
})
MIN_FREE_BYTES = 16 * 1024 * 1024
INSTALLATION_ENABLED = False
STAGE_PRIVATE_FILES = frozenset({
    "etc/managed-supervisor/service.json",
    "etc/managed-supervisor/credentials/protocol-token",
    "etc/managed-dashboard/credentials/supervisor-token",
})


class InstallError(RuntimeError):
    pass


@dataclass(frozen=True)
class CreatedPath:
    path: Path
    device: int
    inode: int
    directory: bool
    ctime_ns: int = 0
    size: int = 0
    mode: int = 0
    uid: int = 0
    gid: int = 0


def _duplicate_key_pairs(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise InstallError("approval manifest contains duplicate keys")
        data[key] = value
    return data


def _read_protected_json(path: Path, *, require_root: bool, max_bytes=64 * 1024) -> dict:
    if not path.is_absolute() or not hasattr(os, "O_NOFOLLOW"):
        raise InstallError("approval manifest path must be absolute and no-follow capable")
    directory_fd = _open_absolute_directory(path.parent, require_root=require_root)
    try:
        fd = os.open(path.name, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW,
                     dir_fd=directory_fd)
    except OSError:
        raise InstallError("approval manifest cannot be opened safely") from None
    finally:
        os.close(directory_fd)
    try:
        metadata = os.fstat(fd)
        if (not stat.S_ISREG(metadata.st_mode)
                or (require_root and metadata.st_uid != 0)
                or metadata.st_mode & 0o022
                or metadata.st_size > max_bytes):
            raise InstallError("approval manifest ownership, mode, or size is unsafe")
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
            raw = stream.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise InstallError("approval manifest exceeds size bound")
        return json.loads(raw, object_pairs_hook=_duplicate_key_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise InstallError("approval manifest is not valid UTF-8 JSON") from None
    finally:
        os.close(fd)


def _check_trusted_ancestors(path: Path, *, require_root: bool) -> None:
    """Reject path traversal through untrusted ancestors before privileged I/O.

    The production target is rooted at /. Every ancestor must be a real
    directory owned by root and not writable by group/other. This prevents a
    non-root package producer from swapping a checked component. Root-level
    concurrent mutation remains outside this helper's threat model.
    """
    if not path.is_absolute():
        raise InstallError("path must be absolute")
    current = Path("/")
    for part in path.parts[1:]:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError:
            raise InstallError("path ancestor is missing or uninspectable") from None
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise InstallError("path ancestor is not a real directory")
        if require_root and metadata.st_uid != 0:
            raise InstallError("path ancestor is not root-owned")
        if metadata.st_mode & 0o022:
            raise InstallError("path ancestor is writable by group or other")


def _open_absolute_directory(path: Path, *, require_root: bool) -> int:
    """Open an absolute directory chain descriptor-relatively with no symlinks."""
    if not path.is_absolute() or ".." in path.parts or not hasattr(os, "O_NOFOLLOW"):
        raise InstallError("trusted directory path must be absolute and normalized")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        current_fd = os.open("/", flags)
    except OSError:
        raise InstallError("filesystem root cannot be opened safely") from None
    try:
        for component in path.parts[1:]:
            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except OSError:
                raise InstallError("trusted directory path is missing or contains a symlink") from None
            metadata = os.fstat(next_fd)
            if (not stat.S_ISDIR(metadata.st_mode)
                    or (require_root and metadata.st_uid != 0)
                    or metadata.st_mode & 0o022):
                os.close(next_fd)
                raise InstallError("trusted directory path has unsafe ownership or permissions")
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _read_stage_file(stage: Path, relative: str, *, require_root=True,
                     private: bool = False) -> bytes:
    if (relative not in EXPECTED_FILES | STAGE_PRIVATE_FILES
            or Path(relative).is_absolute() or ".." in Path(relative).parts):
        raise InstallError("requested stage path is outside the approved file set")
    directory_fd = _open_absolute_directory(stage, require_root=require_root)
    stage_metadata = os.fstat(directory_fd)
    if (require_root and stage_metadata.st_uid != 0) or stage_metadata.st_mode & 0o077:
        os.close(directory_fd)
        raise InstallError("stage directory must be root-owned and private (mode 0700)")
    try:
        parts = Path(relative).parts
        for component in parts[:-1]:
            try:
                child_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                                   getattr(os, "O_CLOEXEC", 0), dir_fd=directory_fd)
            except OSError:
                raise InstallError("staged package contains an unsafe directory component") from None
            metadata = os.fstat(child_fd)
            if ((require_root and metadata.st_uid != 0) or metadata.st_mode & 0o022):
                os.close(child_fd)
                raise InstallError("staged package directory ownership or mode is unsafe")
            os.close(directory_fd)
            directory_fd = child_fd
        try:
            fd = os.open(parts[-1], os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW,
                         dir_fd=directory_fd)
        except OSError:
            raise InstallError("staged package file cannot be opened safely") from None
    except OSError:
        raise InstallError("staged package file cannot be opened safely") from None
    finally:
        os.close(directory_fd)
    try:
        metadata = os.fstat(fd)
        if (not stat.S_ISREG(metadata.st_mode) or (require_root and metadata.st_uid != 0)
                or metadata.st_mode & (0o077 if private else 0o022)
                or metadata.st_size > 4 * 1024 * 1024):
            raise InstallError("staged package file ownership, mode, or size is unsafe")
        chunks = []
        remaining = 4 * 1024 * 1024 + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > 4 * 1024 * 1024:
            raise InstallError("staged package file exceeds size bound")
        return data
    finally:
        os.close(fd)


def approved_payload(stage: Path, manifest_path: Path, *, require_root=True) -> dict[str, bytes]:
    if stage.is_symlink() or not stage.is_dir():
        raise InstallError("stage directory is missing or a symlink")
    stage_metadata = stage.lstat()
    if (require_root and stage_metadata.st_uid != 0) or stage_metadata.st_mode & 0o077:
        raise InstallError("stage directory must be root-owned and private (mode 0700)")
    approval = _read_protected_json(manifest_path, require_root=require_root)
    if not isinstance(approval, dict) or set(approval) != EXPECTED_FILES:
        raise InstallError("approved hash manifest does not name the exact candidate file set")
    _check_trusted_ancestors(stage, require_root=require_root)
    staged_manifest = _read_protected_json(stage / "staged-files.sha256.json", require_root=require_root)
    if staged_manifest != approval:
        raise InstallError("staged hash list differs from the independently approved manifest")
    payload = {}
    for relative, expected_hash in approval.items():
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise InstallError("approved manifest has an invalid SHA-256 entry")
        data = _read_stage_file(stage, relative, require_root=require_root)
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise InstallError("staged file does not match approved SHA-256")
        payload[relative] = data
    return payload


def verify_accounts(*, dashboard_user: str, dashboard_group: str,
                    dashboard_uid: int, dashboard_gid: int,
                    lookup_user=pwd.getpwnam, lookup_group=grp.getgrnam) -> dict:
    names = (dashboard_user, "managed-supervisor", "managed-t3", "managed-egress")
    try:
        users = {name: lookup_user(name) for name in names}
        groups = {name: lookup_group(name) for name in (
            dashboard_group, "managed-dashboard", "managed-supervisor", "managed-t3-egress")}
    except KeyError as exc:
        raise InstallError(f"required pre-provisioned account/group is missing: {exc.args[0]}") from None
    if users[dashboard_user].pw_uid != dashboard_uid or groups[dashboard_group].gr_gid != dashboard_gid:
        raise InstallError("dashboard UID/GID differs from the staged configuration")
    if groups["managed-dashboard"].gr_gid != dashboard_gid:
        raise InstallError("managed-dashboard socket group must use the staged dashboard GID")
    service_uids = [users[name].pw_uid for name in (dashboard_user, "managed-supervisor", "managed-t3", "managed-egress")]
    if any(uid <= 0 for uid in service_uids) or len(set(service_uids)) != len(service_uids):
        raise InstallError("dashboard and service UIDs must be distinct, non-root identities")
    if users["managed-t3"].pw_gid != groups["managed-t3-egress"].gr_gid:
        t3_member = users["managed-t3"].pw_name in groups["managed-t3-egress"].gr_mem
        if not t3_member:
            raise InstallError("managed-t3 must be a member of the broker socket group")
    if users[dashboard_user].pw_gid != groups["managed-dashboard"].gr_gid:
        if dashboard_user not in groups["managed-dashboard"].gr_mem:
            raise InstallError("dashboard must already be a member of managed-dashboard; installer will not edit it")
    return {
        "dashboard_uid": users[dashboard_user].pw_uid,
        "dashboard_gid": groups[dashboard_group].gr_gid,
        "supervisor_uid": users["managed-supervisor"].pw_uid,
        "supervisor_gid": groups["managed-supervisor"].gr_gid,
        "t3_uid": users["managed-t3"].pw_uid,
        "egress_uid": users["managed-egress"].pw_uid,
        "egress_gid": groups["managed-t3-egress"].gr_gid,
    }


def _directory_policy(relative: Path, *, supervisor_gid: int,
                      dashboard_uid: int, dashboard_gid: int) -> tuple[int, int, int]:
    parts = relative.parts
    if parts in (("etc", "managed-supervisor"),
                 ("etc", "managed-supervisor", "credentials")):
        return 0, supervisor_gid, 0o750
    if parts == ("etc", "managed-dashboard", "credentials"):
        return dashboard_uid, dashboard_gid, 0o700
    return 0, 0, 0o755


def _open_root_fd(root: Path, *, require_root: bool) -> int:
    if not root.is_absolute() or not hasattr(os, "O_NOFOLLOW"):
        raise InstallError("installation root must be absolute and no-follow capable")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(root, flags)
    except OSError:
        raise InstallError("installation root cannot be opened safely") from None
    metadata = os.fstat(fd)
    if (not stat.S_ISDIR(metadata.st_mode)
            or (require_root and metadata.st_uid != 0)
            or metadata.st_mode & 0o022):
        os.close(fd)
        raise InstallError("installation root ownership or mode is unsafe")
    return fd


def _ensure_directory_at_root(root: Path, relative: Path, *, supervisor_gid: int,
                              dashboard_uid: int, dashboard_gid: int,
                              require_root: bool, created_dirs: list[CreatedPath]) -> None:
    """Create/check path components using dirfds and O_NOFOLLOW throughout."""
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise InstallError("installation directory is outside target root")
    parent_fd = _open_root_fd(root, require_root=require_root)
    current = Path()
    try:
        for part in relative.parts:
            current = current / part
            expected_uid, expected_gid, expected_mode = _directory_policy(
                current, supervisor_gid=supervisor_gid,
                dashboard_uid=dashboard_uid, dashboard_gid=dashboard_gid,
            )
            try:
                child_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                                   getattr(os, "O_CLOEXEC", 0), dir_fd=parent_fd)
            except FileNotFoundError:
                created = False
                recorded = False
                try:
                    os.mkdir(part, expected_mode, dir_fd=parent_fd)
                    created = True
                    child_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                                       getattr(os, "O_CLOEXEC", 0), dir_fd=parent_fd)
                    metadata = os.fstat(child_fd)
                    if created:
                        created_dirs.append(CreatedPath(
                            root / current, metadata.st_dev, metadata.st_ino, True,
                            mode=expected_mode, uid=expected_uid, gid=expected_gid))
                        recorded = True
                    os.fchown(child_fd, expected_uid, expected_gid)
                    os.fchmod(child_fd, expected_mode)
                except OSError as exc:
                    if created and not recorded:
                        try:
                            os.rmdir(part, dir_fd=parent_fd)
                        except OSError:
                            pass
                    raise InstallError("cannot safely create installation directory") from exc
            except OSError:
                raise InstallError("installation path contains an unsafe directory") from None
            metadata = os.fstat(child_fd)
            if (not stat.S_ISDIR(metadata.st_mode)
                    or (require_root and metadata.st_uid != expected_uid)
                    or metadata.st_gid != expected_gid
                    or stat.S_IMODE(metadata.st_mode) != expected_mode
                    or metadata.st_mode & 0o022):
                os.close(child_fd)
                raise InstallError("installation directory ownership or mode is unsafe")
            os.close(parent_fd)
            parent_fd = child_fd
    finally:
        os.close(parent_fd)


def _create_file_at_root(root: Path, relative: Path, data: bytes, *, uid: int, gid: int,
                         mode: int, require_root: bool, supervisor_gid: int,
                         dashboard_uid: int, dashboard_gid: int,
                         created_files: list[CreatedPath] | None = None) -> Path:
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise InstallError("installation file is outside target root")
    parent = relative.parent
    parent_fd = _open_root_fd(root, require_root=require_root)
    current = Path()
    try:
        for part in parent.parts:
            current = current / part
            child_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                               getattr(os, "O_CLOEXEC", 0), dir_fd=parent_fd)
            metadata = os.fstat(child_fd)
            expected_uid, expected_gid, expected_mode = _directory_policy(
                current, supervisor_gid=supervisor_gid,
                dashboard_uid=dashboard_uid, dashboard_gid=dashboard_gid,
            )
            if not stat.S_ISDIR(metadata.st_mode) or metadata.st_mode & 0o022:
                os.close(child_fd)
                raise InstallError("installation parent changed or is unsafe")
            if ((require_root and metadata.st_uid != expected_uid)
                    or metadata.st_gid != expected_gid
                    or stat.S_IMODE(metadata.st_mode) != expected_mode):
                os.close(child_fd)
                raise InstallError("installation parent ownership or mode changed")
            os.close(parent_fd)
            parent_fd = child_fd
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        try:
            fd = os.open(relative.name, flags, mode, dir_fd=parent_fd)
        except FileExistsError:
            raise InstallError(f"refusing to overwrite existing file: {root / relative}") from None
        complete = False
        try:
            os.fchown(fd, uid, gid)
            os.fchmod(fd, mode)
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise InstallError("short write while installing candidate")
                view = view[written:]
            os.fsync(fd)
            metadata = os.fstat(fd)
            identity = CreatedPath(
                root / relative, metadata.st_dev, metadata.st_ino, False,
                metadata.st_ctime_ns, metadata.st_size, stat.S_IMODE(metadata.st_mode),
                metadata.st_uid, metadata.st_gid,
            )
            complete = True
        finally:
            os.close(fd)
            if not complete:
                try:
                    os.unlink(relative.name, dir_fd=parent_fd)
                except OSError:
                    pass
        if created_files is not None:
            created_files.append(identity)
        os.fsync(parent_fd)
        return root / relative
    finally:
        os.close(parent_fd)


def _remove_at_root(root: Path, created: CreatedPath) -> bool:
    """Remove only the exact inode recorded as created by this transaction."""
    try:
        relative = created.path.relative_to(root)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            return False
        parent_fd = _open_root_fd(root, require_root=(os.geteuid() == 0))
        try:
            for part in relative.parent.parts:
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                                  getattr(os, "O_CLOEXEC", 0), dir_fd=parent_fd)
                os.close(parent_fd)
                parent_fd = next_fd
            metadata = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
            if (metadata.st_dev, metadata.st_ino) != (created.device, created.inode):
                return False
            if created.directory and (
                    not stat.S_ISDIR(metadata.st_mode)
                    or stat.S_IMODE(metadata.st_mode) != created.mode
                    or metadata.st_uid != created.uid or metadata.st_gid != created.gid):
                return False
            if (not created.directory and
                    (metadata.st_ctime_ns, metadata.st_size, stat.S_IMODE(metadata.st_mode),
                     metadata.st_uid, metadata.st_gid) !=
                    (created.ctime_ns, created.size, created.mode, created.uid, created.gid)):
                return False
            if created.directory:
                os.rmdir(relative.name, dir_fd=parent_fd)
            else:
                os.unlink(relative.name, dir_fd=parent_fd)
            os.fsync(parent_fd)
            return True
        finally:
            os.close(parent_fd)
    except OSError:
        return False


def _safe_token(path: Path, *, require_root=True) -> bytes:
    if not path.is_absolute() or not hasattr(os, "O_NOFOLLOW"):
        raise InstallError("MCP token source must be absolute and no-follow capable")
    directory_fd = _open_absolute_directory(path.parent, require_root=require_root)
    try:
        fd = os.open(path.name, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW,
                     dir_fd=directory_fd)
    except OSError:
        raise InstallError("MCP token source cannot be opened safely") from None
    finally:
        os.close(directory_fd)
    try:
        metadata = os.fstat(fd)
        if (not stat.S_ISREG(metadata.st_mode) or (require_root and metadata.st_uid != 0)
                or metadata.st_mode & 0o077 or metadata.st_size > 4096):
            raise InstallError("MCP token source ownership, mode, or size is unsafe")
        data = os.read(fd, 4097).strip()
        if len(data) < 20 or not data.isascii():
            raise InstallError("MCP token source must contain a bounded ASCII credential")
        return data + b"\n"
    finally:
        os.close(fd)


def install_candidate(stage: Path, manifest: Path, mcp_token_file: Path, *,
                      dashboard_user: str, dashboard_group: str,
                      target_root: Path = Path("/"), require_root=True,
                      account_lookup_user=pwd.getpwnam,
                      account_lookup_group=grp.getgrnam,
                      disk_usage=shutil.disk_usage) -> list[str]:
    """Install files only; never enable/start/reload units or modify dashboard config."""
    if not INSTALLATION_ENABLED:
        raise InstallError(
            "installation disabled: target-host prerequisites and end-to-end verification are incomplete"
        )
    if require_root and os.geteuid() != 0:
        raise InstallError("installation requires root")
    if not target_root.is_absolute() or target_root.is_symlink():
        raise InstallError("target root must be an absolute non-symlink directory")
    if require_root and target_root != Path("/"):
        raise InstallError("live installation target is fixed to /")
    _check_trusted_ancestors(target_root, require_root=require_root)
    # Validate all trust inputs before interpreting config or creating paths.
    payload = approved_payload(stage, manifest, require_root=require_root)
    mcp = _safe_token(mcp_token_file, require_root=require_root)
    identities = verify_accounts(
        dashboard_user=dashboard_user, dashboard_group=dashboard_group,
        dashboard_uid=_read_stage_config(stage)["client_uid"],
        dashboard_gid=_read_stage_config(stage)["socket_group_gid"],
        lookup_user=account_lookup_user, lookup_group=account_lookup_group,
    )
    service_config = _read_stage_config(stage)
    sup_uid, sup_gid = identities["supervisor_uid"], identities["supervisor_gid"]
    dashboard_uid = identities["dashboard_uid"]
    dashboard_group_gid = identities["dashboard_gid"]
    token = _read_stage_token(stage / "etc/managed-supervisor/credentials/protocol-token",
                              stage=stage, relative="etc/managed-supervisor/credentials/protocol-token",
                              require_root=require_root)
    dashboard_token = _read_stage_token(stage / "etc/managed-dashboard/credentials/supervisor-token",
                                        stage=stage, relative="etc/managed-dashboard/credentials/supervisor-token",
                                        require_root=require_root)
    if token != dashboard_token:
        raise InstallError("staged dashboard and supervisor protocol tokens differ")
    required_bytes = sum(len(value) for value in payload.values()) + len(mcp) + len(token) * 2
    free = disk_usage(target_root).free
    if free < required_bytes + MIN_FREE_BYTES:
        raise InstallError("insufficient free space for managed candidate; no large T3 runtime is copied")

    uid_root, gid_root = 0, 0
    created_dirs: list[CreatedPath] = []
    created_files: list[CreatedPath] = []
    installed = []
    try:
        # Code and systemd units are trusted by the independently approved
        # hash manifest; install them root-owned and non-writable by services.
        for relative, data in payload.items():
            relpath = Path(relative)
            _ensure_directory_at_root(
                target_root, relpath.parent, supervisor_gid=sup_gid,
                dashboard_uid=dashboard_uid, dashboard_gid=dashboard_group_gid,
                require_root=require_root, created_dirs=created_dirs,
            )
            mode = 0o755 if relative.endswith(".py") and "/orchestrator/" in relative else 0o644
            dest = _create_file_at_root(
                target_root, relpath, data, uid=uid_root, gid=gid_root, mode=mode,
                require_root=require_root, supervisor_gid=sup_gid,
                dashboard_uid=dashboard_uid, dashboard_gid=dashboard_group_gid,
                created_files=created_files,
            )
            installed.append(str(dest))

        _ensure_directory_at_root(
            target_root, Path("etc/managed-supervisor/credentials"),
            supervisor_gid=sup_gid, dashboard_uid=dashboard_uid,
            dashboard_gid=dashboard_group_gid, require_root=require_root,
            created_dirs=created_dirs,
        )
        _ensure_directory_at_root(
            target_root, Path("etc/managed-dashboard/credentials"),
            supervisor_gid=sup_gid, dashboard_uid=dashboard_uid,
            dashboard_gid=dashboard_group_gid, require_root=require_root,
            created_dirs=created_dirs,
        )
        for rel in (
            "etc/managed-supervisor/service.json",
            "etc/managed-supervisor/credentials/protocol-token",
            "etc/managed-dashboard/credentials/supervisor-token",
        ):
            data = _read_stage_file(stage, rel, require_root=require_root)
            if rel.endswith("service.json"):
                if data != (json.dumps(service_config, indent=2, sort_keys=True) + "\n").encode("utf-8"):
                    raise InstallError("staged service configuration changed")
                uid, gid = sup_uid, sup_gid
            elif "managed-dashboard" in rel:
                uid, gid = dashboard_uid, dashboard_group_gid
            else:
                uid, gid = sup_uid, sup_gid
            dest = _create_file_at_root(
                target_root, Path(rel), data, uid=uid, gid=gid, mode=0o600,
                require_root=require_root, supervisor_gid=sup_gid,
                dashboard_uid=dashboard_uid, dashboard_gid=dashboard_group_gid,
                created_files=created_files,
            )
            installed.append(str(dest))
        dest = _create_file_at_root(
            target_root, Path("etc/managed-supervisor/credentials/mcp-token"),
            mcp, uid=sup_uid, gid=sup_gid, mode=0o600, require_root=require_root,
            supervisor_gid=sup_gid, dashboard_uid=dashboard_uid,
            dashboard_gid=dashboard_group_gid,
            created_files=created_files,
        )
        installed.append(str(dest))
        # No dashboard config, dispatch marker, systemctl daemon-reload,
        # enable, start, restart, or provider action is performed here.
        return installed
    except BaseException as original:
        rollback_failures = 0
        for created in reversed(created_files):
            rollback_failures += not _remove_at_root(target_root, created)
        for created in reversed(created_dirs):
            rollback_failures += not _remove_at_root(target_root, created)
        if rollback_failures:
            raise InstallError(
                f"candidate install failed; rollback could not remove {rollback_failures} exact created paths"
            ) from original
        raise


def _read_stage_config(stage: Path) -> dict:
    try:
        raw = _read_stage_file(stage, "etc/managed-supervisor/service.json", private=True)
        data = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, InstallError):
        raise InstallError("staged service config is missing or invalid") from None
    if (not isinstance(data, dict) or data.get("schema") != "managed-supervisor-service/v1"
            or data.get("provider") != "opencode"
            or data.get("socket_path") != "/run/managed-supervisor/managed.sock"
            or data.get("state_path") != "/var/lib/managed-supervisor/state.json"
            or data.get("token_file") != "/etc/managed-supervisor/credentials/protocol-token"
            or data.get("mcp_token_file") != "/etc/managed-supervisor/credentials/mcp-token"
            or data.get("base_url") != "http://127.0.0.1:46687"):
        raise InstallError("staged service config differs from the fixed candidate service contract")
    models = data.get("allowed_models")
    if (not isinstance(models, list) or not models or data.get("model") not in models
            or any(not isinstance(item, str) or not any(
                item.startswith(prefix) and len(item) > len(prefix)
                for prefix in ("opencode/", "opencode-go/")) for item in models)):
        raise InstallError("staged models do not match the supported OpenCode route")
    return data


def _read_stage_token(path: Path, *, stage: Path, relative: str, require_root=True) -> bytes:
    try:
        data = _read_stage_file(stage, relative, require_root=require_root, private=True)
        token = data.strip()
    except (OSError, InstallError):
        raise InstallError("staged protocol token is missing") from None
    if len(token) < 32 or len(token) > 4096 or not token.isascii():
        raise InstallError("staged protocol token is malformed")
    return token + b"\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--approved-manifest", required=True, type=Path,
                        help="root-owned SHA-256 allowlist approved independently")
    parser.add_argument("--mcp-token-file", required=True, type=Path,
                        help="root-owned private token source; value is never printed")
    parser.add_argument("--dashboard-user", required=True)
    parser.add_argument("--dashboard-group", required=True)
    args = parser.parse_args(argv)
    try:
        installed = install_candidate(
            args.stage, args.approved_manifest, args.mcp_token_file,
            dashboard_user=args.dashboard_user, dashboard_group=args.dashboard_group,
        )
    except (InstallError, OSError) as exc:
        print(f"managed candidate install refused: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps({"installed_files": installed,
                      "services_enabled_or_started": False,
                      "dashboard_configuration_changed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
