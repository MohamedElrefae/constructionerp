"""Standalone, read-only kernel observation for a managed T3 supervisor pair.

This module is not wired into dashboard or supervisor startup. Its root-owned
record pins the expected supervisor/T3 PIDs, UIDs, process start ticks, exact
``/proc/<pid>/cgroup`` memberships, socket path and loopback listener port. The
verifier connects to the Unix socket without sending a protocol token, reads
``SO_PEERCRED``, and checks process and listener ownership through ``/proc``.

Assumptions and limits:

* Run as root on Linux with readable ``/proc`` and ``SO_PEERCRED``. Missing,
  hidden, raced or malformed kernel observations fail closed.
* Root owns and provisions the 0444/0400 attestation record, its parent
  directories, and its expected values. Parent directories must not be group
  or world writable. The record is an assertion source, not proof that systemd/cgroups
  enforce resource, network, filesystem or descendant-process containment.
* Cgroup membership is a point-in-time observation. This does not prevent either
  process from moving to another cgroup after verification.
* Finding the T3 listener inode in the pinned PID's fd table binds that PID to
  the listener at observation time. It does not prove the listener is the only
  holder of a duplicated socket fd, nor does it attest T3 application code.
* This code performs no provider requests, dispatches no jobs, and never sends
  the supervisor token. The peer PID must already be known to the root record;
  restart requires a new trusted record.
"""

from __future__ import annotations

import json
import os
import socket
import stat
import struct
from dataclasses import dataclass
from pathlib import Path


SCHEMA = "managed-supervisor-attestation/v1"
MAX_CONFIG_BYTES = 64 * 1024
_FIELDS = {
    "schema", "socket_path", "supervisor_pid", "supervisor_uid",
    "supervisor_start_ticks", "t3_pid", "t3_uid", "t3_start_ticks",
    "supervisor_cgroup_membership", "t3_cgroup_membership", "t3_listener_host", "t3_listener_port",
}


class AttestationError(RuntimeError):
    """Expected process or listener identity could not be proven."""


@dataclass(frozen=True)
class AttestationConfig:
    socket_path: Path
    supervisor_pid: int
    supervisor_uid: int
    supervisor_start_ticks: int
    t3_pid: int
    t3_uid: int
    t3_start_ticks: int
    supervisor_cgroup_membership: tuple[str, ...]
    t3_cgroup_membership: tuple[str, ...]
    t3_listener_host: str
    t3_listener_port: int

    @classmethod
    def from_mapping(cls, value):
        if not isinstance(value, dict) or set(value) != _FIELDS or value.get("schema") != SCHEMA:
            raise AttestationError("unsupported attestation schema or fields")

        def positive_int(name):
            number = value[name]
            if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
                raise AttestationError(f"{name} must be a positive integer")
            return number

        socket_raw = value["socket_path"]
        if not isinstance(socket_raw, str) or not socket_raw or "\x00" in socket_raw:
            raise AttestationError("socket_path must be a nonempty absolute path")
        socket_path = Path(socket_raw)
        if not socket_path.is_absolute():
            raise AttestationError("socket_path must be absolute")
        if len(os.fsencode(str(socket_path))) >= 104:
            raise AttestationError("socket_path exceeds Unix-domain path bound")

        def cgroups(name):
            groups = value[name]
            if (not isinstance(groups, list) or not groups
                    or any(not isinstance(line, str) or not line or "\n" in line for line in groups)
                    or len(set(groups)) != len(groups)):
                raise AttestationError(f"{name} must be a nonempty unique list of exact proc lines")
            for line in groups:
                parts = line.split(":", 2)
                if len(parts) != 3 or not parts[0].isdigit() or not parts[2].startswith("/"):
                    raise AttestationError(f"{name} contains a malformed proc line")
            return tuple(groups)

        supervisor_cgroups = cgroups("supervisor_cgroup_membership")
        t3_cgroups = cgroups("t3_cgroup_membership")

        host, port = value["t3_listener_host"], value["t3_listener_port"]
        if host != "127.0.0.1":
            raise AttestationError("only the IPv4 loopback listener is supported")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise AttestationError("t3_listener_port must be an integer from 1 through 65535")

        supervisor_pid = positive_int("supervisor_pid")
        t3_pid = positive_int("t3_pid")
        if supervisor_pid == t3_pid:
            raise AttestationError("supervisor and T3 must be distinct processes")
        supervisor_uid = positive_int("supervisor_uid")
        t3_uid = positive_int("t3_uid")
        if supervisor_uid == t3_uid:
            raise AttestationError("supervisor and T3 must use distinct UIDs")
        return cls(
            socket_path, supervisor_pid, supervisor_uid,
            positive_int("supervisor_start_ticks"), t3_pid, t3_uid,
            positive_int("t3_start_ticks"), supervisor_cgroups, t3_cgroups, host, port,
        )


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AttestationError("attestation JSON contains duplicate keys")
        result[key] = value
    return result


