"""Collect-only reconciliation is bound to the original correlated jobs.

No job is created or dispatched, and only the jobs selected by id (or the
unsettled jobs bound to the current plan/candidate) are polled/accepted.
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ORCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ORCH))

BASE_FIXTURE = Path(os.environ.get("T3_SEAM_BASE_FIXTURE", "/opt/base-fixture"))
OLD_ROOT = os.environ.get("T3_SEAM_OLD_ROOT", "/var/tmp/guard-case-base-20261115")


class StubLauncher:
    def __init__(self):
        self.polls = []

    def poll(self, job):
        self.polls.append(job["job_id"])


class CollectOnlyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="collect-")
        self.root = Path(self._tmp.name) / "root"
        shutil.copytree(BASE_FIXTURE, self.root)
        db = self.root / "orchestrator/var/checkpoints.db"
        conn = sqlite3.connect(str(db))
        row = conn.execute("select value from workflow_meta where key='config'").fetchone()
        cfg = json.loads(row[0].replace(OLD_ROOT, str(self.root)))
        cfg["root"] = str(self.root)
        conn.execute("update workflow_meta set value=? where key='config'", (json.dumps(cfg),))
        conn.commit()
        conn.close()
        for p in self.root.rglob("*"):
            if p.is_file() and p.suffix in (".json", ".md", ".txt") and p.stat().st_size < 2_000_000:
                try:
                    text = p.read_text()
                except (UnicodeDecodeError, OSError):
                    continue
                if OLD_ROOT in text:
                    p.write_text(text.replace(OLD_ROOT, str(self.root)))
        from cli import make_engine
        from core import WorkflowError

        try:
            make_engine(self.root).run()
        except WorkflowError:
            pass
        conn = sqlite3.connect(str(db))
        self.job_id = conn.execute("select job_id from workflow_jobs").fetchone()[0]
        conn.close()
        from engine import Engine

        self.launcher = StubLauncher()
        self.engine = Engine(self.root, launcher=self.launcher)

    def tearDown(self):
        try:
            self.engine.close()
        finally:
            self._tmp.cleanup()

    def _status(self):
        return self.engine.store.job(self.job_id)["status"]

    def _job_count(self):
        conn = sqlite3.connect(str(self.root / "orchestrator/var/checkpoints.db"))
        try:
            return conn.execute("select count(*) from workflow_jobs").fetchone()[0]
        finally:
            conn.close()

    def test_created_job_is_not_selected_or_dispatched(self):
        self.assertEqual(self._status(), "CREATED")
        before = self._job_count()
        self.engine.collect_only()
        self.assertEqual(self.launcher.polls, [])
        self.assertEqual(self._status(), "CREATED")
        self.assertEqual(self._job_count(), before)

    def test_unsettled_correlated_job_is_polled_only(self):
        self.engine.store.update_job(self.job_id, "LAUNCH_INTENT", launch_attempts=1)
        before = self._job_count()
        self.engine.collect_only()
        self.assertEqual(self.launcher.polls, [self.job_id])
        self.assertEqual(self._status(), "LAUNCH_INTENT")
        self.assertEqual(self._job_count(), before)

    def test_explicit_allowlist_polls_only_that_job(self):
        self.engine.store.update_job(self.job_id, "LAUNCH_INTENT", launch_attempts=1)
        self.engine.collect_only(job_ids=[self.job_id])
        self.assertEqual(self.launcher.polls, [self.job_id])
        self.launcher.polls.clear()
        self.engine.collect_only(job_ids=[])
        self.assertEqual(self.launcher.polls, [])

    def test_forged_job_id_is_refused(self):
        self.engine.store.update_job(self.job_id, "LAUNCH_INTENT", launch_attempts=1)
        from core import WorkflowError

        with self.assertRaises(WorkflowError):
            self.engine.collect_only(job_ids=["job-forged"])
        self.assertEqual(self.launcher.polls, [])

    def test_mismatched_plan_binding_is_refused(self):
        self.engine.store.update_job(
            self.job_id,
            "LAUNCH_INTENT",
            launch_attempts=1,
            plan_revision_hash="0" * 64,
        )
        from core import WorkflowError

        with self.assertRaises(WorkflowError):
            self.engine.collect_only(job_ids=[self.job_id])
        self.assertEqual(self.launcher.polls, [])

    def test_unrelated_terminal_is_not_accepted(self):
        self.engine.store.update_job(self.job_id, "LAUNCH_INTENT", launch_attempts=1)
        dest = Path(self.engine.store.job(self.job_id)["runtime"])
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "terminal.json").write_text(json.dumps({"job_id": self.job_id, "phase": "TERMINAL"}))
        self.engine.collect_only(job_ids=[])
        self.assertEqual(self._status(), "LAUNCH_INTENT")
        result_events = [e for e in self.engine.store.events() if e["kind"] == "result"]
        self.assertEqual(result_events, [])


if __name__ == "__main__":
    unittest.main()
