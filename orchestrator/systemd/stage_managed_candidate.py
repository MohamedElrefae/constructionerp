#!/usr/bin/env python3
"""Build a private, uninstalled file staging tree for the managed-service units.

This tool never writes outside the new ``--output`` directory, changes owners,
creates users/groups, installs units, starts services, or provisions provider
credentials. The emitted ownership manifest is for a separately reviewed
installer. An absent MCP token and dispatch gate intentionally prevent startup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys


SOURCE_ROOT = Path(__file__).resolve().parents[1]
SYSTEMD_SOURCE = SOURCE_ROOT / "systemd"
ALLOWED_FILES = (
    "managed_supervisor_service.py", "managed_supervisor_attestation.py",
    "t3_supervisor.py", "t3_supervisor_client.py", "t3_transport.py",
)
UNIT_FILES = (
    "managed-attestation-verifier.service",
    "managed-t3-netns.service", "managed-t3-egress.service",
    "managed-t3.service", "managed-supervisor.service",
)
SYSTEMD_SUPPORT_FILES = (
    "managed_netns.py", "https_connect_broker.py", "t3_private_proxy_runner.py",
    "verify_managed_host.py", "managed_supervisor_attestation_hook.py",
    "managed_attestation_verifier.py",
)
TMPFILES_FILES = (
    "managed-supervisor-attestation.tmpfiles",
    "managed-attestation-verifier.tmpfiles",
)


class StagingError(ValueError):
    pass


def _safe_existing_directory(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise StagingError("source directory is missing or a symlink")
    return path.resolve(strict=True)


def _write_new(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, flags, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    os.chmod(path, mode)


def stage_candidate(output: str | Path, *, dashboard_uid: int, dashboard_gid: int,
                    allowed_models: list[str], model: str) -> Path:
    """Create a new private staging tree; do not overwrite any existing path."""
    output_path = Path(output)
    if (not output_path.is_absolute() or output_path == Path("/")
            or output_path.name in ("", ".", "..")):
        raise StagingError("--output must be a new absolute directory")
    if (isinstance(dashboard_uid, bool) or not isinstance(dashboard_uid, int) or dashboard_uid <= 0
            or isinstance(dashboard_gid, bool) or not isinstance(dashboard_gid, int) or dashboard_gid < 0):
        raise StagingError("dashboard UID/GID values are invalid")
    if (not isinstance(allowed_models, list) or not allowed_models
            or any(not isinstance(item, str) or not item.strip() for item in allowed_models)
            or len(set(allowed_models)) != len(allowed_models) or model not in allowed_models):
        raise StagingError("model must be in a nonempty unique allowed model list")
    supported_prefixes = ("opencode/", "opencode-go/")
    if any(not any(item.startswith(prefix) and len(item) > len(prefix)
                   for prefix in supported_prefixes) for item in allowed_models):
        raise StagingError(
            "this candidate supports only OpenCode/OpenCode Go model IDs because its egress broker allows opencode.ai"
        )
    if any("\n" in item or "\r" in item for item in allowed_models):
        raise StagingError("model identifiers cannot contain line breaks")

    parent = _safe_existing_directory(output_path.parent)
    output_path = parent / output_path.name
    if output_path.exists() or output_path.is_symlink():
        raise StagingError("output already exists; refusing to replace user files")
    output_path.mkdir(mode=0o700)
    os.chmod(output_path, 0o700)

    try:
        staged_hashes = {}
        target_root = output_path / "opt" / "managed-supervisor" / "orchestrator"
        target_root.mkdir(parents=True, mode=0o755)
        for filename in ALLOWED_FILES:
            source = SOURCE_ROOT / filename
            if source.is_symlink() or not source.is_file():
                raise StagingError(f"required source file is missing or unsafe: {filename}")
            data = source.read_bytes()
            _write_new(target_root / filename, data, 0o644)
            staged_hashes[f"opt/managed-supervisor/orchestrator/{filename}"] = hashlib.sha256(data).hexdigest()
        target_systemd = target_root / "systemd"
        target_systemd.mkdir(mode=0o755)
        for filename in SYSTEMD_SUPPORT_FILES:
            source = SYSTEMD_SOURCE / filename
            if source.is_symlink() or not source.is_file():
                raise StagingError(f"required systemd helper is missing or unsafe: {filename}")
            data = source.read_bytes()
            _write_new(target_systemd / filename, data, 0o755 if filename.endswith(".py") else 0o644)
            staged_hashes[
                f"opt/managed-supervisor/orchestrator/systemd/{filename}"
            ] = hashlib.sha256(data).hexdigest()

        units_dir = output_path / "etc" / "systemd" / "system"
        units_dir.mkdir(parents=True, mode=0o755)
        for filename in UNIT_FILES:
            data = (SYSTEMD_SOURCE / filename).read_bytes()
            _write_new(units_dir / filename, data, 0o644)
            staged_hashes[f"etc/systemd/system/{filename}"] = hashlib.sha256(data).hexdigest()
        for tmpfiles_name in TMPFILES_FILES:
            tmpfiles_data = (SYSTEMD_SOURCE / tmpfiles_name).read_bytes()
            dest_name = tmpfiles_name.replace(".tmpfiles", ".conf")
            tmpfiles_dest = output_path / "etc/tmpfiles.d" / dest_name
            _write_new(tmpfiles_dest, tmpfiles_data, 0o644)
            staged_hashes[f"etc/tmpfiles.d/{dest_name}"] = hashlib.sha256(
                tmpfiles_data).hexdigest()

        # This shared token is generated once, stored as two private staged
        # copies, and never returned or written into the manifest/stdout.
        token = (secrets.token_urlsafe(48) + "\n").encode("ascii")
        supervisor_token = output_path / "etc/managed-supervisor/credentials/protocol-token"
        dashboard_token = output_path / "etc/managed-dashboard/credentials/supervisor-token"
        _write_new(supervisor_token, token, 0o600)
        _write_new(dashboard_token, token, 0o600)

        service_config = {
            "schema": "managed-supervisor-service/v1",
            "socket_path": "/run/managed-supervisor/managed.sock",
            "state_path": "/var/lib/managed-supervisor/state.json",
            "token_file": "/etc/managed-supervisor/credentials/protocol-token",
            "mcp_token_file": "/etc/managed-supervisor/credentials/mcp-token",
            "client_uid": dashboard_uid,
            "socket_group_gid": dashboard_gid,
            "base_url": "http://127.0.0.1:46687",
            "provider": "opencode",
            "model": model,
            "allowed_models": allowed_models,
        }
        _write_new(
            output_path / "etc/managed-supervisor/service.json",
            (json.dumps(service_config, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            0o600,
        )
        ownership = {
            "root:root": ["/opt/managed-supervisor/**", "/etc/systemd/system/managed-*.service"],
            "root:managed-supervisor mode 0750": [
                "/etc/managed-supervisor", "/etc/managed-supervisor/credentials",
            ],
            "managed-supervisor:managed-supervisor mode 0600": [
                "/etc/managed-supervisor/service.json",
                "/etc/managed-supervisor/credentials/protocol-token",
                "/etc/managed-supervisor/credentials/mcp-token (must be provisioned separately)",
            ],
            "dashboard:dashboard mode 0700": ["/etc/managed-dashboard/credentials"],
            "dashboard:dashboard mode 0600": ["/etc/managed-dashboard/credentials/supervisor-token"],
            "not created": [
                "/etc/managed-supervisor/dispatch-reviewed.enable",
                "/etc/managed-supervisor/credentials/mcp-token",
            ],
        }
        _write_new(
            output_path / "ownership-plan.json",
            (json.dumps(ownership, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            0o600,
        )
        _write_new(
            output_path / "staged-files.sha256.json",
            (json.dumps(staged_hashes, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            0o600,
        )
        _write_new(
            output_path / "INSTALL-NOTES.txt",
            b"UNINSTALLED CANDIDATE. No users, groups, credentials, units, or services were changed.\n"
            b"Do not install until T3 executable/API/auth, namespace policy, attestation, dashboard\n"
            b"authorization, and service ownership have been reviewed. MCP token is intentionally absent.\n",
            0o600,
        )
        return output_path
    except BaseException:
        # Only remove the newly-created staging tree. No pre-existing target is
        # ever touched because creation above used mkdir(exist_ok=False).
        shutil.rmtree(output_path, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="new absolute staging directory")
    parser.add_argument("--dashboard-uid", required=True, type=int)
    parser.add_argument("--dashboard-gid", required=True, type=int)
    parser.add_argument("--model", required=True)
    parser.add_argument("--allowed-model", action="append", required=True)
    args = parser.parse_args(argv)
    try:
        stage_candidate(args.output, dashboard_uid=args.dashboard_uid,
                        dashboard_gid=args.dashboard_gid,
                        allowed_models=args.allowed_model, model=args.model)
    except (OSError, StagingError) as exc:
        parser.error(str(exc))
    print("staging tree created with mode 0700; no host users, files, units, or services were changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
