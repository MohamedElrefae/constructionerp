"""Task Registry for the Civil Engineer Dashboard.

Provides self-contained path containment validation, read-only SQLite inspection,
Git worktree branch verification, and task registration persistence.
Zero imports from orchestrator.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from typing import Any

from dashboard.config import BASE_ALLOWED_ROOTS, REGISTRY_DB_PATH, WORKTREES_ROOT


def validate_and_resolve_checkpoint_db(
    base_root: Path | str, candidate_worktree: Path | str
) -> tuple[Path, Path]:
    """Validate that candidate_worktree is strictly contained within base_root,
    contains zero symlinks in any path component, and contains a valid checkpoints.db.

    Rejects parent traversal ('..') BEFORE normalization.
    Inspects original path components for symlinks BEFORE resolution.
    """
    base = Path(base_root).resolve()

    cand_str = str(candidate_worktree).strip()
    if not cand_str:
        raise ValueError("Worktree path cannot be empty")

    # 1. Reject parent traversal ('..') BEFORE any normalization
    raw_parts = [p for p in cand_str.replace("\\", "/").split("/") if p]
    if any(part == ".." for part in raw_parts):
        raise ValueError(
            f"Parent directory traversal ('..') rejected in worktree path: {candidate_worktree}"
        )

    cand = Path(cand_str)
    if not cand.is_absolute():
        cand = base / cand

    # 2. Lexical containment check under allowed base root
    norm_base_str = str(base)
    norm_cand_str = os.path.normpath(str(cand))

    if not (norm_cand_str.startswith(norm_base_str + os.sep) or norm_cand_str == norm_base_str):
        raise ValueError(
            f"Worktree path lexically escapes allowed base directory {base}: {candidate_worktree}"
        )

    if norm_cand_str == norm_base_str:
        raise ValueError(f"Worktree path cannot be the base directory itself: {candidate_worktree}")

    norm_cand = Path(norm_cand_str)
    rel_parts = norm_cand.relative_to(base).parts

    # 3. Inspect EVERY original path component for symlinks BEFORE resolution
    # Strictly rejects in-root symlink aliases (e.g. symlink -> target inside root)
    current = base
    for part in rel_parts:
        current = current / part
        if os.path.islink(current):
            raise ValueError(f"Symlink rejected in worktree path component: {current}")

    # 4. Check intermediate components down to checkpoints.db
    db_rel = Path("orchestrator") / "var" / "checkpoints.db"
    for part in db_rel.parts:
        current = current / part
        if os.path.islink(current):
            raise ValueError(f"Symlink rejected in checkpoints path component: {current}")

    db_full_path = current
    if not db_full_path.is_file():
        raise FileNotFoundError(f"Checkpoints database not found: {db_full_path}")

    # 5. Canonical resolution verification
    if norm_cand.resolve() != norm_cand:
        raise ValueError(f"Worktree path contains aliased divergence: {norm_cand}")
    if db_full_path.resolve() != db_full_path:
        raise ValueError(f"Checkpoints path contains aliased divergence: {db_full_path}")

    return norm_cand, db_full_path


def get_actual_git_branch(worktree_path: Path | str) -> str:
    """Obtain the actual checked-out Git branch in the worktree."""
    worktree = Path(worktree_path)
    res = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        timeout=5.0,
    )
    if res.returncode != 0 or res.stdout.strip() != "true":
        raise ValueError(f"Path is not a valid Git worktree: {worktree_path}")

    branch_res = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        timeout=5.0,
    )
    if branch_res.returncode != 0:
        raise ValueError(f"Failed to resolve Git branch for worktree: {worktree_path}")

    branch = branch_res.stdout.strip()
    if not branch:
        raise ValueError(f"Empty branch resolved for worktree: {worktree_path}")
    return branch


def inspect_readonly_checkpoint_db(db_path: Path | str) -> dict[str, Any]:
    """Inspect checkpoints database in read-only mode and verify integrity and metadata."""
    uri = f"file:{Path(db_path).resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    try:
        cur = conn.cursor()
        # Verify integrity
        cur.execute("PRAGMA integrity_check;")
        row = cur.fetchone()
        if not row or row[0] != "ok":
            raise ValueError(f"Checkpoints database integrity check failed: {row}")

        # Check required table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_meta';")
        if not cur.fetchone():
            raise ValueError("Checkpoints database missing required 'workflow_meta' table")

        cur.execute("SELECT key, value FROM workflow_meta;")
        meta_rows = dict(cur.fetchall())
        work_item = meta_rows.get("work_item")
        task_branch = meta_rows.get("task_branch")

        if not work_item and "config" in meta_rows:
            try:
                cfg = json.loads(meta_rows["config"])
                if isinstance(cfg, dict):
                    work_item = cfg.get("work_item")
                    task_branch = task_branch or cfg.get("branch")
            except Exception:
                pass

        if not work_item:
            raise ValueError("Checkpoints database workflow_meta missing 'work_item'")

        return {
            "work_item": work_item,
            "task_branch": task_branch,
            "meta": meta_rows,
        }
    finally:
        conn.close()


def validate_and_bind_canonical_registry(candidate_path: Path | str, is_test_mode: bool = False) -> Path:
    """Validate full ancestor chain ownership and permissions for registry.db."""
    raw_str = str(candidate_path).strip()
    if any(part == ".." for part in raw_str.replace("\\", "/").split("/")):
        raise ValueError(f"Parent traversal ('..') prohibited in registry path: {candidate_path}")

    target = Path(raw_str)
    if not target.is_absolute():
        raise ValueError(f"Registry path must be absolute: {candidate_path}")

    current = Path(target.parts[0])  # Path("/")
    for part in target.parts[1:]:
        current = current / part
        if os.path.islink(current):
            raise ValueError(f"Symlink rejected in registry path component: {current}")

        is_var_dir = (current == target.parent)
        is_db_file = (current == target)

        if current.exists():
            st = current.stat()
            if is_var_dir:
                if st.st_uid != os.geteuid():
                    raise ValueError(f"Registry directory owner {st.st_uid} != expected {os.geteuid()}")
                if (st.st_mode & 0o077) != 0:
                    raise ValueError(f"Registry directory {current} must have mode 0700 (no group/world access)")
            elif is_db_file:
                if st.st_uid != os.geteuid():
                    raise ValueError(f"Registry database owner {st.st_uid} != expected {os.geteuid()}")
                if (st.st_mode & 0o077) != 0:
                    raise ValueError(f"Registry database {current} must have mode 0600 (no group/world access)")
            else:
                if is_test_mode and current in (Path("/tmp"), Path("/run"), Path("/var"), Path("/var/tmp")):
                    pass
                else:
                    if st.st_uid not in (0, os.geteuid()):
                        raise ValueError(f"Ancestor directory {current} owner {st.st_uid} is neither root nor current user {os.geteuid()}")
                    if (st.st_mode & 0o022) != 0:
                        raise ValueError(f"Ancestor directory {current} must not be group/world-writable (mode {oct(st.st_mode)})")
        else:
            if not is_db_file:
                raise FileNotFoundError(f"Registry path component does not exist: {current}")

    return current.resolve()


def init_registry_db(db_path: Path | str = REGISTRY_DB_PATH) -> None:
    """Initialize the dashboard's internal SQLite registry database."""
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except Exception:
        pass
    conn = sqlite3.connect(str(p))
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS registered_tasks (
                    task_id TEXT PRIMARY KEY,
                    work_item TEXT NOT NULL,
                    worktree_path TEXT NOT NULL UNIQUE,
                    task_branch TEXT NOT NULL,
                    registered_utc TEXT NOT NULL,
                    last_polled_utc TEXT,
                    cached_status TEXT NOT NULL DEFAULT 'DRAFT',
                    cached_stage TEXT NOT NULL DEFAULT 'plan'
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS action_log (
                    action_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    idempotency_key TEXT,
                    request_hash TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    response_json TEXT,
                    correlation_id TEXT,
                    executor_instance_id TEXT NOT NULL,
                    executor_pid INTEGER NOT NULL,
                    executor_start_time INTEGER NOT NULL,
                    child_pid INTEGER,
                    child_pgid INTEGER,
                    child_start_time INTEGER,
                    fencing_token INTEGER NOT NULL DEFAULT 0,
                    heartbeat_utc TEXT,
                    error_message TEXT,
                    session_memory_entry TEXT,
                    created_utc TEXT NOT NULL,
                    updated_utc TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_records (
                    review_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    gate_id TEXT NOT NULL,
                    plan_revision_hash TEXT NOT NULL,
                    scope_hash TEXT NOT NULL,
                    roles_hash TEXT NOT NULL,
                    content_fingerprint TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    reviewed_by TEXT NOT NULL,
                    used_utc TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_context_provenance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    "exists" INTEGER NOT NULL,
                    is_mandatory INTEGER NOT NULL,
                    commit_sha TEXT,
                    content_sha256 TEXT,
                    captured_utc TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action_log_task_id ON action_log(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action_log_idempotency ON action_log(idempotency_key);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action_log_state ON action_log(state);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_review_records_task_gate ON review_records(task_id, gate_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_provenance_task_id ON task_context_provenance(task_id);")
    finally:
        conn.close()

    try:
        os.chmod(str(p), 0o600)
    except Exception:
        pass


class TaskRegistry:
    """Registry managing local worktree registrations."""

    def __init__(
        self,
        db_path: Path | str = REGISTRY_DB_PATH,
        allowed_roots: list[Path] | None = None,
    ):
        self.db_path = Path(db_path)
        self.allowed_roots = allowed_roots or BASE_ALLOWED_ROOTS
        init_registry_db(self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def register_existing_worktree(self, candidate_path: str | Path) -> dict[str, Any]:
        """Validate an existing worktree, inspect its checkpoints DB, and register it."""
        # Find which allowed base root contains the candidate
        cand_p = Path(candidate_path)
        matched_base: Path | None = None
        for base in self.allowed_roots:
            try:
                norm_cand = Path(os.path.normpath(str(cand_p if cand_p.is_absolute() else base / cand_p)))
                if norm_cand.is_relative_to(base) and norm_cand != base:
                    matched_base = base
                    break
            except ValueError:
                continue

        if not matched_base:
            raise ValueError(
                f"Worktree path does not reside within any allowed root: {candidate_path}"
            )

        worktree_path, db_path = validate_and_resolve_checkpoint_db(matched_base, candidate_path)
        actual_branch = get_actual_git_branch(worktree_path)
        db_info = inspect_readonly_checkpoint_db(db_path)

        # Validate task branch matches if recorded in DB
        recorded_branch = db_info.get("task_branch")
        if recorded_branch and recorded_branch != actual_branch:
            raise ValueError(
                f"Git branch mismatch: checked out '{actual_branch}' but checkpoints.db recorded '{recorded_branch}'"
            )

        work_item = db_info["work_item"]
        task_id = worktree_path.name
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO registered_tasks (
                        task_id, work_item, worktree_path, task_branch, registered_utc, cached_status, cached_stage
                    ) VALUES (?, ?, ?, ?, ?, 'INITIALIZED', 'plan')
                    ON CONFLICT(task_id) DO UPDATE SET
                        work_item=excluded.work_item,
                        worktree_path=excluded.worktree_path,
                        task_branch=excluded.task_branch;
                    """,
                    (task_id, work_item, str(worktree_path), actual_branch, now_iso),
                )
        finally:
            conn.close()

        return {
            "task_id": task_id,
            "work_item": work_item,
            "worktree_path": str(worktree_path),
            "task_branch": actual_branch,
            "registered_utc": now_iso,
        }

    def list_tasks(self) -> list[dict[str, Any]]:
        """Return all registered tasks."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT task_id, work_item, worktree_path, task_branch, registered_utc, last_polled_utc, cached_status, cached_stage FROM registered_tasks ORDER BY registered_utc DESC;"
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Get a single registered task by task_id."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT task_id, work_item, worktree_path, task_branch, registered_utc, last_polled_utc, cached_status, cached_stage FROM registered_tasks WHERE task_id = ?;",
                (task_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_task_cache(
        self, task_id: str, status: str, stage: str
    ) -> None:
        """Update cached status and stage from polling results."""
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE registered_tasks
                    SET cached_status = ?, cached_stage = ?, last_polled_utc = ?
                    WHERE task_id = ?;
                    """,
                    (status, stage, now_iso, task_id),
                )
        finally:
            conn.close()

    def unregister_task(self, task_id: str) -> bool:
        """Unregister a task."""
        conn = self._get_connection()
        try:
            with conn:
                cur = conn.execute("DELETE FROM registered_tasks WHERE task_id = ?;", (task_id,))
                return cur.rowcount > 0
        finally:
            conn.close()

    def get_action(self, action_id: str) -> dict[str, Any] | None:
        """Retrieve an action_log record by action_id."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM action_log WHERE action_id = ?;", (action_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_action_by_idempotency(self, idempotency_key: str) -> dict[str, Any] | None:
        """Retrieve an action_log record by idempotency_key."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM action_log WHERE idempotency_key = ?;", (idempotency_key,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def create_review_record(
        self,
        task_id: str,
        gate_id: str,
        plan_revision_hash: str,
        scope_hash: str,
        roles_hash: str,
        content_fingerprint: str,
        reviewed_by: str,
    ) -> dict[str, Any]:
        """Create a new content-bound review record."""
        import uuid
        review_id = f"rev-{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO review_records (
                        review_id, task_id, gate_id, plan_revision_hash, scope_hash,
                        roles_hash, content_fingerprint, created_utc, reviewed_by, used_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL);
                    """,
                    (
                        review_id,
                        task_id,
                        gate_id,
                        plan_revision_hash,
                        scope_hash,
                        roles_hash,
                        content_fingerprint,
                        now_iso,
                        reviewed_by,
                    ),
                )
        finally:
            conn.close()

        return {
            "review_id": review_id,
            "task_id": task_id,
            "gate_id": gate_id,
            "plan_revision_hash": plan_revision_hash,
            "scope_hash": scope_hash,
            "roles_hash": roles_hash,
            "content_fingerprint": content_fingerprint,
            "created_utc": now_iso,
            "reviewed_by": reviewed_by,
            "used_utc": None,
        }

    def get_review_record(self, review_id: str) -> dict[str, Any] | None:
        """Retrieve a review record by review_id."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM review_records WHERE review_id = ?;", (review_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_active_review_for_gate(self, task_id: str, gate_id: str) -> dict[str, Any] | None:
        """Retrieve active (unused) review record for a task and gate."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT * FROM review_records
                WHERE task_id = ? AND gate_id = ? AND used_utc IS NULL
                ORDER BY created_utc DESC LIMIT 1;
                """,
                (task_id, gate_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_reviews_for_task(self, task_id: str) -> list[dict[str, Any]]:
        """Retrieve all review records for a task ordered by created_utc ASC."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM review_records WHERE task_id = ? ORDER BY created_utc ASC;",
                (task_id,),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def mark_review_used(self, review_id: str) -> None:
        """Mark a review record as used upon plan approval."""
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    "UPDATE review_records SET used_utc = ? WHERE review_id = ?;",
                    (now_iso, review_id),
                )
        finally:
            conn.close()

    def record_context_provenance(self, task_id: str, provenance_items: list[dict[str, Any]]) -> None:
        """Persist snapshot of context file provenance."""
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            with conn:
                for item in provenance_items:
                    conn.execute(
                        """
                        INSERT INTO task_context_provenance (
                            task_id, file_path, "exists", is_mandatory, commit_sha, content_sha256, captured_utc
                        ) VALUES (?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            task_id,
                            item.get("path") or item.get("file_path"),
                            1 if item.get("exists") else 0,
                            1 if item.get("is_mandatory") else 0,
                            item.get("commit_sha"),
                            item.get("sha256") or item.get("content_sha256"),
                            now_iso,
                        ),
                    )
        finally:
            conn.close()

    def get_context_provenance(self, task_id: str) -> list[dict[str, Any]]:
        """Retrieve context provenance records for a task."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT file_path, "exists", is_mandatory, commit_sha, content_sha256, captured_utc
                FROM task_context_provenance
                WHERE task_id = ?
                ORDER BY id ASC;
                """,
                (task_id,),
            )
            return [
                {
                    "path": row["file_path"],
                    "exists": bool(row["exists"]),
                    "is_mandatory": bool(row["is_mandatory"]),
                    "commit_sha": row["commit_sha"],
                    "sha256": row["content_sha256"],
                    "captured_utc": row["captured_utc"],
                }
                for row in cur.fetchall()
            ]
        finally:
            conn.close()
