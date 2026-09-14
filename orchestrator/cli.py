"""Owner/operator interface. Agents cannot write the mounted control store."""

import argparse
import importlib.metadata
import json
import subprocess
import sys
import time
from pathlib import Path

from candidates import git
from core import WorkflowError, bytes_hash, canonical, execution_lock, within
from engine import Engine
from packaging.requirements import Requirement
from sandbox import probe
from validate import validate_document

ROOT = Path(__file__).resolve().parents[1]


def doctor(root):
    root = Path(root).resolve()
    pins = json.loads((root / "orchestrator/roles.json").read_text())
    checks = {
        "python": sys.version_info >= (3, 11),
        "sandbox_control_store_and_git_denial": probe(),
        "branch": git(root, "branch", "--show-current").decode().strip()
        == "feature/scope-context-portability",
        "worktree": root != Path("/home/mohamed/frappe-bench/apps/construction"),
    }
    for name in ("langgraph", "langgraph-checkpoint-sqlite", "pydantic", "jsonschema"):
        try:
            checks["dependency:" + name] = bool(importlib.metadata.version(name))
        except importlib.metadata.PackageNotFoundError:
            checks["dependency:" + name] = False
    for line in (root / "orchestrator/requirements.txt").read_text().splitlines():
        if line and not line.startswith((" ", "#", "-")) and "==" in line:
            requirement = Requirement(line.rstrip(" \\"))
            if requirement.marker and not requirement.marker.evaluate():
                continue
            try:
                checks["locked:" + requirement.name] = (
                    importlib.metadata.version(requirement.name) in requirement.specifier
                )
            except importlib.metadata.PackageNotFoundError:
                checks["locked:" + requirement.name] = False
    pins = None
    if (root / "orchestrator/var/checkpoints.db").exists():
        e = Engine(root)
        try:
            checks["sqlite_integrity"] = e.store.integrity()
            checks["recovery_cleared"] = not e.store.meta("recovery_required", False)
            if e.config:
                checks["configured_root"] = e.config["root"] == str(root)
                e.sync_roles_mirror()
                e.export()  # regenerate mirrors, never use them as control input
                pins = e.config.get("roles")
                roles_file = root / "orchestrator/roles.json"
                checks["roles_mirror_synced"] = (
                    roles_file.exists()
                    and canonical(json.loads(roles_file.read_text())) == canonical(pins)
                )
        finally:
            e.close()

    if not pins:
        pins = json.loads((root / "orchestrator/roles.json").read_text())

    for tool in {"codex", "opencode"}:
        pin = next((p for p in pins.values() if p["tool"] == tool), None)
        if not pin:
            checks["binary:" + tool] = False
            continue
        try:
            r = subprocess.run([pin["binary"], "--version"], capture_output=True, text=True, timeout=20)
            checks["binary:" + tool] = (
                r.returncode == 0
                and pin["version"] in r.stdout
                and bytes_hash(Path(pin["binary"]).read_bytes()) == pin["binary_sha256"]
            )
        except (OSError, subprocess.TimeoutExpired):
            checks["binary:" + tool] = False
    evidence = root / "docs/ai/work-items/scope-context-portability/evidence/phase-0-capabilities.json"
    checks["phase0_approved_capabilities"] = (
        evidence.exists()
        and json.loads(evidence.read_text()).get("phase_exit") == "PASSED_WITH_OWNER_DIRECTIVE"
    )
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "native_dispatch_requires_host_metadata_access": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("doctor", "init", "status", "run", "approve", "pause", "resume", "set-role", "role-catalog"):
        p = sub.add_parser(command)
        p.add_argument("--json", action="store_true")
        if command == "init":
            p.add_argument("--work-item")
            p.add_argument("--plan")
            p.add_argument("--scope", type=Path)
            p.add_argument("--stage", default="1")
            p.add_argument(
                "--stages", help="Comma-separated ordered stages; optional stage_contracts in scope JSON"
            )
            p.add_argument("--quorum", action="store_true")
            p.add_argument(
                "--adopt-historical",
                nargs="?",
                const="erp-arabic-bilingual-data",
                help="Adopt historical stages for work-item (default: erp-arabic-bilingual-data)",
            )
            p.add_argument("--descriptor", type=Path, help="ERP target descriptor JSON")
        elif command == "run":
            p.add_argument("--record-owner-commit", action="store_true")
            p.add_argument("--advance-stage", action="store_true")
            p.add_argument("--backup-to", type=Path)
            p.add_argument(
                "--once",
                action="store_true",
                help="Return after one collection pass, leaving native workers alive",
            )
        elif command == "approve":
            p.add_argument("--token-file", type=Path, required=True)
        elif command == "pause":
            p.add_argument("--reason", required=True)
        elif command == "resume":
            p.add_argument("--reason", required=True)
            p.add_argument("--reset-escalation-budget", action="store_true")
            p.add_argument("--abandon-job", action="append", default=[])
            p.add_argument("--reconciliation-evidence", type=Path)
            p.add_argument("--refresh-candidate", action="store_true")
            p.add_argument("--scope-file", type=Path)
            p.add_argument("--ack-restored-backup", action="store_true")
        elif command == "set-role":
            p.add_argument(
                "--role",
                required=True,
                choices=["architect", "builder", "reviewer", "verifier", "proposer", "ai-a1", "ai-a2", "ai-a3"],
            )
            p.add_argument("--tool", required=True, choices=["codex", "opencode"])
            p.add_argument("--model", required=True)
            p.add_argument("--effort", choices=["high", "medium", "low"])
            p.add_argument("--reason", default="Owner role reconfiguration")
        elif command == "role-catalog":
            pass
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        with execution_lock(root / "orchestrator/var/execution.lock", timeout=10):
            if args.command == "doctor":
                result = doctor(root)
            else:
                e = Engine(root)
                try:
                    if args.command == "init":
                        if args.adopt_historical:
                            work_item = args.work_item or args.adopt_historical
                            descriptor = json.loads(args.descriptor.read_text()) if args.descriptor else None
                            result = e.adopt_historical(work_item, descriptor)
                        else:
                            if not args.work_item or not args.plan or not args.scope:
                                raise WorkflowError("Standard init requires --work-item, --plan and --scope")
                            plan = within(root, args.plan)
                            scope = json.loads(args.scope.read_text())
                            required = {"allowed_paths", "requirements", "validation_commands"}
                            if not required <= set(scope) or not all(
                                isinstance(v, list) for k, v in scope.items() if k in required
                            ):
                                raise WorkflowError(
                                    "Scope needs allowed_paths, requirements and validation_commands lists"
                                )
                            stages = args.stages.split(",") if args.stages else [args.stage]
                            stage_scopes = scope.pop("stage_contracts", {})
                            scope = stage_scopes.get(stages[0], scope)
                            config = dict(
                                root=str(root),
                                work_item=args.work_item,
                                stages=stages,
                                stage_scopes=stage_scopes,
                                branch=git(root, "branch", "--show-current").decode().strip(),
                                base_commit=git(root, "rev-parse", "HEAD").decode().strip(),
                                scope=scope,
                                plan_path=args.plan,
                                plan_revision_hash=bytes_hash(plan.read_bytes()),
                                roles=json.loads((root / "orchestrator/roles.json").read_text()),
                                quorum=["ai-a1", "ai-a2", "ai-a3"] if args.quorum else [],
                            )
                            result = e.initialize(config)
                    elif args.command == "status":
                        result = e.view()
                    elif args.command == "run":
                        if args.backup_to:
                            e.store.backup(args.backup_to)
                            result = {"ok": True, "backup": str(args.backup_to.resolve())}
                        elif not doctor(root)["ok"]:
                            raise WorkflowError("Doctor failed; native dispatch refused")
                        else:
                            result = (
                                e.advance_stage()
                                if args.advance_stage
                                else (e.record_owner_commit() if args.record_owner_commit else e.run())
                            )
                    elif args.command == "approve":
                        if not doctor(root)["ok"]:
                            raise WorkflowError("Doctor failed; approval resumption refused")
                        # Only explicitly provided owner input is accepted, never an outbox token.
                        result = e.approve(json.loads(args.token_file.read_text()))
                    elif args.command == "set-role":
                        result = e.reconfigure_role(
                            role=args.role,
                            tool=args.tool,
                            model=args.model,
                            effort=args.effort,
                            reason=args.reason,
                        )
                    elif args.command == "role-catalog":
                        result = e.role_catalog()
                    else:
                        payload = {
                            "reason": ("OWNER:" + args.reason) if args.command == "pause" else args.reason
                        }
                        if args.command == "resume":
                            if args.ack_restored_backup:
                                if not args.reconciliation_evidence:
                                    raise WorkflowError("Owner recovery evidence required")
                                result = e.recover_backup(
                                    args.reconciliation_evidence, args.reset_escalation_budget
                                )
                                print(json.dumps(result, ensure_ascii=False, indent=2))
                                return 0
                            if args.abandon_job and not args.reconciliation_evidence:
                                raise WorkflowError("Explicit owner reconciliation evidence is required")
                            for job in args.abandon_job:
                                e.reconcile_job(job, args.reconciliation_evidence)
                            if args.refresh_candidate:
                                e.refresh_candidate(args.reason)
                            if args.scope_file:
                                e.revise_scope(json.loads(args.scope_file.read_text()), args.reason)
                            payload["reset_budget"] = args.reset_escalation_budget
                        result = e.owner_decision(args.command, payload)
                finally:
                    e.close()
        # Do not retain the writer lock while waiting for native work. Owner pause
        # and status commands must be able to enter between collection passes.
        while (
            args.command in ("run", "approve", "resume")
            and not getattr(args, "once", False)
            and result.get("active_jobs")
            and result.get("status") != "PAUSED"
        ):
            time.sleep(0.5)
            with execution_lock(root / "orchestrator/var/execution.lock", timeout=10):
                e = Engine(root)
                try:
                    result = e.run()
                finally:
                    e.close()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok", True) else 1
    except (WorkflowError, OSError, ValueError) as exc:
        print(
            json.dumps(
                {"ok": False, "error": str(exc) if isinstance(exc, WorkflowError) else type(exc).__name__}
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
