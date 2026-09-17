"""Recoverable Task Bootstrapper with Ownership Verification and Fencing.

Implements non-overwriting bootstrap, atomic CAS recovery claiming,
pre-mutation manifest logging, process identity verification (PID + start time),
git ancestry checks, and exact initial checkpoint contract validation.
"""

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid
from typing import Any

from dashboard.config import (
    CANONICAL_REGISTRY_PATH,
    LOCKS_DIR,
    ORCHESTRATOR_PYTHON,
    REPO_ROOT,
    WORKTREES_ROOT,
)
from dashboard.process import (
    get_process_start_time,
    is_process_alive_with_start_time,
    spawn_supervised_child,
)
from dashboard.registry import TaskRegistry, validate_and_bind_canonical_registry
from dashboard.subprocess_client import run_action


class BootstrapConflictError(Exception):
    """Raised when bootstrap encounters conflict, active lock, or divergence."""


class BootstrapForbiddenError(Exception):
    """Raised when bootstrap is attempted on forbidden targets (e.g. Stage 4)."""


def _normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    """Extract user-defined baseline config keys for deterministic hashing."""
    keys = (
        "root",
        "work_item",
        "branch",
        "base_commit",
        "stages",
        "scope",
        "read_only_context_paths",
        "plan_path",
        "plan_revision_hash",
        "roles",
        "budget",
    )
    return {k: config[k] for k in sorted(keys) if k in config}


def _config_digest(config: dict[str, Any]) -> str:
    norm = _normalize_config(config)
    return hashlib.sha256(json.dumps(norm, sort_keys=True).encode("utf-8")).hexdigest()


def _check_bootstrap_fence(
    registry: TaskRegistry,
    action_id: str,
    fencing_token: int,
    executor_instance_id: str,
) -> None:
    """Verify fence condition under action lock before executing any bootstrap mutation."""
    conn = registry._get_connection()
    try:
        row = conn.execute(
            """
            SELECT fencing_token, executor_instance_id, state
            FROM action_log
            WHERE action_id = ?;
            """,
            (action_id,),
        ).fetchone()
        if not row:
            raise BootstrapConflictError(f"Bootstrap action {action_id} not found in action_log")
        cur_token, cur_inst, cur_state = row[0], row[1], row[2]
        if cur_token != fencing_token or cur_inst != executor_instance_id or cur_state not in ("EXECUTING", "RECOVERING"):
            raise BootstrapConflictError(
                f"Fencing validation failed before mutation for bootstrap action {action_id}: "
                f"expected token={fencing_token}, instance={executor_instance_id}, state in (EXECUTING, RECOVERING); "
                f"found token={cur_token}, instance={cur_inst}, state={cur_state}"
            )
    finally:
        conn.close()


