"""Subprocess API for Civil Engineer Dashboard.

Sole owner of execution.lock during mutations. Executes Engine operations,
runs action-specific preflight checks, deduplicates requests under lock,
and returns JSON to stdout.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# Ensure orchestrator package directory is in sys.path so both
# `python -m orchestrator.dashboard_api` and direct script execution work
_orchestrator_dir = Path(__file__).resolve().parent
if str(_orchestrator_dir) not in sys.path:
    sys.path.insert(0, str(_orchestrator_dir))

from core import (
    DuplicateKeyConflict,
    GrantReconciliationRequired,
    PreconditionError,
    RecoveryError,
    ValidationError as CoreValidationError,
    WorkflowError,
    canonical,
    execution_lock,
)
from engine import Engine
from preflight import (
    run_dispatch_preflight,
    run_display_checks,
    run_init_checks,
    run_owner_action_checks,
)
from stage4 import sanitize_public_text


def sanitize_error(exc: Exception, root: Path | str | None = None) -> str:
    """Sanitize error messages to avoid leaking absolute paths or private content."""
    msg = str(exc)
    if root:
        root_str = str(Path(root).resolve())
        msg = msg.replace(root_str, "[WORKTREE]")
    msg = sanitize_public_text(msg)
    return msg


def get_state_projection(root: Path | str) -> dict:
    """Dedicated read-only projection of workflow state.

    Does NOT instantiate Engine, acquire exclusive execution.lock, or mutate
    any files, checkpoints, or role mirrors.
    """
    root = Path(root).resolve()
    runtime_path = root / "orchestrator/var"
    checks = run_display_checks(runtime_path)
    failed = [c for c in checks if not c.ok]
    if failed:
        raise PreconditionError(f"Display preflight failed: {failed}")

    db_path = runtime_path / "checkpoints.db"
    if not db_path.exists():
        return {"status": "NOT_INITIALIZED"}

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        saver = SqliteSaver(conn)
        checkpoint = saver.get({"configurable": {"thread_id": "workflow"}})
        if not checkpoint or not checkpoint.get("channel_values"):
            return {"status": "NOT_INITIALIZED"}
        v = checkpoint["channel_values"]["view"]

        meta_row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
        config = json.loads(meta_row[0]) if meta_row else {}
    finally:
        conn.close()

    # Allowlisted projection: exclude host absolute paths and private tokens
    return {
        "work_item": v.get("work_item"),
        "stage": v.get("stage"),
        "status": v.get("status"),
        "sub_status": v.get("sub_status"),
        "pause_reason": v.get("pause_reason"),
        "resume_to": v.get("resume_to"),
        "gate": v.get("gate"),
        "plan_granted": bool(v.get("plan_granted")),
        "active_jobs": [
            {
                "job_id": j.get("job_id") if isinstance(j, dict) else str(j),
                "role": j.get("role") if isinstance(j, dict) else None,
                "status": j.get("status") if isinstance(j, dict) else None,
            }
            for j in (v.get("active_jobs") or [])
        ],
        "stages": v.get("stages", {}),
        "next_roles": v.get("next_roles", []),
        "cursor": v.get("cursor"),
        "revision": v.get("revision"),
        "plan_revision_hash": v.get("plan_revision_hash"),
        "roles_hash": v.get("roles_hash") or config.get("roles_hash"),
        "scope_hash": v.get("scope_hash"),
        "approval_refs": v.get("approval_refs", []),
        "completed_dependencies": v.get("completed_dependencies", []),
    }


def get_plan_projection(root: Path | str) -> dict:
    """Dedicated read-only projection of plan text.

    Does NOT instantiate Engine, acquire exclusive execution.lock, or mutate
    any files. Returns a relative plan_path and sanitized plan_text.
    """
    root = Path(root).resolve()
    runtime_path = root / "orchestrator/var"
    checks = run_display_checks(runtime_path)
    failed = [c for c in checks if not c.ok]
    if failed:
        raise PreconditionError(f"Display preflight failed: {failed}")

    db_path = runtime_path / "checkpoints.db"
    plan_art = None
    plan_cfg_path = ""
    if db_path.exists():
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT value FROM workflow_meta WHERE key='plan_artifact'").fetchone()
            if row:
                plan_art = json.loads(row[0]) if row[0].startswith('"') else row[0]
            cfg_row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
            if cfg_row:
                cfg = json.loads(cfg_row[0])
                plan_cfg_path = cfg.get("plan_path", "")
        finally:
            conn.close()

    rel_path = plan_art or plan_cfg_path
    if not rel_path:
        return {"plan_text": "", "plan_path": ""}

    full_path = root / rel_path
    if not full_path.exists():
        return {"plan_text": "", "plan_path": str(rel_path)}

    raw_text = full_path.read_text(encoding="utf-8", errors="replace")

    # Sanitize text (scrub private terms/Arabic, replace host paths with [WORKTREE])
    clean_text = sanitize_public_text(raw_text)
    clean_text = clean_text.replace(str(root), "[WORKTREE]")

    try:
        plan_rel = full_path.relative_to(root)
    except ValueError:
        plan_rel = Path(rel_path)

    return {
        "plan_text": clean_text,
        "plan_path": str(plan_rel),
    }


def deduplicate_action(
    action_id: str | None,
    request_hash: str,
    token_id: str | None,
    submitted_token: dict | None,
    store=None,
    engine=None,
) -> dict | None:
    """Called under execution.lock before executing any mutation."""
    if store is None and engine is not None:
        store = engine.store

    # --- Approval deduplication ---
    if token_id and submitted_token is not None:
        # Validate lookup key matches token's own token_id before any DB access.
        if submitted_token.get("token_id") != token_id:
            raise CoreValidationError(
                f"submitted_token['token_id']={submitted_token.get('token_id')!r} "
                f"does not match lookup token_id={token_id!r}"
            )

        # Inspect BOTH records independently before any early return
        grant_row = store.lookup_grant(token_id)

        grant_event = None
        for event in store.events():
            if (
                event["kind"] == "grant"
                and event["payload"].get("token_id") == token_id
            ):
                grant_event = event
                break

        # Neither present -> genuinely new request; proceed with execution
        if grant_row is None and grant_event is None:
            return None

        # One without the other -> inconsistent state; cannot auto-recover
        if grant_row is None and grant_event is not None:
            raise GrantReconciliationRequired(
                f"Grant event for token_id={token_id!r} exists without a "
                "corresponding grant row. Manual reconciliation required."
            )
        if grant_row is not None and grant_event is None:
            raise GrantReconciliationRequired(
                f"Grant row for token_id={token_id!r} exists without a "
                "corresponding grant event. "
                "_synchronize_checkpoint() cannot create missing events. "
                "Manual reconciliation required."
            )

        # Both present — canonical equality: submitted token vs stored token
        stored_token = grant_row["data"]
        if submitted_token != stored_token:
            differing = sorted(
                f
                for f in set(submitted_token) | set(stored_token)
                if submitted_token.get(f) != stored_token.get(f)
            )
            raise DuplicateKeyConflict(
                f"token_id reused with changed approval bindings: {differing}. "
                f"submitted={submitted_token!r}, stored={stored_token!r}"
            )

        # Verify event payload consistent with stored token
        event_payload = grant_event["payload"]
        if event_payload != stored_token:
            differing = sorted(
                f
                for f in set(event_payload) | set(stored_token)
                if event_payload.get(f) != stored_token.get(f)
            )
            raise GrantReconciliationRequired(
                f"Grant row and event are inconsistent: {differing}. "
                f"row={stored_token!r}, event={event_payload!r}"
            )

        engine._synchronize_checkpoint()
        return {
            "status": "already_complete",
            "source": "grant_event",
            "event_id": grant_event["event_id"],
        }

    # --- Non-approval deduplication via action_id in workflow_events.payload ---
    if action_id:
        for event in store.events():
            if event["payload"].get("action_id") == action_id:
                stored_hash = event["payload"].get("request_hash")
                if not stored_hash:
                    raise DuplicateKeyConflict(
                        "Stored event missing request_hash — rejecting"
                    )
                if stored_hash != request_hash:
                    raise DuplicateKeyConflict(
                        "action_id reused with different request contents"
                    )
                engine._synchronize_checkpoint()
                return {
                    "status": "already_complete",
                    "event_id": event["event_id"],
                }

    return None


def execute_action(root: Path, action: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    root = Path(root).resolve()
    runtime_path = root / "orchestrator/var"

    # Read-only display actions do not acquire execution.lock and do not construct Engine
    if action == "state":
        return get_state_projection(root)
    elif action == "plan":
        return get_plan_projection(root)

    lock_path = runtime_path / "execution.lock"

    with execution_lock(lock_path, timeout=10):
        # 1. Preflight check selection per mutating action
        if action in ("pause", "resume", "reset_budget", "reconfigure_role"):
            cfg = None
            if (runtime_path / "checkpoints.db").exists():
                conn = sqlite3.connect(f"file:{runtime_path / 'checkpoints.db'}?mode=ro", uri=True)
                try:
                    row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
                    if row:
                        cfg = json.loads(row[0])
                finally:
                    conn.close()
            checks = run_owner_action_checks(runtime_path, root, cfg)
            failed = [c for c in checks if not c.ok]
            if failed:
                raise PreconditionError(f"Owner action preflight failed: {failed}")
        elif action == "initialize":
            proposed_branch = None
            if isinstance(payload.get("config"), dict):
                proposed_branch = payload["config"].get("branch")
            if not proposed_branch:
                proposed_branch = payload.get("branch")
            checks = run_init_checks(root, expected_branch=proposed_branch)
            failed = [c for c in checks if not c.ok]
            if failed:
                raise PreconditionError(f"Init preflight failed: {failed}")
        elif action in ("run", "approve_plan", "adopt_scope"):
            cfg = None
            if (runtime_path / "checkpoints.db").exists():
                conn = sqlite3.connect(f"file:{runtime_path / 'checkpoints.db'}?mode=ro", uri=True)
                try:
                    row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
                    if row:
                        cfg = json.loads(row[0])
                finally:
                    conn.close()
            checks = run_dispatch_preflight(cfg, runtime_path, root)
            failed = [c for c in checks if not c.ok]
            if failed:
                raise PreconditionError(f"Dispatch preflight failed: {failed}")

        # 2. Initialize Engine for mutation
        engine = Engine(root)
        try:
            # 3. Deduplication under lock
            token_id = payload.get("token_id")
            submitted_token = payload.get("submitted_token") or payload.get("token")
            action_id = payload.get("action_id")
            request_hash = payload.get("request_hash", "")

            dedup = deduplicate_action(
                action_id=action_id,
                request_hash=request_hash,
                token_id=token_id,
                submitted_token=submitted_token,
                store=engine.store,
                engine=engine,
            )
            if dedup is not None:
                return dedup

            # 4. Dispatch action
            if action == "initialize":
                config = payload["config"]
                return engine.initialize(config)
            elif action == "run":
                return engine.run()
            elif action == "approve_plan":
                if not submitted_token:
                    raise CoreValidationError("approve_plan requires submitted_token or token in payload")
                return engine.approve(submitted_token)
            elif action == "adopt_scope":
                scope = payload["scope"]
                implementation_stages = payload["implementation_stages"]
                return engine.adopt_scope(
                    scope=scope,
                    implementation_stages=implementation_stages,
                    action_id=action_id,
                    request_hash=request_hash,
                )
            elif action == "pause":
                reason = payload.get("reason", "Paused by operator")
                return engine.owner_decision(
                    "pause",
                    {"reason": reason},
                    action_id=action_id,
                    request_hash=request_hash,
                )
            elif action == "resume":
                body = {
                    k: v
                    for k, v in payload.items()
                    if k not in ("action_id", "request_hash", "submitted_token", "token")
                }
                if "reason" not in body:
                    body["reason"] = "Resumed by operator"
                return engine.owner_decision(
                    "resume",
                    body,
                    action_id=action_id,
                    request_hash=request_hash,
                )
            elif action == "reset_budget":
                return engine.owner_decision(
                    "resume",
                    {"reason": "reset_budget", "reset_budget": True},
                    action_id=action_id,
                    request_hash=request_hash,
                )
            elif action == "reconfigure_role":
                role = payload["role"]
                tool = payload["tool"]
                model = payload["model"]
                effort = payload.get("effort", None)
                reason = payload.get("reason", "Owner role reconfiguration")
                return engine.reconfigure_role(
                    role=role,
                    tool=tool,
                    model=model,
                    effort=effort,
                    reason=reason,
                    action_id=action_id,
                    request_hash=request_hash,
                )
            else:
                raise WorkflowError(f"Unknown action: {action}")
        finally:
            engine.close()


def main():
    parser = argparse.ArgumentParser(description="Dashboard Subprocess API")
    parser.add_argument("--root", type=Path, required=True, help="Worktree root directory")
    parser.add_argument("--action", type=str, required=True, help="Action to execute")
    parser.add_argument("--payload", type=str, default=None, help="JSON payload string")
    parser.add_argument("--payload-file", type=Path, default=None, help="JSON payload file")
    args = parser.parse_args()

    payload = {}
    if args.payload:
        payload = json.loads(args.payload)
    elif args.payload_file and args.payload_file.exists():
        payload = json.loads(args.payload_file.read_text())
    elif not sys.stdin.isatty():
        content = sys.stdin.read().strip()
        if content:
            payload = json.loads(content)

    try:
        res = execute_action(args.root, args.action, payload)
        output = {"ok": True, "result": res}
        print(json.dumps(output, default=str))
        sys.exit(0)
    except Exception as exc:
        output = {
            "ok": False,
            "error": sanitize_error(exc, args.root),
            "error_type": type(exc).__name__,
        }
        print(json.dumps(output, default=str))
        sys.exit(1)


if __name__ == "__main__":
    main()
