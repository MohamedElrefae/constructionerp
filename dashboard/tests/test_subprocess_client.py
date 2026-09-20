"""Tests for the Subprocess Client invoking orchestrator.dashboard_api."""

import asyncio
from pathlib import Path
import pytest

from dashboard.config import REPO_ROOT
from dashboard.subprocess_client import (
    ALLOWED_ACTIONS,
    SubprocessClientError,
    get_plan_projection,
    get_state_projection,
    run_action,
)
from dashboard.tests.test_registry import _setup_mock_worktree


@pytest.mark.anyio
async def test_action_allowlist_enforced(tmp_path):
    """Verify that only allowlisted actions are permitted."""
    disallowed_actions = ["pause", "resume", "reset_budget", "run", "reconfigure_role", "eval", "unknown"]
    for action in disallowed_actions:
        with pytest.raises(ValueError, match=r"not permitted"):
            await run_action(tmp_path, action)
    assert "initialize" in ALLOWED_ACTIONS
    assert "adopt_scope" in ALLOWED_ACTIONS
    assert "approve_plan" in ALLOWED_ACTIONS
    assert "review_context" in ALLOWED_ACTIONS
    assert "ai_context" in ALLOWED_ACTIONS


@pytest.mark.anyio
async def test_subprocess_timeout(tmp_path):
    """Verify that long-running subprocess calls raise SubprocessClientError on timeout."""
    wt = _setup_mock_worktree(tmp_path, "wt_timeout")
    with pytest.raises(SubprocessClientError, match=r"timed out"):
        # Use an impossibly short timeout
        await run_action(wt, "state", timeout=0.0001)


@pytest.mark.anyio
async def test_subprocess_state_and_plan_projections(isolated_worktree):
    """Verify state and plan projections executed via subprocess return valid results on isolated fixture."""
    # Get state projection from isolated fixture
    state = await get_state_projection(isolated_worktree)
    assert isinstance(state, dict)
    assert "work_item" in state
    assert "status" in state
    assert "stages" in state

    # Get plan projection from isolated fixture
    plan = await get_plan_projection(isolated_worktree)
    assert isinstance(plan, dict)
    assert plan.get("format") == "plain_text"
    assert plan.get("render_mode") == "text_content"
    assert "plan_text" in plan
    assert "Isolated Test Plan" in plan["plan_text"]
