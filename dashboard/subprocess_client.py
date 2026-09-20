"""Subprocess Client for orchestrator communication.

Provides async invocation of orchestrator.dashboard_api via subprocesses.
Strict constraints:
- Zero Python imports from orchestrator package.
- Absolute Python executable path.
- Fixed working directory.
- Action allowlist: {"state", "plan", "review_context", "ai_context", "adopt_scope", "approve_plan", "initialize"}.
- Concurrency bounded by asyncio.Semaphore(4).
- Strict subprocess timeout (10.0 seconds).
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
    MAX_CONCURRENT_SUBPROCESSES,
    ORCHESTRATOR_PYTHON,
    ORCHESTRATOR_ROOT,
    SUBPROCESS_TIMEOUT_SECONDS,
)
from dashboard.process import async_spawn_supervised_child

ALLOWED_ACTIONS = {
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
}

_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SUBPROCESSES)


class SubprocessClientError(Exception):
    """Exception raised for errors executing subprocess commands."""


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
    if payload:
        cmd.extend(["--payload", json.dumps(payload)])

    env = dict(os.environ)
    env["CANONICAL_DASHBOARD_REGISTRY"] = os.environ.get(
        "CANONICAL_DASHBOARD_REGISTRY", str(CANONICAL_REGISTRY_PATH)
    )

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
            try:
                err_json = json.loads(stdout_str)
                if isinstance(err_json, dict) and "error" in err_json:
                    err_msg = err_json["error"]
            except Exception:
                pass
            raise SubprocessClientError(f"Subprocess error: {err_msg} (stderr: {stderr_str})")

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


async def query_audit_events(
    worktree_path: Path | str, max_events: int = 1000, max_bytes: int = 524288
) -> dict[str, Any]:
    """Retrieve sanitized, dual-bounded audit events for a worktree."""
    return await run_action(
        worktree_path, "audit", payload={"max_events": max_events, "max_bytes": max_bytes}
    )