async def bootstrap_task(
    work_item: str,
    user_brief: str,
    target_path: Path | str | None = None,
    task_id: str | None = None,
    base_ref: str = "HEAD",
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
    executor_instance_id: str | None = None,
    registry: TaskRegistry | None = None,
    is_test_mode: bool = False,
) -> dict[str, Any]:
    """Bootstrap a new task worktree or recover an interrupted bootstrap."""
    if not work_item or not user_brief:
        raise ValueError("work_item and user_brief are required")

    # Authoritative Stage 4 rejection
    if work_item == "erp-arabic-bilingual-data":
        raise BootstrapForbiddenError(
            "Stage 4 erp-arabic-bilingual-data is parked and prohibited from dashboard execution"
        )

    registry = registry or TaskRegistry()
    executor_instance_id = executor_instance_id or f"inst-{uuid.uuid4().hex[:8]}"
    executor_pid = os.getpid()
    executor_start_time = get_process_start_time(executor_pid) or 0

    request_hash = hashlib.sha256(
        f"{work_item}:{user_brief.strip()}:{base_ref}".encode("utf-8")
    ).hexdigest()

    action_id: str | None = None
    existing_row = None
    if idempotency_key:
        existing_row = registry.get_action_by_idempotency(idempotency_key)
        if existing_row:
            action_id = existing_row["action_id"]

    if not action_id:
        action_id = f"act-bootstrap-{uuid.uuid4().hex[:8]}"

    # Universal Lock Hierarchy: Acquire Action Lock FIRST
    locks_dir = (registry.db_path.parent / "locks") if registry and getattr(registry, "db_path", None) else LOCKS_DIR
    locks_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(locks_dir, 0o700)
    except Exception:
        pass
    lock_file_path = locks_dir / f"bootstrap_{action_id}.lock"
    lock_fd = os.open(str(lock_file_path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BootstrapConflictError(
                f"Bootstrap action {action_id} is currently locked by another process"
            ) from exc

        # Under Action Lock: Re-inspect idempotency state
        if idempotency_key:
            existing_row = registry.get_action_by_idempotency(idempotency_key)

        if existing_row:
            # Validate request hash matches
            if existing_row["request_hash"] != request_hash:
                raise BootstrapConflictError(
                    f"Idempotency key {idempotency_key!r} reused with differing request content"
                )

            state = existing_row["state"]
            if state == "COMPLETE":
                if existing_row["response_json"]:
                    return json.loads(existing_row["response_json"])
                task = registry.get_task(existing_row["task_id"])
                if task:
                    return task
                raise BootstrapConflictError("Task marked COMPLETE but registration missing")

            if state == "RECONCILIATION_REQUIRED":
                raise BootstrapConflictError(
                    f"Task initialization requires manual reconciliation: {existing_row.get('error_message')}"
                )

            if state in ("EXECUTING", "RECOVERING"):
                prev_pid = existing_row["executor_pid"]
                prev_start = existing_row["executor_start_time"]
                child_pid = existing_row["child_pid"]
                child_start = existing_row["child_start_time"]

                parent_alive = is_process_alive_with_start_time(prev_pid, prev_start)
                child_alive = is_process_alive_with_start_time(child_pid, child_start)

                if parent_alive or child_alive:
                    raise BootstrapConflictError(
                        f"Bootstrap action is currently active (parent_alive={parent_alive}, child_alive={child_alive})"
                    )

            # Initiate recovery claiming (CAS)
            old_fencing_token = existing_row["fencing_token"]
            now_iso = datetime.now(timezone.utc).isoformat()
            conn = registry._get_connection()
            try:
                with conn:
                    cur = conn.execute(
                        """
                        UPDATE action_log
                        SET state = 'RECOVERING',
                            fencing_token = fencing_token + 1,
                            executor_instance_id = ?,
                            executor_pid = ?,
                            executor_start_time = ?,
                            updated_utc = ?
                        WHERE action_id = ?
                          AND state IN ('EXECUTING', 'RECOVERING', 'EXECUTING_UNKNOWN', 'FAILED')
                          AND fencing_token = ?;
                        """,
                        (
                            executor_instance_id,
                            executor_pid,
                            executor_start_time,
                            now_iso,
                            action_id,
                            old_fencing_token,
                        ),
                    )
                    if cur.rowcount == 0:
                        raise BootstrapConflictError("Concurrent recovery claim failed or state changed")
            finally:
                conn.close()

            new_fencing_token = old_fencing_token + 1
            manifest = json.loads(existing_row["manifest_json"])
            return await _execute_bootstrap_recovery(
                action_id=action_id,
                fencing_token=new_fencing_token,
                executor_instance_id=executor_instance_id,
                manifest=manifest,
                lock_fd=lock_fd,
                registry=registry,
                is_test_mode=is_test_mode,
            )

        # Genuinely new bootstrap request
        target = Path(target_path or (WORKTREES_ROOT / (task_id or f"task-{work_item}-{uuid.uuid4().hex[:8]}"))).resolve()
        task_id = task_id or target.name
        branch_name = f"task/{work_item}-{task_id[-8:]}"

        # Strict Non-Overwriting Preconditions
        if target.exists():
            raise BootstrapConflictError(f"Target worktree path already exists: {target}")

        branch_check = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--verify", f"refs/heads/{branch_name}"],
            capture_output=True,
            text=True,
        )
        if branch_check.returncode == 0:
            raise BootstrapConflictError(f"Branch {branch_name} already exists in git repository")

        # Resolve Git Common Dir and Base SHA
        git_common_dir = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--git-common-dir"],
            text=True,
        ).strip()
        if not Path(git_common_dir).is_absolute():
            git_common_dir = str((REPO_ROOT / git_common_dir).resolve())

        resolved_base_sha = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", base_ref],
            text=True,
        ).strip()

        brief_content_sha256 = hashlib.sha256(user_brief.encode("utf-8")).hexdigest()

        base_config = {
            "root": str(target),
            "work_item": work_item,
            "branch": branch_name,
            "base_commit": resolved_base_sha,
            "stages": ["plan"],
            "scope": {
                "allowed_paths": [f"docs/ai/work-items/{work_item}/**"],
            },
            "read_only_context_paths": [
                "AGENTS.md",
                "SESSION_MEMORY.md",
                "docs/ai/SCHEMA_FACTS.md",
                "docs/ai/CODING_PATTERNS.md",
                "docs/ai/CONTEXT_INDEX.md",
            ],
            "plan_path": f"docs/ai/work-items/{work_item}/owner-brief.md",
            "plan_revision_hash": brief_content_sha256,
            "roles": {},
            "budget": 200,
        }
        base_config_digest = _config_digest(base_config)

        manifest = {
            "work_item": work_item,
            "task_id": task_id,
            "target_path": str(target),
            "git_common_dir": git_common_dir,
            "branch_name": branch_name,
            "resolved_base_sha": resolved_base_sha,
            "brief_commit_sha": None,
            "brief_content_sha256": brief_content_sha256,
            "base_config_digest": base_config_digest,
        }

        # Persist Pre-Mutation Manifest in action_log
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = registry._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO action_log (
                        action_id, task_id, action_type, state, idempotency_key,
                        request_hash, manifest_json, response_json, correlation_id,
                        executor_instance_id, executor_pid, executor_start_time,
                        child_pid, child_pgid, child_start_time, fencing_token,
                        heartbeat_utc, error_message, session_memory_entry,
                        created_utc, updated_utc
                    ) VALUES (
                        ?, ?, 'bootstrap', 'EXECUTING', ?,
                        ?, ?, NULL, ?,
                        ?, ?, ?,
                        NULL, NULL, NULL, 1,
                        ?, NULL, NULL,
                        ?, ?
                    );
                    """,
                    (
                        action_id,
                        task_id,
                        idempotency_key,
                        request_hash,
                        json.dumps(manifest),
                        correlation_id,
                        executor_instance_id,
                        executor_pid,
                        executor_start_time,
                        now_iso,
                        now_iso,
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        # Step 1: Create Git Worktree via Supervised Child (fenced)
        _check_bootstrap_fence(registry, action_id, 1, executor_instance_id)
        worktree_cmd = [
            "git",
            "-C",
            str(REPO_ROOT),
            "worktree",
            "add",
            "-b",
            branch_name,
            str(target),
            resolved_base_sha,
        ]
        proc = spawn_supervised_child(worktree_cmd, lock_fd=lock_fd)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            err_text = (stderr or stdout or b"").decode()
            _mark_failed(registry, action_id, 1, executor_instance_id, f"git worktree add failed: {err_text}")
            raise BootstrapConflictError(f"Failed to create git worktree: {err_text}")

        # Step 2: Write owner brief (fenced)
        _check_bootstrap_fence(registry, action_id, 1, executor_instance_id)
        brief_dir = target / f"docs/ai/work-items/{work_item}"
        brief_dir.mkdir(parents=True, exist_ok=True)
        brief_file = brief_dir / "owner-brief.md"
        brief_file.write_text(user_brief, encoding="utf-8")

        # Step 3: Commit owner brief (fenced)
        _check_bootstrap_fence(registry, action_id, 1, executor_instance_id)
        add_proc = spawn_supervised_child(["git", "-C", str(target), "add", str(brief_file)], lock_fd=lock_fd)
        add_proc.communicate()
        commit_proc = spawn_supervised_child(
            ["git", "-C", str(target), "commit", "-m", f"docs(brief): owner brief for {work_item}"],
            lock_fd=lock_fd,
        )
        commit_proc.communicate()
        if commit_proc.returncode != 0:
            _mark_failed(registry, action_id, 1, executor_instance_id, "git commit owner brief failed")
            raise BootstrapConflictError("Failed to commit owner brief")

        brief_commit_sha = subprocess.check_output(
            ["git", "-C", str(target), "rev-parse", "HEAD"], text=True
        ).strip()
        manifest["brief_commit_sha"] = brief_commit_sha
        base_config["base_commit"] = brief_commit_sha
        manifest["base_config_digest"] = _config_digest(base_config)

        # Update manifest with commit SHA (bound to active fence)
        _check_bootstrap_fence(registry, action_id, 1, executor_instance_id)
        conn = registry._get_connection()
        try:
            with conn:
                cur = conn.execute(
                    """
                    UPDATE action_log
                    SET manifest_json = ?, updated_utc = ?
                    WHERE action_id = ?
                      AND fencing_token = 1
                      AND executor_instance_id = ?
                      AND state = 'EXECUTING';
                    """,
                    (json.dumps(manifest), datetime.now(timezone.utc).isoformat(), action_id, executor_instance_id),
                )
                if cur.rowcount == 0:
                    raise BootstrapConflictError(f"Fence lost while updating manifest for action {action_id}")
        finally:
            conn.close()

        # Step 4: Run Initialize Subprocess (fenced)
        _check_bootstrap_fence(registry, action_id, 1, executor_instance_id)
        init_res = await run_action(
            target,
            "initialize",
            payload={
                "config": base_config,
                "action_id": action_id,
                "fencing_token": 1,
                "executor_instance_id": executor_instance_id,
            },
            action_id=action_id,
            fencing_token=1,
            executor_instance_id=executor_instance_id,
            lock_fd=lock_fd,
        )

        # Step 5: Validate Checkpoint Contract
        db_path = target / "orchestrator" / "var" / "checkpoints.db"
        if not db_path.exists():
            _mark_failed(registry, action_id, 1, executor_instance_id, "checkpoints.db missing after initialize")
            raise BootstrapConflictError("checkpoints.db missing after initialize")

        _validate_checkpoint_contract(db_path, manifest, base_config)

        # Step 6: Register Task & Context Provenance (fenced)
        _check_bootstrap_fence(registry, action_id, 1, executor_instance_id)
        registered = registry.register_existing_worktree(target)
        _record_task_provenance(registry, task_id, target, base_config)

        # Step 7: Complete Action Log
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = registry._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE action_log
                    SET state = 'COMPLETE',
                        response_json = ?,
                        updated_utc = ?
                    WHERE action_id = ?
                      AND fencing_token = 1
                      AND executor_instance_id = ?
                      AND state = 'EXECUTING';
                    """,
                    (json.dumps(registered), now_iso, action_id, executor_instance_id),
                )
        finally:
            conn.close()

        return registered

    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            os.close(lock_fd)
        except Exception:
            pass


