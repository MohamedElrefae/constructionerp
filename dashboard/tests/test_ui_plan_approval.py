"""Playwright UI integration tests for Plan & Approval, Scope Adoption, and AI Context Inspector."""

import asyncio
import json
import os
import threading
import time
from datetime import datetime, timezone

import pytest
import uvicorn
from playwright.async_api import async_playwright

from dashboard.app import app


@pytest.fixture(scope="module")
def ui_live_server():
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

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if server.started:
            break
        time.sleep(0.05)

    yield port

    server.should_exit = True
    thread.join(timeout=3)


@pytest.mark.anyio
async def test_ui_three_tab_navigation(ui_live_server):
    """Verifies seamless switching across all 3 dashboard tabs."""
    base_url = f"http://localhost:{ui_live_server}"
    task_id = "task-ui-tabs"

    state_data = {
        "work_item": "test-tabs-item",
        "branch": "feature/test-tabs",
        "status": "DRAFT",
        "plan_granted": False,
        "stages": {"0": {"status": "INITIALIZED", "historical": True}},
        "active_jobs": [],
        "next_roles": ["architect"],
    }

    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            chromium_sandbox=True,
        )
        context = await browser.new_context()
        page = await context.new_page()

        async def route_handler(route):
            url = route.request.url
            if f"/api/tasks/{task_id}/state" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(state_data))
            elif f"/api/tasks/{task_id}/plan" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {"plan_text": "Tab test plan", "format": "plain_text", "render_mode": "text_content"}
                    ),
                )
            elif f"/api/tasks/{task_id}/review-context" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "gate": None,
                            "proposal": None,
                            "plan_revision_hash": "a" * 64,
                            "scope_hash": "b" * 64,
                            "roles_hash": "c" * 64,
                        }
                    ),
                )
            elif f"/api/tasks/{task_id}/ai-context" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"session_memory_md": "Sprint memory notes", "provenance": []}),
                )
            elif "/api/tasks" in url and route.request.method == "GET":
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        [
                            {
                                "task_id": task_id,
                                "work_item": "test-tabs-item",
                                "task_branch": "feature/test-tabs",
                                "cached_status": "DRAFT",
                                "cached_stage": "plan",
                            }
                        ]
                    ),
                )
            elif "/api/auth/csrf-token" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"csrf_token": "mock_csrf_token"}),
                )
            elif "/api/auth/me" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {"authenticated": True, "username": "engineer", "must_change_password": False}
                    ),
                )
            else:
                await route.continue_()

        await page.route(f"{base_url}/api/**", route_handler)
        await page.goto(base_url)
        await page.wait_for_selector("#tasks-tbody")

        # Open task inspection
        await page.click("button:has-text('Inspect')")
        await page.wait_for_selector("#task-detail-section", state="visible")

        # 1. Default active tab is Progress & Jobs
        assert await page.is_visible("#tab-progress")
        assert not await page.is_visible("#tab-plan")
        assert not await page.is_visible("#tab-context")

        # 2. Switch to Plan & Approval tab
        await page.click(".tab-btn[data-tab='tab-plan']")
        await page.wait_for_timeout(200)
        assert not await page.is_visible("#tab-progress")
        assert await page.is_visible("#tab-plan")
        assert not await page.is_visible("#tab-context")

        # 3. Switch to AI Context & Memory tab
        await page.click(".tab-btn[data-tab='tab-context']")
        await page.wait_for_timeout(200)
        assert not await page.is_visible("#tab-progress")
        assert not await page.is_visible("#tab-plan")
        assert await page.is_visible("#tab-context")

        # 4. Switch back to Progress tab
        await page.click(".tab-btn[data-tab='tab-progress']")
        await page.wait_for_timeout(200)
        assert await page.is_visible("#tab-progress")
        assert not await page.is_visible("#tab-plan")
        assert not await page.is_visible("#tab-context")
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await p.stop()
        await asyncio.sleep(0.1)


