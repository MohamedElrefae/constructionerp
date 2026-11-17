"""Declarative contract for a future externally managed dashboard supervisor.

This module validates configuration only; it does not connect, dispatch, or
enable the dashboard route. A production service must use a dedicated Unix UID
and a Unix-domain socket. The dashboard holds its own private copy of the
shared protocol token; the supervisor keeps a separately protected copy.
"""

from __future__ import annotations

import os
import json
import socket
import stat
import struct
import re
from dataclasses import dataclass
from pathlib import Path


SCHEMA = "dashboard-managed-supervisor/v1"


class ManagedSupervisorConfigError(ValueError):
    """Configuration does not meet the managed-supervisor contract."""


def require_test_only_dispatch(test_mode: bool) -> None:
    """Keep the candidate route unavailable to ordinary dashboard processes."""
    if test_mode is not True:
        raise ManagedSupervisorConfigError(
            "managed supervisor dispatch is unavailable outside explicit test mode")


DISPATCH_SCHEMA = "dashboard-managed-supervisor-dispatch/v1"
_CGROUP_PATH_RE = re.compile(r"^/(?:[A-Za-z0-9_.@:-]+/)*[A-Za-z0-9_.@:-]+$")


@dataclass(frozen=True)
class ManagedSupervisorDispatchConfig:
    """Explicit dashboard dispatch grant for a dedicated supervisor peer.

    The separate schema keeps the existing health-only contract permanently
    read-only. This config is inert unless the dashboard process also receives
    ``DASHBOARD_ENABLE_MANAGED_DISPATCH=1``.
    """

    socket_path: Path
    token_file: Path
    expected_uid: int
    socket_group_gid: int
    expected_cgroup: str
    allowed_models: tuple[str, ...]
    builder_enabled: bool = False

    @classmethod
    def from_mapping(cls, value, *, dashboard_uid: int | None = None):
        if (not isinstance(value, dict) or value.get("schema") != DISPATCH_SCHEMA
                or value.get("dispatch_enabled") is not True):
            raise ManagedSupervisorConfigError(
                "managed dispatch requires the explicit dispatch schema and dispatch_enabled true")
        uid = value.get("expected_uid")
        if isinstance(uid, bool) or not isinstance(uid, int) or uid <= 0:
            raise ManagedSupervisorConfigError("expected_uid must be a positive service UID")
        dashboard_uid = os.geteuid() if dashboard_uid is None else dashboard_uid
        if uid == dashboard_uid:
            raise ManagedSupervisorConfigError("supervisor must run under a dedicated UID distinct from the dashboard")
        gid = value.get("socket_group_gid")
        if isinstance(gid, bool) or not isinstance(gid, int) or gid < 0:
            raise ManagedSupervisorConfigError("socket_group_gid must be a nonnegative GID")

        def absolute_path(key):
            raw = value.get(key)
            if not isinstance(raw, str) or not raw or "\x00" in raw:
                raise ManagedSupervisorConfigError(f"{key} must be a nonempty absolute path")
            path = Path(raw)
            if not path.is_absolute():
                raise ManagedSupervisorConfigError(f"{key} must be an absolute path")
            return path

        sock = absolute_path("socket_path")
        if len(os.fsencode(str(sock))) >= 104:
            raise ManagedSupervisorConfigError("socket_path exceeds the local Unix socket path bound")
        token = absolute_path("token_file")
        cgroup = value.get("expected_cgroup")
        if (not isinstance(cgroup, str) or not _CGROUP_PATH_RE.fullmatch(cgroup)
                or any(part in (".", "..") for part in cgroup.split("/"))
                or not cgroup.endswith(".service")):
            raise ManagedSupervisorConfigError("expected_cgroup must be an exact absolute systemd service cgroup path")
        models = value.get("allowed_models")
        if (not isinstance(models, list) or not models
                or any(not isinstance(model, str) or not model.strip() for model in models)
                or len(set(models)) != len(models)):
            raise ManagedSupervisorConfigError("allowed_models must be a nonempty unique string list")
        builder_enabled = value.get("builder_enabled", False)
        if not isinstance(builder_enabled, bool):
            raise ManagedSupervisorConfigError("builder_enabled must be boolean")
        if not hasattr(socket, "SO_PEERCRED"):
            raise ManagedSupervisorConfigError("platform lacks Unix peer credential authentication")
        return cls(sock, token, uid, gid, cgroup, tuple(models), builder_enabled)

    @classmethod
    def from_file(cls, path, *, dashboard_uid: int | None = None):
        config_path = Path(path)
        if not config_path.is_absolute() or not hasattr(os, "O_NOFOLLOW"):
            raise ManagedSupervisorConfigError("dispatch config path must be absolute and no-follow capable")
        try:
            fd = os.open(str(config_path), os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW)
        except OSError as exc:
            raise ManagedSupervisorConfigError(f"dispatch config cannot be opened: {type(exc).__name__}") from None
        try:
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid()
                    or st.st_mode & 0o022):
                raise ManagedSupervisorConfigError("dispatch config must be dashboard-owned and not group/world writable")
            with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise ManagedSupervisorConfigError("dispatch config exceeds size bound")
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ManagedSupervisorConfigError("dispatch config is not valid UTF-8 JSON") from None
        finally:
            os.close(fd)
        return cls.from_mapping(value, dashboard_uid=dashboard_uid)

    def verify_socket(self, *, access=os.access) -> None:
        try:
            sock = self.socket_path.lstat()
            parent = self.socket_path.parent.stat()
        except OSError as exc:
            raise ManagedSupervisorConfigError(f"supervisor socket unavailable: {type(exc).__name__}") from None
        if not stat.S_ISSOCK(sock.st_mode):
            raise ManagedSupervisorConfigError("configured dispatch endpoint is not a Unix socket")
        if sock.st_uid != self.expected_uid or sock.st_gid != self.socket_group_gid:
            raise ManagedSupervisorConfigError("supervisor socket owner/group mismatch")
        if (sock.st_mode & 0o060) != 0o060 or sock.st_mode & 0o007:
            raise ManagedSupervisorConfigError("supervisor socket must be group read/write and inaccessible to others")
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid not in (0, self.expected_uid)
                or parent.st_gid != self.socket_group_gid or not parent.st_mode & 0o010
                or parent.st_mode & (0o020 | 0o002)):
            raise ManagedSupervisorConfigError("supervisor socket directory ownership/mode is unsafe")
        if not access(self.socket_path, os.R_OK | os.W_OK):
            raise ManagedSupervisorConfigError("dashboard cannot access supervisor socket")

    def peer_verifier(self, *, proc_root: str | Path = "/proc"):
        """Verify kernel peer UID and exact unified-cgroup service path pre-auth."""
        proc_root = Path(proc_root)

        def verify(conn):
            try:
                raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
                pid, uid, _gid = struct.unpack("3i", raw)
                if pid <= 0 or uid != self.expected_uid:
                    return None
                lines = (proc_root / str(pid) / "cgroup").read_text(encoding="ascii").splitlines()
                unified = [line[3:] for line in lines if line.startswith("0::")]
                if len(unified) != 1 or unified[0] != self.expected_cgroup:
                    return None
                return {"identity_observed": True, "pid": pid, "uid": uid,
                        "cgroup": unified[0]}
            except (OSError, UnicodeError, ValueError, struct.error):
                return None

        return verify


