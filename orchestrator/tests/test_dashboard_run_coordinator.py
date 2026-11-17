"""Real HTTP -> subprocess -> engine -> test-only supervisor -> simulator.

No monkeypatching: the dashboard's durable run coordinator spawns
``python -m orchestrator.dashboard_api --action run --supervisor-socket ...``.
The synthetic backend lives only in the test supervisor process; production
cannot select it (see dashboard/config.py test gate).
"""

import json
import os
import shlex
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


def _wait_for(pred, timeout=40.0, interval=0.05):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(interval)
    return False


class DashboardRunCoordinatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="runcoord-http-")
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
        test_python = cls.dir / "coordinator-test-python"
        helper = TESTS / "_coordinator_test_python.py"
        test_python.write_text(
            "#!/bin/sh\nexec " + shlex.quote(sys.executable) + " " + shlex.quote(str(helper)) + ' "$@"\n'
        )
        test_python.chmod(0o700)
        os.environ["ORCHESTRATOR_PYTHON"] = str(test_python)
        os.environ["DASHBOARD_RUN_POLL_BASE"] = "0.05"
        os.environ["DASHBOARD_RUN_POLL_CAP"] = "0.1"
        cls._procs = []
        cls._start_services()
        os.environ["DASHBOARD_SUPERVISOR_SOCKET"] = str(cls.dir / "sup.sock")
        os.environ["DASHBOARD_SUPERVISOR_TOKEN_FILE"] = str(cls.dir / "peer.token")
        try:
            import dashboard.app
            import dashboard.registry as registry_mod
            import dashboard.subprocess_client as subprocess_client
        except Exception as exc:
            raise unittest.SkipTest(f"dashboard unavailable: {type(exc).__name__}: {exc}")
        # The test-owned Python shim injects the synthetic launcher only in
        # subprocesses created by this integration suite.
        subprocess_client.ORCHESTRATOR_PYTHON = test_python
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
    def _start_services(cls):
        mcp = "synthetic-mcp-token-0123456789"
        (cls.dir / "mcp.token").write_text(mcp)
        os.chmod(cls.dir / "mcp.token", 0o600)
        cls.events = cls.dir / "launches.jsonl"
        sim = subprocess.Popen(
            [sys.executable, str(TESTS / "_mcp_sim_server.py"), "--token", mcp, "--events", str(cls.events)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(ORCH),
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
        )
        cls._procs.append(sup)
        assert _wait_for(lambda: (cls.dir / "sup.sock").exists())
        assert sup.stdout.readline()

    def _reset_services(self):
        """Fresh supervisor ledger so each task gets a real, countable launch."""
        for proc in self._procs:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._procs.clear()
        for name in ("state.json", "sup.sock"):
            try:
                (self.dir / name).unlink()
            except FileNotFoundError:
                pass
        self.events.write_text("")
        self._start_services()

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
        cls.user = user

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
        reg = self.registry_mod.TaskRegistry()
        conn = reg._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO registered_tasks (task_id, work_item, worktree_path, "
                "task_branch, registered_utc, cached_status, cached_stage) VALUES (?,?,?,?,?,?,?)",
                (task_id, "pilot-loop", str(root), "pilot", "2026-11-15T00:00:00Z", "DRAFT", "1"),
            )
        conn.close()
        return root, job_id, task_id

    def _post(self, path, body=None, csrf=None):
        return self.client.post(
            path,
            json=body or {},
            headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": csrf or self.csrf},
        )

    def _status(self, task_id):
        r = self.client.get(f"/api/tasks/{task_id}/run-status")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["run"]

    def _launch_events(self):
        if not self.events.exists():
            return []
        return [json.loads(l) for l in self.events.read_text().splitlines() if l.strip()]

    def _launches_since(self, job_id, before):
        return self._launch_count(job_id) - before

    def _launch_count(self, job_id):
        if not self.events.exists():
            return 0
        lines = [json.loads(l) for l in self.events.read_text().splitlines() if l.strip()]
        return len([l for l in lines if f"engine job {job_id}" in (l.get("title") or "")])

    def test_01_start_reaches_a_durable_terminal_state(self):
        # One pass dispatches architect and reviewer; the run then parks on the
        # owner PLAN gate (a deliberate pause, not a failure).
        self._reset_services()
        root, job_id, task_id = self._make_task("ok")
        before = self._launch_count(job_id)
        r = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-ok"})
        self.assertEqual(r.status_code, 200, r.text)
        ok = _wait_for(lambda: self._status(task_id)["terminal"])
        run = self._status(task_id)
        self.assertTrue(ok, run)
        self.assertEqual(run["state"], "PAUSED", run)
        self.assertEqual(run["pause_reason"], "gate", run)
        self.assertEqual(run["passes"], 1)
        view = (run.get("last_result") or {}).get("view") or {}
        self.assertEqual(view.get("status"), "PLAN_SUBMITTED")
        self.assertEqual(view.get("gate", {}).get("scope"), "PLAN")
        self.assertEqual(len(self._launch_events()), 2)
        conn = sqlite3.connect(str(root / "orchestrator/var/checkpoints.db"))
        statuses = dict(conn.execute("select job_id, status from workflow_jobs").fetchall())
        conn.close()
        self.assertEqual(sorted(statuses.values()), ["ACCEPTED", "ACCEPTED"])

    def test_02_browser_disconnect_does_not_stop_the_run(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("disc")
        before = self._launch_count(job_id)
        r = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-disc"})
        self.assertEqual(r.status_code, 200, r.text)
        # No status polling at all: the server loop must finish on its own.
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        self.assertEqual(len(self._launch_events()), 2)

    def test_03_duplicate_start_is_replayed(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("dup")
        before = self._launch_count(job_id)
        r1 = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-dup"})
        self.assertEqual(r1.status_code, 200, r1.text)
        r2 = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-dup"})
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertTrue(r2.json().get("replayed"))
        self.assertEqual(r1.json()["run"]["generation"], r2.json()["run"]["generation"])
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        self.assertEqual(len(self._launch_events()), 2)

    def test_04_competing_starts_have_one_winner(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("race")
        before = self._launch_count(job_id)
        import threading

        results = []

        def start(action_id):
            results.append(self._post(f"/api/tasks/{task_id}/run-start", {"action_id": action_id}))

        threads = [threading.Thread(target=start, args=(f"start-race-{i}",)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        codes = sorted(r.status_code for r in results)
        self.assertEqual(codes, [200, 409], [r.text for r in results])
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        self.assertEqual(len(self._launch_events()), 2)

    def test_05_stop_leaves_no_child_processes(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("stop")
        before = self._launch_count(job_id)
        r = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-stop"})
        self.assertEqual(r.status_code, 200, r.text)
        stop = self._post(f"/api/tasks/{task_id}/run-stop")
        self.assertEqual(stop.status_code, 200, stop.text)
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        self.assertTrue(_wait_for(lambda: not self._children(), timeout=10))
        self.assertLessEqual(self._launches_since(job_id, before), 1)

    def test_06_restart_recovery_resumes_without_duplicate(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("recover")
        before = self._launch_count(job_id)
        dead = subprocess.Popen(["/bin/true"])
        dead.wait(timeout=5)
        now = "2026-11-15T00:00:00Z"
        conn = self.registry_mod.TaskRegistry()._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO run_state (task_id, state, desired, generation, "
                "owner_instance_id, owner_pid, owner_start_time, pass_count, last_pass_index, "
                "last_result_json, last_error, pause_reason, created_utc, updated_utc) "
                "VALUES (?,?,?,?,?,?,?,0,NULL,NULL,NULL,NULL,?,?)",
                (task_id, "RUNNING", "RUN", 1, "inst-dead", dead.pid, 1, now, now),
            )
        conn.close()
        self.client.portal.call(self.appmod.run_coordinator.recover)
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        self.assertEqual(len(self._launch_events()), 2)
        self.assertEqual(self._status(task_id)["generation"], 1)

    def test_07_unauthenticated_and_forged_csrf_are_rejected(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("auth")
        before = self._launch_count(job_id)
        self.client.cookies.clear()
        self.client.get("/api/auth/csrf-token")
        csrf = self.client.cookies.get("dashboard_csrf") or ""
        anon = self.client.post(
            f"/api/tasks/{task_id}/run-start",
            json={"action_id": "a1"},
            headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": csrf},
        )
        self.assertEqual(anon.status_code, 401)
        self.client.get("/api/auth/csrf-token")
        tok = self.client.cookies.get("dashboard_csrf") or ""
        relogin = self.client.post(
            "/api/auth/login",
            json={"username": self.user, "password": "NewPermanentPass123!"},
            headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": tok},
        )
        self.assertEqual(relogin.status_code, 200, relogin.text)
        self.__class__.csrf = relogin.json()["csrf_token"]
        forged = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "a2"}, csrf="forged")
        self.assertEqual(forged.status_code, 403)
        time.sleep(0.2)
        self.assertEqual(self._launches_since(job_id, before), 0)

    def test_08_stale_fence_is_rejected_by_the_engine(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("fence")
        before = self._launch_count(job_id)
        now = "2026-11-15T00:00:00Z"
        conn = self.registry_mod.TaskRegistry()._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO action_log (action_id, task_id, action_type, state, "
                "idempotency_key, request_hash, manifest_json, response_json, correlation_id, "
                "executor_instance_id, executor_pid, executor_start_time, child_pid, child_pgid, "
                "child_start_time, fencing_token, heartbeat_utc, error_message, "
                "session_memory_entry, created_utc, updated_utc) "
                "VALUES (?,?,'run','EXECUTING',?,?,?,NULL,?,?,?,?,NULL,NULL,NULL,1,?,NULL,NULL,?,?)",
                (
                    "stale-pass",
                    task_id,
                    "stale-pass",
                    "h",
                    "{}",
                    "stale-pass",
                    "inst-old",
                    os.getpid(),
                    1,
                    now,
                    now,
                    now,
                ),
            )
        conn.close()
        env = dict(os.environ)
        env["CANONICAL_DASHBOARD_REGISTRY"] = str(self.dir / "dashboard/var/registry.db")
        proc = subprocess.run(
            [
                os.environ["ORCHESTRATOR_PYTHON"],
                "-m",
                "orchestrator.dashboard_api",
                "--root",
                str(root),
                "--action",
                "run",
                "--action-id",
                "stale-pass",
                "--fencing-token",
                "999",
                "--executor-instance-id",
                "inst-stale",
            ],
            capture_output=True,
            text=True,
            cwd=str(ORCH),
            env=env,
            timeout=60,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Fencing validation failed", proc.stdout + proc.stderr)
        self.assertEqual(self._launches_since(job_id, before), 0)

    def test_09_resume_after_pause_does_not_relaunch(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("resume")
        before = self._launch_count(job_id)
        r = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-resume"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        first = self._status(task_id)
        self.assertEqual(len(self._launch_events()), 2)
        r2 = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-resume-2"})
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        second = self._status(task_id)
        self.assertEqual(second["generation"], first["generation"] + 1)
        self.assertEqual(
            len(self._launch_events()),
            2,
            "resume must not relaunch a settled job",
        )

    def test_10_reserved_action_id_prefix_is_rejected(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("reserved")
        before = self._launch_count(job_id)
        r = self._post(
            f"/api/tasks/{task_id}/run-start",
            {"action_id": f"coord-{task_id}-1-0"},
        )
        self.assertEqual(r.status_code, 400, r.text)
        self.assertEqual(self._launches_since(job_id, before), 0)

    def test_11_conflicting_start_is_not_cached_as_success(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("nocache")
        r1 = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-a"})
        self.assertEqual(r1.status_code, 200, r1.text)
        r2 = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-b"})
        if r2.status_code == 409:
            self.assertTrue(r2.json().get("conflict"))
            self.assertFalse(r2.json().get("replayed"))
        else:
            self.assertEqual(r2.status_code, 200, r2.text)
            self.assertFalse(r2.json().get("replayed"), "a conflict must not be replayed as success")
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))

    def test_12_full_workflow_through_all_roles(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("full")
        before = self._launch_count(job_id)
        r = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-full-1"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        first = self._status(task_id)
        _v = (first.get("last_result") or {}).get("view") or {}
        self.assertEqual(_v.get("status"), "PLAN_SUBMITTED", first)
        rv = self._post(f"/api/tasks/{task_id}/create-review", {})
        self.assertEqual(rv.status_code, 200, rv.text)
        ap = self._post(f"/api/tasks/{task_id}/approve-plan", {})
        self.assertEqual(ap.status_code, 200, ap.text)
        r2 = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": "start-full-2"})
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        second = self._status(task_id)
        _v2 = (second.get("last_result") or {}).get("view") or {}
        self.assertEqual(_v2.get("status"), "VERIFIED_FOR_RELEASE", second)
        self.assertEqual(_v2.get("gate", {}).get("scope"), "COMMIT", second)
        # Reviewable commit handoff over HTTP: requirements -> verify (false) ->
        # owner commit in the disposable fixture -> verify (true) -> record the
        # owner token -> the coordinator resumes to COMPLETED.
        req = self.client.get(f"/api/tasks/{task_id}/commit-requirements")
        self.assertEqual(req.status_code, 200, req.text)
        reqs = req.json()
        self.assertTrue(reqs.get("pending"), reqs)
        r = reqs["requirements"]
        self.assertEqual(r["gate_id"], _v2["gate"]["gate_id"])
        self.assertEqual(r["candidate_id"], _v2["candidate"]["candidate_id"])
        self.assertEqual(r["branch"], "pilot")
        verify0 = self._post(f"/api/tasks/{task_id}/commit-verify")
        self.assertEqual(verify0.status_code, 200, verify0.text)
        self.assertFalse(verify0.json().get("verified"), verify0.text)
        import uuid as _uuid

        token = {
            "schema_version": 1,
            "token_id": f"tok-{_uuid.uuid4().hex[:12]}",
            "work_item": _v2["work_item"],
            "gate_id": r["gate_id"],
            "issuer": "synthetic-owner",
            "issued_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "ISSUED",
            "scope": "COMMIT",
            "candidate_id": r["candidate_id"],
            "manifest_hash": r["manifest_hash"],
            "repository_id": r["repository_id"],
            "branch": r["branch"],
            "expected_parent_sha": r["expected_parent_sha"],
            "expected_tree_oid": r["expected_tree_oid"],
            "job_id": r["job_id"],
        }
        arm = self._post(f"/api/tasks/{task_id}/commit-arm", {"token": token, "action_id": "arm-full-1"})
        self.assertEqual(arm.status_code, 200, arm.text)
        self.assertEqual(arm.json()["result"]["gate"]["scope"], "OWNER_COMMIT", arm.text)
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "-c",
                "user.name=Synthetic Owner",
                "-c",
                "user.email=owner@example.invalid",
                "commit",
                "--allow-empty",
                "-m",
                "Synthetic owner commit",
                "-m",
                f"Workflow-Job: {r['job_id']}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        verify1 = self._post(f"/api/tasks/{task_id}/commit-verify")
        self.assertEqual(verify1.status_code, 200, verify1.text)
        self.assertTrue(verify1.json().get("verified"), verify1.text)
        rec = self._post(f"/api/tasks/{task_id}/commit-record", {"action_id": "commit-full-1"})
        self.assertEqual(rec.status_code, 200, rec.text)
        self.assertTrue(rec.json().get("run"))
        self.assertTrue(_wait_for(lambda: self._status(task_id)["state"] == "COMPLETED"))
        final = self._status(task_id)
        fv = (final.get("last_result") or {}).get("view") or {}
        self.assertTrue(fv.get("committed"), final)
        events = self._launch_events()
        self.assertEqual(len(events), 4, events)
        self.assertEqual(len({e["threadId"] for e in events}), 4)
        return

    def test_13_stop_request_does_not_resolve_or_permit_deletion(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("unreg")
        dead = subprocess.Popen(["/bin/true"])
        dead.wait(timeout=5)
        now = "2026-11-15T00:00:00Z"
        conn = self.registry_mod.TaskRegistry()._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO run_state (task_id, state, desired, generation, "
                "owner_instance_id, owner_pid, owner_start_time, pass_count, last_pass_index, "
                "last_result_json, last_error, pause_reason, created_utc, updated_utc) "
                "VALUES (?,?,?,?,?,?,?,1,NULL,NULL,NULL,NULL,?,?)",
                (task_id, "RUNNING", "RUN", 1, "inst-dead", dead.pid, 1, now, now),
            )
            conn.execute(
                "INSERT OR REPLACE INTO run_passes (task_id, generation, pass_index, "
                "action_id, state, result_json, error, started_utc, updated_utc) "
                "VALUES (?,1,0,?,'IN_FLIGHT',NULL,NULL,?,?)",
                (task_id, f"coord-{task_id}-1-0", now, now),
            )
        conn.close()
        self.client.portal.call(self.appmod.run_coordinator.recover)
        parked = self._status(task_id)
        self.assertEqual(parked["state"], "RECONCILIATION_REQUIRED", parked)
        self.assertEqual(parked["pause_reason"], "pass_outcome_unknown", parked)
        delhdr = {"origin": "https://127.0.0.1:8080", "x-csrf-token": self.csrf}
        r = self.client.delete(f"/api/tasks/{task_id}", headers=delhdr)
        self.assertEqual(r.status_code, 409, r.text)
        stop = self._post(f"/api/tasks/{task_id}/run-stop")
        self.assertEqual(stop.status_code, 200, stop.text)
        after = self._status(task_id)
        self.assertEqual(after["state"], "RECONCILIATION_REQUIRED", after)
        self.assertTrue(after["stop_requested"])
        self.assertIn(
            "stop_requested",
            [e["event"] for e in self.client.get(f"/api/tasks/{task_id}/run-status").json()["events"]],
        )
        r2 = self.client.delete(f"/api/tasks/{task_id}", headers=delhdr)
        self.assertEqual(r2.status_code, 409, r2.text)
        bad = self._post(f"/api/tasks/{task_id}/run-abandon", {"acknowledge": "ok"})
        self.assertEqual(bad.status_code, 400, bad.text)
        good = self._post(f"/api/tasks/{task_id}/run-abandon", {"acknowledge": "remote state unknown"})
        self.assertEqual(good.status_code, 200, good.text)
        abandoned = self._status(task_id)
        self.assertEqual(abandoned["state"], "ABANDONED")
        self.assertEqual(abandoned["remote_state"], "unknown")
        r3 = self.client.delete(f"/api/tasks/{task_id}", headers=delhdr)
        self.assertEqual(r3.status_code, 409, r3.text)
        conn = self.registry_mod.TaskRegistry()._get_connection()
        n = conn.execute("SELECT COUNT(*) FROM run_passes WHERE task_id=?", (task_id,)).fetchone()[0]
        conn.close()
        self.assertEqual(n, 1, "pass evidence must survive stop request and abandonment")

    def _to_commit_gate(self, name):
        root, job_id, task_id = self._make_task(name)
        r = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": f"gate-{name}-1"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        self.assertEqual(self._post(f"/api/tasks/{task_id}/create-review", {}).status_code, 200)
        self.assertEqual(self._post(f"/api/tasks/{task_id}/approve-plan", {}).status_code, 200)
        r2 = self._post(f"/api/tasks/{task_id}/run-start", {"action_id": f"gate-{name}-2"})
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertTrue(_wait_for(lambda: self._status(task_id)["terminal"]))
        run = self._status(task_id)
        view = (run.get("last_result") or {}).get("view") or {}
        self.assertEqual(view.get("status"), "VERIFIED_FOR_RELEASE", run)
        self.assertEqual(view.get("gate", {}).get("scope"), "COMMIT", run)
        return root, job_id, task_id, view

    def _commit_token(self, task_id, req, branch=None, parent=None, tree=None):
        import uuid as _uuid

        return {
            "schema_version": 1,
            "token_id": f"tok-{_uuid.uuid4().hex[:12]}",
            "work_item": "pilot-loop",
            "gate_id": req["gate_id"],
            "issuer": "synthetic-owner",
            "issued_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "ISSUED",
            "scope": "COMMIT",
            "candidate_id": req["candidate_id"],
            "manifest_hash": req["manifest_hash"],
            "repository_id": req["repository_id"],
            "branch": branch or req["branch"],
            "expected_parent_sha": parent or req["expected_parent_sha"],
            "expected_tree_oid": tree or req["expected_tree_oid"],
            "job_id": req["job_id"],
        }

    def _git(self, root, *args):
        return subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "-c",
                "user.name=Synthetic Owner",
                "-c",
                "user.email=owner@example.invalid",
                *args,
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def test_14_direct_run_refused_in_conflict_states(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("direct")
        now = "2026-11-15T00:00:00Z"
        conn = self.registry_mod.TaskRegistry()._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO run_state (task_id, state, desired, generation, "
                "owner_instance_id, owner_pid, owner_start_time, pass_count, last_pass_index, "
                "last_result_json, last_error, pause_reason, created_utc, updated_utc) "
                "VALUES (?,?,?,?,?,?,?,0,NULL,NULL,NULL,NULL,?,?)",
                (task_id, "RECONCILIATION_REQUIRED", "STOP", 1, "inst-x", 1, 1, now, now),
            )
        conn.close()
        r = self._post(f"/api/tasks/{task_id}/run", {"action_id": "direct-1"})
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("RECONCILIATION_REQUIRED", r.text)
        conn = self.registry_mod.TaskRegistry()._get_connection()
        with conn:
            conn.execute("UPDATE run_state SET state='ABANDONED' WHERE task_id=?", (task_id,))
        conn.close()
        r2 = self._post(f"/api/tasks/{task_id}/run", {"action_id": "direct-2"})
        self.assertEqual(r2.status_code, 409, r2.text)
        self.assertIn("ABANDONED", r2.text)
        self.assertEqual(len(self._launch_events()), 0)

    def test_15_resolve_is_collect_only(self):
        self._reset_services()
        root, job_id, task_id = self._make_task("collect")
        now = "2026-11-15T00:00:00Z"
        conn = self.registry_mod.TaskRegistry()._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO run_state (task_id, state, desired, generation, "
                "owner_instance_id, owner_pid, owner_start_time, pass_count, last_pass_index, "
                "last_result_json, last_error, pause_reason, created_utc, updated_utc) "
                "VALUES (?,?,?,?,?,?,?,0,NULL,NULL,NULL,NULL,?,?)",
                (task_id, "RECONCILIATION_REQUIRED", "RUN", 1, "inst-x", 1, 1, now, now),
            )
        conn.close()
        # The prepared job is CREATED and ready; collect-only must not dispatch it.
        conn = sqlite3.connect(str(root / "orchestrator/var/checkpoints.db"))
        before = dict(conn.execute("select job_id, status from workflow_jobs").fetchall())
        conn.close()
        self.assertIn("CREATED", before.values())
        res = self._post(f"/api/tasks/{task_id}/run-resolve", {})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(len(self._launch_events()), 0, "collect must not dispatch")
        conn = sqlite3.connect(str(root / "orchestrator/var/checkpoints.db"))
        after = dict(conn.execute("select job_id, status from workflow_jobs").fetchall())
        conn.close()
        self.assertEqual(after, before, "collect must not create or dispatch jobs")
        run = self._status(task_id)
        self.assertEqual(run["state"], "RECONCILIATION_REQUIRED", run)
        self.assertIn(run["pause_reason"], ("no_correlated_job", "still_uncertain"), run)

    def test_16_commit_handoff_error_paths(self):
        self._reset_services()
        root, job_id, task_id, view = self._to_commit_gate("handoff")
        req = self.client.get(f"/api/tasks/{task_id}/commit-requirements").json()
        r = req["requirements"]
        # Invalid token schema and wrong bindings are rejected before any change.
        bad = self._post(
            f"/api/tasks/{task_id}/commit-arm", {"token": {"scope": "PLAN"}, "action_id": "arm-bad"}
        )
        self.assertEqual(bad.status_code, 400, bad.text)
        wrong_branch = self._commit_token(task_id, r, branch="other")
        bad2 = self._post(
            f"/api/tasks/{task_id}/commit-arm", {"token": wrong_branch, "action_id": "arm-branch"}
        )
        self.assertEqual(bad2.status_code, 400, bad2.text)
        token = self._commit_token(task_id, r)
        arm = self._post(f"/api/tasks/{task_id}/commit-arm", {"token": token, "action_id": "arm-ok"})
        self.assertEqual(arm.status_code, 200, arm.text)
        self.assertEqual(arm.json()["result"]["gate"]["scope"], "OWNER_COMMIT")
        # Replay is idempotent; a different token with the same id is a conflict.
        replay = self._post(f"/api/tasks/{task_id}/commit-arm", {"token": token, "action_id": "arm-ok"})
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertTrue(replay.json().get("replayed"))
        other = self._post(
            f"/api/tasks/{task_id}/commit-arm",
            {"token": self._commit_token(task_id, r), "action_id": "arm-ok"},
        )
        self.assertEqual(other.status_code, 409, other.text)
        # Wrong trailer is not a valid owner commit.
        self._git(root, "commit", "--allow-empty", "-m", "Wrong commit", "-m", "Workflow-Job: job-wrong")
        v0 = self._post(f"/api/tasks/{task_id}/commit-verify")
        self.assertFalse(v0.json().get("verified"), v0.text)
        rec0 = self._post(f"/api/tasks/{task_id}/commit-record", {"action_id": "record-wrong"})
        self.assertEqual(rec0.status_code, 400, rec0.text)
        # Reset, make the correct commit, then move HEAD again before recording.
        self._git(root, "reset", "--hard", r["expected_parent_sha"])
        self._git(root, "commit", "--allow-empty", "-m", "Owner commit", "-m", f"Workflow-Job: {r['job_id']}")
        first = self._git(root, "rev-parse", "HEAD")
        self._git(root, "commit", "--allow-empty", "-m", "Concurrent move")
        rec1 = self._post(f"/api/tasks/{task_id}/commit-record", {"action_id": "record-moved"})
        self.assertEqual(rec1.status_code, 400, rec1.text)
        # Restore the expected commit and record it.
        self._git(root, "reset", "--hard", first)
        v1 = self._post(f"/api/tasks/{task_id}/commit-verify")
        self.assertTrue(v1.json().get("verified"), v1.text)
        rec2 = self._post(f"/api/tasks/{task_id}/commit-record", {"action_id": "record-ok"})
        self.assertEqual(rec2.status_code, 200, rec2.text)
        self.assertTrue(_wait_for(lambda: self._status(task_id)["state"] == "COMPLETED"))
        final = self._status(task_id)
        self.assertTrue(((final.get("last_result") or {}).get("view") or {}).get("committed"))

    def _children(self):
        out = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                cmd = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode()
                stat = (entry / "stat").read_text()
                ppid = int(stat.rsplit(")", 1)[1].split()[1])
            except (OSError, ValueError, IndexError):
                continue
            if ppid == os.getpid() and "orchestrator.dashboard_api" in cmd:
                out.append(int(entry.name))
        return out


if __name__ == "__main__":
    unittest.main()
