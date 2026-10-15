"""Verify the STAGED customer tree (F28-D003) — not the checkout.

Checks the actual files in STAGE_DIR against the customer allowlist and never-ship list:
no never-ship path present, every required runtime/build file present, every relative
link inside shipped Markdown resolves inside the staged tree, then records the artifact
manifest with sha256 hashes.

Usage (from the app root):  python3 scripts/verify_staged_distribution.py [--dir DIR]
"""

import argparse
import hashlib
import json
import os
import re
import sys

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s][^)\s]*)\)")

REQUIRED = (
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "docs/CUSTOMER_ONBOARDING.md",
    "docs/MAINTENANCE.md",
    "construction/construction/sidebar/construction_home/construction_home.json",
    "construction/hooks.py",
    "construction/api/construction_reports.py",
    "construction/overrides/boq_permissions.py",
    "construction/overrides/file_permissions.py",
    "construction/overrides/file_download.py",
    "construction/public/js/vite_layout_controls.js",
)

NEVER_SHIP_BASENAMES = (".map",)
NEVER_SHIP_DIRS = ("docs/ai", "orchestrator", "tests_offline", "erpnext-mcp-server")
NEVER_SHIP_ROOTS = ("setup.py",)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/tmp/opencode/customer-dist")
    args = ap.parse_args()
    stage = os.path.abspath(args.dir)
    failures = []
    if not os.path.isdir(stage):
        print(f"STAGED DIR MISSING: {stage} (run stage_distribution.py first)")
        return 2

    present = []
    for root, dirs, files in os.walk(stage):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in files:
            present.append(os.path.relpath(os.path.join(root, fn), stage))
    present_set = set(present)

    # 1. never-ship content must be absent from the actual tree
    bad = sorted(
        p for p in present
        if p in NEVER_SHIP_ROOTS
        or p.startswith(NEVER_SHIP_DIRS)
        or any(p.endswith(ext) for ext in NEVER_SHIP_BASENAMES if p.endswith(".map"))
        or p == "DISTRIBUTION_MANIFEST.json" and False
    )
    # docs/ai check needs prefix care (docs/ai... vs docs/AI): exact prefix
    bad += sorted(p for p in present if p.startswith("docs/ai/") or p == "docs/ai")
    if bad:
        failures.append(f"never-ship paths present in staged tree ({len(bad)}): {bad[:12]}")
    else:
        print(f"PASS never-ship absent ({len(present)} files checked)")

    # 2. required runtime/build files present
    missing = [r for r in REQUIRED if r not in present_set]
    if missing:
        failures.append(f"required files missing: {missing}")
    else:
        print(f"PASS required files present ({len(REQUIRED)})")

    # 3. relative Markdown links resolve inside the staged tree
    broken = []
    for p in sorted(present):
        if not p.endswith(".md"):
            continue
        try:
            text = open(os.path.join(stage, p), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        base = os.path.dirname(p)
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = os.path.normpath(os.path.join(base, target))
            if resolved not in present_set and not os.path.isdir(os.path.join(stage, resolved)):
                broken.append(f"{p} -> {target}")
    if broken:
        failures.append(f"broken doc links ({len(broken)}): {broken[:12]}")
    else:
        print("PASS doc links resolve")

    # 4. artifact manifest + hashes
    rows = []
    for p in sorted(present):
        if p == "DISTRIBUTION_MANIFEST.json":
            continue
        h = hashlib.sha256(open(os.path.join(stage, p), "rb").read()).hexdigest()
        rows.append({"path": p, "sha256": h})
    manifest = {
        "method": "local preparation only; customer delivery pending review.",
        "files": len(rows),
        "rows": rows,
    }
    with open(os.path.join(stage, "DISTRIBUTION_MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"PASS manifest recorded ({len(rows)} hashed files)")

    if failures:
        print("\nSTAGED VERIFICATION FAILED")
        for failure in failures:
            print(" -", failure)
        return 1
    print("\nSTAGED VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
