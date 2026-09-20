"""Pytest fixtures and configuration for dashboard tests."""

import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tempfile

# Set test environment defaults with isolated runtime storage. These must use
# the configuration module's supported test-mode contract before dashboard.app
# is imported by test modules.
TEST_ROOT = Path(tempfile.mkdtemp(prefix="dashboard_test_root_"))
os.chmod(TEST_ROOT, 0o700)
TEST_VAR_DIR = TEST_ROOT / "dashboard" / "var"
TEST_VAR_DIR.mkdir(parents=True)
os.chmod(TEST_ROOT / "dashboard", 0o700)
os.chmod(TEST_VAR_DIR, 0o700)
os.environ["DASHBOARD_TEST_MODE"] = "1"
os.environ["DASHBOARD_TEST_ROOT"] = str(TEST_ROOT)
os.environ["DASHBOARD_HOST"] = "127.0.0.1"
os.environ["DASHBOARD_PORT"] = "8080"
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

import json
import shutil
import sqlite3
import subprocess

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


def create_isolated_worktree(base_dir: Path, name: str = "isolated_wt") -> Path:
    """Create a completely isolated mock worktree with its own Git repo and synthetic checkpoints DB.

    Prevents tests from touching, copying, or locking the live repository.
    """
    wt = base_dir / name
    if wt.exists():
        shutil.rmtree(wt)
    wt.mkdir(parents=True)

    subprocess.run(
        ["git", "init", "-b", "feature/scope-context-portability", str(wt)],
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "-C", str(wt), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.name", "Test User"], check=True)
    (wt / "README.md").write_text("isolated worktree")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-m", "init"], check=True)

    var_dir = wt / "orchestrator" / "var"
    var_dir.mkdir(parents=True)
    (var_dir / "execution.lock").touch()

    plan_dir = wt / "docs" / "ai"
    plan_dir.mkdir(parents=True)
    (plan_dir / "plan.md").write_text("# Isolated Test Plan\n\nSafe plain text content.")

    # Synthetically create checkpoints.db from scratch without touching or copying the live database
    db_path = var_dir / "checkpoints.db"
    script = """
import sys, sqlite3, json
from langgraph.checkpoint.sqlite import SqliteSaver

db_path = sys.argv[1]
conn = sqlite3.connect(db_path)
with conn:
    conn.execute("CREATE TABLE IF NOT EXISTS workflow_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT OR REPLACE INTO workflow_meta (key, value) VALUES (?, ?)", ("work_item", "isolated-test-work-item"))
    conn.execute("INSERT OR REPLACE INTO workflow_meta (key, value) VALUES (?, ?)", ("task_branch", "feature/scope-context-portability"))
    conn.execute("INSERT OR REPLACE INTO workflow_meta (key, value) VALUES (?, ?)", ("plan_artifact", json.dumps("docs/ai/plan.md")))
    conn.execute("INSERT OR REPLACE INTO workflow_meta (key, value) VALUES (?, ?)", ("config", json.dumps({"work_item": "isolated-test-work-item", "branch": "feature/scope-context-portability", "plan_path": "docs/ai/plan.md"})))

saver = SqliteSaver(conn)
saver.setup()
checkpoint = {
    "v": 1,
    "id": "1",
    "ts": "2026-09-17T00:00:00Z",
    "channel_values": {
        "view": {
            "work_item": "isolated-test-work-item",
            "stage": "plan",
            "status": "PLAN_PROPOSED",
            "plan_granted": False,
            "stages": {
                "0": {"status": "INITIALIZED", "historical": True},
                "1": {"status": "PLAN_PROPOSED", "historical": False}
            },
            "active_jobs": [],
            "next_roles": ["reviewer"]
        }
    },
    "channel_versions": {},
    "versions_seen": {},
    "updated_channels": []
}
saver.put({"configurable": {"thread_id": "workflow", "checkpoint_ns": ""}}, checkpoint, {"source": "synthetic"}, {})
conn.close()
"""
    from dashboard.config import ORCHESTRATOR_PYTHON

    subprocess.run([str(ORCHESTRATOR_PYTHON), "-c", script, str(db_path)], check=True)
    return wt


@pytest.fixture
def isolated_worktree(tmp_path) -> Path:
    """Fixture providing an isolated worktree in tmp_path."""
    from dashboard.app import task_registry

    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    return create_isolated_worktree(tmp_path)
