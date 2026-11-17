"""Fail-closed managed-dispatch checks isolated from suite module state."""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class ManagedDispatchEnvironmentTests(unittest.TestCase):
    def run_isolated(self, source):
        """Run checks in a clean interpreter so dashboard.config cannot leak."""
        with tempfile.TemporaryDirectory(prefix="managed-dispatch-isolated-") as tmp:
            tmp_path = Path(tmp)
            bench = tmp_path / "bench"
            (bench / "apps").mkdir(parents=True)
            (bench / "sites").mkdir()
            env = dict(os.environ)
            env["DASHBOARD_TEST_MODE"] = "1"
            env["DASHBOARD_TEST_ROOT"] = str(tmp_path / "dashboard-test")
            env["FRAPPE_BENCH_ROOT"] = str(bench)
            env.pop("DASHBOARD_ENABLE_MANAGED_DISPATCH", None)
            env.pop("DASHBOARD_MANAGED_SUPERVISOR_DISPATCH_CONFIG", None)
            result = subprocess.run(
                [sys.executable, "-c", textwrap.dedent(source)],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_child_env_strips_inherited_managed_dispatch_controls_by_default(self):
        self.run_isolated("""
            from dashboard import subprocess_client as client
            inherited = {
                "DASHBOARD_ENABLE_MANAGED_DISPATCH": "1",
                "DASHBOARD_MANAGED_SUPERVISOR_DISPATCH_CONFIG": "/tmp/forged.json",
                "ENGINE_NATIVE_DISPATCH": "allow-native-host-access",
                "ENGINE_T3_BACKEND": "t3",
            }
            env = client.child_env(inherited, forward_engine_dispatch=False)
            assert "DASHBOARD_ENABLE_MANAGED_DISPATCH" not in env
            assert "DASHBOARD_MANAGED_SUPERVISOR_DISPATCH_CONFIG" not in env
            assert "ENGINE_NATIVE_DISPATCH" not in env
            assert "ENGINE_T3_BACKEND" not in env
        """)

    def test_child_env_passes_only_dashboard_process_config_on_explicit_route(self):
        self.run_isolated("""
            from unittest import mock
            from dashboard import subprocess_client as client
            inherited = {
                "DASHBOARD_ENABLE_MANAGED_DISPATCH": "0",
                "DASHBOARD_MANAGED_SUPERVISOR_DISPATCH_CONFIG": "/tmp/forged.json",
            }
            with mock.patch.object(client, "MANAGED_SUPERVISOR_DISPATCH_ENABLED", True), \\
                 mock.patch.object(client, "MANAGED_SUPERVISOR_DISPATCH_CONFIG", "/etc/dashboard/managed.json"):
                env = client.child_env(inherited, forward_engine_dispatch=False,
                                       managed_dispatch=True)
            assert env["DASHBOARD_ENABLE_MANAGED_DISPATCH"] == "1"
            assert env["DASHBOARD_MANAGED_SUPERVISOR_DISPATCH_CONFIG"] == "/etc/dashboard/managed.json"
            assert "ENGINE_NATIVE_DISPATCH" not in env
            assert "ENGINE_T3_BACKEND" not in env
        """)

    def test_run_refuses_half_configured_managed_dispatch_before_spawn(self):
        self.run_isolated("""
            import asyncio
            import tempfile
            from pathlib import Path
            from unittest import mock
            from dashboard import subprocess_client as client

            async def attempt(enabled, config_path):
                with tempfile.TemporaryDirectory(prefix="managed-run-root-") as tmp:
                    with mock.patch.object(client, "MANAGED_SUPERVISOR_DISPATCH_ENABLED", enabled), \\
                         mock.patch.object(client, "MANAGED_SUPERVISOR_DISPATCH_CONFIG", config_path):
                        try:
                            await client.run_action(Path(tmp), "run")
                        except client.SubprocessClientError:
                            return
                        raise AssertionError("half-configured dispatch unexpectedly proceeded")

            asyncio.run(attempt(False, "/tmp/config.json"))
            asyncio.run(attempt(True, None))
        """)


if __name__ == "__main__":
    unittest.main()
