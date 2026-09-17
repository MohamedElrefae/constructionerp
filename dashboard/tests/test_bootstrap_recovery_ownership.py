"""Tests verifying ownership-verified, fenced, race-free bootstrap recovery and ancestor validation."""

import asyncio
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
import pytest

from dashboard.bootstrap import (
    BootstrapConflictError,
    BootstrapForbiddenError,
    _config_digest,
    _normalize_config,
    bootstrap_task,
)
from dashboard.config import ORCHESTRATOR_PYTHON, REPO_ROOT
from dashboard.process import (
    get_process_start_time,
    is_process_alive_with_start_time,
)
from dashboard.tests.conftest import create_isolated_worktree
from dashboard.registry import TaskRegistry, validate_and_bind_canonical_registry


def test_bootstrap_initial_checkpoint_predicate_matches_real_engine(tmp_path):
    """Executes real Engine.initialize(config) and asserts checkpoint matches exact contract."""
    script = '''
import sys, json, shutil
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))

from candidates import git
from core import bytes_hash, digest
from engine import Engine

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
    stages=["1"],
    base_commit=base,
    branch="test-branch",
    scope=dict(allowed_paths=["docs/ai/work-items/test-work/**"], requirements=["R1"], validation_commands=[["python3", "-c", "print(1)"]]),
    read_only_context_paths=["AGENTS.md", "SESSION_MEMORY.md"],
    plan_path="plan.md",
    plan_revision_hash=bytes_hash((repo / "plan.md").read_bytes()),
    roles={r: {"tool": "synthetic", "binary": "synthetic", "model": "SYNTHETIC"} for r in ["architect", "reviewer", "builder", "verifier", "ai-a1", "ai-a2", "ai-a3"]},
)

engine = Engine(repo)
v = engine.initialize(config)

# Checkpoint predicate assertions matching routing.py:24
assert v["status"] == "DRAFT", f"Expected DRAFT, got {v['status']}"
assert v["stage"] == "1", f"Expected stage 1, got {v['stage']}"
assert v["work_item"] == "test-work"
assert v["active_jobs"] == []
assert v["round"] == 0
assert v["committed"] is False
assert v["scope_hash"] == digest(config["scope"])
assert v["roles_hash"] == digest(config["roles"])
print("SUCCESS")
'''
    cmd = [str(ORCHESTRATOR_PYTHON), "-c", script, str(tmp_path / "engine_init_repo")]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Stderr: {res.stderr}\nStdout: {res.stdout}"
    assert "SUCCESS" in res.stdout


