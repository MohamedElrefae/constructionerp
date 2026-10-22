"""Freeze exact code bytes, modes and deletions using an isolated Git index."""

import io
import os
import subprocess
import tempfile
from pathlib import Path

from core import WorkflowError, atomic_write, bytes_hash, digest, relative, within, write_json


def git(root, *args, input=None, env=None):
    result = subprocess.run(["git", "-C", str(root), *args], input=input, capture_output=True, env=env)
    if result.returncode:
        raise WorkflowError("Git operation failed: " + args[0])
    return result.stdout


def allowed(path, prefixes):
    return any(path == p or (p.endswith("/") and path.startswith(p)) for p in prefixes)


def changed(root, base):
    paths = git(root, "diff", "--name-only", "-z", base).split(b"\0")
    paths += git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    return sorted({p.decode("utf-8") for p in paths if p})


def freeze(root, base, branch, paths, destination, generated=()):
    root = Path(root).resolve()
    destination = Path(destination).resolve()
    if git(root, "rev-parse", "HEAD").decode().strip() != base:
        raise WorkflowError("Stage parent changed")
    if git(root, "branch", "--show-current").decode().strip() != branch:
        raise WorkflowError("Execution branch mismatch")
    if git(root, "diff", "--cached", "--name-only"):
        raise WorkflowError("Pre-existing staged changes; index left untouched")
    for p in paths:
        relative(p.rstrip("/"))
    entries, contents = [], {}
    for name in changed(root, base):
        relative(name)
        if allowed(name, generated):
            continue
        if not allowed(name, paths):
            raise WorkflowError("Undeclared changed file: " + name)
        source = within(root, name, allow_leaf_symlink=True)
        if destination == source or destination in source.parents or source in destination.parents:
            raise WorkflowError("Candidate includes its own snapshot destination")
        if source.is_symlink():
            data = os.readlink(source).encode()
            # Preserve target bytes without following it; reject escaping symlinks.
            target = (source.parent / os.readlink(source)).resolve()
            if not target.is_relative_to(root):
                raise WorkflowError("Candidate symlink escapes execution root")
            mode, kind = "120000", "symlink"
        elif source.is_file():
            data = source.read_bytes()
            mode, kind = ("100755" if source.stat().st_mode & 0o111 else "100644"), "file"
        elif not source.exists():
            entries.append(dict(path=name, kind="deleted", mode=None, content_sha256=None))
            continue
        else:
            raise WorkflowError("Unsupported candidate file kind")
        contents[name] = data
        entries.append(dict(path=name, kind=kind, mode=mode, content_sha256=bytes_hash(data)))
    manifest = dict(kind="code", base_commit=base, branch=branch, entries=entries)
    candidate_id = digest(manifest)
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="workflow-index-") as temp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"))
        git(root, "read-tree", base, env=env)
        for entry in entries:
            if entry["kind"] == "deleted":
                git(root, "update-index", "--force-remove", "--", entry["path"], env=env)
            else:
                oid = (
                    git(root, "hash-object", "-w", "--stdin", input=contents[entry["path"]], env=env)
                    .decode()
                    .strip()
                )
                git(root, "update-index", "--add", "--cacheinfo", entry["mode"], oid, entry["path"], env=env)
        tree = git(root, "write-tree", env=env).decode().strip()
        archive = git(root, "archive", "--format=tar", tree)
    # Detect changes during capture. Never silently review a newer working copy.
    recheck(root, manifest, generated)
    atomic_write(destination / "tree.tar", archive, immutable=True)
    write_json(destination / "manifest.json", manifest, immutable=True)
    record = dict(
        candidate_id=candidate_id,
        manifest_hash=candidate_id,
        tree_oid=tree,
        archive_sha256=bytes_hash(archive),
        manifest=manifest,
    )
    write_json(destination / "binding.json", record, immutable=True)
    return record


def recheck(root, manifest, generated=()):
    actual = {p for p in changed(root, manifest["base_commit"]) if not allowed(p, generated)}
    expected = {e["path"] for e in manifest["entries"]}
    if actual != expected:
        raise WorkflowError("Candidate file set drift")
    if git(root, "rev-parse", "HEAD").decode().strip() != manifest["base_commit"]:
        raise WorkflowError("Candidate parent drift")
    if git(root, "branch", "--show-current").decode().strip() != manifest["branch"]:
        raise WorkflowError("Candidate branch drift")
    for entry in manifest["entries"]:
        p = within(root, entry["path"], allow_leaf_symlink=True)
        if entry["kind"] == "deleted":
            if p.exists() or p.is_symlink():
                raise WorkflowError("Deleted path reappeared")
            continue
        if entry["kind"] == "symlink":
            if not p.is_symlink():
                raise WorkflowError("Candidate symlink changed")
            data, mode = os.readlink(p).encode(), "120000"
        else:
            if p.is_symlink() or not p.is_file():
                raise WorkflowError("Candidate file kind changed")
            data = p.read_bytes()
            mode = "100755" if p.stat().st_mode & 0o111 else "100644"
        if bytes_hash(data) != entry["content_sha256"] or mode != entry["mode"]:
            raise WorkflowError("Candidate bytes/mode drift")


def verify_owner_commit(root, intent):
    """Read-only reconciliation. This module NEVER creates a commit."""
    if git(root, "branch", "--show-current").decode().strip() != intent["branch"]:
        raise WorkflowError("Commit branch mismatch")
    parents = git(root, "show", "-s", "--format=%P", "HEAD").decode().strip().split()
    tree = git(root, "rev-parse", "HEAD^{tree}").decode().strip()
    message = git(root, "show", "-s", "--format=%B", "HEAD").decode()
    if parents != [intent["expected_parent_sha"]] or tree != intent["expected_tree_oid"]:
        raise WorkflowError("Commit outcome uncertain: expected parent/tree not observed")
    trailer = "Workflow-Job: " + intent["job_id"]
    if trailer not in message.splitlines():
        raise WorkflowError("Commit correlation trailer missing")
    return git(root, "rev-parse", "HEAD").decode().strip()
