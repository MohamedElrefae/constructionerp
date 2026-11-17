"""Process-tree behaviour on abrupt parent death.

PDEATHSIG is set on the direct child only; grandchildren are not covered. This
test proves that limitation instead of assuming parent death kills every child.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ORCH = Path(__file__).resolve().parents[1]
PARENT = Path(__file__).resolve().parent / "_pdeathsig_parent.py"


def _alive(pid):
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        return state != "Z"
    except (OSError, IndexError):
        return False


def _wait(pred, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.05)
    return False


class ProcessTreeTests(unittest.TestCase):
    def test_pdeathsig_kills_direct_child_but_not_grandchild(self):
        tmp = tempfile.mkdtemp(prefix="pdeathsig-")
        pidfile = Path(tmp) / "grandchild.pid"
        env = dict(os.environ)
        env["PYTHONPATH"] = ":".join(
            [str(ORCH.parent), str(ORCH), env.get("PYTHONPATH", "")]
        )
        parent = subprocess.Popen(
            [sys.executable, str(PARENT), str(pidfile)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=str(ORCH), env=env)
        try:
            line = parent.stdout.readline()
            self.assertTrue(line, "parent did not report a child pid")
            child = json.loads(line)["child"]
            self.assertTrue(_wait(lambda: pidfile.exists()), "no grandchild pid")
            grandchild = int(pidfile.read_text().strip())
            self.assertTrue(_alive(child))
            self.assertTrue(_alive(grandchild))
            parent.kill()
            parent.wait(timeout=5)
            self.assertTrue(
                _wait(lambda: not _alive(child)), "direct child survived parent death")
            # Grandchildren do not inherit PDEATHSIG.
            self.assertTrue(_alive(grandchild), "grandchild unexpectedly died")
        finally:
            try:
                os.kill(grandchild, signal.SIGKILL)
            except (OSError, UnboundLocalError):
                pass
            try:
                parent.kill()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
