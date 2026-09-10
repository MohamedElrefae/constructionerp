import os
import subprocess
import tarfile
from pathlib import Path

import pytest
from candidates import freeze, git, recheck, verify_owner_commit
from core import WorkflowError, digest, within


def test_candidate_includes_untracked_deletion_modes_symlinks(repo, tmp_path):
    base = git(repo, "rev-parse", "HEAD").decode().strip()
    (repo / "old").unlink()
    (repo / "new").write_text("new bytes")
    (repo / "mode").chmod(0o755)
    (repo / "link").symlink_to("new")
    c = freeze(repo, base, "test", ["old", "new", "mode", "link"], tmp_path / "snapshot")
    assert c["candidate_id"] == digest(c["manifest"])
    entries = {e["path"]: e for e in c["manifest"]["entries"]}
    assert entries["old"]["kind"] == "deleted"
    assert entries["mode"]["mode"] == "100755"
    assert entries["link"]["mode"] == "120000"
    with tarfile.open(tmp_path / "snapshot/tree.tar") as archive:
        assert "old" not in archive.getnames()
        assert archive.extractfile("new").read() == b"new bytes"
    assert git(repo, "diff", "--cached", "--name-only") == b""
    (repo / "new").write_text("drift")
    with pytest.raises(WorkflowError):
        recheck(repo, c["manifest"])


def test_undeclared_and_staged_changes_fail_without_touching_index(repo, tmp_path):
    base = git(repo, "rev-parse", "HEAD").decode().strip()
    (repo / "other").write_text("x")
    with pytest.raises(WorkflowError):
        freeze(repo, base, "test", ["old"], tmp_path / "snapshot")
    git(repo, "add", "other")
    before = git(repo, "write-tree")
    with pytest.raises(WorkflowError):
        freeze(repo, base, "test", ["other"], tmp_path / "snapshot")
    assert git(repo, "write-tree") == before


def test_symlink_escape_and_traversal_refused(repo, tmp_path):
    (repo / "escape").symlink_to(tmp_path)
    with pytest.raises(WorkflowError):
        within(repo, "escape/file")
    with pytest.raises(WorkflowError):
        within(repo, "../other")
    base = git(repo, "rev-parse", "HEAD").decode().strip()
    with pytest.raises(WorkflowError):
        freeze(repo, base, "test", ["escape"], tmp_path / "snapshot")


def test_owner_commit_reconciliation_requires_exact_tree_parent_trailer(repo, tmp_path):
    base = git(repo, "rev-parse", "HEAD").decode().strip()
    (repo / "new").write_text("candidate")
    c = freeze(repo, base, "test", ["new"], tmp_path / "snapshot")
    intent = dict(branch="test", expected_parent_sha=base, expected_tree_oid=c["tree_oid"], job_id="test-job")
    with pytest.raises(WorkflowError):
        verify_owner_commit(repo, intent)
    git(repo, "add", "new")
    git(
        repo,
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "-m",
        "synthetic owner commit\n\nWorkflow-Job: test-job",
    )
    assert verify_owner_commit(repo, intent) == git(repo, "rev-parse", "HEAD").decode().strip()


def test_new_file_after_freeze_invalidates_candidate_even_inside_allowed_scope(repo, tmp_path):
    base = git(repo, "rev-parse", "HEAD").decode().strip()
    (repo / "new").write_text("a")
    c = freeze(repo, base, "test", ["new", "later"], tmp_path / "snapshot")
    (repo / "later").write_text("not reviewed")
    with pytest.raises(WorkflowError, match="file set drift"):
        recheck(repo, c["manifest"])
