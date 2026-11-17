"""No-provider lifecycle checks for the combined T3/supervisor runner."""

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _managed_t3_runner import (
    SYNTHETIC_MODEL,
    IsolatedManagedT3Runner,
    _cgroup_membership,
)


def _process_alive(pid):
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        return state != "Z"
    except (OSError, IndexError):
        return False


class FakeServerLifecycle:
    """Local inert child; no TCP listener, provider config, or network use."""

    def __init__(self, *, repository_root, exit_immediately=False, descendant_pid_file=None):
        self.process = None
        self.shutdown_timeout = 1.0
        self.exit_immediately = exit_immediately
        self.repository_root = repository_root
        self.descendant_pid_file = descendant_pid_file

    def start(self):
        if self.exit_immediately:
            code = "pass"
        elif self.descendant_pid_file:
            code = (
                "import subprocess,sys,time; "
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                f"open({str(self.descendant_pid_file)!r},'w').write(str(child.pid)); "
                "time.sleep(60)"
            )
        else:
            code = "import time; time.sleep(60)"
        self.process = subprocess.Popen(
            [sys.executable, "-c", code],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True, start_new_session=True)
        if self.exit_immediately:
            self.process.wait(timeout=2)
        return self.process

    def wait_ready(self):
        if self.process.poll() is not None:
            raise RuntimeError("synthetic server exited before ready")

    def shutdown(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=self.shutdown_timeout)


class FakeSimulator:
    def __init__(self, state):
        self.state = state
        self.url = "http://127.0.0.1:1"
        self.entered = False
        self.exited = False
        self.thread = SimpleNamespace(is_alive=lambda: not self.exited)

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *_exc):
        self.exited = True


class FakeListener:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class IsolatedManagedT3RunnerTests(unittest.TestCase):
    def _patch_network_edges(self, *, fail_service_start=False):
        fake_listener = FakeListener()

        def fake_start(service):
            if fail_service_start:
                raise RuntimeError("synthetic bind failure")
            service.listener = fake_listener
            return service

        start_patch = mock.patch(
            "_managed_t3_runner.ExperimentalManagedDispatcher.start", autospec=True,
            side_effect=fake_start)
        serve_patch = mock.patch(
            "_managed_t3_runner.ExperimentalManagedDispatcher.serve_forever", autospec=True)
        start_patch.start()
        serve_patch.start()
        self.addCleanup(start_patch.stop)
        self.addCleanup(serve_patch.stop)
        return fake_listener

    def test_server_child_inherits_runner_cgroup_and_supervisor_uses_synthetic_client(self):
        with tempfile.TemporaryDirectory(prefix="managed-runner-ok-") as raw:
            runner = IsolatedManagedT3Runner(
                server=FakeServerLifecycle(
                    repository_root=Path(__file__).resolve().parents[2],
                    descendant_pid_file=Path(raw) / "grandchild.pid"),
                runtime_dir=Path(raw) / "runner-private",
                simulator_factory=FakeSimulator)
            listener = self._patch_network_edges()
            try:
                runner.start()
                process = runner.server.process
                self.assertIsNotNone(process)
                self.assertEqual(_cgroup_membership(os.getpid()), _cgroup_membership(process.pid))
                self.assertIs(runner.supervisor_service.listener, listener)
                pid_file = Path(raw) / "grandchild.pid"
                deadline = time.monotonic() + 2.0
                while not pid_file.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(pid_file.exists(), "T3 fixture did not write descendant PID before cleanup")

                provider = mock.Mock()
                provider.delegate.return_value = {"taskId": "synthetic-thread"}
                provider.status.return_value = {
                    "status": "completed", "summary": "safe result ENGINE-T3-RESULT job-" + "a" * 24,
                    "model": SYNTHETIC_MODEL,
                }
                runner.supervisor_core._client = lambda: provider
                marker = "ENGINE-T3-RESULT job-" + "a" * 24
                job = {
                    "job_id": "job-" + "a" * 24,
                    "client_request_id": "request-" + "b" * 24,
                    "model": SYNTHETIC_MODEL,
                    "brief": "Return a harmless synthetic test result.",
                    "role": "reviewer",
                    "expect_marker": marker,
                }
                request = {"op": "dispatch", "token": runner.supervisor_service.token,
                           "payload": {"job": job}}
                # A same-user fixture cannot supply production root attestation.
                # Verify refusal before installing the explicit test-only verifier.
                refused = runner.supervisor_service._respond(request)
                self.assertFalse(refused["ok"])
                self.assertEqual(refused["error"]["code"], "SERVICE_ATTESTATION_FAILED")
                provider.delegate.assert_not_called()
                runner.supervisor_service.attestation_verifier = mock.Mock(return_value=True)
                dispatched = runner.supervisor_service._respond(request)
                self.assertEqual(dispatched["result"]["state"], "dispatched")
                collected = runner.supervisor_service._respond(
                    {"op": "collect", "token": runner.supervisor_service.token,
                     "payload": {"job_id": job["job_id"]}})
                self.assertEqual(collected["result"]["state"], "completed")
                provider.delegate.assert_called_once()
                provider.status.assert_called_once_with("synthetic-thread")
            finally:
                runner.close()
            self.assertIsNotNone(process.poll())
            self.assertTrue(runner.simulator.exited)
            self.assertTrue(listener.closed)
            self.assertIsNone(runner.supervisor_service.listener)
            grandchild_pid = int(pid_file.read_text())
            self.assertFalse(_process_alive(grandchild_pid), "T3 session descendant survived cleanup")

    def test_service_start_failure_unwinds_server_and_simulator(self):
        with tempfile.TemporaryDirectory(prefix="managed-runner-fail-") as raw:
            runner = IsolatedManagedT3Runner(
                server=FakeServerLifecycle(repository_root=Path(__file__).resolve().parents[2]),
                runtime_dir=Path(raw) / "runner-private",
                simulator_factory=FakeSimulator)
            self._patch_network_edges(fail_service_start=True)
            with self.assertRaisesRegex(RuntimeError, "synthetic bind failure"):
                runner.start()
            self.assertIsNotNone(runner.server.process.poll())
            self.assertTrue(runner.simulator.exited)
            self.assertIsNone(runner.supervisor_service.listener)

    def test_t3_early_exit_unwinds_simulator_before_service_is_started(self):
        with tempfile.TemporaryDirectory(prefix="managed-runner-child-fail-") as raw:
            runner = IsolatedManagedT3Runner(
                server=FakeServerLifecycle(
                    repository_root=Path(__file__).resolve().parents[2], exit_immediately=True),
                runtime_dir=Path(raw) / "runner-private", simulator_factory=FakeSimulator)
            self._patch_network_edges()
            with self.assertRaisesRegex(RuntimeError, "exited before ready"):
                runner.start()
            self.assertTrue(runner.simulator.exited)
            self.assertIsNone(runner.supervisor_service.listener)


if __name__ == "__main__":
    unittest.main()
