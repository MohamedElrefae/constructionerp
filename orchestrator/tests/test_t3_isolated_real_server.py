"""Optional smoke test against a disposable, network-isolated T3 server.

The caller must supply a packaged T3 executable and server entry point inside
an independently isolated environment. No provider tasks are started.
"""

import os
import shutil
import shlex
import socket
import time
import urllib.error
import urllib.request
import pytest

from t3_transport import HttpT3Client, TransportRefusal, obtain_mcp_token
from t3_server_lifecycle import T3ServerProcess
from t3_provider_setup import prepare_opencode_go_deepseek


@pytest.mark.skipif(not os.environ.get("T3_TEST_EXECUTABLE"), reason="isolated T3 package not supplied")
def test_real_server_starts_and_lists_mcp_tools(tmp_path):
    exe = os.environ["T3_TEST_EXECUTABLE"]
    entry = os.environ["T3_TEST_ENTRY"]
    root = tmp_path / "isolated-t3"
    env = dict(os.environ, ELECTRON_RUN_AS_NODE="1", XDG_CACHE_HOME=str(tmp_path / "cache"),
               T3CODE_HOME=str(root))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    server = T3ServerProcess(executable=exe, entry=entry, base_dir=root,
                             repository_root=os.getcwd(), port=port)
    proc = server.start()
    try:
        deadline = time.monotonic() + 25
        ready = False
        while time.monotonic() < deadline and proc.poll() is None:
            try:
                with urllib.request.urlopen(base_url, timeout=0.5) as response:
                    ready = response.status < 500
            except urllib.error.HTTPError as exc:
                ready = exc.code < 500
            except OSError:
                pass
            if ready:
                break
            time.sleep(0.2)
        assert ready, "isolated T3 server did not start"
        wrapper = tmp_path / "t3-cli"
        wrapper.write_text(f"#!/bin/sh\nexec {shlex.quote(exe)} {shlex.quote(entry)} \"$@\"\n")
        wrapper.chmod(0o700)
        token = obtain_mcp_token(base_url=base_url, t3_cli=str(wrapper),
                                 scopes=("orchestration:read",), env=env)["access_token"]
        client = HttpT3Client(base_url, token)
        client.initialize()
        tools = client.list_tools()
        assert "t3_thread_read" in tools
        assert "t3_thread_launch" in tools
        # A fresh server has no enabled provider. Even an idle scratch thread
        # must fail closed until a provider is explicitly configured.
        operate_token = obtain_mcp_token(
            base_url=base_url, t3_cli=str(wrapper),
            scopes=("orchestration:read", "orchestration:operate"),
            access="approval-required", env=env)["access_token"]
        operate = HttpT3Client(base_url, operate_token)
        operate.initialize()
        capabilities = operate._tool("orchestrator_capabilities", {})
        assert capabilities.get("providers"), "isolated T3 has no configured providers"
        with pytest.raises(TransportRefusal, match="disabled"):
            operate._tool("t3_thread_launch", {
                "title": "isolated integration contract check", "scratch": True,
                "modelSelection": {"provider": "opencode", "model": "opencode/deepseek-v4.1-flash-free"},
            })
        server.shutdown()
        server.start()
        server.wait_ready()
        restarted = HttpT3Client(base_url, token)
        deadline = time.monotonic() + 20
        while True:
            try:
                restarted.initialize()
                break
            except TransportRefusal as exc:
                if "HTTP 503" not in str(exc) or time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)
        assert "t3_thread_read" in restarted.list_tools()
    finally:
        server.shutdown()


