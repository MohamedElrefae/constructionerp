"""No-provider tests for read-only managed supervisor socket and peer behavior."""

import json
import os
import socket
import stat
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ORCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ORCH))

from managed_supervisor_service import (  # noqa: E402
    ExperimentalManagedDispatcher,
    ManagedSupervisorServiceError,
    ManagedSupervisorServiceConfig,
    ReadOnlyManagedSupervisor,
    _frame,
    build_managed_dispatcher,
)
from t3_supervisor import Supervisor  # noqa: E402


class FakeListener:
    def __init__(self, *_args):
        self.closed = False
        self.bound = None

    def bind(self, path):
        self.bound = path

    def listen(self, _backlog):
        pass

    def settimeout(self, _timeout):
        pass

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, peer_uid, request=None):
        self.peer_uid = peer_uid
        self.input = bytearray(_frame(request) if request is not None else b"")
        self.output = bytearray()

    def getsockopt(self, *_args):
        return struct.pack("3i", 123, self.peer_uid, 456)

    def recv(self, amount):
        chunk = self.input[:amount]
        del self.input[:amount]
        return bytes(chunk)

    def sendall(self, value):
        self.output.extend(value)


class ManagedSupervisorServiceTests(unittest.TestCase):
    def make_service(self, directory):
        os.chmod(directory, 0o2750)
        return ReadOnlyManagedSupervisor(
            socket_path=directory / "supervisor.sock",
            token="synthetic-service-token-0123456789",
            client_uid=os.geteuid() + 1,
            socket_group_gid=os.getegid(),
        )

    def test_lifecycle_binds_restricted_socket_and_cleans_only_its_inode(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-service-") as tmp:
            service = self.make_service(Path(tmp))
            fake_socket = FakeListener()
            socket_stat = SimpleNamespace(
                st_mode=stat.S_IFSOCK | 0o660,
                st_uid=os.geteuid(), st_gid=os.getegid(), st_dev=1, st_ino=2,
            )
            with mock.patch("managed_supervisor_service.socket.socket", return_value=fake_socket), \
                    mock.patch("managed_supervisor_service.os.chmod"), \
                    mock.patch("pathlib.Path.lstat", return_value=socket_stat), \
                    mock.patch("managed_supervisor_service.os.unlink") as unlink:
                service.start()
                self.assertIs(service.listener, fake_socket)
                self.assertEqual(fake_socket.bound, str(service.socket_path))
                service.close()
                self.assertTrue(fake_socket.closed)
                unlink.assert_called_once_with(service.socket_path)

    def test_health_is_authenticated_read_only_and_dispatch_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-protocol-") as tmp:
            service = self.make_service(Path(tmp))
            health_conn = FakeConnection(service.client_uid, {
                "op": "health", "token": service.token, "payload": {},
            })
            service._handle(health_conn)
            (size,) = struct.unpack(">I", health_conn.output[:4])
            health = json.loads(health_conn.output[4:4 + size])
            self.assertTrue(health["ok"])
            self.assertTrue(health["result"]["read_only"])
            self.assertFalse(health["result"]["builder_enabled"])
            self.assertEqual(health["result"]["protocol"], "managed-supervisor-health/v1")

            dispatch_conn = FakeConnection(service.client_uid, {
                "op": "dispatch", "token": service.token, "payload": {"job": {"job_id": "job-1"}},
            })
            service._handle(dispatch_conn)
            (size,) = struct.unpack(">I", dispatch_conn.output[:4])
            refused = json.loads(dispatch_conn.output[4:4 + size])
            self.assertEqual(refused["error"]["code"], "DISPATCH_DISABLED")

    def test_failed_socket_setup_removes_only_the_bound_inode(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-bind-failure-") as tmp:
            service = self.make_service(Path(tmp))
            fake_socket = FakeListener()
            socket_stat = SimpleNamespace(st_mode=stat.S_IFSOCK | 0o600,
                                          st_uid=os.geteuid(), st_gid=os.getegid(),
                                          st_dev=1, st_ino=2)
            with mock.patch("managed_supervisor_service.socket.socket", return_value=fake_socket), \
                    mock.patch("managed_supervisor_service.os.chmod", side_effect=PermissionError), \
                    mock.patch("pathlib.Path.lstat", return_value=socket_stat), \
                    mock.patch("os.unlink") as unlink:
                with self.assertRaises(PermissionError):
                    service.start()
                unlink.assert_called_once_with(service.socket_path)
                self.assertTrue(fake_socket.closed)

    def test_wrong_peer_is_rejected_before_request_or_token_processing(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-peer-") as tmp:
            service = self.make_service(Path(tmp))
            conn = FakeConnection(os.geteuid(), None)
            service._handle(conn)
            (size,) = struct.unpack(">I", conn.output[:4])
            rejected = json.loads(conn.output[4:4 + size])
            self.assertEqual(rejected["error"]["code"], "PEER_REJECTED")
            self.assertEqual(conn.input, bytearray())

    def test_experimental_bridge_authenticates_and_dispatches_to_state_machine(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-bridge-") as tmp:
            directory = Path(tmp)
            base = self.make_service(directory)
            model = "opencode/deepseek-v4.1-flash-free"
            job_id = "job-" + "a" * 24
            marker = "ENGINE-T3-RESULT " + job_id
            core = Supervisor(socket_path=base.socket_path, state_path=directory / "state.json",
                              token=base.token, base_url="http://127.0.0.1:1",
                              mcp_token="synthetic-mcp-token", model=model,
                              allowed_models=[model], peer_uid=base.client_uid)
            provider = mock.Mock()
            provider.delegate.return_value = {"taskId": "synthetic-thread"}
            provider.status.return_value = {"status": "completed", "summary": marker,
                                            "model": model}
            core._client = lambda: provider
            service = ExperimentalManagedDispatcher(
                core=core, socket_path=base.socket_path, token=base.token,
                client_uid=base.client_uid, socket_group_gid=base.socket_group_gid,
                attestation_verifier=lambda _path: True)

            def call(request, uid=None):
                conn = FakeConnection(base.client_uid if uid is None else uid, request)
                service._handle(conn)
                (size,) = struct.unpack(">I", conn.output[:4])
                return json.loads(conn.output[4:4 + size])

            job = {"job_id": job_id, "client_request_id": "wp1-engine-job-" + "b" * 32,
                   "model": model, "brief": "Compute 6 * 7.", "role": "reviewer",
                   "expect_marker": marker}
            request = {"op": "dispatch", "token": base.token, "payload": {"job": job}}
            self.assertEqual(call(request, uid=os.geteuid())["error"]["code"], "PEER_REJECTED")
            self.assertEqual(call(dict(request, token="bad"))["error"]["code"], "UNAUTHORIZED")
            self.assertEqual(call(dict(request, token="\u00e9"))["error"]["code"], "UNAUTHORIZED")
            self.assertEqual(call(request)["result"]["state"], "dispatched")
            self.assertEqual(call(request)["result"]["state"], "dispatched")
            result = call({"op": "collect", "token": base.token,
                           "payload": {"job_id": job_id}})
            self.assertEqual(result["result"]["state"], "completed")
            provider.delegate.assert_called_once()

    def test_dispatch_and_health_fail_closed_without_live_attestation(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-attest-gate-") as tmp:
            directory = Path(tmp)
            base = self.make_service(directory)
            core = Supervisor(socket_path=base.socket_path, state_path=directory / "state.json",
                              token=base.token, base_url="http://127.0.0.1:1",
                              mcp_token="synthetic-mcp-token", model="model",
                              allowed_models=["model"], peer_uid=base.client_uid,
                              builder_enabled=True)
            core.handle = mock.Mock(side_effect=AssertionError("core must not be reached"))
            service = ExperimentalManagedDispatcher(
                core=core, socket_path=base.socket_path, token=base.token,
                client_uid=base.client_uid, socket_group_gid=base.socket_group_gid,
                attestation_verifier=mock.Mock(side_effect=RuntimeError("missing record")),
            )
            for operation in ("health", "dispatch"):
                conn = FakeConnection(base.client_uid, {
                    "op": operation, "token": base.token, "payload": {},
                })
                service._handle(conn)
                (size,) = struct.unpack(">I", conn.output[:4])
                response = json.loads(conn.output[4:4 + size])
                self.assertEqual(response["error"]["code"], "SERVICE_ATTESTATION_FAILED")
            core.handle.assert_not_called()

            # A verifier must positively confirm attestation; a false return is
            # a denial just like an exception, not permission to reach the core.
            service.attestation_verifier = mock.Mock(return_value=False)
            response = service._respond({"op": "dispatch", "token": base.token, "payload": {}})
            self.assertEqual(response["error"]["code"], "SERVICE_ATTESTATION_FAILED")
            core.handle.assert_not_called()

    def test_default_dispatcher_uses_fixed_root_verifier_client(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-default-root-check-") as tmp:
            directory = Path(tmp)
            base = self.make_service(directory)
            core = Supervisor(socket_path=base.socket_path, state_path=directory / "state.json",
                              token=base.token, base_url="http://127.0.0.1:1",
                              mcp_token="synthetic-mcp-token", model="model",
                              allowed_models=["model"], peer_uid=base.client_uid,
                              builder_enabled=True)
            with mock.patch("managed_supervisor_attestation.verify_via_root_service",
                            return_value=True) as verify:
                service = ExperimentalManagedDispatcher(
                    core=core, socket_path=base.socket_path, token=base.token,
                    client_uid=base.client_uid, socket_group_gid=base.socket_group_gid)
                response = service._respond({"op": "health"})
            verify.assert_called_once_with(service.attestation_path)
            self.assertTrue(response["ok"])
            self.assertTrue(response["result"]["attested"])
            self.assertTrue(response["result"]["builder_enabled"])

    def test_legacy_state_does_not_relaunch_or_claim_verified_retry(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-legacy-") as tmp:
            directory = Path(tmp)
            base = self.make_service(directory)
            core = Supervisor(socket_path=base.socket_path, state_path=directory / "state.json",
                              token=base.token, base_url="http://127.0.0.1:1",
                              mcp_token="synthetic-mcp-token", model="model",
                              allowed_models=["model"], peer_uid=base.client_uid)
            job = {"job_id": "job-1", "client_request_id": "request-1", "model": "model",
                   "role": "reviewer", "brief": "test", "expect_marker": "marker"}
            core.state.put("job-1", {"state": "dispatched", "task_id": "old-thread",
                                     "client_request_id": "request-1"})
            provider = mock.Mock()
            core._client = lambda: provider
            result = core._dispatch(job)
            self.assertEqual(result["state"], "uncertain")
            self.assertEqual(result["task_id"], "old-thread")
            provider.delegate.assert_not_called()

    def test_supervisor_state_remains_private_after_atomic_replacements(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-state-") as tmp:
            directory = Path(tmp)
            base = self.make_service(directory)
            core = Supervisor(socket_path=base.socket_path, state_path=directory / "state.json",
                              token=base.token, base_url="http://127.0.0.1:1",
                              mcp_token="synthetic-mcp-token", model="model",
                              allowed_models=["model"], peer_uid=base.client_uid)
            core.state.put("job-1", {"state": "launching"})
            self.assertEqual(stat.S_IMODE(core.state.path.stat().st_mode), 0o600)
            core.state.put("job-1", {"state": "uncertain"})
            self.assertEqual(stat.S_IMODE(core.state.path.stat().st_mode), 0o600)
            self.assertEqual(json.loads(core.state.path.read_text())["jobs"]["job-1"]["state"], "uncertain")

    def test_supervisor_refuses_symlinked_or_public_existing_state(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-state-check-") as tmp:
            directory = Path(tmp)
            base = self.make_service(directory)
            path = directory / "state.json"
            target = directory / "target.json"
            target.write_text('{"jobs": {}}')
            os.chmod(target, 0o600)
            path.symlink_to(target)
            kwargs = dict(socket_path=base.socket_path, state_path=path, token=base.token,
                          base_url="http://127.0.0.1:1", mcp_token="synthetic-token",
                          model="model", allowed_models=["model"], peer_uid=base.client_uid)
            with self.assertRaises(SystemExit):
                Supervisor(**kwargs)
            path.unlink()
            path.write_text('{"jobs": {}}')
            os.chmod(path, 0o644)
            with self.assertRaises(SystemExit):
                Supervisor(**kwargs)

    def test_mcp_initialization_failure_is_proven_non_launch(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-init-") as tmp:
            directory = Path(tmp)
            base = self.make_service(directory)
            core = Supervisor(socket_path=base.socket_path, state_path=directory / "state.json",
                              token=base.token, base_url="http://127.0.0.1:1",
                              mcp_token="synthetic-mcp-token", model="model",
                              allowed_models=["model"], peer_uid=base.client_uid)
            core._client = mock.Mock(side_effect=RuntimeError("test initialization failure"))
            job = {"job_id": "job-1", "client_request_id": "request-1", "model": "model",
                   "role": "reviewer", "brief": "test", "expect_marker": "marker"}
            result = core._dispatch(job)
            self.assertEqual(result["state"], "prelaunch_failed")
            self.assertIsNone(core.state.get("job-1"))

    def test_rejects_same_uid_and_insecure_parent(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-invalid-") as tmp:
            directory = Path(tmp)
            os.chmod(directory, 0o700)
            with self.assertRaisesRegex(ManagedSupervisorServiceError, "distinct"):
                ReadOnlyManagedSupervisor(
                    socket_path=directory / "sup.sock", token="synthetic-service-token-0123456789",
                    client_uid=os.geteuid(), socket_group_gid=os.getegid())._validate()
            service = self.make_service(directory)
            os.chmod(directory, 0o2777)
            with self.assertRaisesRegex(ManagedSupervisorServiceError, "not group/world writable"):
                service._validate()

    def write_dispatch_config(self, directory, *, builder_enabled=False):
        token_file = directory / "protocol.token"
        mcp_token_file = directory / "mcp.token"
        config_file = directory / "service.json"
        token_file.write_text("synthetic-protocol-token-0123456789")
        mcp_token_file.write_text("synthetic-mcp-token-0123456789")
        os.chmod(token_file, 0o600)
        os.chmod(mcp_token_file, 0o600)
        config_file.write_text(json.dumps({
            "schema": "managed-supervisor-service/v1",
            "socket_path": str(directory / "supervisor.sock"),
            "state_path": str(directory / "state.json"),
            "token_file": str(token_file),
            "mcp_token_file": str(mcp_token_file),
            "client_uid": os.geteuid() + 1,
            "socket_group_gid": os.getegid(),
            "base_url": "http://127.0.0.1:18080",
            "provider": "codex",
            "model": "synthetic/model",
            "allowed_models": ["synthetic/model"],
            "builder_enabled": builder_enabled,
        }))
        os.chmod(config_file, 0o600)
        return config_file

    def test_protected_config_builds_dispatcher_without_contacting_provider(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-entrypoint-") as tmp:
            directory = Path(tmp)
            config_file = self.write_dispatch_config(directory)
            config = ManagedSupervisorServiceConfig.from_file(config_file)
            config.validate_state_location()
            service = build_managed_dispatcher(config_file)
            self.addCleanup(service.close)
            self.assertIsInstance(service, ExperimentalManagedDispatcher)
            self.assertEqual(service.core.allowed_models, ["synthetic/model"])
            self.assertEqual(service.core.provider, "codex")
            self.assertFalse(service.core.builder_enabled)

    def test_protected_config_can_enable_managed_builder_explicitly(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-builder-config-") as tmp:
            directory = Path(tmp)
            config_file = self.write_dispatch_config(directory, builder_enabled=True)
            config = ManagedSupervisorServiceConfig.from_file(config_file)
            self.assertTrue(config.builder_enabled)
            service = build_managed_dispatcher(config_file)
            self.addCleanup(service.close)
            self.assertTrue(service.core.builder_enabled)
            with mock.patch("t3_transport.HttpT3Client") as factory:
                client = service.core._client()
                self.assertEqual(factory.call_args.kwargs["provider"], "codex")
                client.initialize.assert_called_once()
            self.assertEqual(service.core.mcp_token, "synthetic-mcp-token-0123456789")
            self.assertEqual(service.token, "synthetic-protocol-token-0123456789")
            self.assertIsNone(service.listener)
            with self.assertRaisesRegex(ManagedSupervisorServiceError, "already in use"):
                build_managed_dispatcher(config_file)

    def test_dispatch_config_rejects_broad_permissions_and_unknown_fields(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-config-") as tmp:
            directory = Path(tmp)
            config_file = self.write_dispatch_config(directory)
            os.chmod(config_file, 0o640)
            with self.assertRaisesRegex(ManagedSupervisorServiceError, "mode 0600"):
                ManagedSupervisorServiceConfig.from_file(config_file)

            os.chmod(config_file, 0o600)
            value = json.loads(config_file.read_text())
            value["dispatch_enabled"] = True
            config_file.write_text(json.dumps(value))
            os.chmod(config_file, 0o600)
            with self.assertRaisesRegex(ManagedSupervisorServiceError, "schema or fields"):
                ManagedSupervisorServiceConfig.from_file(config_file)

    def test_dispatch_config_rejects_nonprivate_state_directory(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-state-") as tmp:
            directory = Path(tmp)
            config_file = self.write_dispatch_config(directory)
            os.chmod(directory, 0o750)
            config = ManagedSupervisorServiceConfig.from_file(config_file)
            with self.assertRaisesRegex(ManagedSupervisorServiceError, "state directory"):
                config.validate_state_location()

    def test_dispatch_config_rejects_nonloopback_and_credentialed_urls(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-url-") as tmp:
            config_file = self.write_dispatch_config(Path(tmp))
            value = json.loads(config_file.read_text())
            for url in ("http://127.0.0.1.example.invalid", "http://localhost.example.invalid",
                        "http://user@localhost:1234", "https://mcp.example.invalid",
                        "http://127.0.0.1:99999", "http://localhost/path"):
                with self.subTest(url=url):
                    value["base_url"] = url
                    config_file.write_text(json.dumps(value))
                    with self.assertRaisesRegex(ManagedSupervisorServiceError, "loopback origin"):
                        ManagedSupervisorServiceConfig.from_file(config_file)


if __name__ == "__main__":
    unittest.main()
