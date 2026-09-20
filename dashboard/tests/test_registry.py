"""Tests for Task Registry: path validation, security, and read-only database integrity."""

import os
from pathlib import Path
import sqlite3
import subprocess
import pytest

from dashboard.registry import (
    TaskRegistry,
    get_actual_git_branch,
    inspect_readonly_checkpoint_db,
    validate_and_resolve_checkpoint_db,
)


def _setup_mock_worktree(root: Path, name: str, branch: str = "main", work_item: str = "test-item") -> Path:
    wt = root / name
    wt.mkdir(parents=True, exist_ok=True)
    # Init git repo
    subprocess.run(["git", "init", "-b", branch, str(wt)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.name", "Test User"], check=True)
    (wt / "README.md").write_text("test")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-m", "init"], check=True)

    # Checkpoints DB
    var_dir = wt / "orchestrator" / "var"
    var_dir.mkdir(parents=True, exist_ok=True)
    db_path = var_dir / "checkpoints.db"
    conn = sqlite3.connect(str(db_path))
    with conn:
        conn.execute("CREATE TABLE workflow_meta (key TEXT PRIMARY KEY, value TEXT);")
        conn.execute("INSERT INTO workflow_meta VALUES ('work_item', ?);", (work_item,))
        conn.execute("INSERT INTO workflow_meta VALUES ('task_branch', ?);", (branch,))
    conn.close()
    return wt


def test_parent_traversal_rejected(tmp_path):
    base = tmp_path / "worktrees"
    base.mkdir()
    wt = _setup_mock_worktree(base, "wt1")

    # Paths containing .. must be rejected BEFORE normalization
    traversal_paths = [
        str(wt) + "/../wt1",
        "wt1/../wt1",
        "../outside",
        "foo/../../outside",
        str(base) + "/sub/../wt1",
    ]
    for p in traversal_paths:
        with pytest.raises(ValueError, match=r"Parent directory traversal"):
            validate_and_resolve_checkpoint_db(base, p)


def test_in_root_symlink_alias_rejected(tmp_path):
    base = tmp_path / "worktrees"
    base.mkdir()
    wt = _setup_mock_worktree(base, "wt_real")

    # In-root symlink alias: symlink inside base pointing to real worktree inside base
    alias = base / "wt_alias"
    alias.symlink_to(wt)

    with pytest.raises(ValueError, match=r"Symlink rejected in worktree path component"):
        validate_and_resolve_checkpoint_db(base, alias)


def test_intermediate_symlink_components_rejected(tmp_path):
    base = tmp_path / "worktrees"
    base.mkdir()
    wt = _setup_mock_worktree(base, "wt_inter")

    # Symlink at orchestrator component level
    wt_fake = base / "wt_fake"
    wt_fake.mkdir()
    subprocess.run(["git", "init", str(wt_fake)], check=True, capture_output=True)
    (wt_fake / "orchestrator").symlink_to(wt / "orchestrator")

    with pytest.raises(ValueError, match=r"Symlink rejected in checkpoints path component"):
        validate_and_resolve_checkpoint_db(base, wt_fake)


def test_out_of_root_symlink_rejected(tmp_path):
    base = tmp_path / "worktrees"
    base.mkdir()
    outside = tmp_path / "outside_wt"
    _setup_mock_worktree(tmp_path, "outside_wt")

    # Symlink inside base pointing outside
    alias = base / "wt_outside"
    alias.symlink_to(outside)

    with pytest.raises(ValueError, match=r"Symlink rejected in worktree path component"):
        validate_and_resolve_checkpoint_db(base, alias)


def test_git_branch_mismatch_rejected(tmp_path):
    base = tmp_path / "worktrees"
    base.mkdir()
    wt = _setup_mock_worktree(base, "wt_branch", branch="main")

    # Switch git branch to 'feature' so checked out diverges from metadata 'main'
    subprocess.run(["git", "-C", str(wt), "checkout", "-b", "feature"], check=True, capture_output=True)

    reg_db = tmp_path / "registry.db"
    registry = TaskRegistry(db_path=reg_db, allowed_roots=[base])

    with pytest.raises(ValueError, match=r"Git branch mismatch"):
        registry.register_existing_worktree(wt)


def test_readonly_integrity_check(tmp_path):
    base = tmp_path / "worktrees"
    base.mkdir()
    wt = _setup_mock_worktree(base, "wt_valid")

    db_path = wt / "orchestrator" / "var" / "checkpoints.db"
    meta = inspect_readonly_checkpoint_db(db_path)
    assert meta["work_item"] == "test-item"
    assert meta["task_branch"] == "main"

    # Corrupt DB and test integrity failure
    corrupt_db = tmp_path / "corrupt.db"
    corrupt_db.write_bytes(b"garbage sqlite data here")
    with pytest.raises(Exception):
        inspect_readonly_checkpoint_db(corrupt_db)


def test_registry_crud(tmp_path):
    base = tmp_path / "worktrees"
    base.mkdir()
    wt = _setup_mock_worktree(base, "wt_crud", branch="main", work_item="item-1")

    reg_db = tmp_path / "registry.db"
    registry = TaskRegistry(db_path=reg_db, allowed_roots=[base])

    # Register
    res = registry.register_existing_worktree(wt)
    assert res["task_id"] == "wt_crud"
    assert res["work_item"] == "item-1"
    assert res["task_branch"] == "main"

    # List
    tasks = registry.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == "wt_crud"
    assert tasks[0]["cached_status"] == "INITIALIZED"

    # Get
    task = registry.get_task("wt_crud")
    assert task is not None
    assert task["task_id"] == "wt_crud"

    # Update cache
    registry.update_task_cache("wt_crud", "RUNNING", "build")
    task = registry.get_task("wt_crud")
    assert task["cached_status"] == "RUNNING"
    assert task["cached_stage"] == "build"
    assert task["last_polled_utc"] is not None

    # Unregister
    assert registry.unregister_task("wt_crud") is True
    assert registry.get_task("wt_crud") is None
    assert len(registry.list_tasks()) == 0