async def _execute_bootstrap_recovery(
    action_id: str,
    fencing_token: int,
    executor_instance_id: str,
    manifest: dict[str, Any],
    lock_fd: int,
    registry: TaskRegistry,
    is_test_mode: bool = False,
) -> dict[str, Any]:
    """Execute recovery of an interrupted bootstrap action."""
    work_item = manifest["work_item"]
    task_id = manifest["task_id"]
    target = Path(manifest["target_path"])

    # If target directory does not exist, initialize from scratch
    if not target.exists():
        _mark_reconciliation(registry, action_id, fencing_token, executor_instance_id, "Worktree directory missing")
        raise BootstrapConflictError(f"Target directory {target} missing. Manual reconciliation required.")

    # 1. Verify Git Common Dir and Worktree
    try:
        common_dir = subprocess.check_output(
            ["git", "-C", str(target), "rev-parse", "--git-common-dir"], text=True
        ).strip()
        if not Path(common_dir).is_absolute():
            common_dir = str((target / common_dir).resolve())
        if Path(common_dir).resolve() != Path(manifest["git_common_dir"]).resolve():
            _mark_reconciliation(registry, action_id, fencing_token, executor_instance_id, "git-common-dir mismatch")
            raise BootstrapConflictError("Git common-dir mismatch. Manual reconciliation required.")

        branch = subprocess.check_output(
            ["git", "-C", str(target), "branch", "--show-current"], text=True
        ).strip()
        if branch != manifest["branch_name"]:
            _mark_reconciliation(registry, action_id, fencing_token, executor_instance_id, "branch mismatch")
            raise BootstrapConflictError(f"Git branch {branch} != expected {manifest['branch_name']}")

        # Ancestry check
        ancestry = subprocess.run(
            ["git", "-C", str(target), "merge-base", "--is-ancestor", manifest["resolved_base_sha"], "HEAD"],
            capture_output=True,
        )
        if ancestry.returncode != 0:
            _mark_reconciliation(registry, action_id, fencing_token, executor_instance_id, "base ancestry check failed")
            raise BootstrapConflictError("Base commit is not ancestor of HEAD")
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        _mark_reconciliation(registry, action_id, fencing_token, executor_instance_id, f"Git validation failed: {exc}")
        raise BootstrapConflictError(f"Git validation failed: {exc}") from exc

    # 2. Verify owner brief
    brief_file = target / f"docs/ai/work-items/{work_item}/owner-brief.md"
    if not brief_file.is_file():
        _mark_reconciliation(registry, action_id, fencing_token, executor_instance_id, "owner-brief.md missing")
        raise BootstrapConflictError("owner-brief.md missing. Manual reconciliation required.")

    actual_brief_sha = hashlib.sha256(brief_file.read_bytes()).hexdigest()
    if actual_brief_sha != manifest["brief_content_sha256"]:
        _mark_reconciliation(registry, action_id, fencing_token, executor_instance_id, "owner-brief.md content mismatch")
        raise BootstrapConflictError("owner-brief.md content hash mismatch. Manual reconciliation required.")

    # 3. Inspect Checkpoints DB
    db_path = target / "orchestrator" / "var" / "checkpoints.db"
    base_config = {
        "root": str(target),
        "work_item": work_item,
        "branch": manifest["branch_name"],
        "base_commit": manifest.get("brief_commit_sha") or manifest["resolved_base_sha"],
        "stages": ["plan"],
        "scope": {
            "allowed_paths": [f"docs/ai/work-items/{work_item}/**"],
        },
        "read_only_context_paths": [
            "AGENTS.md",
            "SESSION_MEMORY.md",
            "docs/ai/SCHEMA_FACTS.md",
            "docs/ai/CODING_PATTERNS.md",
            "docs/ai/CONTEXT_INDEX.md",
        ],
        "plan_path": f"docs/ai/work-items/{work_item}/owner-brief.md",
        "plan_revision_hash": manifest["brief_content_sha256"],
        "roles": {},
        "budget": 200,
    }

    if not db_path.exists():
        # Crash happened before initialize ran -> run initialize now under lock (fenced)
        _check_bootstrap_fence(registry, action_id, fencing_token, executor_instance_id)
        init_res = await run_action(
            target,
            "initialize",
            payload={
                "config": base_config,
                "action_id": action_id,
                "fencing_token": fencing_token,
                "executor_instance_id": executor_instance_id,
            },
            action_id=action_id,
            fencing_token=fencing_token,
            executor_instance_id=executor_instance_id,
            lock_fd=lock_fd,
        )
    else:
        # DB exists: Check SQLite integrity
        import sqlite3
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            check_row = conn.execute("PRAGMA quick_check;").fetchone()
            if not check_row or check_row[0] != "ok":
                _mark_reconciliation(registry, action_id, fencing_token, executor_instance_id, "checkpoints.db corruption")
                raise BootstrapConflictError("checkpoints.db failed quick_check. Manual reconciliation required.")

            cfg_row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
            if not cfg_row:
                _mark_reconciliation(registry, action_id, fencing_token, executor_instance_id, "workflow_meta config missing")
                raise BootstrapConflictError("workflow_meta config missing. Manual reconciliation required.")

            stored_cfg = json.loads(cfg_row[0])
            stored_digest = _config_digest(stored_cfg)
            if stored_digest != manifest["base_config_digest"]:
                _mark_reconciliation(registry, action_id, fencing_token, executor_instance_id, "stored config digest mismatch")
                raise BootstrapConflictError("Stored config digest mismatch. Manual reconciliation required.")

            # Check if checkpoint exists
            c_row = conn.execute("SELECT 1 FROM checkpoints WHERE thread_id='workflow'").fetchone()
            if not c_row:
                # Crash occurred after config persistence but before checkpoint creation
                _mark_reconciliation(
                    registry,
                    action_id,
                    fencing_token,
                    executor_instance_id,
                    "Config present without checkpoint: interrupted initialization",
                )
                raise BootstrapConflictError(
                    "Interrupted initialization (config present without checkpoint). Manual reconciliation required."
                )
        finally:
            conn.close()

    # Validate exact contract
    _validate_checkpoint_contract(db_path, manifest, base_config)

    # Register Task & Provenance (fenced)
    _check_bootstrap_fence(registry, action_id, fencing_token, executor_instance_id)
    registered = registry.register_existing_worktree(target)
    _record_task_provenance(registry, task_id, target, base_config)

    # Complete action log
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = registry._get_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE action_log
                SET state = 'COMPLETE',
                    response_json = ?,
                    updated_utc = ?
                WHERE action_id = ?
                  AND fencing_token = ?
                  AND executor_instance_id = ?
                  AND state = 'RECOVERING';
                """,
                (json.dumps(registered), now_iso, action_id, fencing_token, executor_instance_id),
            )
    finally:
        conn.close()

    return registered


def _validate_checkpoint_contract(db_path: Path, manifest: dict[str, Any], base_config: dict[str, Any]) -> None:
    """Assert initialized checkpoint adheres strictly to routing.py initial contract."""
    script = """
