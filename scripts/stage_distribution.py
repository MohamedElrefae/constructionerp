"""Stage a curated customer distribution from committed HEAD blobs.

The output directory must not already exist and must be outside the app checkout.
Staging is local preparation only; it does not publish or install the package.

Usage: python3 scripts/stage_distribution.py [--out DIR]
Default output: /tmp/opencode/customer-dist
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from distribution_policy import LICENSE_CANDIDATES, REQUIRED_CUSTOMER_FILES, is_customer_path, never_ships

APP_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT_REAL = APP_ROOT.resolve()
DEFAULT_OUT = Path("/tmp/opencode/customer-dist")


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _tree_digest(rows):
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(row["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def validate_output_path(out, app_root=APP_ROOT_REAL):
    """Reject existing outputs and any destination that could contain the checkout."""
    raw = Path(out).expanduser().absolute()
    if os.path.lexists(raw):
        raise ValueError(f"output already exists; refusing to overwrite or delete: {raw}")

    resolved = raw.resolve(strict=False)
    root = Path(app_root).resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError(f"output must be outside the app checkout: {resolved}")
    if resolved in root.parents:
        raise ValueError(f"output must not be an ancestor of the app checkout: {resolved}")
    return raw


def _git_head(app_root):
    result = subprocess.run(
        ["git", "-C", str(app_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_tree_entries(app_root, head):
    result = subprocess.run(
        ["git", "-C", str(app_root), "ls-tree", "-rz", head],
        check=True,
        capture_output=True,
    )
    entries = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, object_type, object_id = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8")
        entries[path] = (mode, object_type, object_id)
    return entries


def _committed_sources():
    head = _git_head(APP_ROOT)
    entries = _git_tree_entries(APP_ROOT, head)
    selected = sorted(path for path in entries if is_customer_path(path) and not never_ships(path))
    missing_sources = sorted(REQUIRED_CUSTOMER_FILES - set(selected))
    if missing_sources:
        raise FileNotFoundError(f"required customer sources are not tracked in HEAD: {missing_sources}")

    if not set(selected) & LICENSE_CANDIDATES:
        raise FileNotFoundError("no license file found in customer sources")

    staged = []
    for rel in selected:
        mode, object_type, object_id = entries[rel]
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"selected customer source is not a regular committed file: {rel}")
        result = subprocess.run(
            ["git", "-C", str(APP_ROOT), "cat-file", "blob", object_id],
            check=True,
            capture_output=True,
        )
        staged.append((rel, result.stdout))
    return head, staged


def stage(out):
    out = validate_output_path(out)
    head, staged_sources = _committed_sources()
    out.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive mkdir closes the check/use race and never replaces an existing path.
    out.mkdir(exist_ok=False)
    for rel, content in staged_sources:
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)

    rows = [{"path": rel, "sha256": _sha256(content)} for rel, content in staged_sources]
    rows.sort(key=lambda row: row["path"])
    manifest = {
        "schema_version": 1,
        "method": "local staging from committed HEAD blob bytes; not published or installed",
        "source_head": head,
        "artifact_tree_sha256": _tree_digest(rows),
        "files": len(rows),
        "rows": rows,
    }
    (out / "DISTRIBUTION_MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")

    from verify_staged_distribution import verify

    failures = verify(out)
    if failures:
        raise ValueError("staged candidate did not verify: " + "; ".join(failures[:8]))
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    try:
        manifest = stage(args.out)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"staging refused/failed: {exc}", file=sys.stderr)
        return 2
    print(f"staged {manifest['files']} hashed files -> {Path(args.out).absolute()}")
    print(f"artifact tree sha256: {manifest['artifact_tree_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
