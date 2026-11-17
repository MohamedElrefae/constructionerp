"""Lifecycle for an explicitly managed, isolated local T3 server.

This module is intentionally not connected to the orchestrator dispatch path.
It starts only a caller-selected executable and entry point, binds T3 to a
literal loopback address, and stores T3 state below a dedicated scratch root.
Shutdown targets the Popen child only; it never signals a process group.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path


class T3ServerLifecycleError(RuntimeError):
    """Invalid configuration or a managed T3 process lifecycle failure."""


_LOOPBACK_HOSTS = {"127.0.0.1", "::1"}


class T3ServerProcess:
    """Manage one T3 server child with isolated storage and environment.

    The supplied ``repository_root`` is used to prevent accidentally placing
    server state in the source checkout. ``base_dir`` must be an absolute,
    dedicated directory outside that checkout. The directory is retained after
    shutdown for inspection; callers are responsible for eventual cleanup.
    """

    def __init__(
        self,
        *,
        executable: str | Path,
        entry: str | Path,
        base_dir: str | Path,
        repository_root: str | Path,
        port: int,
        host: str = "127.0.0.1",
        startup_timeout: float = 25.0,
        shutdown_timeout: float = 8.0,
    ) -> None:
        self.executable = Path(executable)
        self.entry = Path(entry)
        self.base_dir = Path(base_dir)
        self.repository_root = Path(repository_root)
        self.port = port
        self.host = host
        self.startup_timeout = startup_timeout
        self.shutdown_timeout = shutdown_timeout
        self.process: subprocess.Popen | None = None
        self._log = None
        self.log_path: Path | None = None

    def _validate(self) -> tuple[Path, Path, Path, Path]:
        for label, path in (
            ("executable", self.executable),
            ("entry", self.entry),
            ("base_dir", self.base_dir),
            ("repository_root", self.repository_root),
        ):
            if not path.is_absolute():
                raise T3ServerLifecycleError(f"{label} must be an absolute path")
        if self.host not in _LOOPBACK_HOSTS:
            raise T3ServerLifecycleError("host must be the literal IPv4 or IPv6 loopback address")
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise T3ServerLifecycleError("port must be an explicit integer from 1 through 65535")
        if self.startup_timeout <= 0 or self.shutdown_timeout <= 0:
            raise T3ServerLifecycleError("startup and shutdown timeouts must be positive")

        executable = self.executable.resolve(strict=True)
        entry = self._validated_entry()
        base_dir = self.base_dir.resolve()
        repository_root = self.repository_root.resolve(strict=True)
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise T3ServerLifecycleError("executable must be an executable regular file")
        if not repository_root.is_dir():
            raise T3ServerLifecycleError("repository_root must be a directory")
        if base_dir == repository_root or repository_root in base_dir.parents:
            raise T3ServerLifecycleError("base_dir must be outside the repository checkout")
        if base_dir == executable or base_dir == entry:
            raise T3ServerLifecycleError("base_dir cannot be the executable or entry file")
        if self.base_dir.is_symlink():
            raise T3ServerLifecycleError("base_dir cannot be a symlink")
        if base_dir.exists() and any(base_dir.iterdir()):
            marker = base_dir / ".codex-managed-t3"
            if marker.is_symlink() or not marker.is_file() or marker.read_text() != "managed-t3-state/v1\n":
                raise T3ServerLifecycleError(
                    "nonempty base_dir is not marked as state owned by this lifecycle helper"
                )
        return executable, entry, base_dir, repository_root

    def _validated_entry(self) -> Path:
        """Validate a regular entry file or Electron's virtual app.asar path."""
        parts = self.entry.parts
        archive_index = next((i for i, part in enumerate(parts) if part.endswith(".asar")), None)
        if archive_index is None:
            entry = self.entry.resolve(strict=True)
            if not entry.is_file():
                raise T3ServerLifecycleError("entry must be a regular file")
            return entry
        archive = Path(*parts[: archive_index + 1]).resolve(strict=True)
        suffix = parts[archive_index + 1 :]
        if not archive.is_file() or not suffix or any(part in ("", ".", "..") for part in suffix):
            raise T3ServerLifecycleError("entry inside app.asar must have a safe module path")
        # Node/Electron understands this virtual path; the OS does not, so only
        # the containing archive is checked as a regular on-disk file.
        return Path(str(archive) + "/" + "/".join(suffix))

    @staticmethod
    def _environment(executable: Path, base_dir: Path) -> dict[str, str]:
        """Return a small environment; never copy ambient credentials/config."""
        paths = {
            "config": base_dir / ".config",
            "data": base_dir / ".local" / "share",
            "cache": base_dir / ".cache",
            "tmp": base_dir / "tmp",
        }
        for directory in paths.values():
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
        return {
            "HOME": str(base_dir),
            "XDG_CONFIG_HOME": str(paths["config"]),
            "XDG_DATA_HOME": str(paths["data"]),
            "XDG_CACHE_HOME": str(paths["cache"]),
            "TMPDIR": str(paths["tmp"]),
            # The explicitly selected executable's directory only. No ambient
            # PATH, proxy, cloud, OAuth, or provider variables are inherited.
            "PATH": str(executable.parent),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            # Required by packaged Electron executables invoked as Node.
            "ELECTRON_RUN_AS_NODE": "1",
        }

    def command(self) -> list[str]:
        """Return the fixed T3 desktop-server invocation for review/testing."""
        executable, entry, base_dir, _ = self._validate()
        return [
            str(executable), str(entry), "serve", "--mode", "desktop",
            "--base-dir", str(base_dir), "--port", str(self.port),
            "--host", self.host, "--no-browser",
        ]

    def start(self) -> subprocess.Popen:
        """Start the explicitly configured child without inheriting credentials."""
        if self.process is not None and self.process.poll() is None:
            raise T3ServerLifecycleError("managed T3 process is already running")
        executable, _, base_dir, _ = self._validate()
        self._assert_port_available()
        argv = self.command()
        base_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        base_dir.chmod(0o700)
        marker = base_dir / ".codex-managed-t3"
        if marker.is_symlink():
            raise T3ServerLifecycleError("managed-state marker cannot be a symlink")
        if not marker.exists():
            marker.write_text("managed-t3-state/v1\n")
            marker.chmod(0o600)
        env = self._environment(executable, base_dir)
        self.log_path = base_dir / "t3-server.log"
        log_fd = os.open(
            self.log_path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        os.fchmod(log_fd, 0o600)
        self._log = os.fdopen(log_fd, "wb")
        try:
            self.process = subprocess.Popen(
                argv,
                cwd=str(base_dir),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=self._log,
                stderr=subprocess.STDOUT,
                close_fds=True,
                start_new_session=True,
            )
        except Exception:
            self._log.close()
            self._log = None
            raise
        return self.process

    def _assert_port_available(self) -> None:
        family = socket.AF_INET6 if self.host == "::1" else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            # Permit rebinding after our previous server's connections enter
            # TIME_WAIT, while still rejecting a live listener on this port.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((self.host, self.port))
            except OSError as exc:
                raise T3ServerLifecycleError(
                    f"configured loopback port {self.port} is already in use or unavailable"
                ) from exc

    def wait_ready(self, timeout: float | None = None) -> None:
        """Wait until the configured loopback port accepts a TCP connection."""
        process = self.process
        if process is None:
            raise T3ServerLifecycleError("start() must be called before wait_ready()")
        deadline = time.monotonic() + (self.startup_timeout if timeout is None else timeout)
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise T3ServerLifecycleError(
                    f"T3 child exited before readiness (exit={process.returncode}); see {self.log_path}"
                )
            remaining = max(0.01, min(0.25, deadline - time.monotonic()))
            try:
                with socket.create_connection((self.host, self.port), timeout=remaining):
                    return
            except OSError:
                time.sleep(min(0.1, remaining))
        raise T3ServerLifecycleError(f"T3 server did not accept loopback connections; see {self.log_path}")

    def shutdown(self) -> None:
        """Stop only this Popen child; descendants are deliberately not signaled."""
        process = self.process
        try:
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass  # It exited between poll() and terminate().
                try:
                    process.wait(timeout=self.shutdown_timeout)
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=self.shutdown_timeout)
        finally:
            if self._log is not None:
                self._log.close()
                self._log = None

    def __enter__(self) -> "T3ServerProcess":
        self.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.shutdown()
