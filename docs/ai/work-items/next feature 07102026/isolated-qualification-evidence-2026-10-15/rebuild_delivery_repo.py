#!/usr/bin/env python3
"""Rebuild + re-verify the D4 curated delivery scratch repository (volatile /tmp).

Method (owner-approved D4): fresh `git init`, copy of the customer set only,
single squashed commit, no remotes. Verification: exactly one reachable commit,
`git log --all` clean of never-ship paths, file-by-file hash match against the
staged manifest. NO publication, NO remotes, NO push.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

STAGE = "/tmp/opencode/customer-dist"
DEST = "/tmp/opencode/customer-repo"

NEVER_SHIP_GLOBS = ["docs/ai/", "orchestrator/", "erpnext-mcp-server/", "tests_offline/",
                    ".map", "tests/*.png", "docs/translation/", "docs/scope_context_option_",
                    "docs/feature_reviews/evidence/"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


if os.path.exists(DEST):
    shutil.rmtree(DEST)
os.makedirs(DEST)

# copy staged set (the customer allowlist already applied by stage_distribution.py)
manifest = json.load(open(os.path.join(STAGE, "DISTRIBUTION_MANIFEST.json")))
staged_rows = manifest["rows"]  # verify_staged_distribution.py writes path+sha256 rows
staged_files = [r["path"] for r in staged_rows]
copied = 0
for rel in staged_files:
    src = os.path.join(STAGE, rel)
    if not os.path.exists(src):
        print("MISSING STAGED FILE:", rel)
        sys.exit(1)
    dst = os.path.join(DEST, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    copied += 1
print(f"copied {copied} files into fresh repo")

init = run(["git", "init", "-q", "."], DEST)
assert init.returncode == 0, init.stderr
run(["git", "config", "user.email", "delivery-prep@local.invalid"], DEST)
run(["git", "config", "user.name", "Delivery Preparation"], DEST)
run(["git", "add", "-A"], DEST)
commit = run(["git", "commit", "-q", "-m",
              "Customer candidate: curated set per docs/DISTRIBUTION.md "
              "(local preparation, unpublished)"], DEST)
assert commit.returncode == 0, commit.stderr

# --- verification ---
commits = run(["git", "rev-list", "--all", "--count"], DEST).stdout.strip()
head = run(["git", "rev-parse", "HEAD"], DEST).stdout.strip()
remotes = run(["git", "remote", "-v"], DEST).stdout.strip()
tags = run(["git", "tag"], DEST).stdout.strip()
branches = run(["git", "branch", "-a"], DEST).stdout.strip()
tracked_raw = run(["git", "ls-files", "-z"], DEST).stdout
tracked = [t for t in tracked_raw.split("\0") if t]

print(f"reachable commits: {commits} (must be 1)")
print(f"HEAD: {head}")
print(f"remotes: {remotes or '(none)'} (must be none)")
print(f"tags: {tags or '(none)'}")
print(f"branches: {branches.strip()}")

# never-ship paths must not exist anywhere in the tree
leaks = []
for rel in tracked:
    for g in NEVER_SHIP_GLOBS:
        if g.startswith("."):
            if rel.endswith(g):
                leaks.append(rel)
        else:
            gg = g if g.endswith("/") else g + "/"
            if rel.startswith(gg) or (g in rel):
                leaks.append(f"{rel} (matched {g})")
print(f"never-ship path leaks: {len(set(leaks))}")
for l in sorted(set(leaks)):
    print("   LEAK:", l)

# file-by-file hash match vs staged manifest (authoritative hashes from verify script)
mismatch = []
for rel in staged_files:
    want = next(r["sha256"] for r in staged_rows if r["path"] == rel)
    if sha(os.path.join(DEST, rel)) != want:
        mismatch.append(rel)
print(f"files compared: {len(staged_files)} | mismatches: {len(mismatch)}")
for m in mismatch[:10]:
    print("   MISMATCH:", m)

ok = (commits == "1" and not remotes and not leaks and not mismatch
      and len(tracked) == len(staged_files))
print("VERIFICATION:", "PASSED — separate clean repo, 1 commit, 0 remotes, "
      "0 never-ship paths, byte-identical" if ok else "FAILED")
sys.exit(0 if ok else 1)
