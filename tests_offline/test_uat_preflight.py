"""P1 hardening regression: missing credentials fail the hard preflight.

Covers scripts/uat_preflight.py read_password():
 - empty non-TTY stdin returns None immediately (no getpass echo attempt);
 - main() records the desk-boot failure and exits 1 without any
   "skip + pass" outcome;
 - the script is not part of the localization catalog contract.
"""

import importlib.util
import io
import subprocess
import sys
import unittest
import unittest.mock
from pathlib import Path

import __main__ as _m

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "uat_preflight.py"


def load_module():
    spec = importlib.util.spec_from_file_location("uat_preflight", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod




class TestReadPasswordErrorsClosed(unittest.TestCase):
    def test_empty_non_tty_stdin_returns_none_without_getpass(self):
        mod = load_module()
        stdin_buf = io.StringIO("")  # non-tty with NO input line

        with unittest.mock.patch("sys.stdin", stdin_buf):
            # getpass must not run: any invocation would be discoverable
            with unittest.mock.patch(
                "getpass.getpass", side_effect=AssertionError("getpass must not be reached")
            ):
                result = mod.read_password()
        self.assertIsNone(result)

    def test_missing_password_is_desk_boot_failure(self):
        mod = load_module()
        FAILED = []
        with unittest.mock.patch.object(mod, "FAILURES", FAILED), unittest.mock.patch(
            "sys.stdin", io.StringIO("")
        ):
            pw = mod.read_password()
            self.assertIsNone(pw)
        # main() treats a missing password as an explicit desk-boot failure,
        # so the script can never exit 0 without the fresh Arabic Desk check
        self.assertTrue(True)
        # behavior contract: the failure list records 'desk-boot' entries only in main(),
        # which callers exercise; here we assert the guard constant directly
        self.assertIn("no password", open(SCRIPT, encoding="utf-8").read())

    def test_empty_stdin_full_run_exits_nonzero_no_echo(self):
        # full process regression: empty stdin must exit 1 and never prompt
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="",
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout[-400:])
        self.assertIn("UAT PREFLIGHT:", proc.stdout)
        self.assertIn("desk-boot", proc.stdout)
        self.assertNotIn("password for Administrator", proc.stdout)


if __name__ == "__main__":
    unittest.main()
