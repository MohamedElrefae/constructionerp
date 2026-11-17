"""Engine→T3 integration seam, test-only.

The production T3 backend is refused unconditionally. These tests inject a
synthetic in-process transport through the real entry points
(`cli.make_engine(..., transport_factory=...)` and
`dashboard_api.execute_action(..., engine_factory=...)`) and exercise:
  - synthetic success (dispatch → send → collect → ACCEPTED),
  - lost reply → RECONCILIATION_REQUIRED, restart never re-sends,
  - production refusal even with forged markers / env / user namespace.
No network, no real T3, no provider.
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import dashboard_api
from cli import make_engine
from core import WorkflowError
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from _t3_test_transport import make_synthetic_factory

BASE_FIXTURE = Path(os.environ.get("T3_SEAM_BASE_FIXTURE", "/opt/base-fixture"))
OLD_ROOT = os.environ.get("T3_SEAM_OLD_ROOT", "/var/tmp/guard-case-base-20261115")


def _prepare_root(tmp: Path) -> Path:
    root = tmp / "root"
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
        if p.is_file() and p.suffix in (".json", ".md", ".txt", ".jsonl") and p.stat().st_size < 2_000_000:
            try:
                text = p.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            if OLD_ROOT in text:
                p.write_text(text.replace(OLD_ROOT, str(root)))
    return root


def _job_rows(root: Path):
    conn = sqlite3.connect(str(root / "orchestrator/var/checkpoints.db"))
    try:
        return conn.execute("select job_id, status from workflow_jobs").fetchall()
    finally:
        conn.close()


def _prepare_job(root: Path) -> dict:
    """One native pass creates the job (prepare) and is refused by the gate.

    Returns the job spec envelope so the synthetic transport can emit a
    schema-valid wire result.
    """
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ENGINE_NATIVE_DISPATCH", None)
        os.environ.pop("ENGINE_T3_BACKEND", None)
        with unittest.TestCase().assertRaises(WorkflowError):
            make_engine(root).run()
    rows = _job_rows(root)
    assert rows, "prepare did not create a job"
    job_id = rows[0][0]
    spec = json.loads((root / "orchestrator/var/jobs" / job_id / "spec.json").read_text())
    return {"job_id": job_id, "spec": spec}


def _factory(mode: str, envelope: dict):
    from _t3_test_transport import SyntheticT3Client, SyntheticTransportFactory

    client = SyntheticT3Client(mode=mode)
    client.envelope = envelope
    return SyntheticTransportFactory(client), client


class T3SeamTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="t3-seam-")
        self.addCleanup(self._tmp.cleanup)
        if not BASE_FIXTURE.exists():
            self.skipTest(f"base fixture not available: {BASE_FIXTURE}")
        self.root = _prepare_root(Path(self._tmp.name))
        prepared = _prepare_job(self.root)
        self.job_id = prepared["job_id"]
        self.envelope = prepared["spec"]["envelope"]

    def _run_pass(self, factory):
        with mock.patch.dict(os.environ, {"ENGINE_T3_BACKEND": "t3"}, clear=False):
            return make_engine(self.root, transport_factory=factory, min_poll_interval_s=0).run()

    def _delegates_for_prepared_job(self, client) -> int:
        corr_path = self.root / "orchestrator/var/t3-correlation.json"
        if not corr_path.exists():
            return 0
        rec = json.loads(corr_path.read_text())["records"].get(self.job_id)
        if not rec:
            return 0
        crid = rec.get("client_request_id")
        return len([c for c in client.calls if c[0] == "delegate" and c[1] == crid])

    def test_synthetic_success(self):
        factory, client = _factory("ok", self.envelope)
        view = self._run_pass(factory)
        for _ in range(3):
            if dict(_job_rows(self.root))[self.job_id] == "ACCEPTED":
                break
            view = self._run_pass(factory)
        status = dict(_job_rows(self.root))[self.job_id]
        self.assertEqual(status, "ACCEPTED", view)
        self.assertEqual(self._delegates_for_prepared_job(client), 1)
        terminal = json.loads((self.root / "orchestrator/var/jobs" / self.job_id / "terminal.json").read_text())
        self.assertEqual(terminal["exit_code"], 0)
        ledger = json.loads((self.root / "orchestrator/var/t3-dispatch-ledger.json").read_text())
        rec = ledger["jobs"][self.job_id]
        self.assertEqual(rec["state"], "collected")

    def test_lost_reply_parks_and_restart_never_resends(self):
        factory, client = _factory("lost_reply", self.envelope)
        view = self._run_pass(factory)
        for _ in range(6):
            status = dict(_job_rows(self.root))[self.job_id]
            if status in ("ACCEPTED", "RECONCILIATION_REQUIRED"):
                break
            view = self._run_pass(factory)
        status = dict(_job_rows(self.root))[self.job_id]
        self.assertEqual(status, "RECONCILIATION_REQUIRED", view)
        if status == "RECONCILIATION_REQUIRED":
            self.assertIn("RECONCILIATION", (view.get("pause_reason") or ""))
        self.assertEqual(self._delegates_for_prepared_job(client), 1)
        # restart: a new engine over the same durable files must not re-send
        view2 = self._run_pass(factory)
        self.assertEqual(self._delegates_for_prepared_job(client), 1, view2)
        self.assertEqual(dict(_job_rows(self.root))[self.job_id], status)

    def test_production_backend_refused_even_with_forged_markers(self):
        var = self.root / "orchestrator/var"
        for name in ("t3-isolated-boundary.json", "t3-sealed-launch.json",
                     "sealed-launch-marker.json"):
            (var / name).write_text('{"armed": true, "netns": "forged"}')
        with mock.patch.dict(os.environ, {
            "ENGINE_T3_BACKEND": "t3",
            "ENGINE_T3_LAUNCH_AUTH": "true",
            "ENGINE_NATIVE_DISPATCH": "allow-native-host-access",
        }, clear=False):
            with self.assertRaises(WorkflowError) as ctx:
                make_engine(self.root).run()
        self.assertIn("refused unconditionally", str(ctx.exception))
        # dashboard production run path refuses too (no injection)
        with mock.patch.dict(os.environ, {"ENGINE_T3_BACKEND": "t3"}, clear=False):
            with self.assertRaises(WorkflowError):
                dashboard_api.execute_action(self.root, "run", {})

    def _dashboard_registry(self):
        """Sanctioned dashboard test seam: DASHBOARD_TEST_MODE + a 4-tuple fence row."""
        import sqlite3 as _sqlite3
        import stat as _stat

        base = Path(self._tmp.name) / "dashboard-registry"
        base.mkdir(parents=True)
        base.chmod(0o700)
        var = base / "var"
        var.mkdir()
        var.chmod(0o700)
        db = var / "registry.db"
        conn = _sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE action_log (action_id TEXT, fencing_token INTEGER, "
            "executor_instance_id TEXT, state TEXT, request_hash TEXT, created_utc TEXT)"
        )
        conn.execute(
            "INSERT INTO action_log VALUES (?,?,?,?,?,?)",
            ("act-t3-seam", 7, "executor-t3-seam", "EXECUTING", "", "2026-11-15T00:00:00Z"),
        )
        conn.commit()
        conn.close()
        db.chmod(0o600)
        return db

    def test_dashboard_entry_with_injected_transport(self):
        factory, client = _factory("ok", self.envelope)
        registry = self._dashboard_registry()
        payload = {
            "action_id": "act-t3-seam",
            "fencing_token": 7,
            "executor_instance_id": "executor-t3-seam",
        }
        env = {
            "ENGINE_T3_BACKEND": "t3",
            "DASHBOARD_TEST_MODE": "1",
            "DASHBOARD_REGISTRY_DB": str(registry),
        }
        with mock.patch.dict(os.environ, env, clear=False):
            view = dashboard_api.execute_action(
                self.root, "run", payload,
                engine_factory=lambda r: make_engine(r, transport_factory=factory, min_poll_interval_s=0),
            )
        for _ in range(3):
            if dict(_job_rows(self.root))[self.job_id] == "ACCEPTED":
                break
            with mock.patch.dict(os.environ, env, clear=False):
                view = dashboard_api.execute_action(
                    self.root, "run", payload,
                    engine_factory=lambda r: make_engine(r, transport_factory=factory, min_poll_interval_s=0),
                )
        self.assertEqual(dict(_job_rows(self.root))[self.job_id], "ACCEPTED", view)
        self.assertEqual(self._delegates_for_prepared_job(client), 1)


if __name__ == "__main__":
    unittest.main()

class ShippedPathSelectionTests(unittest.TestCase):
    """The shipped entry paths must not be able to select the test double."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="t3-ship-")
        self.addCleanup(self._tmp.cleanup)
        if not BASE_FIXTURE.exists():
            self.skipTest(f"base fixture not available: {BASE_FIXTURE}")
        self.root = _prepare_root(Path(self._tmp.name))
        self.registry = self._dashboard_registry()

    def _dashboard_registry(self):
        import sqlite3 as _sqlite3

        base = Path(self._tmp.name) / "dashboard-registry"
        base.mkdir(parents=True)
        base.chmod(0o700)
        var = base / "var"
        var.mkdir()
        var.chmod(0o700)
        db = var / "registry.db"
        conn = _sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE action_log (action_id TEXT, fencing_token INTEGER, "
            "executor_instance_id TEXT, state TEXT, request_hash TEXT, created_utc TEXT)"
        )
        conn.execute("INSERT INTO action_log VALUES (?,?,?,?,?,?)",
                     ("act-ship", 11, "executor-ship", "EXECUTING", "", "2026-11-15T00:00:00Z"))
        conn.commit()
        conn.close()
        db.chmod(0o600)
        return db

    def test_cli_cannot_select_fake_via_env(self):
        import cli
        import io
        from contextlib import redirect_stdout

        argv = ["cli.py", "--root", str(self.root), "run", "--once"]
        env = {
            "ENGINE_T3_BACKEND": "t3",
            "ENGINE_T3_TEST_TRANSPORT": "1",
            "ENGINE_T3_FAKE": "1",
            "ENGINE_T3_TRANSPORT": "tests._t3_test_transport",
            "ENGINE_NATIVE_DISPATCH": "allow-native-host-access",
        }
        buf = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(sys, "argv", argv):
            with redirect_stdout(buf):
                rc = cli.main()
        self.assertEqual(rc, 1)
        self.assertIn("refused unconditionally", buf.getvalue())

    def test_dashboard_payload_cannot_select_fake(self):
        payload = {
            "action_id": "act-ship",
            "fencing_token": 11,
            "executor_instance_id": "executor-ship",
            "engine_factory": "tests._t3_test_transport",
            "transport_factory": "tests._t3_test_transport",
        }
        env = {
            "ENGINE_T3_BACKEND": "t3",
            "DASHBOARD_TEST_MODE": "1",
            "DASHBOARD_REGISTRY_DB": str(self.registry),
        }
        with mock.patch.dict(os.environ, env, clear=False):
            with self.assertRaises(WorkflowError) as ctx:
                dashboard_api.execute_action(self.root, "run", payload)
        self.assertIn("refused unconditionally", str(ctx.exception))

    def test_config_cannot_select_fake(self):
        import sqlite3 as _sqlite3

        db = self.root / "orchestrator/var/checkpoints.db"
        conn = _sqlite3.connect(str(db))
        row = conn.execute("select value from workflow_meta where key='config'").fetchone()
        cfg = json.loads(row[0])
        cfg["transport_factory"] = "tests._t3_test_transport"
        cfg["engine_factory"] = "tests._t3_test_transport"
        conn.execute("update workflow_meta set value=? where key='config'", (json.dumps(cfg),))
        conn.commit()
        conn.close()
        with mock.patch.dict(os.environ, {"ENGINE_T3_BACKEND": "t3"}, clear=False):
            engine = make_engine(self.root)
            with self.assertRaises(WorkflowError) as ctx:
                engine.run()
        self.assertIn("refused unconditionally", str(ctx.exception))

    def test_read_only_works_with_t3_env(self):
        with mock.patch.dict(os.environ, {"ENGINE_T3_BACKEND": "t3"}, clear=False):
            view = make_engine(self.root).view()
        self.assertIn("status", view)

    def test_no_shipped_module_imports_test_double(self):
        shipped = Path(__file__).resolve().parents[1]
        offenders = []
        for p in shipped.rglob("*.py"):
            parts = set(p.parts)
            if "tests" in parts or "__pycache__" in parts:
                continue
            text = p.read_text(errors="ignore")
            if "_t3_test_transport" in text or "t3_test_transport" in text:
                offenders.append(str(p.relative_to(shipped)))
        self.assertEqual(offenders, [])

    def test_test_double_not_at_shipped_path(self):
        shipped = Path(__file__).resolve().parents[1]
        self.assertFalse((shipped / "t3_test_transport.py").exists())
        self.assertTrue((shipped / "tests/_t3_test_transport.py").exists())

