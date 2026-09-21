"""Offline regression: site-connection exceptions in the preflight are
recorded as clean preflight failures — never a traceback, never a crash
exit path (Stage-8-x robustness review, owner request 2026-09-21).
"""

import http.client
import importlib.util
import io
import subprocess
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "uat_preflight.py"


def load_module():
    spec = importlib.util.spec_from_file_location("uat_preflight", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestConnectionExceptionRecorded(unittest.TestCase):
    def test_connection_exception_records_failure_without_traceback(self):
        mod = load_module()
        mod.FAILURES.clear()
        with unittest.mock.patch.object(
            mod,
            "http_req",
            side_effect=http.client.RemoteDisconnected("simulated drop"),
        ):
            mod.http_req_attested("v16.localhost", "/desk")
        recorded = "".join(mod.FAILURES)
        self.assertIn("connection: /desk", recorded)
        self.assertIn("RemoteDisconnected", recorded)

    def test_no_password_from_empty_stdin_direct(self):
        mod = load_module()
        with unittest.mock.patch("sys.stdin", io.StringIO("")):
            self.assertIsNone(mod.read_password())

    def test_full_process_empty_stdin_exits_1(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="",
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("desk-boot", proc.stdout)
        self.assertNotIn("Traceback", proc.stderr)


if __name__ == "__main__":
    unittest.main()
