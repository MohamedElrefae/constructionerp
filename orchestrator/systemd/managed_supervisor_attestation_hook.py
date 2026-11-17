#!/usr/bin/env python3
"""Root-only systemd lifecycle hook for a runtime managed-service attestation.

This candidate hook discovers PID/UID/cgroup state from systemd and /proc,
verifies the Unix peer and T3 listener before atomically publishing a short-lived
root-owned record, and removes the record on service stop. It resolves the T3
listener owner separately from the unit MainPID (the proxy runner) and refuses
ambiguous descriptor holders. It never sends an application frame or credential.
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
import secrets
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from managed_supervisor_attestation import (
    AttestationConfig,
    AttestationError,
    _listener_inode,
    verify_peer_and_processes,
)

ATTESTATION_PATH = Path("/run/managed-supervisor-attestation/record.json")
SOCKET_PATH = Path("/run/managed-supervisor/managed.sock")
T3_HOST = "127.0.0.1"
T3_PORT = 46687
SYSTEMCTL = "/usr/bin/systemctl"


class HookError(RuntimeError):
    pass


def _run_systemctl(unit: str, *, runner=subprocess.run) -> dict[str, int | str]:
    requested = "ActiveState,MainPID,User,Group,ControlGroup"
    try:
        result = runner(
            [SYSTEMCTL, "show", "--no-pager", f"--property={requested}", unit],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
            check=False,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        raise HookError("systemd unit state is unavailable") from None
    if result.returncode != 0:
        raise HookError("systemd unit state query failed")
    values = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            raise HookError("systemd returned malformed unit properties")
        key, value = line.split("=", 1)
        if key in values:
            raise HookError("systemd returned duplicate unit properties")
        values[key] = value
    expected_group = {
        "managed-supervisor.service": ("managed-supervisor", "managed-dashboard"),
        "managed-t3.service": ("managed-t3", "managed-t3-egress"),
    }
    if unit not in expected_group:
        raise HookError("unsupported service unit")
    user, group = expected_group[unit]
    if (
        values.get("ActiveState") not in ("active", "activating")
        or values.get("User") != user
        or values.get("Group") != group
    ):
        raise HookError("service unit identity or active state mismatch")
    expected_cgroup = f"/system.slice/{unit}"
    if values.get("ControlGroup") != expected_cgroup:
        raise HookError("service unit cgroup differs from the fixed candidate unit")
    try:
        pid = int(values["MainPID"])
    except (KeyError, ValueError):
        raise HookError("service unit MainPID is missing or malformed") from None
    if pid <= 0:
        raise HookError("service unit has no running MainPID")
    try:
        uid = pwd.getpwnam(user).pw_uid
    except KeyError:
        raise HookError("service unit user is missing") from None
    return {"pid": pid, "uid": uid, "cgroup": expected_cgroup}


def _proc_identity(pid: int, uid: int, cgroup: str, *, proc_root: Path) -> tuple[int, tuple[str, ...]]:
    process = proc_root / str(pid)
    try:
        stat_text = (process / "stat").read_text(encoding="ascii")
        status_text = (process / "status").read_text(encoding="ascii")
        cgroup_lines = tuple(sorted((process / "cgroup").read_text(encoding="ascii").splitlines()))
        tail = stat_text.rsplit(")", 1)[1].split()
        start_ticks = int(tail[19])
        uid_line = next(line for line in status_text.splitlines() if line.startswith("Uid:"))
        effective_uid = int(uid_line.split()[2])
    except (OSError, UnicodeDecodeError, IndexError, ValueError, StopIteration):
        raise HookError(f"process {pid} identity is uninspectable") from None
    # This candidate deliberately supports cgroup v2 only and requires a
    # single exact unified hierarchy membership.
    if cgroup_lines != (f"0::{cgroup}",):
        raise HookError(f"process {pid} is outside its exact unified service cgroup")
    if effective_uid != uid or start_ticks <= 0:
        raise HookError(f"process {pid} UID or start time is invalid")
    return start_ticks, cgroup_lines


def _listener_owner_pid(
    unit_main_pid: int, unit_uid: int, unit_cgroup: str, *, proc_root: Path, port: int
) -> tuple[int, int, tuple[str, ...]]:
    """Resolve the unique process owning the listener FD inside the unit cgroup.

    The T3 service MainPID is a runner, not necessarily the listener. First
    obtain the loopback listener inode from that unit process's network table,
    then enumerate all visible process FD tables. Ambiguous holders or a holder
    outside the exact T3 cgroup fail closed.
    """
    inode = _listener_inode(unit_main_pid, port, proc_root)
    holders = []
    try:
        processes = list(proc_root.iterdir())
    except OSError:
        raise HookError("cannot enumerate /proc for listener ownership") from None
    for process in processes:
        if not process.name.isdigit():
            continue
        try:
            links = [os.readlink(entry) for entry in (process / "fd").iterdir()]
        except FileNotFoundError:
            # A process that vanished during the scan cannot still own the FD.
            continue
        except OSError:
            raise HookError("a process FD table is uninspectable during listener ownership scan") from None
        if f"socket:[{inode}]" in links:
            holders.append(int(process.name))
    if len(holders) != 1:
        raise HookError("T3 listener FD owner is absent or ambiguous")
    listener_pid = holders[0]
    start_ticks, cgroups = _proc_identity(
        listener_pid,
        unit_uid,
        unit_cgroup,
        proc_root=proc_root,
    )
    # Re-read runner identity to detect exit, PID reuse, or cgroup movement
    # during the discovery pass. verify_peer_and_processes repeats this check.
    _proc_identity(unit_main_pid, unit_uid, unit_cgroup, proc_root=proc_root)
    return listener_pid, start_ticks, cgroups


def _open_record_directory(path: Path, *, require_root: bool) -> int:
    if not path.is_absolute() or ".." in path.parts or not path.name:
        raise HookError("attestation path must be an absolute normalized path")
    if require_root and path != ATTESTATION_PATH:
        raise HookError("attestation path is fixed by the service contract")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    directory_fd = os.open("/", flags)
    try:
        for component in path.parts[1:-1]:
            next_fd = os.open(component, flags, dir_fd=directory_fd)
            metadata = os.fstat(next_fd)
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or (require_root and metadata.st_uid != 0)
                or (require_root and metadata.st_mode & 0o022)
            ):
                os.close(next_fd)
                raise HookError("attestation parent directory is not protected")
            os.close(directory_fd)
            directory_fd = next_fd
        return directory_fd
    except BaseException:
        os.close(directory_fd)
        raise


def _remove_record(path: Path, *, require_root: bool = True) -> None:
    directory_fd = _open_record_directory(path, require_root=require_root)
    try:
        try:
            os.unlink(path.name, dir_fd=directory_fd)
            os.fsync(directory_fd)
        except FileNotFoundError:
            pass
    finally:
        os.close(directory_fd)


def _publish_record(path: Path, config: AttestationConfig, *, require_root: bool) -> None:
    directory_fd = _open_record_directory(path, require_root=require_root)
    temporary = f".record.{os.getpid()}.{secrets.token_hex(8)}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    raw = (
        json.dumps(
            {
                "schema": "managed-supervisor-attestation/v1",
                "socket_path": str(config.socket_path),
                "supervisor_pid": config.supervisor_pid,
                "supervisor_uid": config.supervisor_uid,
                "supervisor_start_ticks": config.supervisor_start_ticks,
                "t3_pid": config.t3_pid,
                "t3_uid": config.t3_uid,
                "t3_start_ticks": config.t3_start_ticks,
                "supervisor_cgroup_membership": list(config.supervisor_cgroup_membership),
                "t3_cgroup_membership": list(config.t3_cgroup_membership),
                "t3_listener_host": config.t3_listener_host,
                "t3_listener_port": config.t3_listener_port,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    fd = None
    try:
        fd = os.open(temporary, flags, 0o400, dir_fd=directory_fd)
        owner_uid, owner_gid = (0, 0) if require_root else (os.geteuid(), os.getegid())
        os.fchown(fd, owner_uid, owner_gid)
        os.fchmod(fd, 0o444)
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise HookError("short write while publishing attestation")
            view = view[count:]
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.rename(temporary, path.name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
    except BaseException as exc:
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except OSError:
            pass
        if isinstance(exc, HookError):
            raise
        raise HookError(f"attestation record could not be published: {type(exc).__name__}") from None
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory_fd)


def publish_attestation(
    *,
    path: Path = ATTESTATION_PATH,
    runner=subprocess.run,
    proc_root=Path("/proc"),
    timeout: float = 15.0,
    sleeper=time.sleep,
    require_root: bool = True,
) -> dict:
    """Observe services and publish only after peer/listener verification."""
    if require_root and os.geteuid() != 0:
        raise HookError("attestation lifecycle hook must run as root")
    if timeout <= 0 or timeout > 30:
        raise HookError("attestation startup timeout is outside the supported bound")
    # Eliminate any prior generation before observing new process identities.
    _remove_record(path, require_root=require_root)
    supervisor = _run_systemctl("managed-supervisor.service", runner=runner)
    t3 = _run_systemctl("managed-t3.service", runner=runner)
    supervisor_start, supervisor_cgroups = _proc_identity(
        supervisor["pid"], supervisor["uid"], supervisor["cgroup"], proc_root=Path(proc_root)
    )
    # The systemd MainPID is the T3 runner. Verify it, then resolve the unique
    # child process that owns the actual configured loopback listener socket.
    _proc_identity(t3["pid"], t3["uid"], t3["cgroup"], proc_root=Path(proc_root))
    listener_pid, t3_start, t3_cgroups = _listener_owner_pid(
        t3["pid"],
        t3["uid"],
        t3["cgroup"],
        proc_root=Path(proc_root),
        port=T3_PORT,
    )
    config = AttestationConfig(
        SOCKET_PATH,
        supervisor["pid"],
        supervisor["uid"],
        supervisor_start,
        listener_pid,
        t3["uid"],
        t3_start,
        supervisor_cgroups,
        t3_cgroups,
        T3_HOST,
        T3_PORT,
    )
    deadline = time.monotonic() + timeout
    while True:
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            conn.settimeout(min(1.0, timeout))
            conn.connect(str(SOCKET_PATH))
        except OSError:
            conn.close()
            if time.monotonic() >= deadline:
                raise HookError("supervisor Unix socket did not become available") from None
            sleeper(0.1)
            continue
        try:
            observed = verify_peer_and_processes(conn, config, proc_root=proc_root)
        except AttestationError as exc:
            raise HookError(f"runtime identity verification failed: {type(exc).__name__}") from None
        finally:
            conn.close()
        _publish_record(path, config, require_root=require_root)
        return observed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--publish", action="store_true")
    mode.add_argument("--remove", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.remove:
            if os.geteuid() != 0:
                raise HookError("attestation lifecycle hook must run as root")
            _remove_record(ATTESTATION_PATH)
        else:
            publish_attestation()
    except (HookError, AttestationError, OSError) as exc:
        print(f"managed attestation lifecycle failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