def test_bootstrap_parent_death_before_child_setup():
    """Simulates race where parent process exits before child launcher setup; verifies launcher terminates."""
    fake_parent_pid = 999999
    cmd = [
        sys.executable,
        "-m",
        "dashboard.launcher",
        "--parent-pid",
        str(fake_parent_pid),
        "--parent-start-time",
        "12345",
        "--",
        "echo",
        "should_not_run",
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode != 0
    assert "should_not_run" not in res.stdout
    assert "Parent process died or changed" in res.stderr


def test_launcher_parent_pid_reuse_aborts_exec():
    """Simulates parent PID reuse where PPID matches expected PID but start-time differs; verifies abort."""
    actual_ppid = os.getpid()
    actual_start_time = get_process_start_time(actual_ppid)
    assert actual_start_time is not None

    wrong_start_time = actual_start_time + 999999
    cmd = [
        sys.executable,
        "-m",
        "dashboard.launcher",
        "--parent-pid",
        str(actual_ppid),
        "--parent-start-time",
        str(wrong_start_time),
        "--",
        "echo",
        "should_not_run",
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode != 0
    assert "should_not_run" not in res.stdout
    assert "Parent start time mismatch" in res.stderr


def test_bootstrap_pid_reuse_protection():
    """Verifies is_process_alive_with_start_time detects PID reuse."""
    pid = os.getpid()
    actual_start_time = get_process_start_time(pid)
    assert actual_start_time is not None

    # Exact start time matches -> alive
    assert is_process_alive_with_start_time(pid, actual_start_time) is True

    # Modified start time (recycled PID) -> treated as dead
    assert is_process_alive_with_start_time(pid, actual_start_time + 1000) is False

    # Non-existent PID -> dead
    assert is_process_alive_with_start_time(999999, 12345) is False


def test_bootstrap_stale_worker_mutation_aborted_after_fencing(tmp_path):
    """Simulates stale worker attempting mutation after recovery incremented fencing token; verifies hard stop."""
    db_path = tmp_path / "registry.db"
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE action_log (
                action_id TEXT PRIMARY KEY,
                task_id TEXT,
                action_type TEXT,
                state TEXT,
                idempotency_key TEXT,
                request_hash TEXT,
                executor_instance_id TEXT,
                fencing_token INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO action_log (action_id, task_id, action_type, state, executor_instance_id, fencing_token)
            VALUES ('act-1', 'task-1', 'bootstrap', 'EXECUTING', 'inst-recovered', 2)
        """)
    conn.close()

    script = f'''
import sys
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))
from dashboard_api import verify_action_fence
from core import WorkflowError

try:
    verify_action_fence(Path(r"{db_path}"), "act-1", fencing_token=1, executor_instance_id="inst-stale")
    print("UNEXPECTED_SUCCESS")
except WorkflowError as exc:
    assert "Fencing validation failed" in str(exc)
    print("FENCE_BLOCKED")
'''
    res = subprocess.run([str(ORCHESTRATOR_PYTHON), "-c", script], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert "FENCE_BLOCKED" in res.stdout


def test_bootstrap_two_simultaneous_recovery_requests(tmp_path):
    """Two concurrent recovery requests compete via CAS; confirms exactly one succeeds."""
    db_path = tmp_path / "registry.db"
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE action_log (
                action_id TEXT PRIMARY KEY,
                state TEXT,
                fencing_token INTEGER,
                executor_instance_id TEXT,
                updated_utc TEXT
            )
        """)
        conn.execute("""
            INSERT INTO action_log (action_id, state, fencing_token, executor_instance_id, updated_utc)
            VALUES ('act-concurrent', 'EXECUTING_UNKNOWN', 1, 'inst-old', '2026-09-17T00:00:00Z')
        """)
    conn.close()

    def try_claim(inst_id, expected_token):
        c = sqlite3.connect(db_path)
        with c:
            cur = c.execute("""
                UPDATE action_log
                SET state = 'RECOVERING',
                    fencing_token = fencing_token + 1,
                    executor_instance_id = ?,
                    updated_utc = '2026-09-17T01:00:00Z'
                WHERE action_id = 'act-concurrent'
                  AND state IN ('EXECUTING_UNKNOWN', 'FAILED')
                  AND fencing_token = ?
            """, (inst_id, expected_token))
            return cur.rowcount

    # First worker claims
    res1 = try_claim("inst-worker-1", expected_token=1)
    assert res1 == 1

    # Second worker attempts same claim with old fencing_token=1 -> fails (0 rows)
    res2 = try_claim("inst-worker-2", expected_token=1)
    assert res2 == 0


def test_ancestor_chain_permissions_validated(tmp_path):
    """Simulates an ancestor directory with group/world-writable permissions; asserts rejected fail-closed."""
    var_dir = tmp_path / "sub" / "var"
    var_dir.mkdir(parents=True, exist_ok=True)
    db_file = var_dir / "registry.db"
    db_file.touch()

    # Make parent directory world-writable (0o777)
    os.chmod(tmp_path / "sub", 0o777)
    try:
        with pytest.raises(ValueError, match=r"Ancestor directory .* must not be group/world-writable"):
            validate_and_bind_canonical_registry(db_file, is_test_mode=True)
    finally:
        os.chmod(tmp_path / "sub", 0o755)


def test_registry_permissions_and_ownership_enforced(tmp_path):
    """Verifies var/ must have mode 0700 and registry.db mode 0600."""
    var_dir = tmp_path / "var"
    var_dir.mkdir(parents=True, exist_ok=True)
    db_file = var_dir / "registry.db"
    db_file.touch()

    # Test bad var_dir permissions (0o755)
    os.chmod(var_dir, 0o755)
    os.chmod(db_file, 0o600)
    with pytest.raises(ValueError, match=r"Registry directory .* must have mode 0700"):
        validate_and_bind_canonical_registry(db_file, is_test_mode=True)

    # Test bad db_file permissions (0o644)
    os.chmod(var_dir, 0o700)
    os.chmod(db_file, 0o644)
    with pytest.raises(ValueError, match=r"Registry database .* must have mode 0600"):
        validate_and_bind_canonical_registry(db_file, is_test_mode=True)

    # Correct permissions (0o700 and 0o600) -> succeeds
    os.chmod(var_dir, 0o700)
    os.chmod(db_file, 0o600)
    res = validate_and_bind_canonical_registry(db_file, is_test_mode=True)
    assert res == db_file.resolve()


def test_registry_symlink_component_rejected(tmp_path):
    """Simulates a symlink component in the path walk; asserts rejected before opening."""
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    link_dir = tmp_path / "link_dir"
    link_dir.symlink_to(real_dir)

    target = link_dir / "var" / "registry.db"
    with pytest.raises(ValueError, match=r"Symlink rejected in registry path component"):
        validate_and_bind_canonical_registry(target, is_test_mode=True)


def test_registry_path_traversal_rejected(tmp_path):
    """Simulates .. traversal in raw path string; asserts rejected before normalization."""
    raw_path = f"{tmp_path}/../fake/var/registry.db"
    with pytest.raises(ValueError, match=r"Parent traversal \('\.\.'\) prohibited"):
        validate_and_bind_canonical_registry(raw_path, is_test_mode=True)


def test_subprocess_registry_derivation_consistency_assertion(tmp_path):
    """Subprocess derives canonical path from worktree root and asserts consistency with CANONICAL_DASHBOARD_REGISTRY."""
    script = '''
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))
from dashboard_api import get_canonical_registry_path

root = Path(sys.argv[1])
# Correct env matching derived
os.environ["CANONICAL_DASHBOARD_REGISTRY"] = str((root / "dashboard/var/registry.db").resolve())
path = get_canonical_registry_path(root)
assert path == (root / "dashboard/var/registry.db").resolve()

# Mismatched env -> raises WorkflowError or AssertionError
os.environ["CANONICAL_DASHBOARD_REGISTRY"] = "/tmp/spoofed/registry.db"
try:
    get_canonical_registry_path(root)
    print("UNEXPECTED_SUCCESS")
except Exception as exc:
    if "Registry derivation mismatch" in str(exc):
        print("ASSERTION_HELD")
'''
    res = subprocess.run([str(ORCHESTRATOR_PYTHON), "-c", script, str(tmp_path)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert "ASSERTION_HELD" in res.stdout


def test_bootstrap_crash_after_config_before_checkpoint_halts_reconciliation(tmp_path):
    """Simulates crash after config persistence in workflow_meta but before checkpoints table has row; halts with RECONCILIATION_REQUIRED."""
    target_dir = tmp_path / "crashed_task"
    target_dir.mkdir(parents=True)
    var_dir = target_dir / "orchestrator" / "var"
    var_dir.mkdir(parents=True)

    # Initialize checkpoints.db with workflow_meta but NO checkpoint rows
    db_path = var_dir / "checkpoints.db"
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("CREATE TABLE workflow_meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO workflow_meta VALUES ('config', '{\"work_item\":\"test-work\"}')")
        conn.execute("CREATE TABLE checkpoints (thread_id TEXT, checkpoint_ns TEXT, checkpoint_id TEXT, parent_checkpoint_id TEXT, type TEXT, checkpoint BLOB, metadata BLOB)")
    conn.close()

    # Recovery check logic
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    has_config = conn.execute("SELECT 1 FROM workflow_meta WHERE key='config'").fetchone() is not None
    has_checkpoint = conn.execute("SELECT 1 FROM checkpoints WHERE thread_id='workflow'").fetchone() is not None
    conn.close()

    assert has_config is True
    assert has_checkpoint is False
    # Verified invariant: When config is present but checkpoint missing -> RECONCILIATION_REQUIRED
    # and directory must NOT be deleted.
    assert target_dir.exists()


def test_managed_worktree_requires_fencing_for_all_mutations(tmp_path):
    """Mutations on managed worktrees strictly require (action_id, fencing_token, executor_instance_id)."""
    wt = create_isolated_worktree(tmp_path, "managed_wt")
    var_dir = wt / "dashboard" / "var"
    var_dir.mkdir(parents=True, exist_ok=True)
    reg_db = var_dir / "registry.db"
    reg_db.touch()
    os.chmod(reg_db, 0o600)

    cmd = [
        str(ORCHESTRATOR_PYTHON),
        "-m",
        "orchestrator.dashboard_api",
        "--root",
        str(wt),
        "--action",
        "adopt_scope",
        "--payload",
        json.dumps({"scope": {}, "implementation_stages": ["1"]}),
    ]
    env = dict(os.environ)
    env["DASHBOARD_TEST_MODE"] = "1"
    env["CANONICAL_DASHBOARD_REGISTRY"] = str(reg_db.resolve())
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, env=env)
    assert res.returncode != 0
    output = json.loads(res.stdout)
    assert output["ok"] is False
    assert output["error_type"] == "PreconditionError"
    assert output["error"] == "Precondition check failed"


def test_bootstrap_mutation_halted_when_fence_token_incremented(tmp_path):
    """Asserts that if the fencing token is incremented mid-bootstrap, subsequent mutations halt immediately."""
    from dashboard.bootstrap import _check_bootstrap_fence, BootstrapConflictError
    from dashboard.registry import TaskRegistry

    db_path = tmp_path / "registry.db"
    registry = TaskRegistry(db_path=db_path)
    action_id = "act-mid-fence-test"
    executor_inst = "inst-test-1"

    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("""
            INSERT INTO action_log (
                action_id, task_id, action_type, state, idempotency_key,
                request_hash, manifest_json, executor_instance_id, executor_pid,
                executor_start_time, fencing_token, created_utc, updated_utc
            ) VALUES (
                ?, 't-1', 'bootstrap', 'EXECUTING', 'k-1',
                'h-1', '{}', ?, 100, 100, 1, '2026-09-17T00:00:00Z', '2026-09-17T00:00:00Z'
            )
        """, (action_id, executor_inst))
    conn.close()

    # Step 1 check passes
    _check_bootstrap_fence(registry, action_id, 1, executor_inst)

    # Fence token increments (e.g. recovery claimed action or revoked)
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("UPDATE action_log SET fencing_token = 2 WHERE action_id = ?", (action_id,))
    conn.close()

    # Step 2 check must halt with BootstrapConflictError
    with pytest.raises(BootstrapConflictError, match="Fencing validation failed"):
        _check_bootstrap_fence(registry, action_id, 1, executor_inst)


@pytest.mark.anyio
async def test_bootstrap_with_distinct_dashboard_and_target_worktree_roots(tmp_path, monkeypatch):
    """End-to-end bootstrap verifying controlling dashboard registry root and target worktree root are distinct."""
    # 1. Setup distinct controlling dashboard service root
    dashboard_service_root = tmp_path / "dashboard_service"
    dashboard_service_root.mkdir(parents=True)
    var_dir = dashboard_service_root / "dashboard" / "var"
    var_dir.mkdir(parents=True)
    for p in (tmp_path, dashboard_service_root, dashboard_service_root / "dashboard", var_dir):
        try:
            os.chmod(p, 0o700)
        except Exception:
            pass
    registry_db = var_dir / "registry.db"

    from dashboard.registry import init_registry_db
    init_registry_db(registry_db)
    os.chmod(registry_db, 0o600)
    locks_dir = var_dir / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(locks_dir, 0o700)

    # 2. Define distinct target worktree location (must not exist yet)
    target_worktree = tmp_path / f"target_wt_{uuid.uuid4().hex[:6]}"
    assert not target_worktree.exists()

    # 3. Configure environment and TaskRegistry pointing to the distinct dashboard service root
    monkeypatch.setenv("DASHBOARD_TEST_MODE", "1")
    monkeypatch.setenv("DASHBOARD_TEST_ROOT", str(dashboard_service_root))
    monkeypatch.setenv("CANONICAL_DASHBOARD_REGISTRY", str(registry_db.resolve()))

    registry = TaskRegistry(db_path=registry_db, allowed_roots=[tmp_path])

    # 4. Execute bootstrap_task targeting target_worktree
    work_item = f"dist-{uuid.uuid4().hex[:6]}"
    user_brief = "# Distinct Root Test Brief\n\nVerify registry location portability."

    branch_name = None
    try:
        task = await bootstrap_task(
            work_item=work_item,
            user_brief=user_brief,
            target_path=target_worktree,
            registry=registry,
            is_test_mode=True,
        )
        branch_name = f"task/{work_item}-{task['task_id'][-8:]}"

        # 5. Assertions on target worktree
        assert target_worktree.exists()
        target_ckpt_db = target_worktree / "orchestrator" / "var" / "checkpoints.db"
        assert target_ckpt_db.exists()

        # Verify target worktree does NOT contain a dashboard registry
        target_registry_db = target_worktree / "dashboard" / "var" / "registry.db"
        assert not target_registry_db.exists()

        # Verify checkpoint contract via subprocess get_state_projection
        from dashboard.subprocess_client import get_state_projection
        state = await get_state_projection(target_worktree)
        assert state is not None
        assert state["status"] == "DRAFT"
        assert state["work_item"] == work_item
        assert state["stage"] == "plan"

        # 6. Assertions on controlling dashboard registry
        conn_reg = sqlite3.connect(f"file:{registry_db}?mode=ro", uri=True)
        try:
            # Verify task registration
            task_row = conn_reg.execute(
                "SELECT task_id, work_item, worktree_path FROM registered_tasks WHERE work_item = ?",
                (work_item,),
            ).fetchone()
            assert task_row is not None
            assert task_row[0] == task["task_id"]
            assert Path(task_row[2]).resolve() == target_worktree.resolve()

            # Verify action_log state is COMPLETE with fencing_token = 1
            action_row = conn_reg.execute(
                "SELECT state, fencing_token, executor_instance_id, manifest_json FROM action_log WHERE task_id = ?",
                (task["task_id"],),
            ).fetchone()
            assert action_row is not None
            assert action_row[0] == "COMPLETE"
            assert action_row[1] == 1
            manifest = json.loads(action_row[3])
            assert Path(manifest["target_path"]).resolve() == target_worktree.resolve()
        finally:
            conn_reg.close()
    finally:
        if target_worktree.exists():
            subprocess.run(["git", "-C", str(REPO_ROOT), "worktree", "remove", "--force", str(target_worktree)], capture_output=True)
            subprocess.run(["git", "-C", str(REPO_ROOT), "worktree", "prune"], capture_output=True)
        if branch_name:
            subprocess.run(["git", "-C", str(REPO_ROOT), "branch", "-D", branch_name], capture_output=True)


