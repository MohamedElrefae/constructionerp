"""Playwright UI integration tests for Week 3 Civil Engineer Dashboard.

Covers:
- 8-tab switching and active styling.
- Results & Evidence tab: table listing, "View" file inspection panel with plain text rendering and SHA-256 badge.
- Findings & Backlog tab: summary stats badges and interactive filtering (all, blocking, backlog, defects).
- Hardened Diff Viewer tab: base/head badges, changed files count & tags, unified diff view with line highlighting.
- Settings & Roles tab: role configuration table, escalation counters, execution timeouts.
- Stage 4 ERP Status tab: PARKED badge, integrity badge, manifest metadata, masked paths, invariant notice.
- Export Dropdown: menu toggling and export options.
"""

import asyncio
import json
import os
import threading
import time
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
async def test_ui_week3_eight_tab_navigation_and_features(ui_live_server):
    """Verifies all 8 tabs, inspection panels, findings filters, diff viewer, settings, and ERP status."""
    base_url = f"http://localhost:{ui_live_server}"
    task_id = "task-ui-week3"

    state_data = {
        "work_item": "test-week3-item",
        "branch": "feature/test-week3",
        "status": "IN_PROGRESS",
        "plan_granted": True,
        "stages": {"0": {"status": "INITIALIZED", "historical": True}, "1": {"status": "IN_PROGRESS"}},
        "active_jobs": [{"role": "engineer", "status": "active"}],
        "next_roles": ["reviewer"],
    }

    plan_data = {
        "plan_text": "# Week 3 Plan\nApproved plain-text plan content.",
        "format": "plain_text",
        "render_mode": "text_content",
    }

    ai_data = {
        "session_memory_md": "Sprint memory notes for Week 3",
        "provenance": [],
    }

    evidence_data = {
        "work_item": "test-week3-item",
        "files": [
            {
                "filename": "stage1_output.txt",
                "size_bytes": 1024,
                "modified_utc": "2026-09-17T12:00:00Z",
            }
        ],
    }

    evidence_file_data = {
        "filename": "stage1_output.txt",
        "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "size_bytes": 1024,
        "content": "Stage 1 verification PASSED with 0 errors.",
        "truncated": False,
    }

    findings_data = {
        "work_item": "test-week3-item",
        "findings": [
            {
                "id": "FINDING-001",
                "classification": "implementation_defect",
                "severity": "BLOCKING",
                "description": "Missing CSRF token verification in route",
                "stage": "1",
                "role": "engineer",
            },
            {
                "id": "FINDING-002",
                "classification": "documentation",
                "severity": "LOW",
                "description": "Minor typo in code comment",
                "stage": "1",
                "role": "reviewer",
            },
        ],
        "backlog": [
            {
                "id": "BACKLOG-001",
                "title": "Deferred Performance Optimization",
                "description": "Profile SQLite indexing under high concurrency",
            }
        ],
        "stats": {
            "total_findings": 2,
            "blocking_findings": 1,
            "backlog_items": 1,
        },
    }

    diff_data = {
        "base_commit": "1234567890abcdef",
        "head_commit": "abcdef1234567890",
        "files": [{"status": "M", "path": "dashboard/app.py"}],
        "diff_text": "diff --git a/dashboard/app.py b/dashboard/app.py\n--- a/dashboard/app.py\n+++ b/dashboard/app.py\n@@ -1,3 +1,4 @@\n+added line\n-removed line\n",
        "truncated": False,
    }

    settings_data = {
        "work_item": "test-week3-item",
        "roles": {
            "architect": {
                "tool": "cortex",
                "model": "claude-3-5-sonnet",
                "effort": "high",
                "version": "1.0",
                "prompt_sha256": "11112222333344445555666677778888",
            }
        },
        "escalation_status": {
            "consecutive_blockers": 0,
            "cycles_in_stage": 1,
            "stage_attempts": 1,
            "pause_reason": None,
        },
        "timeouts": {
            "soft_timeout": 2700,
            "hard_timeout": 3600,
        },
    }

    erp_data = {
        "status": "PARKED",
        "integrity_status": "unverified_permissions",
        "manifest_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "permissions": "0o664",
        "company": "Elrefae",
        "domain": "account-master",
        "export_file": "account_catalog_20260910_121018.json",
        "rows": 81,
        "groups": 26,
        "leaves": 55,
        "recorded_utc": "2026-09-10T12:10:18Z",
        "masked_export_path": "[PATH]",
        "warnings": ["Directory has unsafe permissions 0o775"],
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
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(plan_data))
            elif f"/api/tasks/{task_id}/review-context" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"gate": None, "proposal": None, "plan_revision_hash": "a"*64, "scope_hash": "b"*64, "roles_hash": "c"*64}))
            elif f"/api/tasks/{task_id}/ai-context" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(ai_data))
            elif f"/api/tasks/{task_id}/evidence/stage1_output.txt" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(evidence_file_data))
            elif f"/api/tasks/{task_id}/evidence" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(evidence_data))
            elif f"/api/tasks/{task_id}/findings" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(findings_data))
            elif f"/api/tasks/{task_id}/diff" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(diff_data))
            elif f"/api/tasks/{task_id}/settings" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(settings_data))
            elif "/api/erp/projection" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(erp_data))
            elif "/api/tasks" in url and route.request.method == "GET":
                await route.fulfill(status=200, content_type="application/json", body=json.dumps([{"task_id": task_id, "work_item": "test-week3-item", "task_branch": "feature/test-week3", "cached_status": "IN_PROGRESS", "cached_stage": "1"}]))
            elif "/api/auth/csrf-token" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"csrf_token": "mock_csrf_token"}))
            elif "/api/auth/me" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"authenticated": True, "username": "engineer", "must_change_password": False}))
            else:
                await route.continue_()

        await page.route(f"{base_url}/api/**", route_handler)
        await page.goto(base_url)
        await page.wait_for_selector("#tasks-tbody")

        # Open task inspection
        await page.click("button:has-text('Inspect')")
        await page.wait_for_selector("#task-detail-section", state="visible")

        # Verify export dropdown toggle
        await page.click("#export-menu-btn")
        assert await page.is_visible("#export-menu")
        assert await page.is_visible("#export-audit-link")
        assert await page.is_visible("#export-state-link")
        assert await page.is_visible("#export-reviews-link")
        # Click outside to close
        await page.click("#detail-task-id")
        await page.wait_for_timeout(100)
        assert not await page.is_visible("#export-menu")

        # 1. Tab: Progress & Jobs
        assert await page.is_visible("#tab-progress")

        # 2. Tab: Plan & Approval
        await page.click(".tab-btn[data-tab='tab-plan']")
        await page.wait_for_timeout(150)
        assert await page.is_visible("#tab-plan")
        plan_text = await page.text_content("#plan-display")
        assert "Approved plain-text plan content" in plan_text

        # 3. Tab: AI Context & Memory
        await page.click(".tab-btn[data-tab='tab-context']")
        await page.wait_for_timeout(150)
        assert await page.is_visible("#tab-context")

        # 4. Tab: Results & Evidence
        await page.click(".tab-btn[data-tab='tab-evidence']")
        await page.wait_for_timeout(200)
        assert await page.is_visible("#tab-evidence")
        await page.wait_for_selector("#evidence-tbody tr")
        assert "stage1_output.txt" in await page.text_content("#evidence-tbody")

        # Click View button to open evidence viewer panel
        await page.click("#evidence-tbody button:has-text('View')")
        await page.wait_for_selector("#evidence-viewer-panel", state="visible")
        ev_content = await page.text_content("#evidence-display")
        assert "Stage 1 verification PASSED" in ev_content
        sha_badge = await page.text_content("#evidence-sha-badge")
        assert "SHA-256:" in sha_badge

        # 5. Tab: Findings & Backlog
        await page.click(".tab-btn[data-tab='tab-findings']")
        await page.wait_for_timeout(200)
        assert await page.is_visible("#tab-findings")
        assert "1 Blocking Defects" in await page.text_content("#blocking-count-badge")
        assert "2 Total Findings" in await page.text_content("#total-findings-badge")
        assert "1 Backlog Items" in await page.text_content("#backlog-count-badge")

        # Verify initial 'All' filter renders both findings and backlog
        findings_html = await page.inner_html("#findings-list")
        assert "FINDING-001" in findings_html
        assert "BACKLOG-001" in findings_html

        # Click 'Blocking Only' filter
        await page.click(".filter-btn[data-filter='blocking']")
        await page.wait_for_timeout(150)
        blocking_html = await page.inner_html("#findings-list")
        assert "FINDING-001" in blocking_html
        assert "BACKLOG-001" not in blocking_html

        # Click 'Backlog Only' filter
        await page.click(".filter-btn[data-filter='backlog']")
        await page.wait_for_timeout(150)
        backlog_html = await page.inner_html("#findings-list")
        assert "FINDING-001" not in backlog_html
        assert "BACKLOG-001" in backlog_html

        # 6. Tab: Diff Viewer
        await page.click(".tab-btn[data-tab='tab-diff']")
        await page.wait_for_timeout(200)
        assert await page.is_visible("#tab-diff")
        base_badge = await page.text_content("#diff-base-badge")
        assert "Base: 12345678" in base_badge
        assert "1" == (await page.text_content("#diff-files-count")).strip()
        assert "M dashboard/app.py" in await page.text_content("#diff-files-list")
        diff_view_text = await page.text_content("#diff-display")
        assert "added line" in diff_view_text
        assert "removed line" in diff_view_text
        # Verify colored line elements present
        assert await page.is_visible(".diff-line-add")
        assert await page.is_visible(".diff-line-del")

        # 7. Tab: Settings & Roles
        await page.click(".tab-btn[data-tab='tab-settings']")
        await page.wait_for_timeout(200)
        assert await page.is_visible("#tab-settings")
        roles_text = await page.text_content("#settings-roles-tbody")
        assert "architect" in roles_text
        assert "claude-3-5-sonnet" in roles_text
        assert "1" == (await page.text_content("#settings-cycles-in-stage")).strip()
        assert "2700" == (await page.text_content("#settings-soft-timeout")).strip()

        # 8. Tab: ERP Status
        await page.click(".tab-btn[data-tab='tab-erp']")
        await page.wait_for_timeout(200)
        assert await page.is_visible("#tab-erp")
        assert "PARKED" in await page.text_content("#erp-status-badge")
        assert "UNVERIFIED_PERMISSIONS" in await page.text_content("#erp-integrity-badge")
        assert "Elrefae" in await page.text_content("#erp-company")
        assert "account-master" in await page.text_content("#erp-domain")
        assert "81" in await page.text_content("#erp-rows")
        assert "Stage 4 Invariant:" in await page.text_content("#tab-erp")
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await p.stop()
        await asyncio.sleep(0.1)
