"""Verify an already-staged customer tree without modifying it."""

import argparse
import csv
import hashlib
import json
import os
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath

from distribution_policy import LICENSE_CANDIDATES, REQUIRED_CUSTOMER_FILES, is_customer_path, never_ships

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s][^)\s]*)\)")
MANIFEST = "DISTRIBUTION_MANIFEST.json"
REQUIRED = REQUIRED_CUSTOMER_FILES | frozenset(
    {
        "construction/construction/sidebar/construction_home/construction_home.json",
        "construction/hooks.py",
        "construction/api/construction_reports.py",
        "construction/overrides/boq_permissions.py",
        "construction/overrides/file_permissions.py",
        "construction/overrides/file_download.py",
        "construction/public/js/vite_layout_controls.js",
        "construction/data/translations/approved_ar_overrides.csv",
        "construction/locale/ar.po",
        "construction/data/glossary/egyptian_construction_glossary.json",
    }
)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_digest(rows):
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(row["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _validate_released_content_references(csv_path, payload_paths):
    """Require each active CSV content reference to resolve inside the package."""
    failures = []
    found_active_ref = False
    try:
        with csv_path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            required_columns = {"release_status", "decision_ref"}
            if not reader.fieldnames or not required_columns <= set(reader.fieldnames):
                return ["translation CSV is missing release_status or decision_ref columns"]
            for row_number, row in enumerate(reader, start=2):
                if (row.get("release_status") or "").strip().casefold() != "released":
                    continue
                for ref in (row.get("decision_ref") or "").split(";"):
                    ref = ref.strip()
                    if not ref.startswith("content:"):
                        continue
                    found_active_ref = True
                    target = ref[len("content:") :]
                    path = PurePosixPath(target)
                    if (
                        not target
                        or "\\" in target
                        or path.is_absolute()
                        or any(part in {"", ".", ".."} for part in path.parts)
                        or posixpath.normpath(target) != target
                    ):
                        failures.append(f"CSV row {row_number} has a noncanonical content reference: {ref}")
                        continue
                    if not is_customer_path(target) or never_ships(target):
                        failures.append(f"CSV row {row_number} references noncustomer content: {target}")
                    elif target not in payload_paths:
                        failures.append(f"CSV row {row_number} references missing content: {target}")
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return [f"translation CSV content references could not be read: {exc}"]

    if not found_active_ref:
        failures.append("translation CSV has no Released content references")
    return failures


def verify(stage):
    stage = Path(stage).absolute()
    failures = []
    if not stage.is_dir() or stage.is_symlink():
        return [f"staged directory missing or is a symlink: {stage}"]

    actual = {}
    for path in stage.rglob("*"):
        rel = path.relative_to(stage).as_posix()
        if path.is_symlink():
            failures.append(f"symlink is not permitted in staged tree: {rel}")
        elif path.is_file():
            actual[rel] = path

    if MANIFEST not in actual:
        return [*failures, f"required manifest missing: {MANIFEST}"]

    payload_paths = set(actual) - {MANIFEST}
    forbidden = sorted(path for path in payload_paths if never_ships(path))
    if forbidden:
        failures.append(f"never-ship paths present ({len(forbidden)}): {forbidden[:12]}")

    unexpected = sorted(path for path in payload_paths if not is_customer_path(path))
    if unexpected:
        failures.append(f"paths outside customer allowlist ({len(unexpected)}): {unexpected[:12]}")

    missing = sorted(set(REQUIRED) - payload_paths)
    if missing:
        failures.append(f"required files missing: {missing}")

    licenses = sorted(path for path in payload_paths if path in LICENSE_CANDIDATES)
    if not licenses or not any(actual[path].stat().st_size > 0 for path in licenses):
        failures.append("at least one nonempty LICENSE, LICENSE.txt, or license.txt file is required")

    csv_ref_path = "construction/data/translations/approved_ar_overrides.csv"
    if csv_ref_path in actual:
        failures.extend(_validate_released_content_references(actual[csv_ref_path], payload_paths))

    broken = []
    for rel in sorted(payload_paths):
        if not rel.endswith(".md"):
            continue
        try:
            text = actual[rel].read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(rel), target))
            if resolved not in payload_paths and not (stage / resolved).is_dir():
                broken.append(f"{rel} -> {target}")
    if broken:
        failures.append(f"broken relative Markdown links ({len(broken)}): {broken[:12]}")

    try:
        manifest = json.loads(actual[MANIFEST].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [*failures, f"manifest is unreadable: {exc}"]

    if not isinstance(manifest, dict):
        return [*failures, "manifest must be a JSON object"]
    rows = manifest.get("rows")
    if not isinstance(rows, list):
        return [*failures, "manifest rows must be a list"]

    paths = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            failures.append("manifest rows contain malformed paths")
            continue
        paths.append(row["path"])
    if len(paths) != len(rows) or len(paths) != len(set(paths)):
        failures.append("manifest rows contain malformed or duplicate paths")
    if set(paths) != payload_paths:
        failures.append("manifest path inventory does not match staged payload")

    valid_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rel = row.get("path")
        expected = row.get("sha256")
        if (
            not isinstance(rel, str)
            or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
        ):
            failures.append(f"invalid manifest row: {row!r}")
            continue
        if rel in actual and _sha256(actual[rel]) != expected:
            failures.append(f"sha256 mismatch: {rel}")
        valid_rows.append(row)

    valid_rows.sort(key=lambda row: row["path"])
    if manifest.get("schema_version") != 1:
        failures.append("unsupported manifest schema_version")
    if manifest.get("files") != len(payload_paths):
        failures.append("manifest file count does not match staged payload")
    if manifest.get("artifact_tree_sha256") != _tree_digest(valid_rows):
        failures.append("manifest artifact tree digest is invalid")
    if not isinstance(manifest.get("source_head"), str) or not re.fullmatch(
        r"[0-9a-f]{40,64}", manifest["source_head"]
    ):
        failures.append("manifest source_head is missing or malformed")

    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="/tmp/opencode/customer-dist")
    args = parser.parse_args()
    failures = verify(args.dir)
    if failures:
        print("STAGED VERIFICATION FAILED")
        for failure in failures:
            print(" -", failure)
        return 1
    print("STAGED VERIFICATION PASSED: allowlist, exclusions, links, and file hashes verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
