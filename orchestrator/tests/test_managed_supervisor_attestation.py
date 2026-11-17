import json
import os
import socket
import stat
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from managed_supervisor_attestation import (
    SCHEMA,
    AttestationConfig,
    AttestationError,
    load_root_owned_config,
    verify_peer_and_processes,
)


def config_data(**updates):
    data = {
        "schema": SCHEMA,
        "socket_path": "/run/managed/supervisor.sock",
        "supervisor_pid": 101,
        "supervisor_uid": 1001,
        "supervisor_start_ticks": 123,
        "t3_pid": 202,
        "t3_uid": 1002,
        "t3_start_ticks": 456,
        "supervisor_cgroup_membership": ["0::/system.slice/managed.service"],
        "t3_cgroup_membership": ["0::/system.slice/managed.service"],
        "t3_listener_host": "127.0.0.1",
        "t3_listener_port": 43000,
    }
    data.update(updates)
    return data


class FakeConnection:
    def __init__(self, pid=101, uid=1001, gid=1001):
        self.credentials = struct.pack("3i", pid, uid, gid)

    def getsockopt(self, _level, _option, _size):
        return self.credentials

    def getpeername(self):
        return "/run/managed/supervisor.sock"


class ManagedSupervisorAttestationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.proc = Path(self.temp.name)
        self.config = AttestationConfig.from_mapping(config_data())
        self._make_process(101, 1001, 123)
        self._make_process(202, 1002, 456)
        (self.proc / "202" / "net").mkdir()
        (self.proc / "202" / "net" / "tcp6").write_text("header\n")
        (self.proc / "101" / "ns").mkdir()
        (self.proc / "202" / "ns").mkdir()
        (self.proc / "101" / "ns" / "net").write_text("synthetic namespace")
        os.link(self.proc / "101" / "ns" / "net", self.proc / "202" / "ns" / "net")
        self._write_tcp_table()
        (self.proc / "202" / "fd" / "3").symlink_to("socket:[555]")

    def tearDown(self):
        self.temp.cleanup()

    def _make_process(self, pid, uid, start_ticks, cgroup="0::/system.slice/managed.service"):
        directory = self.proc / str(pid)
        (directory / "fd").mkdir(parents=True, exist_ok=True)
        # stat fields after comm begin at field 3; starttime is field 22, index 19.
        tail = ["S"] + ["0"] * 18 + [str(start_ticks)]
        (directory / "stat").write_text(f"{pid} (proc with (parens)) {' '.join(tail)}\n")
        (directory / "status").write_text(f"Name:\ttest\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n")
        (directory / "cgroup").write_text(cgroup + "\n")

    def _write_tcp_table(self, *, state="0A", inode="555", local=None):
        address = local or f"0100007F:{43000:04X}"
        row = f"  0: {address} 00000000:0000 {state} 00000000:00000000 00:00000000 00000000 1002 0 {inode}"
        (self.proc / "202" / "net" / "tcp").write_text(
            "  sl local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode\n"
            + row
            + "\n"
        )

    def test_accepts_matching_peer_process_cgroup_and_listener_owner(self):
        result = verify_peer_and_processes(FakeConnection(), self.config, proc_root=self.proc)
        self.assertTrue(result["identity_observed"])
        self.assertEqual(result["listener_inode"], "555")
        self.assertEqual(result["supervisor_pid"], 101)

    def test_accepts_independently_pinned_service_cgroups(self):
        (self.proc / "202" / "cgroup").write_text("0::/system.slice/t3.service\n")
        config = AttestationConfig.from_mapping(
            config_data(t3_cgroup_membership=["0::/system.slice/t3.service"])
        )
        self.assertTrue(
            verify_peer_and_processes(FakeConnection(), config, proc_root=self.proc)["identity_observed"]
        )

    def test_rejects_peer_pid_or_uid_mismatch(self):
        for connection in (FakeConnection(pid=303), FakeConnection(uid=3000)):
            with self.subTest(connection=connection.credentials):
                with self.assertRaises(AttestationError):
                    verify_peer_and_processes(connection, self.config, proc_root=self.proc)

    def test_rejects_connection_to_a_different_socket_path(self):
        connection = FakeConnection()
        connection.getpeername = lambda: "/run/managed/other.sock"
        with self.assertRaisesRegex(AttestationError, "socket differs"):
            verify_peer_and_processes(connection, self.config, proc_root=self.proc)

    def test_rejects_changed_process_starttime_uid_or_cgroup(self):
        cases = (
            ("stat", "202 (t3) S " + "0 " * 18 + "457\n"),
            ("status", "Name:\tt3\nUid:\t1002\t3000\t1002\t1002\n"),
            ("cgroup", "0::/system.slice/other.service\n"),
        )
        for filename, contents in cases:
            with self.subTest(filename=filename):
                path = self.proc / "202" / filename
                original = path.read_text()
                path.write_text(contents)
                try:
                    with self.assertRaises(AttestationError):
                        verify_peer_and_processes(FakeConnection(), self.config, proc_root=self.proc)
                finally:
                    path.write_text(original)

    def test_rejects_missing_proc_or_listener_data(self):
        (self.proc / "101" / "status").unlink()
        with self.assertRaises(AttestationError):
            verify_peer_and_processes(FakeConnection(), self.config, proc_root=self.proc)
        self._make_process(101, 1001, 123)
        (self.proc / "202" / "net" / "tcp").unlink()
        with self.assertRaises(AttestationError):
            verify_peer_and_processes(FakeConnection(), self.config, proc_root=self.proc)

    def test_rejects_absent_or_ambiguous_listener(self):
        self._write_tcp_table(state="01")
        with self.assertRaises(AttestationError):
            verify_peer_and_processes(FakeConnection(), self.config, proc_root=self.proc)
        self._write_tcp_table()
        path = self.proc / "202" / "net" / "tcp"
        path.write_text(path.read_text() + path.read_text().splitlines()[1] + "\n")
        with self.assertRaises(AttestationError):
            verify_peer_and_processes(FakeConnection(), self.config, proc_root=self.proc)

    def test_rejects_listener_inode_not_owned_by_t3_pid(self):
        (self.proc / "202" / "fd" / "3").unlink()
        with self.assertRaises(AttestationError):
            verify_peer_and_processes(FakeConnection(), self.config, proc_root=self.proc)

    def test_rejects_different_network_namespace_and_wildcard_listener(self):
        namespace = self.proc / "202" / "ns" / "net"
        namespace.unlink()
        namespace.write_text("different namespace")
        with self.assertRaisesRegex(AttestationError, "network namespace"):
            verify_peer_and_processes(FakeConnection(), self.config, proc_root=self.proc)
        namespace.unlink()
        os.link(self.proc / "101" / "ns" / "net", namespace)
        path = self.proc / "202" / "net" / "tcp"
        row = path.read_text().splitlines()[1]
        path.write_text(path.read_text() + row.replace("0100007F", "00000000") + "\n")
        with self.assertRaisesRegex(AttestationError, "wildcard"):
            verify_peer_and_processes(FakeConnection(), self.config, proc_root=self.proc)

    def test_config_rejects_ambiguous_or_invalid_records(self):
        duplicate = json.dumps(config_data())[:-1] + ',"schema":"managed-supervisor-attestation/v1"}'
        with self.assertRaises(AttestationError):
            json.loads(
                duplicate,
                object_pairs_hook=lambda pairs: __import__(
                    "managed_supervisor_attestation"
                )._reject_duplicate_keys(pairs),
            )
        for updates in (
            {"supervisor_pid": True},
            {"t3_listener_port": True},
            {"t3_listener_host": "0.0.0.0"},
            {"t3_cgroup_membership": []},
            {"supervisor_pid": 202},
        ):
            with self.subTest(updates=updates), self.assertRaises(AttestationError):
                AttestationConfig.from_mapping(config_data(**updates))

    def test_config_loader_requires_root_owned_nonwritable_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attestation.json"
            path.write_text(json.dumps(config_data()))
            path.chmod(0o444)
            real_fstat = os.fstat

            def fake_fstat(fd):
                result = real_fstat(fd)
                mode = result.st_mode
                if stat.S_ISDIR(mode):
                    mode &= ~0o022
                return SimpleNamespace(st_mode=mode, st_uid=0, st_size=result.st_size)

            opened_fd = []
            real_open = os.open

            def track_open(*args, **kwargs):
                fd = real_open(*args, **kwargs)
                opened_fd.append(fd)
                return fd

            with (
                mock.patch("managed_supervisor_attestation.os.open", side_effect=track_open),
                mock.patch("managed_supervisor_attestation.os.fstat", side_effect=fake_fstat),
            ):
                loaded = load_root_owned_config(path)
            self.assertEqual(loaded.supervisor_pid, 101)

            with (
                mock.patch("managed_supervisor_attestation.os.open", side_effect=track_open),
                mock.patch("managed_supervisor_attestation.os.fstat", side_effect=lambda fd: real_fstat(fd)),
            ):
                with self.assertRaises(AttestationError):
                    load_root_owned_config(path)

    def test_config_loader_rejects_writable_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attestation.json"
            path.write_text(json.dumps(config_data()))
            path.chmod(0o444)
            with self.assertRaises(AttestationError):
                load_root_owned_config(path)

    def test_config_loader_rejects_intermediate_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "real").mkdir()
            (root / "real" / "record").write_text(json.dumps(config_data()))
            (root / "link").symlink_to(root / "real", target_is_directory=True)
            real_fstat = os.fstat

            def trusted_metadata(fd):
                result = real_fstat(fd)
                return SimpleNamespace(st_mode=result.st_mode & ~0o022, st_uid=0, st_size=result.st_size)

            with mock.patch("managed_supervisor_attestation.os.fstat", side_effect=trusted_metadata):
                with self.assertRaises(AttestationError):
                    load_root_owned_config(root / "link" / "record")

    def test_config_loader_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.write_text(json.dumps(config_data()))
            link = Path(directory) / "link"
            link.symlink_to(target)
            with self.assertRaises(AttestationError):
                load_root_owned_config(link)


if __name__ == "__main__":
    unittest.main()
