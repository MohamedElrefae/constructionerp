#!/usr/bin/env python3
"""Generate the self-verifying G10 evidence manifest.

Enumerates every deliverable and modified file for the dependency-security
remediation work item, computes SHA-256 digests, and writes
evidence/MANIFEST.json. Pair with verify_manifest.py to prove integrity.

Usage:
    python3 docs/ai/work-items/dependency-security-remediation/scripts/generate_manifest.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORK_ITEM_REL = "docs/ai/work-items/dependency-security-remediation"
WORK_ITEM = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(WORK_ITEM, "..", "..", "..", ".."))

DELIVERABLES = [
    f"{WORK_ITEM_REL}/SCOPE.md",
    f"{WORK_ITEM_REL}/evidence/dependency-reconciliation.log",
    f"{WORK_ITEM_REL}/evidence/clean-build.log",
    f"{WORK_ITEM_REL}/evidence/security-guards.log",
    f"{WORK_ITEM_REL}/evidence/gates.log",
    f"{WORK_ITEM_REL}/scripts/reconcile_dependencies.py",
    f"{WORK_ITEM_REL}/scripts/generate_manifest.py",
    f"{WORK_ITEM_REL}/scripts/verify_manifest.py",
    "construction/construction/utils/security.py",
    "construction/utils/security.py",
    "construction/tests/test_dependency_security_guards.py",
    "pyproject.toml",
    "requirements.txt",
]


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, text=True, capture_output=True, check=True
    ).stdout.strip()


def main() -> int:
    files = {}
    for rel in DELIVERABLES:
        abs_path = os.path.join(REPO, rel)
        if not os.path.isfile(abs_path):
            raise SystemExit(f"missing deliverable: {rel}")
        files[rel] = sha256(abs_path)

    manifest = {
        "session": "3A",
        "work_item": "dependency-security-remediation",
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "base_commit": "78b7094bcd61f6acf1a6c5a346cf2f3066590ad4",
        "hash_algorithm": "sha256",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": files,
    }

    out = os.path.join(REPO, WORK_ITEM_REL, "evidence", "MANIFEST.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"wrote {os.path.relpath(out, REPO)} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
