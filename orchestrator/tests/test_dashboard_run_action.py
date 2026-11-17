"""Authenticated dashboard run action (ASGI) with a synthetic engine/transport.

Test-only seam: `dashboard.app.run_action` is replaced with an in-process call to
`orchestrator.dashboard_api.execute_action(..., engine_factory=...)`; the
endpoint, session auth, CSRF middleware, canonical 4-tuple fence, action-id
dedup and the engine dispatch gate are the real ones. The managed supervisor
bridge and MCP simulator run as separate processes inside the no-network harness.
The fixture uses the same UID and a synthetic-only builder; it does not test
production identity separation or real editing.
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

from t3_supervisor_client import SupervisorLauncher  # noqa: E402

MODEL = "opencode/deepseek-v4.1-flash-free"


class SyntheticWorkflowLauncher(SupervisorLauncher):
    allow_builder_for_tests = True


def _wait_for(pred, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.05)
    return False


class DashboardRunActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="dash-run-")
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
        os.environ["ENGINE_NATIVE_DISPATCH"] = "allow-native-host-access"
        os.environ.pop("ENGINE_T3_BACKEND", None)
        try:
            import dashboard.app  # noqa: F401
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
        # synthetic account is now authenticated and password-set
        cls._wire_engine()
        cls._prepare_task()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.client.__exit__(None, None, None)
        finally:
            for p in getattr(cls, "_procs", []):
                try:
                    p.terminate(); p.wait(timeout=5)
                except Exception:
                    try: p.kill()
                    except Exception: pass
            cls._tmp.cleanup()

    # -- auth ----------------------------------------------------------- #
    @classmethod
    def _csrf(cls):
        cls.client.get("/api/auth/csrf-token")
        return cls.client.cookies.get("dashboard_csrf") or ""

    @classmethod
    def _login(cls):
        from dashboard import auth as auth_mod

        creds = auth_mod.auth_store.credentials_file_path
        if not creds.is_file() and getattr(cls, "user", None):
            user, pw = cls.user, cls.password
        else:
            if not creds.is_file():
                auth_mod.create_initial_credentials_file(file_path=creds)
            user = pw = None
            for line in creds.read_text().splitlines():
                if line.startswith("Username: "): user = line.split(": ", 1)[1]
                if line.startswith("Password: "): pw = line.split(": ", 1)[1]
        cls.user = user
        tok = cls._csrf()
        r = cls.client.post("/api/auth/login", json={"username": user, "password": pw},
                            headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": tok})
        assert r.status_code == 200, r.text
        cls.csrf = r.json()["csrf_token"]
        if auth_mod.auth_store.is_initial_user(user):
            r2 = cls.client.post("/api/auth/setup-password",
                                 json={"current_password": pw, "new_password": "NewPermanentPass123!"},
                                 headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": cls.csrf})
            assert r2.status_code == 200, r2.text
            cls.password = "NewPermanentPass123!"
        else:
            cls.password = pw

    # -- synthetic engine + supervisor --------------------------------- #
    @classmethod
    def _wire_engine(cls):
        import orchestrator.dashboard_api as oda
        from engine import Engine
        from t3_supervisor_client import SupervisorLauncher
        from dashboard import subprocess_client

        cls.sim_state = {"launches": []}
        cls._start_sim(cls.dir / "launches.jsonl")
        cls._start_sup()
        sock = cls.dir / "sup.sock"
        token = (cls.dir / "peer.token").read_text().strip()

        async def fake_run_action(worktree, action, payload=None, **kw):
            def factory(root):
                return Engine(root, launcher=SyntheticWorkflowLauncher(
                    root, sock, token, allowed_models=[MODEL]))
            try:
                return oda.execute_action(Path(worktree), action, payload or {},
                                          engine_factory=factory)
            except Exception as exc:
                raise subprocess_client.SubprocessClientError(str(exc)) from None

        from unittest import mock
        cls._patch = mock.patch.object(cls.appmod, "run_action", fake_run_action)
        cls._patch.start()

    @classmethod
    def _start_sim(cls, events, fail=None):
        token = "synthetic-mcp-token-0123456789"
        (cls.dir / "mcp.token").write_text(token)
        os.chmod(cls.dir / "mcp.token", 0o600)
        cls.mcp_token = token
        cls.events = events
        args = [sys.executable, str(TESTS / "_mcp_sim_server.py"), "--token", token,
                "--events", str(events)] + (["--fail", fail] if fail else [])
        cls.sim = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, cwd=str(ORCH))
        cls._procs = getattr(cls, "_procs", []) + [cls.sim]
        cls.url = json.loads(cls.sim.stdout.readline())["url"]

    @classmethod
    def _start_sup(cls):
        token = "synthetic-peer-token-0123456789"
        (cls.dir / "peer.token").write_text(token)
        os.chmod(cls.dir / "peer.token", 0o600)
        cls.sup = subprocess.Popen(
            [sys.executable, str(TESTS / "_synthetic_managed_supervisor_server.py"),
             "--socket", str(cls.dir / "sup.sock"),
             "--state", str(cls.dir / "state.json"),
             "--token-file", str(cls.dir / "peer.token"),
             "--base-url", cls.url,
             "--mcp-token-file", str(cls.dir / "mcp.token"),
             "--model", MODEL, "--allowed-model", MODEL],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ORCH))
        cls._procs = getattr(cls, "_procs", []) + [cls.sup]
        assert _wait_for(lambda: (cls.dir / "sup.sock").exists())
        assert cls.sup.stdout.readline()

    @classmethod
    def _launch_count(cls, job_id=None):
        if not cls.events.exists():
            return 0
        lines = [json.loads(l) for l in cls.events.read_text().splitlines() if l.strip()]
        if job_id is not None:
            return len([l for l in lines if f"engine job {job_id}" in (l.get("title") or "")])
        return len(lines)

    # -- engine fixture + task row -------------------------------------- #
    @classmethod
    def _prepare_task(cls):
        root = cls.dir / "root"
        root.mkdir()
        from candidates import git
        from core import bytes_hash
        from engine import Engine
        git(root, "init", "-b", "pilot")
        git(root, "config", "user.name", "Synthetic Test")
        git(root, "config", "user.email", "synthetic@example.invalid")
        shutil.copytree(ORCH.parent / "docs/ai/roles", root / "docs/ai/roles")
        (root / "plan.md").write_text("Synthetic dashboard workflow plan\n")
        (root / "app.py").write_text("VALUE = 1\n")
        (root / ".gitignore").write_text("orchestrator/var/\n")
        evidence = root / "docs/ai/work-items/pilot-loop/evidence"
        evidence.mkdir(parents=True)
        (evidence / "phase-0-capabilities.json").write_text(
            json.dumps({"phase_exit": "PASSED_WITH_OWNER_DIRECTIVE"}))
        git(root, "add", ".")
        git(root, "-c", "core.hooksPath=/dev/null", "commit", "-m", "synthetic dashboard fixture")
        base = git(root, "rev-parse", "HEAD").decode().strip()
        cfg = {
            "root": str(root), "work_item": "pilot-loop", "stages": ["1"],
            "base_commit": base, "branch": "pilot", "plan_path": "plan.md",
            "plan_revision_hash": bytes_hash((root / "plan.md").read_bytes()),
            "scope": {"allowed_paths": ["app.py"], "requirements": ["R1"],
                      "validation_commands": [["/usr/bin/python3", "-c", "pass"]]},
            "roles": {role: {"tool": "synthetic", "binary": "synthetic", "model": MODEL,
                             "prompt_sha256": bytes_hash((root / "docs/ai/roles" /
                                 ((role if role in ("architect", "reviewer", "builder", "verifier") else "ai-reviewer") + ".md")).read_bytes())}
                      for role in ("architect", "reviewer", "builder", "verifier", "ai-a1", "ai-a2", "ai-a3")},
        }
        seed = Engine(root, launcher=SyntheticWorkflowLauncher(
            root, cls.dir / "sup.sock", (cls.dir / "peer.token").read_text().strip(),
            allowed_models=[MODEL]))
        try:
            seed.initialize(cfg)
        finally:
            seed.close()
        db = root / "orchestrator/var/checkpoints.db"
        # create the job through the native gate (refusal leaves it CREATED)
        from cli import make_engine
        from core import WorkflowError
        os.environ.pop("ENGINE_NATIVE_DISPATCH", None)
        os.environ.pop("ENGINE_T3_BACKEND", None)
        try:
            make_engine(root).run()
        except WorkflowError as exc:
            refusal = str(exc)
        else:
            raise AssertionError("native dispatch gate did not refuse")
        conn = sqlite3.connect(str(db))
        row = conn.execute("select job_id from workflow_jobs").fetchone()
        conn.close()
        if row is None:
            raise AssertionError(f"fixture did not create a job; native refusal: {refusal}")
        cls.job_id = row[0]
        cls.root = root
        reg = cls.registry_mod.TaskRegistry()
        conn = reg._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO registered_tasks (task_id, work_item, worktree_path, "
                "task_branch, registered_utc, cached_status, cached_stage) VALUES (?,?,?,?,?,?,?)",
                ("task-run-1", "pilot-loop", str(root), "pilot",
                 "2026-11-15T00:00:00Z", "DRAFT", "1"),
            )
        conn.close()

    def setUp(self):
        # Each endpoint test starts from an idle run row; the direct-run lease
        # intentionally refuses a task left in reconciliation by another test.
        conn = self.registry_mod.TaskRegistry()._get_connection()
        with conn:
            conn.execute("DELETE FROM run_state")
            conn.execute("DELETE FROM run_passes")
        conn.close()

    def _post_run(self, payload=None, csrf=None, task="task-run-1"):
        headers = {"origin": "https://127.0.0.1:8080", "x-csrf-token": csrf or self.csrf}
        return self.client.post(f"/api/tasks/{task}/run", json=payload or {}, headers=headers)

    # -- tests ---------------------------------------------------------- #
    def test_unauthenticated_is_401_and_no_dispatch(self):
        before = self._launch_count(self.job_id)
        self.client.cookies.clear()
        csrf = self._csrf()
        r = self._post_run({"action_id": "act-unauth"}, csrf=csrf)
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self._launch_count(self.job_id), before)
        self._login()

    def test_forged_csrf_is_403_and_no_dispatch(self):
        before = self._launch_count(self.job_id)
        r = self._post_run({"action_id": "act-forged"}, csrf="forged-token")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self._launch_count(self.job_id), before)

    def test_authenticated_run_success_and_duplicate(self):
        before = self._launch_count(self.job_id)
        r = self._post_run({"action_id": "act-run-ok"})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertIn("result", body)
        # engine may need a collect pass; use a new action id for a second pass
        for _ in range(3):
            conn = sqlite3.connect(str(self.root / "orchestrator/var/checkpoints.db"))
            status = conn.execute("select status from workflow_jobs where job_id=?", (self.job_id,)).fetchone()[0]
            conn.close()
            if status == "ACCEPTED":
                break
            r = self._post_run({"action_id": f"act-run-collect-{time.time_ns()}"})
            self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(status, "ACCEPTED")
        self.assertEqual(self._launch_count(self.job_id), before + 1, "exactly one launch for the job")
        # duplicate with the same action id returns the cached result, no new launch
        launches = self._launch_count(self.job_id)
        r2 = self._post_run({"action_id": "act-run-ok"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["result"], body["result"])
        self.assertEqual(self._launch_count(self.job_id), launches)

    def test_managed_route_reaches_real_socket_checks_and_refuses_unverified_identity(self):
        """Exercise dashboard/API managed route without crossing the UID boundary.

        The fixture supervisor runs under this test process UID. The dispatch
        config deliberately expects a different UID, so the real socket check
        must reject it before token loading, Engine construction, or launch.
        """
        import orchestrator.dashboard_api as oda
        from dashboard import subprocess_client

        config_path = self.dir / "managed-dispatch.json"
        config_path.write_text(json.dumps({
            "schema": "dashboard-managed-supervisor-dispatch/v1",
            "dispatch_enabled": True,
            "socket_path": str(self.dir / "sup.sock"),
            "token_file": str(self.dir / "peer.token"),
            "expected_uid": os.geteuid() + 1,
            "socket_group_gid": os.getegid(),
            "expected_cgroup": "/user.slice/test-managed-supervisor.service",
            "allowed_models": [MODEL],
        }))
        config_path.chmod(0o600)
        before = self._launch_count(self.job_id)

        async def managed_route(worktree, action, payload=None, **_kwargs):
            try:
                return oda.execute_action(
                    Path(worktree), action, payload or {},
                    managed_dispatch_config=str(config_path),
                    managed_dispatch_enabled=True,
                )
            except Exception as exc:
                raise subprocess_client.SubprocessClientError(str(exc)) from None

        original = self.appmod.run_action
        self.appmod.run_action = managed_route
        try:
            response = self._post_run({"action_id": "act-managed-identity-denied"})
        finally:
            self.appmod.run_action = original

        self.assertEqual(response.status_code, 500, response.text)
        self.assertIn("socket owner/group mismatch", response.text)
        self.assertEqual(self._launch_count(self.job_id), before)

    def test_lost_reply_error_is_clear_and_no_dispatch(self):
        """The endpoint maps engine/supervisor reconciliation errors to a clear 500.

        The underlying lost-reply/restart behaviour (uncertain → reconciliation,
        no re-send) is proven at the supervisor/engine seam in
        test_t3_supervisor.py; here we assert the HTTP mapping and zero dispatch.
        """
        from dashboard import subprocess_client

        original = self.appmod.run_action
        calls = {"n": 0}

        async def failing(*args, **kwargs):
            calls["n"] += 1
            raise subprocess_client.SubprocessClientError(
                "RECONCILIATION_REQUIRED: synthetic lost reply; no re-send")

        self.appmod.run_action = failing
        try:
            before = self._launch_count(self.job_id)
            r = self._post_run({"action_id": "act-lost"})
            self.assertEqual(r.status_code, 500)
            self.assertIn("RECONCILIATION_REQUIRED", r.text)
            self.assertEqual(self._launch_count(self.job_id), before)
            self.assertEqual(calls["n"], 1)
        finally:
            self.appmod.run_action = original

    def test_stale_action_id_with_different_payload_is_409(self):
        self._post_run({"action_id": "act-stale"})
        r = self._post_run({"action_id": "act-stale", "different": True})
        self.assertEqual(r.status_code, 409)
        self.assertIn("different request payload", r.text)


class RunTerminalContractTests(unittest.TestCase):
    """Pure terminal contract used by the UI to stop its bounded loop."""

    def setUp(self):
        sys.path.insert(0, str(ORCH))
        import dashboard_api

        self.fn = dashboard_api.run_terminal

    def test_paused_view_is_terminal(self):
        self.assertTrue(self.fn({"status": "PAUSED", "active_jobs": []}, {}))

    def test_gate_is_terminal(self):
        self.assertTrue(self.fn({"status": "DRAFT", "gate": {"reason": "x"}, "active_jobs": []}, {}))

    def test_no_jobs_is_terminal(self):
        self.assertTrue(self.fn({"status": "DRAFT", "active_jobs": []}, {}))

    def test_dispatchable_job_is_not_terminal(self):
        self.assertFalse(self.fn({"status": "BUILD_IN_PROGRESS", "active_jobs": ["j1"]}, {"j1": "CREATED"}))

    def test_in_flight_job_is_not_terminal(self):
        self.assertFalse(self.fn({"status": "BUILD_IN_PROGRESS", "active_jobs": ["j1"]}, {"j1": "RUNNING"}))

    def test_accepted_job_is_terminal(self):
        self.assertTrue(self.fn({"status": "BUILD_IN_PROGRESS", "active_jobs": ["j1"]}, {"j1": "ACCEPTED"}))

    def test_mixed_statuses_are_not_terminal(self):
        view = {"status": "BUILD_IN_PROGRESS", "active_jobs": ["j1", "j2"]}
        self.assertFalse(self.fn(view, {"j1": "ACCEPTED", "j2": "CREATED"}))

    def test_reconciliation_job_is_terminal(self):
        self.assertTrue(self.fn({"status": "PAUSED", "active_jobs": ["j1"]}, {"j1": "RECONCILIATION_REQUIRED"}))


if __name__ == "__main__":
    unittest.main()
