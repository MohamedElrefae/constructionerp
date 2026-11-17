#!/usr/bin/env python3
"""Read-only host prerequisite check for the disabled managed-service candidate.

This is not an installer or deployment approval. It does not create accounts,
read credentials, run systemctl mutations, or contact T3/provider endpoints.
"""

from __future__ import annotations

import argparse
import grp
import json
import os
import pwd
import shutil
import subprocess
import sys
from pathlib import Path

SYSTEMCTL = "/usr/bin/systemctl"
T3_EXECUTABLE = Path("/usr/local/bin/t3")
MIN_FREE_BYTES = 16 * 1024 * 1024


def _systemd_manager(runner=subprocess.run) -> tuple[bool, str]:
    try:
        result = runner(
            [SYSTEMCTL, "show", "--no-pager", "--property=Version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
            check=False,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, "systemd manager query unavailable or timed out"
    if result.returncode != 0:
        return False, "systemd manager bus unavailable or denied"
    value = result.stdout.strip()
    if not value.startswith("Version=") or not value[8:].isdigit():
        return False, "systemd manager returned no numeric version"
    return True, value[8:]


def collect_preflight(
    *,
    dashboard_user: str,
    dashboard_group: str,
    runner=subprocess.run,
    disk_usage=shutil.disk_usage,
    proc_root=Path("/proc"),
    filesystem_root=Path("/"),
    cgroup_root=Path("/sys/fs/cgroup"),
    t3_executable=T3_EXECUTABLE,
) -> dict:
    checks: list[dict] = []

    def record(name, ok, detail, *, blocking=True):
        checks.append({"name": name, "ok": bool(ok), "blocking": blocking, "detail": str(detail)})

    record(
        "effective_root",
        os.geteuid() == 0,
        "root is required for installation and kernel process attestation",
    )

    try:
        pwd.getpwnam(dashboard_user)
        dashboard_gid = grp.getgrnam(dashboard_group).gr_gid
        groups = {
            name: grp.getgrnam(name)
            for name in (dashboard_group, "managed-dashboard", "managed-supervisor", "managed-t3-egress")
        }
        users = {
            name: pwd.getpwnam(name)
            for name in (dashboard_user, "managed-supervisor", "managed-t3", "managed-egress")
        }
        user_uids = [users[name].pw_uid for name in users]
        managed_group_ids = [
            groups[name].gr_gid for name in ("managed-dashboard", "managed-supervisor", "managed-t3-egress")
        ]
        t3_group_ok = (
            users["managed-t3"].pw_gid == groups["managed-t3-egress"].gr_gid
            or users["managed-t3"].pw_name in groups["managed-t3-egress"].gr_mem
        )
        dashboard_group_ok = (
            users[dashboard_user].pw_gid == groups["managed-dashboard"].gr_gid
            or dashboard_user in groups["managed-dashboard"].gr_mem
        )
        valid = (
            len(set(user_uids)) == len(user_uids)
            and all(uid > 0 for uid in user_uids)
            and len(set(managed_group_ids)) == len(managed_group_ids)
            and dashboard_gid == groups["managed-dashboard"].gr_gid
            and t3_group_ok
            and dashboard_group_ok
        )
        record(
            "service_accounts_and_groups",
            valid,
            "required distinct service UIDs and managed groups are provisioned"
            if valid
            else "dashboard socket group must be managed-dashboard and IDs must be distinct",
        )
    except KeyError as exc:
        record("service_accounts_and_groups", False, f"required account/group is missing: {exc.args[0]}")

    manager_ok, manager_info = _systemd_manager(runner=runner)
    record("systemd_manager", manager_ok, manager_info)

    cgroup_v2 = (Path(cgroup_root) / "cgroup.controllers").is_file() and (
        Path(cgroup_root) / "cgroup.procs"
    ).exists()
    record(
        "unified_cgroup_v2",
        cgroup_v2,
        "kernel exposes the unified cgroup v2 hierarchy"
        if cgroup_v2
        else "unified cgroup v2 hierarchy is unavailable",
    )

    ptrace_path = Path(proc_root) / "sys/kernel/yama/ptrace_scope"
    try:
        ptrace_scope = ptrace_path.read_text(encoding="ascii").strip()
        record(
            "ptrace_scope_observable",
            ptrace_scope.isdigit(),
            f"kernel ptrace_scope={ptrace_scope}"
            if ptrace_scope.isdigit()
            else "kernel ptrace_scope value is malformed",
            blocking=True,
        )
    except OSError:
        record("ptrace_scope_observable", False, "kernel ptrace_scope is missing or unreadable")

    try:
        free_bytes = disk_usage(filesystem_root).free
        record(
            "candidate_disk_space",
            free_bytes >= MIN_FREE_BYTES,
            f"{free_bytes} bytes free; at least {MIN_FREE_BYTES} required",
        )
    except OSError:
        record("candidate_disk_space", False, "target filesystem free space is uninspectable")

    ip_path = shutil.which("ip")
    record("iproute2", bool(ip_path), ip_path or "ip command is unavailable")
    t3_ok = Path(t3_executable).is_file() and os.access(t3_executable, os.X_OK)
    record(
        "approved_t3_executable_present",
        t3_ok,
        str(t3_executable) if t3_ok else f"{t3_executable} is missing or not executable",
    )

    blockers = [check["name"] for check in checks if check["blocking"] and not check["ok"]]
    return {
        "preflight_only": True,
        "installation_enabled": False,
        "deployment_ready": False,
        "dashboard_user": dashboard_user,
        "dashboard_group": dashboard_group,
        "checks": checks,
        "blocking_checks": blockers,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dashboard-user", required=True)
    parser.add_argument("--dashboard-group", required=True)
    args = parser.parse_args(argv)
    result = collect_preflight(dashboard_user=args.dashboard_user, dashboard_group=args.dashboard_group)
    print(json.dumps(result, sort_keys=True))
    return 0 if not result["blocking_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
