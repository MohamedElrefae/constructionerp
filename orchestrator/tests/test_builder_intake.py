import base64
import hashlib
import os

import pytest

from builder_intake import MAX_FILE_BYTES, MAX_FILES, MAX_TOTAL_BYTES, stage_bundle
from core import WorkflowError


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _entry(path, base, content):
    return {
        "path": path,
        "base_sha256": _hash(base) if base is not None else None,
        "content_base64": base64.b64encode(content).decode("ascii"),
        "content_sha256": _hash(content),
    }


def test_stages_verified_changes_in_new_separate_workspace(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "existing.txt").write_bytes(b"baseline")
    bundle = {"files": [_entry("existing.txt", b"baseline", b"proposed"),
                        _entry("new/file.txt", None, b"new content")]}

    result = stage_bundle(source, bundle, tmp_path / "staged", ["existing.txt", "new/"])

    assert (tmp_path / "staged/existing.txt").read_bytes() == b"proposed"
    assert (tmp_path / "staged/new/file.txt").read_bytes() == b"new content"
    assert (source / "existing.txt").read_bytes() == b"baseline"
    assert result["staged_paths"] == ["existing.txt", "new/file.txt"]
    assert result["status"] == "staged_for_review"
    assert result["validation_complete"] is False
    assert result["validation_passed"] is False
    assert (tmp_path / "staged").stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("path", ["../escape", "/absolute", "a/../b", "a\\b", "./dot"])
def test_rejects_traversal_absolute_and_non_normalized_paths(tmp_path, path):
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(WorkflowError):
        stage_bundle(source, {"files": [_entry(path, None, b"x")]},
                     tmp_path / "staged", ["safe/"])
    assert not (tmp_path / "staged").exists()


def test_rejects_symlinked_source_path_and_duplicate_names(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "file").write_bytes(b"secret")
    (source / "link").symlink_to(outside, target_is_directory=True)
    symlink_item = _entry("link/file", b"secret", b"overwrite")
    with pytest.raises(WorkflowError, match="Symlink"):
        stage_bundle(source, {"files": [symlink_item]}, tmp_path / "staged", ["link/"])

    item = _entry("safe", None, b"x")
    with pytest.raises(WorkflowError, match="Duplicate"):
        stage_bundle(source, {"files": [item, item]}, tmp_path / "duplicate", ["safe"])
    assert not (tmp_path / "staged").exists()
    assert not (tmp_path / "duplicate").exists()


@pytest.mark.parametrize("bad_entry", [
    lambda: {**_entry("file", None, b"payload"), "content_sha256": "0" * 64},
    lambda: {**_entry("file", b"wrong-base", b"payload"), "base_sha256": _hash(b"wrong-base")},
])
def test_rejects_content_or_base_hash_mismatch(tmp_path, bad_entry):
    source = tmp_path / "source"
    source.mkdir()
    (source / "file").write_bytes(b"actual-base")
    with pytest.raises(WorkflowError, match="hash mismatch"):
        stage_bundle(source, {"files": [bad_entry()]}, tmp_path / "staged", ["file"])
    assert not (tmp_path / "staged").exists()


def test_rejects_size_limits_and_existing_or_in_tree_destination(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    oversized = b"x" * (MAX_FILE_BYTES + 1)
    with pytest.raises(WorkflowError, match="size limit"):
        stage_bundle(source, {"files": [_entry("large", None, oversized)]},
                     tmp_path / "staged", ["large"])
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(WorkflowError, match="already exists"):
        stage_bundle(source, {"files": [_entry("small", None, b"x")]}, existing, ["small"])
    with pytest.raises(WorkflowError, match="separate"):
        stage_bundle(source, {"files": [_entry("small", None, b"x")]},
                     source / "staged", ["small"])
    assert not (tmp_path / "staged").exists()


def test_rejects_fifo_without_waiting_for_a_writer(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    os.mkfifo(source / "pipe")
    with pytest.raises(WorkflowError, match="regular file"):
        stage_bundle(source, {"files": [_entry("pipe", b"unused", b"new")]},
                     tmp_path / "staged", ["pipe"])
    assert not (tmp_path / "staged").exists()


def test_rejects_file_count_and_aggregate_size_bounds(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    too_many = [_entry(f"f{i}", None, b"x") for i in range(MAX_FILES + 1)]
    with pytest.raises(WorkflowError, match="file count"):
        stage_bundle(source, {"files": too_many}, tmp_path / "too-many", ["f"])

    chunk = b"x" * (MAX_TOTAL_BYTES // 5 + 1)
    aggregate = [_entry(f"part{i}", None, chunk) for i in range(5)]
    with pytest.raises(WorkflowError, match="total size"):
        stage_bundle(source, {"files": aggregate}, tmp_path / "too-large", [f"part{i}" for i in range(5)])
    assert not (tmp_path / "too-many").exists()
    assert not (tmp_path / "too-large").exists()
