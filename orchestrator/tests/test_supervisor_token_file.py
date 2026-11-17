"""Fail-closed local credential file checks for the dashboard supervisor route."""

import os
import json
import socket
import struct
import sys
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path

ORCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ORCH))

from t3_supervisor_client import (ManagedSupervisorLauncher, SupervisorClient, SupervisorLauncher,
                                  SupervisorRefusal, load_private_supervisor_token)  # noqa: E402


class PrivateSupervisorTokenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="supervisor-token-")
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.path = self.directory / "peer.token"

    def write(self, value="test-only-token", mode=0o600):
        self.path.write_text(value, encoding="utf-8")
        os.chmod(self.path, mode)

    def test_reads_private_current_user_regular_file(self):
        self.write("test-only-token\n")
        self.assertEqual(load_private_supervisor_token(self.path), "test-only-token")

    def test_rejects_relative_path(self):
        with self.assertRaisesRegex(SupervisorRefusal, "absolute"):
            load_private_supervisor_token("relative.token")

    def test_rejects_group_or_world_readable_file(self):
        self.write(mode=0o640)
        with self.assertRaisesRegex(SupervisorRefusal, "permissions"):
            load_private_supervisor_token(self.path)

    def test_rejects_symlink(self):
        target = self.directory / "target"
        target.write_text("test-only-token", encoding="utf-8")
        os.chmod(target, 0o600)
        self.path.symlink_to(target)
        with self.assertRaisesRegex(SupervisorRefusal, "cannot be opened"):
            load_private_supervisor_token(self.path)

    def test_rejects_empty_and_oversized_values(self):
        self.write("\n")
        with self.assertRaisesRegex(SupervisorRefusal, "empty"):
            load_private_supervisor_token(self.path)
        self.write("x" * 4097)
        with self.assertRaisesRegex(SupervisorRefusal, "size bound"):
            load_private_supervisor_token(self.path)

    def test_rejects_non_regular_file(self):
        with self.assertRaisesRegex(SupervisorRefusal, "regular file"):
            load_private_supervisor_token(self.directory)

    def test_rejects_non_ascii_token(self):
        self.write("\u00e9")
        with self.assertRaisesRegex(SupervisorRefusal, "ASCII"):
            load_private_supervisor_token(self.path)

    def test_rejects_health_pid_that_does_not_match_kernel_peer(self):
        path = str(self.directory / "server.sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(1)
        self.addCleanup(server.close)

        def respond():
            conn, _ = server.accept()
            with conn:
                header = conn.recv(4)
                size = struct.unpack(">I", header)[0]
                while size:
                    chunk = conn.recv(size)
                    if not chunk:
                        return
                    size -= len(chunk)
                response = json.dumps({"ok": True, "result": {
                    "pid": os.getpid() + 1, "uid": os.geteuid()}}).encode()
                conn.sendall(struct.pack(">I", len(response)) + response)

        thread = threading.Thread(target=respond, daemon=True)
        thread.start()
        with self.assertRaisesRegex(SupervisorRefusal, "does not match socket peer"):
            SupervisorClient(path, "synthetic-token").call("health")
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

    def test_launcher_uses_recorded_launch_time(self):
        launcher = SupervisorLauncher(self.directory, "unused", "synthetic", allowed_models=["model"])
        expected = "2026-11-16T12:34:56Z"
        self.assertEqual(launcher._recorded_start({"history": [
            {"state": "launching", "utc": expected}]}), expected)
        with self.assertRaisesRegex(SupervisorRefusal, "launch time"):
            launcher._recorded_start({"history": [{"state": "launching", "utc": "invalid"}]})

    def test_peer_verifier_runs_before_token_is_sent(self):
        path = str(self.directory / "verify.sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(1)
        self.addCleanup(server.close)
        received = []

        def accept():
            conn, _ = server.accept()
            with conn:
                received.append(conn.recv(4096))

        thread = threading.Thread(target=accept, daemon=True)
        thread.start()

        def deny(_conn):
            raise SupervisorRefusal("synthetic attestation failure")

        with self.assertRaisesRegex(SupervisorRefusal, "attestation failure"):
            SupervisorClient(path, "synthetic-secret-token", peer_verifier=deny).call("health")
        thread.join(timeout=2)
        self.assertEqual(received, [b""])

    def test_false_peer_verification_refuses_before_token(self):
        path = str(self.directory / "verify-false.sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(1)
        self.addCleanup(server.close)
        received = []

        def accept():
            conn, _ = server.accept()
            with conn:
                received.append(conn.recv(4096))

        thread = threading.Thread(target=accept, daemon=True)
        thread.start()
        with self.assertRaisesRegex(SupervisorRefusal, "did not confirm"):
            SupervisorClient(path, "synthetic-secret-token", peer_verifier=lambda _conn: False).call("health")
        thread.join(timeout=2)
        self.assertEqual(received, [b""])

    def test_launcher_propagates_proven_prelaunch_failure(self):
        from core import ProvenNoLaunch
        launcher = SupervisorLauncher(self.directory, "unused", "synthetic", allowed_models=["model"])
        launcher.client = mock.Mock()
        launcher.client.call.return_value = {"state": "prelaunch_failed", "error": "unavailable"}
        job = {"job_id": "job-" + "a" * 24, "role": "reviewer",
               "spec": {"model": "model", "prompt": "test", "hard_timeout": 1}}
        with self.assertRaises(ProvenNoLaunch):
            launcher(job)

    def test_managed_launcher_requires_distinct_uid_and_verifier(self):
        args = (self.directory, "/tmp/supervisor.sock", "synthetic-token")
        with self.assertRaisesRegex(SupervisorRefusal, "verifier"):
            ManagedSupervisorLauncher(*args, allowed_models=["model"],
                                      expected_uid=os.geteuid() + 1, peer_verifier=None)
        with self.assertRaisesRegex(SupervisorRefusal, "differ"):
            ManagedSupervisorLauncher(*args, allowed_models=["model"],
                                      expected_uid=os.geteuid(), peer_verifier=lambda _conn: None)
        verifier = mock.Mock()
        launcher = ManagedSupervisorLauncher(*args, allowed_models=["model"],
                                              expected_uid=os.geteuid() + 1, peer_verifier=verifier)
        self.assertIs(launcher.client.peer_verifier, verifier)
        launcher.client.call = mock.Mock(return_value={"ready": True, "read_only": False,
            "protocol": "experimental-managed-supervisor/v1", "builder_enabled": False})
        job = {"job_id": "job-" + "a" * 24, "role": "reviewer",
               "spec": {"model": "model", "prompt": "Synthetic review.", "hard_timeout": 1}}
        launcher.preflight(job)
        launcher.client.call.return_value["read_only"] = True
        with self.assertRaisesRegex(SupervisorRefusal, "health"):
            launcher.preflight(job)

    def test_production_managed_launcher_still_refuses_builder_dispatch(self):
        args = (self.directory, "/tmp/supervisor.sock", "synthetic-token")
        launcher = ManagedSupervisorLauncher(
            *args, allowed_models=["model"], expected_uid=os.geteuid() + 1,
            peer_verifier=lambda _conn: {"identity_observed": True},
        )
        job = {"job_id": "job-" + "a" * 24, "role": "builder",
               "spec": {"model": "model", "prompt": "test", "hard_timeout": 1}}
        with self.assertRaisesRegex(SupervisorRefusal, "read-only; builder dispatch is refused"):
            launcher._validate_job(job)

    def test_builder_requires_explicit_managed_launcher_and_supervisor_capability(self):
        args = (self.directory, "/tmp/supervisor.sock", "synthetic-token")
        launcher = ManagedSupervisorLauncher(
            *args, allowed_models=["model"], expected_uid=os.geteuid() + 1,
            peer_verifier=lambda _conn: {"identity_observed": True}, builder_enabled=True,
        )
        launcher.client.call = mock.Mock(return_value={
            "ready": True, "read_only": False, "builder_enabled": True,
            "protocol": "experimental-managed-supervisor/v1",
        })
        job_id = "job-" + "a" * 24
        job = {"job_id": job_id, "role": "builder", "spec": {
            "model": "model", "prompt": "source packet: {\\\"files\\\": []}",
            "hard_timeout": 1,
        }}
        launcher.preflight(job)
        launcher.client.call.return_value["builder_enabled"] = False
        with self.assertRaisesRegex(SupervisorRefusal, "health"):
            launcher.preflight(job)

    def test_managed_builder_parse_preserves_return_bundle(self):
        launcher = ManagedSupervisorLauncher(
            self.directory, "/tmp/supervisor.sock", "synthetic-token",
            allowed_models=["model"], expected_uid=os.geteuid() + 1,
            peer_verifier=lambda _conn: {"identity_observed": True}, builder_enabled=True,
        )
        job_id = "job-" + "a" * 24
        wire = {"result_json": "{}", "explanation": "changed file", "plan_text": "",
                "builder_bundle_json": '{"files":[{"path":"src/app.py","content":"ok"}]}' }
        launcher.client.call = mock.Mock(return_value={"record": {
            "job_id": job_id, "task_id": "thread-1"}})
        task_id, body, returned, events = launcher.parse(
            {"job_id": job_id, "role": "builder"}, json.dumps(wire))
        self.assertEqual(task_id, "thread-1")
        self.assertEqual(returned["builder_bundle_json"], wire["builder_bundle_json"])
        self.assertEqual(body, {})
        self.assertEqual(events, [])

    def test_receipt_for_rechecks_completed_result_and_durable_state(self):
        args = (self.directory, "/tmp/supervisor.sock", "synthetic-token")
        launcher = ManagedSupervisorLauncher(
            *args, allowed_models=["model"], expected_uid=os.geteuid() + 1,
            peer_verifier=lambda _conn: {"identity_observed": True},
        )
        body = {"schema_version": 1, "job_id": "job-" + "a" * 24,
                "work_item": "test-work", "stage": "1", "role": "builder",
                "tool": "opencode", "model": "model", "session_id": "session-1",
                "dispatch_mode": "manual", "candidate_kind": "code",
                "candidate_id": "b" * 64, "plan_revision_hash": "c" * 64,
                "prompt_version": "d" * 64, "status": "COMPLETE", "verdict": "PASS",
                "failure_class": None, "findings": [],
                "evidence_paths": [{"artifact_id": "evidence", "sha256": "e" * 64,
                                    "visibility": "public"}],
                "started_utc": "2026-11-16T00:00:00Z",
                "finished_utc": "2026-11-16T00:00:01Z"}
        assistant_text = ("ENGINE-T3-RESULT " + body["job_id"] + "\n" + json.dumps({
            "result_json": json.dumps(body), "explanation": "prepared", "plan_text": "",
        }))
        receipt = {"state": "completed", "job_id": body["job_id"], "task_id": "task-1",
                   "model_evidence": "configured_only", "executed_model": None,
                   "configured_model": "model", "validated_utc": "2026-11-16T00:00:01Z",
                   "summary": assistant_text}
        launcher.client.call = mock.Mock(side_effect=[
            {"state": "completed", "receipt": receipt},
            {"record": {"job_id": body["job_id"], "task_id": "task-1", "model": "model"}},
        ])
        job = {"job_id": body["job_id"], "role": "builder",
               "spec": {"model": "model", "envelope": body}}
        with mock.patch("t3_result.decode_t3_result", return_value=("task-1", body, {}, [])):
            self.assertEqual(launcher.receipt_for(job), receipt)


if __name__ == "__main__":
    unittest.main()
