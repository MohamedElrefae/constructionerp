"""Subprocess Client for orchestrator communication.

Provides async invocation of orchestrator.dashboard_api via subprocesses.
Strict constraints:
- Zero Python imports from orchestrator package.
- Absolute Python executable path.
- Fixed working directory.
- Action allowlist: see ALLOWED_ACTIONS (state, plan, review_context,
  ai_context, adopt_scope, approve_plan, initialize, run, ...).
- Concurrency bounded by asyncio.Semaphore(4).
- Strict subprocess timeout (10.0 s; `run` gets at least 120 s).
- Passes canonical registry in environment as consistency assertion.
- Uses dashboard.process for parent-death signaling and lock inheritance.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dashboard.config import (
    CANONICAL_REGISTRY_PATH,
    FORWARD_ENGINE_DISPATCH_ENV,
    MANAGED_SUPERVISOR_CONFIG,
    MANAGED_SUPERVISOR_DISPATCH_CONFIG,
    MANAGED_SUPERVISOR_DISPATCH_ENABLED,
    MAX_CONCURRENT_SUBPROCESSES,
    ORCHESTRATOR_PYTHON,
    ORCHESTRATOR_ROOT,
    SUBPROCESS_TIMEOUT_SECONDS,
    SUPERVISOR_SOCKET,
    SUPERVISOR_TOKEN_FILE,
)
from dashboard.process import async_spawn_supervised_child

ALLOWED_ACTIONS = {
    "run",
    "state",
    "plan",
    "review_context",
    "ai_context",
    "adopt_scope",
    "approve_plan",
    "initialize",
    "findings",
    "evidence",
    "read_evidence",
    "diff",
    "settings",
    "audit",
    "commit_requirements",
    "verify_commit",
    "record_commit",
    "arm_commit",
    "collect",
    "supervisor_health",
}

_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SUBPROCESSES)


class SubprocessClientError(Exception):
    """Exception raised for errors executing subprocess commands."""


def child_env(environ=None, forward_engine_dispatch=None, managed_dispatch=False):
    """Environment for the engine subprocess.

    A browser click must not implicitly inherit a host-level dispatch ack, so
    ENGINE_NATIVE_DISPATCH / ENGINE_T3_BACKEND are dropped unless the operator
    sets DASHBOARD_ALLOW_ENGINE_DISPATCH=1. Everything else is inherited.
    """
    env = dict(os.environ if environ is None else environ)
    forward = FORWARD_ENGINE_DISPATCH_ENV if forward_engine_dispatch is None else forward_engine_dispatch
    if not forward:
        env.pop("ENGINE_NATIVE_DISPATCH", None)
        env.pop("ENGINE_T3_BACKEND", None)
    # Never pass inherited managed-dispatch controls through implicitly.
    env.pop("DASHBOARD_ENABLE_MANAGED_DISPATCH", None)
    env.pop("DASHBOARD_MANAGED_SUPERVISOR_DISPATCH_CONFIG", None)
    if managed_dispatch:
        if not MANAGED_SUPERVISOR_DISPATCH_ENABLED or not MANAGED_SUPERVISOR_DISPATCH_CONFIG:
            raise SubprocessClientError("managed dispatch requires an explicit enable flag and config")
        env["DASHBOARD_ENABLE_MANAGED_DISPATCH"] = "1"
        env["DASHBOARD_MANAGED_SUPERVISOR_DISPATCH_CONFIG"] = str(MANAGED_SUPERVISOR_DISPATCH_CONFIG)
    env["CANONICAL_DASHBOARD_REGISTRY"] = env.get(
        "CANONICAL_DASHBOARD_REGISTRY", str(CANONICAL_REGISTRY_PATH)
    )
    return env


async def run_action(
    worktree_path: Path | str,
    action: str,
    payload: dict[str, Any] | None = None,
    action_id: str | None = None,
    fencing_token: int | None = None,
    executor_instance_id: str | None = None,
    lock_fd: int | None = None,
    timeout: float = SUBPROCESS_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Execute an allowlisted action via orchestrator subprocess."""
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Action {action!r} not permitted. Allowed actions: {sorted(ALLOWED_ACTIONS)}")

    worktree = Path(worktree_path).resolve()
    if not worktree.is_dir():
        raise FileNotFoundError(f"Worktree directory not found: {worktree}")

    managed_setting_present = bool(MANAGED_SUPERVISOR_DISPATCH_CONFIG)
    if action in ("run", "collect") and (managed_setting_present or MANAGED_SUPERVISOR_DISPATCH_ENABLED):
        if not MANAGED_SUPERVISOR_DISPATCH_ENABLED:
            raise SubprocessClientError("managed dispatch config is present but dispatch is disabled")
        if not MANAGED_SUPERVISOR_DISPATCH_CONFIG:
            raise SubprocessClientError("managed dispatch is enabled but its config path is missing")
    managed_dispatch = (
        action in ("run", "collect")
        and MANAGED_SUPERVISOR_DISPATCH_ENABLED
        and bool(MANAGED_SUPERVISOR_DISPATCH_CONFIG)
    )

    cmd = [
        str(ORCHESTRATOR_PYTHON),
        "-m",
        "orchestrator.dashboard_api",
        "--root",
        str(worktree),
        "--action",
        action,
    ]
    if action_id:
        cmd.extend(["--action-id", str(action_id)])
    if fencing_token is not None:
        cmd.extend(["--fencing-token", str(fencing_token)])
    if executor_instance_id:
        cmd.extend(["--executor-instance-id", str(executor_instance_id)])
    if SUPERVISOR_SOCKET:
        cmd.extend(["--supervisor-socket", str(SUPERVISOR_SOCKET)])
    if SUPERVISOR_TOKEN_FILE:
        cmd.extend(["--supervisor-token-file", str(SUPERVISOR_TOKEN_FILE)])
    if action == "supervisor_health" and MANAGED_SUPERVISOR_CONFIG:
        cmd.extend(["--managed-supervisor-config", str(MANAGED_SUPERVISOR_CONFIG)])
    if payload:
        cmd.extend(["--payload", json.dumps(payload)])

    env = child_env(managed_dispatch=managed_dispatch)

    if action == "run":
        timeout = max(timeout, 120.0)
    async with _semaphore:
        proc = None
        try:
            proc = await async_spawn_supervised_child(
                cmd,
                lock_fd=lock_fd,
                cwd=str(ORCHESTRATOR_ROOT),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            if proc is not None:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
            raise SubprocessClientError(
                f"Subprocess timed out after {timeout} seconds (action={action})"
            ) from exc
        except (asyncio.CancelledError, Exception):
            if proc is not None:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
            raise
        finally:
            if proc is not None and getattr(proc, "_transport", None) is not None:
                try:
                    proc._transport.close()
                except Exception:
                    pass

        stdout_str = stdout_b.decode("utf-8", errors="replace").strip()
        stderr_str = stderr_b.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            err_msg = stderr_str or stdout_str or f"Subprocess exited with code {proc.returncode}"
            err_msg = " ".join(err_msg.split())[:300]
            try:
                err_json = json.loads(stdout_str)
                if isinstance(err_json, dict) and "error" in err_json:
                    err_msg = " ".join(str(err_json["error"]).split())[:300]
            except Exception:
                pass
            raise SubprocessClientError(f"Subprocess error: {err_msg} (stderr: {stderr_str[:800]})")

        try:
            res = json.loads(stdout_str)
        except json.JSONDecodeError as exc:
            raise SubprocessClientError(
                f"Failed to parse subprocess output as JSON: {stdout_str[:200]}"
            ) from exc

        if not res.get("ok"):
            raise SubprocessClientError(res.get("error", "Unknown subprocess failure"))

        return res.get("result", {})


async def get_state_projection(worktree_path: Path | str) -> dict[str, Any]:
    """Retrieve the read-only state projection for a worktree."""
    return await run_action(worktree_path, "state")


async def get_plan_projection(worktree_path: Path | str) -> dict[str, Any]:
    """Retrieve the read-only plan projection for a worktree."""
    return await run_action(worktree_path, "plan")


async def get_review_context(worktree_path: Path | str) -> dict[str, Any]:
    """Retrieve the review context projection for a worktree."""
    return await run_action(worktree_path, "review_context")


async def get_ai_context(worktree_path: Path | str) -> dict[str, Any]:
    """Retrieve the AI conventions and sprint memory projection for a worktree."""
    return await run_action(worktree_path, "ai_context")


async def adopt_scope(
    worktree_path: Path | str,
    scope: dict[str, Any],
    implementation_stages: list[str],
    action_id: str,
    request_hash: str,
    fencing_token: int | None = None,
    executor_instance_id: str | None = None,
    lock_fd: int | None = None,
) -> dict[str, Any]:
    """Adopt an architect scope proposal."""
    payload = {
        "scope": scope,
        "implementation_stages": implementation_stages,
        "action_id": action_id,
        "request_hash": request_hash,
    }
    return await run_action(
        worktree_path,
        "adopt_scope",
        payload=payload,
        action_id=action_id,
        fencing_token=fencing_token,
        executor_instance_id=executor_instance_id,
        lock_fd=lock_fd,
    )


async def approve_plan(
    worktree_path: Path | str,
    token: dict[str, Any],
    action_id: str | None = None,
    fencing_token: int | None = None,
    executor_instance_id: str | None = None,
    lock_fd: int | None = None,
) -> dict[str, Any]:
    """Grant approval for a plan without dispatching tasks."""
    payload = {
        "submitted_token": token,
        "action_id": action_id,
    }
    return await run_action(
        worktree_path,
        "approve_plan",
        payload=payload,
        action_id=action_id,
        fencing_token=fencing_token,
        executor_instance_id=executor_instance_id,
        lock_fd=lock_fd,
    )


async def initialize_task(
    worktree_path: Path | str,
    config: dict[str, Any],
    action_id: str | None = None,
    fencing_token: int | None = None,
    executor_instance_id: str | None = None,
    lock_fd: int | None = None,
) -> dict[str, Any]:
    """Initialize a task worktree."""
    payload = {
        "config": config,
        "action_id": action_id,
    }
    return await run_action(
        worktree_path,
        "initialize",
        payload=payload,
        action_id=action_id,
        fencing_token=fencing_token,
        executor_instance_id=executor_instance_id,
        lock_fd=lock_fd,
    )


async def query_findings(worktree_path: Path | str) -> dict[str, Any]:
    """Retrieve the read-only findings and backlog projection for a worktree."""
    return await run_action(worktree_path, "findings")


async def query_evidence_list(worktree_path: Path | str) -> dict[str, Any]:
    """Retrieve the list of available evidence artifacts for a worktree."""
    return await run_action(worktree_path, "evidence")


async def query_evidence_content(worktree_path: Path | str, filename: str) -> dict[str, Any]:
    """Read a specific evidence artifact using descriptor-relative validation."""
    return await run_action(worktree_path, "read_evidence", payload={"filename": filename})


async def query_diff(worktree_path: Path | str) -> dict[str, Any]:
    """Retrieve the git diff projection against stored configuration base commit."""
    return await run_action(worktree_path, "diff")


async def query_settings(worktree_path: Path | str) -> dict[str, Any]:
    """Retrieve read-only settings, role pins, and escalation counters."""
    return await run_action(worktree_path, "settings")


async def query_supervisor_health() -> dict[str, Any]:
    """Check the optional managed supervisor over its read-only Unix socket."""
    if not MANAGED_SUPERVISOR_CONFIG:
        raise SubprocessClientError("managed supervisor health is not configured")
    return await run_action(ORCHESTRATOR_ROOT, "supervisor_health")


async def query_audit_events(
    worktree_path: Path | str, max_events: int = 1000, max_bytes: int = 524288
) -> dict[str, Any]:
    """Retrieve sanitized, dual-bounded audit events for a worktree."""
    return await run_action(
        worktree_path, "audit", payload={"max_events": max_events, "max_bytes": max_bytes}
    )
