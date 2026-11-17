#!/usr/bin/env python3
"""Receipt + fresh-seal preparation only. No signals, starts, service edits or recovery.

A manual maintenance/re-login acknowledgement is mandatory; cross-boot preparation
additionally requires explicit acknowledgement. Existing reviewed ownership, source,
state, job/executor, lock and startup checks are retained unchanged.
"""

import argparse
import hashlib
import json
import shlex
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def boot_id():
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def runtime(release):
    root = Path(release).absolute()
    if root.is_symlink():
        raise ValueError("Symlink release refused")
    manifest = json.loads((root / "MANIFEST.json").read_text())
    reviewed = json.loads((root / "HANDOFF_SOURCE.json").read_text())
    if digest(root / "HANDOFF_SOURCE.json") != manifest["files"]["HANDOFF_SOURCE.json"]:
        raise ValueError("Startup manifest mismatch")
    for name, expected in reviewed["files"].items():
        p = Path(name)
        if p.is_absolute() or ".." in p.parts or (root / p).is_symlink() or digest(root / p) != expected:
            raise ValueError("Reviewed source mismatch")
    sys.path.insert(0, str(root / "src"))
    from catalog_front.binding import listener_owned, process_identity
    from catalog_front.files import read_private
    from quiescent_handoff.operator import alive, metadata_location, seal, write_private
    from quiescent_handoff.state import Unsafe

    return (
        root,
        reviewed,
        (
            process_identity,
            listener_owned,
            read_private,
            alive,
            seal,
            write_private,
            metadata_location,
            Unsafe,
        ),
    )


def clean_sidecars(anchor):
    """No implicit SQLite crash recovery on canonical files is qualified here."""
    from quiescent_handoff.state import Unsafe, registry_image, safe_path

    registry = safe_path(anchor["state"]["registry"]["path"])

    def check(db):
        for suffix in ("-journal", "-wal", "-shm"):
            p = safe_path(str(db) + suffix)
            if p.exists() and p.stat().st_size:
                raise Unsafe(
                    "Nonempty SQLite sidecar requires separately reviewed crash/WAL recovery; no automatic restart"
                )

    check(registry)
    tasks, _, _, _ = registry_image(registry)
    for task in tasks:
        check(safe_path(task["worktree_path"]) / "orchestrator/var/checkpoints.db")


def enroll(release, plan_file, output):
    root, reviewed, helpers = runtime(release)
    identity, listener_owned, read_private, alive, seal, write_private, location, Unsafe = helpers
    p = Path(plan_file).absolute()
    plan = json.loads(read_private(p, 16_000_000))
    if Path(plan["release_root"]) != root or plan["release_files"] != reviewed["files"]:
        raise Unsafe("Plan/release contract mismatch")
    owner_path = p.with_name(p.name + ".owner.json")
    owner = json.loads(read_private(owner_path, 100_000))
    if identity(owner["pid"]) != owner:
        raise Unsafe("Ready owner identity is not current")
    port = int(plan["anchor"]["configuration"]["DASHBOARD_PORT"])
    if not listener_owned(owner["pid"], f"http://127.0.0.1:{port}"):
        raise Unsafe("Ready owner does not own configured listener")
    target = location(output, [*plan["metadata_exclusions"], str(root)])
    if target.parent != Path(plan["lease_file"]).parent or target.parent != p.parent:
        raise Unsafe("Receipt/plan/lease must share dedicated private metadata directory")
    receipt = {
        "schema": "fresh-restart-receipt/v1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "boot_id": boot_id(),
        "owner": owner,
        "owner_record": str(owner_path),
        "source_plan": str(p),
        "source_plan_sha256": digest(p),
        "release_root": str(root),
        "release_contract_sha256": digest(root / "HANDOFF_SOURCE.json"),
        "lease_file": plan["lease_file"],
        "port": port,
        "meaning": "Observed ready owner identity, not permission for concurrent ownership or session export",
    }
    write_private(target, receipt)
    return {"receipt": str(target), "owner_pid": owner["pid"], "signals_or_state_changes": False}


