"""Tests for the future external-supervisor contract; no dispatch is enabled."""

import os
import json
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

from managed_supervisor_contract import (  # noqa: E402
    DISPATCH_SCHEMA,
    SCHEMA,
    ManagedSupervisorConfig,
    ManagedSupervisorConfigError,
    ManagedSupervisorDispatchConfig,
    require_test_only_dispatch,
)
from t3_supervisor_client import SupervisorClient, SupervisorLauncher  # noqa: E402


def config(socket_path, *, expected_uid=None, socket_group_gid=None, **overrides):
    value = {
        "schema": SCHEMA,
        "dispatch_enabled": False,
        "socket_path": str(socket_path),
        "token_file": "/run/dashboard-t3/peer.token",
        "expected_uid": (os.geteuid() + 1) if expected_uid is None else expected_uid,
        "socket_group_gid": os.getegid() if socket_group_gid is None else socket_group_gid,
        "allowed_models": ["opencode-go/deepseek-v4.1-flash"],
    }
    value.update(overrides)
    return value


def dispatch_config(socket_path, *, expected_uid=None, **overrides):
    value = {
        "schema": DISPATCH_SCHEMA,
        "dispatch_enabled": True,
        "socket_path": str(socket_path),
        "token_file": "/run/dashboard-t3/peer.token",
        "expected_uid": os.geteuid() + 1 if expected_uid is None else expected_uid,
        "socket_group_gid": os.getegid(),
        "expected_cgroup": "/system.slice/t3-managed-supervisor.service",
        "allowed_models": ["opencode-go/deepseek-v4.1-flash"],
    }
    value.update(overrides)
    return value


