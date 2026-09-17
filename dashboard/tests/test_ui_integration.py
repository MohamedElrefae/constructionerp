"""Playwright DOM integration test for Plain-Text Contract, Network Isolation, and Truthful Display."""

import asyncio
import json
import os
from pathlib import Path
import threading
import time
import pytest
from datetime import datetime, timezone
import uvicorn
from playwright.async_api import async_playwright

from dashboard.app import app
from dashboard.auth import (
    auth_store,
    create_initial_credentials_file,
    hash_password,
    session_manager,
)


@pytest.fixture(scope="module")
def live_server():
    """Run uvicorn server in background thread for browser testing."""
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    os.environ["no_proxy"] = "127.0.0.1,localhost"
    os.environ["DASHBOARD_DISABLE_COORDINATOR"] = "1"
    port = 8080

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to become responsive
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if server.started:
            break
        time.sleep(0.05)

    yield port

    server.should_exit = True
    thread.join(timeout=3)


@pytest.mark.anyio
async def test_ui_plain_text_contract_and_network_isolation(live_server):
    """Verify Playwright DOM rendering adheres strictly to plain-text contract and network isolation."""
    server_port = live_server
    base_url = f"http://localhost:{server_port}"
    task_id = "test-worktree-task"

    # Malicious plan payloads designed to trigger XSS or network requests if rendered via innerHTML/markdown
    malicious_payload = (
        '# Malicious Plan Injection\n\n'
        '<img src="/injected_image.png" onerror="alert(\'xss_img\')">\n'
        '<script>alert("xss_script")</script>\n'
        '<a href="javascript:alert(\'xss_link\')">Click Here</a>\n'
        '[click](javascript:alert((1)))\n'
        '> [target]: javascript:alert(1)\n'
    )

    EXPECTED_URL_PREFIXES = {
        f"{base_url}/",
        f"{base_url}/static/app.css",
        f"{base_url}/static/app.js",
        f"{base_url}/api/auth/csrf-token",
        f"{base_url}/api/auth/me",
        f"{base_url}/api/auth/login",
        f"{base_url}/api/auth/setup-password",
        f"{base_url}/api/tasks",
        f"{base_url}/api/tasks/{task_id}/state",
        f"{base_url}/api/tasks/{task_id}/plan",
        f"{base_url}/api/tasks/{task_id}/review-context",
        f"{base_url}/api/tasks/{task_id}/ai-context",
        f"{base_url}/favicon.ico",
    }

    recorded_requests = []
    dialog_events = []

    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            chromium_sandbox=True,
        )

        context = await browser.new_context()
        page = await context.new_page()

        # Monitor all network requests
        page.on("request", lambda req: recorded_requests.append(req.url))
        page.on("dialog", lambda d: dialog_events.append(d.message))

        # Mock API responses for plan and state
        state_data = {
            "work_item": "test-work-item",
            "branch": "feature/test",
            "status": "DRAFT",
            "plan_granted": False,
            "stages": {
                "0": {"status": "INITIALIZED", "historical": True},
                "1": {"status": "PLAN_SUBMITTED", "historical": False},
            },
            "active_jobs": [
                {"role": "architect", "status": None},  # Missing status -> must be 'Unknown'
                {"role": None, "status": "RUNNING"},    # Missing role -> must be 'Role: Unspecified'
            ],
            "next_roles": ["reviewer"],
        }

        async def route_handler(route):
            url = route.request.url
            if f"/api/tasks/{task_id}/state" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(state_data),
                )
            elif f"/api/tasks/{task_id}/plan" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "plan_text": malicious_payload,
                        "format": "plain_text",
                        "render_mode": "text_content",
                    }),
                )
            elif f"/api/tasks/{task_id}/review-context" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"plan_revision_hash": "a"*64, "scope_hash": "b"*64, "roles_hash": "c"*64, "gate": None, "proposal": None}),
                )
            elif f"/api/tasks/{task_id}/ai-context" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"session_memory_md": "", "provenance": []}),
                )
            elif "/api/tasks" in url and route.request.method == "GET":
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps([{
                        "task_id": task_id,
                        "work_item": "test-work-item",
                        "task_branch": "feature/test",
                        "cached_status": "DRAFT",
                        "cached_stage": "plan",
                    }]),
                )
            elif "/api/auth/me" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"authenticated": True, "username": "engineer"}),
                )
            else:
                await route.continue_()

        await page.route(f"{base_url}/api/**", route_handler)

        # Navigate to dashboard
        await page.goto(base_url)
        await page.wait_for_selector("#tasks-tbody")

        # Inspect the task and switch to Plan tab
        await page.click("button:has-text('Inspect')")
        await page.click(".tab-btn[data-tab='tab-plan']")
        await page.wait_for_selector("#plan-display")

        # Give client JS time to finish DOM updates
        await page.wait_for_timeout(500)

        # 1. Assert Plain-Text Contract:
        # Zero <img>, <script>, or <a> tags injected inside #plan-display
        container_html = await page.inner_html("#plan-display")
        assert "<img" not in container_html.lower()
        assert "<script" not in container_html.lower()
        assert "<a" not in container_html.lower()

        # Text content must match raw plain text exactly
        container_text = await page.text_content("#plan-display")
        assert container_text == malicious_payload

        # Zero alert / dialog events triggered
        assert len(dialog_events) == 0

        # 2. Assert Strict Network Isolation:
        # Every single recorded request must be in the expected allowlist
        for req_url in recorded_requests:
            is_allowed = any(
                req_url == prefix or req_url.startswith(prefix + "?")
                for prefix in EXPECTED_URL_PREFIXES
            )
            assert is_allowed, f"Violation of Network Isolation: unexpected request to {req_url}"

        # 3. Assert Truthful Display:
        # Plan title when plan_granted is False
        title_text = await page.text_content("#plan-title")
        assert title_text == "Proposed Plan (Pending Approval)"

        # Missing active job status rendered strictly as "Unknown" (never "Pending")
        jobs_html = await page.inner_html("#jobs-container")
        assert "Unknown" in jobs_html
        assert "Pending" not in jobs_html
        assert "Role: Unspecified" in jobs_html

        # Historical stage indicator present
        stages_html = await page.inner_html("#stages-container")
        assert "(historical)" in stages_html

        # Test plan_granted: True update
        state_data["plan_granted"] = True
        await page.evaluate("() => refreshTaskDetail()")
        await page.wait_for_timeout(300)
        approved_title_text = await page.text_content("#plan-title")
        assert approved_title_text == "Approved Plan"
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await p.stop()
        await asyncio.sleep(0.1)


