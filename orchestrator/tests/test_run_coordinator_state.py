"""Durable run coordinator: state machine, bounds, recovery, fencing.

The coordinator is exercised with an injected pass function (no subprocess) so
the state machine, bounds, lease and recovery logic are tested directly.
"""

import asyncio
import atexit
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
sys.path.insert(0, str(ORCH))

# dashboard.config resolves its var dir at import time; keep it inside a
# disposable temp root so the read-only candidate bind stays untouched.
_TEST_ROOT = tempfile.mkdtemp(prefix="runcoord-root-")
_BENCH = Path(_TEST_ROOT) / "bench"
(_BENCH / "apps").mkdir(parents=True)
(_BENCH / "sites").mkdir(parents=True)
os.environ.setdefault("DASHBOARD_TEST_MODE", "1")
os.environ["DASHBOARD_TEST_ROOT"] = _TEST_ROOT
os.environ["FRAPPE_BENCH_ROOT"] = str(_BENCH)
os.environ.setdefault("ORCHESTRATOR_ROOT", str(ORCH.parent))
os.environ.setdefault("ORCHESTRATOR_PYTHON", "/usr/bin/python3.12")


atexit.register(lambda: shutil.rmtree(_TEST_ROOT, ignore_errors=True))


class CoordinatorStateMachineTests(unittest.TestCase):
    def setUp(self):
        from dashboard import run_coordinator as rc

        self.rc = rc
        self._tmp = tempfile.TemporaryDirectory(prefix="runcoord-")
        self.dir = Path(self._tmp.name)
        self.dir.chmod(0o700)
        self.registry = _FakeRegistry(self.dir / "registry.db")
        for i in range(1, 30):
            self.registry.add_task(f"t{i}", self.dir / "root")
        self.calls = []
        self.loop = asyncio.new_event_loop()
        self._coords = []

    def tearDown(self):
        for coord in self._coords:
            try:
                self.loop.run_until_complete(coord.shutdown())
            except Exception:
                pass
        self.loop.close()
        self._tmp.cleanup()

    def _coordinator(self, run_once, **kwargs):
        coord = self.rc.RunCoordinator(
            self.registry,
            instance_id="inst-test",
            run_once=run_once,
            poll_base=0.01,
            poll_cap=0.02,
            locks_dir=self.dir / "locks",
            **kwargs,
        )
        self._coords.append(coord)
        return coord

    def _call(self, fn, *args):
        async def _invoke():
            return fn(*args)

        return self.loop.run_until_complete(_invoke())

    def _wait(self, pred, timeout=10.0):
        async def _poll():
            end = time.time() + timeout
            while time.time() < end:
                if pred():
                    return True
                await asyncio.sleep(0.01)
            return False

        return self.loop.run_until_complete(_poll())

    def _fake(self, terminal_after=None):
        async def run_once(path, action_id, generation, lock_fd=None, action="run"):
            self.calls.append((action_id, generation))
            n = len(self.calls)
            done = terminal_after is not None and n >= terminal_after
            return {
                "view": {"status": "BUILD_IN_PROGRESS", "active_jobs": ["j1"]},
                "terminal": done,
                "job_status": {"j1": "ACCEPTED" if done else "CREATED"},
            }

        return run_once

    def test_runs_to_completion_and_restart_is_new_generation(self):
        coord = self._coordinator(self._fake(terminal_after=2))
        res = self._call(coord.start, "t1")
        self.assertTrue(res["ok"])
        self.assertTrue(self._wait(lambda: coord.status("t1")["state"] == "COMPLETED"))
        self.assertEqual(coord.status("t1")["passes"], 2)
        self.assertEqual(len(self.calls), 2)
        res2 = self._call(coord.start, "t1")
        self.assertTrue(res2["ok"])
        self.assertEqual(coord.status("t1")["generation"], 2)

    def test_max_passes_pauses_with_reason(self):
        coord = self._coordinator(self._fake(terminal_after=None), max_passes=3)
        self._call(coord.start, "t2")
        self.assertTrue(self._wait(lambda: coord.status("t2")["state"] == "PAUSED"))
        run = coord.status("t2")
        self.assertEqual(run["pause_reason"], "MAX_PASSES")
        self.assertEqual(run["passes"], 3)
        self.assertEqual(len(self.calls), 3)
        self.loop.run_until_complete(asyncio.sleep(0.05))
        self.assertEqual(len(self.calls), 3, "no dispatch after the bound")

    def test_max_seconds_pauses_with_reason(self):
        coord = self._coordinator(self._fake(terminal_after=None), max_seconds=0.05)
        self._call(coord.start, "t10")
        self.assertTrue(self._wait(lambda: coord.status("t10")["state"] == "PAUSED"))
        self.assertEqual(coord.status("t10")["pause_reason"], "MAX_SECONDS")

    def test_forty_pass_boundary_pauses_without_extra_dispatch(self):
        coord = self._coordinator(self._fake(terminal_after=None), max_passes=40)
        self._call(coord.start, "t11")
        self.assertTrue(self._wait(lambda: coord.status("t11")["state"] == "PAUSED"))
        run = coord.status("t11")
        self.assertEqual(run["passes"], 40)
        self.assertEqual(run["pause_reason"], "MAX_PASSES")
        self.assertEqual(len(self.calls), 40)
        self.loop.run_until_complete(asyncio.sleep(0.05))
        self.assertEqual(len(self.calls), 40)

    def test_stop_is_observed_between_passes(self):
        async def slow(path, action_id, generation, lock_fd=None, action="run"):
            self.calls.append(action_id)
            await asyncio.sleep(0.02)
            return {"view": {"status": "BUILD_IN_PROGRESS"}, "terminal": False, "job_status": {}}

        coord = self._coordinator(slow)
        self._call(coord.start, "t3")
        self.assertTrue(self._wait(lambda: coord.status("t3")["state"] == "RUNNING"))
        self._call(coord.request, "t3", "STOP")
        self.assertTrue(self._wait(lambda: coord.status("t3")["state"] == "STOPPED"))
        count = len(self.calls)
        self.loop.run_until_complete(asyncio.sleep(0.1))
        self.assertEqual(len(self.calls), count)

    def test_pause_is_observed_between_passes(self):
        coord = self._coordinator(self._fake(terminal_after=None))
        self._call(coord.start, "t4")
        self.assertTrue(self._wait(lambda: coord.status("t4")["state"] == "RUNNING"))
        self._call(coord.request, "t4", "PAUSE")
        self.assertTrue(self._wait(lambda: coord.status("t4")["state"] == "PAUSED"))
        self.assertEqual(coord.status("t4")["pause_reason"], "pause")

    def test_failed_pass_marks_the_action_log_row_failed(self):
        async def boom(path, action_id, generation, lock_fd=None, action="run"):
            raise RuntimeError("synthetic pass failure")

        coord = self._coordinator(boom)
        self._call(coord.start, "t14")
        self.assertTrue(self._wait(lambda: coord.status("t14")["state"] == "RECONCILIATION_REQUIRED"))
        aid = self.rc.pass_action_id("t14", 1, 0)
        conn = self.registry._get_connection()
        row = conn.execute(
            "SELECT state, error_message FROM action_log WHERE action_id = ?", (aid,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row, "failed pass must update its action_log row")
        self.assertEqual(row["state"], "FAILED")
        self.assertIn("synthetic pass failure", row["error_message"])

    def test_forget_drops_run_rows_and_action_log(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self._call(coord.start, "t15")
        self.assertTrue(self._wait(lambda: coord.status("t15")["state"] == "COMPLETED"))
        self.loop.run_until_complete(coord.forget("t15"))
        conn = self.registry._get_connection()
        n_state = conn.execute("SELECT COUNT(*) FROM run_state WHERE task_id='t15'").fetchone()[0]
        n_passes = conn.execute("SELECT COUNT(*) FROM run_passes WHERE task_id='t15'").fetchone()[0]
        n_log = conn.execute(
            "SELECT COUNT(*) FROM action_log WHERE task_id='t15' AND action_type='run'"
        ).fetchone()[0]
        conn.close()
        self.assertEqual((n_state, n_passes, n_log), (0, 0, 0))

    def test_forget_clears_direct_run_actions_but_preserves_other_tasks(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        conn = self.registry._get_connection()
        with conn:
            for task_id, action_id in (("t15", "old-direct"), ("other", "unrelated-direct")):
                conn.execute(
                    "INSERT INTO action_log (action_id, task_id, action_type, state, "
                    "request_hash, manifest_json, executor_instance_id, executor_pid, executor_start_time, created_utc, updated_utc) "
                    "VALUES (?,?,'run_direct','COMPLETE','synthetic-hash','{}','synthetic',1,1,?,?)",
                    (action_id, task_id, "2026-11-17", "2026-11-17"),
                )
        conn.close()
        self.loop.run_until_complete(coord.forget("t15"))
        conn = self.registry._get_connection()
        self.assertIsNone(conn.execute("SELECT 1 FROM action_log WHERE action_id='old-direct'").fetchone())
        self.assertIsNotNone(
            conn.execute("SELECT 1 FROM action_log WHERE action_id='unrelated-direct'").fetchone()
        )
        conn.close()

    def _seed_commit_action(self, task_id="t15", action_id="commit-handoff"):
        conn = self.registry._get_connection()
        with conn:
            conn.execute(
                "INSERT INTO action_log (action_id, task_id, action_type, state, request_hash, manifest_json, "
                "executor_instance_id, executor_pid, executor_start_time, created_utc, updated_utc) "
                "VALUES (?,?,'record_commit','COMPLETE','hash','{}','synthetic',1,1,?,?)",
                (action_id, task_id, "2026-11-17", "2026-11-17"),
            )
        conn.close()

    def test_commit_handoff_is_atomic_with_recoverable_run(self):
        self._seed_commit_action()
        coord = self._coordinator(self._fake(terminal_after=1))
        spawn = coord._spawn
        coord._spawn = lambda task, generation: None  # exit between durable write and loop creation
        result = self._call(lambda task: coord.start(task, handoff_action_id="commit-handoff"), "t15")
        self.assertTrue(result["ok"])
        conn = self.registry._get_connection()
        manifest = json.loads(
            conn.execute("SELECT manifest_json FROM action_log WHERE action_id='commit-handoff'").fetchone()[
                0
            ]
        )
        conn.close()
        self.assertEqual(manifest["coordinator_handoff_generation"], 1)
        self.assertEqual(coord.status("t15")["state"], "STARTING")
        coord._spawn = spawn
        self._call(coord.recover)
        self.assertTrue(self._wait(lambda: coord.status("t15")["state"] == "COMPLETED"))
        count = len(self.calls)
        retry = self._call(lambda task: coord.start(task, handoff_action_id="commit-handoff"), "t15")
        self.assertTrue(retry["ok"])
        self.assertEqual(coord.status("t15")["generation"], 1)
        self.assertEqual(len(self.calls), count)

    def test_commit_handoff_preserves_uncertain_outcome_guard(self):
        self._seed_commit_action()
        self.registry.seed_run("t15", "RECONCILIATION_REQUIRED", 3, os.getpid(), _start_time(os.getpid()))
        coord = self._coordinator(self._fake(terminal_after=1))
        result = self._call(lambda task: coord.start(task, handoff_action_id="commit-handoff"), "t15")
        self.assertFalse(result["ok"])
        self.assertEqual(coord.status("t15")["generation"], 3)
        self.assertEqual(self.calls, [])

    def test_commit_handoff_rejects_another_tasks_commit(self):
        self._seed_commit_action(task_id="t14")
        coord = self._coordinator(self._fake(terminal_after=1))
        with self.assertRaises(self.rc.RunBusy):
            self._call(lambda task: coord.start(task, handoff_action_id="commit-handoff"), "t15")
        self.assertEqual(coord.status("t15")["state"], "IDLE")

    def test_forget_refuses_while_active(self):
        async def slow(path, action_id, generation, lock_fd=None, action="run"):
            await asyncio.sleep(0.3)
            return {"view": {"status": "RUNNING"}, "terminal": False, "job_status": {}}

        coord = self._coordinator(slow)
        self._call(coord.start, "t16")
        self.assertTrue(self._wait(lambda: coord.status("t16")["state"] == "RUNNING"))
        with self.assertRaises(self.rc.RunBusy):
            self.loop.run_until_complete(coord.forget("t16"))
        conn = self.registry._get_connection()
        n = conn.execute("SELECT COUNT(*) FROM run_state WHERE task_id='t16'").fetchone()[0]
        conn.close()
        self.assertEqual(n, 1, "active run records must survive a refused forget")

    def test_pid_reuse_is_not_mistaken_for_a_live_owner(self):
        import os as _os

        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run(
            "t17",
            state="RUNNING",
            generation=1,
            owner_pid=_os.getpid(),
            owner_start=_start_time(_os.getpid()) + 1,
            owner_instance="inst-old",
        )
        self.assertEqual(coord.status("t17")["state"], "RECONCILIATION_REQUIRED")
        self.assertEqual(self._call(coord.recover), ["t17"])
        self.assertTrue(self._wait(lambda: coord.status("t17")["state"] == "COMPLETED"))

    def test_recovery_race_has_exactly_one_winner(self):
        import threading

        a = self._coordinator(self._fake(terminal_after=1))
        b = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run("t18", state="RUNNING", generation=1, owner_pid=_dead_pid(), owner_start=1)
        results = [None, None]

        def run(coord, idx):
            loop = asyncio.new_event_loop()
            try:

                async def invoke():
                    return coord.recover()

                results[idx] = loop.run_until_complete(invoke())
            finally:
                try:
                    loop.run_until_complete(coord.shutdown())
                except Exception:
                    pass
                loop.close()

        threads = [threading.Thread(target=run, args=(a, 0)), threading.Thread(target=run, args=(b, 1))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        winners = [r for r in results if r == ["t18"]]
        self.assertEqual(len(winners), 1, results)

    def test_unknown_pass_requires_resolution_before_operator_resume(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run("t19", state="RUNNING", generation=1, owner_pid=_dead_pid(), owner_start=1)
        self.registry.seed_pass("t19", 1, 0, "coord-t19-1-0", "IN_FLIGHT")
        conn = self.registry._get_connection()
        with conn:
            conn.execute("UPDATE run_state SET pass_count=1 WHERE task_id=?", ("t19",))
        conn.close()
        self._call(coord.recover)
        self.assertEqual(coord.status("t19")["state"], "RECONCILIATION_REQUIRED")
        self.assertFalse(self._call(coord.start, "t19")["ok"])
        resolved = self.loop.run_until_complete(coord.resolve("t19"))
        self.assertTrue(resolved["resolved"], resolved)
        self.assertEqual(coord.status("t19")["generation"], 1)
        res = self._call(coord.start, "t19")
        self.assertTrue(res["ok"])
        self.assertTrue(self._wait(lambda: coord.status("t19")["state"] == "COMPLETED"))
        self.assertEqual(coord.status("t19")["generation"], 2)

    def test_stop_request_does_not_resolve_reconciliation(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run("t20", state="RUNNING", generation=1, owner_pid=_dead_pid(), owner_start=1)
        self.registry.seed_pass("t20", 1, 0, "coord-t20-1-0", "IN_FLIGHT")
        self._call(coord.recover)
        self.assertEqual(coord.status("t20")["state"], "RECONCILIATION_REQUIRED")
        res = self._call(coord.request, "t20", "STOP")
        self.assertTrue(res["ok"])
        run = coord.status("t20")
        self.assertEqual(run["state"], "RECONCILIATION_REQUIRED", run)
        self.assertTrue(run["stop_requested"])
        self.assertEqual(run["pause_reason"], "pass_outcome_unknown")
        events = [e["event"] for e in coord.events("t20")]
        self.assertIn("stop_requested", events)
        with self.assertRaises(self.rc.RunBusy):
            self.loop.run_until_complete(coord.forget("t20"))
        # Manual abandonment requires an explicit acknowledgement and preserves
        # every pass row; it never asserts remote termination.
        bad = coord.abandon("t20", "tester", "ok")
        self.assertFalse(bad["ok"])
        good = coord.abandon("t20", "tester", "remote state unknown")
        self.assertTrue(good["ok"])
        run = coord.status("t20")
        self.assertEqual(run["state"], "ABANDONED")
        self.assertEqual(run["remote_state"], "unknown")
        self.assertEqual(run["pause_reason"], "pass_outcome_unknown")
        self.assertFalse(coord.start("t20")["ok"])
        conn = self.registry._get_connection()
        n = conn.execute("SELECT COUNT(*) FROM run_passes WHERE task_id='t20'").fetchone()[0]
        conn.close()
        self.assertEqual(n, 1, "abandonment must preserve pass evidence")

    def test_resolve_refused_during_live_coordinator_pass(self):
        async def slow(path, action_id, generation, lock_fd=None, action="run"):
            await asyncio.sleep(0.3)
            return {"view": {"status": "RUNNING"}, "terminal": False, "job_status": {}}

        coord = self._coordinator(slow)
        self._call(coord.start, "t27")
        self.assertTrue(self._wait(lambda: coord.status("t27")["state"] == "RUNNING"))
        res = self.loop.run_until_complete(coord.resolve("t27"))
        self.assertFalse(res["resolved"], res)
        self.assertTrue(res.get("conflict"), res)
        self.assertEqual(coord.status("t27")["state"], "RUNNING")
        self._call(coord.request, "t27", "STOP")
        self.assertTrue(self._wait(lambda: coord.status("t27")["state"] == "STOPPED"))

    def test_resolve_refused_during_live_direct_pass(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        lease = coord.acquire_direct("t28")
        self.assertTrue(lease["ok"])
        res = self.loop.run_until_complete(coord.resolve("t28"))
        self.assertFalse(res["resolved"], res)
        self.assertTrue(res.get("conflict"), res)
        coord.finalize_direct(
            "t28",
            lease["generation"],
            result={"view": {"status": "DRAFT"}, "terminal": False, "job_status": {}},
        )
        self.assertEqual(coord.status("t28")["state"], "PAUSED")

    def test_start_cannot_bypass_required_reconciliation(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run(
            "t28",
            state="RECONCILIATION_REQUIRED",
            generation=4,
            owner_pid=_dead_pid(),
            owner_start=1,
        )
        self.registry.seed_pass("t28", 4, 0, "coord-t28-4-0", "IN_FLIGHT")
        result = self._call(coord.start, "t28")
        self.assertFalse(result["ok"], result)
        self.assertEqual(coord.status("t28")["state"], "RECONCILIATION_REQUIRED")
        self.assertEqual(coord.status("t28")["generation"], 4)
        self.assertEqual(coord._last_pass("t28", 4)["state"], "IN_FLIGHT")
        self.assertEqual(self.calls, [])

    def test_never_started_task_can_be_forgotten(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.loop.run_until_complete(coord.forget("t28"))
        self.assertEqual(coord.status("t28")["state"], "IDLE")
        self.assertEqual(self.calls, [])

    def test_start_cannot_take_over_an_aged_live_direct_lease(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        lease = coord.acquire_direct("t28")
        conn = self.registry._get_connection()
        with conn:
            conn.execute(
                "UPDATE run_state SET updated_utc=? WHERE task_id=?", ("2000-01-01T00:00:00Z", "t28")
            )
        conn.close()
        result = self._call(coord.start, "t28")
        self.assertFalse(result["ok"], result)
        self.assertEqual(coord.status("t28")["generation"], lease["generation"])
        self.assertEqual(self.calls, [])
        coord.finalize_direct("t28", lease["generation"], result={"terminal": False})
        self.assertTrue(self._call(coord.start, "t28")["ok"])

    def test_start_preserves_unknown_pass_of_dead_owner(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run(
            "t28",
            state="RUNNING",
            generation=4,
            owner_pid=_dead_pid(),
            owner_start=1,
        )
        self.registry.seed_pass("t28", 4, 0, "coord-t28-4-0", "IN_FLIGHT")
        result = self._call(coord.start, "t28")
        self.assertFalse(result["ok"], result)
        self.assertEqual(coord.status("t28")["state"], "RECONCILIATION_REQUIRED")
        self.assertEqual(coord.status("t28")["generation"], 4)
        self.assertEqual(coord._last_pass("t28", 4)["state"], "IN_FLIGHT")
        self.assertEqual(self.calls, [])

    def test_single_pass_keeps_aged_lease_until_completion(self):
        async def scenario():
            entered, release = asyncio.Event(), asyncio.Event()

            async def held(*args):
                entered.set()
                await release.wait()
                return {"terminal": False, "view": {}, "job_status": {}}

            coord = self._coordinator(held)
            pending = asyncio.create_task(coord.run_single("t28"))
            await entered.wait()
            conn = self.registry._get_connection()
            with conn:
                conn.execute(
                    "UPDATE run_state SET updated_utc=? WHERE task_id=?", ("2000-01-01T00:00:00Z", "t28")
                )
            conn.close()
            refused = coord.start("t28")
            release.set()
            completed = await pending
            self.assertFalse(refused["ok"], refused)
            self.assertTrue(completed["ok"], completed)
            self.assertEqual(coord.status("t28")["state"], "PAUSED")
            self.assertNotIn("t28", coord._direct)

        self.loop.run_until_complete(scenario())

    def test_cancelled_single_pass_requires_reconciliation(self):
        async def scenario():
            entered = asyncio.Event()

            async def held(*args):
                entered.set()
                await asyncio.Event().wait()

            coord = self._coordinator(held)
            pending = asyncio.create_task(coord.run_single("t28"))
            await entered.wait()
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            self.assertEqual(coord.status("t28")["state"], "RECONCILIATION_REQUIRED")
            self.assertFalse(coord.start("t28")["ok"])
            self.assertNotIn("t28", coord._direct)

        self.loop.run_until_complete(scenario())

    def test_abandon_first_blocks_resolve(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run("t22", state="RUNNING", generation=1, owner_pid=_dead_pid(), owner_start=1)
        self.registry.seed_pass("t22", 1, 0, "coord-t22-1-0", "IN_FLIGHT")
        self._call(coord.recover)
        self.assertEqual(coord.status("t22")["state"], "RECONCILIATION_REQUIRED")
        self.assertTrue(coord.abandon("t22", "tester", "remote state unknown")["ok"])
        res = self.loop.run_until_complete(coord.resolve("t22"))
        self.assertFalse(res["resolved"])
        self.assertEqual(coord.status("t22")["state"], "ABANDONED")
        self.assertEqual(len(self.calls), 0)

    def test_abandon_during_resolve_is_refused(self):
        async def slow(path, action_id, generation, lock_fd=None, action="run"):
            await asyncio.sleep(0.3)
            return {
                "view": {"status": "BUILD_IN_PROGRESS"},
                "terminal": True,
                "job_status": {"j1": "ACCEPTED"},
            }

        coord = self._coordinator(slow)
        self.registry.seed_run("t23", state="RUNNING", generation=1, owner_pid=_dead_pid(), owner_start=1)
        self.registry.seed_pass("t23", 1, 0, "coord-t23-1-0", "IN_FLIGHT")
        _c = self.registry._get_connection()
        with _c:
            _c.execute("UPDATE run_state SET pass_count=1 WHERE task_id=?", ("t23",))
        _c.close()
        self._call(coord.recover)
        self.assertEqual(coord.status("t23")["state"], "RECONCILIATION_REQUIRED")
        task = self.loop.create_task(coord.resolve("t23"))
        self.loop.run_until_complete(asyncio.sleep(0))
        self.assertTrue(self._wait(lambda: coord.status("t23")["state"] == "RUNNING"))
        refused = coord.abandon("t23", "tester", "remote state unknown")
        self.assertFalse(refused["ok"], "abandon must not run during an authoritative collect")
        self.loop.run_until_complete(task)
        self.assertEqual(coord.status("t23")["state"], "COMPLETED")
        self.assertFalse(coord.status("t23")["abandoned"])

    def test_stop_during_resolve_is_recorded(self):
        async def slow(path, action_id, generation, lock_fd=None, action="run"):
            await asyncio.sleep(0.3)
            return {
                "view": {"status": "BUILD_IN_PROGRESS"},
                "terminal": True,
                "job_status": {"j1": "ACCEPTED"},
            }

        coord = self._coordinator(slow)
        self.registry.seed_run("t24", state="RUNNING", generation=1, owner_pid=_dead_pid(), owner_start=1)
        self.registry.seed_pass("t24", 1, 0, "coord-t24-1-0", "IN_FLIGHT")
        _c = self.registry._get_connection()
        with _c:
            _c.execute("UPDATE run_state SET pass_count=1 WHERE task_id=?", ("t24",))
        _c.close()
        self._call(coord.recover)
        self.assertEqual(coord.status("t24")["state"], "RECONCILIATION_REQUIRED")
        task = self.loop.create_task(coord.resolve("t24"))
        self.loop.run_until_complete(asyncio.sleep(0))
        self.assertTrue(self._wait(lambda: coord.status("t24")["state"] == "RUNNING"))
        self._call(coord.request, "t24", "STOP")
        self.loop.run_until_complete(task)
        run = coord.status("t24")
        self.assertEqual(run["state"], "COMPLETED")
        self.assertTrue(run["stop_requested"], run)
        self.assertEqual(run["desired"], "STOP")
        self.assertIn("stop_requested", [e["event"] for e in coord.events("t24")])

    def test_stop_on_owner_lost_raw_row_records_only(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run("t25", state="RUNNING", generation=1, owner_pid=_dead_pid(), owner_start=1)
        self._call(coord.request, "t25", "STOP")
        raw = (
            self.registry._get_connection()
            .execute("SELECT state, desired, stop_requested_utc FROM run_state WHERE task_id='t25'")
            .fetchone()
        )
        self.assertEqual(raw["state"], "RUNNING", "the raw state must not be resolved by a click")
        self.assertEqual(raw["desired"], "STOP")
        self.assertTrue(raw["stop_requested_utc"])
        self.assertEqual(coord.status("t25")["state"], "RECONCILIATION_REQUIRED")
        res = self.loop.run_until_complete(coord.resolve("t25"))
        self.assertTrue(res["resolved"], res)
        self.assertEqual(res["run"]["state"], "COMPLETED")

    def test_resolve_collects_a_late_result(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run("t21", state="RUNNING", generation=1, owner_pid=_dead_pid(), owner_start=1)
        self.registry.seed_pass("t21", 1, 0, "coord-t21-1-0", "IN_FLIGHT")
        conn = self.registry._get_connection()
        with conn:
            conn.execute("UPDATE run_state SET pass_count=1 WHERE task_id='t21'")
        conn.close()
        self._call(coord.recover)
        self.assertEqual(coord.status("t21")["state"], "RECONCILIATION_REQUIRED")
        res = self.loop.run_until_complete(coord.resolve("t21"))
        self.assertTrue(res["ok"], res)
        self.assertTrue(res["resolved"], res)
        self.assertEqual(res["run"]["state"], "COMPLETED")
        self.assertEqual(len(self.calls), 1)
        conn = self.registry._get_connection()
        n = conn.execute("SELECT COUNT(*) FROM run_passes WHERE task_id='t21'").fetchone()[0]
        conn.close()
        self.assertEqual(n, 2, "original in-flight pass row is preserved")

    def test_request_does_not_overwrite_a_terminal_state(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self._call(coord.start, "t12")
        self.assertTrue(self._wait(lambda: coord.status("t12")["state"] == "COMPLETED"))
        self._call(coord.request, "t12", "STOP")
        self.assertEqual(coord.status("t12")["state"], "COMPLETED")

    def test_orphaned_same_instance_loop_can_be_restarted(self):
        import os as _os

        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run(
            "t13",
            state="RUNNING",
            generation=1,
            owner_pid=_os.getpid(),
            owner_start=_start_time(_os.getpid()),
            owner_instance="inst-test",
        )
        res = self._call(coord.start, "t13")
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["run"]["generation"], 2)

    def test_direct_lease_races_coordinator_start(self):
        import threading

        results = {}

        def do_start(coord):
            loop = asyncio.new_event_loop()
            try:

                async def invoke():
                    return coord.start("t26")

                results["start"] = loop.run_until_complete(invoke())
            finally:
                loop.run_until_complete(coord.shutdown())
                loop.close()

        def do_direct(coord):
            results["direct"] = coord.acquire_direct("t26")

        async def slow(path, action_id, generation, lock_fd=None, action="run"):
            await asyncio.sleep(0.3)
            return {"view": {"status": "RUNNING"}, "terminal": False, "job_status": {}}

        a = self._coordinator(slow)
        b = self._coordinator(self._fake(terminal_after=1))
        threads = [
            threading.Thread(target=do_start, args=(a,)),
            threading.Thread(target=do_direct, args=(b,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        wins = [k for k, v in results.items() if v.get("ok")]
        self.assertEqual(len(wins), 1, results)

    def test_competing_start_conflicts(self):
        async def slow(path, action_id, generation, lock_fd=None, action="run"):
            self.calls.append(action_id)
            await asyncio.sleep(0.2)
            return {"view": {"status": "RUNNING"}, "terminal": False, "job_status": {}}

        coord = self._coordinator(slow)
        self.assertTrue(self._call(coord.start, "t5")["ok"])
        second = self._call(coord.start, "t5")
        self.assertFalse(second["ok"])
        self.assertTrue(second["conflict"])
        self.assertEqual(len(self.calls), 1)

    def test_dead_owner_status_is_reconciliation_required(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run("t6", state="RUNNING", generation=1, owner_pid=_dead_pid(), owner_start=1)
        run = coord.status("t6")
        self.assertEqual(run["state"], "RECONCILIATION_REQUIRED")
        self.assertEqual(run["pause_reason"], "owner_lost")

    def test_recovery_resumes_a_cleanly_interrupted_run(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run("t7", state="RUNNING", generation=3, owner_pid=_dead_pid(), owner_start=1)
        self.assertEqual(self._call(coord.recover), ["t7"])
        self.assertTrue(self._wait(lambda: coord.status("t7")["state"] == "COMPLETED"))
        self.assertEqual(coord.status("t7")["generation"], 3, "same run generation")
        self.assertEqual(len(self.calls), 1)

    def test_recovery_surfaces_an_unknown_pass(self):
        coord = self._coordinator(self._fake(terminal_after=1))
        self.registry.seed_run("t8", state="RUNNING", generation=2, owner_pid=_dead_pid(), owner_start=1)
        self.registry.seed_pass("t8", 2, 0, "coord-t8-2-0", "IN_FLIGHT")
        self._call(coord.recover)
        run = coord.status("t8")
        self.assertEqual(run["state"], "RECONCILIATION_REQUIRED")
        self.assertEqual(run["pause_reason"], "pass_outcome_unknown")
        self.assertEqual(len(self.calls), 0, "no blind re-send")

    def test_stale_fence_cannot_complete_a_pass(self):
        async def slow(path, action_id, generation, lock_fd=None, action="run"):
            self.calls.append(action_id)
            await asyncio.sleep(0.2)
            return {"view": {"status": "RUNNING"}, "terminal": False, "job_status": {}}

        coord = self._coordinator(slow)
        self._call(coord.start, "t9")
        self.assertTrue(self._wait(lambda: coord.status("t9")["state"] == "RUNNING"))
        # Claim a fresh pass, then let another owner bump the fence token.
        self.assertEqual(coord._claim("t9", 1, 5, "coord-t9-1-5", "h"), "claimed")
        conn = self.registry._get_connection()
        with conn:
            conn.execute("UPDATE action_log SET fencing_token = fencing_token + 1")
        conn.close()
        self.assertFalse(
            coord._complete_pass("t9", 1, 5, "coord-t9-1-5", {"view": {}, "terminal": True, "job_status": {}})
        )


def _start_time(pid):
    from dashboard.process import get_process_start_time

    return get_process_start_time(pid)


def _dead_pid():
    proc = subprocess.Popen(["/bin/true"])
    proc.wait(timeout=5)
    return proc.pid


class _FakeRegistry:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        from dashboard.registry import init_registry_db

        init_registry_db(self.db_path)
        self._tasks = {}

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def add_task(self, task_id, worktree_path):
        self._tasks[task_id] = {"task_id": task_id, "worktree_path": str(worktree_path)}

    def get_task(self, task_id):
        return self._tasks.get(task_id)

    def seed_run(self, task_id, state, generation, owner_pid, owner_start, owner_instance="inst-old"):
        now = "2026-11-15T00:00:00Z"
        conn = self._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO run_state (task_id, state, desired, generation, "
                "owner_instance_id, owner_pid, owner_start_time, pass_count, last_pass_index, "
                "last_result_json, last_error, pause_reason, created_utc, updated_utc) "
                "VALUES (?,?,'RUN',?,?,?,?,0,NULL,NULL,NULL,NULL,?,?)",
                (task_id, state, generation, owner_instance, owner_pid, owner_start, now, now),
            )
        conn.close()

    def seed_pass(self, task_id, generation, pass_index, action_id, state):
        now = "2026-11-15T00:00:00Z"
        conn = self._get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO run_passes (task_id, generation, pass_index, "
                "action_id, state, result_json, error, started_utc, updated_utc) "
                "VALUES (?,?,?,?,?,NULL,NULL,?,?)",
                (task_id, generation, pass_index, action_id, state, now, now),
            )
        conn.close()


if __name__ == "__main__":
    unittest.main()
