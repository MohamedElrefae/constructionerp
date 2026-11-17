"""Durable server-side run coordinator.

The browser is a viewer, not the driver. Closing a tab does not cancel or stop
a run: the loop lives in the dashboard server, and its state is persisted in
the registry database before every engine pass.

Durability model
----------------
- ``run_state`` holds one row per task: state (STARTING/RUNNING/PAUSED/STOPPED/
  COMPLETED/RECONCILIATION_REQUIRED), the operator's desired state (RUN/PAUSE/
  STOP), the run generation, the owner instance/pid/start-time, pass count and
  the last result/error.
- ``run_passes`` holds one row per attempted pass with a deterministic
  action-id. The row is written (IN_FLIGHT) before the engine subprocess is
  spawned, so a restart can tell "never sent" from "outcome unknown".
- A restarted server takes over runs whose owner process is gone. If the last
  pass completed, it resumes from the durable result. If the last pass was
  in flight when the owner died, it marks the run RECONCILIATION_REQUIRED
  instead of blindly re-sending; the engine's job state and the supervisor's
  no-relaunch ledger make a later resume safe.

Fencing semantics
-----------------
``generation`` is written into ``action_log.fencing_token`` and verified by the
engine. The coordinator writes that row itself, so the fence is a
**dedup/consistency anchor inside one trust domain**, not authorization: any
same-uid process that can write the registry could insert a matching row.
HTTP authorization is session auth + CSRF; worker dispatch stays blocked by the
engine dispatch gate. The coordinator only ever asks the engine to ``run``.

Bounded work
------------
Each loop is bounded by ``max_passes`` and ``max_seconds``; hitting either bound
moves the run to PAUSED with an explicit reason, never a silent stop. Between
passes the loop backs off exponentially up to ``poll_cap``.
"""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from dashboard.config import (
    LOCKS_DIR,
    RUN_MAX_PASSES,
    RUN_MAX_SECONDS,
    RUN_POLL_BASE_SECONDS,
    RUN_POLL_CAP_SECONDS,
)
from dashboard.process import get_process_start_time, is_process_alive_with_start_time
from dashboard.subprocess_client import SubprocessClientError, run_action

logger = logging.getLogger(__name__)

TERMINAL_STATES = {
    "PAUSED",
    "STOPPED",
    "COMPLETED",
    "RECONCILIATION_REQUIRED",
    "ABANDONED",
}
# States whose local cancellation/completion was verified. Only these permit
# unregister (row deletion); unknown outcomes and abandonments keep evidence.
VERIFIED_TERMINAL = {"PAUSED", "STOPPED", "COMPLETED"}
ACTIVE_STATES = {"STARTING", "RUNNING"}
RECONCILIATION_JOB_STATUSES = {
    "RECONCILIATION_REQUIRED",
    "OWNER_RECONCILED",
    "LAUNCH_FAILED",
}
# Reserved namespace for coordinator pass ids. HTTP callers may not choose an
# action_id with this prefix, so a client cannot pre-claim a pass id.
PASS_ACTION_PREFIX = "coord-"


def pass_action_id(task_id: str, generation: int, pass_index: int) -> str:
    return f"{PASS_ACTION_PREFIX}{task_id}-{generation}-{pass_index}"


class RunBusy(RuntimeError):
    """The run cannot be dropped: a pass or its subprocess may still be live."""


def _engine_child_pids(worktree_path: str) -> list[int]:
    """PIDs of live ``orchestrator.dashboard_api`` children for a worktree."""
    pids: list[int] = []
    root = str(Path(worktree_path).resolve())
    proc = Path("/proc")
    if not proc.is_dir():
        return pids
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmd = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode()
        except OSError:
            continue
        if "orchestrator.dashboard_api" in cmd and f"--root {root}" in cmd:
            pids.append(int(entry.name))
    return pids


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _recent(ts: str | None, seconds: float = 150.0) -> bool:
    if not ts:
        return False
    try:
        then = datetime.fromisoformat(ts)
    except ValueError:
        return False
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - then).total_seconds() < seconds


