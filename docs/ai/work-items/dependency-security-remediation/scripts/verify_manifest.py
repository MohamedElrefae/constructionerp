#!/usr/bin/env python3
"""Verify the self-verifying G10 evidence manifest.

Reads evidence/MANIFEST.json and asserts that every listed digest matches the
file on disk. Exit code is non-zero on any mismatch or missing file.

Usage:
    python3 docs/ai/work-items/dependency-security-remediation/scripts/verify_manifest.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK_ITEM_REL = "docs/ai/work-items/dependency-security-remediation"
WORK_ITEM = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(WORK_ITEM, "..", "..", "..", ".."))
MANIFEST = os.path.join(REPO, WORK_ITEM_REL, "evidence", "MANIFEST.json")


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    with open(MANIFEST, encoding="utf-8") as handle:
        manifest = json.load(handle)

    failures = []
    for rel, expected in manifest.get("files", {}).items():
        abs_path = os.path.join(REPO, rel)
        if not os.path.isfile(abs_path):
            failures.append(f"MISSING {rel}")
            continue
        actual = sha256(abs_path)
        if actual != expected:
            failures.append(f"MISMATCH {rel}\n  expected {expected}\n  actual   {actual}")
        else:
            print(f"OK   {rel}")

    print()
    print(f"manifest: {MANIFEST}")
    print(f"entries : {len(manifest.get('files', {}))}")
    if failures:
        print(f"FAILURES: {len(failures)}")
        print("\n".join(failures))
        return 1
    print("RESULT  : PASS (all digests verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