@pytest.mark.anyio
async def test_ui_first_run_auth_and_permanent_password_setup(live_server):
    """Verify first-run login displays password setup UI, enforces valid permanent password, and transitions to tasks."""
    server_port = live_server
    base_url = f"http://localhost:{server_port}"

    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            chromium_sandbox=True,
        )
        context = await browser.new_context()
        page = await context.new_page()

        # State tracking for mocked API
        user_state = {
            "authenticated": False,
            "must_change_password": True,
            "password": "initial_password_123",
        }

        async def route_handler(route):
            url = route.request.url
            if "/api/auth/me" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "authenticated": user_state["authenticated"],
                        "username": "engineer" if user_state["authenticated"] else None,
                        "must_change_password": user_state["must_change_password"],
                    }),
                )
            elif "/api/auth/login" in url and route.request.method == "POST":
                req_data = json.loads(route.request.post_data)
                if req_data.get("username") == "engineer" and req_data.get("password") == user_state["password"]:
                    user_state["authenticated"] = True
                    await route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps({
                            "ok": True,
                            "username": "engineer",
                            "csrf_token": "mock_csrf_tok",
                            "must_change_password": user_state["must_change_password"],
                        }),
                    )
                else:
                    await route.fulfill(
                        status=401,
                        content_type="application/json",
                        body=json.dumps({"detail": "Invalid credentials"}),
                    )
            elif "/api/auth/setup-password" in url and route.request.method == "POST":
                req_data = json.loads(route.request.post_data)
                cur = req_data.get("current_password")
                new_pw = req_data.get("new_password")
                if cur != user_state["password"]:
                    await route.fulfill(
                        status=401,
                        content_type="application/json",
                        body=json.dumps({"detail": "Invalid current password"}),
                    )
                elif len(new_pw) < 12:
                    await route.fulfill(
                        status=400,
                        content_type="application/json",
                        body=json.dumps({"detail": "New permanent password must be at least 12 characters long"}),
                    )
                elif cur == new_pw:
                    await route.fulfill(
                        status=400,
                        content_type="application/json",
                        body=json.dumps({"detail": "New permanent password must be different from current password"}),
                    )
                else:
                    user_state["must_change_password"] = False
                    user_state["password"] = new_pw
                    await route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps({"ok": True, "detail": "Permanent password configured successfully"}),
                    )
            elif "/api/tasks" in url and route.request.method == "GET":
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps([]),
                )
            else:
                await route.continue_()

        await page.route(f"{base_url}/api/**", route_handler)

        await page.goto(base_url)
        await page.wait_for_selector("#auth-section")

        # 1. Fill and submit login form
        await page.fill("#login-username", "engineer")
        await page.fill("#login-password", "initial_password_123")
        await page.click("#login-form button[type='submit']")

        # 2. Verify transition to setup-password section
        await page.wait_for_selector("#setup-password-section", state="visible")
        auth_style = await page.eval_on_selector("#auth-section", "el => el.style.display")
        assert auth_style == "none"
        main_style = await page.eval_on_selector("#main-content", "el => el.style.display")
        assert main_style == "none"

        # Verify current password was pre-filled
        current_val = await page.input_value("#setup-current-password")
        assert current_val == "initial_password_123"

        # 3. Try submitting short password (<12 chars)
        await page.fill("#setup-new-password", "short")
        await page.click("#setup-password-form button[type='submit']")
        await page.wait_for_selector("#setup-password-error", state="visible")
        err_msg = await page.text_content("#setup-password-error")
        assert "at least 12 characters" in err_msg

        # 4. Submit valid permanent password
        await page.fill("#setup-new-password", "ValidPermanentPass2026!")
        await page.click("#setup-password-form button[type='submit']")

        # 5. Verify transition to main content (dashboard tasks)
        await page.wait_for_selector("#main-content", state="visible")
        setup_style = await page.eval_on_selector("#setup-password-section", "el => el.style.display")
        assert setup_style == "none"
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await p.stop()
        await asyncio.sleep(0.1)