class RunCoordinator:
    """Owns durable, server-side run loops for registered tasks."""

    def __init__(
        self,
        registry,
        *,
        instance_id: str,
        run_once: Callable[[str, str, int], Awaitable[dict]] | None = None,
        max_passes: int = RUN_MAX_PASSES,
        max_seconds: float = RUN_MAX_SECONDS,
        poll_base: float = RUN_POLL_BASE_SECONDS,
        poll_cap: float = RUN_POLL_CAP_SECONDS,
        locks_dir: Path | None = None,
    ):
        self.registry = registry
        self.instance_id = instance_id
        self._run_once = run_once or self._default_run_once
        self.max_passes = int(max_passes)
        self.max_seconds = float(max_seconds)
        self.poll_base = float(poll_base)
        self.poll_cap = float(poll_cap)
        self.locks_dir = Path(locks_dir or LOCKS_DIR)
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        self._loops: dict[str, asyncio.Task] = {}
        self._direct: set[str] = set()

    # -- persistence helpers -------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        return self.registry._get_connection()

    def _owner_fields(self) -> dict[str, Any]:
        pid = os.getpid()
        return {
            "owner_instance_id": self.instance_id,
            "owner_pid": pid,
            "owner_start_time": get_process_start_time(pid) or 0,
        }

    def _owner_alive(self, row: sqlite3.Row) -> bool:
        if row["owner_pid"] is None or row["owner_start_time"] is None:
            return False
        return is_process_alive_with_start_time(row["owner_pid"], row["owner_start_time"])

    def _row(self, task_id: str) -> sqlite3.Row | None:
        conn = self._conn()
        try:
            return conn.execute("SELECT * FROM run_state WHERE task_id = ?", (task_id,)).fetchone()
        finally:
            conn.close()

    def _last_pass(self, task_id: str, generation: int) -> sqlite3.Row | None:
        conn = self._conn()
        try:
            return conn.execute(
                "SELECT * FROM run_passes WHERE task_id = ? AND generation = ? "
                "ORDER BY pass_index DESC LIMIT 1",
                (task_id, generation),
            ).fetchone()
        finally:
            conn.close()

    # -- public API ----------------------------------------------------------

    def status(self, task_id: str) -> dict[str, Any]:
        row = self._row(task_id)
        if not row:
            return {
                "task_id": task_id,
                "state": "IDLE",
                "desired": "RUN",
                "generation": 0,
                "passes": 0,
                "owner_alive": False,
                "last_error": None,
                "pause_reason": None,
                "last_result": None,
                "updated_utc": None,
                "stop_requested": False,
                "abandoned": False,
                "remote_state": None,
                "terminal": False,
                "verified_terminal": False,
            }
        state = row["state"]
        reason = row["pause_reason"]
        owner_alive = self._owner_alive(row)
        if state in ACTIVE_STATES and not owner_alive:
            state = "RECONCILIATION_REQUIRED"
            reason = reason or "owner_lost"
        last_result = None
        if row["last_result_json"]:
            try:
                last_result = json.loads(row["last_result_json"])
            except ValueError:
                last_result = None
        return {
            "task_id": task_id,
            "state": state,
            "desired": row["desired"],
            "generation": row["generation"],
            "passes": row["pass_count"],
            "last_pass_index": row["last_pass_index"],
            "last_action_id": row["last_action_id"],
            "owner_alive": owner_alive,
            "last_error": row["last_error"],
            "pause_reason": reason,
            "last_result": last_result,
            "updated_utc": row["updated_utc"],
            "stop_requested": bool(row["stop_requested_utc"]),
            "stop_requested_utc": row["stop_requested_utc"],
            "abandoned": state == "ABANDONED",
            "abandoned_utc": row["abandoned_utc"],
            "abandoned_by": row["abandoned_by"],
            "remote_state": row["remote_state"],
            "terminal": state in TERMINAL_STATES,
            "verified_terminal": state in VERIFIED_TERMINAL,
        }

    def acquire_direct(self, task_id: str) -> dict[str, Any]:
        """Lease for a single-pass direct run through the same run_state row."""
        now = _now()
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM run_state WHERE task_id = ?", (task_id,)).fetchone()
            if row and (
                row["state"] in ACTIVE_STATES or row["state"] in ("RECONCILIATION_REQUIRED", "ABANDONED")
            ):
                conn.rollback()
                return {
                    "ok": False,
                    "conflict": True,
                    "run": self.status(task_id),
                    "detail": f"Run is {self.status(task_id)['state']}; resolve or stop it first",
                }
            generation = (row["generation"] if row else 0) + 1
            owner = self._owner_fields()
            if row:
                conn.execute(
                    "UPDATE run_state SET state='STARTING', desired='RUN', generation=?, "
                    "owner_instance_id=?, owner_pid=?, owner_start_time=?, pass_count=0, "
                    "last_pass_index=NULL, last_result_json=NULL, last_error=NULL, "
                    "pause_reason=NULL, updated_utc=? WHERE task_id=?",
                    (
                        generation,
                        owner["owner_instance_id"],
                        owner["owner_pid"],
                        owner["owner_start_time"],
                        now,
                        task_id,
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO run_state (task_id, state, desired, generation, "
                    "owner_instance_id, owner_pid, owner_start_time, pass_count, "
                    "last_pass_index, last_result_json, last_error, pause_reason, "
                    "created_utc, updated_utc) VALUES (?,?,?,?,?,?,?,0,NULL,NULL,NULL,NULL,?,?)",
                    (
                        task_id,
                        "STARTING",
                        "RUN",
                        generation,
                        owner["owner_instance_id"],
                        owner["owner_pid"],
                        owner["owner_start_time"],
                        now,
                        now,
                    ),
                )
            conn.commit()
            self._direct.add(task_id)
            return {"ok": True, "generation": generation}
        finally:
            conn.close()

    def finalize_direct(
        self, task_id: str, generation: int, result: dict | None = None, error: str | None = None
    ) -> None:
        if error:
            self._set_state(
                task_id, generation, "RECONCILIATION_REQUIRED", reason="pass_failed", error=error[:1000]
            )
        elif result and result.get("terminal"):
            state, reason = self._terminal_state(result)
            self._set_state(task_id, generation, state, reason=reason, result=result)
        else:
            self._set_state(task_id, generation, "PAUSED", reason="single_pass", result=result or {})
        self._direct.discard(task_id)

    async def run_single(self, task_id: str) -> dict[str, Any]:
        """Run one pass under the same tracked lease as a direct HTTP run."""
        lease = self.acquire_direct(task_id)
        if not lease.get("ok"):
            return lease
        generation = lease["generation"]
        try:
            result = await self._pass(task_id, generation, 0)
            if result is None:
                self._direct.discard(task_id)
                run = self.status(task_id)
                return {"ok": False, "run": run, "detail": run.get("last_error") or "Run failed"}
            self.finalize_direct(task_id, generation, result=result)
            return {
                "ok": True,
                "view": result.get("view"),
                "terminal": bool(result.get("terminal")),
                "job_status": result.get("job_status"),
                "run": self.status(task_id),
            }
        except asyncio.CancelledError:
            self.finalize_direct(
                task_id, generation, error="Single pass cancelled; outcome requires reconciliation"
            )
            raise

    def start(self, task_id: str) -> dict[str, Any]:
        """Acquire the run lease and start the loop. Idempotent per task."""
        now = _now()
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM run_state WHERE task_id = ?", (task_id,)).fetchone()
            if row and row["state"] == "ABANDONED":
                conn.rollback()
                return {"ok": False, "abandoned": True, "run": self.status(task_id)}
            if row and row["state"] == "RECONCILIATION_REQUIRED":
                conn.rollback()
                return {
                    "ok": False,
                    "conflict": True,
                    "run": self.status(task_id),
                    "detail": "Resolve the uncertain outcome before starting another run",
                }
            if row and row["state"] in ACTIVE_STATES:
                same_owner = row["owner_instance_id"] == self.instance_id and (
                    task_id in self._direct or (task_id in self._loops and not self._loops[task_id].done())
                )
                # Tracked passes retain their lease while queued or executing,
                # regardless of heartbeat age. Recent untracked rows and other
                # live owner instances also refuse takeover.
                live_lease = self._owner_alive(row) and (
                    row["owner_instance_id"] != self.instance_id or _recent(row["updated_utc"])
                )
                if same_owner or live_lease:
                    conn.rollback()
                    return {"ok": False, "conflict": True, "run": self.status(task_id)}
                unknown_pass = conn.execute(
                    "SELECT 1 FROM run_passes WHERE task_id=? AND generation=? "
                    "AND state='IN_FLIGHT' LIMIT 1",
                    (task_id, row["generation"]),
                ).fetchone()
                if unknown_pass:
                    conn.execute(
                        "UPDATE run_state SET state='RECONCILIATION_REQUIRED', "
                        "pause_reason='pass_outcome_unknown', updated_utc=? "
                        "WHERE task_id=? AND generation=?",
                        (now, task_id, row["generation"]),
                    )
                    conn.commit()
                    return {
                        "ok": False,
                        "conflict": True,
                        "run": self.status(task_id),
                        "detail": "Resolve the uncertain pass before starting another run",
                    }
                # Same instance but no live loop: a crashed loop, not a live owner.
                logger.warning("taking over orphaned run loop for %s", task_id)
            generation = (row["generation"] if row else 0) + 1
            owner = self._owner_fields()
            if row:
                conn.execute(
                    "UPDATE run_state SET state='STARTING', desired='RUN', generation=?, "
                    "owner_instance_id=?, owner_pid=?, owner_start_time=?, pass_count=0, "
                    "last_pass_index=NULL, last_result_json=NULL, last_error=NULL, "
                    "pause_reason=NULL, updated_utc=? WHERE task_id=?",
                    (
                        generation,
                        owner["owner_instance_id"],
                        owner["owner_pid"],
                        owner["owner_start_time"],
                        now,
                        task_id,
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO run_state (task_id, state, desired, generation, "
                    "owner_instance_id, owner_pid, owner_start_time, pass_count, "
                    "last_pass_index, last_result_json, last_error, pause_reason, "
                    "created_utc, updated_utc) VALUES (?,?,?,?,?,?,?,0,NULL,NULL,NULL,NULL,?,?)",
                    (
                        task_id,
                        "STARTING",
                        "RUN",
                        generation,
                        owner["owner_instance_id"],
                        owner["owner_pid"],
                        owner["owner_start_time"],
                        now,
                        now,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
        self._spawn(task_id, generation)
        return {"ok": True, "run": self.status(task_id)}

    def request(self, task_id: str, desired: str) -> dict[str, Any]:
        """Record a PAUSE/STOP request. Never resolves an unknown outcome.

        For a live loop the request is observed between passes. For a run in
        RECONCILIATION_REQUIRED (or an owner-lost active row) the request is
        recorded durably (``stop_requested_utc`` + an append-only event) and the
        state stays RECONCILIATION_REQUIRED: a UI click cannot prove a remote
        job stopped or completed. Resolution requires an authoritative collect
        pass (``resolve``) or a separately scoped abandonment.
        """
        assert desired in ("PAUSE", "STOP")
        target = "PAUSED" if desired == "PAUSE" else "STOPPED"
        now = _now()
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM run_state WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                conn.rollback()
                return {"ok": True, "run": self.status(task_id)}
            effective = row["state"]
            owner_alive = self._owner_alive(row)
            if effective in ACTIVE_STATES and not owner_alive:
                effective = "RECONCILIATION_REQUIRED"
            if effective in VERIFIED_TERMINAL or effective == "ABANDONED":
                conn.rollback()
                return {"ok": True, "run": self.status(task_id)}
            if effective == "RECONCILIATION_REQUIRED":
                conn.execute(
                    "UPDATE run_state SET desired=?, stop_requested_utc=COALESCE(stop_requested_utc, ?), "
                    "updated_utc=? WHERE task_id=? AND generation=?",
                    (desired, now, now, task_id, row["generation"]),
                )
                conn.commit()
                self._event(
                    task_id,
                    row["generation"],
                    "stop_requested" if desired == "STOP" else "pause_requested",
                    {"state": effective},
                    actor=None,
                )
                return {"ok": True, "run": self.status(task_id)}
            if row["state"] in ACTIVE_STATES and owner_alive:
                conn.execute(
                    "UPDATE run_state SET desired=?, stop_requested_utc=COALESCE(stop_requested_utc, ?), "
                    "updated_utc=? WHERE task_id=?",
                    (desired, now, now, task_id),
                )
                conn.commit()
                self._event(
                    task_id,
                    row["generation"],
                    "stop_requested" if desired == "STOP" else "pause_requested",
                    {"state": row["state"]},
                    actor=None,
                )
                return {"ok": True, "run": self.status(task_id)}
            conn.rollback()
            return {"ok": True, "run": self.status(task_id)}
        finally:
            conn.close()

    async def resolve(self, task_id: str) -> dict[str, Any]:
        """Authoritative reconciliation of an unknown pass outcome.

        Runs exactly one engine collect pass for the original generation: the
        engine polls the supervisor's durable ledger for the launched job and
        accepts the late result (or keeps the run in reconciliation). It never
        deletes evidence and never starts a second launch for a launched job.
        """
        loop = self._loops.get(task_id)
        if (loop and not loop.done()) or task_id in self._direct:
            return {
                "ok": False,
                "resolved": False,
                "conflict": True,
                "run": self.status(task_id),
                "detail": "A live pass is running; wait for it to finish",
            }
        row = self._row(task_id)
        if not row:
            return {"ok": False, "resolved": False, "run": self.status(task_id)}
        # An owner-lost ACTIVE row is reported as reconciliation but is not yet
        # persisted as such: take it over (CAS) before resolving. A live owner
        # (even the same instance, e.g. a direct pass) is never raced.
        if row["state"] in ACTIVE_STATES:
            if self._owner_alive(row):
                return {
                    "ok": False,
                    "resolved": False,
                    "conflict": True,
                    "run": self.status(task_id),
                    "detail": "A live run owns this task; stop it or wait for it to finish",
                }
            owner = self._owner_fields()
            conn = self._conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                cur = conn.execute(
                    "UPDATE run_state SET state='RECONCILIATION_REQUIRED', owner_instance_id=?, "
                    "owner_pid=?, owner_start_time=?, updated_utc=? "
                    "WHERE task_id=? AND generation=? AND state IN ('STARTING','RUNNING') "
                    "AND owner_instance_id IS ? AND owner_pid IS ? AND owner_start_time IS ?",
                    (
                        owner["owner_instance_id"],
                        owner["owner_pid"],
                        owner["owner_start_time"],
                        _now(),
                        task_id,
                        row["generation"],
                        row["owner_instance_id"],
                        row["owner_pid"],
                        row["owner_start_time"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
            if not cur.rowcount:
                return {"ok": False, "resolved": False, "run": self.status(task_id)}
            row = self._row(task_id)
        if row["state"] != "RECONCILIATION_REQUIRED":
            return {"ok": False, "resolved": False, "run": self.status(task_id)}
        generation = row["generation"]
        if row["owner_instance_id"] != self.instance_id or not self._owner_alive(row):
            owner = self._owner_fields()
            conn = self._conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                cur = conn.execute(
                    "UPDATE run_state SET owner_instance_id=?, owner_pid=?, owner_start_time=?, "
                    "updated_utc=? WHERE task_id=? AND generation=? AND state='RECONCILIATION_REQUIRED' "
                    "AND owner_instance_id IS ? AND owner_pid IS ? AND owner_start_time IS ?",
                    (
                        owner["owner_instance_id"],
                        owner["owner_pid"],
                        owner["owner_start_time"],
                        _now(),
                        task_id,
                        generation,
                        row["owner_instance_id"],
                        row["owner_pid"],
                        row["owner_start_time"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
            if not cur.rowcount:
                return {"ok": False, "resolved": False, "run": self.status(task_id)}
            row = self._row(task_id)
        prior_desired = row["desired"]
        # One collect pass: state RUNNING + desired RUN are required by _claim.
        # The transition is a CAS on the observed reconciliation state so a
        # concurrent abandon/start cannot be resurrected.
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "UPDATE run_state SET state='RUNNING', desired='RUN', updated_utc=? "
                "WHERE task_id=? AND generation=? AND state='RECONCILIATION_REQUIRED' "
                "AND owner_instance_id=?",
                (_now(), task_id, generation, self.instance_id),
            )
            conn.commit()
        finally:
            conn.close()
        if not cur.rowcount:
            return {"ok": False, "resolved": False, "run": self.status(task_id)}
        result = await self._pass(task_id, generation, row["pass_count"], action="collect")
        resolved = False
        if result is not None:
            if result.get("selected") == []:
                self._set_state(
                    task_id,
                    generation,
                    "RECONCILIATION_REQUIRED",
                    reason="no_correlated_job",
                    error="No unsettled job bound to this run was found to collect.",
                )
                result = None
        if result is not None:
            if result.get("terminal"):
                state, reason = self._terminal_state(result)
                self._set_state(task_id, generation, state, reason=reason, result=result)
                resolved = state in VERIFIED_TERMINAL
            else:
                self._set_state(
                    task_id,
                    generation,
                    "RECONCILIATION_REQUIRED",
                    reason="still_uncertain",
                    error="Authoritative collect did not prove the original job outcome.",
                )
        else:
            # _pass already recorded the failure/reconciliation state.
            pass
        # Restore the operator's requested desired state only if no new request
        # arrived during the pass (a concurrent STOP leaves desired='STOP').
        conn = self._conn()
        try:
            with conn:
                conn.execute(
                    "UPDATE run_state SET desired=? WHERE task_id=? AND generation=? "
                    "AND owner_instance_id=? AND desired='RUN'",
                    (prior_desired, task_id, generation, self.instance_id),
                )
        finally:
            conn.close()
        self._event(
            task_id,
            generation,
            "resolved",
            {"resolved": resolved, "state": self.status(task_id)["state"]},
            actor=None,
        )
        return {"ok": True, "resolved": resolved, "run": self.status(task_id)}

    def abandon(self, task_id: str, actor: str, acknowledge: str) -> dict[str, Any]:
        """Separately scoped manual abandonment. Never asserts remote termination.

        Requires an explicit acknowledgement string; moves the run to ABANDONED,
        keeps every pass/action row and event as immutable evidence, and blocks
        start/unregister until a separately scoped recovery process exists.
        """
        if acknowledge != "remote state unknown":
            return {"ok": False, "detail": "acknowledgement required", "run": self.status(task_id)}
        now = _now()
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM run_state WHERE task_id = ?", (task_id,)).fetchone()
            if not row or row["state"] not in ("RECONCILIATION_REQUIRED", "ABANDONED"):
                conn.rollback()
                return {
                    "ok": False,
                    "detail": "no unknown-outcome run to abandon",
                    "run": self.status(task_id),
                }
            conn.execute(
                "UPDATE run_state SET state='ABANDONED', desired='STOP', remote_state='unknown', "
                "abandoned_utc=COALESCE(abandoned_utc, ?), abandoned_by=COALESCE(abandoned_by, ?), "
                "updated_utc=? WHERE task_id=? AND generation=?",
                (now, actor, now, task_id, row["generation"]),
            )
            conn.commit()
        finally:
            conn.close()
        self._event(
            task_id,
            row["generation"],
            "abandoned",
            {"remote_state": "unknown", "acknowledge": acknowledge},
            actor=actor,
        )
        return {"ok": True, "run": self.status(task_id)}

    def events(self, task_id: str) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT id, generation, event, detail, actor, created_utc "
                "FROM run_events WHERE task_id=? ORDER BY id",
                (task_id,),
            ).fetchall()
        finally:
            conn.close()
        out = []
        for r in rows:
            try:
                detail = json.loads(r["detail"]) if r["detail"] else None
            except ValueError:
                detail = r["detail"]
            out.append(
                {
                    "id": r["id"],
                    "generation": r["generation"],
                    "event": r["event"],
                    "detail": detail,
                    "actor": r["actor"],
                    "created_utc": r["created_utc"],
                }
            )
        return out

    def _event(self, task_id: str, generation: int, event: str, detail=None, actor=None) -> None:
        conn = self._conn()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO run_events (task_id, generation, event, detail, actor, created_utc) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        task_id,
                        generation,
                        event,
                        json.dumps(detail) if detail is not None else None,
                        actor,
                        _now(),
                    ),
                )
        finally:
            conn.close()

    def recover(self) -> list[str]:
        """Resume or surface runs whose owner died (startup / crash recovery)."""
        resumed: list[str] = []
        conn = self._conn()
        try:
            rows = conn.execute("SELECT * FROM run_state WHERE state IN ('STARTING','RUNNING')").fetchall()
        finally:
            conn.close()
        for row in rows:
            task_id = row["task_id"]
            if self._owner_alive(row) and row["owner_instance_id"] != self.instance_id:
                continue  # another live dashboard instance owns it
            if self._owner_alive(row) and task_id in self._loops:
                continue
            task = self.registry.get_task(task_id)
            if not task:
                self._set_state(
                    task_id,
                    row["generation"],
                    "STOPPED",
                    reason="task_missing",
                    owner_instance=row["owner_instance_id"],
                )
                continue
            last = self._last_pass(task_id, row["generation"])
            if last and last["state"] == "IN_FLIGHT":
                logger.warning("run %s has an in-flight pass; surfacing reconciliation", task_id)
                self._set_state(
                    task_id,
                    row["generation"],
                    "RECONCILIATION_REQUIRED",
                    owner_instance=row["owner_instance_id"],
                    reason="pass_outcome_unknown",
                    error=(
                        "The server restarted while an engine pass was in flight; "
                        "the send outcome is unknown. Review the job, then resume."
                    ),
                )
                continue
            owner = self._owner_fields()
            now = _now()
            conn = self._conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                cur = conn.execute(
                    "UPDATE run_state SET owner_instance_id=?, owner_pid=?, "
                    "owner_start_time=?, updated_utc=? WHERE task_id=? AND generation=? "
                    "AND state IN ('STARTING','RUNNING') "
                    "AND owner_instance_id IS ? AND owner_pid IS ? AND owner_start_time IS ?",
                    (
                        owner["owner_instance_id"],
                        owner["owner_pid"],
                        owner["owner_start_time"],
                        now,
                        task_id,
                        row["generation"],
                        row["owner_instance_id"],
                        row["owner_pid"],
                        row["owner_start_time"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
            if cur.rowcount:
                self._spawn(task_id, row["generation"])
                resumed.append(task_id)
        return resumed

    async def forget(self, task_id: str) -> None:
        """Drop a task's run records after proving no pass is still running.

        Refused by the caller while the run is active or awaiting reconciliation.
        The loop is cancelled and awaited (which kills and reaps its engine
        subprocess), then a /proc scan refuses deletion if any engine child for
        this worktree is still alive.
        """
        row = self._row(task_id)
        if row and (
            row["state"] in ACTIVE_STATES or row["state"] in ("RECONCILIATION_REQUIRED", "ABANDONED")
        ):
            raise RunBusy(f"run {task_id} is {row['state']}; resolve or stop it first")
        loop = self._loops.pop(task_id, None)
        if loop and not loop.done():
            loop.cancel()
            try:
                await loop
            except (asyncio.CancelledError, Exception):
                pass
        task = self.registry.get_task(task_id)
        if task and _engine_child_pids(task["worktree_path"]):
            raise RunBusy(f"engine subprocess still alive for {task_id}; refusing to drop run records")
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "DELETE FROM run_state WHERE task_id = ? "
                "AND state NOT IN ('STARTING','RUNNING','RECONCILIATION_REQUIRED','ABANDONED')",
                (task_id,),
            )
            if (
                cur.rowcount != 1
                and conn.execute(
                    "SELECT 1 FROM run_state WHERE task_id=?",
                    (task_id,),
                ).fetchone()
            ):
                conn.rollback()
                raise RunBusy(f"run {task_id} became active during unregister")
            conn.execute("DELETE FROM run_passes WHERE task_id = ?", (task_id,))
            conn.execute(
                "DELETE FROM action_log WHERE task_id = ? AND action_type IN ('run','run_start','run_direct')",
                (task_id,),
            )
            conn.commit()
        finally:
            conn.close()

    async def shutdown(self) -> None:
        """Cancel loops; durable state lets the next startup recover."""
        loops = list(self._loops.values())
        for task in loops:
            task.cancel()
        for task in loops:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._loops.clear()

    # -- loop ----------------------------------------------------------------

    def _spawn(self, task_id: str, generation: int) -> None:
        existing = self._loops.get(task_id)
        if existing and not existing.done():
            existing.cancel()
        self._loops[task_id] = asyncio.create_task(self._loop(task_id, generation))

    async def _loop(self, task_id: str, generation: int) -> None:
        started = time.monotonic()
        idle = 0
        try:
            while True:
                row = self._row(task_id)
                if not row or row["generation"] != generation:
                    return
                if row["state"] in TERMINAL_STATES:
                    return
                if row["desired"] != "RUN":
                    target = "PAUSED" if row["desired"] == "PAUSE" else "STOPPED"
                    self._set_state(task_id, generation, target, reason=row["desired"].lower())
                    return
                if row["pass_count"] >= self.max_passes:
                    self._set_state(
                        task_id,
                        generation,
                        "PAUSED",
                        reason="MAX_PASSES",
                        error=f"Stopped after the {self.max_passes}-pass bound; resume to continue.",
                    )
                    return
                if time.monotonic() - started > self.max_seconds:
                    self._set_state(
                        task_id,
                        generation,
                        "PAUSED",
                        reason="MAX_SECONDS",
                        error=f"Stopped after the {int(self.max_seconds)}s bound; resume to continue.",
                    )
                    return
                result = await self._pass(task_id, generation, row["pass_count"], action="run")
                if result is None:
                    return
                if result.get("terminal"):
                    state, reason = self._terminal_state(result)
                    self._set_state(task_id, generation, state, reason=reason, result=result)
                    return
                idle += 1
                delay = min(self.poll_base * (2 ** (idle - 1)), self.poll_cap)
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # never leave a run silently active
            logger.exception("run loop failed for %s generation %s", task_id, generation)
            self._set_state(
                task_id,
                generation,
                "RECONCILIATION_REQUIRED",
                reason="coordinator_error",
                error=f"{type(exc).__name__}: {exc}",
            )
        finally:
            current = self._loops.get(task_id)
            if current is asyncio.current_task():
                self._loops.pop(task_id, None)

    def _terminal_state(self, result: dict[str, Any]) -> tuple[str, str | None]:
        statuses = list((result.get("job_status") or {}).values())
        if any(s in RECONCILIATION_JOB_STATUSES for s in statuses):
            return "RECONCILIATION_REQUIRED", "job_reconciliation"
        view = result.get("view") or {}
        if view.get("pause_reason") == "RECONCILIATION_REQUIRED":
            # A collect pass without a provable remote outcome must never be
            # reported as a verified PAUSED/terminal state.
            return "RECONCILIATION_REQUIRED", "job_reconciliation"
        if view.get("status") == "PAUSED" or view.get("gate"):
            return "PAUSED", view.get("pause_reason") or "gate"
        return "COMPLETED", None

    async def _pass(
        self, task_id: str, generation: int, pass_index: int, action: str = "run"
    ) -> dict[str, Any] | None:
        action_id = pass_action_id(task_id, generation, pass_index)
        request_hash = hashlib.sha256(
            json.dumps(
                {"task_id": task_id, "generation": generation, "pass": pass_index},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        claim = self._claim(task_id, generation, pass_index, action_id, request_hash, action)
        if claim == "lease_lost":
            return None
        if claim == "pass_exists":
            self._set_state(
                task_id,
                generation,
                "RECONCILIATION_REQUIRED",
                reason="pass_index_exists",
                error=f"Pass index {pass_index} already exists; manual reconciliation required.",
            )
            return None
        if claim == "action_exists":
            self._set_state(
                task_id,
                generation,
                "RECONCILIATION_REQUIRED",
                reason="pass_outcome_unknown",
                error=(
                    f"Pass {pass_index} was already attempted ({action_id}) with an "
                    "unknown outcome; review the job, then resume."
                ),
            )
            return None
        task = self.registry.get_task(task_id)
        if not task:
            self._fail_pass(task_id, generation, pass_index, "Task disappeared")
            return None
        lock_file = self.locks_dir / f"action_{action_id}.lock"
        lock_fd = None
        try:
            lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self._fail_pass(
                    task_id,
                    generation,
                    pass_index,
                    f"Action lock for {action_id} is held by another executor",
                )
                return None
            result = await self._run_once(task["worktree_path"], action_id, generation, lock_fd, action)
        except SubprocessClientError as exc:
            self._fail_pass(task_id, generation, pass_index, str(exc))
            return None
        except Exception as exc:
            self._fail_pass(task_id, generation, pass_index, f"{type(exc).__name__}: {exc}")
            return None
        finally:
            if lock_fd is not None:
                try:
                    os.close(lock_fd)
                except OSError:
                    pass
        if not self._complete_pass(task_id, generation, pass_index, action_id, result):
            self._set_state(
                task_id,
                generation,
                "RECONCILIATION_REQUIRED",
                reason="fence_lost",
                error="Another coordinator took over while this pass was in flight.",
            )
            return None
        return result

    async def _default_run_once(
        self,
        worktree_path: str,
        action_id: str,
        generation: int,
        lock_fd: int | None = None,
        action: str = "run",
    ) -> dict[str, Any]:
        return await run_action(
            worktree_path,
            action,
            payload={
                "action_id": action_id,
                "fencing_token": generation,
                "executor_instance_id": self.instance_id,
            },
            action_id=action_id,
            fencing_token=generation,
            executor_instance_id=self.instance_id,
            lock_fd=lock_fd,
        )

    # -- pass persistence ----------------------------------------------------

    def _claim(
        self,
        task_id: str,
        generation: int,
        pass_index: int,
        action_id: str,
        request_hash: str,
        action: str = "run",
    ) -> str:
        now = _now()
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM run_state WHERE task_id = ?", (task_id,)).fetchone()
            if (
                not row
                or row["generation"] != generation
                or row["owner_instance_id"] != self.instance_id
                or row["state"] not in ACTIVE_STATES
                or row["desired"] != "RUN"
            ):
                conn.rollback()
                return "lease_lost"
            existing = conn.execute("SELECT 1 FROM action_log WHERE action_id = ?", (action_id,)).fetchone()
            if existing:
                conn.rollback()
                return "action_exists"
            try:
                conn.execute(
                    "INSERT INTO run_passes (task_id, generation, pass_index, action_id, "
                    "state, result_json, error, started_utc, updated_utc) "
                    "VALUES (?,?,?,?,?,NULL,NULL,?,?)",
                    (task_id, generation, pass_index, action_id, "IN_FLIGHT", now, now),
                )
            except sqlite3.IntegrityError:
                conn.rollback()
                return "pass_exists"
            conn.execute(
                """
                INSERT INTO action_log (
                    action_id, task_id, action_type, state, idempotency_key,
                    request_hash, manifest_json, response_json, correlation_id,
                    executor_instance_id, executor_pid, executor_start_time,
                    child_pid, child_pgid, child_start_time, fencing_token,
                    heartbeat_utc, error_message, session_memory_entry,
                    created_utc, updated_utc
                ) VALUES (?,?,?,?,?,?,?,NULL,?,?,?,?,NULL,NULL,NULL,?,?,NULL,NULL,?,?)
                """,
                (
                    action_id,
                    task_id,
                    action,
                    "EXECUTING",
                    action_id,
                    request_hash,
                    json.dumps({}),
                    action_id,
                    self.instance_id,
                    os.getpid(),
                    get_process_start_time(os.getpid()) or 0,
                    generation,
                    now,
                    now,
                    now,
                ),
            )
            conn.execute(
                "UPDATE run_state SET state='RUNNING', pass_count=?, "
                "last_action_id=?, last_pass_index=?, updated_utc=? WHERE task_id=?",
                (pass_index + 1, action_id, pass_index, now, task_id),
            )
            conn.commit()
            return "claimed"
        finally:
            conn.close()

    def _complete_pass(
        self,
        task_id: str,
        generation: int,
        pass_index: int,
        action_id: str,
        result: dict[str, Any],
    ) -> bool:
        now = _now()
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "UPDATE action_log SET state='COMPLETE', response_json=?, updated_utc=? "
                "WHERE action_id=? AND state='EXECUTING' AND fencing_token=? "
                "AND executor_instance_id=?",
                (json.dumps(result), now, action_id, generation, self.instance_id),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return False
            conn.execute(
                "UPDATE run_passes SET state='COMPLETE', result_json=?, updated_utc=? "
                "WHERE task_id=? AND generation=? AND pass_index=? AND state='IN_FLIGHT'",
                (json.dumps(result), now, task_id, generation, pass_index),
            )
            conn.execute(
                "UPDATE run_state SET last_result_json=?, last_error=NULL, updated_utc=? "
                "WHERE task_id=? AND generation=? AND owner_instance_id=?",
                (json.dumps(result), now, task_id, generation, self.instance_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def _fail_pass(self, task_id: str, generation: int, pass_index: int, error: str) -> None:
        now = _now()
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE run_passes SET state='FAILED', error=?, updated_utc=? "
                "WHERE task_id=? AND generation=? AND pass_index=? AND state='IN_FLIGHT'",
                (error[:1000], now, task_id, generation, pass_index),
            )
            conn.execute(
                "UPDATE action_log SET state='FAILED', error_message=?, updated_utc=? "
                "WHERE action_id=? AND state='EXECUTING' AND fencing_token=? "
                "AND executor_instance_id=?",
                (
                    error[:500],
                    now,
                    pass_action_id(task_id, generation, pass_index),
                    generation,
                    self.instance_id,
                ),
            )
            conn.execute(
                "UPDATE run_state SET state='RECONCILIATION_REQUIRED', "
                "pause_reason='pass_failed', last_error=?, updated_utc=? "
                "WHERE task_id=? AND generation=? AND owner_instance_id=?",
                (error[:1000], now, task_id, generation, self.instance_id),
            )
            conn.commit()
        finally:
            conn.close()

    def _set_state(
        self,
        task_id: str,
        generation: int,
        state: str,
        *,
        reason: str | None = None,
        error: str | None = None,
        result: dict[str, Any] | None = None,
        owner_instance: str | None = None,
    ) -> None:
        now = _now()
        owner = owner_instance if owner_instance is not None else self.instance_id
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if result is not None:
                conn.execute(
                    "UPDATE run_state SET state=?, pause_reason=?, last_error=?, "
                    "last_result_json=?, updated_utc=? WHERE task_id=? AND generation=? "
                    "AND owner_instance_id = ?",
                    (state, reason, error, json.dumps(result), now, task_id, generation, owner),
                )
            else:
                conn.execute(
                    "UPDATE run_state SET state=?, pause_reason=?, last_error=?, "
                    "updated_utc=? WHERE task_id=? AND generation=? AND owner_instance_id = ?",
                    (state, reason, error, now, task_id, generation, owner),
                )
            conn.commit()
        finally:
            conn.close()
