"""Subprocess API for Civil Engineer Dashboard.

Sole owner of execution.lock during mutations. Executes Engine operations,
runs action-specific preflight checks, deduplicates requests under lock,
and returns JSON to stdout.
"""

import argparse
import json
import sys
from pathlib import Path

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
    lock_path = runtime_path / "execution.lock"

    with execution_lock(lock_path, timeout=10):
        # 1. Preflight check selection per action
        if action in ("state", "plan"):
            checks = run_display_checks(runtime_path)
            failed = [c for c in checks if not c.ok]
            if failed:
                raise PreconditionError(f"Display preflight failed: {failed}")
        elif action in ("pause", "resume", "reset_budget", "reconfigure_role"):
            cfg = None
            if (runtime_path / "checkpoints.db").exists():
                tmp_e = Engine(root)
                try:
                    cfg = tmp_e.config
                finally:
                    tmp_e.close()
            checks = run_owner_action_checks(runtime_path, root, cfg)
            failed = [c for c in checks if not c.ok]
            if failed:
                raise PreconditionError(f"Owner action preflight failed: {failed}")
        elif action == "initialize":
            checks = run_init_checks(root)
            failed = [c for c in checks if not c.ok]
            if failed:
                raise PreconditionError(f"Init preflight failed: {failed}")
        elif action in ("run", "approve_plan", "adopt_scope"):
            cfg = None
            if (runtime_path / "checkpoints.db").exists():
                tmp_e = Engine(root)
                try:
                    cfg = tmp_e.config
                finally:
                    tmp_e.close()
            checks = run_dispatch_preflight(cfg, runtime_path, root)
            failed = [c for c in checks if not c.ok]
            if failed:
                raise PreconditionError(f"Dispatch preflight failed: {failed}")

        # 2. Initialize Engine
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
            if action == "state":
                return engine.view()
            elif action == "plan":
                plan_art = engine.store.meta("plan_artifact")
                plan_path = (root / plan_art) if plan_art else (root / engine.config.get("plan_path", ""))
                if plan_path.exists():
                    text = plan_path.read_text()
                    return {"plan_text": text, "plan_path": str(plan_path)}
                return {"plan_text": "", "plan_path": ""}
            elif action == "initialize":
                config = payload["config"]
                return engine.initialize(config)
            elif action == "run":
                once = payload.get("once", False)
                return engine.run(once=once)
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
            "error": str(exc),
            "error_type": type(exc).__name__,
        }
        print(json.dumps(output, default=str))
        sys.exit(1)


if __name__ == "__main__":
    main()