def load_root_owned_config(path) -> AttestationConfig:
    """Open a root-owned record through root-controlled, no-follow directories."""
    config_path = Path(path)
    if (not config_path.is_absolute() or not hasattr(os, "O_NOFOLLOW")
            or ".." in config_path.parts or len(config_path.parts) < 2):
        raise AttestationError("config path must be absolute and no-follow capable")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    directory_fd = None
    try:
        directory_fd = os.open("/", flags | os.O_DIRECTORY)
        for component in config_path.parts[1:-1]:
            metadata = os.fstat(directory_fd)
            if metadata.st_uid != 0 or metadata.st_mode & 0o022:
                raise AttestationError("config parent directory must be root-owned and not group/world writable")
            next_fd = os.open(component, flags | os.O_DIRECTORY, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        metadata = os.fstat(directory_fd)
        if metadata.st_uid != 0 or metadata.st_mode & 0o022:
            raise AttestationError("config parent directory must be root-owned and not group/world writable")
        fd = os.open(config_path.name, flags, dir_fd=directory_fd)
    except OSError as exc:
        raise AttestationError(f"attestation config cannot be opened: {type(exc).__name__}") from None
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
    try:
        metadata = os.fstat(fd)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0
                or metadata.st_mode & 0o222 or metadata.st_size > MAX_CONFIG_BYTES):
            raise AttestationError("config must be a root-owned, non-writable regular file within size bound")
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
            raw = stream.read(MAX_CONFIG_BYTES + 1)
        if len(raw) > MAX_CONFIG_BYTES:
            raise AttestationError("attestation config exceeds size bound")
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AttestationError("attestation config must be UTF-8 JSON") from None
    finally:
        os.close(fd)
    return AttestationConfig.from_mapping(value)


def _proc_process(pid: int, proc_root: Path, *, expected_uid: int,
                  expected_start_ticks: int, expected_cgroup: tuple[str, ...]) -> None:
    process_dir = proc_root / str(pid)
    try:
        stat_line = (process_dir / "stat").read_text(encoding="ascii")
        # comm may contain spaces or parentheses; Linux's final ')' is the
        # separator before field 3. starttime is field 22, index 19 thereafter.
        tail = stat_line.rsplit(")", 1)[1].split()
        status = (process_dir / "status").read_text(encoding="ascii")
        cgroup_lines = tuple(sorted((process_dir / "cgroup").read_text(encoding="ascii").splitlines()))
    except (OSError, IndexError, UnicodeDecodeError):
        raise AttestationError(f"process {pid} proc identity is missing or uninspectable") from None
    if len(tail) <= 19 or tail[19] != str(expected_start_ticks):
        raise AttestationError(f"process {pid} start time does not match the trusted record")
    uid_line = next((line for line in status.splitlines() if line.startswith("Uid:")), None)
    try:
        uids = uid_line.split()[1:5]
        effective_uid = int(uids[1])
    except (AttributeError, IndexError, ValueError):
        raise AttestationError(f"process {pid} effective UID is uninspectable") from None
    if effective_uid != expected_uid:
        raise AttestationError(f"process {pid} effective UID does not match the trusted record")
    if cgroup_lines != tuple(sorted(expected_cgroup)):
        raise AttestationError(f"process {pid} cgroup membership does not match the trusted record")


def _listener_inode(pid: int, port: int, proc_root: Path) -> str:
    table = proc_root / str(pid) / "net" / "tcp"
    try:
        rows = table.read_text(encoding="ascii").splitlines()[1:]
    except (OSError, UnicodeDecodeError):
        raise AttestationError("kernel TCP listener table is missing or uninspectable") from None
    target = f"0100007F:{port:04X}"
    matches = []
    try:
        for row in rows:
            columns = row.split()
            if len(columns) < 10:
                raise AttestationError("kernel TCP listener table is malformed")
            if columns[3] != "0A":
                continue
            address = columns[1].upper()
            if address == f"00000000:{port:04X}":
                raise AttestationError("wildcard listener conflicts with the configured T3 port")
            if address == target:
                matches.append(columns[9])
    except (IndexError, ValueError):
        raise AttestationError("kernel TCP listener table is malformed") from None
    if len(matches) != 1 or not matches[0].isdigit():
        raise AttestationError("configured T3 listener is absent or ambiguous in kernel TCP table")
    try:
        rows6 = (proc_root / str(pid) / "net" / "tcp6").read_text(encoding="ascii").splitlines()[1:]
        for row in rows6:
            columns = row.split()
            if len(columns) < 10:
                raise AttestationError("kernel IPv6 listener table is malformed")
            if columns[3] == "0A" and columns[1].upper().endswith(f":{port:04X}"):
                raise AttestationError("IPv6 listener conflicts with the configured T3 port")
    except (OSError, UnicodeDecodeError):
        raise AttestationError("kernel IPv6 listener table is missing or uninspectable") from None
    return matches[0]


