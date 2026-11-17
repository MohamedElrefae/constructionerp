"""Standalone read-only projection over a disposable engine SQLite store.

TEST-ONLY / UNROUTABLE. This module is intentionally independent of Engine,
Store, TaskRegistry and the dashboard. It opens a checkpoint database read-only,
refuses live WAL/journal sidecars (which cannot be proven side-effect-free or
snapshot-consistent here), and returns only bounded, allowlisted metadata. It is
not a service, route, authentication mechanism or security boundary.

The synthetic API can read/copy data before any independently trusted project
authorization. ReadPrincipal is a freely constructible test object and
TEST_ONLY/ROUTABLE metadata is not enforcement. Never route this module or point
it at real workflow/customer data.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DB_RELATIVE = Path("orchestrator/var/checkpoints.db")
MAX_EVENTS = 100
MAX_PAYLOAD_KEYS = 32
MAX_PAYLOAD_BYTES = 65536
MAX_CONFIG_BYTES = 65536
MAX_CURSOR = 2**63 - 1
MAX_ID_LENGTH = 128
MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024
TEST_ONLY = True
ROUTABLE = False
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
HASH_RE = re.compile(r"[a-f0-9]{64}\Z")
GIT_RE = re.compile(r"[a-f0-9]{40}\Z")
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\Z")
GOVERNED_ROLES = frozenset(
    {"architect", "builder", "reviewer", "verifier", "proposer", "ai-a1", "ai-a2", "ai-a3"}
)
SAFE_STAGES = frozenset({"0", "1", "2", "3", "4"})
SAFE_EVENT_KINDS = frozenset(
    {
        "grant",
        "observation",
        "result",
        "intent",
        "pause",
        "resume",
        "cancel",
        "scope_adopted",
        "role_reconfigured",
        "owner_commit",
        "context_added",
        "seed",
        "escalation",
        "recovery",
    }
)


class ProjectionError(Exception):
    code = "projection_error"


class ProjectionDenied(ProjectionError):
    code = "forbidden"


class ProjectionUnsupported(ProjectionError):
    code = "unsupported"


class ProjectionInvalid(ProjectionError):
    code = "invalid_request"


@dataclass(frozen=True)
class ReadPrincipal:
    """Synthetic test authority; not real T3 authentication."""

    subject: str
    project_id: str
    work_item_id: str
    capabilities: frozenset[str]

    def __post_init__(self):
        for value in (self.subject, self.project_id, self.work_item_id):
            if (
                not isinstance(value, str)
                or not value
                or len(value) > MAX_ID_LENGTH
                or not ID_RE.fullmatch(value)
            ):
                raise ProjectionInvalid("Invalid or oversized principal identity")
        if "read" not in self.capabilities:
            raise ProjectionDenied("Read capability is required")


def _validate_root(root: str | Path) -> Path:
    candidate = Path(root)
    if not candidate.is_absolute():
        raise ProjectionInvalid("Projection root must be absolute")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ProjectionInvalid("Projection root is not accessible") from exc
    if not resolved.is_dir():
        raise ProjectionInvalid("Projection root must be a directory")
    if resolved != candidate:
        # A symlinked/aliased root is not a trusted fixed path.
        raise ProjectionInvalid("Projection root must not be an alias")
    return resolved


def _sidecars(db: Path):
    return tuple(db.with_name(db.name + suffix) for suffix in ("-wal", "-shm", "-journal"))


def _ensure_no_sidecars(db: Path) -> None:
    if any(sidecar.exists() or sidecar.is_symlink() for sidecar in _sidecars(db)):
        raise ProjectionUnsupported(
            "WAL/SHM sidecars appeared during the read-only open; no-write projection is unsupported"
        )


def _database_path(root: Path) -> Path:
    cursor = root
    for part in DB_RELATIVE.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ProjectionInvalid("Symlink in projection path")
    try:
        db = cursor.resolve(strict=True)
    except OSError as exc:
        raise ProjectionUnsupported("Checkpoint database is absent") from exc
    if not db.is_file() or not db.is_relative_to(root):
        raise ProjectionInvalid("Projection database path is invalid")
    if db.parent != (root / "orchestrator/var").resolve():
        raise ProjectionInvalid("Projection database escaped its fixed directory")
    _ensure_no_sidecars(db)
    # A quiescent WAL-configured DB can have no sidecars. Detect the persistent
    # header mode before opening; SQLite can create -wal/-shm on a read-only open.
    try:
        header = db.open("rb").read(100)
    except OSError as exc:
        raise ProjectionUnsupported("Checkpoint header is unreadable") from exc
    if len(header) < 100 or header[:16] != b"SQLite format 3\x00":
        raise ProjectionUnsupported("Checkpoint database header is invalid")
    if header[18] == 2 or header[19] == 2:
        raise ProjectionUnsupported(
            "Checkpoint database is persistently WAL-configured; no-write projection is unsupported"
        )
    if header[18] not in (1, 0) or header[19] not in (1, 0):
        raise ProjectionUnsupported("Unsupported SQLite journal header mode")
    return db


def _connect(db: Path) -> sqlite3.Connection:
    # as_uri percent-encodes URI-special path characters; do not interpolate a raw path.
    conn = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=2000")
    return conn


def _json_object(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ProjectionUnsupported(f"Malformed {label}")
    return value


def _safe_config(config: dict, principal: ReadPrincipal) -> dict:
    project_id = config.get("project_id")
    work_item = config.get("work_item")
    if not isinstance(project_id, str) or not project_id or len(project_id) > MAX_ID_LENGTH:
        raise ProjectionUnsupported("Checkpoint has no authoritative project binding")
    if not isinstance(work_item, str) or not work_item or len(work_item) > MAX_ID_LENGTH:
        raise ProjectionUnsupported("Checkpoint has no bounded work-item binding")
    if project_id != principal.project_id:
        raise ProjectionDenied("Project scope mismatch")
    if work_item != principal.work_item_id:
        raise ProjectionDenied("Work-item scope mismatch")
    stage = config.get("stage")
    if stage is not None and stage not in SAFE_STAGES:
        raise ProjectionUnsupported("Unsupported stage token in checkpoint")
    roles = config.get("roles")
    if not isinstance(roles, dict) or not set(roles) <= GOVERNED_ROLES:
        raise ProjectionUnsupported("Unsupported role set in checkpoint")
    candidate = config.get("candidate")
    candidate_id = candidate.get("candidate_id") if isinstance(candidate, dict) else None
    if candidate_id is not None and not HASH_RE.fullmatch(str(candidate_id)):
        raise ProjectionUnsupported("Malformed candidate binding")
    base_commit = config.get("base_commit")
    if base_commit is not None and not GIT_RE.fullmatch(str(base_commit)):
        raise ProjectionUnsupported("Malformed base commit")
    hashes = {}
    for field in ("plan_revision_hash", "scope_hash", "roles_hash"):
        value = config.get(field)
        if value is not None and not HASH_RE.fullmatch(str(value)):
            raise ProjectionUnsupported(f"Malformed {field}")
        hashes[field] = value
    branch = config.get("branch")
    branch_sha256 = hashlib.sha256(branch.encode()).hexdigest() if isinstance(branch, str) else None
    scope = config.get("scope")
    allowed_paths = scope.get("allowed_paths") if isinstance(scope, dict) else []
    allowed_count = len(allowed_paths) if isinstance(allowed_paths, list) else 0
    return {
        "work_item": principal.work_item_id,
        "project_id": principal.project_id,
        "branch_sha256": branch_sha256,
        "stage": stage,
        "base_commit": base_commit,
        "plan_revision_hash": hashes["plan_revision_hash"],
        "scope_hash": hashes["scope_hash"],
        "roles_hash": hashes["roles_hash"],
        "allowed_path_count": allowed_count,
        "role_names": sorted(roles),
        "candidate_id": candidate_id,
    }


def _payload_summary(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ProjectionUnsupported("Event payload exceeds the projection bound")
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ProjectionUnsupported("Event payload is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ProjectionUnsupported("Event payload is not an object")
    if len(payload) > MAX_PAYLOAD_KEYS:
        raise ProjectionUnsupported("Event payload has too many keys")
    # Values and arbitrary keys are not returned; only a digest and count.
    return {
        "payload_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "payload_key_count": len(payload),
    }


def project_work_item(
    root: str | Path,
    principal: ReadPrincipal,
    *,
    after: int = 0,
    limit: int = 50,
) -> dict:
    """Return bounded work-item metadata and sanitized event summaries."""
    if not isinstance(principal, ReadPrincipal):
        raise ProjectionDenied("Synthetic principal is required")
    if isinstance(after, bool) or not isinstance(after, int) or after < 0 or after > MAX_CURSOR:
        raise ProjectionInvalid("after must be a bounded non-negative integer")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_EVENTS:
        raise ProjectionInvalid(f"limit must be between 1 and {MAX_EVENTS}")

    root_path = _validate_root(root)
    db = _database_path(root_path)
    try:
        conn = _connect(db)
    except sqlite3.Error as exc:
        raise ProjectionUnsupported("Checkpoint database is not readable") from exc
    try:
        # A writer can change journal mode between the precheck and this open.
        # SQLite may create sidecars during the open; fail closed, but do not
        # pretend the no-write guarantee survived the race.
        _ensure_no_sidecars(db)
        conn.execute("BEGIN")
        _ensure_no_sidecars(db)
        try:
            config_row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
        except sqlite3.Error as exc:
            raise ProjectionUnsupported("Checkpoint metadata is unavailable") from exc
        config_raw = config_row["value"] if config_row else None
        if config_raw is None or len(config_raw.encode("utf-8")) > MAX_CONFIG_BYTES:
            raise ProjectionUnsupported("Checkpoint has no bounded config")
        try:
            config = json.loads(config_raw)
        except (TypeError, ValueError) as exc:
            raise ProjectionUnsupported("Checkpoint config is corrupt") from exc
        config = _json_object(config, "checkpoint config")

        projection = _safe_config(config, principal)
        rows = conn.execute(
            "SELECT seq, event_id, kind, length(CAST(payload AS BLOB)) AS payload_bytes, "
            "created_utc FROM workflow_events "
            "WHERE seq > ? ORDER BY seq LIMIT ?",
            (after, limit + 1),
        ).fetchall()
        events = []
        truncated = len(rows) > limit
        for row in rows[:limit]:
            if not ID_RE.fullmatch(str(row["event_id"])):
                raise ProjectionUnsupported("Malformed event ID")
            if row["kind"] not in SAFE_EVENT_KINDS:
                raise ProjectionUnsupported("Unsupported event kind")
            if not TIMESTAMP_RE.fullmatch(str(row["created_utc"])):
                raise ProjectionUnsupported("Malformed event timestamp")
            if row["payload_bytes"] > MAX_PAYLOAD_BYTES:
                raise ProjectionUnsupported("Event payload exceeds the projection bound")
            payload_row = conn.execute(
                "SELECT payload FROM workflow_events WHERE seq=?", (row["seq"],)
            ).fetchone()
            if payload_row is None:
                raise ProjectionUnsupported("Event disappeared during projection")
            summary = _payload_summary(payload_row["payload"])
            events.append(
                {
                    "seq": row["seq"],
                    "event_id": row["event_id"],
                    "kind": row["kind"],
                    "created_utc": row["created_utc"],
                    **summary,
                }
            )
        _ensure_no_sidecars(db)
        return {
            "work_item": projection,
            "events": events,
            "next_cursor": events[-1]["seq"] if events else after,
            "truncated": truncated,
            "source": "sqlite_workflow_meta_and_events",
            "authority": "synthetic_test_principal",
        }
    finally:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        conn.close()


def project_work_item_snapshot(
    root: str | Path,
    principal: ReadPrincipal,
    *,
    after: int = 0,
    limit: int = 50,
) -> dict:
    """Copy a verified synthetic DB to a private temp dir and read only the copy.

    TEST-ONLY. The source must be a quiescent rollback-mode DB with no sidecars.
    The copy is not authority, freshness proof, or a production snapshot. Source
    metadata/descriptor identity is checked before/after, but same-UID adversarial
    writes cannot be proven excluded without OS isolation.
    """
    root_path = _validate_root(root)
    source = _database_path(root_path)
    try:
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ProjectionUnsupported("Synthetic source cannot be opened") from exc
    try:
        before = os.fstat(fd)
        if before.st_size > MAX_SNAPSHOT_BYTES:
            raise ProjectionUnsupported("Synthetic source exceeds the snapshot bound")
        with tempfile.TemporaryDirectory(prefix="control-projection-") as temp:
            copy_root = Path(temp)
            var = copy_root / "orchestrator" / "var"
            var.mkdir(parents=True, mode=0o700)
            copy_db = var / "checkpoints.db"
            with copy_db.open("wb") as destination:
                os.chmod(copy_db, 0o600)
                copied = 0
                while True:
                    chunk = os.read(fd, 1024 * 1024)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > MAX_SNAPSHOT_BYTES:
                        raise ProjectionUnsupported(
                            "Synthetic source grew beyond the snapshot bound during copy"
                        )
                    destination.write(chunk)
            after_stat = os.fstat(fd)
            identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            identity_after = (
                after_stat.st_dev,
                after_stat.st_ino,
                after_stat.st_size,
                after_stat.st_mtime_ns,
            )
            if identity_before != identity_after:
                raise ProjectionUnsupported("Synthetic source changed during snapshot")
            # Re-check the source header/sidecars after the copy. A concurrent
            # writer can still change them after this check; no race-free proof.
            _database_path(root_path)
            return project_work_item(copy_root, principal, after=after, limit=limit)
    finally:
        os.close(fd)
