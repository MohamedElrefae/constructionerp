"""API endpoint integration tests verifying read-only scope, auth, and contract."""

import json
from pathlib import Path
import pytest
import httpx

from dashboard.app import app
from dashboard.auth import auth_store, session_manager


@pytest.fixture
def auth_headers_and_cookies():
    """Create authenticated session and CSRF tokens for testing."""
    data = auth_store._load_data()
    if "users" not in data:
        data["users"] = {}
    if "engineer" not in data["users"]:
        data["users"]["engineer"] = {
            "password_hash": "scrypt$16384$8$1$00$00",
            "is_initial": False,
        }
    else:
        data["users"]["engineer"]["is_initial"] = False
    auth_store._save_data(data)

    session_token = session_manager.create_session("engineer")
    csrf_token = "valid_test_csrf_token"
    cookies = {
        "dashboard_session": session_token,
        "dashboard_csrf": csrf_token,
    }
    headers = {
        "host": "127.0.0.1:8080",
        "origin": "https://127.0.0.1:8080",
        "x-csrf-token": csrf_token,
    }
    return headers, cookies


@pytest.mark.anyio
async def test_unauthenticated_api_access_rejected():
    """Verify that unauthenticated requests to protected endpoints return 401."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080") as client:
        endpoints = [
            ("GET", "/api/tasks"),
            ("POST", "/api/tasks/register"),
            ("GET", "/api/tasks/any_id"),
            ("DELETE", "/api/tasks/any_id"),
            ("GET", "/api/tasks/any_id/state"),
            ("GET", "/api/tasks/any_id/plan"),
            ("POST", "/api/auth/setup-password"),
        ]
        client.cookies.set("dashboard_csrf", "csrf123")
        for method, path in endpoints:
            if method == "GET":
                resp = await client.get(path)
            elif method == "POST":
                resp = await client.post(path, json={"worktree_path": "."}, headers={"x-csrf-token": "csrf123", "origin": "https://127.0.0.1:8080"})
            elif method == "DELETE":
                resp = await client.delete(path, headers={"x-csrf-token": "csrf123", "origin": "https://127.0.0.1:8080"})
            assert resp.status_code == 401
            assert resp.json()["detail"] == "Authentication required"


@pytest.mark.anyio
async def test_secure_cookie_policy_enforced():
    """Verify that all response Set-Cookie headers contain the Secure flag."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080") as client:
        resp = await client.get("/api/auth/csrf-token")
        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "").lower()
        assert "secure" in set_cookie
        assert "samesite=strict" in set_cookie


@pytest.mark.anyio
async def test_absence_of_mutating_workflow_endpoints(auth_headers_and_cookies):
    """Verify strictly read-only scope: pause, resume, reset_budget routes DO NOT exist."""
    headers, cookies = auth_headers_and_cookies
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies) as client:
        mutating_paths = [
            "/api/tasks/task1/pause",
            "/api/tasks/task1/resume",
            "/api/tasks/task1/reset_budget",
            "/api/tasks/pause",
            "/api/tasks/resume",
            "/api/tasks/dispatch",
        ]
        for path in mutating_paths:
            resp = await client.post(path, json={}, headers=headers)
            # Route must not exist (404 or 405)
            assert resp.status_code in (404, 405)


