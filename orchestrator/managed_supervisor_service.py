"""Managed-supervisor Unix-socket entry point.

Without ``--dispatch-config`` this service accepts only authenticated health
requests. The explicit dispatcher mode uses a protected configuration file and
the existing experimental supervisor state machine. It is a deployment
candidate only: it is not installed or enabled in any live environment and
requires a root-published live process-attestation record before serving
health or dispatcher requests. It does not provide process/container/network
containment for model tasks.
"""

from __future__ import annotations

import fcntl
import hmac
import json
import os
import socket
import stat
import struct
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

MAX_FRAME = 1024 * 1024
ATTESTATION_RECORD = Path("/run/managed-supervisor-attestation/record.json")


class ManagedSupervisorServiceError(RuntimeError):
    """Invalid service configuration or socket lifecycle failure."""


@dataclass(frozen=True)
class ManagedSupervisorServiceConfig:
    """Protected runtime configuration for an explicitly launched service."""

    socket_path: Path
    state_path: Path
    token_file: Path
    mcp_token_file: Path
    client_uid: int
    socket_group_gid: int
    base_url: str
    provider: str
    model: str
    allowed_models: tuple[str, ...]
    builder_enabled: bool = False

    @classmethod
    def from_file(cls, path):
        config_path = Path(path)
        if not config_path.is_absolute() or not hasattr(os, "O_NOFOLLOW"):
            raise ManagedSupervisorServiceError("config path must be absolute and no-follow capable")
        try:
            fd = os.open(str(config_path), os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW)
        except OSError as exc:
            raise ManagedSupervisorServiceError(
                f"service config cannot be opened: {type(exc).__name__}"
            ) from None
        try:
            metadata = os.fstat(fd)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or metadata.st_mode & 0o077
            ):
                raise ManagedSupervisorServiceError(
                    "service config must be a service-owned regular file with mode 0600 or stricter"
                )
            with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise ManagedSupervisorServiceError("service config exceeds size bound")
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ManagedSupervisorServiceError("service config is not valid UTF-8 JSON") from None
        finally:
            os.close(fd)

        expected = {
            "schema",
            "socket_path",
            "state_path",
            "token_file",
            "mcp_token_file",
            "client_uid",
            "socket_group_gid",
            "base_url",
            "provider",
            "model",
            "allowed_models",
        }
        if (
            not isinstance(value, dict)
            or set(value) not in (expected, expected | {"builder_enabled"})
            or value.get("schema") != "managed-supervisor-service/v1"
        ):
            raise ManagedSupervisorServiceError("unsupported service config schema or fields")
        builder_enabled = value.get("builder_enabled", False)
        if not isinstance(builder_enabled, bool):
            raise ManagedSupervisorServiceError("builder_enabled must be boolean")

        def absolute_path(key):
            raw_path = value[key]
            if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path:
                raise ManagedSupervisorServiceError(f"{key} must be a nonempty absolute path")
            result = Path(raw_path)
            if not result.is_absolute():
                raise ManagedSupervisorServiceError(f"{key} must be an absolute path")
            return result

        client_uid = value["client_uid"]
        group_gid = value["socket_group_gid"]
        if isinstance(client_uid, bool) or not isinstance(client_uid, int) or client_uid <= 0:
            raise ManagedSupervisorServiceError("client_uid must be a positive UID")
        if client_uid == os.geteuid():
            raise ManagedSupervisorServiceError("dashboard peer must use a UID distinct from the supervisor")
        if isinstance(group_gid, bool) or not isinstance(group_gid, int) or group_gid < 0:
            raise ManagedSupervisorServiceError("socket_group_gid must be a nonnegative GID")
        model, allowed = value["model"], value["allowed_models"]
        if value["provider"] not in ("opencode", "codex"):
            raise ManagedSupervisorServiceError("unsupported T3 provider")
        if (
            not isinstance(model, str)
            or not model.strip()
            or not isinstance(allowed, list)
            or not allowed
            or any(not isinstance(item, str) or not item.strip() for item in allowed)
            or len(set(allowed)) != len(allowed)
            or model not in allowed
        ):
            raise ManagedSupervisorServiceError("model and allowed_models must be nonempty and consistent")
        base_url = value["base_url"]
        if not isinstance(base_url, str):
            raise ManagedSupervisorServiceError("base_url must be a loopback origin")
        try:
            parts = urllib.parse.urlsplit(base_url)
            port = parts.port
        except ValueError:
            raise ManagedSupervisorServiceError("base_url must be a loopback origin") from None
        if (
            parts.scheme not in ("http", "https")
            or parts.hostname not in ("127.0.0.1", "::1")
            or parts.username is not None
            or parts.password is not None
            or parts.path not in ("", "/")
            or parts.query
            or parts.fragment
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise ManagedSupervisorServiceError("base_url must be a loopback origin")
        socket_path = absolute_path("socket_path")
        if len(os.fsencode(str(socket_path))) >= 104:
            raise ManagedSupervisorServiceError("socket_path exceeds the local Unix socket path bound")
        return cls(
            socket_path,
            absolute_path("state_path"),
            absolute_path("token_file"),
            absolute_path("mcp_token_file"),
            client_uid,
            group_gid,
            base_url,
            value["provider"],
            model,
            tuple(allowed),
            builder_enabled,
        )

    def validate_state_location(self):
        """Require a private service-owned directory and a safe existing state file."""
        try:
            parent = self.state_path.parent.stat()
            current = self.state_path.lstat()
        except FileNotFoundError:
            current = None
            try:
                parent = self.state_path.parent.stat()
            except OSError as exc:
                raise ManagedSupervisorServiceError(
                    f"state directory unavailable: {type(exc).__name__}"
                ) from None
        except OSError as exc:
            raise ManagedSupervisorServiceError(f"state location unavailable: {type(exc).__name__}") from None
        if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.geteuid() or parent.st_mode & 0o077:
            raise ManagedSupervisorServiceError(
                "state directory must be service-owned and private (mode 0700)"
            )
        if current is not None and (
            not stat.S_ISREG(current.st_mode) or current.st_uid != os.geteuid() or current.st_mode & 0o077
        ):
            raise ManagedSupervisorServiceError("state file must be a service-owned private regular file")


def build_managed_dispatcher(config_path):
    """Build the authenticated dispatcher from protected config and secret files."""
    try:
        from .t3_supervisor import Supervisor
        from .t3_supervisor_client import load_private_supervisor_token
    except ImportError:
        from t3_supervisor import Supervisor
        from t3_supervisor_client import load_private_supervisor_token

    config = ManagedSupervisorServiceConfig.from_file(config_path)
    config.validate_state_location()
    protocol_token = load_private_supervisor_token(config.token_file)
    mcp_token = load_private_supervisor_token(config.mcp_token_file)
    lock_path = config.state_path.with_name(config.state_path.name + ".lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise ManagedSupervisorServiceError(f"state lock unavailable: {type(exc).__name__}") from None
    try:
        lock_stat = os.fstat(lock_fd)
        if (
            not stat.S_ISREG(lock_stat.st_mode)
            or lock_stat.st_uid != os.geteuid()
            or lock_stat.st_mode & 0o077
        ):
            raise ManagedSupervisorServiceError("state lock must be a private service-owned regular file")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ManagedSupervisorServiceError("supervisor state is already in use") from None
        core = Supervisor(
            socket_path=config.socket_path,
            state_path=config.state_path,
            token=protocol_token,
            base_url=config.base_url,
            mcp_token=mcp_token,
            model=config.model,
            allowed_models=config.allowed_models,
            peer_uid=config.client_uid,
            provider=config.provider,
            builder_enabled=config.builder_enabled,
        )
        service = ExperimentalManagedDispatcher(
            core=core,
            socket_path=config.socket_path,
            token=protocol_token,
            client_uid=config.client_uid,
            socket_group_gid=config.socket_group_gid,
        )
        service._state_lock_fd = lock_fd
        service._state_lock_required = True
        return service
    except BaseException:
        os.close(lock_fd)
        raise


def _frame(value: dict) -> bytes:
    body = json.dumps(value, separators=(",", ":")).encode("utf-8")
    if not body or len(body) > MAX_FRAME:
        body = b'{"ok":false,"error":{"code":"RESPONSE_TOO_LARGE"}}'
    return struct.pack(">I", len(body)) + body


def _recv_exact(conn, length: int) -> bytes:
    chunks = []
    remaining = length
    while remaining:
        part = conn.recv(remaining)
        if not part:
            raise ConnectionError("truncated supervisor request")
        chunks.append(part)
        remaining -= len(part)
    return b"".join(chunks)


class ReadOnlyManagedSupervisor:
    """A dedicated-UID health endpoint with strict socket cleanup ownership."""

    def __init__(
        self, *, socket_path, token: str, client_uid: int, socket_group_gid: int, timeout: float = 0.5
    ):
        self.socket_path = Path(socket_path)
        self.token = token
        self.client_uid = client_uid
        self.socket_group_gid = socket_group_gid
        self.timeout = timeout
        self.uid = os.geteuid()
        self.started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.listener = None
        self._lock_fd = None
        self._socket_identity = None

    def _validate(self):
        if not self.socket_path.is_absolute() or "\x00" in str(self.socket_path):
            raise ManagedSupervisorServiceError("socket_path must be an absolute filesystem path")
        if len(os.fsencode(str(self.socket_path))) >= 104:
            raise ManagedSupervisorServiceError("socket_path exceeds local Unix socket path bound")
        if not hasattr(socket, "SO_PEERCRED"):
            raise ManagedSupervisorServiceError("platform lacks Unix peer credential authentication")
        if (
            self.uid <= 0
            or isinstance(self.client_uid, bool)
            or not isinstance(self.client_uid, int)
            or self.client_uid <= 0
        ):
            raise ManagedSupervisorServiceError("service and dashboard must use explicit non-root UIDs")
        if self.client_uid == self.uid:
            raise ManagedSupervisorServiceError("dashboard peer must use a UID distinct from the supervisor")
        if (
            isinstance(self.socket_group_gid, bool)
            or not isinstance(self.socket_group_gid, int)
            or self.socket_group_gid < 0
        ):
            raise ManagedSupervisorServiceError("socket_group_gid must be a nonnegative GID")
        if (
            not isinstance(self.token, str)
            or not self.token.isascii()
            or len(self.token) < 32
            or len(self.token) > 4096
        ):
            raise ManagedSupervisorServiceError("service token must be a bounded, high-entropy string")
        if self.timeout <= 0:
            raise ManagedSupervisorServiceError("socket timeout must be positive")

        try:
            parent = self.socket_path.parent.stat()
        except OSError as exc:
            raise ManagedSupervisorServiceError(f"socket parent unavailable: {type(exc).__name__}") from None
        if (
            not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid not in (0, self.uid)
            or parent.st_gid != self.socket_group_gid
            or not (parent.st_mode & stat.S_ISGID)
            or not (parent.st_mode & 0o010)
            or parent.st_mode & (0o020 | 0o002)
            or not os.access(self.socket_path.parent, os.W_OK | os.X_OK)
        ):
            raise ManagedSupervisorServiceError(
                "socket parent must be service/root-owned, setgid to the shared group, group-traversable, and not group/world writable"
            )

    def start(self):
        """Acquire a service lock and bind a new 0660 Unix socket; never unlink stale paths."""
        self._validate()
        lock_path = self.socket_path.with_name(self.socket_path.name + ".lock")
        if not hasattr(os, "O_NOFOLLOW"):
            raise ManagedSupervisorServiceError("platform cannot safely open the socket lock")
        try:
            self._lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
            lock_stat = os.fstat(self._lock_fd)
            if (
                not stat.S_ISREG(lock_stat.st_mode)
                or lock_stat.st_uid != self.uid
                or lock_stat.st_mode & 0o077
            ):
                raise ManagedSupervisorServiceError("socket lock file ownership/mode is unsafe")
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.close()
            raise ManagedSupervisorServiceError(
                f"supervisor socket lock unavailable: {type(exc).__name__}"
            ) from None
        except ManagedSupervisorServiceError:
            self.close()
            raise
        if self.socket_path.exists() or self.socket_path.is_symlink():
            self.close()
            raise ManagedSupervisorServiceError("socket path already exists; refusing to replace it")

        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            listener.bind(str(self.socket_path))
            bound = self.socket_path.lstat()
            if not stat.S_ISSOCK(bound.st_mode) or bound.st_uid != self.uid:
                raise ManagedSupervisorServiceError("bound socket identity is unsafe")
            self._socket_identity = (bound.st_dev, bound.st_ino)
            os.chmod(self.socket_path, 0o660)
            current = self.socket_path.lstat()
            if current.st_gid != self.socket_group_gid:
                os.chown(self.socket_path, -1, self.socket_group_gid)
                current = self.socket_path.lstat()
            if (
                not stat.S_ISSOCK(current.st_mode)
                or current.st_uid != self.uid
                or current.st_gid != self.socket_group_gid
                or (current.st_mode & 0o777) != 0o660
            ):
                raise ManagedSupervisorServiceError("bound socket ownership/mode does not match contract")
            listener.listen(8)
            listener.settimeout(self.timeout)
            if (current.st_dev, current.st_ino) != self._socket_identity:
                raise ManagedSupervisorServiceError("bound socket changed during setup")
            self.listener = listener
            return self
        except Exception:
            listener.close()
            self._unlink_owned_socket()
            self.close()
            raise

    def _handle(self, conn):
        creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        _pid, peer_uid, _gid = struct.unpack("3i", creds)
        if peer_uid != self.client_uid:
            conn.sendall(_frame({"ok": False, "error": {"code": "PEER_REJECTED"}}))
            return
        (length,) = struct.unpack(">I", _recv_exact(conn, 4))
        if length <= 0 or length > MAX_FRAME:
            conn.sendall(_frame({"ok": False, "error": {"code": "BAD_FRAME"}}))
            return
        try:
            request = json.loads(_recv_exact(conn, length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, ConnectionError):
            conn.sendall(_frame({"ok": False, "error": {"code": "BAD_REQUEST"}}))
            return
        candidate = request.get("token") if isinstance(request, dict) else None
        if (
            not isinstance(candidate, str)
            or not candidate.isascii()
            or not hmac.compare_digest(candidate, self.token)
        ):
            conn.sendall(_frame({"ok": False, "error": {"code": "UNAUTHORIZED"}}))
            return
        conn.sendall(_frame(self._respond(request)))

    def _respond(self, request):
        if request.get("op") != "health":
            return {"ok": False, "error": {"code": "DISPATCH_DISABLED"}}
        return {
            "ok": True,
            "result": {
                "ready": True,
                "pid": os.getpid(),
                "uid": self.uid,
                "protocol": "managed-supervisor-health/v1",
                "read_only": True,
                "builder_enabled": False,
                "started_utc": self.started_utc,
            },
        }

    def serve_forever(self):
        if self.listener is None:
            self.start()
        while self.listener is not None:
            try:
                conn, _ = self.listener.accept()
            except TimeoutError:
                continue
            except OSError:
                if self.listener is None:
                    break
                raise
            try:
                conn.settimeout(self.timeout)
                self._handle(conn)
            except (OSError, ConnectionError, struct.error):
                pass
            finally:
                conn.close()

    def _unlink_owned_socket(self):
        if self._socket_identity is None:
            return
        try:
            current = self.socket_path.lstat()
            if stat.S_ISSOCK(current.st_mode) and (current.st_dev, current.st_ino) == self._socket_identity:
                self.socket_path.unlink()
        except FileNotFoundError:
            pass
        finally:
            self._socket_identity = None

    def close(self):
        listener, self.listener = self.listener, None
        if listener is not None:
            listener.close()
        self._unlink_owned_socket()
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *_exc):
        self.close()


class ExperimentalManagedDispatcher(ReadOnlyManagedSupervisor):
    """Protocol bridge for the existing supervisor state machine.

    This retains its historical name because the wrapped core is experimental.
    It combines the distinct-UID authenticated socket with that core, but does
    not contain T3 or its children and is not a production-hardened service.
    """

    def __init__(self, *, core, attestation_path=ATTESTATION_RECORD, attestation_verifier=None, **kwargs):
        super().__init__(**kwargs)
        self._state_lock_fd = None
        self._state_lock_required = False
        if not hmac.compare_digest(self.token, core.token):
            raise ManagedSupervisorServiceError("supervisor protocol tokens differ")
        if core.peer_uid != self.client_uid:
            raise ManagedSupervisorServiceError("supervisor peer UID differs")
        if Path(core.socket_path) != self.socket_path:
            raise ManagedSupervisorServiceError("supervisor socket paths differ")
        self.core = core
        self.attestation_path = Path(attestation_path)
        if attestation_verifier is None:
            try:
                from .managed_supervisor_attestation import verify_via_root_service
            except ImportError:
                from managed_supervisor_attestation import verify_via_root_service
            attestation_verifier = verify_via_root_service
        self.attestation_verifier = attestation_verifier

    def _validate(self):
        super()._validate()
        if self._state_lock_required and self._state_lock_fd is None:
            raise ManagedSupervisorServiceError("supervisor state lock is not held")

    def _respond(self, request):
        try:
            if self.attestation_verifier(self.attestation_path) is not True:
                raise ManagedSupervisorServiceError("attestation was not confirmed")
        except Exception:
            # No operation, including health, is served when the root-published
            # live process identity no longer matches kernel observations.
            return {"ok": False, "error": {"code": "SERVICE_ATTESTATION_FAILED"}}
        if request.get("op") == "health":
            return {
                "ok": True,
                "result": {
                    "ready": True,
                    "uid": self.uid,
                    "pid": os.getpid(),
                    "read_only": False,
                    "builder_enabled": self.core.builder_enabled,
                    "attested": True,
                    "protocol": "experimental-managed-supervisor/v1",
                },
            }
        return self.core.handle(request)

    def close(self):
        super().close()
        if self._state_lock_fd is not None:
            os.close(self._state_lock_fd)
            self._state_lock_fd = None


def main():
    import argparse

    try:
        from .t3_supervisor_client import load_private_supervisor_token
    except ImportError:
        from t3_supervisor_client import load_private_supervisor_token

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch-config", help="protected config for explicit dispatcher mode")
    parser.add_argument("--socket", help="read-only health socket path")
    parser.add_argument("--token-file", help="read-only health protocol token file")
    parser.add_argument("--client-uid", type=int, help="dashboard peer UID")
    parser.add_argument("--socket-group-gid", type=int, help="shared socket group GID")
    args = parser.parse_args()
    if args.dispatch_config:
        if any(
            value is not None
            for value in (args.socket, args.token_file, args.client_uid, args.socket_group_gid)
        ):
            parser.error("--dispatch-config cannot be combined with read-only socket options")
        service = build_managed_dispatcher(args.dispatch_config)
    else:
        if any(
            value is None for value in (args.socket, args.token_file, args.client_uid, args.socket_group_gid)
        ):
            parser.error(
                "read-only mode requires --socket, --token-file, --client-uid and --socket-group-gid"
            )
        service = ReadOnlyManagedSupervisor(
            socket_path=args.socket,
            token=load_private_supervisor_token(args.token_file),
            client_uid=args.client_uid,
            socket_group_gid=args.socket_group_gid,
        )
    try:
        service.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.close()


if __name__ == "__main__":
    main()
