import asyncio
import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import https_connect_broker
import install_managed_candidate
import managed_netns
import managed_supervisor_attestation_hook
import preflight_managed_candidate
import stage_managed_candidate
import verify_managed_host

SYSTEMD = Path(__file__).parent


class ManagedSystemdUnitTests(unittest.TestCase):
    def test_service_units_use_separate_users_and_shared_pinned_netns(self):
        t3 = (SYSTEMD / "managed-t3.service").read_text()
        supervisor = (SYSTEMD / "managed-supervisor.service").read_text()
        self.assertIn("User=managed-t3\n", t3)
        self.assertIn("User=managed-supervisor\n", supervisor)
        self.assertIn("NetworkNamespacePath=/run/netns/managed-t3", t3)
        self.assertIn("NetworkNamespacePath=/run/netns/managed-t3", supervisor)
        self.assertIn("KillMode=control-group", t3)
        self.assertIn("KillMode=control-group", supervisor)
        self.assertIn("NoNewPrivileges=yes", t3)
        self.assertIn("NoNewPrivileges=yes", supervisor)
        self.assertIn("ConditionPathExists=/etc/managed-supervisor/dispatch-reviewed.enable", supervisor)
        self.assertIn("UnsetEnvironment=HTTP_PROXY HTTPS_PROXY ALL_PROXY", supervisor)
        self.assertIn(
            "ExecStartPost=+/usr/bin/python3 /opt/managed-supervisor/orchestrator/systemd/managed_supervisor_attestation_hook.py --publish",
            supervisor,
        )
        self.assertIn(
            "ExecStopPost=+/usr/bin/python3 /opt/managed-supervisor/orchestrator/systemd/managed_supervisor_attestation_hook.py --remove",
            supervisor,
        )
        self.assertIn("systemd-tmpfiles-setup.service", supervisor)
        self.assertIn(
            "Requires=managed-t3-netns.service managed-t3.service managed-attestation-verifier.service",
            supervisor,
        )
        self.assertIn("SupplementaryGroups=managed-supervisor", supervisor)
        verifier = (SYSTEMD / "managed-attestation-verifier.service").read_text()
        self.assertIn("User=root", verifier)
        self.assertIn("RestrictAddressFamilies=AF_UNIX", verifier)
        self.assertIn("CapabilityBoundingSet=CAP_SYS_PTRACE", verifier)
        self.assertNotIn("AF_INET", verifier)
        self.assertNotIn("[Install]", supervisor)

    def test_worker_has_loopback_only_api_and_group_limited_proxy_socket(self):
        t3 = (SYSTEMD / "managed-t3.service").read_text()
        broker = (SYSTEMD / "managed-t3-egress.service").read_text()
        self.assertIn("--host=127.0.0.1", t3)
        self.assertIn("--proxy-port=3128", t3)
        self.assertIn("SupplementaryGroups=managed-t3-egress", t3)
        self.assertIn("--socket-group=managed-t3-egress", broker)
        self.assertIn("--allow-host=opencode.ai", broker)
        self.assertIn("RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6", broker)


