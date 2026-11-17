"""Test-only combined lifecycle for an isolated T3 server and managed supervisor.

The supervisor and synthetic MCP simulator stay in this runner process. The
T3 server is launched as its child, so it inherits the runner's cgroup. The
supervisor's only outbound endpoint is the simulator bound to loopback; no
provider endpoint or ambient credentials are accepted by this helper.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
from pathlib import Path

from _mcp_sim import SimServer, SimState
from managed_supervisor_service import ExperimentalManagedDispatcher
from t3_server_lifecycle import T3ServerProcess
from t3_supervisor import Supervisor

SYNTHETIC_MODEL = "opencode/synthetic-managed-runner"
SYNTHETIC_PROTOCOL_TOKEN = "synthetic-managed-protocol-token-0123456789"
SYNTHETIC_MCP_TOKEN = "synthetic-managed-mcp-token-0123456789"


class IsolatedManagedT3RunnerError(RuntimeError):
    """Combined runner configuration, startup, or cleanup failure."""


def _cgroup_membership(pid: int) -> tuple[str, ...]:
    """Return kernel cgroup membership for a live process, failing closed."""
    try:
        rows = Path(f"/proc/{pid}/cgroup").read_text(encoding="ascii").splitlines()
    except OSError as exc:
        raise IsolatedManagedT3RunnerError(
            f"cannot inspect process cgroup membership: {type(exc).__name__}"
        ) from None
    if not rows:
        raise IsolatedManagedT3RunnerError("process has no inspectable cgroup membership")
    return tuple(rows)


class IsolatedManagedT3Runner:
    """Start and own one test T3 process plus a colocated supervisor service.

    ``runtime_dir`` must be a dedicated directory outside the repository.
    The server executable and entry are supplied through ``T3ServerProcess``;
    tests should use a local inert fixture. Shutdown also targets the server's
    private process group to reap descendants that remain in its new session.
    This is a test harness, not an OS sandbox or production service manager.
    """

    def __init__(self, *, server: T3ServerProcess, runtime_dir: str | Path, simulator_factory=SimServer):
        self.server = server
        self.runtime_dir = Path(runtime_dir)
        self.sim_state = SimState(token=SYNTHETIC_MCP_TOKEN)
        self.simulator = simulator_factory(self.sim_state)
        self.supervisor_core: Supervisor | None = None
        self.supervisor_service: ExperimentalManagedDispatcher | None = None
        self._service_thread: threading.Thread | None = None
        self._simulator_started = False
        self._started = False

    def _prepare_runtime(self) -> tuple[Path, Path]:
        if not self.runtime_dir.is_absolute() or self.runtime_dir.is_symlink():
            raise IsolatedManagedT3RunnerError("runtime_dir must be an absolute non-symlink path")
        self.runtime_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        metadata = self.runtime_dir.stat()
        if metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
            raise IsolatedManagedT3RunnerError("runtime_dir must be owned by this UID and private")
        repository_root = getattr(self.server, "repository_root", None)
        if repository_root is not None:
            root = Path(repository_root).resolve(strict=True)
            runtime = self.runtime_dir.resolve(strict=True)
            if runtime == root or root in runtime.parents:
                raise IsolatedManagedT3RunnerError("runtime_dir must be outside the repository checkout")

        state_dir = self.runtime_dir / "supervisor-state"
        if state_dir.is_symlink():
            raise IsolatedManagedT3RunnerError("supervisor state directory cannot be a symlink")
        state_dir.mkdir(mode=0o700, exist_ok=True)
        state_metadata = state_dir.stat()
        if state_metadata.st_uid != os.geteuid() or state_metadata.st_mode & 0o077:
            raise IsolatedManagedT3RunnerError("supervisor state directory must be service-owned and private")
        socket_dir = self.runtime_dir / "supervisor-socket"
        if socket_dir.is_symlink():
            raise IsolatedManagedT3RunnerError("supervisor socket directory cannot be a symlink")
        socket_dir.mkdir(mode=0o750, exist_ok=True)
        socket_dir.chmod(0o2750)
        if socket_dir.stat().st_uid != os.geteuid() or socket_dir.stat().st_gid != os.getegid():
            raise IsolatedManagedT3RunnerError("test socket directory ownership mismatch")
        return state_dir, socket_dir

    def start(self) -> IsolatedManagedT3Runner:
        if self._started:
            raise IsolatedManagedT3RunnerError("combined runner is already started")
        try:
            state_dir, socket_dir = self._prepare_runtime()
            self.simulator.__enter__()
            self._simulator_started = True
            self.supervisor_core = Supervisor(
                socket_path=socket_dir / "managed.sock",
                state_path=state_dir / "state.json",
                token=SYNTHETIC_PROTOCOL_TOKEN,
                base_url=self.simulator.url,
                mcp_token=SYNTHETIC_MCP_TOKEN,
                model=SYNTHETIC_MODEL,
                allowed_models=[SYNTHETIC_MODEL],
                peer_uid=os.geteuid() + 1,
            )
            self.supervisor_service = ExperimentalManagedDispatcher(
                core=self.supervisor_core,
                socket_path=socket_dir / "managed.sock",
                token=SYNTHETIC_PROTOCOL_TOKEN,
                client_uid=os.geteuid() + 1,
                socket_group_gid=os.getegid(),
                timeout=0.2,
            )

            self.server.start()
            process = self.server.process
            if process is None:
                raise IsolatedManagedT3RunnerError("T3 lifecycle did not return a child process")
            self.server.wait_ready()
            if _cgroup_membership(os.getpid()) != _cgroup_membership(process.pid):
                raise IsolatedManagedT3RunnerError("T3 child did not inherit runner cgroup membership")

            self.supervisor_service.start()
            self._service_thread = threading.Thread(
                target=self.supervisor_service.serve_forever,
                name="test-managed-supervisor",
                daemon=True,
            )
            self._service_thread.start()
            self._started = True
            return self
        except BaseException:
            self._cleanup(suppress_errors=True)
            raise

    def _stop_server_group(self) -> None:
        process = self.server.process
        if process is None or process.poll() is not None:
            self.server.shutdown()
            return
        try:
            process_group = os.getpgid(process.pid)
        except ProcessLookupError:
            self.server.shutdown()
            return
        if process_group != process.pid:
            self.server.shutdown()
            raise IsolatedManagedT3RunnerError("T3 lifecycle child no longer owns its private process group")
        try:
            os.killpg(process_group, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=self.server.shutdown_timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process_group, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=self.server.shutdown_timeout)
        finally:
            self.server.shutdown()

    def _cleanup(self, *, suppress_errors: bool) -> None:
        errors = []
        if self.supervisor_service is not None:
            try:
                self.supervisor_service.close()
            except Exception as exc:  # cleanup must continue across independent resources
                errors.append(exc)
        if self._service_thread is not None:
            self._service_thread.join(timeout=2.0)
            if self._service_thread.is_alive():
                errors.append(IsolatedManagedT3RunnerError("supervisor service thread did not stop"))
            self._service_thread = None
        try:
            self._stop_server_group()
        except Exception as exc:
            errors.append(exc)
        if self._simulator_started:
            try:
                self.simulator.__exit__(None, None, None)
            except Exception as exc:
                errors.append(exc)
            self._simulator_started = False
        self._started = False
        if errors and not suppress_errors:
            raise IsolatedManagedT3RunnerError(
                "combined runner cleanup had failures: " + ", ".join(type(err).__name__ for err in errors)
            )

    def close(self) -> None:
        """Stop the managed service, T3 process group, and simulator."""
        self._cleanup(suppress_errors=False)

    def __enter__(self) -> IsolatedManagedT3Runner:
        return self.start()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._cleanup(suppress_errors=exc is not None)
