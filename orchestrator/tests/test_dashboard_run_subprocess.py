"""Real HTTP -> production subprocess -> engine -> supervisor -> simulator.

No monkeypatching of run_action: the dashboard spawns
`python -m orchestrator.dashboard_api --action run --supervisor-socket ...`,
which builds the engine with the supervisor launcher. The supervisor is the
test-only process backed by the local MCP simulator; the engine only sees a
socket path (production contract).
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ORCH = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ORCH))
sys.path.insert(0, str(TESTS))

MODEL = "opencode/deepseek-v4.1-flash-free"
BASE_FIXTURE = Path(os.environ.get("T3_SEAM_BASE_FIXTURE", "/opt/base-fixture"))
OLD_ROOT = os.environ.get("T3_SEAM_OLD_ROOT", "/var/tmp/guard-case-base-20261115")


def _wait_for(pred, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.05)
    return False


class DashboardRunSubprocessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="dash-sub-")
        cls.dir = Path(cls._tmp.name)
        cls.dir.chmod(0o700)
        bench = cls.dir / "bench"
        (bench / "apps").mkdir(parents=True)
        (bench / "sites").mkdir(parents=True)
        dash_var = cls.dir / "dashboard" / "var"
        dash_var.mkdir(parents=True)
        (cls.dir / "dashboard").chmod(0o700)
        dash_var.chmod(0o700)
        os.environ["FRAPPE_BENCH_ROOT"] = str(bench)
        os.environ["DASHBOARD_TEST_MODE"] = "1"
        os.environ["DASHBOARD_TEST_ROOT"] = str(cls.dir)
        os.environ["ORCHESTRATOR_ROOT"] = str(ORCH.parent)
        os.environ["ORCHESTRATOR_PYTHON"] = "/usr/bin/python3.12"
        cls._procs = []
        cls._start_services()
        os.environ["DASHBOARD_SUPERVISOR_SOCKET"] = str(cls.dir / "sup.sock")
        os.environ["DASHBOARD_SUPERVISOR_TOKEN_FILE"] = str(cls.dir / "peer.token")
        try:
            import dashboard.app
            import dashboard.registry as registry_mod
        except Exception as exc:
            raise unittest.SkipTest(f"dashboard unavailable: {type(exc).__name__}: {exc}")
        registry_mod.init_registry_db(dash_var / "registry.db")
        from starlette.testclient import TestClient

        import dashboard.app as appmod

        cls.appmod = appmod
        cls.registry_mod = registry_mod
        cls.client = TestClient(appmod.app, base_url="https://127.0.0.1:8080")
        cls.client.__enter__()
        cls._login()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.client.__exit__(None, None, None)
        finally:
            for p in getattr(cls, "_procs", []):
                try:
                    p.terminate()
                    p.wait(timeout=5)
                except Exception:
                    try:
                        p.kill()
                    except Exception:
                        pass
            cls._tmp.cleanup()

    @classmethod
    def _start_services(cls, fail=None):
        mcp = "synthetic-mcp-token-0123456789"
        (cls.dir / "mcp.token").write_text(mcp)
        os.chmod(cls.dir / "mcp.token", 0o600)
        cls.events = cls.dir / "launches.jsonl"
        args = [
            sys.executable,
            str(TESTS / "_mcp_sim_server.py"),
            "--token",
            mcp,
            "--events",
            str(cls.events),
        ] + (["--fail", fail] if fail else [])
        sim = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ORCH))
        cls._procs.append(sim)
        cls.url = json.loads(sim.stdout.readline())["url"]
        peer = "synthetic-peer-token-0123456789"
        (cls.dir / "peer.token").write_text(peer)
        os.chmod(cls.dir / "peer.token", 0o600)
        sup = subprocess.Popen(
            [
                sys.executable,
                str(ORCH / "t3_supervisor.py"),
                "--socket",
                str(cls.dir / "sup.sock"),
                "--state",
                str(cls.dir / "state.json"),
                "--token-file",
                str(cls.dir / "peer.token"),
                "--base-url",
                cls.url,
                "--mcp-token-file",
                str(cls.dir / "mcp.token"),
                "--model",
                MODEL,
                "--allowed-model",
                MODEL,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(ORCH),
        )
        cls._procs.append(sup)
        assert _wait_for(lambda: (cls.dir / "sup.sock").exists())
        assert sup.stdout.readline()

    @classmethod
    def _login(cls):
        from dashboard import auth as auth_mod

        creds = auth_mod.auth_store.credentials_file_path
        if not creds.is_file():
            auth_mod.create_initial_credentials_file(file_path=creds)
        user = pw = None
        for line in creds.read_text().splitlines():
            if line.startswith("Username: "):
                user = line.split(": ", 1)[1]
            if line.startswith("Password: "):
                pw = line.split(": ", 1)[1]
        cls.client.get("/api/auth/csrf-token")
        tok = cls.client.cookies.get("dashboard_csrf") or ""
        r = cls.client.post(
            "/api/auth/login",
            json={"username": user, "password": pw},
            headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": tok},
        )
        assert r.status_code == 200, r.text
        csrf = r.json()["csrf_token"]
        r2 = cls.client.post(
            "/api/auth/setup-password",
            json={"current_password": pw, "new_password": "NewPermanentPass123!"},
            headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": csrf},
        )
        assert r2.status_code == 200, r2.text
        cls.csrf = csrf

    @classmethod
    def _make_task(cls, name):
        """Fresh engine root + prepared job + registry task per test."""
        root = cls.dir / f"root-{name}"
        shutil.copytree(BASE_FIXTURE, root)
        db = root / "orchestrator/var/checkpoints.db"
        conn = sqlite3.connect(str(db))
        row = conn.execute("select value from workflow_meta where key='config'").fetchone()
        cfg = json.loads(row[0].replace(OLD_ROOT, str(root)))
        cfg["root"] = str(root)
        conn.execute("update workflow_meta set value=? where key='config'", (json.dumps(cfg),))
        conn.commit()
        conn.close()
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in (".json", ".md", ".txt") and p.stat().st_size < 2_000_000:
                try:
                    text = p.read_text()
                except (UnicodeDecodeError, OSError):
                    continue
                if OLD_ROOT in text:
                    p.write_text(text.replace(OLD_ROOT, str(root)))
        from cli import make_engine
        from core import WorkflowError

        os.environ.pop("ENGINE_NATIVE_DISPATCH", None)
        os.environ.pop("ENGINE_T3_BACKEND", None)
        try:
            make_engine(root).run()
        except WorkflowError:
            pass
        conn = sqlite3.connect(str(db))
        job_id = conn.execute("select job_id from workflow_jobs").fetchone()[0]
        conn.close()
        task_id = f"task-{name}"
        reg = cls.registry_mod.TaskRegistry()
        conn = reg._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO registered_tasks (task_id, work_item, worktree_path, "
                "task_branch, registered_utc, cached_status, cached_stage) VALUES (?,?,?,?,?,?,?)",
                (task_id, "pilot-loop", str(root), "pilot", "2026-11-15T00:00:00Z", "DRAFT", "1"),
            )
        conn.close()
        return root, job_id, task_id

    def _post_run(self, task_id, action_id):
        return self.client.post(
            f"/api/tasks/{task_id}/run",
            json={"action_id": action_id},
            headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": self.csrf},
        )

    def _status(self, root, job_id):
        conn = sqlite3.connect(str(root / "orchestrator/var/checkpoints.db"))
        s = conn.execute("select status from workflow_jobs where job_id=?", (job_id,)).fetchone()[0]
        conn.close()
        return s

    def _launch_count(self, job_id=None):
        if not self.events.exists():
            return 0
        lines = [json.loads(l) for l in self.events.read_text().splitlines() if l.strip()]
        if job_id is not None:
            return len([l for l in lines if f"engine job {job_id}" in (l.get("title") or "")])
        return len(lines)

    def test_01_real_subprocess_success(self):
        root, job_id, task_id = self._make_task("ok")
        before = self._launch_count(job_id)
        r = self._post_run(task_id, "act-sub-ok")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json().get("ok"))
        last = r.json()
        for _ in range(6):
            if self._status(root, job_id) == "ACCEPTED":
                break
            r = self._post_run(task_id, f"act-sub-pass-{time.time_ns()}")
            self.assertEqual(r.status_code, 200, r.text)
            last = r.json()
        self.assertEqual(self._status(root, job_id), "ACCEPTED")
        self.assertTrue(
            (last or {}).get("result", {}).get("terminal"),
            f"run must report terminal once the job is ACCEPTED; got {last}",
        )
        self.assertEqual(self._launch_count(job_id), before + 1, "one launch via the real subprocess path")
        # A further pass after ACCEPTED must be terminal and must not dispatch again.
        r2 = self._post_run(task_id, f"act-sub-after-{time.time_ns()}")
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertTrue(r2.json()["result"]["terminal"], r2.text)
        self.assertEqual(self._launch_count(job_id), before + 1)

    def test_02_child_env_strips_dispatch_ack(self):
        """The browser click must not inherit a host-level dispatch ack."""
        from dashboard.subprocess_client import child_env

        armed = {
            "ENGINE_NATIVE_DISPATCH": "allow-native-host-access",
            "ENGINE_T3_BACKEND": "t3",
            "KEEP": "1",
        }
        stripped = child_env(armed, forward_engine_dispatch=False)
        self.assertNotIn("ENGINE_NATIVE_DISPATCH", stripped)
        self.assertNotIn("ENGINE_T3_BACKEND", stripped)
        self.assertEqual(stripped["KEEP"], "1")
        self.assertIn("CANONICAL_DASHBOARD_REGISTRY", stripped)
        forwarded = child_env(armed, forward_engine_dispatch=True)
        self.assertEqual(forwarded["ENGINE_NATIVE_DISPATCH"], "allow-native-host-access")

    def test_03_real_subprocess_duplicate_is_cached(self):
        root, job_id, task_id = self._make_task("dup")
        r1 = self._post_run(task_id, "act-sub-dup")
        self.assertEqual(r1.status_code, 200, r1.text)
        launches = self._launch_count(job_id)
        r2 = self._post_run(task_id, "act-sub-dup")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["result"], r1.json()["result"])
        self.assertEqual(self._launch_count(job_id), launches)

    def test_04_refusal_surfaces_as_clear_error(self):
        root, job_id, task_id = self._make_task("refused")
        # stop the supervisor; the run must fail with a clear error, no dispatch
        sup = self._procs[-1]
        sup.terminate()
        sup.wait(timeout=5)
        launches = self._launch_count(job_id)
        r = self._post_run(task_id, f"act-sub-refused-{time.time_ns()}")
        self.assertEqual(r.status_code, 500, r.text)
        self.assertIn("Run failed", r.text)
        self.assertEqual(self._launch_count(job_id), launches)
        # restart for any later test
        self._start_services()


if __name__ == "__main__":
    unittest.main()