@pytest.mark.anyio
async def test_ui_plain_text_plan_and_scope_proposal_adoption(ui_live_server):
    """Verifies plain-text DOM contract for plan display and scope proposal adoption."""
    base_url = f"http://localhost:{ui_live_server}"
    task_id = "task-ui-adopt"

    proposal_data = {
        "scope": {
            "allowed_paths": ["docs/ai/work-items/test/**", "src/auth/**"],
            "requirements": ["R1: Scope portability"],
            "validation_commands": [["python3", "-c", "print('OK')"]],
        },
        "implementation_stages": ["stage1_backend", "stage2_frontend"],
    }

    state_data = {
        "work_item": "test-adopt-item",
        "branch": "feature/test-adopt",
        "status": "DRAFT",
        "plan_granted": False,
        "stages": {"0": {"status": "INITIALIZED", "historical": True}},
        "active_jobs": [],
        "next_roles": ["reviewer"],
    }

    malicious_plan = (
        "# Security Verification Plan\n\n"
        "<b onmouseover=\"alert('xss')\">Safe Hover</b>\n"
        '<img src="/xss.jpg" onerror="alert(\'img_xss\')">\n'
        "<script>alert('script_xss')</script>\n"
    )

    scope_adopted = False

    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            chromium_sandbox=True,
        )
        context = await browser.new_context()
        page = await context.new_page()

        async def route_handler(route):
            nonlocal scope_adopted
            url = route.request.url
            if f"/api/tasks/{task_id}/state" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(state_data))
            elif f"/api/tasks/{task_id}/plan" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "plan_text": malicious_plan,
                            "format": "plain_text",
                            "render_mode": "text_content",
                        }
                    ),
                )
            elif f"/api/tasks/{task_id}/review-context" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "gate": {"gate_id": "gate-adopt-1", "scope": "PLAN"},
                            "proposal": proposal_data,
                            "plan_revision_hash": "a" * 64,
                            "scope_hash": "b" * 64,
                            "roles_hash": "c" * 64,
                            "plan_granted": False,
                            "current_stage": "plan",
                        }
                    ),
                )
            elif f"/api/tasks/{task_id}/adopt-scope" in url and route.request.method == "POST":
                scope_adopted = True
                req = json.loads(route.request.post_data)
                assert req["scope"]["allowed_paths"] == proposal_data["scope"]["allowed_paths"]
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "ok": True,
                            "detail": "Scope proposal adopted successfully",
                        }
                    ),
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
                    body=json.dumps(
                        [
                            {
                                "task_id": task_id,
                                "work_item": "test-adopt-item",
                                "task_branch": "feature/test-adopt",
                                "cached_status": "DRAFT",
                                "cached_stage": "plan",
                            }
                        ]
                    ),
                )
            elif "/api/auth/csrf-token" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"csrf_token": "mock_csrf_token"}),
                )
            elif "/api/auth/me" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {"authenticated": True, "username": "engineer", "must_change_password": False}
                    ),
                )
            else:
                await route.continue_()

        await page.route(f"{base_url}/api/**", route_handler)
        await page.goto(base_url)
        await page.wait_for_selector("#tasks-tbody")

        # Inspect task and open Plan & Approval tab
        await page.click("button:has-text('Inspect')")
        await page.click(".tab-btn[data-tab='tab-plan']")
        await page.wait_for_selector("#plan-display", state="visible")

        # 1. Plain-text contract verification
        container_text = await page.text_content("#plan-display")
        assert container_text == malicious_plan
        container_html = await page.inner_html("#plan-display")
        assert "<img" not in container_html.lower()
        assert "<script" not in container_html.lower()

        # 2. Architect Scope Proposal verification
        await page.wait_for_selector("#adopt-scope-btn", state="visible")
        details_text = await page.text_content("#proposal-details")
        assert "src/auth/**" in details_text
        assert "R1: Scope portability" in details_text

        # 3. Adopt Scope Proposal action
        await page.click("#adopt-scope-btn")
        await page.wait_for_selector("#adopt-scope-msg", state="visible")
        msg_text = await page.text_content("#adopt-scope-msg")
        assert "Scope proposal adopted successfully" in msg_text
        assert scope_adopted is True
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await p.stop()
        await asyncio.sleep(0.1)


