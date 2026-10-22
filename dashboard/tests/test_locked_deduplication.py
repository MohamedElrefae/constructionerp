"""Tests verifying locked deduplication, conflict handling, and audit preservation."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from dashboard.config import ORCHESTRATOR_PYTHON, REPO_ROOT
from dashboard.registry import TaskRegistry
from dashboard.tests.conftest import create_isolated_worktree


def test_duplicate_approval_token_deduplication(tmp_path):
    """Submits duplicate approval token; asserts deduplicate_action returns synchronized view."""
    script = """
import sys, json, shutil
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))
sys.path.insert(0, str(Path("orchestrator/tests").resolve()))

from candidates import git
from core import bytes_hash, digest, utc
from engine import Engine
from test_week0_prerequisites import ProposalStub, _sample_proposal
from dashboard_api import deduplicate_action

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
    "architect": {"verdict": "PASS", "wire": {"plan_text": plan_with_proposal, "explanation": "OK"}},
    "reviewer": {"verdict": "PASS", "wire": {"explanation": "Reviewed plan"}},
})

engine = Engine(repo, launcher=stub)
engine.initialize(config)
v = engine.run()

token = dict(
    token_id="tok-dedup-test-1",
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

# First call: execute grant
engine.grant_and_synchronize(token)

# Second call: deduplicate_action under lock
dedup = deduplicate_action(
    action_id=None,
    request_hash="",
    token_id=token["token_id"],
    submitted_token=token,
    store=engine.store,
    engine=engine,
)
assert dedup is not None
assert dedup["status"] == "already_complete"
assert engine.view()["plan_granted"] is True
print("DEDUP_SUCCESS")
"""
    cmd = [str(ORCHESTRATOR_PYTHON), "-c", script, str(tmp_path / "repo_dedup")]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Stderr: {res.stderr}\nStdout: {res.stdout}"
    assert "DEDUP_SUCCESS" in res.stdout


def test_same_key_different_payload_conflict(tmp_path):
    """Submitting same token_id with modified payload raises DuplicateKeyConflict."""
    script = """
import sys, json, shutil
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))
sys.path.insert(0, str(Path("orchestrator/tests").resolve()))

from candidates import git
from core import bytes_hash, digest, utc
from engine import Engine
from test_week0_prerequisites import ProposalStub, _sample_proposal
from dashboard_api import deduplicate_action, DuplicateKeyConflict

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
    "architect": {"verdict": "PASS", "wire": {"plan_text": plan_with_proposal, "explanation": "OK"}},
    "reviewer": {"verdict": "PASS", "wire": {"explanation": "Reviewed plan"}},
})

engine = Engine(repo, launcher=stub)
engine.initialize(config)
v = engine.run()

token = dict(
    token_id="tok-conflict-test-1",
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

engine.grant_and_synchronize(token)

# Submit tampered token with same token_id
tampered_token = dict(token, scope_hash="f" * 64)

try:
    deduplicate_action(
        action_id=None,
        request_hash="",
        token_id=token["token_id"],
        submitted_token=tampered_token,
        store=engine.store,
        engine=engine,
    )
    print("UNEXPECTED_SUCCESS")
except DuplicateKeyConflict as exc:
    assert "token_id reused with changed approval bindings" in str(exc)
    print("CONFLICT_DETECTED")
"""
    cmd = [str(ORCHESTRATOR_PYTHON), "-c", script, str(tmp_path / "repo_conflict")]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Stderr: {res.stderr}\nStdout: {res.stdout}"
    assert "CONFLICT_DETECTED" in res.stdout


def test_action_log_and_review_records_persist_after_task_unregistration(tmp_path):
    """Asserts action_log and review_records persist when a task is unregistered (audit preservation)."""
    db_path = tmp_path / "registry.db"
    registry = TaskRegistry(db_path=db_path)

    # 1. Register a task
    mock_wt = tmp_path / "task_wt"
    mock_wt.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(mock_wt)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(mock_wt), "config", "user.email", "t@e.com"], check=True)
    subprocess.run(["git", "-C", str(mock_wt), "config", "user.name", "Test"], check=True)
    (mock_wt / "README.md").write_text("test")
    subprocess.run(["git", "-C", str(mock_wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(mock_wt), "commit", "-m", "init"], check=True)

    # Setup orchestrator/var/checkpoints.db
    var_dir = mock_wt / "orchestrator" / "var"
    var_dir.mkdir(parents=True, exist_ok=True)
    ckpt_db = var_dir / "checkpoints.db"
    conn = sqlite3.connect(str(ckpt_db))
    with conn:
        conn.execute("CREATE TABLE workflow_meta (key TEXT PRIMARY KEY, value TEXT);")
        conn.execute("INSERT INTO workflow_meta VALUES ('work_item', 'test-item');")
        conn.execute("INSERT INTO workflow_meta VALUES ('task_branch', 'main');")
    conn.close()

    if tmp_path not in registry.allowed_roots:
        registry.allowed_roots.append(tmp_path)
    registered = registry.register_existing_worktree(mock_wt)
    task_id = registered["task_id"]

    # 2. Insert action_log record
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO action_log (
                action_id, task_id, action_type, state, idempotency_key,
                request_hash, manifest_json, executor_instance_id,
                executor_pid, executor_start_time, fencing_token,
                created_utc, updated_utc
            ) VALUES (
                'act-audit-1', ?, 'approve_plan', 'COMPLETE', 'idemp-1',
                'req-1', '{}', 'inst-1',
                1000, 100000, 1,
                '2026-09-17T00:00:00Z', '2026-09-17T00:00:00Z'
            )
        """,
            (task_id,),
        )
    conn.close()

    # 3. Insert review_record
    review = registry.create_review_record(
        task_id=task_id,
        gate_id="gate-123",
        plan_revision_hash="p" * 64,
        scope_hash="s" * 64,
        roles_hash="r" * 64,
        content_fingerprint="f" * 64,
        reviewed_by="engineer",
    )

    # 4. Unregister the task
    unregistered = registry.unregister_task(task_id)
    assert unregistered is True

    # 5. Assert action_log and review_records still persist
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    action_row = cur.execute(
        "SELECT action_id, state FROM action_log WHERE task_id = ?", (task_id,)
    ).fetchone()
    review_row = cur.execute(
        "SELECT review_id, reviewed_by FROM review_records WHERE task_id = ?", (task_id,)
    ).fetchone()
    conn.close()

    assert action_row is not None
    assert action_row[0] == "act-audit-1"
    assert action_row[1] == "COMPLETE"

    assert review_row is not None
    assert review_row[0] == review["review_id"]
    assert review_row[1] == "engineer"


