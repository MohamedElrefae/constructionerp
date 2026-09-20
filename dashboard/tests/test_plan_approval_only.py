"""Tests verifying approval-only engine operation and dispatch non-invocation."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dashboard.config import ORCHESTRATOR_PYTHON, REPO_ROOT


def run_in_orchestrator(code: str, *args: str) -> subprocess.CompletedProcess:
    """Run a Python snippet inside the orchestrator venv where LangGraph is installed."""
    cmd = [str(ORCHESTRATOR_PYTHON), "-c", code, *args]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Orchestrator script failed (code {proc.returncode}):\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def test_grant_and_synchronize_records_grant_and_sets_plan_granted(tmp_path):
    """Verifies grant_and_synchronize validates token v2, records grant row and event, and updates checkpoint."""
    script = """
import sys, json, shutil
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))
sys.path.insert(0, str(Path("orchestrator/tests").resolve()))

from candidates import git
from core import bytes_hash, digest, utc
from engine import Engine
from test_week0_prerequisites import ProposalStub, _sample_proposal

repo = Path(sys.argv[1])
repo.mkdir(parents=True, exist_ok=True)
git(repo, "init", "-b", "test-branch")
git(repo, "config", "user.name", "Test User")
git(repo, "config", "user.email", "test@example.com")
(repo / "old").write_text("old")
(repo / "mode").write_text("mode")
(repo / "AGENTS.md").write_text("agents")
(repo / "SESSION_MEMORY.md").write_text("memory")
git(repo, "add", ".")
git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "init")

source = Path.cwd()
shutil.copytree(source / "docs/ai/roles", repo / "docs/ai/roles")
(repo / "plan.md").write_text("Approved bootstrap plan")
git(repo, "add", ".")
git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "fixture")
base = git(repo, "rev-parse", "HEAD").decode().strip()

config = dict(
    root=str(repo),
    work_item="test-work",
    stages=["plan"],
    base_commit=base,
    branch="test-branch",
    scope=dict(allowed_paths=["docs/ai/work-items/test-work/**"], requirements=["R1"], validation_commands=[["python3", "-c", "print(1)"]]),
    read_only_context_paths=["AGENTS.md", "SESSION_MEMORY.md"],
    plan_path="plan.md",
    plan_revision_hash=bytes_hash((repo / "plan.md").read_bytes()),
    roles={r: {"tool": "synthetic", "binary": "synthetic", "model": "SYNTHETIC"} for r in ["architect", "reviewer", "builder", "verifier", "ai-a1", "ai-a2", "ai-a3"]},
)

proposal = _sample_proposal()
plan_with_proposal = f"# Proposed Architecture\\n\\n```scope-proposal\\n{json.dumps(proposal)}\\n```\\n"

stub = ProposalStub(outcomes={
    "architect": {
        "verdict": "PASS",
        "wire": {"plan_text": plan_with_proposal, "explanation": "OK"},
    },
    "reviewer": {
        "verdict": "PASS",
        "wire": {"explanation": "Reviewed plan"},
    },
})

engine = Engine(repo, launcher=stub)
engine.initialize(config)
v = engine.run()
assert v["gate"] is not None
assert v["gate"]["scope"] == "PLAN"
assert v["plan_granted"] is False

token = dict(
    token_id="tok-plan-grant-sync-1",
    status="ISSUED",
    issuer="owner",
    issued_utc=utc(),
    scope="PLAN",
    schema_version=2,
    gate_id=v["gate"]["gate_id"],
    work_item=v["work_item"],
    plan_revision_hash=v["plan_revision_hash"],
    scope_hash=v["scope_hash"],
    roles_hash=v.get("roles_hash") or digest(engine.config.get("roles", {})),
    repository_id=str(repo),
    branch=engine.config["branch"],
    stages=["plan"],
)

new_view = engine.grant_and_synchronize(token)

row = engine.store.conn.execute("SELECT status, data FROM workflow_grants WHERE token_id=?", (token["token_id"],)).fetchone()
assert row is not None
assert row[0] == "CONSUMED"
assert json.loads(row[1])["scope"] == "PLAN"

