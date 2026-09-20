"""Background Polling Coordinator for registered tasks.

Maintains lock-free polling of registered worktrees:
- Periodically queries state projections via SubprocessClient.
- Updates cached status and stage in registry.db.
- Holds zero locks; never accesses or creates execution.lock.
"""

import asyncio
import logging
from typing import Any

from dashboard.registry import TaskRegistry
from dashboard.subprocess_client import get_state_projection, SubprocessClientError

logger = logging.getLogger(__name__)


class TaskCoordinator:
    """Coordinates background polling of registered tasks."""

    def __init__(
        self,
        registry: TaskRegistry | None = None,
        poll_interval_seconds: float = 3.0,
    ):
        self.registry = registry or TaskRegistry()
        self.poll_interval_seconds = poll_interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None

    async def poll_once(self) -> None:
        """Execute one polling cycle over all registered tasks."""
        tasks = self.registry.list_tasks()
        for t in tasks:
            task_id = t["task_id"]
            worktree_path = t["worktree_path"]
            try:
                state = await get_state_projection(worktree_path)
                status = state.get("status", t.get("cached_status", "UNKNOWN"))
                current_stage = state.get("current_stage", t.get("cached_stage", "plan"))
                self.registry.update_task_cache(task_id, status, current_stage)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "Error polling state for task %s (%s): %s",
                    task_id,
                    worktree_path,
                    exc,
                )

    async def _run_loop(self) -> None:
        """Background polling loop."""
        while self._running:
            try:
                await self.poll_once()
            except Exception as exc:
                logger.error("Unexpected error in coordinator poll loop: %s", exc)
            try:
                await asyncio.sleep(self.poll_interval_seconds)
            except asyncio.CancelledError:
                break

    def start(self) -> None:
        """Start background polling task."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop background polling task gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            await asyncio.sleep(0.05)
