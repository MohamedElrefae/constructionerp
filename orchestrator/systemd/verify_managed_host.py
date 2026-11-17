#!/usr/bin/env python3
"""Read-only host verification for the uninstalled managed-service candidate.

Run as root only after a separate, reviewed installation. This checks active
systemd properties, actual loopback-only namespace links, cgroup membership,
peer credentials and T3 listener ownership. It prints no token values and
does not send a supervisor protocol frame or call any provider.
"""

from __future__ import annotations

import argparse
import grp
import json
import os
import pwd
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from managed_supervisor_attestation import (
    AttestationError,
    attest_managed_supervisor,
    load_root_owned_config,
)


class HostVerificationError(RuntimeError):
    pass


SYSTEMCTL = "/usr/bin/systemctl"
IP = "/usr/sbin/ip"


def run_readonly(argv: list[str], *, runner=subprocess.run, timeout=5) -> str:
    try:
        result = runner(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
            check=False,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        raise HostVerificationError("host verification command unavailable or timed out") from None
    if result.returncode != 0:
        raise HostVerificationError("host verification command failed")
    return result.stdout


def parse_properties(text: str) -> dict[str, str]:
    properties = {}
    for line in text.splitlines():
        if "=" not in line:
            raise HostVerificationError("systemd returned malformed unit properties")
        key, value = line.split("=", 1)
        properties[key] = value
    return properties


def verify_unit(
    unit: str,
    *,
    user: str,
    group: str,
    runner=subprocess.run,
    required_properties: dict[str, str] | None = None,
) -> dict[str, str]:
    requested = "ActiveState,MainPID,User,Group,KillMode,NoNewPrivileges,ProtectControlGroups,ControlGroup"
    if required_properties:
        requested += "," + ",".join(required_properties)
    text = run_readonly([SYSTEMCTL, "show", "--no-pager", f"--property={requested}", unit], runner=runner)
    values = parse_properties(text)
    expected = {
        "ActiveState": "active",
        "User": user,
        "Group": group,
        "KillMode": "control-group",
        "NoNewPrivileges": "yes",
        "ProtectControlGroups": "yes",
    }
    if any(values.get(key) != value for key, value in expected.items()):
        raise HostVerificationError(f"{unit} active state or sandbox properties mismatch")
    for key, value in (required_properties or {}).items():
        observed = values.get(key, "")
        if key == "CapabilityBoundingSet":
            if observed.lower().split() != value.lower().split():
                raise HostVerificationError(f"{unit} capability bounding set mismatch")
        elif observed != value:
            raise HostVerificationError(f"{unit} required sandbox property mismatch")
    cgroup = values.get("ControlGroup", "")
    if not cgroup.startswith("/system.slice/") or not cgroup.endswith(".service"):
        raise HostVerificationError(f"{unit} has no systemd service cgroup")
    try:
        main_pid = int(values.get("MainPID", ""))
    except ValueError:
        raise HostVerificationError(f"{unit} has no numeric MainPID") from None
    if main_pid <= 0:
        raise HostVerificationError(f"{unit} has no running MainPID")
    return values


def verify_verifier_process(pid: int, cgroup: str, *, proc_root=Path("/proc")) -> None:
    """Check root verifier MainPID's effective identity, cgroup and ptrace cap."""
    try:
        status = (Path(proc_root) / str(pid) / "status").read_text(encoding="ascii")
        groups = (Path(proc_root) / str(pid) / "cgroup").read_text(encoding="ascii").splitlines()
        uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
        gid_line = next(line for line in status.splitlines() if line.startswith("Gid:"))
        effective_uid = int(uid_line.split()[2])
        effective_gid = int(gid_line.split()[2])
        cap_bnd = int(next(line.split()[1] for line in status.splitlines() if line.startswith("CapBnd:")), 16)
        cap_eff = int(next(line.split()[1] for line in status.splitlines() if line.startswith("CapEff:")), 16)
    except (OSError, StopIteration, IndexError, ValueError, UnicodeDecodeError):
        raise HostVerificationError(
            "root verifier process identity or capabilities are uninspectable"
        ) from None
    try:
        expected_gid = grp.getgrnam("managed-supervisor").gr_gid
    except KeyError:
        raise HostVerificationError("managed-supervisor group is missing") from None
    ptrace = 1 << 19  # Linux CAP_SYS_PTRACE
    if (
        effective_uid != 0
        or effective_gid != expected_gid
        or sorted(groups) != [f"0::{cgroup}"]
        or cap_bnd != ptrace
        or cap_eff & ptrace == 0
    ):
        raise HostVerificationError("root verifier process identity, cgroup, or CAP_SYS_PTRACE mismatch")


def verify_loopback_only_links(text: str) -> None:
    try:
        links = json.loads(text)
    except (ValueError, TypeError):
        raise HostVerificationError("namespace link state is not valid JSON") from None
    if not isinstance(links, list) or len(links) != 1 or not isinstance(links[0], dict):
        raise HostVerificationError("T3 namespace has an unexpected network interface set")
    link = links[0]
    if link.get("ifname") != "lo" or "UP" not in link.get("flags", []):
        raise HostVerificationError("T3 namespace loopback interface is absent or down")


def verify_attested_cgroups(result: dict, *, supervisor_unit: dict, t3_unit: dict) -> None:
    if result.get("identity_observed") is not True:
        raise HostVerificationError("process attestation did not report verified identity")
    try:
        supervisor_pid = int(result["supervisor_pid"])
        main_supervisor_pid = int(supervisor_unit["MainPID"])
    except (KeyError, TypeError, ValueError):
        raise HostVerificationError("supervisor MainPID or attested peer PID is malformed") from None
    if supervisor_pid != main_supervisor_pid:
        raise HostVerificationError("attested supervisor peer is not the active unit MainPID")
    for field, unit in (("supervisor_cgroup_membership", supervisor_unit), ("t3_cgroup_membership", t3_unit)):
        lines = result.get(field)
        expected = f"0::{unit.get('ControlGroup', '')}"
        if not isinstance(lines, list) or len(lines) != 1 or lines[0] != expected or expected == "0::":
            raise HostVerificationError(f"attested {field} differs from the exact systemd cgroup")
    try:
        listener_port = int(result["t3_listener_port"])
    except (KeyError, TypeError, ValueError):
        raise HostVerificationError("attested T3 listener port is malformed") from None
    if (
        result.get("t3_listener_host") != "127.0.0.1"
        or not 1 <= listener_port <= 65535
        or not isinstance(result.get("listener_inode"), str)
        or not result["listener_inode"].isdigit()
    ):
        raise HostVerificationError("attested T3 listener is not a pinned IPv4 loopback socket")


def verify_owned_path(path: str | Path, *, owner: str, group: str, mode: int, kind: str = "file") -> None:
    try:
        metadata = Path(path).lstat()
        expected_uid = pwd.getpwnam(owner).pw_uid
        expected_gid = grp.getgrnam(group).gr_gid
    except (OSError, KeyError):
        raise HostVerificationError("required service file or account is missing") from None
    type_ok = (
        stat.S_ISREG(metadata.st_mode)
        if kind == "file"
        else (stat.S_ISSOCK(metadata.st_mode) if kind == "socket" else stat.S_ISDIR(metadata.st_mode))
    )
    if (
        not type_ok
        or metadata.st_uid != expected_uid
        or metadata.st_gid != expected_gid
        or stat.S_IMODE(metadata.st_mode) != mode
    ):
        raise HostVerificationError("required service file ownership or mode mismatch")


def verify_service_config(
    config: dict, *, dashboard_user: str, dashboard_group: str, socket_path: str
) -> None:
    try:
        dashboard_uid = pwd.getpwnam(dashboard_user).pw_uid
        dashboard_gid = grp.getgrnam(dashboard_group).gr_gid
        managed_socket_gid = grp.getgrnam("managed-dashboard").gr_gid
    except KeyError:
        raise HostVerificationError("dashboard account or socket group is missing") from None
    if (
        not isinstance(config, dict)
        or config.get("schema") != "managed-supervisor-service/v1"
        or config.get("client_uid") != dashboard_uid
        or config.get("socket_group_gid") != dashboard_gid
        or dashboard_gid != managed_socket_gid
        or config.get("socket_path") != socket_path
        or config.get("base_url") != "http://127.0.0.1:46687"
        or config.get("provider") != "opencode"
    ):
        raise HostVerificationError("service config peer, socket, or endpoint identity mismatch")


def verify_host(
    config_path: str | Path,
    *,
    dashboard_user: str,
    dashboard_group: str,
    runner=subprocess.run,
    attestor=attest_managed_supervisor,
) -> dict:
    if os.geteuid() != 0:
        raise HostVerificationError("host verification must run as root")
    units = {
        "managed-t3-netns.service": ("root", "root"),
        "managed-t3-egress.service": ("managed-egress", "managed-t3-egress"),
        "managed-t3.service": ("managed-t3", "managed-t3-egress"),
        "managed-supervisor.service": ("managed-supervisor", "managed-dashboard"),
        "managed-attestation-verifier.service": ("root", "managed-supervisor"),
    }
    unit_state = {
        unit: verify_unit(
            unit,
            user=identity[0],
            group=identity[1],
            runner=runner,
            required_properties=(
                {"CapabilityBoundingSet": "cap_sys_ptrace", "RestrictAddressFamilies": "AF_UNIX"}
                if unit == "managed-attestation-verifier.service"
                else None
            ),
        )
        for unit, identity in units.items()
        if unit != "managed-t3-netns.service"
    }
    verifier_pid = int(unit_state["managed-attestation-verifier.service"]["MainPID"])
    verifier_cgroup = unit_state["managed-attestation-verifier.service"]["ControlGroup"]
    verify_verifier_process(verifier_pid, verifier_cgroup)
    verify_owned_path(
        "/run/managed-attestation-verifier",
        owner="root",
        group="managed-supervisor",
        mode=0o750,
        kind="directory",
    )
    verify_owned_path(
        "/run/managed-attestation-verifier/verify.sock",
        owner="root",
        group="managed-supervisor",
        mode=0o660,
        kind="socket",
    )
    netns = parse_properties(
        run_readonly(
            [SYSTEMCTL, "show", "--no-pager", "--property=ActiveState", "managed-t3-netns.service"],
            runner=runner,
        )
    )
    if netns.get("ActiveState") != "active":
        raise HostVerificationError("managed T3 network namespace unit is not active")
    links = run_readonly([IP, "netns", "exec", "managed-t3", IP, "-j", "link", "show"], runner=runner)
    verify_loopback_only_links(links)
    verify_owned_path(
        "/run/managed-t3-egress",
        owner="managed-egress",
        group="managed-t3-egress",
        mode=0o750,
        kind="directory",
    )
    verify_owned_path(
        "/run/managed-t3-egress/broker.sock",
        owner="managed-egress",
        group="managed-t3-egress",
        mode=0o660,
        kind="socket",
    )
    attested = attestor(config_path)
    verify_attested_cgroups(
        attested,
        supervisor_unit=unit_state["managed-supervisor.service"],
        t3_unit=unit_state["managed-t3.service"],
    )
    config = load_root_owned_config(config_path)
    verify_owned_path(
        config.socket_path, owner="managed-supervisor", group="managed-dashboard", mode=0o660, kind="socket"
    )
    config_file = Path("/etc/managed-supervisor/service.json")
    verify_owned_path(config_file, owner="managed-supervisor", group="managed-supervisor", mode=0o600)
    service_config = json.loads(config_file.read_text(encoding="utf-8"))
    verify_service_config(
        service_config,
        dashboard_user=dashboard_user,
        dashboard_group=dashboard_group,
        socket_path=str(config.socket_path),
    )
    for path in (
        "/etc/managed-supervisor/service.json",
        "/etc/managed-supervisor/credentials/protocol-token",
        "/etc/managed-supervisor/credentials/mcp-token",
    ):
        verify_owned_path(path, owner="managed-supervisor", group="managed-supervisor", mode=0o600)
    verify_owned_path(
        "/etc/managed-dashboard/credentials/supervisor-token",
        owner=dashboard_user,
        group=dashboard_user,
        mode=0o600,
    )
    return {
        "verified": True,
        "units": sorted([*unit_state, "managed-t3-netns.service"]),
        "supervisor_pid": attested["supervisor_pid"],
        "t3_pid": attested["t3_pid"],
        "t3_listener_port": attested["t3_listener_port"],
        "controls_attested": [
            "peer pid/uid",
            "process start times",
            "process cgroups",
            "shared network namespace",
            "T3 loopback listener inode owner",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attestation-config", required=True)
    parser.add_argument("--dashboard-user", required=True, help="existing dashboard service account name")
    parser.add_argument(
        "--dashboard-group", required=True, help="existing group allowed to access supervisor socket"
    )
    args = parser.parse_args(argv)
    try:
        print(
            json.dumps(
                verify_host(
                    args.attestation_config,
                    dashboard_user=args.dashboard_user,
                    dashboard_group=args.dashboard_group,
                ),
                sort_keys=True,
            )
        )
    except (AttestationError, HostVerificationError, KeyError, TypeError) as exc:
        print(f"managed host verification failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