class DashboardFenceTests(T3SeamTests):
    """Dashboard production fence: invalid/unauthorized input is refused."""

    def _env(self):
        return {"ENGINE_T3_BACKEND": "t3", "DASHBOARD_TEST_MODE": "1",
                "DASHBOARD_REGISTRY_DB": str(self._dashboard_registry())}

    def test_dashboard_missing_fence_parameters_refused(self):
        with mock.patch.dict(os.environ, self._env(), clear=False):
            with self.assertRaises(Exception) as ctx:
                dashboard_api.execute_action(self.root, "run", {})
        self.assertIn("Fencing parameters", str(ctx.exception))

    def test_dashboard_wrong_fence_token_refused(self):
        payload = {"action_id": "act-t3-seam", "fencing_token": 999,
                   "executor_instance_id": "executor-t3-seam"}
        with mock.patch.dict(os.environ, self._env(), clear=False):
            with self.assertRaises(Exception) as ctx:
                dashboard_api.execute_action(self.root, "run", payload)
        self.assertIn("Fencing validation failed", str(ctx.exception))

    def test_dashboard_lost_reply_parks(self):
        factory, client = _factory("lost_reply", self.envelope)
        payload = {"action_id": "act-t3-seam", "fencing_token": 7,
                   "executor_instance_id": "executor-t3-seam"}
        env = self._env()
        with mock.patch.dict(os.environ, env, clear=False):
            for _ in range(6):
                status = dict(_job_rows(self.root))[self.job_id]
                if status in ("RECONCILIATION_REQUIRED", "ACCEPTED"):
                    break
                dashboard_api.execute_action(
                    self.root, "run", payload,
                    engine_factory=lambda r: make_engine(r, transport_factory=factory, min_poll_interval_s=0),
                )
        self.assertEqual(dict(_job_rows(self.root))[self.job_id], "RECONCILIATION_REQUIRED")
        self.assertEqual(self._delegates_for_prepared_job(client), 1)

    def test_dashboard_restart_never_resends(self):
        factory, client = _factory("ok", self.envelope)
        payload = {"action_id": "act-t3-seam", "fencing_token": 7,
                   "executor_instance_id": "executor-t3-seam"}
        env = self._env()
        with mock.patch.dict(os.environ, env, clear=False):
            for _ in range(3):
                if dict(_job_rows(self.root))[self.job_id] == "ACCEPTED":
                    break
                dashboard_api.execute_action(
                    self.root, "run", payload,
                    engine_factory=lambda r: make_engine(r, transport_factory=factory, min_poll_interval_s=0),
                )
            before = self._delegates_for_prepared_job(client)
            dashboard_api.execute_action(
                self.root, "run", payload,
                engine_factory=lambda r: make_engine(r, transport_factory=factory, min_poll_interval_s=0),
            )
        self.assertEqual(self._delegates_for_prepared_job(client), before)
        self.assertEqual(before, 1)
