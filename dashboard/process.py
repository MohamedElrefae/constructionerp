"""Process supervision and PID-reuse protected helpers.

Extracts process start-time ticks from /proc/<pid>/stat field 22,
verifies liveness against kernel PID recycling, and provides supervised
child execution wrapped in dashboard.launcher with PR_SET_PDEATHSIG.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def get_process_start_time(pid: int) -> int | None:
    """Extract starttime (field 22) in clock ticks from /proc/<pid>/stat."""
    if not pid or pid <= 0:
        return None
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            content = f.read()
            rparen = content.rfind(")")
            if rparen == -1:
                return None
            fields = content[rparen + 2 :].split()
            # field 22 is index 19 after the command closing parenthesis
            return int(fields[19])
    except (FileNotFoundError, ProcessLookupError, IndexError, ValueError, OSError, PermissionError):
        return None


def is_process_alive_with_start_time(pid: int | None, expected_start_time: int | None) -> bool:
    """Check if process is alive and its start time matches expected.

    Guarantees that a recycled PID belonging to a new, unrelated process
    is never mistaken for the original process.
    """
    if pid is None or expected_start_time is None or pid <= 0:
        return False
    actual_start_time = get_process_start_time(pid)
    if actual_start_time is None:
        return False
    return actual_start_time == expected_start_time


def build_supervised_cmd(
    cmd: list[str],
    parent_pid: int | None = None,
    parent_start_time: int | None = None,
    lock_fd: int | None = None,
) -> list[str]:
    """Construct command wrapped by dashboard.launcher."""
    if parent_pid is None:
        parent_pid = os.getpid()
    if parent_start_time is None:
        parent_start_time = get_process_start_time(parent_pid) or 0

    launcher_cmd = [
        sys.executable,
        "-m",
        "dashboard.launcher",
        "--parent-pid",
        str(parent_pid),
        "--parent-start-time",
        str(parent_start_time),
    ]
    if lock_fd is not None:
        launcher_cmd.extend(["--lock-fd", str(lock_fd)])
    launcher_cmd.append("--")
    launcher_cmd.extend(cmd)
    return launcher_cmd


def spawn_supervised_child(
    cmd: list[str],
    lock_fd: int | None = None,
    cwd: Path | str | None = None,
    env: dict | None = None,
    stdout: Any = subprocess.PIPE,
    stderr: Any = subprocess.PIPE,
    **kwargs,
) -> subprocess.Popen:
    """Synchronously spawn a child process under dashboard.launcher supervision."""
    parent_pid = os.getpid()
    parent_start_time = get_process_start_time(parent_pid) or 0

    if lock_fd is not None:
        os.set_inheritable(lock_fd, True)
        pass_fds = kwargs.pop("pass_fds", ())
        if lock_fd not in pass_fds:
            pass_fds = (*tuple(pass_fds), lock_fd)
        kwargs["pass_fds"] = pass_fds

    wrapped_cmd = build_supervised_cmd(
        cmd,
        parent_pid=parent_pid,
        parent_start_time=parent_start_time,
        lock_fd=lock_fd,
    )

    return subprocess.Popen(
        wrapped_cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=stdout,
        stderr=stderr,
        **kwargs,
    )


async def async_spawn_supervised_child(
    cmd: list[str],
    lock_fd: int | None = None,
    cwd: Path | str | None = None,
    env: dict | None = None,
    **kwargs,
) -> asyncio.subprocess.Process:
    """Asynchronously spawn a child process under dashboard.launcher supervision."""
    parent_pid = os.getpid()
    parent_start_time = get_process_start_time(parent_pid) or 0

    pass_fds = kwargs.pop("pass_fds", ())
    if lock_fd is not None:
        os.set_inheritable(lock_fd, True)
        if lock_fd not in pass_fds:
            pass_fds = (*tuple(pass_fds), lock_fd)

    wrapped_cmd = build_supervised_cmd(
        cmd,
        parent_pid=parent_pid,
        parent_start_time=parent_start_time,
        lock_fd=lock_fd,
    )

    return await asyncio.create_subprocess_exec(
        *wrapped_cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        pass_fds=pass_fds,
        **kwargs,
    )