@pytest.mark.skipif(not os.environ.get("T3_TEST_EXECUTABLE"), reason="isolated T3 package not supplied")
def test_configured_go_provider_can_create_idle_thread(tmp_path):
    exe = os.environ["T3_TEST_EXECUTABLE"]
    entry = os.environ["T3_TEST_ENTRY"]
    root = tmp_path / "go-t3"
    prepare_opencode_go_deepseek(
        base_dir=root, repository_root=os.getcwd(),
        opencode_binary="/var/tmp/guard-rehearsal-stubs/opencode",
    )
    env = dict(os.environ, ELECTRON_RUN_AS_NODE="1", XDG_CACHE_HOME=str(tmp_path / "cache"),
               T3CODE_HOME=str(root))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    server = T3ServerProcess(executable=exe, entry=entry, base_dir=root,
                             repository_root=os.getcwd(), port=port)
    server.start()
    try:
        deadline = time.monotonic() + 25
        while True:
            try:
                with urllib.request.urlopen(base_url, timeout=0.5) as response:
                    if response.status < 500:
                        break
            except urllib.error.HTTPError as exc:
                if exc.code < 500:
                    break
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise AssertionError("isolated T3 server did not become ready")
            time.sleep(0.2)
        wrapper = tmp_path / "t3-cli"
        wrapper.write_text(f"#!/bin/sh\nexec {shlex.quote(exe)} {shlex.quote(entry)} \"$@\"\n")
        wrapper.chmod(0o700)
        token = obtain_mcp_token(base_url=base_url, t3_cli=str(wrapper),
                                 scopes=("orchestration:read", "orchestration:operate"),
                                 access="approval-required", env=env)["access_token"]
        client = HttpT3Client(base_url, token)
        client.initialize()
        launched = client._tool("t3_thread_launch", {
            "title": "isolated Go model contract", "scratch": True,
            "modelSelection": {"instanceId": "opencode", "model": "opencode-go/deepseek-v4.1-flash"},
        })
        assert launched.get("threadId")
        assert launched.get("runId") is None
        assert launched["modelSelection"]["model"] == "opencode-go/deepseek-v4.1-flash"
    finally:
        server.shutdown()


@pytest.mark.skipif(not os.environ.get("T3_TEST_AUTH_SOURCE"), reason="isolated credential test not requested")
def test_signed_in_go_provider_is_available_in_real_t3(tmp_path):
    """Probe configuration only; no thread, model prompt, or provider request."""
    exe = os.environ["T3_TEST_EXECUTABLE"]
    entry = os.environ["T3_TEST_ENTRY"]
    root = tmp_path / "go-authenticated"
    setup = prepare_opencode_go_deepseek(
        base_dir=root, repository_root=os.getcwd(),
        opencode_binary=os.environ["T3_TEST_OPENCODE_BINARY"],
    )
    setup.auth_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copyfile(os.environ["T3_TEST_AUTH_SOURCE"], setup.auth_path)
    setup.auth_path.chmod(0o600)
    env = dict(os.environ, ELECTRON_RUN_AS_NODE="1", XDG_CACHE_HOME=str(tmp_path / "cache"),
               T3CODE_HOME=str(root))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    server = T3ServerProcess(executable=exe, entry=entry, base_dir=root,
                             repository_root=os.getcwd(), port=port)
    server.start()
    try:
        deadline = time.monotonic() + 25
        while True:
            try:
                with urllib.request.urlopen(base_url, timeout=0.5) as response:
                    if response.status < 500:
                        break
            except urllib.error.HTTPError as exc:
                if exc.code < 500:
                    break
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise AssertionError("isolated T3 server did not become ready")
            time.sleep(0.2)
        wrapper = tmp_path / "t3-cli"
        wrapper.write_text(f"#!/bin/sh\nexec {shlex.quote(exe)} {shlex.quote(entry)} \"$@\"\n")
        wrapper.chmod(0o700)
        token = obtain_mcp_token(base_url=base_url, t3_cli=str(wrapper),
                                 scopes=("orchestration:read",), env=env)["access_token"]
        client = HttpT3Client(base_url, token)
        client.initialize()
        deadline = time.monotonic() + 20
        while True:
            capabilities = client._tool("orchestrator_capabilities", {"search": "deepseek-v4.1-flash"})
            providers = [p for p in capabilities.get("providers", [])
                         if p.get("providerInstanceId") == "opencode"]
            assert len(providers) == 1, "OpenCode provider missing"
            if providers[0].get("canRunChildTask"):
                break
            if time.monotonic() >= deadline:
                raise AssertionError("OpenCode provider not ready in isolated profile")
            time.sleep(0.5)
    finally:
        server.shutdown()