class ManagedSupervisorContractTests(unittest.TestCase):
    def test_dispatch_gate_is_closed_outside_explicit_test_mode(self):
        require_test_only_dispatch(True)
        for value in (False, None, 1, "1"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ManagedSupervisorConfigError, "outside explicit test mode"):
                    require_test_only_dispatch(value)

    def test_dispatch_contract_requires_explicit_enable_and_exact_cgroup(self):
        parsed = ManagedSupervisorDispatchConfig.from_mapping(dispatch_config("/run/sup.sock"))
        self.assertEqual(parsed.expected_cgroup, "/system.slice/t3-managed-supervisor.service")
        self.assertEqual(parsed.allowed_models, ("opencode-go/deepseek-v4.1-flash",))
        self.assertFalse(parsed.builder_enabled)
        enabled = ManagedSupervisorDispatchConfig.from_mapping(
            dispatch_config("/run/sup.sock", builder_enabled=True))
        self.assertTrue(enabled.builder_enabled)
        for invalid in (
            dispatch_config("/run/sup.sock", dispatch_enabled=False),
            dispatch_config("/run/sup.sock", expected_cgroup="relative.service"),
            dispatch_config("/run/sup.sock", expected_cgroup="/system.slice/../other.service"),
            dispatch_config("/run/sup.sock", expected_cgroup="/system.slice/wrong.scope"),
            dispatch_config("/run/sup.sock", allowed_models=[]),
            dispatch_config("/run/sup.sock", builder_enabled=1),
            dispatch_config("/run/sup.sock", expected_uid=os.geteuid()),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ManagedSupervisorConfigError):
                    ManagedSupervisorDispatchConfig.from_mapping(invalid)

    def test_dispatch_peer_verifier_requires_kernel_uid_and_exact_cgroup(self):
        with tempfile.TemporaryDirectory(prefix="managed-peer-") as tmp:
            proc = Path(tmp)
            pid = 4242
            proc_dir = proc / str(pid)
            proc_dir.mkdir()
            cgroup_file = proc_dir / "cgroup"
            cgroup_file.write_text("0::/system.slice/t3-managed-supervisor.service\n")
            cfg = ManagedSupervisorDispatchConfig.from_mapping(dispatch_config("/run/sup.sock"))

            class FakeSocket:
                peer_uid = cfg.expected_uid

                def getsockopt(self, *_args):
                    return struct.pack("3i", pid, self.peer_uid, 987)

            verifier = cfg.peer_verifier(proc_root=proc)
            self.assertTrue(verifier(FakeSocket())["identity_observed"])
            cgroup_file.write_text("0::/system.slice/other.service\n")
            self.assertIsNone(verifier(FakeSocket()))
            FakeSocket.peer_uid = os.geteuid()
            self.assertIsNone(verifier(FakeSocket()))

    def test_dispatch_config_file_is_dashboard_owned_bounded_and_no_follow(self):
        with tempfile.TemporaryDirectory(prefix="managed-dispatch-config-") as tmp:
            directory = Path(tmp)
            path = directory / "dispatch.json"
            path.write_text(json.dumps(dispatch_config("/run/sup.sock")))
            os.chmod(path, 0o600)
            parsed = ManagedSupervisorDispatchConfig.from_file(path)
            self.assertEqual(parsed.expected_uid, os.geteuid() + 1)
            os.chmod(path, 0o622)
            with self.assertRaisesRegex(ManagedSupervisorConfigError, "not group/world writable"):
                ManagedSupervisorDispatchConfig.from_file(path)
            link = directory / "dispatch-link.json"
            link.symlink_to(path)
            with self.assertRaisesRegex(ManagedSupervisorConfigError, "cannot be opened"):
                ManagedSupervisorDispatchConfig.from_file(link)

    def test_accepts_explicit_separate_uid_unix_socket_contract(self):
        parsed = ManagedSupervisorConfig.from_mapping(config("/run/dashboard-t3/supervisor.sock"))
        self.assertEqual(parsed.expected_uid, os.geteuid() + 1)
        self.assertEqual(parsed.socket_path, Path("/run/dashboard-t3/supervisor.sock"))
        self.assertEqual(parsed.launcher_options(), {
            "allowed_models": ["opencode-go/deepseek-v4.1-flash"],
            "expected_uid": os.geteuid() + 1,
        })

    def test_refuses_enabled_or_unknown_contract(self):
        with self.assertRaisesRegex(ManagedSupervisorConfigError, "dispatch_enabled false"):
            ManagedSupervisorConfig.from_mapping(config("/run/sup.sock", dispatch_enabled=True))
        with self.assertRaisesRegex(ManagedSupervisorConfigError, "schema"):
            ManagedSupervisorConfig.from_mapping({"schema": "v2"})

    def test_requires_separate_uid_and_absolute_local_paths(self):
        with self.assertRaisesRegex(ManagedSupervisorConfigError, "dedicated UID"):
            ManagedSupervisorConfig.from_mapping(config("/run/sup.sock", expected_uid=os.geteuid()))
        with self.assertRaisesRegex(ManagedSupervisorConfigError, "absolute"):
            ManagedSupervisorConfig.from_mapping(config("relative.sock"))
        with self.assertRaisesRegex(ManagedSupervisorConfigError, "absolute"):
            ManagedSupervisorConfig.from_mapping(config("/run/sup.sock", token_file="peer.token"))

    def test_requires_unique_nonempty_model_pins_and_valid_socket_group(self):
        with self.assertRaisesRegex(ManagedSupervisorConfigError, "allowed_models"):
            ManagedSupervisorConfig.from_mapping(config("/run/sup.sock", allowed_models=[]))
        with self.assertRaisesRegex(ManagedSupervisorConfigError, "allowed_models"):
            ManagedSupervisorConfig.from_mapping(config("/run/sup.sock", allowed_models=["m", "m"]))
        with self.assertRaisesRegex(ManagedSupervisorConfigError, "socket_group_gid"):
            ManagedSupervisorConfig.from_mapping(config("/run/sup.sock", socket_group_gid=True))

    def test_socket_verification_requires_service_owned_group_socket(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-") as tmp:
            directory = Path(tmp)
            path = directory / "supervisor.sock"
            parsed = ManagedSupervisorConfig.from_mapping(config(
                path, expected_uid=os.geteuid(), socket_group_gid=os.getegid()),
                dashboard_uid=os.geteuid() + 1)
            sock_stat = SimpleNamespace(
                st_mode=stat.S_IFSOCK | 0o660,
                st_uid=parsed.expected_uid,
                st_gid=parsed.socket_group_gid,
            )
            parent_stat = SimpleNamespace(
                st_mode=stat.S_IFDIR | 0o750,
                st_uid=parsed.expected_uid,
                st_gid=parsed.socket_group_gid,
            )
            with mock.patch.object(Path, "lstat", return_value=sock_stat), \
                    mock.patch.object(Path, "stat", return_value=parent_stat):
                parsed.verify_socket(access=lambda *_args: True)
                sock_stat.st_mode = stat.S_IFSOCK | 0o666
                with self.assertRaisesRegex(ManagedSupervisorConfigError, "deny all world"):
                    parsed.verify_socket(access=lambda *_args: True)

    def test_config_file_is_private_bounded_and_no_follow(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-config-") as tmp:
            directory = Path(tmp)
            path = directory / "supervisor.json"
            path.write_text(json.dumps(config("/run/dashboard-t3/supervisor.sock")))
            os.chmod(path, 0o600)
            parsed = ManagedSupervisorConfig.from_file(path)
            self.assertEqual(parsed.expected_uid, os.geteuid() + 1)
            os.chmod(path, 0o622)
            with self.assertRaisesRegex(ManagedSupervisorConfigError, "not writable"):
                ManagedSupervisorConfig.from_file(path)
            link = directory / "link.json"
            link.symlink_to(path)
            with self.assertRaisesRegex(ManagedSupervisorConfigError, "cannot be opened"):
                ManagedSupervisorConfig.from_file(link)

    def test_dashboard_health_adapter_uses_read_only_op_and_checks_identity(self):
        with tempfile.TemporaryDirectory(prefix="managed-sup-health-") as tmp:
            directory = Path(tmp)
            token_path = directory / "token"
            token_path.write_text("synthetic-private-token-0123456789")
            os.chmod(token_path, 0o600)
            config_path = directory / "config.json"
            config_path.write_text(json.dumps(config(
                "/run/dashboard-t3/supervisor.sock",
                token_file=str(token_path),
            )))
            os.chmod(config_path, 0o600)
            fake = mock.Mock()
            fake.call.return_value = {
                "ready": True, "uid": os.geteuid() + 1, "read_only": True,
                "protocol": "managed-supervisor-health/v1", "pid": 123,
            }
            with mock.patch.object(ManagedSupervisorConfig, "verify_socket"), \
                    mock.patch("t3_supervisor_client.SupervisorClient", return_value=fake) as client:
                from managed_supervisor_contract import check_managed_supervisor_health
                result = check_managed_supervisor_health(config_path)
            client.assert_called_once()
            fake.call.assert_called_once_with("health")
            self.assertTrue(result["read_only"])
            self.assertEqual(result["uid"], os.geteuid() + 1)
            self.assertNotIn("token", result)

    def test_launcher_can_pin_distinct_kernel_peer_uid(self):
        launcher = SupervisorLauncher(
            "/tmp/root", "/run/sup.sock", "test-token",
            allowed_models=["opencode-go/deepseek-v4.1-flash"], expected_uid=12345)
        self.assertEqual(launcher.client.expected_uid, 12345)
        with self.assertRaisesRegex(ValueError, "expected_uid"):
            SupervisorClient("/run/sup.sock", "test-token", expected_uid=True)


if __name__ == "__main__":
    unittest.main()