def _process_owns_socket(pid: int, inode: str, proc_root: Path) -> None:
    fd_dir = proc_root / str(pid) / "fd"
    try:
        entries = list(fd_dir.iterdir())
        links = [os.readlink(entry) for entry in entries]
    except OSError:
        raise AttestationError(f"cannot inspect process {pid} file descriptors") from None
    if f"socket:[{inode}]" not in links:
        raise AttestationError(f"T3 process {pid} does not own the configured listener socket")


def verify_peer_and_processes(conn, config: AttestationConfig, *, proc_root="/proc") -> dict:
    """Verify connected peer creds, pinned processes/cgroups and T3 listener ownership."""
    proc_root = Path(proc_root)
    if not hasattr(socket, "SO_PEERCRED"):
        raise AttestationError("platform does not expose Unix peer credentials")
    try:
        peer_path = conn.getpeername()
        if not isinstance(peer_path, (str, bytes)) or os.fsdecode(peer_path) != str(config.socket_path):
            raise AttestationError("connected supervisor socket differs from the trusted path")
        credentials = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        peer_pid, peer_uid, _peer_gid = struct.unpack("3i", credentials)
    except (OSError, struct.error):
        raise AttestationError("Unix peer credentials are missing or malformed") from None
    if peer_pid != config.supervisor_pid or peer_uid != config.supervisor_uid:
        raise AttestationError("Unix peer PID/UID differs from the trusted supervisor identity")

    _proc_process(peer_pid, proc_root, expected_uid=config.supervisor_uid,
                  expected_start_ticks=config.supervisor_start_ticks,
                  expected_cgroup=config.supervisor_cgroup_membership)
    _proc_process(config.t3_pid, proc_root, expected_uid=config.t3_uid,
                  expected_start_ticks=config.t3_start_ticks,
                  expected_cgroup=config.t3_cgroup_membership)
    try:
        supervisor_net = (proc_root / str(peer_pid) / "ns" / "net").stat()
        t3_net = (proc_root / str(config.t3_pid) / "ns" / "net").stat()
    except OSError:
        raise AttestationError("process network namespaces are uninspectable") from None
    if (supervisor_net.st_dev, supervisor_net.st_ino) != (t3_net.st_dev, t3_net.st_ino):
        raise AttestationError("supervisor and T3 must share a network namespace")
    inode = _listener_inode(config.t3_pid, config.t3_listener_port, proc_root)
    _process_owns_socket(config.t3_pid, inode, proc_root)
    # Detect common exit/reuse or cgroup movement during the observations.
    _proc_process(peer_pid, proc_root, expected_uid=config.supervisor_uid,
                  expected_start_ticks=config.supervisor_start_ticks,
                  expected_cgroup=config.supervisor_cgroup_membership)
    _proc_process(config.t3_pid, proc_root, expected_uid=config.t3_uid,
                  expected_start_ticks=config.t3_start_ticks,
                  expected_cgroup=config.t3_cgroup_membership)
    return {
        "identity_observed": True,
        "supervisor_pid": peer_pid,
        "supervisor_uid": peer_uid,
        "t3_pid": config.t3_pid,
        "t3_uid": config.t3_uid,
        "supervisor_cgroup_membership": list(config.supervisor_cgroup_membership),
        "t3_cgroup_membership": list(config.t3_cgroup_membership),
        "t3_listener_host": config.t3_listener_host,
        "t3_listener_port": config.t3_listener_port,
        "listener_inode": inode,
    }


