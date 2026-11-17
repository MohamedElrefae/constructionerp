"""Fail-closed execution guards: native dispatch, ERP/host execution, binary probes.

No spawn, no network, no model. Everything here is pure unit-level behavior.
"""

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import (
    HOST_EXECUTION_ENV,
    HOST_EXECUTION_VALUE,
    NATIVE_DISPATCH_ENV,
    NATIVE_DISPATCH_VALUE,
    WorkflowError,
    host_execution_allowed,
    native_dispatch_allowed,
    require_host_execution,
    require_native_dispatch,
)
from preflight import check_binary


class _TruthyLauncher:
    def __call__(self, job):  # pragma: no cover - must never run
        raise AssertionError("launcher must not be invoked")


class _FalsyLauncher(_TruthyLauncher):
    def __bool__(self):
        return False


class NativeDispatchGuardTests(unittest.TestCase):
    def test_no_env_refuses(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(NATIVE_DISPATCH_ENV, None)
            self.assertFalse(native_dispatch_allowed(None))
            with self.assertRaises(WorkflowError):
                require_native_dispatch(None, "test")

    def test_wrong_value_refuses(self):
        with mock.patch.dict(os.environ, {NATIVE_DISPATCH_ENV: "true"}, clear=False):
            with self.assertRaises(WorkflowError):
                require_native_dispatch(None, "test")

    def test_explicit_value_admits_native(self):
        with mock.patch.dict(os.environ, {NATIVE_DISPATCH_ENV: NATIVE_DISPATCH_VALUE}, clear=False):
            self.assertIsNone(require_native_dispatch(None, "test"))

    def test_truthy_launcher_skips_gate(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(NATIVE_DISPATCH_ENV, None)
            self.assertIsNone(require_native_dispatch(_TruthyLauncher(), "test"))

    def test_falsy_launcher_still_refuses(self):
        """The spawn branch treats a falsy launcher as native; the gate must too."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(NATIVE_DISPATCH_ENV, None)
            with self.assertRaises(WorkflowError):
                require_native_dispatch(_FalsyLauncher(), "test")


class HostExecutionGuardTests(unittest.TestCase):
    def test_no_env_refuses(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(HOST_EXECUTION_ENV, None)
            self.assertFalse(host_execution_allowed())
            with self.assertRaises(WorkflowError):
                require_host_execution("ERP dry-run")

    def test_wrong_value_refuses(self):
        with mock.patch.dict(os.environ, {HOST_EXECUTION_ENV: "yes"}, clear=False):
            with self.assertRaises(WorkflowError):
                require_host_execution("ERP import")

    def test_explicit_value_admits(self):
        with mock.patch.dict(os.environ, {HOST_EXECUTION_ENV: HOST_EXECUTION_VALUE}, clear=False):
            self.assertIsNone(require_host_execution("ERP dry-run"))


class ProbeTransportGuardTests(unittest.TestCase):
    def test_probe_refuses_without_acknowledgment(self):
        import probe_transports

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(NATIVE_DISPATCH_ENV, None)
            with mock.patch.object(sys, "argv", ["probe_transports.py", "--report", "/tmp/x.json"]):
                with self.assertRaises(WorkflowError):
                    probe_transports.main()


class CheckBinaryBoundedControlTests(unittest.TestCase):
    """A pin mismatch must be detected without executing the binary."""

    def _fake_binary(self, directory: Path, marker: Path) -> Path:
        path = directory / "fake-binary"
        path.write_text("#!/bin/sh\n" f"echo executed >> {marker}\n" "echo 'fake 9.9.9'\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def test_hash_mismatch_never_executes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            marker = tmp / "marker"
            binary = self._fake_binary(tmp, marker)
            pin = {"binary": str(binary), "version": "9.9.9", "binary_sha256": "0" * 64}
            result = check_binary("test", pin)
            self.assertFalse(result.ok)
            self.assertIn("hash mismatch", result.message.lower())
            self.assertFalse(marker.exists(), "binary must not be executed on hash mismatch")

    def test_matching_hash_executes_and_validates_version(self):
        import hashlib

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            marker = tmp / "marker"
            binary = self._fake_binary(tmp, marker)
            sha = hashlib.sha256(binary.read_bytes()).hexdigest()
            pin = {"binary": str(binary), "version": "9.9.9", "binary_sha256": sha}
            result = check_binary("test", pin)
            self.assertTrue(result.ok)
            self.assertTrue(marker.exists(), "pinned binary is executed")


class LibraryCallGateTests(unittest.TestCase):
    """In-process library entry points must refuse without the operation-class ack.

    Each test installs a fake `bench` that writes a marker; the assertion is that the
    marker does not exist on refusal and does exist when acknowledged. This fails if
    the guard is removed (the marker would be written).
    """

    def _fake_bench(self, tmp: Path, marker: Path, payload_line: str) -> Path:
        bench_dir = tmp / "env" / "bin"
        bench_dir.mkdir(parents=True)
        bench = bench_dir / "bench"
        bench.write_text("#!/bin/sh\n" f"echo ran >> {marker}\n" f"echo '{payload_line}'\n")
        bench.chmod(bench.stat().st_mode | stat.S_IXUSR)
        return bench

    def test_dry_run_console_refuses_without_ack(self):
        import dry_run

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            marker = tmp / "marker"
            self._fake_bench(tmp, marker, '__DRYRUN_REPORT__{"accounts": {}, "total_accounts": 0}')
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(HOST_EXECUTION_ENV, None)
                with self.assertRaises(WorkflowError) as ctx:
                    dry_run._run_read_console(str(tmp), "no-site", [])
                self.assertIn("ERP dry-run disabled", str(ctx.exception))
                self.assertFalse(marker.exists(), "bench must not run without the ack")
            with mock.patch.dict(os.environ, {HOST_EXECUTION_ENV: HOST_EXECUTION_VALUE}, clear=False):
                report = dry_run._run_read_console(str(tmp), "no-site", [])
                self.assertEqual(report["total_accounts"], 0)
                self.assertTrue(marker.exists(), "acknowledged run executes the (fake) bench")

    def test_import_console_refuses_without_ack(self):
        import import_adapter

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            marker = tmp / "marker"
            self._fake_bench(tmp, marker, '__IMPORT_REPORT__{"before": {}, "after": {}}')
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(HOST_EXECUTION_ENV, None)
                with self.assertRaises(WorkflowError) as ctx:
                    import_adapter._run_write_console(str(tmp), "no-site", [])
                self.assertIn("ERP import disabled", str(ctx.exception))
                self.assertFalse(marker.exists(), "bench must not run without the ack")
            with mock.patch.dict(os.environ, {HOST_EXECUTION_ENV: HOST_EXECUTION_VALUE}, clear=False):
                report = import_adapter._run_write_console(str(tmp), "no-site", [])
                self.assertEqual(report, {"before": {}, "after": {}})
                self.assertTrue(marker.exists(), "acknowledged run executes the (fake) bench")


class AgentEnvStripTests(unittest.TestCase):
    """Guard tokens must not leak into the spawned agent's environment."""

    def test_invocation_env_excludes_engine_tokens(self):
        import adapters

        spec = {
            "tool": "opencode",
            "binary": "/nonexistent/opencode",
            "prompt": "x",
            "role": "architect",
            "model": "m/m",
            "root": "/tmp",
            "wire_schema": "/tmp/wire.json",
            "neutral_mounts": [],
            "effort": None,
            "runtime": "/tmp/runtime",
            "work_item_root": "/tmp/work-item",
            "control_root": "/tmp/control",
            "read_artifacts": [],
        }
        with mock.patch.dict(
            os.environ,
            {
                "ENGINE_NATIVE_DISPATCH": "allow-native-host-access",
                "ENGINE_HOST_EXECUTION": "allow-host-execution",
                "WORKFLOW_SECRET": "x",
            },
            clear=False,
        ):
            _argv, env = adapters.invocation(spec)
        self.assertNotIn("ENGINE_NATIVE_DISPATCH", env)
        self.assertNotIn("ENGINE_HOST_EXECUTION", env)
        self.assertNotIn("WORKFLOW_SECRET", env)


class SwapDetectionTests(unittest.TestCase):
    """Pre/post hashing detects a swapped binary; it is detection, not atomicity."""

    def test_binary_changed_during_execution_is_detected(self):
        import hashlib

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            binary = tmp / "selfmod"
            binary.write_text("#!/bin/sh\necho x >> \"$0\"\necho 'fake 9.9.9'\n")
            binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
            pin = {
                "binary": str(binary),
                "version": "9.9.9",
                "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            }
            result = check_binary("test", pin)
            self.assertFalse(result.ok)
            self.assertIn("changed during execution", result.message)


if __name__ == "__main__":
    unittest.main()