@pytest.mark.anyio
async def test_ui_unmocked_end_to_end_auth_and_setup(live_server):
    """Verify real, unmocked browser authentication flow:
    
    1. Reads actual credentials from initial_credentials.txt.
    2. Submits unmocked POST /api/auth/login with CSRF and Host headers.
    3. Browser handles real SameSite=Strict, Secure=True cookies.
    4. Submits unmocked POST /api/auth/setup-password with valid permanent password.
    5. Verifies initial_credentials.txt is unlinked on disk.
    6. Verifies browser transitions to main dashboard where unmocked /api/tasks succeeds.
    7. Tests logout and verifies old credentials fail while permanent credentials succeed.
    """
    # Ensure fresh initial credentials exist for unmocked flow
    session_manager._sessions.clear()
    if not auth_store.credentials_file_path.is_file():
        username, initial_password = create_initial_credentials_file(
            file_path=auth_store.credentials_file_path,
            username="engineer",
        )
        pw_hash = hash_password(initial_password)
        data = {
            "users": {
                username: {
                    "password_hash": pw_hash,
                    "created_utc": datetime.now(timezone.utc).isoformat(),
                    "is_initial": True,
                }
            }
        }
        auth_store._save_data(data)
    else:
        content = auth_store.credentials_file_path.read_text(encoding="utf-8")
        initial_password = ""
        for line in content.splitlines():
            if line.startswith("Password:"):
                initial_password = line.split(":", 1)[1].strip()
        data = auth_store._load_data()
        data["users"]["engineer"]["is_initial"] = True
        data["users"]["engineer"]["password_hash"] = hash_password(initial_password)
        auth_store._save_data(data)

    server_port = live_server
    base_url = f"http://localhost:{server_port}"

    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            chromium_sandbox=True,
        )
        context = await browser.new_context()
        page = await context.new_page()

        # ZERO page.route() - Every single request is REAL and unmocked!
        await page.goto(base_url)
        await page.wait_for_selector("#auth-section", state="visible")

        # 1. Fill and submit login form with real initial credentials
        await page.fill("#login-username", "engineer")
        await page.fill("#login-password", initial_password)
        await page.click("#login-form button[type='submit']")

        # 2. Wait for transition to setup-password section
        await page.wait_for_selector("#setup-password-section", state="visible")
        assert await page.eval_on_selector("#auth-section", "el => el.style.display") == "none"
        assert await page.eval_on_selector("#main-content", "el => el.style.display") == "none"

        # Verify real cookies stored by the browser
        cookies = await context.cookies()
        session_cookie = next((c for c in cookies if c["name"] == "dashboard_session"), None)
        csrf_cookie = next((c for c in cookies if c["name"] == "dashboard_csrf"), None)
        assert session_cookie is not None
        assert session_cookie["secure"] is True
        assert session_cookie["httpOnly"] is True
        assert session_cookie["sameSite"].lower() == "strict"
        assert csrf_cookie is not None
        assert csrf_cookie["secure"] is True
        assert csrf_cookie["sameSite"].lower() == "strict"

        # 3. Enter new permanent password and submit
        new_perm_pw = "RealPermanentPass2026!"
        await page.fill("#setup-new-password", new_perm_pw)
        await page.click("#setup-password-form button[type='submit']")

        # 4. Wait for transition to main dashboard content
        await page.wait_for_selector("#main-content", state="visible")
        assert await page.eval_on_selector("#setup-password-section", "el => el.style.display") == "none"

        # 5. Verify on disk that initial_credentials.txt is UNLINKED
        assert not auth_store.credentials_file_path.exists(), "initial_credentials.txt must be deleted after permanent password setup"

        # 6. Verify in auth store that is_initial is now False
        assert auth_store.is_initial_user("engineer") is False

        # 7. Verify tasks table container is displayed (GET /api/tasks succeeded unmocked)
        await page.wait_for_selector("#tasks-table-container", state="visible")

        # 8. Test logout
        await page.click("#logout-btn")
        await page.wait_for_selector("#auth-section", state="visible")

        # 9. Verify old initial password no longer works
        await page.fill("#login-username", "engineer")
        await page.fill("#login-password", initial_password)
        await page.click("#login-form button[type='submit']")
        await page.wait_for_selector("#login-error", state="visible")
        assert "Invalid credentials" in await page.text_content("#login-error")

        # 10. Verify new permanent password works and enters dashboard directly
        await page.fill("#login-username", "engineer")
        await page.fill("#login-password", new_perm_pw)
        await page.click("#login-form button[type='submit']")
        await page.wait_for_selector("#main-content", state="visible")
        assert await page.eval_on_selector("#setup-password-section", "el => el.style.display") == "none"
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await p.stop()
        await asyncio.sleep(0.1)