@pytest.mark.anyio
async def test_task_lifecycle_api(auth_headers_and_cookies, isolated_worktree):
    """Test full read-only task API lifecycle using isolated worktree fixture (never live repository)."""
    headers, cookies = auth_headers_and_cookies
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies) as client:
        # 1. Register isolated mock worktree
        reg_resp = await client.post(
            "/api/tasks/register",
            json={"worktree_path": str(isolated_worktree)},
            headers=headers,
        )
        assert reg_resp.status_code == 200
        reg_data = reg_resp.json()
        assert reg_data["ok"] is True
        task_id = reg_data["task"]["task_id"]

        # 2. List tasks
        list_resp = await client.get("/api/tasks", headers=headers)
        assert list_resp.status_code == 200
        tasks = list_resp.json()
        assert any(t["task_id"] == task_id for t in tasks)

        # 3. Get task detail
        detail_resp = await client.get(f"/api/tasks/{task_id}", headers=headers)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["task_id"] == task_id

        # 4. Get state projection
        state_resp = await client.get(f"/api/tasks/{task_id}/state", headers=headers)
        assert state_resp.status_code == 200
        state_data = state_resp.json()
        assert "status" in state_data
        assert "stages" in state_data

        # 5. Get plan projection (verifying plain text contract)
        plan_resp = await client.get(f"/api/tasks/{task_id}/plan", headers=headers)
        assert plan_resp.status_code == 200
        plan_data = plan_resp.json()
        assert plan_data["format"] == "plain_text"
        assert plan_data["render_mode"] == "text_content"
        assert "plan_text" in plan_data
        assert "Isolated Test Plan" in plan_data["plan_text"]

        # 6. Unregister task
        del_resp = await client.delete(f"/api/tasks/{task_id}", headers=headers)
        assert del_resp.status_code == 200
        assert del_resp.json()["ok"] is True

        # Verify task no longer found
        detail_resp2 = await client.get(f"/api/tasks/{task_id}", headers=headers)
        assert detail_resp2.status_code == 404


@pytest.mark.anyio
async def test_permanent_password_setup_api(auth_headers_and_cookies):
    """Test POST /api/auth/setup-password validations and functionality."""
    headers, cookies = auth_headers_and_cookies
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies) as client:
        # Invalid payload
        resp = await client.post("/api/auth/setup-password", json={}, headers=headers)
        assert resp.status_code == 400

        # Short password (< 12 chars)
        resp = await client.post(
            "/api/auth/setup-password",
            json={"current_password": "any", "new_password": "short"},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "at least 12 characters" in resp.json()["detail"]

        # Same password
        resp = await client.post(
            "/api/auth/setup-password",
            json={"current_password": "same_password_123", "new_password": "same_password_123"},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "different from current" in resp.json()["detail"]


@pytest.mark.anyio
async def test_index_html_serving():
    """Verify that root GET / serves the dashboard single-page HTML."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "<title>Civil Engineer Dashboard</title>" in resp.text
        assert 'id="plan-display"' in resp.text
        assert 'id="setup-password-section"' in resp.text


@pytest.mark.anyio
async def test_initial_password_session_blocked_from_task_apis(isolated_worktree):
    """Verify that an initial-password session is rejected with 403 on all task endpoints until setup-password is completed."""
    # Configure user as an initial user
    data = auth_store._load_data()
    data["users"]["initial_engineer"] = {
        "password_hash": "scrypt$16384$8$1$00$00",
        "is_initial": True,
    }
    auth_store._save_data(data)

    session_token = session_manager.create_session("initial_engineer")
    csrf_token = "test_csrf_token_init"
    cookies = {
        "dashboard_session": session_token,
        "dashboard_csrf": csrf_token,
    }
    headers = {
        "host": "127.0.0.1:8080",
        "origin": "https://127.0.0.1:8080",
        "x-csrf-token": csrf_token,
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies) as client:
        # 1. Direct bypass attempt on GET /api/tasks
        resp = await client.get("/api/tasks", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Password setup required"

        # 2. Direct bypass attempt on POST /api/tasks/register
        resp = await client.post(
            "/api/tasks/register",
            json={"worktree_path": str(isolated_worktree)},
            headers=headers,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Password setup required"

        # 3. Direct bypass attempt on GET /api/tasks/{task_id}
        resp = await client.get("/api/tasks/task1", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Password setup required"

        # 4. Direct bypass attempt on GET /api/tasks/{task_id}/state
        resp = await client.get("/api/tasks/task1/state", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Password setup required"

        # 5. Direct bypass attempt on GET /api/tasks/{task_id}/plan
        resp = await client.get("/api/tasks/task1/plan", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Password setup required"

        # 6. Direct bypass attempt on DELETE /api/tasks/{task_id}
        resp = await client.delete("/api/tasks/task1", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Password setup required"

