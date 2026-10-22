"""Tests stay outside Construction's Frappe-importing package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import shutil

import pytest
from candidates import git
from core import bytes_hash


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "test")
    git(root, "config", "user.name", "Synthetic Test")
    git(root, "config", "user.email", "test@example.invalid")
    (root / "old").write_text("old")
    (root / "mode").write_text("mode")
    git(root, "add", ".")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-m", "test fixture baseline")
    return root


@pytest.fixture
def configured(repo, tmp_path):
    # Framework fixture files are committed only inside the throwaway test repository.
    source = Path(__file__).resolve().parents[2]
    shutil.copytree(source / "docs/ai/roles", repo / "docs/ai/roles")
    (repo / "plan.md").write_text("Approved bootstrap plan")
    (repo / ".gitignore").write_text("orchestrator/var/\n")
    git(repo, "add", ".")
    git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "synthetic framework fixture")
    base = git(repo, "rev-parse", "HEAD").decode().strip()
    config = dict(
        root=str(repo),
        work_item="test-work",
        stages=["1"],
        base_commit=base,
        branch="test",
        scope={
            "allowed_paths": ["old", "mode", "new"],
            "requirements": ["R1"],
            "validation_commands": [["python3", "-c", "print(1)"]],
        },
        plan_path="plan.md",
        plan_revision_hash=bytes_hash((repo / "plan.md").read_bytes()),
        roles={
            r: {"tool": "synthetic", "binary": "synthetic", "model": "SYNTHETIC"}
            for r in ["architect", "reviewer", "builder", "verifier", "ai-a1", "ai-a2", "ai-a3"]
        },
    )
    return repo, config
