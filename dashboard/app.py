"""Main ASGI application for the Civil Engineer Dashboard.

Configured with Starlette and uvicorn.
Middleware order:
1. HostValidationMiddleware (outermost raw ASGI - validates Host header syntax and allowlist)
2. OriginAndCSRFMiddleware (validates loopback Origin/Referer and double-submit CSRF)
3. SessionAuthenticationMiddleware (authenticates session cookie)

Strictly read-only workflow endpoints:
- No pause, resume, reset_budget, or stage4 dispatching endpoints.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any
import uuid

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from dashboard.auth import (
    HostValidationMiddleware,
    OriginAndCSRFMiddleware,
    SessionAuthenticationMiddleware,
    auth_store,
    rate_limiter,
    remove_initial_credentials_file,
    session_manager,
)
from dashboard.bootstrap import (
    BootstrapConflictError,
    BootstrapForbiddenError,
    bootstrap_task,
)
from dashboard.config import (
    CANONICAL_REGISTRY_PATH,
    CSRF_COOKIE_NAME,
    DASHBOARD_DIR,
    DASHBOARD_TEST_MODE,
    HOST,
    LOCKS_DIR,
    PORT,
    REPO_ROOT,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
)
from dashboard.coordinator import TaskCoordinator
from dashboard.process import get_process_start_time, is_process_alive_with_start_time
from dashboard.registry import TaskRegistry, validate_and_bind_canonical_registry
from dashboard.subprocess_client import (
    SubprocessClientError,
    adopt_scope,
    approve_plan,
    get_ai_context,
    get_plan_projection,
    get_review_context,
    get_state_projection,
    query_audit_events,
    query_diff,
    query_evidence_content,
    query_evidence_list,
    query_findings,
    query_settings,
)
from dashboard.security import SecurityError, read_authoritative_stage4_manifest

SERVER_INSTANCE_ID = f"inst-srv-{uuid.uuid4().hex[:8]}"

task_registry = TaskRegistry()
coordinator = TaskCoordinator(registry=task_registry)


# ---------------------------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------------------------

async def get_csrf_token(request: Request) -> Response:
    """Generate and return an ephemeral CSRF token and set cookie."""
    token = secrets.token_urlsafe(32)
    resp = JSONResponse({"csrf_token": token})
    # Secure cookie policy: unconditionally secure=True per specification
    resp.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=False,  # Accessible to client-side JS for X-CSRF-Token header
        samesite="strict",
        path="/",
        secure=True,
    )
    return resp


async def login(request: Request) -> Response:
    """Authenticate user, set session cookie, and rotate CSRF token."""
    client_ip = request.client.host if request.client else "unknown"

    if rate_limiter.is_rate_limited(client_ip):
        return JSONResponse(
            {"detail": "Too many failed login attempts. Try again later."},
            status_code=429,
        )

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return JSONResponse({"detail": "Username and password required"}, status_code=400)

    if not auth_store.verify_user(username, password):
        rate_limiter.record_failure(client_ip)
        return JSONResponse({"detail": "Invalid credentials"}, status_code=401)

    # Login succeeded: reset rate limiting
    rate_limiter.reset(client_ip)

    must_change = auth_store.is_initial_user(username)

    session_token = session_manager.create_session(username)
    new_csrf_token = secrets.token_urlsafe(32)

    resp = JSONResponse(
        {
            "ok": True,
            "username": username,
            "csrf_token": new_csrf_token,
            "must_change_password": must_change,
        }
    )

    # Unconditional secure cookie policy
    # Session cookie: HttpOnly, SameSite=Strict, Secure=True
    resp.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        httponly=True,
        samesite="strict",
        path="/",
        max_age=SESSION_MAX_AGE_SECONDS,
        secure=True,
    )

    # Rotated CSRF cookie: SameSite=Strict, Secure=True
    resp.set_cookie(
        CSRF_COOKIE_NAME,
        new_csrf_token,
        httponly=False,
        samesite="strict",
        path="/",
        secure=True,
    )

    return resp


async def setup_password(request: Request) -> Response:
    """Configure permanent password for authenticated account.
    
    Upon successful permanent password setup, the initial credential file is automatically deleted.
    """
    auth_err = _require_auth(request, allow_initial=True)
    if auth_err:
        return auth_err

    username = request.state.user
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not current_password or not new_password:
        return JSONResponse(
            {"detail": "current_password and new_password required"},
            status_code=400,
        )

    if len(new_password) < 12:
        return JSONResponse(
            {"detail": "New permanent password must be at least 12 characters long"},
            status_code=400,
        )

    if current_password == new_password:
        return JSONResponse(
            {"detail": "New permanent password must be different from current password"},
            status_code=400,
        )

    try:
        success = auth_store.change_password(username, current_password, new_password)
        if not success:
            return JSONResponse({"detail": "Invalid current password"}, status_code=401)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    # Initial credential file is ONLY unlinked upon successful permanent password setup!
    remove_initial_credentials_file(file_path=auth_store.credentials_file_path)

    return JSONResponse(
        {
            "ok": True,
            "detail": "Permanent password configured successfully",
        }
    )


async def logout(request: Request) -> Response:
    """Clear session and delete session cookies."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    session_manager.delete_session(session_token)

    new_csrf_token = secrets.token_urlsafe(32)
    resp = JSONResponse({"ok": True, "csrf_token": new_csrf_token})
    resp.delete_cookie(SESSION_COOKIE_NAME, path="/")
    resp.set_cookie(
        CSRF_COOKIE_NAME,
        new_csrf_token,
        httponly=False,
        samesite="strict",
        path="/",
        secure=True,
    )
    return resp


