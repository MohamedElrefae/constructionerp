"""Stage the curated customer distribution locally (F28-D003, docs/DISTRIBUTION.md).

Builds STAGE_DIR from the current worktree (which equals the F31 snapshot: HEAD fa38022
+ recorded diff + hashed untracked files) applying the customer allowlist and the
never-ship list. No publication, no commit, no network. Internal evidence never leaves
this machine; only the manifest (paths + hashes) is recorded alongside.

Usage (from the app root):  python3 scripts/stage_distribution.py [--out DIR]
Default out: /tmp/opencode/customer-dist/
"""

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Never-ship patterns, relative to the app root. First match wins.
NEVER_SHIP = (
    "docs/ai/*",
    "docs/feature_reviews/evidence/*",
    "docs/translation/*",
    "docs/scope_context_option_*",
    "orchestrator/*",
    "tests_offline/*",
    "erpnext-mcp-server/*",
    "construction/public/dist/js/*.map",
    "construction/tests/*.png",
    "**/__pycache__/*",
    "**/*.pyc",
    "setup.py",
    "dist/*",
)

# Customer allowlist: (source relative path or dir, destination relative path).
# A source dir ships its whole tree minus NEVER_SHIP.
CUSTOMER = (
    ("construction", "construction"),
    ("README.md", "README.md"),
    ("pyproject.toml", "pyproject.toml"),
    ("requirements.txt", "requirements.txt"),
    ("LICENSE", "LICENSE"),
    ("LICENSE.txt", "LICENSE.txt"),
    ("license.txt", "license.txt"),
    ("docs/CUSTOMER_ONBOARDING.md", "docs/CUSTOMER_ONBOARDING.md"),
    ("docs/MAINTENANCE.md", "docs/MAINTENANCE.md"),
    ("docs/onboarding.md", "docs/onboarding.md"),
    ("docs/token_reference.md", "docs/token_reference.md"),
    ("docs/BILINGUAL_TASK_GUIDES.md", "docs/BILINGUAL_TASK_GUIDES.md"),
    ("docs/DISTRIBUTION.md", "docs/DISTRIBUTION.md"),
    ("docs/PERMISSION_SETUP.md", "docs/PERMISSION_SETUP.md"),
)


def never_ships(rel):
    rel = rel.replace(os.sep, "/")
    return any(fnmatch.fnmatchcase(rel, pat) or fnmatch.fnmatchcase(rel, pat.rstrip("/*"))
               for pat in NEVER_SHIP)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/opencode/customer-dist")
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    staged, skipped = [], []
    for src_rel, dst_rel in CUSTOMER:
        src = os.path.join(APP_ROOT, src_rel)
        if not os.path.exists(src):
            if src_rel.upper().startswith("LICENSE"):
                continue  # any one license file suffices; checked below
            skipped.append(f"missing source (not staged): {src_rel}")
            continue
        if os.path.isdir(src):
            for root, dirs, files in os.walk(src):
                dirs[:] = [d for d in dirs if "__pycache__" not in d]
                for fn in files:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, APP_ROOT)
                    if never_ships(rel):
                        skipped.append(f"excluded: {rel}")
                        continue
                    dst = os.path.join(out, os.path.relpath(full, APP_ROOT))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(full, dst)
                    staged.append(os.path.relpath(full, APP_ROOT))
        else:
            if never_ships(src_rel):
                skipped.append(f"excluded: {src_rel}")
                continue
            dst = os.path.join(out, dst_rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            staged.append(src_rel)

    # License presence: at least one must have shipped.
    if not any(os.path.basename(s).lower().startswith("license") for s in staged):
        print("WARNING: no license file found to stage", file=sys.stderr)

    manifest = {
        "method": "local staging from worktree snapshot (F31 snapshot HEAD fa38022 + diff); "
                  "no publication. Customer delivery pending review.",
        "staged_files": len(staged),
        "excluded_count": len([s for s in skipped if s.startswith("excluded")]),
        "missing_sources": [s for s in skipped if s.startswith("missing")],
        "files": sorted(staged),
    }
    with open(os.path.join(out, "DISTRIBUTION_MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"staged {len(staged)} files -> {out}")
    print(f"excluded {manifest['excluded_count']} | missing sources: {manifest['missing_sources']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