import sys, sqlite3, json
from langgraph.checkpoint.sqlite import SqliteSaver

db_path = sys.argv[1]
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
try:
    saver = SqliteSaver(conn)
    checkpoint = saver.get({"configurable": {"thread_id": "workflow"}})
    if not checkpoint or not checkpoint.get("channel_values"):
        sys.exit(2)
    view = checkpoint["channel_values"]["view"]
    print(json.dumps(view))
finally:
    conn.close()
"""
    res = subprocess.run(
        [str(ORCHESTRATOR_PYTHON), "-c", script, str(db_path)],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise BootstrapConflictError(f"Failed to inspect workflow checkpoint: {res.stderr or res.stdout}")

    try:
        view = json.loads(res.stdout.strip())
    except Exception as exc:
        raise BootstrapConflictError(f"Corrupt checkpoint view output: {exc}") from exc

    expected_stage = base_config.get("stage") or base_config["stages"][0]
    if view.get("status") != "DRAFT":
        raise BootstrapConflictError(f"Initial status {view.get('status')!r} != 'DRAFT'")
    if view.get("stage") != expected_stage:
        raise BootstrapConflictError(f"Initial stage {view.get('stage')!r} != {expected_stage!r}")
    if view.get("work_item") != manifest["work_item"]:
        raise BootstrapConflictError(f"Work item {view.get('work_item')!r} != {manifest['work_item']!r}")
    if view.get("active_jobs") != []:
        raise BootstrapConflictError(f"Initial active_jobs is not empty: {view.get('active_jobs')}")
    if view.get("round") != 0:
        raise BootstrapConflictError(f"Initial round is {view.get('round')} != 0")
    if view.get("committed") is not False:
        raise BootstrapConflictError(f"Initial committed is {view.get('committed')} != False")


def _record_task_provenance(registry: TaskRegistry, task_id: str, target: Path, config: dict[str, Any]) -> None:
    context_paths = config.get("read_only_context_paths") or []
    items = []
    for rel_p in context_paths:
        f = target / rel_p
        exists = f.is_file()
        sha = hashlib.sha256(f.read_bytes()).hexdigest() if exists else None
        items.append({
            "path": rel_p,
            "exists": exists,
            "is_mandatory": rel_p in ("AGENTS.md", "SESSION_MEMORY.md"),
            "sha256": sha,
            "commit_sha": config.get("base_commit"),
        })
    registry.record_context_provenance(task_id, items)


def _mark_failed(registry: TaskRegistry, action_id: str, fencing_token: int, executor_instance_id: str, error: str) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = registry._get_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE action_log
                SET state = 'FAILED', error_message = ?, updated_utc = ?
                WHERE action_id = ? AND fencing_token = ? AND executor_instance_id = ?;
                """,
                (error, now_iso, action_id, fencing_token, executor_instance_id),
            )
    finally:
        conn.close()


def _mark_reconciliation(registry: TaskRegistry, action_id: str, fencing_token: int, executor_instance_id: str, error: str) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = registry._get_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE action_log
                SET state = 'RECONCILIATION_REQUIRED', error_message = ?, updated_utc = ?
                WHERE action_id = ? AND fencing_token = ? AND executor_instance_id = ?;
                """,
                (error, now_iso, action_id, fencing_token, executor_instance_id),
            )
    finally:
        conn.close()
