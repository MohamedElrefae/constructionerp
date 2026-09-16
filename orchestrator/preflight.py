"""Extracted preflight checks with action-specific sets."""

import importlib.metadata
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from candidates import git
from core import bytes_hash, canonical
from packaging.requirements import Requirement
from sandbox import probe


class CheckResult:
    def __init__(self, name: str, ok: bool, message: str = ""):
        self.name = name
        self.ok = ok
        self.message = message

    def __bool__(self):
        return bool(self.ok)

    def to_dict(self):
        return {"name": self.name, "ok": self.ok, "message": self.message}

    def __repr__(self):
        return f"CheckResult({self.name!r}, ok={self.ok!r}, message={self.message!r})"


def _resolve_db_path(runtime_path: Path | str) -> Path | None:
    p = Path(runtime_path).resolve()
    if p.is_file() and p.name.endswith(".db"):
        return p if p.exists() else None
    if (p / "checkpoints.db").exists():
        return p / "checkpoints.db"
    if (p / "orchestrator/var/checkpoints.db").exists():
        return p / "orchestrator/var/checkpoints.db"
    return None


def check_sqlite_integrity(runtime_path: Path | str) -> CheckResult:
    db_path = _resolve_db_path(runtime_path)
    if not db_path:
        return CheckResult("sqlite_integrity", True, "No database present")
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            ok = bool(row and row[0] == "ok")
            return CheckResult("sqlite_integrity", ok, "" if ok else str(row))
        finally:
            conn.close()
    except Exception as exc:
        return CheckResult("sqlite_integrity", False, str(exc))


def check_recovery_cleared(runtime_path: Path | str) -> CheckResult:
    db_path = _resolve_db_path(runtime_path)
    if not db_path:
        return CheckResult("recovery_cleared", True, "No database present")
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT value FROM workflow_meta WHERE key='recovery_required'").fetchone()
            if not row:
                return CheckResult("recovery_cleared", True)
            val = json.loads(row[0])
            ok = not bool(val)
            return CheckResult("recovery_cleared", ok, "Recovery required" if not ok else "")
        finally:
            conn.close()
    except Exception as exc:
        return CheckResult("recovery_cleared", False, str(exc))


def check_configured_root(config: dict | None, worktree: Path | str) -> CheckResult:
    worktree = Path(worktree).resolve()
    if config and "root" in config:
        cfg_root = Path(config["root"]).resolve()
        ok = cfg_root == worktree
        return CheckResult("configured_root", ok, f"Configured root {cfg_root} != {worktree}" if not ok else "")
    ok = worktree != Path("/home/mohamed/frappe-bench/apps/construction").resolve()
    return CheckResult("configured_root", ok, "Worktree cannot be apps/construction" if not ok else "")


def check_roles_mirror_synced(config: dict | None, worktree: Path | str) -> CheckResult:
    worktree = Path(worktree).resolve()
    roles_file = worktree / "orchestrator/roles.json"
    if not roles_file.exists():
        return CheckResult("roles_mirror_synced", False, "roles.json does not exist")
    if config and config.get("roles"):
        try:
            mirror_content = canonical(json.loads(roles_file.read_text()))
            config_content = canonical(config["roles"])
            ok = mirror_content == config_content
            return CheckResult("roles_mirror_synced", ok, "roles.json differs from config" if not ok else "")
        except Exception as exc:
            return CheckResult("roles_mirror_synced", False, str(exc))
    return CheckResult("roles_mirror_synced", True)


def check_binary(role: str, pin: dict | None) -> CheckResult:
    if not pin or "binary" not in pin:
        return CheckResult(f"binary:{role}", False, f"No binary pin configured for {role}")
    bin_path = Path(pin["binary"])
    if not bin_path.exists():
        return CheckResult(f"binary:{role}", False, f"Binary not found: {bin_path}")
    try:
        r = subprocess.run([str(bin_path), "--version"], capture_output=True, text=True, timeout=20)
        ok = (
            r.returncode == 0
            and pin.get("version", "") in r.stdout
            and bytes_hash(bin_path.read_bytes()) == pin.get("binary_sha256", "")
        )
        return CheckResult(f"binary:{role}", ok, "Version or hash mismatch" if not ok else "")
    except Exception as exc:
        return CheckResult(f"binary:{role}", False, str(exc))


def check_branch(config: dict | None, worktree: Path | str, expected_branch: str | None = None) -> CheckResult:
    worktree = Path(worktree).resolve()
    try:
        current = git(worktree, "branch", "--show-current").decode().strip()
    except Exception as exc:
        return CheckResult("branch", False, f"Failed to get branch: {exc}")
    expected = expected_branch or (config.get("branch") if config else None) or "feature/scope-context-portability"
    ok = current == expected
    return CheckResult("branch", ok, f"Current branch {current!r} != expected {expected!r}" if not ok else "")


