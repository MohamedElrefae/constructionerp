"""Tests verifying read-only context delivery, provenance recording, and sandbox mounting."""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from dashboard.config import ORCHESTRATOR_PYTHON, REPO_ROOT
from dashboard.registry import TaskRegistry


def test_mandatory_context_missing_fails_initialization(tmp_path):
    """Omitting AGENTS.md or SESSION_MEMORY.md fails Engine.initialize() with CoreValidationError."""
    script = """
import sys, json, shutil
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))

from candidates import git
from core import bytes_hash, digest, ValidationError as CoreValidationError
from engine import Engine

repo = Path(sys.argv[1])
repo.mkdir(parents=True, exist_ok=True)
git(repo, "init", "-b", "test-branch")
git(repo, "config", "user.name", "Test User")
git(repo, "config", "user.email", "test@example.com")
(repo / "old").write_text("old")
(repo / "mode").write_text("mode")
(repo / "AGENTS.md").write_text("agents")
# Intentionally NOT creating SESSION_MEMORY.md
git(repo, "add", ".")
git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "init")

source = Path.cwd()
shutil.copytree(source / "docs/ai/roles", repo / "docs/ai/roles")
(repo / "plan.md").write_text("Approved bootstrap plan")
git(repo, "add", ".")
git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "fixture")
base = git(repo, "rev-parse", "HEAD").decode().strip()

# Missing from read_only_context_paths
config = dict(
    root=str(repo),
    work_item="test-work",
    stages=["1"],
    base_commit=base,
    branch="test-branch",
    scope=dict(allowed_paths=["docs/ai/work-items/test-work/**"], requirements=["R1"], validation_commands=[["python3", "-c", "print(1)"]]),
    read_only_context_paths=["AGENTS.md"],  # Missing SESSION_MEMORY.md
    plan_path="plan.md",
    plan_revision_hash=bytes_hash((repo / "plan.md").read_bytes()),
    roles={r: {"tool": "synthetic", "binary": "synthetic", "model": "SYNTHETIC"} for r in ["architect", "reviewer", "builder", "verifier", "ai-a1", "ai-a2", "ai-a3"]},
)

engine = Engine(repo)
try:
    engine.initialize(config)
    print("UNEXPECTED_SUCCESS")
except CoreValidationError as exc:
    assert "Mandatory read-only context path missing" in str(exc)
    print("FAILED_AS_EXPECTED")

# Now add SESSION_MEMORY.md to paths, but file not on disk
config["read_only_context_paths"] = ["AGENTS.md", "SESSION_MEMORY.md"]
try:
    engine.initialize(config)
    print("UNEXPECTED_SUCCESS_2")
except CoreValidationError as exc:
    assert "Mandatory read-only context file does not exist on disk" in str(exc)
    print("FAILED_AS_EXPECTED_2")
"""
    cmd = [str(ORCHESTRATOR_PYTHON), "-c", script, str(tmp_path / "repo_missing_ctx")]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Stderr: {res.stderr}\nStdout: {res.stdout}"
    assert "FAILED_AS_EXPECTED" in res.stdout
    assert "FAILED_AS_EXPECTED_2" in res.stdout


def test_context_paths_disjointness_enforced(tmp_path):
    """Asserts that read-only context paths intersecting with scope.allowed_paths raises CoreValidationError."""
    script = """
import sys, json, shutil
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))

from candidates import git
from core import bytes_hash, digest, ValidationError as CoreValidationError
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

# Context path intersects with allowed_paths
config = dict(
    root=str(repo),
    work_item="test-work",
    stages=["1"],
    base_commit=base,
    branch="test-branch",
    scope=dict(allowed_paths=["AGENTS.md"], requirements=["R1"], validation_commands=[["python3", "-c", "print(1)"]]),
    read_only_context_paths=["AGENTS.md", "SESSION_MEMORY.md"],
    plan_path="plan.md",
    plan_revision_hash=bytes_hash((repo / "plan.md").read_bytes()),
    roles={r: {"tool": "synthetic", "binary": "synthetic", "model": "SYNTHETIC"} for r in ["architect", "reviewer", "builder", "verifier", "ai-a1", "ai-a2", "ai-a3"]},
)

engine = Engine(repo)
try:
    engine.initialize(config)
    print("UNEXPECTED_SUCCESS")
except CoreValidationError as exc:
    assert "intersects with scope.allowed_paths" in str(exc)
    print("DISJOINTNESS_ENFORCED")
"""
    cmd = [str(ORCHESTRATOR_PYTHON), "-c", script, str(tmp_path / "repo_disjoint")]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Stderr: {res.stderr}\nStdout: {res.stdout}"
    assert "DISJOINTNESS_ENFORCED" in res.stdout


def test_optional_context_missing_recorded_in_provenance(tmp_path):
    """Missing optional context file is recorded as exists=0 in provenance table without failing."""
    registry = TaskRegistry(db_path=tmp_path / "registry.db")
    provenance_entries = [
        {
            "file_path": "AGENTS.md",
            "exists": 1,
            "is_mandatory": 1,
            "commit_sha": "sha1",
            "content_sha256": "h1",
        },
        {
            "file_path": "SESSION_MEMORY.md",
            "exists": 1,
            "is_mandatory": 1,
            "commit_sha": "sha1",
            "content_sha256": "h2",
        },
        {
            "file_path": "docs/ai/SCHEMA_FACTS.md",
            "exists": 0,
            "is_mandatory": 0,
            "commit_sha": "sha1",
            "content_sha256": None,
        },
    ]
    registry.record_context_provenance("task-123", provenance_entries)

    rows = registry.get_context_provenance("task-123")
    assert len(rows) == 3
    missing_entry = next(r for r in rows if r["path"] == "docs/ai/SCHEMA_FACTS.md")
    assert missing_entry["exists"] is False
    assert missing_entry["is_mandatory"] is False
    assert missing_entry["sha256"] is None

    mandatory_entry = next(r for r in rows if r["path"] == "AGENTS.md")
    assert mandatory_entry["exists"] is True
    assert mandatory_entry["is_mandatory"] is True
