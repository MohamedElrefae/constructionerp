#!/usr/bin/env python3
"""Transport the owner-authorized PRIVATE Frappe v16 Pillow 13 vendor divergence.

The reviewed divergence commit (af440917...) is NOT published to any public frappe
repository and is therefore NOT fetchable by SHA. Instead of applying an
uncommitted working-tree patch (which leaves HEAD at the upstream base and lets a
HEAD-only vendor-delta gate miss the divergence), this applier:

  1. proves the checkout is the exact pinned base with a clean tracked
     working tree AND index;
  2. applies the reviewed one-line patch and proves the staged tree is the
     reviewed divergence tree;
  3. reconstructs the EXACT reviewed private commit locally from the recorded
     raw commit object (git hash-object -t commit -w), proving its SHA-1;
  4. checks out that commit and proves HEAD == the reviewed commit, HEAD tree ==
     the reviewed tree, parent == the pinned base, and that the tracked working
     tree and index are clean.

Modes
  apply     (default) perform steps 1-4. Requires the pinned base as HEAD.
  --verify  re-assert the effective committed identity and a clean tracked
            working tree and index against it, without writing anything. Use at
            execution/measurement boundaries (before native/JS execution and
            before measurement).

Every mismatch exits non-zero BEFORE the job continues. This script is
fail-closed: it never resets, checks out, stashes or cleans away unexpected
changes. A dirty checkout is a failure, not something to repair.

Usage:
  apply_private_vendor_divergence.py <frappe-app-dir> <patch-file> <identity-json> [--verify]
"""

import hashlib
import json
import subprocess
import sys

PREFIX = "PRIVATE VENDOR DIVERGENCE FAILED"
OK_APPLIED = "PRIVATE VENDOR DIVERGENCE APPLIED"
OK_VERIFIED = "PRIVATE VENDOR DIVERGENCE VERIFIED"


def fail(message):
	print(f"{PREFIX}: {message}", file=sys.stderr)
	sys.exit(1)


def run_git(app_dir, *args):
	return subprocess.run(
		["git", "-C", app_dir, *args], capture_output=True, text=True
	)


def git(app_dir, *args):
	proc = run_git(app_dir, *args)
	if proc.returncode != 0:
		fail(
			f"git {' '.join(args)} failed with exit {proc.returncode}: "
			f"{(proc.stderr or proc.stdout).strip()}"
		)
	return proc.stdout.strip()


def sha256_file(path):
	with open(path, "rb") as handle:
		return hashlib.sha256(handle.read()).hexdigest()


def load_identity(identity_file):
	try:
		with open(identity_file, encoding="utf-8") as handle:
			identity = json.load(handle)
	except (OSError, ValueError) as exc:
		fail(f"cannot read identity record {identity_file}: {exc}")
	required = (
		"base_commit",
		"base_tree",
		"base_file",
		"base_file_sha256",
		"patch_file",
		"patch_sha256",
		"effective_commit",
		"effective_commit_tree",
		"effective_commit_parent",
		"commit_object_file",
		"commit_object_sha256",
		"commit_object_bytes",
		"patched_file",
		"patched_file_sha256",
	)
	missing = [key for key in required if key not in identity]
	if missing:
		fail(f"identity record is missing required keys: {', '.join(missing)}")
	if identity["effective_commit_parent"] != identity["base_commit"]:
		fail(
			"identity record is internally inconsistent: effective_commit_parent "
			f"{identity['effective_commit_parent']} != base_commit {identity['base_commit']}"
		)
	return identity


def status_tracked(app_dir):
	# Porcelain output is position sensitive (" M path" vs "M  path"); do not strip
	# leading spaces, only the trailing newline.
	return run_git(app_dir, "status", "--porcelain=v1", "--untracked-files=no").stdout.rstrip("\n")