async def me(request: Request) -> Response:
    """Check current authentication status."""
    user = getattr(request.state, "user", None)
    if user:
        must_change = auth_store.is_initial_user(user)
        return JSONResponse(
            {
                "authenticated": True,
                "username": user,
                "must_change_password": must_change,
            }
        )
    return JSONResponse({"authenticated": False, "username": None})


# ---------------------------------------------------------------------------
# Task Management Routes (Strictly Read-Only)
# ---------------------------------------------------------------------------

def _require_auth(request: Request, allow_initial: bool = False) -> JSONResponse | None:
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    if not allow_initial and auth_store.is_initial_user(user):
        return JSONResponse({"detail": "Password setup required"}, status_code=403)
    return None


def _check_stage4_forbidden(work_item: str | None) -> JSONResponse | None:
    """Stage 4 Hard Isolation: fail-closed on all mutations."""
    if work_item == "erp-arabic-bilingual-data":
        return JSONResponse(
            {"detail": "Stage 4 erp-arabic-bilingual-data is parked and prohibited from dashboard execution"},
            status_code=403,
        )
    return None


async def list_tasks(request: Request) -> Response:
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err
    return JSONResponse(task_registry.list_tasks())


async def register_task(request: Request) -> Response:
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    worktree_path = data.get("worktree_path")
    if not worktree_path:
        return JSONResponse({"detail": "worktree_path is required"}, status_code=400)

    try:
        task = task_registry.register_existing_worktree(worktree_path)
        return JSONResponse({"ok": True, "task": task})
    except (ValueError, FileNotFoundError) as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"detail": f"Registration failed: {exc}"}, status_code=500)


async def bootstrap_task_endpoint(request: Request) -> Response:
    """Recoverable, non-overwriting Task Bootstrap endpoint."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    work_item = (data.get("work_item") or "").strip()
    user_brief = (data.get("user_brief") or "").strip()
    base_ref = data.get("base_ref", "HEAD")
    idempotency_key = data.get("idempotency_key")
    correlation_id = data.get("correlation_id")

    stage4_err = _check_stage4_forbidden(work_item)
    if stage4_err:
        return stage4_err

    if not work_item or not user_brief:
        return JSONResponse({"detail": "work_item and user_brief required"}, status_code=400)

    try:
        task = await bootstrap_task(
            work_item=work_item,
            user_brief=user_brief,
            base_ref=base_ref,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            registry=task_registry,
            is_test_mode=DASHBOARD_TEST_MODE,
        )
        return JSONResponse({"ok": True, "task": task})
    except BootstrapForbiddenError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=403)
    except BootstrapConflictError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=409)
    except Exception as exc:
        return JSONResponse({"detail": f"Bootstrap failed: {exc}"}, status_code=500)


async def get_task_detail(request: Request) -> Response:
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)
    return JSONResponse(task)


async def unregister_task(request: Request) -> Response:
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    if task_registry.unregister_task(task_id):
        return JSONResponse({"ok": True})
    return JSONResponse({"detail": "Task not found"}, status_code=404)


async def get_task_state(request: Request) -> Response:
    """Retrieve dynamic state projection from orchestrator subprocess."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    try:
        state = await get_state_projection(task["worktree_path"])
        task_registry.update_task_cache(
            task_id,
            state.get("status", task.get("cached_status", "UNKNOWN")),
            state.get("current_stage", task.get("cached_stage", "plan")),
        )
        return JSONResponse(state)
    except SubprocessClientError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to get state: {exc}"}, status_code=500)


