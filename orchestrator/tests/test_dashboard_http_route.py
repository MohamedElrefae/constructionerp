"""Dashboard HTTP route tests (ASGI), test-only.

Exercises the real Starlette app: Host validation, session authentication and
the Origin/CSRF middleware on a mutating route. No engine dispatch, no site, no
network. The 4-tuple action fence lives in the orchestrator (`execute_action`)
and is covered separately.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DASHBOARD_TEST_MODE", "1")


def _prepare_env(root: Path):
    root.chmod(0o700)
    bench = root / "bench"
    (bench / "apps").mkdir(parents=True, exist_ok=True)
    (bench / "sites").mkdir(parents=True, exist_ok=True)
    dash_var = root / "dashboard" / "var"
    dash_var.mkdir(parents=True, exist_ok=True)
    root.joinpath("dashboard").chmod(0o700)
    dash_var.chmod(0o700)
    os.environ["FRAPPE_BENCH_ROOT"] = str(bench)
    os.environ["DASHBOARD_TEST_ROOT"] = str(root)


class DashboardHttpRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="dash-http-")
        cls.root = Path(cls._tmp.name)
        _prepare_env(cls.root)
        try:
            import dashboard.app  # noqa: F401
        except Exception as exc:  # missing deps/package: skip, never fail silently
            raise unittest.SkipTest(f"dashboard package unavailable: {type(exc).__name__}: {exc}")
        from starlette.testclient import TestClient
        import importlib
        import dashboard.config
        import dashboard.app

        importlib.reload(dashboard.config)
        importlib.reload(dashboard.app)
        cls.client = TestClient(dashboard.app.app, base_url="https://127.0.0.1:8080")
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.client.__exit__(None, None, None)
        finally:
            cls._tmp.cleanup()

    def test_bad_host_is_rejected(self):
        r = self.client.get("/api/tasks", headers={"host": "evil.example"})
        self.assertEqual(r.status_code, 400)

    def test_unauthenticated_get_is_401(self):
        r = self.client.get("/api/tasks")
        self.assertEqual(r.status_code, 401)

    def test_supervisor_health_requires_a_session(self):
        from starlette.testclient import TestClient
        import dashboard.app

        client = TestClient(dashboard.app.app, base_url="https://127.0.0.1:8080")
        self.assertEqual(client.get("/api/supervisor/health").status_code, 401)

    def _csrf(self):
        self.client.get("/api/auth/csrf-token")
        token = self.client.cookies.get("dashboard_csrf")
        return {"origin": "https://127.0.0.1:8080", "x-csrf-token": token or ""}

    def test_unauthenticated_mutation_is_401(self):
        r = self.client.post(
            "/api/tasks/bootstrap",
            json={"work_item": "pilot-loop", "user_brief": "x"},
            headers=self._csrf(),
        )
        self.assertEqual(r.status_code, 401)

    def test_mutation_without_origin_is_403(self):
        r = self.client.post("/api/tasks/bootstrap", json={"work_item": "x", "user_brief": "y"})
        self.assertEqual(r.status_code, 403)
        self.assertIn("Origin", r.text)

    def test_wrong_password_is_401(self):
        r = self.client.post(
            "/api/auth/login",
            json={"username": "engineer", "password": "wrong-password"},
            headers=self._csrf(),
        )
        self.assertEqual(r.status_code, 401)

    def test_forged_session_cookie_is_401(self):
        self.client.cookies.set("dashboard_session", "forged-session-token")
        try:
            r = self.client.get("/api/tasks")
        finally:
            self.client.cookies.clear()
        self.assertEqual(r.status_code, 401)

    def test_authenticated_mutation_requires_csrf(self):
        from dashboard import auth as auth_mod

        creds = auth_mod.auth_store.credentials_file_path
        if not creds.is_file():
            auth_mod.create_initial_credentials_file(file_path=creds)
        username, password = None, None
        for line in creds.read_text().splitlines():
            if line.startswith("Username: "):
                username = line.split(": ", 1)[1]
            if line.startswith("Password: "):
                password = line.split(": ", 1)[1]
        self.assertTrue(username and password)
        r = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers=self._csrf(),
        )
        self.assertEqual(r.status_code, 200, r.text)
        csrf = r.json().get("csrf_token")
        # authenticated, but no CSRF header: middleware must refuse
        r2 = self.client.post(
            "/api/tasks/bootstrap",
            json={"work_item": "pilot-loop", "user_brief": "x"},
            headers={"origin": "https://127.0.0.1:8080"},
        )
        self.assertEqual(r2.status_code, 403)
        self.assertIn("CSRF", r2.text)
        # authenticated + CSRF, but invalid body: proves the request reaches the
        # handler without dispatching anything
        r3 = self.client.post(
            "/api/tasks/bootstrap",
            json={"work_item": "", "user_brief": ""},
            headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": csrf or ""},
        )
        # complete the initial password setup, then the authenticated request
        # reaches the handler (empty body -> 400) without dispatching anything
        r_setup = self.client.post(
            "/api/auth/setup-password",
            json={"current_password": password,
                  "new_password": "NewPermanentPass123!"},
            headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": csrf or ""},
        )
        self.assertEqual(r_setup.status_code, 200, r_setup.text)
        r3 = self.client.post(
            "/api/tasks/bootstrap",
            json={"work_item": "", "user_brief": ""},
            headers={"origin": "https://127.0.0.1:8080", "x-csrf-token": csrf or ""},
        )
        self.assertEqual(r3.status_code, 400)
        with patch("dashboard.app.query_supervisor_health", new=AsyncMock(return_value={"read_only": True})):
            health = self.client.get("/api/supervisor/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["supervisor"]["read_only"])


if __name__ == "__main__":
    unittest.main()
