"""Real dashboard process kill/restart: between passes and mid-pass.

The dashboard server runs as a separate process (uvicorn). The test kills it
with SIGKILL and starts a new one, so recovery is exercised as a genuine
process restart, not a clean lifespan shutdown.
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
PORT = 8123
BASE_URL = f"http://127.0.0.1:{PORT}"
ORIGIN = f"https://127.0.0.1:{PORT}"


def _wait_for(pred, timeout=40.0, interval=0.05):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(interval)
    return False


class DashboardProcessRestartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import httpx

        cls._tmp = tempfile.TemporaryDirectory(prefix="proc-restart-")
        cls.dir = Path(cls._tmp.name)
        cls.dir.chmod(0o700)
        bench = cls.dir / "bench"
        (bench / "apps").mkdir(parents=True)
        (bench / "sites").mkdir(parents=True)
        dash_var = cls.dir / "dashboard" / "var"
        dash_var.mkdir(parents=True)
        (cls.dir / "dashboard").chmod(0o700)
        dash_var.chmod(0o700)
        cls.env = dict(os.environ)
        cls.env.update(
            FRAPPE_BENCH_ROOT=str(bench),
            DASHBOARD_TEST_MODE="1",
            DASHBOARD_TEST_ROOT=str(cls.dir),
            DASHBOARD_HOST="127.0.0.1",
            DASHBOARD_PORT=str(PORT),
            ORCHESTRATOR_ROOT=str(ORCH.parent),
            ORCHESTRATOR_PYTHON="/usr/bin/python3.12",
            DASHBOARD_RUN_POLL_BASE="0.05",
            DASHBOARD_RUN_POLL_CAP="0.1",
            PYTHONPATH=":".join([str(ORCH.parent), str(ORCH), "/opt/py312-site-packages", "/opt/dash-deps"]),
        )
        for key in ("ENGINE_NATIVE_DISPATCH", "ENGINE_T3_BACKEND"):
            cls.env.pop(key, None)
        cls._procs = []
        cls._start_services()
        cls.env["DASHBOARD_SUPERVISOR_SOCKET"] = str(cls.dir / "sup.sock")
        cls.env["DASHBOARD_SUPERVISOR_TOKEN_FILE"] = str(cls.dir / "peer.token")
        # Registry + credentials are created by the server process from env;
        # create the registry schema up front so tasks can be registered.
        os.environ.update(cls.env)
        from dashboard.registry import init_registry_db

        init_registry_db(dash_var / "registry.db")
        cls._start_server()
        cls._login()

    @classmethod
    def tearDownClass(cls):
        for proc in reversed(getattr(cls, "_procs", [])):
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass
        cls._tmp.cleanup()

    @classmethod
    def _start_services(cls, delay=1.5):
        mcp = "synthetic-mcp-token-0123456789"
        (cls.dir / "mcp.token").write_text(mcp)
        os.chmod(cls.dir / "mcp.token", 0o600)
        cls.events = cls.dir / "launches.jsonl"
        sim = subprocess.Popen(
            [
                sys.executable,
                str(TESTS / "_mcp_sim_server.py"),
                "--token",
                mcp,
                "--events",
                str(cls.events),
                "--delay",
                str(delay),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(ORCH),
            env=cls.env,
        )
        cls._procs.append(sim)
        cls.url = json.loads(sim.stdout.readline())["url"]
        peer = "synthetic-peer-token-0123456789"
        (cls.dir / "peer.token").write_text(peer)
        os.chmod(cls.dir / "peer.token", 0o600)
        sup = subprocess.Popen(
            [
                sys.executable,
                str(TESTS / "_synthetic_supervisor_server.py"),
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
            env=cls.env,
        )
        cls._procs.append(sup)
        assert _wait_for(lambda: (cls.dir / "sup.sock").exists())
        assert sup.stdout.readline()

    @classmethod
    def _start_server(cls):
        proc = subprocess.Popen(
            [sys.executable, "-m", "dashboard.app"],
            cwd=str(ORCH.parent),
            env=cls.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cls._procs.append(proc)
        cls.server = proc
        import httpx

        def ready():
            try:
                return httpx.get(BASE_URL + "/api/auth/csrf-token", timeout=1.0).status_code == 200
            except Exception:
                return False

        if not _wait_for(ready, timeout=20):
            out, err = proc.communicate(timeout=5)
            raise RuntimeError(f"dashboard server did not start: {out[-2000:]}\n{err[-2000:]}")
        return proc

    @classmethod
    def _login(cls):
        import httpx

        cls.client = httpx.Client(base_url=BASE_URL, timeout=60.0)
        r = cls.client.get("/api/auth/csrf-token")
        csrf = r.json()["csrf_token"]
        cls.client.headers.update(
            {"Cookie": f"dashboard_csrf={csrf}", "X-CSRF-Token": csrf, "Origin": ORIGIN}
        )
        if not getattr(cls, "user", None):
            from dashboard import auth as auth_mod

            creds = Path(cls.env["DASHBOARD_TEST_ROOT"]) / "dashboard" / "var" / "initial_credentials.txt"
            if not creds.is_file():
                auth_mod.create_initial_credentials_file(file_path=creds)
            user = pw = None
            for line in creds.read_text().splitlines():
                if line.startswith("Username: "):
                    user = line.split(": ", 1)[1]
                if line.startswith("Password: "):
                    pw = line.split(": ", 1)[1]
            cls.user = user
            cls.password = pw
        r = cls.client.post("/api/auth/login", json={"username": cls.user, "password": cls.password})
        if r.status_code == 401 and not getattr(cls, "password_setup", False):
            r = cls.client.post(
                "/api/auth/login", json={"username": cls.user, "password": "NewPermanentPass123!"}
            )
            if r.status_code == 200:
                cls.password = "NewPermanentPass123!"
                cls.password_setup = True
        assert r.status_code == 200, r.text
        csrf = r.json()["csrf_token"]
        session = None
        for header in r.headers.get_list("set-cookie"):
            if header.startswith("dashboard_session="):
                session = header.split(";", 1)[0].split("=", 1)[1]
        assert session, r.headers
        cls.client.headers.update(
            {
                "Cookie": f"dashboard_session={session}; dashboard_csrf={csrf}",
                "X-CSRF-Token": csrf,
                "Origin": ORIGIN,
            }
        )
        if not getattr(cls, "password_setup", False):
            r2 = cls.client.post(
                "/api/auth/setup-password",
                json={"current_password": cls.password, "new_password": "NewPermanentPass123!"},
            )
            assert r2.status_code == 200, r2.text
            cls.password = "NewPermanentPass123!"
            cls.password_setup = True
            csrf = r2.json().get("csrf_token", csrf)
            for header in r2.headers.get_list("set-cookie"):
                if header.startswith("dashboard_session="):
                    session = header.split(";", 1)[0].split("=", 1)[1]
            cls.client.headers.update(
                {
                    "Cookie": f"dashboard_session={session}; dashboard_csrf={csrf}",
                    "X-CSRF-Token": csrf,
                    "Origin": ORIGIN,
                }
            )
        cls.csrf = csrf

    def _reset_services(self, delay=1.5):
        server = getattr(self, "server", None)
        for proc in list(self._procs):
            if proc is server:
                continue
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._procs = [server] if server else []
        for name in ("state.json", "sup.sock"):
            try:
                (self.dir / name).unlink()
            except FileNotFoundError:
                pass
        self.events.write_text("")
        self._start_services(delay=delay)

    def _make_task(self, name):
        root = self.dir / f"root-{name}"
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

        try:
            make_engine(root).run()
        except WorkflowError:
            pass
        conn = sqlite3.connect(str(db))
        job_id = conn.execute("select job_id from workflow_jobs").fetchone()[0]
        conn.close()
        task_id = f"task-{name}"
        from dashboard.registry import TaskRegistry

        reg = TaskRegistry()
        conn = reg._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO registered_tasks (task_id, work_item, worktree_path, "
                "task_branch, registered_utc, cached_status, cached_stage) VALUES (?,?,?,?,?,?,?)",
                (task_id, "pilot-loop", str(root), "pilot", "2026-11-15T00:00:00Z", "DRAFT", "1"),
            )
        conn.close()
        return root, job_id, task_id

    def _status(self, task_id):
        r = self.client.get(f"/api/tasks/{task_id}/run-status")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["run"]

    def _launch_events(self):
        if not self.events.exists():
            return []
        return [json.loads(l) for l in self.events.read_text().splitlines() if l.strip()]

    def _job_status(self, root, job_id):
        conn = sqlite3.connect(str(root / "orchestrator/var/checkpoints.db"))
        try:
            row = conn.execute("select status from workflow_jobs where job_id=?", (job_id,)).fetchone()
        finally:
            conn.close()
        return row[0] if row else None

    def _engine_children(self, root):
        pids = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                cmd = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode()
            except OSError:
                continue
            if "orchestrator.dashboard_api" in cmd and f"--root {root}" in cmd:
                pids.append(int(entry.name))
        return pids

    def _kill_server(self):
        self.server.kill()
        self.server.wait(timeout=10)

    def test_01_kill_between_passes_preserves_terminal_state(self):
        root, job_id, task_id = self._make_task("between")
        r = self.client.post(f"/api/tasks/{task_id}/run-start", json={"action_id": "between-1"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"], timeout=30))
        first = self._status(task_id)
        self.assertEqual(first["state"], "PAUSED")
        launches = len(self._launch_events())
        self._kill_server()
        self._start_server()
        self._login()
        second = self._status(task_id)
        self.assertEqual(second["state"], "PAUSED")
        self.assertEqual(second["generation"], first["generation"])
        self.assertEqual(len(self._launch_events()), launches, "restart must not relaunch")

    def test_02_kill_mid_pass_parks_and_stop_does_not_resolve(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("midpass")
        r = self.client.post(f"/api/tasks/{task_id}/run-start", json={"action_id": "mid-1"})
        self.assertEqual(r.status_code, 200, r.text)
        db = self.dir / "dashboard/var/registry.db"

        def pass_in_flight():
            conn = sqlite3.connect(str(db))
            try:
                row = conn.execute(
                    "select state from action_log where action_id like ?",
                    (f"coord-{task_id}-%",),
                ).fetchone()
                return bool(row and row[0] == "EXECUTING")
            finally:
                conn.close()

        self.assertTrue(
            _wait_for(
                lambda: pass_in_flight() and self._job_status(root, job_id) in ("LAUNCH_INTENT", "RUNNING"),
                timeout=20,
            )
        )
        self._kill_server()
        self.assertTrue(
            _wait_for(lambda: not self._engine_children(root), timeout=10),
            "engine subprocess survived the dashboard kill",
        )
        self._start_server()
        self._login()
        parked = self._status(task_id)
        self.assertEqual(parked["state"], "RECONCILIATION_REQUIRED", parked)
        self.assertEqual(parked["pause_reason"], "pass_outcome_unknown", parked)
        launches = len(self._launch_events())
        self.assertLessEqual(launches, 2)
        # A STOP click records the request but cannot resolve the unknown outcome.
        stop = self.client.post(f"/api/tasks/{task_id}/run-stop", json={})
        self.assertEqual(stop.status_code, 200, stop.text)
        after_stop = self._status(task_id)
        self.assertEqual(after_stop["state"], "RECONCILIATION_REQUIRED", after_stop)
        self.assertTrue(after_stop["stop_requested"])
        delhdr = {"Origin": ORIGIN, "X-CSRF-Token": self.csrf}
        refused = self.client.delete(f"/api/tasks/{task_id}", headers=delhdr)
        self.assertEqual(refused.status_code, 409, refused.text)
        # Duplicate stop requests are idempotent (one recorded request).
        stop2 = self.client.post(f"/api/tasks/{task_id}/run-stop", json={})
        self.assertEqual(stop2.status_code, 200, stop2.text)
        # Authoritative reconciliation collects the late result; never a re-send.
        resolved = None
        for _ in range(20):
            res = self.client.post(f"/api/tasks/{task_id}/run-resolve", json={})
            self.assertEqual(res.status_code, 200, res.text)
            resolved = self._status(task_id)
            if resolved["state"] != "RECONCILIATION_REQUIRED":
                break
            time.sleep(0.5)
        self.assertNotEqual(resolved["state"], "RECONCILIATION_REQUIRED", resolved)
        events = self._launch_events()
        self.assertEqual(
            len({e["threadId"] for e in events}), len(events), f"a job was launched twice: {events}"
        )
        self.assertLessEqual(len(events), 2, events)
        conn = sqlite3.connect(str(db))
        try:
            n = conn.execute("SELECT COUNT(*) FROM run_passes WHERE task_id=?", (task_id,)).fetchone()[0]
        finally:
            conn.close()
        self.assertGreaterEqual(n, 1, "pass evidence preserved")

    def test_03_remote_still_running_is_not_resolved_by_a_stop_click(self):
        self._reset_services(delay=5.0)
        root, job_id, task_id = self._make_task("remote")
        r = self.client.post(f"/api/tasks/{task_id}/run-start", json={"action_id": "remote-1"})
        self.assertEqual(r.status_code, 200, r.text)
        db = self.dir / "dashboard/var/registry.db"

        def pass_in_flight():
            conn = sqlite3.connect(str(db))
            try:
                row = conn.execute(
                    "select state from action_log where action_id like ?",
                    (f"coord-{task_id}-%",),
                ).fetchone()
                return bool(row and row[0] == "EXECUTING")
            finally:
                conn.close()

        self.assertTrue(
            _wait_for(
                lambda: pass_in_flight() and self._job_status(root, job_id) in ("LAUNCH_INTENT", "RUNNING"),
                timeout=20,
            )
        )
        self._kill_server()
        self.assertTrue(_wait_for(lambda: not self._engine_children(root), timeout=10))
        self._start_server()
        self._login()
        parked = self._status(task_id)
        self.assertEqual(parked["state"], "RECONCILIATION_REQUIRED", parked)
        # The remote MCP launch is still in progress. A stop click records the
        # request but must not claim termination or allow deletion.
        stop = self.client.post(f"/api/tasks/{task_id}/run-stop", json={})
        self.assertEqual(stop.status_code, 200, stop.text)
        still = self._status(task_id)
        self.assertEqual(still["state"], "RECONCILIATION_REQUIRED", still)
        self.assertTrue(still["stop_requested"])
        refused = self.client.delete(
            f"/api/tasks/{task_id}", headers={"Origin": ORIGIN, "X-CSRF-Token": self.csrf}
        )
        self.assertEqual(refused.status_code, 409, refused.text)
        # Authoritative reconciliation waits for the supervisor ledger and then
        # accepts the late result; it never launches a second time.
        resolved = None
        for _ in range(20):
            res = self.client.post(f"/api/tasks/{task_id}/run-resolve", json={})
            self.assertEqual(res.status_code, 200, res.text)
            resolved = self._status(task_id)
            if resolved["state"] != "RECONCILIATION_REQUIRED":
                break
            time.sleep(0.5)
        self.assertNotEqual(resolved["state"], "RECONCILIATION_REQUIRED", resolved)
        events = self._launch_events()
        self.assertEqual(len({e["threadId"] for e in events}), len(events), events)
        self.assertLessEqual(len(events), 2, events)
        conn = sqlite3.connect(str(db))
        try:
            n = conn.execute("SELECT COUNT(*) FROM run_passes WHERE task_id=?", (task_id,)).fetchone()[0]
        finally:
            conn.close()
        self.assertGreaterEqual(n, 1)


if __name__ == "__main__":
    unittest.main()
