"""Tests for TaskCoordinator background polling and zero-lock execution."""

import asyncio
from pathlib import Path
import pytest

from dashboard.config import REPO_ROOT
from dashboard.coordinator import TaskCoordinator
from dashboard.registry import TaskRegistry


@pytest.mark.anyio
async def test_coordinator_poll_once(tmp_path, isolated_worktree):
    """Test that coordinator polls registered tasks and updates cache without locks, using an isolated worktree fixture."""
    reg_db = tmp_path / "registry.db"
    # Allow temporary root containing the isolated worktree
    registry = TaskRegistry(db_path=reg_db, allowed_roots=[tmp_path])

    # Register isolated mock worktree fixture (never the live repository)
    task = registry.register_existing_worktree(isolated_worktree)
    task_id = task["task_id"]

    coordinator = TaskCoordinator(registry=registry, poll_interval_seconds=0.1)

    # Isolated fixture lock file
    isolated_lock = isolated_worktree / "orchestrator" / "var" / "execution.lock"

    await coordinator.poll_once()

    # Verify task cache is updated
    updated = registry.get_task(task_id)
    assert updated is not None
    assert updated["last_polled_utc"] is not None
    assert updated["cached_status"] is not None
    assert updated["cached_stage"] is not None

    # Verify coordinator holds zero locks on the isolated fixture:
    # file is immediately and non-blockingly lockable
    import fcntl
    with open(isolated_lock, "a+b") as h:
        fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(h, fcntl.LOCK_UN)


@pytest.mark.anyio
async def test_coordinator_start_stop(tmp_path):
    """Test starting and stopping coordinator gracefully."""
    reg_db = tmp_path / "registry.db"
    registry = TaskRegistry(db_path=reg_db)
    coordinator = TaskCoordinator(registry=registry, poll_interval_seconds=0.05)

    coordinator.start()
    assert coordinator._running is True
    assert coordinator._task is not None

    await asyncio.sleep(0.1)

    await coordinator.stop()
    assert coordinator._running is False
    assert coordinator._task is None