@pytest.mark.anyio
async def test_ui_review_snapshot_creation_and_gated_approval(ui_live_server):
    """Verifies review snapshot creation with SHA-256 fingerprint and gated approval flow."""
    base_url = f"http://localhost:{ui_live_server}"
    task_id = "task-ui-approval"

    plan_revision_hash = "11" * 32
    scope_hash = "22" * 32
    roles_hash = "33" * 32

    review_created = False
    plan_approved = False
    active_review_record = None

    state_data = {
        "work_item": "test-approval-item",
        "branch": "feature/test-approval",
        "status": "DRAFT",
        "plan_granted": False,
        "stages": {"0": {"status": "INITIALIZED", "historical": True}},
        "active_jobs": [],
        "next_roles": ["reviewer"],
    }

    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            chromium_sandbox=True,
        )
        context = await browser.new_context()
        page = await context.new_page()

        async def route_handler(route):
            nonlocal review_created, plan_approved, active_review_record
            url = route.request.url
            if f"/api/tasks/{task_id}/state" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(state_data))
            elif f"/api/tasks/{task_id}/plan" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "plan_text": "# Plan to be Approved\nDetailed steps.",
                            "format": "plain_text",
                            "render_mode": "text_content",
                        }
                    ),
                )
            elif f"/api/tasks/{task_id}/review-context" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "gate": {"gate_id": "gate-rev-1", "scope": "PLAN"},
                            "proposal": None,
                            "plan_revision_hash": plan_revision_hash,
                            "scope_hash": scope_hash,
                            "roles_hash": roles_hash,
                            "plan_granted": state_data["plan_granted"],
                            "current_stage": "plan",
                            "active_review": active_review_record,
                        }
                    ),
                )
            elif f"/api/tasks/{task_id}/create-review" in url and route.request.method == "POST":
                review_created = True
                req = json.loads(route.request.post_data)
                active_review_record = {
                    "review_id": "rev-test-1234",
                    "reviewed_by": "engineer",
                    "created_utc": "2026-09-17T12:00:00Z",
                    "content_fingerprint": req["content_fingerprint"],
                }
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "ok": True,
                            "review": active_review_record,
                        }
                    ),
                )
            elif f"/api/tasks/{task_id}/approve-plan" in url and route.request.method == "POST":
                plan_approved = True
                state_data["plan_granted"] = True
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "ok": True,
                            "detail": "Plan approved successfully",
                            "result": {"status": "already_complete"},
                        }
                    ),
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
                    body=json.dumps(
                        [
                            {
                                "task_id": task_id,
                                "work_item": "test-approval-item",
                                "task_branch": "feature/test-approval",
                                "cached_status": "DRAFT",
                                "cached_stage": "plan",
                            }
                        ]
                    ),
                )
            elif "/api/auth/csrf-token" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"csrf_token": "mock_csrf_token"}),
                )
            elif "/api/auth/me" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {"authenticated": True, "username": "engineer", "must_change_password": False}
                    ),
                )
            else:
                await route.continue_()

        await page.route(f"{base_url}/api/**", route_handler)
        await page.goto(base_url)
        await page.wait_for_selector("#tasks-tbody")

        # Inspect task and navigate to Plan & Approval tab
        await page.click("button:has-text('Inspect')")
        await page.click(".tab-btn[data-tab='tab-plan']")
        await page.wait_for_selector("#review-subcard", state="visible")

        # 1. Before review snapshot: "Create Review Snapshot" is visible, "Approve Plan" is hidden
        await page.wait_for_selector("#create-review-btn", state="visible")
        approve_visible = await page.is_visible("#approve-plan-btn")
        assert not approve_visible

        review_details = await page.text_content("#review-hashes-details")
        assert "gate-rev-1" in review_details
        assert plan_revision_hash in review_details

        # 2. Click "Create Review Snapshot"
        await page.click("#create-review-btn")
        await page.wait_for_timeout(400)
        assert review_created is True
        assert active_review_record is not None

        # 3. After review snapshot: "Create Review Snapshot" is hidden, "Approve Plan" is visible
        await page.wait_for_selector("#approve-plan-btn", state="visible")
        create_visible = await page.is_visible("#create-review-btn")
        assert not create_visible

        updated_review_details = await page.text_content("#review-hashes-details")
        assert "rev-test-1234" in updated_review_details
        assert active_review_record["content_fingerprint"] in updated_review_details

        # 4. Click "Approve Plan"
        await page.click("#approve-plan-btn")
        await page.wait_for_selector("#approval-msg", state="visible")
        approval_msg = await page.text_content("#approval-msg")
        assert "Plan approved successfully" in approval_msg
        assert plan_approved is True
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await p.stop()
        await asyncio.sleep(0.1)