def assert_clean_tracked(app_dir, boundary, expected_head_tree):
	"""Require a clean tracked working tree AND index against the current HEAD."""
	status = status_tracked(app_dir)
	if status:
		fail(
			f"tracked working tree/index is NOT clean at {boundary}; refusing to "
			f"continue and NOT resetting anything:\n{status}"
		)
	head_tree = git(app_dir, "rev-parse", "HEAD^{tree}")
	if head_tree != expected_head_tree:
		fail(
			f"HEAD tree {head_tree} != expected {expected_head_tree} at {boundary}"
		)
	index_tree = git(app_dir, "write-tree")
	if index_tree != head_tree:
		fail(
			f"index tree {index_tree} != HEAD tree {head_tree} at {boundary}: the "
			"staged content is not the committed vendor content"
		)
	if run_git(app_dir, "diff-index", "--quiet", "HEAD", "--").returncode != 0:
		fail(f"tracked working tree differs from HEAD at {boundary}")
	if run_git(app_dir, "diff-index", "--cached", "--quiet", "HEAD", "--").returncode != 0:
		fail(f"index differs from HEAD at {boundary}")


def assert_commit_identity(app_dir, identity, boundary):
	head = git(app_dir, "rev-parse", "HEAD")
	if head != identity["effective_commit"]:
		fail(
			f"HEAD {head} != reviewed private vendor commit "
			f"{identity['effective_commit']} at {boundary}"
		)
	head_tree = git(app_dir, "rev-parse", "HEAD^{tree}")
	if head_tree != identity["effective_commit_tree"]:
		fail(
			f"HEAD tree {head_tree} != reviewed private vendor tree "
			f"{identity['effective_commit_tree']} at {boundary}"
		)
	commit_type = git(app_dir, "cat-file", "-t", identity["effective_commit"])
	if commit_type != "commit":
		fail(f"{identity['effective_commit']} is a {commit_type}, not a commit")
	parent = git(app_dir, "rev-parse", f"{identity['effective_commit']}^")
	if parent != identity["effective_commit_parent"]:
		fail(
			f"private vendor commit parent {parent} != pinned base "
			f"{identity['effective_commit_parent']}"
		)


def assert_transport_files(identity_file, identity):
	patch_path = str((_identity_dir(identity_file) / identity["patch_file"]))
	try:
		digest = sha256_file(patch_path)
	except OSError as exc:
		fail(f"cannot read transport patch {patch_path}: {exc}")
	if digest != identity["patch_sha256"]:
		fail(f"transport patch digest {digest} != pinned {identity['patch_sha256']}")
	object_path = str((_identity_dir(identity_file) / identity["commit_object_file"]))
	try:
		object_digest = sha256_file(object_path)
	except OSError as exc:
		fail(f"cannot read raw commit object {object_path}: {exc}")
	if object_digest != identity["commit_object_sha256"]:
		fail(
			f"raw commit object digest {object_digest} != pinned "
			f"{identity['commit_object_sha256']} (tampered commit metadata)"
		)
	with open(object_path, "rb") as handle:
		size = len(handle.read())
	if size != identity["commit_object_bytes"]:
		fail(
			f"raw commit object is {size} bytes, pinned "
			f"{identity['commit_object_bytes']} (tampered commit metadata)"
		)
	return patch_path, object_path


def _identity_dir(identity_file):
	from pathlib import Path

	return Path(identity_file).resolve().parent