events = [e for e in engine.store.events() if e["kind"] == "grant" and e["payload"]["token_id"] == token["token_id"]]
assert len(events) == 1

assert new_view["plan_granted"] is True
assert new_view["active_jobs"] == []
print("SUCCESS")
"""
    res = run_in_orchestrator(script, str(tmp_path / "repo1"))
    assert "SUCCESS" in res.stdout


def test_grant_and_synchronize_never_invokes_run_or_dispatch(tmp_path):
    """Spies on Engine.run, Engine._dispatch, and Engine._prepare; asserts zero calls during approval."""
    script = """
import sys, json, shutil
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path("orchestrator").resolve()))
sys.path.insert(0, str(Path("orchestrator/tests").resolve()))

from candidates import git
from core import bytes_hash, digest, utc
from engine import Engine
from test_week0_prerequisites import ProposalStub, _sample_proposal

repo = Path(sys.argv[1])
repo.mkdir(parents=True, exist_ok=True)
git(repo, "init", "-b", "test-branch")
git(repo, "config", "user.name", "Test User")
git(repo, "config", "user.email", "test@example.com")
(repo / "old").write_text("old")
(repo / "mode").write_text("mode")
(repo / "AGENTS.md").write_text("agents")
(repo / "SESSION_MEMORY.md").write_text("memory")
git(repo, "add", ".")
git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "init")

source = Path.cwd()
shutil.copytree(source / "docs/ai/roles", repo / "docs/ai/roles")
(repo / "plan.md").write_text("Approved bootstrap plan")
git(repo, "add", ".")
git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "fixture")
base = git(repo, "rev-parse", "HEAD").decode().strip()

config = dict(
    root=str(repo),
    work_item="test-work",
    stages=["plan"],
    base_commit=base,
    branch="test-branch",
    scope=dict(allowed_paths=["docs/ai/work-items/test-work/**"], requirements=["R1"], validation_commands=[["python3", "-c", "print(1)"]]),
    read_only_context_paths=["AGENTS.md", "SESSION_MEMORY.md"],
    plan_path="plan.md",
    plan_revision_hash=bytes_hash((repo / "plan.md").read_bytes()),
    roles={r: {"tool": "synthetic", "binary": "synthetic", "model": "SYNTHETIC"} for r in ["architect", "reviewer", "builder", "verifier", "ai-a1", "ai-a2", "ai-a3"]},
)

proposal = _sample_proposal()
plan_with_proposal = f"# Proposed Architecture\\n\\n```scope-proposal\\n{json.dumps(proposal)}\\n```\\n"

stub = ProposalStub(outcomes={
    "architect": {
        "verdict": "PASS",
        "wire": {"plan_text": plan_with_proposal, "explanation": "OK"},
    },
    "reviewer": {
        "verdict": "PASS",
        "wire": {"explanation": "Reviewed plan"},
    },
})

engine = Engine(repo, launcher=stub)
engine.initialize(config)
v = engine.run()
assert v["gate"] is not None

token = dict(
    token_id="tok-plan-grant-sync-2",
    status="ISSUED",
    issuer="owner",
    issued_utc=utc(),
    scope="PLAN",
    schema_version=2,
    gate_id=v["gate"]["gate_id"],
    work_item=v["work_item"],
    plan_revision_hash=v["plan_revision_hash"],
    scope_hash=v["scope_hash"],
    roles_hash=v.get("roles_hash") or digest(engine.config.get("roles", {})),
    repository_id=str(repo),
    branch=engine.config["branch"],
    stages=["plan"],
)

original_run = engine.run
original_dispatch = engine._dispatch
original_prepare = engine._prepare

run_spy = MagicMock(side_effect=original_run)
dispatch_spy = MagicMock(side_effect=original_dispatch)
prepare_spy = MagicMock(side_effect=original_prepare)

engine.run = run_spy
engine._dispatch = dispatch_spy
engine._prepare = prepare_spy

launcher_calls_before = len(stub.starts)

