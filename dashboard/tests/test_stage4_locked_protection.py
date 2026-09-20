"""Tests verifying locked Stage 4 protection and identity spoofing rejection."""

import json
import sqlite3
import subprocess
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from dashboard.app import app, task_registry
from dashboard.auth import auth_store, session_manager
from dashboard.config import ORCHESTRATOR_PYTHON, REPO_ROOT
from dashboard.tests.conftest import create_isolated_worktree


def create_stage4_worktree(base_dir: Path, name: str = "stage4_wt") -> Path:
    """Create a mock Stage 4 worktree with stored work_item 'erp-arabic-bilingual-data'."""
    wt = base_dir / name
    wt.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["git", "init", "-b", "feature/scope-context-portability", str(wt)], check=True, capture_output=True
    )
    subprocess.run(["git", "-C", str(wt), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.name", "Test User"], check=True)
    (wt / "README.md").write_text("stage 4 worktree")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-m", "init"], check=True)

    var_dir = wt / "orchestrator" / "var"
    var_dir.mkdir(parents=True, exist_ok=True)
    (var_dir / "execution.lock").touch()

    plan_dir = wt / "docs" / "ai"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "plan.md").write_text("# Stage 4 Parked Plan\n\nRead-only content.")

    db_path = var_dir / "checkpoints.db"
    script = """
import sys, sqlite3, json
from langgraph.checkpoint.sqlite import SqliteSaver

db_path = sys.argv[1]
conn = sqlite3.connect(db_path)
with conn:
    conn.execute("CREATE TABLE IF NOT EXISTS workflow_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT OR REPLACE INTO workflow_meta (key, value) VALUES (?, ?)", ("work_item", "erp-arabic-bilingual-data"))
    conn.execute("INSERT OR REPLACE INTO workflow_meta (key, value) VALUES (?, ?)", ("task_branch", "feature/scope-context-portability"))
    conn.execute("INSERT OR REPLACE INTO workflow_meta (key, value) VALUES (?, ?)", ("plan_artifact", json.dumps("docs/ai/plan.md")))
    conn.execute("INSERT OR REPLACE INTO workflow_meta (key, value) VALUES (?, ?)", ("config", json.dumps({"work_item": "erp-arabic-bilingual-data", "branch": "feature/scope-context-portability", "plan_path": "docs/ai/plan.md"})))

saver = SqliteSaver(conn)
saver.setup()
checkpoint = {
    "v": 1,
    "id": "1",
    "ts": "2026-09-17T00:00:00Z",
    "channel_values": {
        "view": {
            "work_item": "erp-arabic-bilingual-data",
            "stage": "plan",
            "status": "PARKED",
            "plan_granted": False,
            "stages": {
                "0": {"status": "INITIALIZED", "historical": True},
                "1": {"status": "PARKED", "historical": False}
            },
            "active_jobs": [],
            "next_roles": []
        }
    },
    "channel_versions": {},
    "versions_seen": {},
    "updated_channels": []
}
saver.put({"configurable": {"thread_id": "workflow", "checkpoint_ns": ""}}, checkpoint, {"source": "synthetic"}, {})
conn.close()
"""
    subprocess.run([str(ORCHESTRATOR_PYTHON), "-c", script, str(db_path)], check=True)
    return wt


def test_stage4_rejected_when_caller_supplies_different_work_item(tmp_path):
    """Caller sets payload.work_item = 'benign-item' against parked Stage 4 root; asserts PreconditionError."""
    wt = create_stage4_worktree(tmp_path, "s4_spoof_wt")
    cmd = [
        str(ORCHESTRATOR_PYTHON),
        "-m",
        "orchestrator.dashboard_api",
        "--root",
        str(wt),
        "--action",
        "approve_plan",
        "--payload",
        json.dumps({"work_item": "benign-item", "submitted_token": {"work_item": "benign-item"}}),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode != 0
    output = json.loads(res.stdout)
    assert output["ok"] is False
    assert output["error_type"] == "PreconditionError"
    assert output["error"] == "Precondition check failed"


def test_work_item_mismatch_rejected(tmp_path):
    """Caller supplies work-item differing from stored configuration; asserts rejected with CoreValidationError."""
    wt = create_isolated_worktree(tmp_path, "normal_wt")
    cmd = [
        str(ORCHESTRATOR_PYTHON),
        "-m",
        "orchestrator.dashboard_api",
        "--root",
        str(wt),
        "--action",
        "approve_plan",
        "--payload",
        json.dumps({"work_item": "different-item", "submitted_token": {"work_item": "different-item"}}),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode != 0
    output = json.loads(res.stdout)
    assert output["ok"] is False
    assert output["error_type"] in ("CoreValidationError", "ValidationError")
    assert output["error"] == "Invalid request or validation failed"


def test_stage4_rejected_across_all_mutations(tmp_path):
    """Verifies initialize, adopt_scope, approve_plan reject Stage 4 on server (403) and subprocess (PreconditionError)."""
    wt = create_stage4_worktree(tmp_path, "s4_mutations_wt")

    # 1. Test subprocess rejection for mutations
    for action in ("initialize", "adopt_scope", "approve_plan", "run", "pause", "resume", "reset_budget"):
        cmd = [
            str(ORCHESTRATOR_PYTHON),
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(wt),
            "--action",
            action,
            "--payload",
            json.dumps({"work_item": "erp-arabic-bilingual-data"}),
        ]
        res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        assert res.returncode != 0
        output = json.loads(res.stdout)
        assert output["ok"] is False
        assert output["error_type"] == "PreconditionError"

    # 2. Test server HTTP API rejection (403 Forbidden)
    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    registered_task = task_registry.register_existing_worktree(wt)
    task_id = registered_task["task_id"]

    data = auth_store._load_data()
    if "users" not in data:
        data["users"] = {}
    data["users"]["engineer"] = {
        "password_hash": "scrypt$16384$8$1$00$00",
        "is_initial": False,
    }
    auth_store._save_data(data)

    client = TestClient(app)
    session_token = session_manager.create_session("engineer")
    csrf_token = "valid_csrf_token"
    client.cookies.set("dashboard_session", session_token)
    client.cookies.set("dashboard_csrf", csrf_token)

    headers = {
        "Host": "127.0.0.1:8080",
        "Origin": "https://127.0.0.1:8080",
        "X-CSRF-Token": csrf_token,
    }

    # POST /api/tasks/{task_id}/adopt-scope
    resp = client.post(
        f"/api/tasks/{task_id}/adopt-scope",
        headers=headers,
        json={"scope": {"allowed_paths": []}, "implementation_stages": ["1"]},
    )
    assert resp.status_code == 403
    assert "Stage 4" in (resp.json().get("detail") or resp.json().get("error"))

    # POST /api/tasks/{task_id}/create-review
    resp = client.post(
        f"/api/tasks/{task_id}/create-review",
        headers=headers,
        json={},
    )
    assert resp.status_code == 403
    assert "Stage 4" in (resp.json().get("detail") or resp.json().get("error"))

    # POST /api/tasks/{task_id}/approve-plan
    resp = client.post(
        f"/api/tasks/{task_id}/approve-plan",
        headers=headers,
        json={"review_id": "rev-1"},
    )
    assert resp.status_code == 403
    assert "Stage 4" in (resp.json().get("detail") or resp.json().get("error"))

    # POST /api/tasks/bootstrap with work_item="erp-arabic-bilingual-data"
    resp = client.post(
        "/api/tasks/bootstrap",
        headers=headers,
        json={"work_item": "erp-arabic-bilingual-data", "user_brief": "test brief"},
    )
    assert resp.status_code == 403
    assert "Stage 4" in (resp.json().get("detail") or resp.json().get("error"))


def test_stage4_read_only_monitoring_preserved(tmp_path):
    """Verifies state and plan remain readable for Stage 4 worktree."""
    wt = create_stage4_worktree(tmp_path, "s4_ro_wt")

    # Subprocess state
    cmd = [
        str(ORCHESTRATOR_PYTHON),
        "-m",
        "orchestrator.dashboard_api",
        "--root",
        str(wt),
        "--action",
        "state",
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    output = json.loads(res.stdout)
    assert output["ok"] is True
    assert output["result"]["work_item"] == "erp-arabic-bilingual-data"
    assert output["result"]["status"] == "PARKED"

    # Subprocess plan
    cmd = [
        str(ORCHESTRATOR_PYTHON),
        "-m",
        "orchestrator.dashboard_api",
        "--root",
        str(wt),
        "--action",
        "plan",
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    output = json.loads(res.stdout)
    assert output["ok"] is True
    assert output["result"]["format"] == "plain_text"
    assert "Stage 4 Parked Plan" in output["result"]["plan_text"]


def test_stage4_blocked_by_directory_name_without_checkpoint(tmp_path):
    """Verifies that an uninitialized worktree whose directory name is 'erp-arabic-bilingual-data' is blocked from all mutations."""
    s4_dir = tmp_path / "erp-arabic-bilingual-data"
    s4_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main", str(s4_dir)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(s4_dir), "config", "user.email", "t@e.com"], check=True)
    subprocess.run(["git", "-C", str(s4_dir), "config", "user.name", "Test"], check=True)
    (s4_dir / "README.md").write_text("s4 raw")
    subprocess.run(["git", "-C", str(s4_dir), "add", "."], check=True)
    subprocess.run(["git", "-C", str(s4_dir), "commit", "-m", "init"], check=True)

    # Mutating actions without payload work_item must be blocked purely by directory name
    for action in ("initialize", "run", "adopt_scope", "approve_plan"):
        cmd = [
            str(ORCHESTRATOR_PYTHON),
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(s4_dir),
            "--action",
            action,
            "--payload",
            "{}",
        ]
        res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        assert res.returncode != 0
        output = json.loads(res.stdout)
        assert output["ok"] is False
        assert output["error_type"] == "PreconditionError"
        assert output["error"] == "Precondition check failed"