def test_server_side_review_derivation_and_mismatch_rejection(monkeypatch, tmp_path):
    """Asserts that create_review_endpoint derives review hashes and fingerprint server-side and rejects client mismatch with 409."""
    import hashlib

    from starlette.testclient import TestClient

    from dashboard.app import app, task_registry
    from dashboard.auth import auth_store, session_manager

    # 1. Setup mock registered task
    wt = tmp_path / "rev_task"
    wt.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(wt)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.email", "t@e.com"], check=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.name", "Test"], check=True)
    (wt / "README.md").write_text("test")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-m", "init"], check=True)

    var_dir = wt / "orchestrator" / "var"
    var_dir.mkdir(parents=True, exist_ok=True)
    ckpt_db = var_dir / "checkpoints.db"
    conn = sqlite3.connect(str(ckpt_db))
    with conn:
        conn.execute("CREATE TABLE workflow_meta (key TEXT PRIMARY KEY, value TEXT);")
        conn.execute("INSERT INTO workflow_meta VALUES ('work_item', 'test-item');")
        conn.execute("INSERT INTO workflow_meta VALUES ('task_branch', 'main');")
    conn.close()

    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    registered = task_registry.register_existing_worktree(wt)
    task_id = registered["task_id"]

    # 2. Mock get_review_context and get_plan_projection
    async def mock_get_review_context(path):
        return {
            "gate": {"gate_id": "gate-auth-1", "scope": "PLAN"},
            "plan_revision_hash": "hash-plan-111",
            "scope_hash": "hash-scope-222",
            "roles_hash": "hash-roles-333",
        }

    async def mock_get_plan_projection(path):
        return {"plan_text": "Authoritative Plan Text"}

    monkeypatch.setattr("dashboard.app.get_review_context", mock_get_review_context)
    monkeypatch.setattr("dashboard.app.get_plan_projection", mock_get_plan_projection)

    # 3. Setup auth
    data = auth_store._load_data()
    if "users" not in data:
        data["users"] = {}
    data["users"]["engineer"] = {
        "password_hash": "scrypt$16384$8$1$00$00",
        "is_initial": False,
    }
    auth_store._save_data(data)

    client = TestClient(app)
    session_token = session_manager.create_session("engineer")
    csrf_token = "valid_csrf_token"
    client.cookies.set("dashboard_session", session_token)
    client.cookies.set("dashboard_csrf", csrf_token)

    headers = {
        "Host": "127.0.0.1:8080",
        "Origin": "http://127.0.0.1:8080",
        "X-CSRF-Token": csrf_token,
    }

    # 4. Client submits mismatched content_fingerprint -> 409 Conflict
    bad_resp = client.post(
        f"/api/tasks/{task_id}/create-review",
        headers=headers,
        json={"content_fingerprint": "bad-client-fingerprint"},
    )
    assert bad_resp.status_code == 409
    assert "content_fingerprint mismatch" in bad_resp.json()["detail"]

    # 5. Client submits mismatched gate_id -> 409 Conflict
    bad_gate_resp = client.post(
        f"/api/tasks/{task_id}/create-review",
        headers=headers,
        json={"gate_id": "gate-wrong"},
    )
    assert bad_gate_resp.status_code == 409
    assert "gate_id mismatch" in bad_gate_resp.json()["detail"]

    # 6. Authoritative expected fingerprint
    expected_fp = hashlib.sha256(b"Authoritative Plan Texthash-scope-222hash-roles-333").hexdigest()

    # 7. Empty client body -> Server automatically derives and stores snapshot -> 200 OK
    good_resp = client.post(
        f"/api/tasks/{task_id}/create-review",
        headers=headers,
        json={},
    )
    assert good_resp.status_code == 200
    rev = good_resp.json()["review"]
    assert rev["gate_id"] == "gate-auth-1"
    assert rev["plan_revision_hash"] == "hash-plan-111"
    assert rev["scope_hash"] == "hash-scope-222"
    assert rev["roles_hash"] == "hash-roles-333"
    assert rev["content_fingerprint"] == expected_fp
    assert rev["reviewed_by"] == "engineer"