def apply_mode(app_dir, identity_file, identity):
	patch_path, object_path = assert_transport_files(identity_file, identity)

	head = git(app_dir, "rev-parse", "HEAD")
	if head != identity["base_commit"]:
		fail(
			f"vendor checkout HEAD {head} != pinned base {identity['base_commit']} "
			"(wrong base; nothing was applied)"
		)
	head_tree = git(app_dir, "rev-parse", "HEAD^{tree}")
	if head_tree != identity["base_tree"]:
		fail(
			f"vendor checkout HEAD tree {head_tree} != pinned base tree "
			f"{identity['base_tree']} (wrong base; nothing was applied)"
		)
	assert_clean_tracked(app_dir, "pre-apply", identity["base_tree"])

	check = run_git(app_dir, "apply", "--check", patch_path)
	if check.returncode != 0:
		fail("transport patch does not apply cleanly:\n" + (check.stderr or check.stdout))

	applied = run_git(app_dir, "apply", patch_path)
	if applied.returncode != 0:
		fail("transport patch apply failed:\n" + (applied.stderr or applied.stdout))

	expected_unstaged = f" M {identity['patched_file']}"
	status = status_tracked(app_dir)
	if status != expected_unstaged:
		fail(
			"applying the transport patch changed an unexpected set of tracked "
			f"paths; expected only '{expected_unstaged}', got:\n{status}"
		)

	patched_path = f"{app_dir.rstrip('/')}/{identity['patched_file']}"
	patched_digest = sha256_file(patched_path)
	if patched_digest != identity["patched_file_sha256"]:
		fail(
			f"patched {identity['patched_file']} digest {patched_digest} != pinned "
			f"{identity['patched_file_sha256']}"
		)
	with open(patched_path, encoding="utf-8") as handle:
		if '"Pillow~=13.0.0",' not in handle.read():
			fail(f"patched {identity['patched_file']} does not declare Pillow~=13.0.0")

	git(app_dir, "add", "--", identity["patched_file"])
	expected_staged = f"M  {identity['patched_file']}"
	status = status_tracked(app_dir)
	if status != expected_staged:
		fail(
			"staging the reviewed patch staged an unexpected set of tracked paths; "
			f"expected only '{expected_staged}', got:\n{status}"
		)
	index_tree = git(app_dir, "write-tree")
	if index_tree != identity["effective_commit_tree"]:
		fail(
			f"staged tree {index_tree} != reviewed private vendor tree "
			f"{identity['effective_commit_tree']}"
		)

	object_sha = git(app_dir, "hash-object", "-t", "commit", object_path)
	if object_sha != identity["effective_commit"]:
		fail(
			f"raw commit object hashes to {object_sha}, not the reviewed private "
			f"vendor commit {identity['effective_commit']} (tampered commit metadata)"
		)

	# The raw object is authoritative; assert its header lines before writing it.
	with open(object_path, encoding="utf-8") as handle:
		object_header = [handle.readline().strip(), handle.readline().strip()]
	if object_header[0] != f"tree {identity['effective_commit_tree']}":
		fail(f"raw commit object tree line '{object_header[0]}' != reviewed tree")
	if object_header[1] != f"parent {identity['effective_commit_parent']}":
		fail(f"raw commit object parent line '{object_header[1]}' != pinned base")

	git(app_dir, "hash-object", "-t", "commit", "-w", object_path)
	if git(app_dir, "cat-file", "-t", identity["effective_commit"]) != "commit":
		fail("reconstructed commit object is not readable as a commit")

	git(
		app_dir,
		"-c",
		"advice.detachedHead=false",
		"checkout",
		"--detach",
		identity["effective_commit"],
	)

	assert_commit_identity(app_dir, identity, "post-checkout")
	assert_clean_tracked(
		app_dir, "post-checkout", identity["effective_commit_tree"]
	)

	print(
		f"{OK_APPLIED}: base {identity['base_commit']} -> effective HEAD "
		f"{identity['effective_commit']} (tree {identity['effective_commit_tree']}, "
		"upstream-supported: NO, unpublished: reconstructed locally from the "
		"recorded commit object)"
	)


def verify_mode(app_dir, identity_file, identity):
	assert_transport_files(identity_file, identity)
	assert_commit_identity(app_dir, identity, "measurement")
	assert_clean_tracked(app_dir, "measurement", identity["effective_commit_tree"])
	print(
		f"{OK_VERIFIED}: HEAD {identity['effective_commit']} "
		f"(tree {identity['effective_commit_tree']}), tracked worktree and index clean"
	)


def main(argv):
	if len(argv) not in (4, 5):
		fail(
			"usage: apply_private_vendor_divergence.py <frappe-app-dir> "
			"<patch-file> <identity-json> [--verify]"
		)
	app_dir = argv[1].rstrip("/")
	patch_file = argv[2]
	identity_file = argv[3]
	mode = argv[4] if len(argv) == 5 else "apply"
	if mode not in ("apply", "--verify"):
		fail(f"unknown mode {mode!r} (expected apply or --verify)")
	identity = load_identity(identity_file)
	# The patch path is an explicit argument in CI; it must be the reviewed file.
	try:
		patch_digest = sha256_file(patch_file)
	except OSError as exc:
		fail(f"cannot read transport patch {patch_file}: {exc}")
	if patch_digest != identity["patch_sha256"]:
		fail(f"transport patch digest {patch_digest} != pinned {identity['patch_sha256']}")
	if mode == "--verify":
		verify_mode(app_dir, identity_file, identity)
	else:
		apply_mode(app_dir, identity_file, identity)
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv))
