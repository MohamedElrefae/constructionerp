#!/usr/bin/env python3
"""Generate the self-verifying G16 evidence manifest.

Enumerates every deliverable and modified file for the end-to-end
bilingual commercial UAT work item, computes SHA-256 digests, and
writes evidence/MANIFEST.json. Pair with verify_manifest.py to prove
integrity.

Usage:
    python3 docs/ai/work-items/e2e-bilingual-commercial-uat/scripts/generate_manifest.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORK_ITEM_REL = "docs/ai/work-items/e2e-bilingual-commercial-uat"
WORK_ITEM = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(WORK_ITEM, "..", "..", "..", ".."))

EVIDENCE_REL = f"{WORK_ITEM_REL}/evidence"
SAMPLES_REL = f"{EVIDENCE_REL}/rendered-samples"

SAMPLE_FILES = sorted(
    f"{SAMPLES_REL}/{name}"
    for name in os.listdir(os.path.join(REPO, SAMPLES_REL))
    if os.path.isfile(os.path.join(REPO, SAMPLES_REL, name))
)

DELIVERABLES = [
    f"{WORK_ITEM_REL}/SCOPE.md",
    f"{EVIDENCE_REL}/e2e-workflow-execution.log",
    f"{EVIDENCE_REL}/gates.log",
    f"{WORK_ITEM_REL}/scripts/generate_manifest.py",
    f"{WORK_ITEM_REL}/scripts/verify_manifest.py",
    "construction/tests/test_e2e_bilingual_commercial_workflow.py",
    *SAMPLE_FILES,
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
        "session": "3C",
        "work_item": "e2e-bilingual-commercial-uat",
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "base_commit": "7cdb01d56db3be36edbfa9a69e884ff7a280277b",
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
