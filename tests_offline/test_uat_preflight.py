"""Offline regression: site-connection exceptions in the preflight are
recorded as clean preflight failures — never a traceback, never a crash
exit path (Stage-8-x robustness review, owner request 2026-09-21).
"""

import http.client
import importlib.util
import io
import json
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

    def test_attested_request_uses_configured_port(self):
        mod = load_module()
        mod.FAILURES.clear()
        mod.UAT_PORT = 8002
        with unittest.mock.patch.object(mod, "http_req", return_value=(200, "", None)) as req:
            mod.http_req_attested("v16rehearsal.localhost", "/api/method/ping")
        req.assert_called_once_with(
            "v16rehearsal.localhost",
            "/api/method/ping",
            method="GET",
            body=None,
            headers=None,
            port=8002,
        )

    def test_main_posts_login_request(self):
        mod = load_module()
        mod.FAILURES.clear()
        desk_html = "frappe.boot = " + json.dumps(
            {"lang": "ar", "__messages": {str(i): "v" for i in range(1000)}}
        ) + ";\n"
        with (
            unittest.mock.patch("sys.argv", ["uat_preflight.py", "--port=8002"]),
            unittest.mock.patch("sys.stdin", io.StringIO("password\n")),
            unittest.mock.patch.object(mod, "redis_reachable"),
            unittest.mock.patch.object(
                mod,
                "http_req_attested",
                side_effect=[(200, "", None), (200, "", "sid-1"), (200, desk_html, None)],
            ) as request,
            unittest.mock.patch.object(mod, "logout"),
        ):
            self.assertEqual(mod.main(), 0)
        self.assertEqual(request.call_args_list[1].kwargs["method"], "POST")

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