def check_dependencies(worktree: Path | str) -> list[CheckResult]:
    results = [
        CheckResult("python", sys.version_info >= (3, 11), f"Python version {sys.version}")
    ]
    for name in ("langgraph", "langgraph-checkpoint-sqlite", "pydantic", "jsonschema"):
        try:
            ok = bool(importlib.metadata.version(name))
            results.append(CheckResult(f"dependency:{name}", ok))
        except importlib.metadata.PackageNotFoundError:
            results.append(CheckResult(f"dependency:{name}", False, f"Package {name} not found"))

    req_file = Path(worktree).resolve() / "orchestrator/requirements.txt"
    if req_file.exists():
        for line in req_file.read_text().splitlines():
            if line and not line.startswith((" ", "#", "-")) and "==" in line:
                req = Requirement(line.rstrip(" \\"))
                if req.marker and not req.marker.evaluate():
                    continue
                try:
                    installed = importlib.metadata.version(req.name)
                    ok = installed in req.specifier
                    results.append(CheckResult(f"locked:{req.name}", ok))
                except importlib.metadata.PackageNotFoundError:
                    results.append(CheckResult(f"locked:{req.name}", False, f"{req.name} not installed"))
    return results


def check_sandbox_probe(worktree: Path | str | None = None) -> CheckResult:
    try:
        ok = bool(probe())
        return CheckResult("sandbox_control_store_and_git_denial", ok)
    except Exception as exc:
        return CheckResult("sandbox_control_store_and_git_denial", False, str(exc))


def check_approved_capabilities(config: dict | None, runtime_path: Path | str | None = None, worktree: Path | str | None = None) -> CheckResult:
    root = Path(worktree).resolve() if worktree else (Path(config["root"]).resolve() if config and "root" in config else Path(".").resolve())
    evidence = root / "docs/ai/work-items/scope-context-portability/evidence/phase-0-capabilities.json"
    if config and "work_item" in config:
        item_evidence = root / f"docs/ai/work-items/{config['work_item']}/evidence/phase-0-capabilities.json"
        if item_evidence.exists():
            evidence = item_evidence
    if not evidence.exists():
        fallback = (
            Path(__file__).resolve().parents[1]
            / "docs/ai/work-items/scope-context-portability/evidence/phase-0-capabilities.json"
        )
        if fallback.exists():
            evidence = fallback
        else:
            return CheckResult("phase0_approved_capabilities", False, f"Missing evidence: {evidence}")
    try:
        data = json.loads(evidence.read_text())
        ok = data.get("phase_exit") == "PASSED_WITH_OWNER_DIRECTIVE"
        return CheckResult("phase0_approved_capabilities", ok, f"Phase exit: {data.get('phase_exit')}")
    except Exception as exc:
        return CheckResult("phase0_approved_capabilities", False, str(exc))


def run_display_checks(runtime_path: Path | str) -> list[CheckResult]:
    """Lightweight checks for read-only display subprocess: sqlite_integrity only."""
    return [check_sqlite_integrity(runtime_path)]


def run_owner_action_checks(runtime_path: Path | str, worktree: Path | str, config: dict | None = None) -> list[CheckResult]:
    """Checks for owner actions (pause, resume, reset_budget, reconfigure_role).
    Includes sqlite_integrity, recovery_cleared, configured_root.
    Skips binary checks so broken binaries don't block repair."""
    return [
        check_sqlite_integrity(runtime_path),
        check_recovery_cleared(runtime_path),
        check_configured_root(config, worktree),
    ]


def run_init_checks(worktree: Path | str, expected_branch: str | None = None) -> list[CheckResult]:
    """Checks before engine.initialize(). Includes: configured_root, branch, dependencies."""
    results = [
        check_configured_root(None, worktree),
        check_branch(None, worktree, expected_branch=expected_branch),
    ]
    results.extend(check_dependencies(worktree))
    return results


def run_dispatch_preflight(config: dict | None, runtime_path: Path | str, worktree: Path | str) -> list[CheckResult]:
    """Full check set before dispatching an agent or approving a plan.
    Includes: sqlite_integrity, recovery_cleared, configured_root, roles_mirror_synced,
    branch, dependencies, sandbox_probe, approved_capabilities, and binary per active role."""
    worktree = Path(worktree).resolve()
    results = [
        check_sqlite_integrity(runtime_path),
        check_recovery_cleared(runtime_path),
        check_configured_root(config, worktree),
        check_roles_mirror_synced(config, worktree),
        check_branch(config, worktree),
        check_sandbox_probe(worktree),
        check_approved_capabilities(config, runtime_path, worktree),
    ]
    results.extend(check_dependencies(worktree))

    # Binary checks for active roles
    pins = (config.get("roles") if config else None)
    if not pins:
        roles_file = worktree / "orchestrator/roles.json"
        if roles_file.exists():
            try:
                pins = json.loads(roles_file.read_text())
            except Exception:
                pins = {}
        else:
            pins = {}

    active_tools = {
        p.get("tool")
        for p in pins.values()
        if isinstance(p, dict) and p.get("tool") in {"codex", "opencode"}
    }
    for tool in sorted(active_tools):
        pin = next((p for p in pins.values() if isinstance(p, dict) and p.get("tool") == tool), None)
        results.append(check_binary(tool, pin))

    return results
