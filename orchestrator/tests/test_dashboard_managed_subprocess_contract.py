"""Real dashboard CLI subprocess against a test-owned managed supervisor.

The fixture intentionally shares the test UID. This verifies the production
health CLI refuses to mistake a same-UID synthetic endpoint for a managed
service with a separately authenticated peer. It makes no dispatch/provider
request and does not relax the production UID contract.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

ORCH = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent


def _wait_socket(path, proc, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise AssertionError(f"synthetic supervisor exited: {proc.stderr.read()}")
        if path.exists():
            return
        time.sleep(0.02)
    raise AssertionError("synthetic supervisor socket did not appear")


@pytest.fixture
def synthetic_managed_supervisor():
    with tempfile.TemporaryDirectory(prefix="dash-managed-cli-") as temp:
        root = Path(temp)
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            probe.bind(str(root / "socket-probe"))
        except OSError as exc:
            pytest.skip(f"environment disallows Unix socket binding: {type(exc).__name__}")
        finally:
            probe.close()
            try:
                (root / "socket-probe").unlink()
            except FileNotFoundError:
                pass
        socket_dir = root / "socket"
        socket_dir.mkdir(mode=0o750)
        socket_dir.chmod(0o2750)
        state_dir = root / "state"
        state_dir.mkdir(mode=0o700)
        token_path = root / "peer.token"
        token_path.write_text("synthetic-cli-peer-token-0123456789")
        token_path.chmod(0o600)
        mcp_path = root / "mcp.token"
        mcp_path.write_text("synthetic-cli-mcp-token-0123456789")
        mcp_path.chmod(0o600)
        socket_path = socket_dir / "managed.sock"
        proc = subprocess.Popen(
            [
                sys.executable,
                str(TESTS / "_synthetic_managed_supervisor_server.py"),
                "--socket",
                str(socket_path),
                "--state",
                str(state_dir / "state.json"),
                "--token-file",
                str(token_path),
                "--base-url",
                "http://127.0.0.1:1",
                "--mcp-token-file",
                str(mcp_path),
                "--model",
                "opencode-go/deepseek-v4.1-flash",
                "--allowed-model",
                "opencode-go/deepseek-v4.1-flash",
                "--peer-uid",
                str(os.geteuid()),
            ],
            cwd=ORCH,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _wait_socket(socket_path, proc)
            ready = proc.stdout.readline()
            assert '"ready": true' in ready
            yield root, socket_path, token_path, proc
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


def test_dashboard_cli_reports_same_uid_peer_as_not_managed(synthetic_managed_supervisor):
    root, socket_path, token_path, _proc = synthetic_managed_supervisor

    # The synthetic managed service is reachable and the kernel reports the
    # actual same UID. Its read-only health claims the experimental protocol,
    # so it cannot satisfy the dashboard's distinct-UID managed contract.
    sys.path.insert(0, str(ORCH))
    from t3_supervisor_client import SupervisorClient

    health = SupervisorClient(socket_path, token_path.read_text().strip()).call("health")
    assert health["uid"] == os.geteuid()
    assert health["read_only"] is False
    assert health["protocol"] == "experimental-managed-supervisor/v1"

    config_path = root / "dashboard-supervisor.json"
    config_path.write_text(
        json.dumps(
            {
                "schema": "dashboard-managed-supervisor/v1",
                "dispatch_enabled": False,
                "socket_path": str(socket_path),
                "token_file": str(token_path),
                "expected_uid": os.geteuid() + 1,
                "socket_group_gid": os.getegid(),
                "allowed_models": ["opencode-go/deepseek-v4.1-flash"],
            }
        )
    )
    config_path.chmod(0o600)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(root),
            "--action",
            "supervisor_health",
            "--managed-supervisor-config",
            str(config_path),
        ],
        cwd=ORCH.parent,
        text=True,
        capture_output=True,
        timeout=10,
        env={**os.environ, "PYTHONPATH": str(ORCH.parent) + os.pathsep + os.environ.get("PYTHONPATH", "")},
    )
    assert result.returncode != 0
    assert "supervisor socket owner/group mismatch" in result.stderr
    assert "synthetic-cli-peer-token" not in result.stdout + result.stderr


def test_distinct_peer_uid_config_refuses_dashboard_uid(synthetic_managed_supervisor):
    root, socket_path, token_path, _proc = synthetic_managed_supervisor
    config_path = root / "same-uid.json"
    config_path.write_text(
        json.dumps(
            {
                "schema": "dashboard-managed-supervisor/v1",
                "dispatch_enabled": False,
                "socket_path": str(socket_path),
                "token_file": str(token_path),
                "expected_uid": os.geteuid(),
                "socket_group_gid": os.getegid(),
                "allowed_models": ["opencode-go/deepseek-v4.1-flash"],
            }
        )
    )
    config_path.chmod(0o600)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(root),
            "--action",
            "supervisor_health",
            "--managed-supervisor-config",
            str(config_path),
        ],
        cwd=ORCH.parent,
        text=True,
        capture_output=True,
        timeout=10,
        env={**os.environ, "PYTHONPATH": str(ORCH.parent) + os.pathsep + os.environ.get("PYTHONPATH", "")},
    )
    assert result.returncode != 0
    assert "dedicated UID distinct from the dashboard" in result.stderr