@pytest.mark.anyio
async def test_ui_ai_context_inspector_and_clipboard_copy(ui_live_server):
    """Verifies AI Context Inspector display, file provenance table, and Copy Sprint Memory."""
    base_url = f"http://localhost:{ui_live_server}"
    task_id = "task-ui-context"

    session_memory_content = (
        "### Sprint 1 Notes\n- Architect proposed new boundary.\n- Reviewer validated R1.\n"
    )
    provenance_data = [
        {
            "path": "AGENTS.md",
            "is_mandatory": True,
            "exists": True,
            "sha256": "aaaa1111222233334444555566667777888899990000aaaabbbbccccddddeeee",
            "byte_count": 512,
            "mode": "ro-bind",
        },
        {
            "path": "SESSION_MEMORY.md",
            "is_mandatory": True,
            "exists": True,
            "sha256": "bbbb1111222233334444555566667777888899990000aaaabbbbccccddddeeee",
            "byte_count": 256,
            "mode": "ro-bind",
        },
        {
            "path": "docs/ai/ref.md",
            "is_mandatory": False,
            "exists": False,
            "sha256": None,
            "byte_count": None,
            "mode": "ro-bind",
        },
    ]

    state_data = {
        "work_item": "test-ctx-item",
        "branch": "feature/test-ctx",
        "status": "DRAFT",
        "plan_granted": False,
        "stages": {"0": {"status": "INITIALIZED", "historical": True}},
        "active_jobs": [],
        "next_roles": ["builder"],
    }

    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            chromium_sandbox=True,
        )
        context = await browser.new_context(permissions=["clipboard-read", "clipboard-write"])
        page = await context.new_page()

        async def route_handler(route):
            url = route.request.url
            if f"/api/tasks/{task_id}/state" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(state_data))
            elif f"/api/tasks/{task_id}/plan" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {"plan_text": "Plan text", "format": "plain_text", "render_mode": "text_content"}
                    ),
                )
            elif f"/api/tasks/{task_id}/review-context" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "gate": None,
                            "proposal": None,
                            "plan_revision_hash": "a" * 64,
                            "scope_hash": "b" * 64,
                            "roles_hash": "c" * 64,
                        }
                    ),
                )
            elif f"/api/tasks/{task_id}/ai-context" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "session_memory_md": session_memory_content,
                            "provenance": provenance_data,
                        }
                    ),
                )
            elif "/api/tasks" in url and route.request.method == "GET":
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        [
                            {
                                "task_id": task_id,
                                "work_item": "test-ctx-item",
                                "task_branch": "feature/test-ctx",
                                "cached_status": "DRAFT",
                                "cached_stage": "plan",
                            }
                        ]
                    ),
                )
            elif "/api/auth/csrf-token" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"csrf_token": "mock_csrf_token"}),
                )
            elif "/api/auth/me" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {"authenticated": True, "username": "engineer", "must_change_password": False}
                    ),
                )
            else:
                await route.continue_()

        await page.route(f"{base_url}/api/**", route_handler)
        await page.goto(base_url)
        await page.wait_for_selector("#tasks-tbody")

        # Inspect task and navigate to AI Context & Memory tab
        await page.click("button:has-text('Inspect')")
        await page.click(".tab-btn[data-tab='tab-context']")
        await page.wait_for_selector("#sprint-memory-display", state="visible")

        # 1. Verify sprint memory plain-text display
        mem_display = await page.text_content("#sprint-memory-display")
        assert session_memory_content.strip() == mem_display.strip()

        # 2. Verify provenance table
        await page.wait_for_selector("#provenance-tbody tr")
        tbody_html = await page.inner_html("#provenance-tbody")
        assert "AGENTS.md" in tbody_html
        assert "SESSION_MEMORY.md" in tbody_html
        assert "docs/ai/ref.md" in tbody_html
        assert "PRESENT" in tbody_html
        assert "MISSING" in tbody_html

        # 3. Test Copy Sprint Memory button
        await page.click("#copy-memory-btn")
        await page.wait_for_selector("#copy-memory-msg", state="visible")
        copy_msg = await page.text_content("#copy-memory-msg")
        assert "copied to clipboard" in copy_msg.lower()

        # Verify clipboard contents
        clipboard_content = await page.evaluate("navigator.clipboard.readText()")
        assert clipboard_content.strip() == session_memory_content.strip()
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await p.stop()
        await asyncio.sleep(0.1)