def prepare(
    release,
    receipt_file,
    output,
    mode="guarded",
    ack_maintenance=False,
    ack_relogin=False,
    ack_cross_boot=False,
):
    root, reviewed, helpers = runtime(release)
    identity, listener_owned, read_private, alive, seal, write_private, location, Unsafe = helpers
    if ack_maintenance is not True or ack_relogin is not True:
        raise Unsafe("Explicit protected maintenance and re-login acknowledgements required")
    receipt = json.loads(read_private(receipt_file, 200_000))
    if receipt["schema"] != "fresh-restart-receipt/v1" or Path(receipt["release_root"]) != root:
        raise Unsafe("Receipt contract differs")
    if receipt["release_contract_sha256"] != digest(root / "HANDOFF_SOURCE.json"):
        raise Unsafe("Reviewed release changed")
    if receipt["boot_id"] != boot_id() and ack_cross_boot is not True:
        raise Unsafe("Cross-boot owner record requires explicit review; not a reusable PID identity")
    old_path = Path(receipt["source_plan"])
    if digest(old_path) != receipt["source_plan_sha256"]:
        raise Unsafe("Original owner plan changed")
    old = json.loads(read_private(old_path, 16_000_000))
    owner = json.loads(read_private(receipt["owner_record"], 100_000))
    if owner != receipt["owner"] or old["lease_file"] != receipt["lease_file"]:
        raise Unsafe("Owner/lease receipt binding changed")
    if alive(owner):
        raise Unsafe("Previous owner is alive; this tool never stops it")
    if mode not in ("guarded", "rollback_bridge"):
        raise Unsafe("Unsupported mode")
    target = location(output, [*old["metadata_exclusions"], str(root)])
    if target.parent != Path(receipt["lease_file"]).parent or Path(receipt_file).parent != target.parent:
        raise Unsafe("Use the original private metadata directory and authority lease")
    if target.exists() or target.with_name(target.name + ".owner.json").exists():
        raise Unsafe("A fresh plan filename and readiness record are required")
    # Reserve no listener and signal nobody. Occupied port is a refusal, not a takeover.
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", receipt["port"]))
    clean_sidecars(old["anchor"])
    # The shared reviewed seal enforces leases, current directories/files/schema,
    # active jobs/executors and existing action/execution fences. No override exists.
    plan = seal(
        old["anchor"], receipt["lease_file"], root, reviewed["files"], mode=mode, previous_owner=owner
    )
    clean_sidecars(old["anchor"])
    write_private(target, plan)
    argv = [
        owner["argv"][0],
        "-m",
        "quiescent_handoff",
        "--plan",
        str(target),
        "--port",
        str(receipt["port"]),
    ]
    return {
        "fresh_plan": str(target),
        "mode": mode,
        "unresolved_actions_preserved": plan["state"]["unresolved_count"],
        "start_argv": argv,
        "start_command_for_operator": shlex.join(argv),
        "required_environment": {"PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
        "catalogue_environment": "Retain the existing reviewed DASHBOARD_MODEL_CATALOG_FILE; no credential is passed in argv",
        "service_started": False,
        "session_policy": "All old in-memory sessions end; same account records, explicit re-login",
        "next": "Review output, select this fresh plan in the unit for a separate controlled start, then enroll its actual ready owner. Never blindly restart the old plan.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release", required=True)
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("enroll")
    q.add_argument("--plan", required=True)
    q.add_argument("--output", required=True)
    q = sub.add_parser("prepare")
    q.add_argument("--receipt", required=True)
    q.add_argument("--output", required=True)
    q.add_argument("--mode", choices=("guarded", "rollback_bridge"), default="guarded")
    q.add_argument("--ack-maintenance", action="store_true")
    q.add_argument("--ack-relogin", action="store_true")
    q.add_argument("--ack-cross-boot", action="store_true")
    a = p.parse_args()
    try:
        if a.command == "enroll":
            result = enroll(a.release, a.plan, a.output)
        else:
            result = prepare(
                a.release, a.receipt, a.output, a.mode, a.ack_maintenance, a.ack_relogin, a.ack_cross_boot
            )
        print(json.dumps(result))
        return 0
    except Exception as exc:
        # No original request, auth, SQL data or raw exception text leaves private metadata.
        print(
            json.dumps(
                {
                    "refused": True,
                    "reason_class": type(exc).__name__,
                    "reason": str(exc)
                    if type(exc).__name__ in ("Unsafe", "BindingError")
                    else "Private input, path, port or source validation failed",
                    "signals": False,
                    "service_started": False,
                    "canonical_state_mutated": False,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
