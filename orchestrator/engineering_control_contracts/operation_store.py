"""TEST-ONLY O02 durable operation/correlation prototype.

This module models the *state machine* required for idempotent command receipts,
writer fencing and restart recovery. It is not a production operation store:
SQLite on one host, caller-supplied correlation, and no proof of fsync,
power-loss durability, multi-host consensus or transactional coupling to the
engine's SQLite/checkpoint/Git effects.

It deliberately does NOT import the engine, open a workflow database, launch a
worker or expose a route. Tests must pass a temporary directory.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}\Z")
HASH_RE = re.compile(r"[a-f0-9]{64}\Z")

STATES = ("intent", "completed", "failed", "uncertain")
EFFECT_STATES = ("pending", "completed", "failed", "uncertain")


class OperationError(Exception):
    code = "conflict"


class OperationConflict(OperationError):
    code = "conflict"


class OperationFenced(OperationError):
    code = "conflict"


class OperationNotFound(OperationError):
    code = "not_found"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ValueError(f"Invalid {field}")
    return value


def _hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        raise ValueError(f"Invalid {field}")
    return value


@dataclass(frozen=True)
class Operation:
    operation_id: str
    subject: str
    project_id: str
    work_item_id: str
    operation: str
    target_id: str
    idempotency_key: str
    request_hash: str
    state: str
    effect_state: str
    revision: int
    receipt: dict[str, Any] | None
    job_id: str | None
    attempt: int | None
    runtime_ref: str | None
    writer_epoch: int
    created_utc: str
    updated_utc: str
    uncertain_reason: str | None
    evidence_ref: str | None


SCHEMA = """
CREATE TABLE IF NOT EXISTS control_fence (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    epoch INTEGER NOT NULL,
    instance_id TEXT NOT NULL,
    updated_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operations (
    operation_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    project_id TEXT NOT NULL,
    work_item_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    target_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    state TEXT NOT NULL,
    effect_state TEXT NOT NULL,
    revision INTEGER NOT NULL,
    receipt_json TEXT,
    job_id TEXT,
    attempt INTEGER,
    runtime_ref TEXT,
    writer_epoch INTEGER NOT NULL,
    created_utc TEXT NOT NULL,
    updated_utc TEXT NOT NULL,
    uncertain_reason TEXT,
    evidence_ref TEXT,
    UNIQUE (subject, project_id, work_item_id, operation, target_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_operations_state ON operations(state);
"""


class OperationStore:
    """Single-host test journal. Never point this at a real workflow directory."""

    __test__ = False

    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        if self.path.suffix != ".db":
            raise ValueError("Test operation store requires a .db path")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    @staticmethod
    def _row(row: sqlite3.Row | None) -> Operation | None:
        if row is None:
            return None
        data = dict(row)
        receipt_json = data.pop("receipt_json", None)
        data["receipt"] = json.loads(receipt_json) if receipt_json else None
        return Operation(**data)

    def claim_writer(self, instance_id: str) -> int:
        """Advance the writer epoch. The previously current writer is fenced."""
        _id(instance_id, "instance_id")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT epoch FROM control_fence WHERE id=1").fetchone()
            epoch = (row["epoch"] + 1) if row else 1
            conn.execute(
                "INSERT INTO control_fence (id, epoch, instance_id, updated_utc) VALUES (1, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET epoch=excluded.epoch, "
                "instance_id=excluded.instance_id, updated_utc=excluded.updated_utc",
                (epoch, instance_id, utc()),
            )
            conn.execute("COMMIT")
            return epoch
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def current_epoch(self) -> int | None:
        with self._connection() as conn:
            row = conn.execute("SELECT epoch FROM control_fence WHERE id=1").fetchone()
            return row["epoch"] if row else None

    def _fence(self, conn: sqlite3.Connection, epoch: int) -> None:
        row = conn.execute("SELECT epoch FROM control_fence WHERE id=1").fetchone()
        if row is None or row["epoch"] != epoch:
            raise OperationFenced("Writer epoch is stale")

    def begin(
        self,
        *,
        epoch: int,
        subject: str,
        project_id: str,
        work_item_id: str,
        operation: str,
        target_id: str,
        idempotency_key: str,
        body: dict[str, Any],
        expected_revision: int,
        current_revision: int,
        operation_id: str,
    ) -> Operation:
        """Persist intent before any external effect; matching replay returns it.

        ``current_revision`` is a caller-supplied test stand-in for an
        authoritative revision read. Production must obtain it from the
        authoritative store inside this transaction; it is not trusted merely
        because a caller supplies it.
        """
        for value, field in (
            (subject, "subject"),
            (project_id, "project_id"),
            (work_item_id, "work_item_id"),
            (operation, "operation"),
            (target_id, "target_id"),
            (idempotency_key, "idempotency_key"),
            (operation_id, "operation_id"),
        ):
            _id(value, field)
        if not isinstance(body, dict) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise ValueError("Invalid request or revision")
        if not isinstance(current_revision, int) or current_revision < 0:
            raise ValueError("Invalid current revision")
        request_hash = digest(body)
        now = utc()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._fence(conn, epoch)
            existing = conn.execute(
                "SELECT * FROM operations WHERE subject=? AND project_id=? AND work_item_id=? "
                "AND operation=? AND target_id=? AND idempotency_key=?",
                (subject, project_id, work_item_id, operation, target_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != request_hash or existing["revision"] != expected_revision:
                    raise OperationConflict(
                        "Idempotency key reused with different content or expected revision"
                    )
                conn.execute("COMMIT")
                return self._row(existing)  # Matching replay precedes stale-revision rejection.
            # Fresh intent requires the request's expectation to match the
            # test-supplied current revision, checked in the same write txn.
            # Production must read the authoritative revision itself.
            if expected_revision != current_revision:
                raise OperationConflict("Stale revision precondition")
            conn.execute(
                "INSERT INTO operations (operation_id, subject, project_id, work_item_id, operation, "
                "target_id, idempotency_key, request_hash, state, effect_state, revision, receipt_json, "
                "job_id, attempt, runtime_ref, writer_epoch, created_utc, updated_utc, uncertain_reason, "
                "evidence_ref) VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,?,?,?,NULL,NULL)",
                (
                    operation_id,
                    subject,
                    project_id,
                    work_item_id,
                    operation,
                    target_id,
                    idempotency_key,
                    request_hash,
                    "intent",
                    "pending",
                    expected_revision,
                    epoch,
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
            conn.execute("COMMIT")
            return self._row(row)
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def complete(
        self,
        operation_id: str,
        *,
        epoch: int,
        receipt: dict[str, Any],
        job_id: str | None = None,
        attempt: int | None = None,
        runtime_ref: str | None = None,
    ) -> Operation:
        """Record the observed completed effect. No new job is ever created here."""
        _id(operation_id, "operation_id")
        if not isinstance(receipt, dict):
            raise ValueError("Receipt must be an object")
        for value, field in ((job_id, "job_id"), (runtime_ref, "runtime_ref")):
            if value is not None:
                _id(value, field)
        if attempt is not None and (not isinstance(attempt, int) or attempt < 1):
            raise ValueError("Invalid attempt")
        body = canonical(receipt)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._fence(conn, epoch)
            row = conn.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
            if row is None:
                raise OperationNotFound(operation_id)
            if row["writer_epoch"] != epoch:
                raise OperationFenced("Operation belongs to a fenced writer")
            if row["state"] == "completed":
                if row["receipt_json"] != body.decode():
                    raise OperationConflict("Completion replay carries a different receipt")
                if (
                    (job_id is not None and job_id != row["job_id"])
                    or (attempt is not None and attempt != row["attempt"])
                    or (runtime_ref is not None and runtime_ref != row["runtime_ref"])
                ):
                    raise OperationConflict("Completion replay carries different runtime correlation")
                conn.execute("COMMIT")
                return self._row(row)
            if row["state"] != "intent":
                raise OperationConflict(f"Cannot complete operation in state {row['state']}")
            conn.execute(
                "UPDATE operations SET state='completed', effect_state='completed', receipt_json=?, "
                "job_id=COALESCE(?, job_id), attempt=COALESCE(?, attempt), "
                "runtime_ref=COALESCE(?, runtime_ref), updated_utc=? WHERE operation_id=?",
                (body.decode(), job_id, attempt, runtime_ref, utc(), operation_id),
            )
            updated = conn.execute(
                "SELECT * FROM operations WHERE operation_id=?", (operation_id,)
            ).fetchone()
            conn.execute("COMMIT")
            return self._row(updated)
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def mark_uncertain(self, operation_id: str, *, epoch: int, reason: str) -> Operation:
        _id(operation_id, "operation_id")
        if not isinstance(reason, str) or not 1 <= len(reason) <= 512:
            raise ValueError("Invalid uncertainty reason")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._fence(conn, epoch)
            row = conn.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
            if row is None:
                raise OperationNotFound(operation_id)
            if row["state"] != "intent":
                raise OperationConflict(f"Cannot mark {row['state']} uncertain")
            conn.execute(
                "UPDATE operations SET state='uncertain', effect_state='uncertain', "
                "uncertain_reason=?, updated_utc=? WHERE operation_id=?",
                (reason, utc(), operation_id),
            )
            updated = conn.execute(
                "SELECT * FROM operations WHERE operation_id=?", (operation_id,)
            ).fetchone()
            conn.execute("COMMIT")
            return self._row(updated)
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def recover(self, *, epoch: int, reason: str = "writer restart before completion") -> list[Operation]:
        """After restart, every unfinished intent becomes uncertain; never relaunch."""
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._fence(conn, epoch)
            conn.execute(
                "UPDATE operations SET state='uncertain', effect_state='uncertain', "
                "uncertain_reason=?, updated_utc=? WHERE state='intent'",
                (reason, utc()),
            )
            rows = conn.execute("SELECT * FROM operations WHERE state='uncertain'").fetchall()
            conn.execute("COMMIT")
            return [self._row(row) for row in rows]  # type: ignore[misc]
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def reconcile(
        self,
        operation_id: str,
        *,
        epoch: int,
        outcome: str,
        receipt: dict[str, Any] | None = None,
        job_id: str | None = None,
        evidence_ref: str | None = None,
    ) -> Operation:
        """Finish an uncertain operation from external observation, without relaunch."""
        _id(operation_id, "operation_id")
        if outcome not in ("completed", "failed"):
            raise ValueError("Reconciliation outcome must be completed or failed")
        if outcome == "completed" and not isinstance(receipt, dict):
            raise ValueError("Completed reconciliation requires an observed receipt")
        if outcome == "failed" and receipt is not None:
            raise ValueError("Failed reconciliation cannot carry a receipt")
        for value, field in ((job_id, "job_id"), (evidence_ref, "evidence_ref")):
            if value is not None:
                _id(value, field)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._fence(conn, epoch)
            row = conn.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
            if row is None:
                raise OperationNotFound(operation_id)
            if row["state"] != "uncertain":
                raise OperationConflict(f"Cannot reconcile operation in state {row['state']}")
            if row["writer_epoch"] == epoch:
                raise OperationConflict("Recovery requires a new writer epoch")
            conn.execute(
                "UPDATE operations SET state=?, effect_state=?, receipt_json=?, "
                "job_id=COALESCE(?, job_id), evidence_ref=?, writer_epoch=?, updated_utc=? "
                "WHERE operation_id=?",
                (
                    outcome,
                    outcome,
                    canonical(receipt).decode() if receipt is not None else None,
                    job_id,
                    evidence_ref,
                    epoch,
                    utc(),
                    operation_id,
                ),
            )
            updated = conn.execute(
                "SELECT * FROM operations WHERE operation_id=?", (operation_id,)
            ).fetchone()
            conn.execute("COMMIT")
            return self._row(updated)
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def get(self, operation_id: str) -> Operation:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
        operation = self._row(row)
        if operation is None:
            raise OperationNotFound(operation_id)
        return operation

    def uncertain(self) -> list[Operation]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM operations WHERE state='uncertain' ORDER BY created_utc"
            ).fetchall()
        return [self._row(row) for row in rows]  # type: ignore[misc]