view = engine.grant_and_synchronize(token)

assert run_spy.call_count == 0, f"Engine.run was called {run_spy.call_count} times!"
assert dispatch_spy.call_count == 0, f"Engine._dispatch was called {dispatch_spy.call_count} times!"
assert prepare_spy.call_count == 0, f"Engine._prepare was called {prepare_spy.call_count} times!"
assert len(stub.starts) == launcher_calls_before, "Launcher was called during approval!"
assert view["active_jobs"] == [], f"active_jobs is not empty: {view['active_jobs']}"

print("SUCCESS")
"""
    res = run_in_orchestrator(script, str(tmp_path / "repo2"))
    assert "SUCCESS" in res.stdout


def test_grant_and_synchronize_leaves_active_jobs_empty(tmp_path):
    """Verifies that active_jobs is strictly [] after grant_and_synchronize."""
    script = """
import sys, json, shutil
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))
sys.path.insert(0, str(Path("orchestrator/tests").resolve()))

from candidates import git
from core import bytes_hash, digest, utc
from engine import Engine
from test_week0_prerequisites import ProposalStub, _sample_proposal

repo = Path(sys.argv[1])
repo.mkdir(parents=True, exist_ok=True)
git(repo, "init", "-b", "test-branch")
git(repo, "config", "user.name", "Test User")
git(repo, "config", "user.email", "test@example.com")
(repo / "old").write_text("old")
(repo / "mode").write_text("mode")
(repo / "AGENTS.md").write_text("agents")
(repo / "SESSION_MEMORY.md").write_text("memory")
git(repo, "add", ".")
git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "init")

source = Path.cwd()
shutil.copytree(source / "docs/ai/roles", repo / "docs/ai/roles")
(repo / "plan.md").write_text("Approved bootstrap plan")
git(repo, "add", ".")
git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "fixture")
base = git(repo, "rev-parse", "HEAD").decode().strip()

config = dict(
    root=str(repo),
    work_item="test-work",
    stages=["plan"],
    base_commit=base,
    branch="test-branch",
    scope=dict(allowed_paths=["docs/ai/work-items/test-work/**"], requirements=["R1"], validation_commands=[["python3", "-c", "print(1)"]]),
    read_only_context_paths=["AGENTS.md", "SESSION_MEMORY.md"],
    plan_path="plan.md",
    plan_revision_hash=bytes_hash((repo / "plan.md").read_bytes()),
    roles={r: {"tool": "synthetic", "binary": "synthetic", "model": "SYNTHETIC"} for r in ["architect", "reviewer", "builder", "verifier", "ai-a1", "ai-a2", "ai-a3"]},
)

proposal = _sample_proposal()
plan_with_proposal = f"# Proposed Architecture\\n\\n```scope-proposal\\n{json.dumps(proposal)}\\n```\\n"

stub = ProposalStub(outcomes={
    "architect": {
        "verdict": "PASS",
        "wire": {"plan_text": plan_with_proposal, "explanation": "OK"},
    },
    "reviewer": {
        "verdict": "PASS",
        "wire": {"explanation": "Reviewed plan"},
    },
})

engine = Engine(repo, launcher=stub)
engine.initialize(config)
v = engine.run()
assert v["gate"] is not None

token = dict(
    token_id="tok-plan-grant-sync-3",
    status="ISSUED",
    issuer="owner",
    issued_utc=utc(),
    scope="PLAN",
    schema_version=2,
    gate_id=v["gate"]["gate_id"],
    work_item=v["work_item"],
    plan_revision_hash=v["plan_revision_hash"],
    scope_hash=v["scope_hash"],
    roles_hash=v.get("roles_hash") or digest(engine.config.get("roles", {})),
    repository_id=str(repo),
    branch=engine.config["branch"],
    stages=["plan"],
)

view = engine.grant_and_synchronize(token)
assert view["active_jobs"] == []
print("SUCCESS")
"""
    res = run_in_orchestrator(script, str(tmp_path / "repo3"))
    assert "SUCCESS" in res.stdout