class NamespaceLifecycleTests(unittest.TestCase):
    def test_create_creates_fixed_namespace_and_only_enables_loopback(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "managed-t3"
            calls = []

            def run(args):
                calls.append(args)
                if args[:3] == ["netns", "add", "managed-t3"]:
                    path.touch()

            with (
                mock.patch.object(managed_netns, "NAMESPACE_PATH", path),
                mock.patch.object(managed_netns.os, "geteuid", return_value=0),
                mock.patch.object(managed_netns, "_run", side_effect=run),
            ):
                managed_netns.create()
            self.assertEqual(calls[0], ["netns", "add", "managed-t3"])
            self.assertEqual(calls[1][-4:], ["link", "set", "lo", "up"])
            self.assertNotIn("route", " ".join(calls[1]))

    def test_create_refuses_to_adopt_existing_namespace(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "managed-t3"
            path.touch()
            with (
                mock.patch.object(managed_netns, "NAMESPACE_PATH", path),
                mock.patch.object(managed_netns.os, "geteuid", return_value=0),
                mock.patch.object(managed_netns, "_run") as run,
            ):
                with self.assertRaises(managed_netns.NamespaceError):
                    managed_netns.create()
                run.assert_not_called()

    def test_failed_loopback_setup_attempts_to_remove_partial_namespace(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "managed-t3"
            calls = []

            def run(args):
                calls.append(args)
                if args[:3] == ["netns", "add", "managed-t3"]:
                    path.touch()
                elif args[0:3] == ["netns", "exec", "managed-t3"]:
                    raise managed_netns.NamespaceError("synthetic failure")

            with (
                mock.patch.object(managed_netns, "NAMESPACE_PATH", path),
                mock.patch.object(managed_netns.os, "geteuid", return_value=0),
                mock.patch.object(managed_netns, "_run", side_effect=run),
            ):
                with self.assertRaises(managed_netns.NamespaceError):
                    managed_netns.create()
            self.assertEqual(calls[-1], ["netns", "del", "managed-t3"])


class BrokerSocketPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_group_mode_is_applied_before_serving_and_socket_is_removed(self):
        class FakeServer:
            def close(self):
                return None

            async def wait_closed(self):
                return None

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def serve_forever(self):
                raise asyncio.CancelledError()

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "broker.sock"

            async def fake_start_server(*_args, **_kwargs):
                path.touch()
                return FakeServer()

            with (
                mock.patch.object(
                    https_connect_broker.asyncio, "start_unix_server", side_effect=fake_start_server
                ),
                mock.patch.object(https_connect_broker.os, "chown") as chown,
            ):
                with self.assertRaises(asyncio.CancelledError):
                    await https_connect_broker.serve(path, {"opencode.ai"}, socket_gid=1234)
            chown.assert_called_once_with(path, -1, 1234)
            self.assertFalse(path.exists())

    async def test_default_socket_mode_remains_private_and_invalid_gid_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "broker.sock"
            with mock.patch.object(https_connect_broker.asyncio, "start_unix_server") as start:
                with self.assertRaises(ValueError):
                    await https_connect_broker.serve(path, {"opencode.ai"}, socket_gid=-1)
                start.assert_not_called()


class StagingProvisionerTests(unittest.TestCase):
    def test_stager_creates_private_new_tree_and_withholds_dispatch_and_mcp_secret(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "candidate"
            created = stage_managed_candidate.stage_candidate(
                output,
                dashboard_uid=1500,
                dashboard_gid=1600,
                allowed_models=["opencode/model-a"],
                model="opencode/model-a",
            )
            self.assertEqual(created.stat().st_mode & 0o777, 0o700)
            config = json.loads((created / "etc/managed-supervisor/service.json").read_text())
            self.assertEqual(config["client_uid"], 1500)
            self.assertEqual(config["socket_group_gid"], 1600)
            self.assertFalse((created / "etc/managed-supervisor/dispatch-reviewed.enable").exists())
            self.assertFalse((created / "etc/managed-supervisor/credentials/mcp-token").exists())
            dashboard_token = (created / "etc/managed-dashboard/credentials/supervisor-token").read_bytes()
            service_token = (created / "etc/managed-supervisor/credentials/protocol-token").read_bytes()
            self.assertEqual(dashboard_token, service_token)
            self.assertEqual(len(service_token.strip()), 64)
            self.assertEqual(
                (created / "etc/managed-supervisor/credentials/protocol-token").stat().st_mode & 0o777, 0o600
            )
            self.assertTrue((created / "etc/systemd/system/managed-attestation-verifier.service").is_file())
            self.assertTrue(
                (
                    created / "opt/managed-supervisor/orchestrator/systemd/managed_attestation_verifier.py"
                ).is_file()
            )
            self.assertTrue((created / "etc/tmpfiles.d/managed-attestation-verifier.conf").is_file())

    def test_stager_refuses_existing_destination_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "candidate"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("preserve")
            with self.assertRaises(stage_managed_candidate.StagingError):
                stage_managed_candidate.stage_candidate(
                    output,
                    dashboard_uid=1500,
                    dashboard_gid=1600,
                    allowed_models=["opencode/model-a"],
                    model="opencode/model-a",
                )
            self.assertEqual(sentinel.read_text(), "preserve")

    def test_stager_requires_explicit_model_allowlist(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(stage_managed_candidate.StagingError):
                stage_managed_candidate.stage_candidate(
                    Path(temporary) / "candidate",
                    dashboard_uid=1500,
                    dashboard_gid=1600,
                    allowed_models=["opencode/model-a"],
                    model="opencode/model-b",
                )

    def test_stager_rejects_models_without_an_opencode_route(self):
        with tempfile.TemporaryDirectory() as temporary:
            for model in ("codex/gpt-5", "gpt-6-luna"):
                with (
                    self.subTest(model=model),
                    self.assertRaisesRegex(stage_managed_candidate.StagingError, "OpenCode"),
                ):
                    stage_managed_candidate.stage_candidate(
                        Path(temporary) / model.replace("/", "-"),
                        dashboard_uid=1500,
                        dashboard_gid=1600,
                        allowed_models=[model],
                        model=model,
                    )

    def test_stager_allows_known_opencode_go_model_on_opencode_instance(self):
        model = "opencode-go/deepseek-v4.1-flash"
        with tempfile.TemporaryDirectory() as temporary:
            created = stage_managed_candidate.stage_candidate(
                Path(temporary) / "candidate",
                dashboard_uid=1500,
                dashboard_gid=1600,
                allowed_models=[model],
                model=model,
            )
            config = json.loads((created / "etc/managed-supervisor/service.json").read_text())
            self.assertEqual(config["provider"], "opencode")
            self.assertEqual(config["model"], model)


class InstallerTrustBoundaryTests(unittest.TestCase):
    def test_installer_has_hard_stop_before_any_host_or_stage_access(self):
        with self.assertRaisesRegex(install_managed_candidate.InstallError, "installation disabled"):
            install_managed_candidate.install_candidate(
                Path("/missing-stage"),
                Path("/missing-approval"),
                Path("/missing-token"),
                dashboard_user="missing",
                dashboard_group="missing",
            )

    def test_privileged_input_path_rejects_world_writable_ancestor(self):
        with tempfile.TemporaryDirectory() as temporary:
            untrusted = Path(temporary) / "untrusted-stage"
            untrusted.mkdir(mode=0o777)
            untrusted.chmod(0o777)
            with self.assertRaisesRegex(install_managed_candidate.InstallError, "writable"):
                install_managed_candidate._check_trusted_ancestors(untrusted, require_root=False)

    def test_stage_reader_rejects_unapproved_relative_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(install_managed_candidate.InstallError):
                install_managed_candidate._read_stage_file(
                    Path(temporary), "../../etc/shadow", require_root=False
                )

    def test_stage_reader_uses_dirfds_and_rejects_symlink_components(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary) / "stage"
            (stage / "etc/managed-supervisor").mkdir(parents=True, mode=0o700)
            (stage / "etc").chmod(0o755)
            (stage / "etc/managed-supervisor").chmod(0o750)
            config = stage / "etc/managed-supervisor/service.json"
            config.write_text("{}")
            config.chmod(0o600)
            stage.chmod(0o700)

            def stage_opener(_path, **_kwargs):
                return os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)

            with (
                mock.patch.object(
                    install_managed_candidate, "_open_absolute_directory", side_effect=stage_opener
                ),
                mock.patch.object(Path, "lstat", side_effect=AssertionError("pathname lstat used")),
            ):
                self.assertEqual(
                    install_managed_candidate._read_stage_file(
                        stage, "etc/managed-supervisor/service.json", require_root=False, private=True
                    ),
                    b"{}",
                )

            (stage / "etc/managed-supervisor").rename(stage / "etc/managed-supervisor.saved")
            (stage / "etc/managed-supervisor").symlink_to(
                stage / "etc/managed-supervisor.saved", target_is_directory=True
            )
            with self.assertRaises(install_managed_candidate.InstallError):
                install_managed_candidate._read_stage_file(
                    stage, "etc/managed-supervisor/service.json", require_root=False, private=True
                )

    def test_mcp_secret_source_open_is_relative_to_trusted_directory_fd(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            secret = root / "mcp-token"
            secret.write_text("synthetic-token-value-long-enough\n")
            secret.chmod(0o600)

            def opener(_path, **_kwargs):
                return os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)

            with (
                mock.patch.object(install_managed_candidate, "_open_absolute_directory", side_effect=opener),
                mock.patch.object(Path, "lstat", side_effect=AssertionError("pathname lstat used")),
            ):
                self.assertEqual(
                    install_managed_candidate._safe_token(secret, require_root=False),
                    b"synthetic-token-value-long-enough\n",
                )
            secret.unlink()
            secret.symlink_to("/etc/passwd")
            with mock.patch.object(install_managed_candidate, "_open_absolute_directory", side_effect=opener):
                with self.assertRaises(install_managed_candidate.InstallError):
                    install_managed_candidate._safe_token(secret, require_root=False)

    def test_dirfd_install_traversal_rejects_symlink_component(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir(mode=0o700)
            (root / "opt").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(install_managed_candidate.InstallError):
                install_managed_candidate._ensure_directory_at_root(
                    root,
                    Path("opt/managed-supervisor"),
                    supervisor_gid=0,
                    dashboard_uid=os.getuid(),
                    dashboard_gid=0,
                    require_root=False,
                    created_dirs=[],
                )
            self.assertEqual(list(outside.iterdir()), [])

    def test_dirfd_install_traversal_rejects_unsafe_existing_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unsafe = root / "opt"
            unsafe.mkdir(mode=0o700)
            unsafe.chmod(0o777)
            with self.assertRaises(install_managed_candidate.InstallError):
                install_managed_candidate._ensure_directory_at_root(
                    root,
                    Path("opt/managed-supervisor"),
                    supervisor_gid=0,
                    dashboard_uid=os.getuid(),
                    dashboard_gid=0,
                    require_root=False,
                    created_dirs=[],
                )

    def test_dirfd_file_creation_is_exclusive_and_writes_under_open_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "opt/managed-supervisor/orchestrator"
            parent.mkdir(parents=True, mode=0o755)
            for directory in (root / "opt", root / "opt/managed-supervisor", parent):
                directory.chmod(0o755)

            def policy(*_args, **_kwargs):
                return os.getuid(), os.getgid(), 493

            relative = Path("opt/managed-supervisor/orchestrator/entry.py")
            with mock.patch.object(install_managed_candidate, "_directory_policy", side_effect=policy):
                created = install_managed_candidate._create_file_at_root(
                    root,
                    relative,
                    b"safe payload",
                    uid=os.getuid(),
                    gid=os.getgid(),
                    mode=0o644,
                    require_root=False,
                    supervisor_gid=os.getgid(),
                    dashboard_uid=os.getuid(),
                    dashboard_gid=os.getgid(),
                )
                self.assertEqual(created.read_bytes(), b"safe payload")
                with self.assertRaises(install_managed_candidate.InstallError):
                    install_managed_candidate._create_file_at_root(
                        root,
                        relative,
                        b"replacement",
                        uid=os.getuid(),
                        gid=os.getgid(),
                        mode=0o644,
                        require_root=False,
                        supervisor_gid=os.getgid(),
                        dashboard_uid=os.getuid(),
                        dashboard_gid=os.getgid(),
                    )
            self.assertEqual(created.read_bytes(), b"safe payload")

    def test_rollback_removes_only_recorded_inode_and_reports_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "opt/managed-supervisor/orchestrator"
            parent.mkdir(parents=True, mode=0o755)
            for directory in (root / "opt", root / "opt/managed-supervisor", parent):
                directory.chmod(0o755)

            def policy(*_args, **_kwargs):
                return os.getuid(), os.getgid(), 493

            relative = Path("opt/managed-supervisor/orchestrator/entry.py")
            receipts = []
            with mock.patch.object(install_managed_candidate, "_directory_policy", side_effect=policy):
                path = install_managed_candidate._create_file_at_root(
                    root,
                    relative,
                    b"installed",
                    uid=os.getuid(),
                    gid=os.getgid(),
                    mode=0o644,
                    require_root=False,
                    supervisor_gid=os.getgid(),
                    dashboard_uid=os.getuid(),
                    dashboard_gid=os.getgid(),
                    created_files=receipts,
                )
                self.assertEqual(len(receipts), 1)
                original = receipts[0]
                self.assertTrue(install_managed_candidate._remove_at_root(root, original))
                self.assertFalse(path.exists())
                path = install_managed_candidate._create_file_at_root(
                    root,
                    relative,
                    b"installed",
                    uid=os.getuid(),
                    gid=os.getgid(),
                    mode=0o644,
                    require_root=False,
                    supervisor_gid=os.getgid(),
                    dashboard_uid=os.getuid(),
                    dashboard_gid=os.getgid(),
                    created_files=receipts,
                )
                original = receipts[-1]
                path.unlink()
                path.write_bytes(b"replacement")
                self.assertFalse(install_managed_candidate._remove_at_root(root, original))
                self.assertEqual(path.read_bytes(), b"replacement")


class AttestationLifecycleHookTests(unittest.TestCase):
    @staticmethod
    def _proc_process(root, pid, uid, start, cgroup):
        process = root / str(pid)
        process.mkdir()
        fields = ["S"] + ["0"] * 18 + [str(start)]
        (process / "stat").write_text(f"{pid} (candidate proc) " + " ".join(fields))
        (process / "status").write_text(f"Name:\ttest\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n")
        (process / "cgroup").write_text(f"0::{cgroup}\n")

    def test_publish_discovers_units_verifies_before_atomic_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record_dir = root / "attestation"
            record_dir.mkdir(mode=0o700)
            record = record_dir / "record.json"
            proc = root / "proc"
            proc.mkdir(mode=0o700)
            sup_cgroup = "/system.slice/managed-supervisor.service"
            t3_cgroup = "/system.slice/managed-t3.service"
            self._proc_process(proc, 111, 1201, 777, sup_cgroup)
            self._proc_process(proc, 222, 1202, 888, t3_cgroup)
            self._proc_process(proc, 223, 1202, 889, t3_cgroup)
            (proc / "223" / "fd").mkdir()
            (proc / "223" / "fd" / "7").symlink_to("socket:[54321]")
            unit_values = {
                "managed-supervisor.service": (
                    "activating",
                    111,
                    "managed-supervisor",
                    "managed-dashboard",
                    sup_cgroup,
                ),
                "managed-t3.service": ("active", 222, "managed-t3", "managed-t3-egress", t3_cgroup),
            }

            def runner(argv, **_kwargs):
                unit = argv[-1]
                active, pid, user, group, cgroup = unit_values[unit]
                return mock.Mock(
                    returncode=0,
                    stdout=(
                        f"ActiveState={active}\nMainPID={pid}\nUser={user}\nGroup={group}\nControlGroup={cgroup}\n"
                    ),
                )

            class FakeConnection:
                def settimeout(self, _timeout):
                    pass

                def connect(self, _path):
                    pass

                def close(self):
                    pass

            with (
                mock.patch.object(
                    managed_supervisor_attestation_hook.pwd,
                    "getpwnam",
                    side_effect=lambda name: mock.Mock(
                        pw_uid={
                            "managed-supervisor": 1201,
                            "managed-t3": 1202,
                        }[name]
                    ),
                ),
                mock.patch.object(
                    managed_supervisor_attestation_hook.socket, "socket", return_value=FakeConnection()
                ),
                mock.patch.object(
                    managed_supervisor_attestation_hook, "_listener_inode", return_value="54321"
                ),
                mock.patch.object(
                    managed_supervisor_attestation_hook,
                    "verify_peer_and_processes",
                    return_value={"identity_observed": True},
                ) as verify,
                mock.patch.object(managed_supervisor_attestation_hook.os, "geteuid", return_value=0),
                mock.patch.object(managed_supervisor_attestation_hook.os, "fchown"),
            ):
                result = managed_supervisor_attestation_hook.publish_attestation(
                    path=record,
                    runner=runner,
                    proc_root=proc,
                    require_root=False,
                )
            self.assertTrue(result["identity_observed"])
            verify.assert_called_once()
            self.assertEqual(verify.call_args.args[1].t3_pid, 223)
            data = json.loads(record.read_text())
            self.assertEqual(data["supervisor_pid"], 111)
            self.assertEqual(data["t3_pid"], 223)
            self.assertEqual(data["supervisor_cgroup_membership"], [f"0::{sup_cgroup}"])
            self.assertEqual(record.stat().st_mode & 0o777, 0o444)
            parsed = managed_supervisor_attestation_hook.AttestationConfig.from_mapping(data)
            self.assertEqual(parsed.t3_start_ticks, 889)

    def test_failed_observation_leaves_no_stale_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            record_dir = Path(temporary) / "attestation"
            record_dir.mkdir(mode=0o700)
            record = record_dir / "record.json"
            record.write_text("stale")
            with (
                mock.patch.object(managed_supervisor_attestation_hook.os, "geteuid", return_value=0),
                mock.patch.object(
                    managed_supervisor_attestation_hook,
                    "_run_systemctl",
                    side_effect=managed_supervisor_attestation_hook.HookError("bad unit"),
                ),
            ):
                with self.assertRaises(managed_supervisor_attestation_hook.HookError):
                    managed_supervisor_attestation_hook.publish_attestation(
                        path=record,
                        proc_root=Path(temporary),
                        require_root=False,
                    )
            self.assertFalse(record.exists())

    def test_stop_hook_removes_record_through_dirfd(self):
        with tempfile.TemporaryDirectory() as temporary:
            record_dir = Path(temporary) / "attestation"
            record_dir.mkdir(mode=0o700)
            record = record_dir / "record.json"
            record.write_text("candidate")
            managed_supervisor_attestation_hook._remove_record(record, require_root=False)
            self.assertFalse(record.exists())

    def test_proc_identity_rejects_wrong_exact_cgroup(self):
        with tempfile.TemporaryDirectory() as temporary:
            proc = Path(temporary)
            self._proc_process(proc, 303, 1203, 999, "/system.slice/other.service")
            with self.assertRaisesRegex(managed_supervisor_attestation_hook.HookError, "exact unified"):
                managed_supervisor_attestation_hook._proc_identity(
                    303,
                    1203,
                    "/system.slice/managed-t3.service",
                    proc_root=proc,
                )

    def test_real_nested_runner_child_fd_identifies_actual_listener_owner(self):
        if not hasattr(os, "fork"):
            self.skipTest("requires Linux process and /proc semantics")
        parent_sock, child_sock = socket.socketpair()
        ready_r, ready_w = os.pipe()
        release_r, release_w = os.pipe()
        child_pid = os.fork()
        if child_pid == 0:
            try:
                parent_sock.close()
                os.close(ready_r)
                os.close(release_w)
                os.write(ready_w, b"r")
                os.read(release_r, 1)
            finally:
                os._exit(0)
        child_sock.close()
        os.close(ready_w)
        os.close(release_r)
        fixture_proc = None
        try:
            os.read(ready_r, 1)
            actual_cgroups = tuple(sorted(Path(f"/proc/{os.getpid()}/cgroup").read_text().splitlines()))
            unified = [line for line in actual_cgroups if line.startswith("0::")]
            if len(unified) != 1:
                self.skipTest("requires a unified cgroup v2 hierarchy")
            cgroup = unified[0].split("::", 1)[1]
            fd_entries = list(Path(f"/proc/{child_pid}/fd").iterdir())
            child_socket_fd = next(entry for entry in fd_entries if os.readlink(entry).startswith("socket:["))
            inode = os.readlink(child_socket_fd).removeprefix("socket:[").removesuffix("]")
            with tempfile.TemporaryDirectory() as temporary:
                fixture_proc = Path(temporary) / "proc"
                fixture_proc.mkdir(mode=0o700)
                (fixture_proc / str(os.getpid())).symlink_to(f"/proc/{os.getpid()}")
                (fixture_proc / str(child_pid)).symlink_to(f"/proc/{child_pid}")
                with mock.patch.object(
                    managed_supervisor_attestation_hook, "_listener_inode", return_value=inode
                ):
                    owner_pid, _ticks, memberships = managed_supervisor_attestation_hook._listener_owner_pid(
                        os.getpid(),
                        os.getuid(),
                        cgroup,
                        proc_root=fixture_proc,
                        port=46687,
                    )
            self.assertEqual(owner_pid, child_pid)
            self.assertEqual(memberships, (f"0::{cgroup}",))
        finally:
            os.write(release_w, b"x")
            os.close(release_w)
            os.close(ready_r)
            parent_sock.close()
            os.waitpid(child_pid, 0)


class HostVerificationContractTests(unittest.TestCase):
    def test_read_only_preflight_never_claims_deployment_readiness(self):
        class Result:
            returncode = 0
            stdout = "Version=255\n"

        users = {
            "dash": SimpleNamespace(pw_name="dash", pw_uid=1101, pw_gid=2001),
            "managed-supervisor": SimpleNamespace(pw_name="managed-supervisor", pw_uid=1102, pw_gid=2002),
            "managed-t3": SimpleNamespace(pw_name="managed-t3", pw_uid=1103, pw_gid=2003),
            "managed-egress": SimpleNamespace(pw_name="managed-egress", pw_uid=1104, pw_gid=2003),
        }
        groups = {
            "managed-dashboard": SimpleNamespace(gr_name="managed-dashboard", gr_gid=2001, gr_mem=["dash"]),
            "managed-supervisor": SimpleNamespace(gr_name="managed-supervisor", gr_gid=2002, gr_mem=[]),
            "managed-t3-egress": SimpleNamespace(
                gr_name="managed-t3-egress", gr_gid=2003, gr_mem=["managed-t3", "managed-egress"]
            ),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ptrace = root / "sys/kernel/yama/ptrace_scope"
            ptrace.parent.mkdir(parents=True)
            ptrace.write_text("1\n")
            t3 = root / "t3"
            t3.write_text("synthetic binary")
            t3.chmod(0o755)
            cgroup = root / "cgroup"
            cgroup.mkdir()
            (cgroup / "cgroup.controllers").touch()
            (cgroup / "cgroup.procs").touch()
            with (
                mock.patch.object(
                    preflight_managed_candidate.pwd, "getpwnam", side_effect=lambda name: users[name]
                ),
                mock.patch.object(
                    preflight_managed_candidate.grp, "getgrnam", side_effect=lambda name: groups[name]
                ),
                mock.patch.object(
                    preflight_managed_candidate, "_systemd_manager", return_value=(True, "255")
                ),
                mock.patch.object(preflight_managed_candidate.os, "geteuid", return_value=0),
                mock.patch.object(preflight_managed_candidate.shutil, "which", return_value="/usr/sbin/ip"),
            ):
                result = preflight_managed_candidate.collect_preflight(
                    dashboard_user="dash",
                    dashboard_group="managed-dashboard",
                    disk_usage=lambda _path: SimpleNamespace(free=64 * 1024 * 1024),
                    proc_root=root,
                    t3_executable=t3,
                    cgroup_root=cgroup,
                )
        self.assertEqual(result["blocking_checks"], [])
        self.assertTrue(result["preflight_only"])
        self.assertFalse(result["installation_enabled"])
        self.assertFalse(result["deployment_ready"])

    def test_loopback_namespace_and_cgroups_fail_closed(self):
        verify_managed_host.verify_loopback_only_links('[{"ifname":"lo","flags":["LOOPBACK","UP"]}]')
        with self.assertRaises(verify_managed_host.HostVerificationError):
            verify_managed_host.verify_loopback_only_links(
                '[{"ifname":"lo","flags":["UP"]},{"ifname":"eth0","flags":["UP"]}]'
            )
        valid = {
            "identity_observed": True,
            "supervisor_pid": 101,
            "t3_listener_port": 46687,
            "t3_listener_host": "127.0.0.1",
            "listener_inode": "123456",
            "supervisor_cgroup_membership": ["0::/system.slice/managed-supervisor.service"],
            "t3_cgroup_membership": ["0::/system.slice/managed-t3.service"],
        }
        sup_unit = {"MainPID": "101", "ControlGroup": "/system.slice/managed-supervisor.service"}
        t3_unit = {"MainPID": "202", "ControlGroup": "/system.slice/managed-t3.service"}
        verify_managed_host.verify_attested_cgroups(valid, supervisor_unit=sup_unit, t3_unit=t3_unit)
        wrong_peer = dict(valid, supervisor_pid=999)
        with self.assertRaisesRegex(verify_managed_host.HostVerificationError, "MainPID"):
            verify_managed_host.verify_attested_cgroups(
                wrong_peer,
                supervisor_unit=sup_unit,
                t3_unit=t3_unit,
            )
        valid["t3_cgroup_membership"] = ["0::/system.slice/other.service"]
        with self.assertRaises(verify_managed_host.HostVerificationError):
            verify_managed_host.verify_attested_cgroups(valid, supervisor_unit=sup_unit, t3_unit=t3_unit)

    def test_systemd_unit_properties_must_match_identity_and_containment(self):
        class Result:
            returncode = 0
            stdout = (
                "ActiveState=active\nMainPID=202\nUser=managed-t3\nGroup=managed-t3-egress\n"
                "KillMode=control-group\nNoNewPrivileges=yes\nProtectControlGroups=yes\n"
                "ControlGroup=/system.slice/managed-t3.service\n"
            )

        verify_managed_host.verify_unit(
            "managed-t3.service",
            user="managed-t3",
            group="managed-t3-egress",
            runner=lambda *_args, **_kwargs: Result(),
        )
        Result.stdout = Result.stdout.replace("KillMode=control-group", "KillMode=process")
        with self.assertRaises(verify_managed_host.HostVerificationError):
            verify_managed_host.verify_unit(
                "managed-t3.service",
                user="managed-t3",
                group="managed-t3-egress",
                runner=lambda *_args, **_kwargs: Result(),
            )

    def test_root_verifier_unit_requires_single_capability_and_unix_only_socket(self):
        class Result:
            returncode = 0
            stdout = (
                "ActiveState=active\nMainPID=303\nUser=root\nGroup=managed-supervisor\n"
                "KillMode=control-group\nNoNewPrivileges=yes\nProtectControlGroups=yes\n"
                "ControlGroup=/system.slice/managed-attestation-verifier.service\n"
                "CapabilityBoundingSet=cap_sys_ptrace\nRestrictAddressFamilies=AF_UNIX\n"
            )

        required = {"CapabilityBoundingSet": "CAP_SYS_PTRACE", "RestrictAddressFamilies": "AF_UNIX"}
        verify_managed_host.verify_unit(
            "managed-attestation-verifier.service",
            user="root",
            group="managed-supervisor",
            required_properties=required,
            runner=lambda *_args, **_kwargs: Result(),
        )
        Result.stdout = Result.stdout.replace(
            "CapabilityBoundingSet=cap_sys_ptrace", "CapabilityBoundingSet=cap_sys_ptrace cap_net_raw"
        )
        with self.assertRaisesRegex(verify_managed_host.HostVerificationError, "capability"):
            verify_managed_host.verify_unit(
                "managed-attestation-verifier.service",
                user="root",
                group="managed-supervisor",
                required_properties=required,
                runner=lambda *_args, **_kwargs: Result(),
            )

    def test_root_verifier_process_identity_and_ptrace_capability_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            proc = Path(temporary) / "303"
            proc.mkdir()
            (proc / "status").write_text(
                "Uid:\t0\t0\t0\t0\nGid:\t1600\t1600\t1600\t1600\n"
                f"CapBnd:\t{1 << 19:016x}\nCapEff:\t{1 << 19:016x}\n"
            )
            (proc / "cgroup").write_text("0::/system.slice/managed-attestation-verifier.service\n")
            with mock.patch.object(verify_managed_host.grp, "getgrnam", return_value=mock.Mock(gr_gid=1600)):
                verify_managed_host.verify_verifier_process(
                    303, "/system.slice/managed-attestation-verifier.service", proc_root=Path(temporary)
                )
                (proc / "status").write_text(
                    "Uid:\t0\t0\t0\t0\nGid:\t1600\t1600\t1600\t1600\n"
                    f"CapBnd:\t{1 << 19:016x}\nCapEff:\t0\n"
                )
                with self.assertRaisesRegex(verify_managed_host.HostVerificationError, "CAP_SYS_PTRACE"):
                    verify_managed_host.verify_verifier_process(
                        303, "/system.slice/managed-attestation-verifier.service", proc_root=Path(temporary)
                    )

    def test_staged_service_config_must_match_dashboard_gid_and_endpoint(self):
        class Account:
            pw_uid = 1500

        class Group:
            gr_gid = 1600

        config = {
            "schema": "managed-supervisor-service/v1",
            "client_uid": 1500,
            "socket_group_gid": 1600,
            "socket_path": "/run/managed-supervisor/managed.sock",
            "base_url": "http://127.0.0.1:46687",
            "provider": "opencode",
        }

        def group_lookup(name):
            return Group()

        with (
            mock.patch.object(verify_managed_host.pwd, "getpwnam", return_value=Account()),
            mock.patch.object(verify_managed_host.grp, "getgrnam", side_effect=group_lookup),
        ):
            verify_managed_host.verify_service_config(
                config,
                dashboard_user="dash",
                dashboard_group="managed-dashboard",
                socket_path="/run/managed-supervisor/managed.sock",
            )
            config["socket_group_gid"] = 999
            with self.assertRaises(verify_managed_host.HostVerificationError):
                verify_managed_host.verify_service_config(
                    config,
                    dashboard_user="dash",
                    dashboard_group="managed-dashboard",
                    socket_path="/run/managed-supervisor/managed.sock",
                )


if __name__ == "__main__":
    unittest.main()
