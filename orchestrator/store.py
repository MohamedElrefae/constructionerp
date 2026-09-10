"""SQLite job/event authority. JSONL files are write-only derived exports."""

import json
import sqlite3
from pathlib import Path

from core import WorkflowError, atomic_write, canonical, utc


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
        self.conn.close()

    def meta(self, key, default=None):
        row = self.conn.execute("SELECT value FROM workflow_meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_meta(self, key, value):
        with self.conn:
            self.conn.execute(
                "INSERT INTO workflow_meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, canonical(value).decode()),
            )

    def event(self, event_id, kind, payload):
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
        row = self.conn.execute("SELECT * FROM workflow_jobs WHERE job_id=?", (job_id,)).fetchone()
        return dict(json.loads(row["data"]), status=row["status"]) if row else None

    def create_job(self, key, data):
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
        row = self.conn.execute(
            "SELECT data FROM workflow_grants WHERE gate_id=?", (token["gate_id"],)
        ).fetchone()
        if row:
            if row[0] != body:
                raise WorkflowError("Gate already has another grant")
            return
        with self.conn:
            self.conn.execute(
                "INSERT INTO workflow_grants VALUES (?,?,?,?)",
                (token["token_id"], token["gate_id"], "ISSUED", body),
            )

    def grant_for(self, gate):
        row = self.conn.execute("SELECT * FROM workflow_grants WHERE gate_id=?", (gate,)).fetchone()
        return dict(token=json.loads(row["data"]), status=row["status"]) if row else None

    def consume(self, gate):
        with self.conn:
            self.conn.execute("UPDATE workflow_grants SET status='CONSUMED' WHERE gate_id=?", (gate,))

    def reconfigure(self, config, event_id, kind, payload):
        with self.conn:
            self.conn.execute(
                "UPDATE workflow_meta SET value=? WHERE key=?", (canonical(config).decode(), "config")
            )
            self.conn.execute(
                "INSERT INTO workflow_events(event_id,kind,payload,created_utc) VALUES (?,?,?,?)",
                (event_id, kind, canonical(payload).decode(), utc()),
            )

    def complete_grant(self, event_id, gate, payload):
        body = canonical(payload).decode()
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
        atomic_write(path, b"".join(canonical(e) + b"\n" for e in self.events()))

    def backup(self, destination):
        target = sqlite3.connect(destination)
        try:
            self.conn.backup(target)
        finally:
            target.close()

    def integrity(self):
        return self.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