def verify_local_service_attestation(config_path, *, supervisor_pid=None, supervisor_uid=None,
                                     proc_root="/proc") -> AttestationConfig:
    """Revalidate a root-published record from inside the pinned supervisor.

    This does not create trust in the record: it checks that the record is
    root-owned and then re-reads process UIDs, start times, cgroups, network
    namespace identity, and T3 listener ownership immediately before service
    work. It is a point-in-time check and cannot prevent a trusted systemd
    restart from beginning after the check returns.
    """
    config = load_root_owned_config(config_path)
    current_pid = os.getpid() if supervisor_pid is None else supervisor_pid
    current_uid = os.geteuid() if supervisor_uid is None else supervisor_uid
    if config.supervisor_pid != current_pid or config.supervisor_uid != current_uid:
        raise AttestationError("root record does not identify this supervisor process")
    proc_root = Path(proc_root)
    _proc_process(current_pid, proc_root, expected_uid=config.supervisor_uid,
                  expected_start_ticks=config.supervisor_start_ticks,
                  expected_cgroup=config.supervisor_cgroup_membership)
    _proc_process(config.t3_pid, proc_root, expected_uid=config.t3_uid,
                  expected_start_ticks=config.t3_start_ticks,
                  expected_cgroup=config.t3_cgroup_membership)
    try:
        supervisor_net = (proc_root / str(current_pid) / "ns" / "net").stat()
        t3_net = (proc_root / str(config.t3_pid) / "ns" / "net").stat()
    except OSError:
        raise AttestationError("process network namespaces are uninspectable") from None
    if (supervisor_net.st_dev, supervisor_net.st_ino) != (t3_net.st_dev, t3_net.st_ino):
        raise AttestationError("supervisor and T3 must share a network namespace")
    inode = _listener_inode(config.t3_pid, config.t3_listener_port, proc_root)
    _process_owns_socket(config.t3_pid, inode, proc_root)
    _proc_process(current_pid, proc_root, expected_uid=config.supervisor_uid,
                  expected_start_ticks=config.supervisor_start_ticks,
                  expected_cgroup=config.supervisor_cgroup_membership)
    _proc_process(config.t3_pid, proc_root, expected_uid=config.t3_uid,
                  expected_start_ticks=config.t3_start_ticks,
                  expected_cgroup=config.t3_cgroup_membership)
    return config


def attest_managed_supervisor(config_path, *, timeout: float = 1.0) -> dict:
    """Root-only socket attestation; never sends auth data or a protocol frame."""
    if os.geteuid() != 0:
        raise AttestationError("attestation must run as root to inspect protected process state")
    if timeout <= 0:
        raise AttestationError("timeout must be positive")
    config = load_root_owned_config(config_path)
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        conn.settimeout(timeout)
        conn.connect(str(config.socket_path))
        return verify_peer_and_processes(conn, config)
    except OSError as exc:
        raise AttestationError(f"supervisor socket unavailable: {type(exc).__name__}") from None
    finally:
        conn.close()


VERIFIER_SOCKET = Path("/run/managed-attestation-verifier/verify.sock")


def verify_via_root_service(config_path=Path("/run/managed-supervisor-attestation/record.json"),
                            *, socket_path=VERIFIER_SOCKET, timeout: float = 1.0) -> bool:
    """Ask the fixed root verifier to inspect cross-UID process state.

    The request has one fixed version token and no caller-selected paths or
    operation. Peer credentials ensure the endpoint is root-owned; the root
    endpoint separately requires this process's PID and UID to match the
    root-published attestation. Any protocol or connection failure denies.
    """
    if Path(socket_path) != VERIFIER_SOCKET:
        raise AttestationError("root verifier socket path is fixed")
    if Path(config_path) != Path("/run/managed-supervisor-attestation/record.json"):
        raise AttestationError("root attestation record path is fixed")
    if timeout <= 0 or timeout > 5:
        raise AttestationError("root verifier timeout is outside the supported bound")
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        conn.settimeout(timeout)
        conn.connect(str(VERIFIER_SOCKET))
        if not hasattr(socket, "SO_PEERCRED"):
            raise AttestationError("platform does not expose Unix peer credentials")
        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        _pid, uid, _gid = struct.unpack("3i", raw)
        if uid != 0:
            raise AttestationError("root verifier peer UID is not root")
        conn.sendall(b"V1\n")
        conn.shutdown(socket.SHUT_WR)
        response = conn.recv(4)
        if response != b"OK\n":
            raise AttestationError("root verifier denied or returned an invalid response")
        return True
    except OSError as exc:
        raise AttestationError(f"root verifier unavailable: {type(exc).__name__}") from None
    except struct.error:
        raise AttestationError("root verifier peer credentials are malformed") from None
    finally:
        conn.close()