@dataclass(frozen=True)
class ManagedSupervisorConfig:
    socket_path: Path
    token_file: Path
    expected_uid: int
    socket_group_gid: int
    allowed_models: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value, *, dashboard_uid: int | None = None):
        """Parse the strict versioned contract without enabling dispatch."""
        if not isinstance(value, dict) or value.get("schema") != SCHEMA:
            raise ManagedSupervisorConfigError("unsupported supervisor config schema")
        if value.get("dispatch_enabled") is not False:
            raise ManagedSupervisorConfigError(
                "managed supervisor contract must keep dispatch_enabled false")

        uid = value.get("expected_uid")
        if isinstance(uid, bool) or not isinstance(uid, int) or uid <= 0:
            raise ManagedSupervisorConfigError("expected_uid must be a positive service UID")
        dashboard_uid = os.geteuid() if dashboard_uid is None else dashboard_uid
        if uid == dashboard_uid:
            raise ManagedSupervisorConfigError(
                "supervisor must run under a dedicated UID distinct from the dashboard")

        gid = value.get("socket_group_gid")
        if isinstance(gid, bool) or not isinstance(gid, int) or gid < 0:
            raise ManagedSupervisorConfigError("socket_group_gid must be a nonnegative GID")

        def absolute_path(key):
            raw = value.get(key)
            if not isinstance(raw, str) or not raw or "\x00" in raw:
                raise ManagedSupervisorConfigError(f"{key} must be a nonempty absolute path")
            path = Path(raw)
            if not path.is_absolute():
                raise ManagedSupervisorConfigError(f"{key} must be an absolute path")
            return path

        socket_path = absolute_path("socket_path")
        if len(os.fsencode(str(socket_path))) >= 104:
            raise ManagedSupervisorConfigError("socket_path exceeds the local Unix socket path bound")
        token_file = absolute_path("token_file")
        if not hasattr(socket, "SO_PEERCRED"):
            raise ManagedSupervisorConfigError("platform cannot authenticate Unix socket peer credentials")

        models = value.get("allowed_models")
        if (not isinstance(models, list) or not models
                or any(not isinstance(model, str) or not model.strip() for model in models)
                or len(set(models)) != len(models)):
            raise ManagedSupervisorConfigError("allowed_models must be a nonempty unique string list")

        return cls(socket_path, token_file, uid, gid, tuple(models))

    @classmethod
    def from_file(cls, path, *, dashboard_uid: int | None = None):
        """Read a bounded, dashboard-owned config without following a symlink."""
        config_path = Path(path)
        if not config_path.is_absolute() or not hasattr(os, "O_NOFOLLOW"):
            raise ManagedSupervisorConfigError("config path must be absolute and no-follow capable")
        try:
            fd = os.open(str(config_path), os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW)
        except OSError as exc:
            raise ManagedSupervisorConfigError(
                f"supervisor config cannot be opened: {type(exc).__name__}") from None
        try:
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid()
                    or st.st_mode & 0o022):
                raise ManagedSupervisorConfigError(
                    "supervisor config must be a current-user regular file not writable by group/others")
            with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as fh:
                raw = fh.read(65537)
            if len(raw) > 65536:
                raise ManagedSupervisorConfigError("supervisor config exceeds size bound")
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ManagedSupervisorConfigError("supervisor config is not valid UTF-8 JSON") from None
        finally:
            os.close(fd)
        return cls.from_mapping(value, dashboard_uid=dashboard_uid)

    def verify_socket(self, *, access=os.access) -> None:
        """Verify the live socket matches the configured service UID/group.

        The service manager must create a private runtime directory traversable
        by the dashboard's shared group, and a group read/write socket with no
        world permissions. This check validates the endpoint metadata and the
        current process's actual ability to connect; it is not a process
        attestation beyond the kernel peer UID checked by SupervisorClient.
        """
        try:
            sock = self.socket_path.lstat()
            parent = self.socket_path.parent.stat()
        except OSError as exc:
            raise ManagedSupervisorConfigError(
                f"supervisor socket is unavailable: {type(exc).__name__}") from None
        if not stat.S_ISSOCK(sock.st_mode):
            raise ManagedSupervisorConfigError("configured supervisor endpoint is not a Unix socket")
        if sock.st_uid != self.expected_uid or sock.st_gid != self.socket_group_gid:
            raise ManagedSupervisorConfigError("supervisor socket owner/group mismatch")
        if (sock.st_mode & 0o060) != 0o060 or (sock.st_mode & 0o007):
            raise ManagedSupervisorConfigError(
                "supervisor socket must grant group read/write and deny all world access")
        if (not stat.S_ISDIR(parent.st_mode)
                or parent.st_uid not in (0, self.expected_uid)
                or parent.st_gid != self.socket_group_gid
                or not (parent.st_mode & 0o010)
                or parent.st_mode & (0o020 | 0o002)):
            raise ManagedSupervisorConfigError(
                "supervisor socket directory must be service/root-owned, group-traversable, and not group/world writable")
        if not access(self.socket_path, os.R_OK | os.W_OK):
            raise ManagedSupervisorConfigError("dashboard cannot access the supervisor socket")

    def launcher_options(self) -> dict:
        """Values that a later approved connection adapter must pass through."""
        return {"allowed_models": list(self.allowed_models), "expected_uid": self.expected_uid}


def check_managed_supervisor_health(config_path) -> dict:
    """Perform the dashboard's read-only authenticated Unix-socket check."""
    try:
        from .t3_supervisor_client import SupervisorClient, load_private_supervisor_token
    except ImportError:
        from t3_supervisor_client import SupervisorClient, load_private_supervisor_token

    config = ManagedSupervisorConfig.from_file(config_path)
    config.verify_socket()
    token = load_private_supervisor_token(config.token_file)
    result = SupervisorClient(
        config.socket_path, token, timeout=3.0, expected_uid=config.expected_uid
    ).call("health")
    if (result.get("uid") != config.expected_uid
            or result.get("read_only") is not True
            or result.get("protocol") != "managed-supervisor-health/v1"
            or not result.get("ready")):
        raise ManagedSupervisorConfigError("supervisor health identity/capability response mismatch")
    return {
        "ready": True,
        "read_only": True,
        "uid": config.expected_uid,
        "protocol": result["protocol"],
        "pid": result.get("pid"),
        "allowed_models": list(config.allowed_models),
    }
