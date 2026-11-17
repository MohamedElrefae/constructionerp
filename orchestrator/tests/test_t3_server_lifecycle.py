import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from t3_server_lifecycle import T3ServerLifecycleError, T3ServerProcess


def _test_server(tmp_path: Path, *, host="127.0.0.1", port=43127):
    repository = tmp_path / "checkout"
    repository.mkdir()
    entry = tmp_path / "synthetic_t3.py"
    entry.write_text(
        "import json, os, pathlib, sys, time\n"
        "pathlib.Path(os.environ['HOME'], 'child.json').write_text(json.dumps({"
        "'argv': sys.argv[1:], 'env': dict(os.environ)}))\n"
        "while True: time.sleep(1)\n"
    )
    return T3ServerProcess(
        executable=Path(sys.executable).resolve(),
        entry=entry.resolve(),
        base_dir=(tmp_path / "isolated-state").resolve(),
        repository_root=repository.resolve(),
        port=port,
        host=host,
        startup_timeout=2,
        shutdown_timeout=2,
    )


def test_synthetic_child_gets_fixed_loopback_command_and_clean_private_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-secret-must-not-pass")
    monkeypatch.setenv("T3CODE_HOME", "/ambient/t3-home")
    server = _test_server(tmp_path)
    monkeypatch.setattr(server, "_assert_port_available", lambda: None)
    process = server.start()
    try:
        child_record = server.base_dir / "child.json"
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not child_record.exists():
            time.sleep(0.02)
        assert child_record.exists()
        observed = json.loads(child_record.read_text())
        assert observed["argv"] == [
            "serve",
            "--mode",
            "desktop",
            "--base-dir",
            str(server.base_dir),
            "--port",
            "43127",
            "--host",
            "127.0.0.1",
            "--no-browser",
        ]
        child_env = observed["env"]
        assert child_env["HOME"] == str(server.base_dir)
        assert child_env["XDG_CONFIG_HOME"] == str(server.base_dir / ".config")
        assert child_env["XDG_DATA_HOME"] == str(server.base_dir / ".local" / "share")
        assert child_env["XDG_CACHE_HOME"] == str(server.base_dir / ".cache")
        assert child_env["TMPDIR"] == str(server.base_dir / "tmp")
        assert child_env["PATH"] == str(Path(sys.executable).resolve().parent)
        assert child_env["ELECTRON_RUN_AS_NODE"] == "1"
        assert "OPENAI_API_KEY" not in child_env
        assert "T3CODE_HOME" not in child_env
        assert server.log_path.is_file()
        assert server.log_path.stat().st_mode & 0o777 == 0o600
    finally:
        server.shutdown()
    assert process.poll() is not None
    assert process.returncode == 0 or process.returncode == -15


@pytest.mark.parametrize("host", ["localhost", "0.0.0.0", "192.0.2.1", "::"])
def test_rejects_non_literal_loopback_hosts_before_starting(tmp_path, host):
    server = _test_server(tmp_path, host=host)
    with pytest.raises(T3ServerLifecycleError, match="literal.*loopback"):
        server.start()
    assert server.process is None


def test_rejects_data_directory_inside_checkout(tmp_path):
    server = _test_server(tmp_path)
    server.base_dir = server.repository_root / "t3-state"
    with pytest.raises(T3ServerLifecycleError, match="outside the repository"):
        server.start()
    assert server.process is None


def test_readiness_probe_uses_only_configured_loopback_and_requires_started_child(tmp_path):
    server = _test_server(tmp_path)
    server._assert_port_available = lambda: None
    with pytest.raises(T3ServerLifecycleError, match=r"start\(\)"):
        server.wait_ready()
    process = server.start()

    class ReadySocket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    try:
        with patch("t3_server_lifecycle.socket.create_connection", return_value=ReadySocket()) as connect:
            server.wait_ready(timeout=0.5)
        assert connect.call_args.args[0] == ("127.0.0.1", 43127)
    finally:
        server.shutdown()
    assert process.poll() is not None


def test_refuses_nonempty_existing_data_directory(tmp_path):
    server = _test_server(tmp_path)
    server.base_dir.mkdir()
    (server.base_dir / "unrelated").write_text("existing state")
    with pytest.raises(T3ServerLifecycleError, match="not marked as state owned"):
        server.start()
    assert server.process is None


def test_app_asar_virtual_entry_validates_archive_and_preserves_virtual_path(tmp_path):
    server = _test_server(tmp_path)
    archive = tmp_path / "resources" / "app.asar"
    archive.parent.mkdir()
    archive.write_bytes(b"synthetic archive marker")
    server.entry = Path(str(archive) + "/dist/cli.js")
    assert server.command()[1] == str(archive) + "/dist/cli.js"


def test_existing_managed_data_directory_can_be_reused(tmp_path, monkeypatch):
    server = _test_server(tmp_path)
    monkeypatch.setattr(server, "_assert_port_available", lambda: None)
    first = server.start()
    server.shutdown()
    assert first.poll() is not None
    second = server.start()
    try:
        assert second.poll() is None
        assert (server.base_dir / ".codex-managed-t3").is_file()
    finally:
        server.shutdown()
