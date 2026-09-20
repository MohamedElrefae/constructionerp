import json
import sqlite3
import threading
import uuid
from pathlib import Path

from core import WorkflowError, atomic_write, canonical, utc


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._lock:
            self.conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS workflow_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS workflow_events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL,
                kind TEXT NOT NULL, payload TEXT NOT NULL, created_utc TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS workflow_jobs (
                job_id TEXT PRIMARY KEY, logical_key TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS workflow_grants (
                token_id TEXT PRIMARY KEY, gate_id TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL, data TEXT NOT NULL);
        """)
        self.conn.commit()

    def close(self):
        with self._lock:
            self.conn.close()

    def meta(self, key, default=None):
        with self._lock:
            row = self.conn.execute("SELECT value FROM workflow_meta WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else default

    def set_meta(self, key, value):
        with self._lock:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO workflow_meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, canonical(value).decode()),
                )

    def event(self, event_id, kind, payload):
        with self._lock:
            existing = self.conn.execute("SELECT * FROM workflow_events WHERE event_id=?", (event_id,)).fetchone()
            body = canonical(payload).decode()
            if existing:
                if existing["kind"] != kind or existing["payload"] != body:
                    raise WorkflowError("Duplicate event ID with different content")
                return existing["seq"]
            with self.conn:
                cursor = self.conn.execute(
                    "INSERT INTO workflow_events(event_id,kind,payload,created_utc) VALUES (?,?,?,?)",
                    (event_id, kind, body, utc()),
                )
                return cursor.lastrowid

    def events(self, after=0):
        with self._lock:
            return [
                dict(
                    seq=row["seq"],
                    event_id=row["event_id"],
                    kind=row["kind"],
                    payload=json.loads(row["payload"]),
                    created_utc=row["created_utc"],
                )
                for row in self.conn.execute("SELECT * FROM workflow_events WHERE seq>? ORDER BY seq", (after,))
            ]

    def job(self, job_id):
        with self._lock:
            row = self.conn.execute("SELECT * FROM workflow_jobs WHERE job_id=?", (job_id,)).fetchone()
            return dict(json.loads(row["data"]), status=row["status"]) if row else None

    def create_job(self, key, data):
        with self._lock:
            row = self.conn.execute("SELECT job_id FROM workflow_jobs WHERE logical_key=?", (key,)).fetchone()
            if row:
                return self.job(row[0])
            with self.conn:
                self.conn.execute(
                    "INSERT INTO workflow_jobs VALUES (?,?,?,?)",
                    (data["job_id"], key, "CREATED", canonical(data).decode()),
                )
            return self.job(data["job_id"])

    def update_job(self, job_id, status, **updates):
        with self._lock:
            job = self.job(job_id)
            if not job:
                raise WorkflowError("Unknown job")
            job.update(updates)
            job.pop("status")
            with self.conn:
                self.conn.execute(
                    "UPDATE workflow_jobs SET status=?,data=? WHERE job_id=?",
                    (status, canonical(job).decode(), job_id),
                )

    def grant(self, token):
        body = canonical(token).decode()
        with self._lock:
            row = self.conn.execute(
                "SELECT status, data FROM workflow_grants WHERE gate_id=?", (token["gate_id"],)
            ).fetchone()
            if row:
                if row["status"] == "INVALIDATED":
                    with self.conn:
                        self.conn.execute(
                            "UPDATE workflow_grants SET token_id=?, status='ISSUED', data=? WHERE gate_id=?",
                            (token["token_id"], body, token["gate_id"]),
                        )
                    return
                if row["data"] != body:
                    raise WorkflowError("Gate already has another grant")
                return
            with self.conn:
                self.conn.execute(
                    "INSERT INTO workflow_grants VALUES (?,?,?,?)",
                    (token["token_id"], token["gate_id"], "ISSUED", body),
                )

    def grant_for(self, gate):
        with self._lock:
            row = self.conn.execute("SELECT * FROM workflow_grants WHERE gate_id=?", (gate,)).fetchone()
            return dict(token=json.loads(row["data"]), status=row["status"]) if row else None

    def lookup_grant(self, token_id: str) -> dict | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT status, data FROM workflow_grants WHERE token_id = ?", (token_id,)
            ).fetchone()
            if row is None:
                return None
            return {
                "status": row["status"] if isinstance(row, sqlite3.Row) else row[0],
                "data": json.loads(row["data"] if isinstance(row, sqlite3.Row) else row[1]),
            }

    def consume(self, gate):
        with self._lock:
            with self.conn:
                self.conn.execute("UPDATE workflow_grants SET status='CONSUMED' WHERE gate_id=?", (gate,))

    def invalidate_grants(self):
        with self._lock:
            with self.conn:
                rows = self.conn.execute(
                    "SELECT token_id FROM workflow_grants WHERE status IN ('ISSUED', 'RESERVED')"
                ).fetchall()
                invalidated = [r["token_id"] if isinstance(r, sqlite3.Row) else r[0] for r in rows]
                if invalidated:
                    self.conn.execute(
                        "UPDATE workflow_grants SET status='INVALIDATED' WHERE status IN ('ISSUED', 'RESERVED')"
                    )
                return invalidated

    def reconfigure(self, config, event_id, kind, payload, invalidate_grants=False):
        with self._lock:
            with self.conn:
                invalidated = []
                if invalidate_grants:
                    rows = self.conn.execute(
                        "SELECT token_id FROM workflow_grants WHERE status IN ('ISSUED', 'RESERVED')"
                    ).fetchall()
                    invalidated = [r["token_id"] if isinstance(r, sqlite3.Row) else r[0] for r in rows]
                    if invalidated:
                        self.conn.execute(
                            "UPDATE workflow_grants SET status='INVALIDATED' WHERE status IN ('ISSUED', 'RESERVED')"
                        )
                payload["invalidated_grants"] = invalidated
                self.conn.execute(
                    "UPDATE workflow_meta SET value=? WHERE key=?", (canonical(config).decode(), "config")
                )
                self.conn.execute(
                    "INSERT INTO workflow_events(event_id,kind,payload,created_utc) VALUES (?,?,?,?)",
                    (event_id, kind, canonical(payload).decode(), utc()),
                )
                return invalidated

    def adopt_scope_atomic(
        self,
        new_config: dict,
        action_id: str,
        scope_hash: str,
        implementation_stages: list[str],
        candidate_meta: dict,
        request_hash: str,
    ) -> tuple[str, int]:
        with self._lock:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO workflow_meta VALUES ('config', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (canonical(new_config).decode(),),
                )
                self.conn.execute(
                    "UPDATE workflow_grants SET status='INVALIDATED' WHERE status IN ('ISSUED', 'RESERVED')"
                )
                new_event_id = str(uuid.uuid4())
                payload = {
                    "scope_hash": scope_hash,
                    "implementation_stages": implementation_stages,
                    "candidate_meta": candidate_meta,
                    "action_id": action_id,
                    "request_hash": request_hash,
                }
                cursor = self.conn.execute(
                    "INSERT INTO workflow_events(event_id, kind, payload, created_utc) VALUES (?, ?, ?, ?)",
                    (new_event_id, "scope_adopted", canonical(payload).decode(), utc()),
                )
                seq = cursor.lastrowid
                return (new_event_id, seq)

    def complete_grant(self, event_id, gate, payload):
        body = canonical(payload).decode()
        with self._lock:
            with self.conn:
                row = self.conn.execute(
                    "SELECT payload FROM workflow_events WHERE event_id=?", (event_id,)
                ).fetchone()
                if row and row[0] != body:
                    raise WorkflowError("Commit completion correlation mismatch")
                self.conn.execute(
                    "INSERT OR IGNORE INTO workflow_events(event_id,kind,payload,created_utc) VALUES (?,?,?,?)",
                    (event_id, "owner_commit", body, utc()),
                )
                self.conn.execute("UPDATE workflow_grants SET status='CONSUMED' WHERE gate_id=?", (gate,))

    def export_ledger(self, path):
        with self._lock:
            atomic_write(path, b"".join(canonical(e) + b"\n" for e in self.events()))

    def backup(self, destination):
        with self._lock:
            target = sqlite3.connect(destination)
            try:
                self.conn.backup(target)
            finally:
                target.close()

    def integrity(self):
        with self._lock:
            return self.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
