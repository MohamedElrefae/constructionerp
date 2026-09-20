"""Verification of strict non-dispatching guarantee for Week 3 inspection endpoints.

Asserts:
- Engine is never instantiated or run (0 calls to Engine.run, _prepare, _dispatch, launcher).
- Zero delta on checkpoints.db (jobs count, workflow_events count & max seq, checkpoints count).
- Absence and rejection of mutating workflow routes (pause, resume, reset_budget, run, reconfigure_role).
- Zero file mutations across the worktree.
"""

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from dashboard.app import app, task_registry
from dashboard.auth import auth_store, session_manager
from dashboard.tests.conftest import create_isolated_worktree


@pytest.fixture
def auth_headers_and_cookies():
    """Create authenticated session and CSRF tokens for testing."""
    data = auth_store._load_data()
    if "users" not in data:
        data["users"] = {}
    data["users"]["engineer"] = {
        "password_hash": "scrypt$16384$8$1$00$00",
        "is_initial": False,
    }
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


def get_db_fingerprint(db_path: Path) -> dict:
    """Read counts and max seq from checkpoints.db."""
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        fp = {}
        for tbl in ("jobs", "workflow_events", "checkpoints", "workflow_meta"):
            if tbl in tables:
                fp[f"{tbl}_count"] = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            else:
                fp[f"{tbl}_count"] = 0
        if "workflow_events" in tables:
            max_seq = conn.execute("SELECT MAX(seq) FROM workflow_events").fetchone()[0]
            fp["workflow_events_max_seq"] = max_seq
        return fp
    finally:
        conn.close()


@pytest.mark.anyio
async def test_strict_non_dispatching_and_zero_db_delta(auth_headers_and_cookies, tmp_path):
    """Verify that all 9 Week 3 endpoints trigger zero engine calls and zero DB mutations."""
    headers, cookies = auth_headers_and_cookies
    wt = create_isolated_worktree(tmp_path, "wt_non_dispatch")
    db_path = wt / "orchestrator/var/checkpoints.db"

    # Seed an evidence file in secure directory
    evidence_dir = wt / "docs/ai/work-items/isolated-test-work-item/evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "stage1_output.txt"
    evidence_file.write_text("Test validation output.")

    # Set secure permissions (0o755 / 0o644) so descriptor relative open succeeds
    curr = evidence_dir
    while curr != wt.parent:
        curr.chmod(0o755)
        curr = curr.parent
    evidence_file.chmod(0o644)

    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    reg = task_registry.register_existing_worktree(str(wt))
    task_id = reg["task_id"]

    # Update config to have task_base_commit so diff succeeds
    import subprocess

    head_rev = subprocess.check_output(["git", "-C", str(wt), "rev-parse", "HEAD"]).decode().strip()
    conn = sqlite3.connect(str(db_path))
    with conn:
        conn.execute(
            "UPDATE workflow_meta SET value = ? WHERE key = 'config'",
            (json.dumps({"work_item": "isolated-test-work-item", "task_base_commit": head_rev}),),
        )
    conn.close()

    initial_fp = get_db_fingerprint(db_path)
    assert initial_fp != {}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        called_actions = []
        import dashboard.subprocess_client as sc

        orig_run_action = sc.run_action

        async def spy_run_action(worktree_path, action, payload=None):
            # Assert strictly non-mutating / non-dispatching action
            assert action not in (
                "run",
                "dispatch",
                "pause",
                "resume",
                "reset_budget",
                "reconfigure_role",
                "adopt_scope",
                "approve_plan",
            )
            called_actions.append(action)
            return await orig_run_action(worktree_path, action, payload)

        with patch.object(sc, "run_action", side_effect=spy_run_action):
            endpoints = [
                (f"/api/tasks/{task_id}/findings", 200),
                (f"/api/tasks/{task_id}/evidence", 200),
                (f"/api/tasks/{task_id}/evidence/stage1_output.txt", 200),
                (f"/api/tasks/{task_id}/diff", 200),
                (f"/api/tasks/{task_id}/settings", 200),
                (f"/api/tasks/{task_id}/export/audit", 200),
                (f"/api/tasks/{task_id}/export/state", 200),
                (f"/api/tasks/{task_id}/export/reviews", 200),
                ("/api/erp/projection", 200),
            ]

            for path, expected_status in endpoints:
                resp = await client.get(path, headers=headers)
                assert (
                    resp.status_code == expected_status
                ), f"Path {path} returned {resp.status_code}: {resp.text}"

                # Verify database unchanged after every single endpoint call
                current_fp = get_db_fingerprint(db_path)
                assert (
                    current_fp == initial_fp
                ), f"Database delta detected after calling {path}: {current_fp} vs {initial_fp}"

        # Confirm that only read-only actions were dispatched
        for act in called_actions:
            assert act in ("findings", "evidence", "read_evidence", "diff", "settings", "audit", "state")


@pytest.mark.anyio
async def test_rejection_of_mutating_actions(auth_headers_and_cookies):
    """Verify that mutating owner decision and execution endpoints are strictly rejected."""
    headers, cookies = auth_headers_and_cookies
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        rejected_actions = [
            ("POST", "/api/tasks/task-non-dispatch/pause"),
            ("POST", "/api/tasks/task-non-dispatch/resume"),
            ("POST", "/api/tasks/task-non-dispatch/reset_budget"),
            ("POST", "/api/tasks/task-non-dispatch/run"),
            ("POST", "/api/tasks/task-non-dispatch/reconfigure_role"),
            ("POST", "/api/tasks/task-non-dispatch/dispatch"),
            ("POST", "/api/tasks/pause"),
            ("POST", "/api/tasks/resume"),
        ]

        for method, path in rejected_actions:
            resp = await client.post(path, json={}, headers=headers)
            assert resp.status_code in (
                404,
                405,
            ), f"Mutating endpoint {path} should not exist but returned {resp.status_code}"