async def get_task_plan(request: Request) -> Response:
    """Retrieve plain-text plan projection from orchestrator subprocess."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    try:
        plan = await get_plan_projection(task["worktree_path"])
        return JSONResponse(plan)
    except SubprocessClientError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to get plan: {exc}"}, status_code=500)


async def get_task_review_context(request: Request) -> Response:
    """Retrieve review context including gate, hashes, proposal, and provenance."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    try:
        ctx = await get_review_context(task["worktree_path"])
        gate = ctx.get("gate")
        active_review = None
        if gate and gate.get("gate_id"):
            active_review = task_registry.get_active_review_for_gate(task_id, gate["gate_id"])
        ctx["active_review"] = active_review
        return JSONResponse(ctx)
    except SubprocessClientError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to get review context: {exc}"}, status_code=500)


async def adopt_scope_endpoint(request: Request) -> Response:
    """Adopt an architect scope proposal."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    stage4_err = _check_stage4_forbidden(task.get("work_item"))
    if stage4_err:
        return stage4_err

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    scope = data.get("scope")
    implementation_stages = data.get("implementation_stages")
    if not scope or not implementation_stages:
        return JSONResponse({"detail": "scope and implementation_stages required"}, status_code=400)

    action_id = data.get("action_id") or f"act-adopt-{uuid.uuid4().hex[:8]}"
    request_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    executor_instance_id = SERVER_INSTANCE_ID
    executor_pid = os.getpid()
    executor_start_time = get_process_start_time(executor_pid) or 0
    fencing_token = 1

    lock_file = LOCKS_DIR / f"action_{action_id}.lock"
    lock_fd = None
    try:
        lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return JSONResponse(
                {"detail": f"Action {action_id} is currently executing on another worker"},
                status_code=409,
            )

        conn = task_registry._get_connection()
        try:
            existing = conn.execute(
                "SELECT state, request_hash, response_json, error_message FROM action_log WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        finally:
            conn.close()

        if existing:
            ex_state, ex_req_hash, ex_resp, ex_err = existing[0], existing[1], existing[2], existing[3]
            if ex_state == "COMPLETE":
                if ex_req_hash != request_hash:
                    return JSONResponse({"detail": "action_id reused with different request payload"}, status_code=409)
                cached_res = json.loads(ex_resp) if ex_resp else {}
                return JSONResponse({"ok": True, "result": cached_res})
            elif ex_state == "FAILED":
                return JSONResponse({"detail": f"Action previously failed: {ex_err}"}, status_code=500)
            elif ex_state in ("EXECUTING", "RECOVERING"):
                return JSONResponse({"detail": f"Action {action_id} is currently in progress"}, status_code=409)
            else:
                return JSONResponse({"detail": f"Action {action_id} in unexpected state: {ex_state}"}, status_code=409)

        now_iso = datetime.now(timezone.utc).isoformat()
        manifest = {"scope": scope, "implementation_stages": implementation_stages}
        conn = task_registry._get_connection()
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
                        ?, ?, 'adopt_scope', 'EXECUTING', ?,
                        ?, ?, NULL, ?,
                        ?, ?, ?,
                        NULL, NULL, NULL, ?,
                        ?, NULL, NULL,
                        ?, ?
                    );
                    """,
                    (
                        action_id,
                        task_id,
                        action_id,
                        request_hash,
                        json.dumps(manifest),
                        action_id,
                        executor_instance_id,
                        executor_pid,
                        executor_start_time,
                        fencing_token,
                        now_iso,
                        now_iso,
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        try:
            res = await adopt_scope(
                task["worktree_path"],
                scope=scope,
                implementation_stages=implementation_stages,
                action_id=action_id,
                request_hash=request_hash,
                fencing_token=fencing_token,
                executor_instance_id=executor_instance_id,
                lock_fd=lock_fd,
            )
            comp_iso = datetime.now(timezone.utc).isoformat()
            c_conn = task_registry._get_connection()
            try:
                with c_conn:
                    c_conn.execute(
                        """
                        UPDATE action_log
                        SET state = 'COMPLETE',
                            response_json = ?,
                            updated_utc = ?
                        WHERE action_id = ?
                          AND state = 'EXECUTING'
                          AND fencing_token = ?
                          AND executor_instance_id = ?;
                        """,
                        (json.dumps(res), comp_iso, action_id, fencing_token, executor_instance_id),
                    )
            finally:
                c_conn.close()
            return JSONResponse({"ok": True, "result": res})
        except SubprocessClientError as exc:
            fail_iso = datetime.now(timezone.utc).isoformat()
            f_conn = task_registry._get_connection()
            try:
                with f_conn:
                    f_conn.execute(
                        """
                        UPDATE action_log
                        SET state = 'FAILED',
                            error_message = ?,
                            updated_utc = ?
                        WHERE action_id = ?
                          AND state = 'EXECUTING'
                          AND fencing_token = ?
                          AND executor_instance_id = ?;
                        """,
                        (str(exc), fail_iso, action_id, fencing_token, executor_instance_id),
                    )
            finally:
                f_conn.close()
            return JSONResponse({"detail": str(exc)}, status_code=502)
        except Exception as exc:
            fail_iso = datetime.now(timezone.utc).isoformat()
            f_conn = task_registry._get_connection()
            try:
                with f_conn:
                    f_conn.execute(
                        """
                        UPDATE action_log
                        SET state = 'FAILED',
                            error_message = ?,
                            updated_utc = ?
                        WHERE action_id = ?
                          AND state = 'EXECUTING'
                          AND fencing_token = ?
                          AND executor_instance_id = ?;
                        """,
                        (str(exc), fail_iso, action_id, fencing_token, executor_instance_id),
                    )
            finally:
                f_conn.close()
            return JSONResponse({"detail": f"Failed to adopt scope: {exc}"}, status_code=500)
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                os.close(lock_fd)
            except Exception:
                pass


async def create_review_endpoint(request: Request) -> Response:
    """Create a content-bound review record derived authoritatively server-side."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    stage4_err = _check_stage4_forbidden(task.get("work_item"))
    if stage4_err:
        return stage4_err

    data = {}
    try:
        data = await request.json()
    except Exception:
        pass

    try:
        ctx = await get_review_context(task["worktree_path"])
        plan_proj = await get_plan_projection(task["worktree_path"])
    except SubprocessClientError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to read gate state: {exc}"}, status_code=500)

    gate = ctx.get("gate")
    if not gate or gate.get("scope") != "PLAN":
        return JSONResponse({"detail": "No pending PLAN gate for this task"}, status_code=400)

    auth_gate_id = gate.get("gate_id")
    auth_plan_revision_hash = ctx.get("plan_revision_hash") or ""
    auth_scope_hash = ctx.get("scope_hash") or ""
    auth_roles_hash = ctx.get("roles_hash") or ""
    plan_text = plan_proj.get("plan_text") or ""
    data_to_hash = (plan_text + auth_scope_hash + auth_roles_hash).encode("utf-8")
    auth_content_fingerprint = hashlib.sha256(data_to_hash).hexdigest()

    # If client supplied values, strictly validate against server-derived authoritative values
    client_gate_id = data.get("gate_id")
    client_plan_hash = data.get("plan_revision_hash")
    client_scope_hash = data.get("scope_hash")
    client_roles_hash = data.get("roles_hash")
    client_fingerprint = data.get("content_fingerprint")

    if client_gate_id and client_gate_id != auth_gate_id:
        return JSONResponse(
            {"detail": f"gate_id mismatch: client {client_gate_id!r} != server {auth_gate_id!r}"},
            status_code=409,
        )
    if client_plan_hash and client_plan_hash != auth_plan_revision_hash:
        return JSONResponse(
            {"detail": "plan_revision_hash mismatch with authoritative server state"},
            status_code=409,
        )
    if client_scope_hash and client_scope_hash != auth_scope_hash:
        return JSONResponse(
            {"detail": "scope_hash mismatch with authoritative server state"},
            status_code=409,
        )
    if client_roles_hash and client_roles_hash != auth_roles_hash:
        return JSONResponse(
            {"detail": "roles_hash mismatch with authoritative server state"},
            status_code=409,
        )
    if client_fingerprint and client_fingerprint != auth_content_fingerprint:
        return JSONResponse(
            {"detail": "content_fingerprint mismatch with authoritative server state"},
            status_code=409,
        )

    user = getattr(request.state, "user", "operator")
    record = task_registry.create_review_record(
        task_id=task_id,
        gate_id=auth_gate_id,
        plan_revision_hash=auth_plan_revision_hash,
        scope_hash=auth_scope_hash,
        roles_hash=auth_roles_hash,
        content_fingerprint=auth_content_fingerprint,
        reviewed_by=user,
    )
    return JSONResponse({"ok": True, "review": record})


async def approve_plan_endpoint(request: Request) -> Response:
    """Grant approval for a plan without dispatching tasks."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    stage4_err = _check_stage4_forbidden(task.get("work_item"))
    if stage4_err:
        return stage4_err

    data = {}
    try:
        data = await request.json()
    except Exception:
        pass

    try:
        ctx = await get_review_context(task["worktree_path"])
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to read gate state: {exc}"}, status_code=502)

    gate = ctx.get("gate")
    if not gate or gate.get("scope") != "PLAN":
        return JSONResponse({"detail": "No pending PLAN gate for this task"}, status_code=400)

    gate_id = gate.get("gate_id")
    review_record = task_registry.get_active_review_for_gate(task_id, gate_id)
    if not review_record:
        return JSONResponse(
            {"detail": "No active review snapshot found for this gate. Please create a review first."},
            status_code=400,
        )

    # Validate review record bindings match current gate hashes
    if (
        review_record["plan_revision_hash"] != ctx.get("plan_revision_hash")
        or review_record["scope_hash"] != ctx.get("scope_hash")
        or review_record["roles_hash"] != ctx.get("roles_hash")
    ):
        return JSONResponse(
            {"detail": "Review snapshot hashes do not match current pending gate. Re-review required."},
            status_code=409,
        )

    action_id = data.get("action_id") or f"act-approve-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    current_user = getattr(request.state, "user", "operator")

    token = {
        "schema_version": 2,
        "token_id": f"tok-{uuid.uuid4().hex[:12]}",
        "gate_id": gate_id,
        "work_item": task["work_item"],
        "scope": "PLAN",
        "stages": [ctx.get("current_stage") or "1"],
        "plan_revision_hash": review_record["plan_revision_hash"],
        "scope_hash": review_record["scope_hash"],
        "roles_hash": review_record["roles_hash"],
        "repository_id": str(task["worktree_path"]),
        "branch": task["task_branch"],
        "status": "ISSUED",
        "issued_by": current_user,
        "issued_utc": now_iso,
    }

    request_hash = hashlib.sha256(json.dumps(token, sort_keys=True).encode()).hexdigest()
    executor_instance_id = SERVER_INSTANCE_ID
    executor_pid = os.getpid()
    executor_start_time = get_process_start_time(executor_pid) or 0
    fencing_token = 1

    lock_file = LOCKS_DIR / f"action_{action_id}.lock"
    lock_fd = None
    try:
        lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return JSONResponse(
                {"detail": f"Action {action_id} is currently executing on another worker"},
                status_code=409,
            )

        conn = task_registry._get_connection()
        try:
            existing = conn.execute(
                "SELECT state, request_hash, response_json, error_message FROM action_log WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        finally:
            conn.close()

        if existing:
            ex_state, ex_req_hash, ex_resp, ex_err = existing[0], existing[1], existing[2], existing[3]
            if ex_state == "COMPLETE":
                cached_res = json.loads(ex_resp) if ex_resp else {}
                return JSONResponse({"ok": True, "result": cached_res})
            elif ex_state == "FAILED":
                return JSONResponse({"detail": f"Action previously failed: {ex_err}"}, status_code=500)
            elif ex_state in ("EXECUTING", "RECOVERING"):
                return JSONResponse({"detail": f"Action {action_id} is currently in progress"}, status_code=409)
            else:
                return JSONResponse({"detail": f"Action {action_id} in unexpected state: {ex_state}"}, status_code=409)

        conn = task_registry._get_connection()
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
                        ?, ?, 'approve_plan', 'EXECUTING', ?,
                        ?, ?, NULL, ?,
                        ?, ?, ?,
                        NULL, NULL, NULL, ?,
                        ?, NULL, NULL,
                        ?, ?
                    );
                    """,
                    (
                        action_id,
                        task_id,
                        action_id,
                        request_hash,
                        json.dumps(token),
                        action_id,
                        executor_instance_id,
                        executor_pid,
                        executor_start_time,
                        fencing_token,
                        now_iso,
                        now_iso,
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        try:
            res = await approve_plan(
                task["worktree_path"],
                token=token,
                action_id=action_id,
                fencing_token=fencing_token,
                executor_instance_id=executor_instance_id,
                lock_fd=lock_fd,
            )
            task_registry.mark_review_used(review_record["review_id"])
            comp_iso = datetime.now(timezone.utc).isoformat()
            c_conn = task_registry._get_connection()
            try:
                with c_conn:
                    c_conn.execute(
                        """
                        UPDATE action_log
                        SET state = 'COMPLETE',
                            response_json = ?,
                            updated_utc = ?
                        WHERE action_id = ?
                          AND state = 'EXECUTING'
                          AND fencing_token = ?
                          AND executor_instance_id = ?;
                        """,
                        (json.dumps(res), comp_iso, action_id, fencing_token, executor_instance_id),
                    )
            finally:
                c_conn.close()
            return JSONResponse({"ok": True, "result": res})
        except SubprocessClientError as exc:
            fail_iso = datetime.now(timezone.utc).isoformat()
            f_conn = task_registry._get_connection()
            try:
                with f_conn:
                    f_conn.execute(
                        """
                        UPDATE action_log
                        SET state = 'FAILED',
                            error_message = ?,
                            updated_utc = ?
                        WHERE action_id = ?
                          AND state = 'EXECUTING'
                          AND fencing_token = ?
                          AND executor_instance_id = ?;
                        """,
                        (str(exc), fail_iso, action_id, fencing_token, executor_instance_id),
                    )
            finally:
                f_conn.close()
            return JSONResponse({"detail": str(exc)}, status_code=502)
        except Exception as exc:
            fail_iso = datetime.now(timezone.utc).isoformat()
            f_conn = task_registry._get_connection()
            try:
                with f_conn:
                    f_conn.execute(
                        """
                        UPDATE action_log
                        SET state = 'FAILED',
                            error_message = ?,
                            updated_utc = ?
                        WHERE action_id = ?
                          AND state = 'EXECUTING'
                          AND fencing_token = ?
                          AND executor_instance_id = ?;
                        """,
                        (str(exc), fail_iso, action_id, fencing_token, executor_instance_id),
                    )
            finally:
                f_conn.close()
            return JSONResponse({"detail": f"Failed to approve plan: {exc}"}, status_code=500)
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                os.close(lock_fd)
            except Exception:
                pass


async def get_task_ai_context(request: Request) -> Response:
    """Retrieve AI conventions, sprint memory, and file provenance."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    try:
        ai_ctx = await get_ai_context(task["worktree_path"])
        db_prov = task_registry.get_context_provenance(task_id)
        if db_prov:
            ai_ctx["provenance"] = db_prov
        return JSONResponse(ai_ctx)
    except SubprocessClientError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to get AI context: {exc}"}, status_code=500)


async def get_context_summary(request: Request) -> Response:
    """Return context summary and files status across base repository."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    context_files = [
        "AGENTS.md",
        "SESSION_MEMORY.md",
        "docs/ai/SCHEMA_FACTS.md",
        "docs/ai/CODING_PATTERNS.md",
        "docs/ai/CONTEXT_INDEX.md",
    ]
    summary = []
    for rel_p in context_files:
        f = REPO_ROOT / rel_p
        exists = f.is_file()
        sha = hashlib.sha256(f.read_bytes()).hexdigest() if exists else None
        summary.append({
            "path": rel_p,
            "exists": exists,
            "is_mandatory": rel_p in ("AGENTS.md", "SESSION_MEMORY.md"),
            "sha256": sha,
        })
    return JSONResponse({"context_files": summary})


async def index(request: Request) -> Response:
    """Serve the single-page dashboard HTML."""
    template_path = DASHBOARD_DIR / "templates" / "index.html"
    if not template_path.is_file():
        return HTMLResponse("<h1>Dashboard template not found</h1>", status_code=500)
    return HTMLResponse(template_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: Starlette):
    # 1. Startup: Validate full ancestor chain and canonical registry
    validate_and_bind_canonical_registry(
        CANONICAL_REGISTRY_PATH, is_test_mode=DASHBOARD_TEST_MODE
    )

    # 2. Startup Lifespan Reconciliation under Action Lock -> Execution Lock Hierarchy
    conn = task_registry._get_connection()
    try:
        cur = conn.execute(
            "SELECT action_id, state, executor_instance_id, executor_pid, executor_start_time, child_pid, child_start_time, fencing_token FROM action_log WHERE state IN ('EXECUTING', 'RECOVERING');"
        )
        unresolved_rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    for row in unresolved_rows:
        act_id = row["action_id"]
        lock_file = LOCKS_DIR / f"bootstrap_{act_id}.lock"
        if not lock_file.exists():
            lock_file = LOCKS_DIR / f"action_{act_id}.lock"
        lock_fd = None
        try:
            lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                # Lock is held by live executor or inherited child process! Leave row untouched.
                continue

            # Under Action Lock: Verify process liveness with start times
            parent_alive = is_process_alive_with_start_time(row["executor_pid"], row["executor_start_time"])
            child_alive = is_process_alive_with_start_time(row["child_pid"], row["child_start_time"])

            if parent_alive or child_alive:
                # Still running or child still alive
                continue

            # BOTH are confirmed dead: atomic conditional update matching observed tuple
            now_iso = datetime.now(timezone.utc).isoformat()
            r_conn = task_registry._get_connection()
            try:
                with r_conn:
                    r_conn.execute(
                        """
                        UPDATE action_log
                        SET state = 'EXECUTING_UNKNOWN',
                            fencing_token = fencing_token + 1,
                            updated_utc = ?
                        WHERE action_id = ?
                          AND state = ?
                          AND executor_instance_id = ?
                          AND fencing_token = ?;
                        """,
                        (now_iso, act_id, row["state"], row["executor_instance_id"], row["fencing_token"]),
                    )
            finally:
                r_conn.close()
        except Exception:
            pass
        finally:
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except Exception:
                    pass
                try:
                    os.close(lock_fd)
                except Exception:
                    pass

    # Start coordinator background polling
    if not os.environ.get("DASHBOARD_DISABLE_COORDINATOR"):
        coordinator.start()
    yield
    # Shutdown
    if not os.environ.get("DASHBOARD_DISABLE_COORDINATOR"):
        await coordinator.stop()


async def get_task_findings(request: Request) -> Response:
    """Retrieve findings and backlog projection."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    try:
        res = await query_findings(task["worktree_path"])
        return JSONResponse(res)
    except SubprocessClientError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to get findings: {exc}"}, status_code=500)


async def get_task_evidence(request: Request) -> Response:
    """List available evidence artifacts."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    try:
        res = await query_evidence_list(task["worktree_path"])
        return JSONResponse(res)
    except SubprocessClientError as exc:
        err_str = str(exc)
        if "unsafe permissions" in err_str.lower():
            return JSONResponse({"detail": "evidence unavailable: unsafe permissions"}, status_code=403)
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to list evidence: {exc}"}, status_code=500)


async def get_task_evidence_file(request: Request) -> Response:
    """Read a specific evidence file with descriptor-relative validation."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    filename = request.path_params["filename"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    try:
        res = await query_evidence_content(task["worktree_path"], filename)
        return JSONResponse(res)
    except SubprocessClientError as exc:
        err_str = str(exc)
        if "unsafe permissions" in err_str.lower():
            return JSONResponse({"detail": "evidence unavailable: unsafe permissions"}, status_code=403)
        if "not permitted" in err_str.lower() or "invalid filename" in err_str.lower() or "invalid relative" in err_str.lower():
            return JSONResponse({"detail": str(exc)}, status_code=400)
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to read evidence: {exc}"}, status_code=500)


async def get_task_diff(request: Request) -> Response:
    """Retrieve git diff projection against stored configuration base commit."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    try:
        res = await query_diff(task["worktree_path"])
        return JSONResponse(res)
    except SubprocessClientError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to get diff: {exc}"}, status_code=500)


async def get_task_settings(request: Request) -> Response:
    """Retrieve read-only role configurations and escalation counters."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    try:
        res = await query_settings(task["worktree_path"])
        return JSONResponse(res)
    except SubprocessClientError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to get settings: {exc}"}, status_code=500)


async def export_task_audit(request: Request) -> Response:
    """Export sanitized audit event ledger as JSON Lines."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    work_item = task.get("work_item") or task_id
    try:
        res = await query_audit_events(task["worktree_path"], max_events=1000, max_bytes=524288)
        events = res.get("events", [])
        meta = res.get("metadata", {})

        lines = [json.dumps(ev, ensure_ascii=False) for ev in events]
        lines.append(json.dumps({"_metadata": meta}, ensure_ascii=False))
        content = "\n".join(lines) + "\n"

        headers = {
            "Content-Type": "application/x-ndjson",
            "Content-Disposition": f'attachment; filename="{work_item}_audit.jsonl"',
            "X-Audit-Truncated": str(meta.get("truncated", False)).lower(),
            "X-Audit-Truncation-Reason": str(meta.get("truncation_reason") or ""),
            "X-Audit-Events-Count": str(len(events)),
            "X-Audit-Bytes": str(meta.get("emitted_bytes", len(content.encode("utf-8")))),
        }
        return Response(content=content, media_type="application/x-ndjson", headers=headers)
    except SubprocessClientError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to export audit: {exc}"}, status_code=500)


async def export_task_state(request: Request) -> Response:
    """Export state projection as JSON."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    work_item = task.get("work_item") or task_id
    try:
        state = await get_state_projection(task["worktree_path"])
        content = json.dumps(state, indent=2, ensure_ascii=False)
        headers = {
            "Content-Type": "application/json",
            "Content-Disposition": f'attachment; filename="{work_item}_state.json"',
        }
        return Response(content=content, media_type="application/json", headers=headers)
    except SubprocessClientError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to export state: {exc}"}, status_code=500)


async def export_task_reviews(request: Request) -> Response:
    """Export review records for a task as JSON."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    task_id = request.path_params["task_id"]
    task = task_registry.get_task(task_id)
    if not task:
        return JSONResponse({"detail": "Task not found"}, status_code=404)

    work_item = task.get("work_item") or task_id
    try:
        reviews = task_registry.get_reviews_for_task(task_id)
        content = json.dumps({"task_id": task_id, "work_item": work_item, "reviews": reviews}, indent=2, default=str)
        headers = {
            "Content-Type": "application/json",
            "Content-Disposition": f'attachment; filename="{work_item}_reviews.json"',
        }
        return Response(content=content, media_type="application/json", headers=headers)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to export reviews: {exc}"}, status_code=500)


async def get_erp_projection(request: Request) -> Response:
    """Read-only inspection of authoritative Stage 4 manifest with integrity disclosure."""
    auth_err = _require_auth(request)
    if auth_err:
        return auth_err

    try:
        res = read_authoritative_stage4_manifest()
        return JSONResponse(res)
    except SecurityError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=403)
    except Exception as exc:
        return JSONResponse({"detail": f"Failed to read Stage 4 manifest: {exc}"}, status_code=500)


# ---------------------------------------------------------------------------
# Application Initialization & Routes
# ---------------------------------------------------------------------------

routes = [
    Route("/", endpoint=index, methods=["GET"]),
    Route("/api/auth/csrf-token", endpoint=get_csrf_token, methods=["GET"]),
    Route("/api/auth/login", endpoint=login, methods=["POST"]),
    Route("/api/auth/setup-password", endpoint=setup_password, methods=["POST"]),
    Route("/api/auth/logout", endpoint=logout, methods=["POST"]),
    Route("/api/auth/me", endpoint=me, methods=["GET"]),
    Route("/api/context/summary", endpoint=get_context_summary, methods=["GET"]),
    Route("/api/tasks", endpoint=list_tasks, methods=["GET"]),
    Route("/api/tasks/register", endpoint=register_task, methods=["POST"]),
    Route("/api/tasks/bootstrap", endpoint=bootstrap_task_endpoint, methods=["POST"]),
    Route("/api/tasks/{task_id}", endpoint=get_task_detail, methods=["GET"]),
    Route("/api/tasks/{task_id}", endpoint=unregister_task, methods=["DELETE"]),
    Route("/api/tasks/{task_id}/state", endpoint=get_task_state, methods=["GET"]),
    Route("/api/tasks/{task_id}/plan", endpoint=get_task_plan, methods=["GET"]),
    Route("/api/tasks/{task_id}/review-context", endpoint=get_task_review_context, methods=["GET"]),
    Route("/api/tasks/{task_id}/adopt-scope", endpoint=adopt_scope_endpoint, methods=["POST"]),
    Route("/api/tasks/{task_id}/create-review", endpoint=create_review_endpoint, methods=["POST"]),
    Route("/api/tasks/{task_id}/approve-plan", endpoint=approve_plan_endpoint, methods=["POST"]),
    Route("/api/tasks/{task_id}/ai-context", endpoint=get_task_ai_context, methods=["GET"]),
    Route("/api/tasks/{task_id}/findings", endpoint=get_task_findings, methods=["GET"]),
    Route("/api/tasks/{task_id}/evidence", endpoint=get_task_evidence, methods=["GET"]),
    Route("/api/tasks/{task_id}/evidence/{filename}", endpoint=get_task_evidence_file, methods=["GET"]),
    Route("/api/tasks/{task_id}/diff", endpoint=get_task_diff, methods=["GET"]),
    Route("/api/tasks/{task_id}/settings", endpoint=get_task_settings, methods=["GET"]),
    Route("/api/tasks/{task_id}/export/audit", endpoint=export_task_audit, methods=["GET"]),
    Route("/api/tasks/{task_id}/export/state", endpoint=export_task_state, methods=["GET"]),
    Route("/api/tasks/{task_id}/export/reviews", endpoint=export_task_reviews, methods=["GET"]),
    Route("/api/erp/projection", endpoint=get_erp_projection, methods=["GET"]),
    Mount("/static", app=StaticFiles(directory=str(DASHBOARD_DIR / "static")), name="static"),
]

# Configure Starlette app with middleware stack:
raw_app = Starlette(
    routes=routes,
    lifespan=lifespan,
    middleware=[
        Middleware(SessionAuthenticationMiddleware),
        Middleware(OriginAndCSRFMiddleware),
    ],
)

# Outermost HostValidationMiddleware wraps raw Starlette ASGI application
app = HostValidationMiddleware(raw_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
