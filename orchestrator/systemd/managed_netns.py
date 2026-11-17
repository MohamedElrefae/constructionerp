#!/usr/bin/env python3
"""Root-only lifecycle for the fixed, loopback-only managed T3 namespace.

The namespace is intentionally created with no veth or external interface.
T3 egress is mediated through the separate host-side Unix-socket HTTPS broker;
T3's local server and the supervisor share this namespace for loopback traffic.
This helper never configures routes, NAT, DNS, or a host-facing interface.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


NAMESPACE = "managed-t3"
NAMESPACE_PATH = Path("/run/netns") / NAMESPACE
IP = Path("/usr/sbin/ip")


class NamespaceError(RuntimeError):
    pass


def _run(args: list[str]) -> None:
    try:
        result = subprocess.run(
            [str(IP), *args], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=5, check=False,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        raise NamespaceError("iproute2 namespace operation failed") from None
    if result.returncode != 0:
        raise NamespaceError("iproute2 namespace operation was refused")


def create() -> None:
    if os.geteuid() != 0:
        raise NamespaceError("namespace lifecycle requires root")
    if NAMESPACE_PATH.exists() or NAMESPACE_PATH.is_symlink():
        raise NamespaceError("managed namespace already exists; refusing to adopt it")
    _run(["netns", "add", NAMESPACE])
    try:
        _run(["netns", "exec", NAMESPACE, str(IP), "link", "set", "lo", "up"])
        if not NAMESPACE_PATH.exists() or NAMESPACE_PATH.is_symlink():
            raise NamespaceError("created namespace path is missing or unsafe")
    except BaseException:
        try:
            _run(["netns", "del", NAMESPACE])
        except NamespaceError:
            pass
        raise


def delete() -> None:
    if os.geteuid() != 0:
        raise NamespaceError("namespace lifecycle requires root")
    if not NAMESPACE_PATH.exists() and not NAMESPACE_PATH.is_symlink():
        return
    if NAMESPACE_PATH.is_symlink():
        raise NamespaceError("namespace path is a symlink; refusing deletion")
    _run(["netns", "del", NAMESPACE])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "delete"))
    args = parser.parse_args(argv)
    try:
        (create if args.action == "create" else delete)()
    except NamespaceError as exc:
        print(f"managed namespace: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
