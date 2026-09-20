"""Trusted Pre-Exec PDEATHSIG Launcher with Parent Identity Verification.

Spawns child subprocesses (Git and orchestrator commands) with:
1. PR_SET_PDEATHSIG set to SIGTERM
2. Verification of os.getppid() == parent_pid
3. Verification of parent start_time from /proc/<ppid>/stat against parent_start_time
4. Inherited lock file descriptor preserved
5. execvp into target command
"""

import argparse
import ctypes
import os
import signal
import sys


def main():
    parser = argparse.ArgumentParser(description="Trusted PDEATHSIG Child Process Launcher")
    parser.add_argument("--parent-pid", type=int, required=True, help="Expected parent PID")
    parser.add_argument(
        "--parent-start-time", type=int, required=True, help="Expected parent process start time"
    )
    parser.add_argument("--lock-fd", type=int, default=None, help="Inherited file descriptor holding lock")
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Target command to exec")

    args = parser.parse_args()
    if not args.cmd or args.cmd == ["--"]:
        sys.stderr.write("No command specified to exec\n")
        os._exit(1)

    cmd = args.cmd
    if cmd[0] == "--":
        cmd = cmd[1:]

    # 1. Set parent-death signal to SIGTERM
    try:
        libc = ctypes.CDLL("libc.so.6")
        PR_SET_PDEATHSIG = 1
        res = libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)
        if res != 0:
            sys.stderr.write(f"prctl PR_SET_PDEATHSIG failed with code {res}\n")
            os._exit(1)
    except Exception as exc:
        sys.stderr.write(f"Failed to set PR_SET_PDEATHSIG: {exc}\n")
        os._exit(1)

    # 2. Race check: Verify parent has not already died or changed between fork and prctl
    current_ppid = os.getppid()
    if current_ppid != args.parent_pid:
        sys.stderr.write(f"Parent process died or changed: {current_ppid} != {args.parent_pid}\n")
        os._exit(1)

    # 3. PID reuse check: Verify parent start-time matches expected
    try:
        with open(f"/proc/{current_ppid}/stat", "r") as f:
            stat_content = f.read()
            rparen = stat_content.rfind(")")
            if rparen == -1:
                os._exit(1)
            remaining_fields = stat_content[rparen + 2 :].split()
            actual_ppid_start_time = int(remaining_fields[19])
        if actual_ppid_start_time != args.parent_start_time:
            sys.stderr.write(
                f"Parent start time mismatch: {actual_ppid_start_time} != {args.parent_start_time}\n"
            )
            os._exit(1)
    except Exception as exc:
        sys.stderr.write(f"Failed to verify parent start time: {exc}\n")
        os._exit(1)

    # 4. If lock_fd was specified, ensure it is not closed on exec
    if args.lock_fd is not None:
        try:
            os.set_inheritable(args.lock_fd, True)
        except Exception:
            pass

    # 5. Exec target command
    try:
        os.execvp(cmd[0], cmd)
    except Exception as exc:
        sys.stderr.write(f"execvp failed for {cmd[0]}: {exc}\n")
        os._exit(1)


if __name__ == "__main__":
    main()
