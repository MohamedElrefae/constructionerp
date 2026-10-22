#!/usr/bin/env python3
"""Fail-closed checker for the exact relaxed-permissions review ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RULE = "relaxed-permissions"


def target(
    path: str, start: tuple[int, int, int], end: tuple[int, int, int], index: int, fields: dict[str, Any]
) -> dict[str, Any]:
    return {
        "finding": {
            "check_id": RULE,
            "path": path,
            "start": dict(zip(("line", "col", "offset"), start, strict=True)),
            "end": dict(zip(("line", "col", "offset"), end, strict=True)),
        },
        "permission_index": index,
        "canonical_fields": fields,
    }


# Independently pinned inventory: editing the editable ledger cannot substitute
# another set of five paths/findings and make them appear approved.
PINNED_INVENTORY = [
    target(
        "construction/construction/doctype/construction_theme/construction_theme.json",
        (657, 5, 15769),
        (660, 6, 15813),
        2,
        {"read": 1, "role": "All"},
    ),
    target(
        "construction/construction/doctype/form_layout_profile/form_layout_profile.json",
        (131, 3, 2972),
        (134, 4, 3008),
        1,
        {"read": 1, "role": "All"},
    ),
    target(
        "construction/construction/doctype/modern_theme_settings/modern_theme_settings.json",
        (104, 5, 2782),
        (107, 6, 2826),
        1,
        {"read": 1, "role": "All"},
    ),
    target(
        "construction/construction/doctype/user_desk_theme/user_desk_theme.json",
        (232, 5, 7311),
        (239, 6, 7432),
        1,
        {"create": 1, "delete": 1, "if_owner": 1, "read": 1, "role": "All", "write": 1},
    ),
    target(
        "construction/construction/doctype/user_scope_context/user_scope_context.json",
        (110, 5, 2285),
        (116, 6, 2387),
        1,
        {"create": 1, "if_owner": 1, "read": 1, "role": "All", "write": 1},
    ),
]


def normalize_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("path must be a non-empty relative string")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or path.as_posix() != value
        or "\\" in value
    ):
        raise ValueError("path must be canonical and relative to candidateRoot")
    return value


def identity(record: dict[str, Any]) -> tuple[Any, ...]:
    path = normalize_path(record.get("path"))
    if not isinstance(record.get("check_id"), str) or not record["check_id"]:
        raise ValueError("check_id must be a non-empty string")
    points = []
    for name in ("start", "end"):
        point = record.get(name)
        if not isinstance(point, dict) or set(point) != {"line", "col", "offset"}:
            raise ValueError(f"{name} must contain exactly line, col, and offset")
        if any(type(point[k]) is not int for k in point):
            raise ValueError(f"{name} coordinates must be integers")
        if point["line"] < 1 or point["col"] < 1 or point["offset"] < 0:
            raise ValueError(f"{name} coordinates are out of range")
        points.append(point)
    start, end = points
    if end["offset"] < start["offset"] or (end["line"], end["col"]) < (start["line"], start["col"]):
        raise ValueError("finding span end precedes start")
    return (
        record["check_id"],
        path,
        start["line"],
        start["col"],
        start["offset"],
        end["line"],
        end["col"],
        end["offset"],
    )


def identity_record(record: dict[str, Any]) -> dict[str, Any]:
    return {k: record[k] for k in ("check_id", "path", "start", "end")}


def key_for_target(target_record: dict[str, Any]) -> tuple[Any, ...]:
    return identity(target_record["finding"])


def safe_file(root: Path, relative: Any) -> Path:
    normalized = normalize_path(relative)
    candidate = (root / normalized).resolve(strict=True)
    root = root.resolve(strict=True)
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise ValueError(f"reference escapes candidateRoot or is not a file: {normalized}")
    return candidate


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reviewed_source_manifest_sha256(entry: dict[str, Any]) -> str:
    """Hash the canonical source/guard/test path-and-digest manifest.

    The manifest intentionally excludes review_gate and decision fields, so it
    has no self-reference. File digests are separately checked against the
    candidate tree before this value can satisfy a REVIEWED gate.
    """
    finding = entry.get("finding")
    if not isinstance(finding, dict):
        raise ValueError("finding must be an object")
    source_path = normalize_path(finding.get("path"))
    source_sha = entry.get("source_sha256")
    if not isinstance(source_sha, str) or not SHA256_RE.fullmatch(source_sha):
        raise ValueError("source_sha256 must be a lowercase SHA-256")

    by_path = {source_path: source_sha}
    for ref_name in ("guards", "tests"):
        refs = entry.get(ref_name)
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"{ref_name} must be a non-empty file-reference array")
        for ref in refs:
            if not isinstance(ref, dict):
                raise ValueError(f"{ref_name} reference must be an object")
            path = normalize_path(ref.get("path"))
            digest = ref.get("sha256")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                raise ValueError(f"{ref_name} reference sha256 must be a lowercase SHA-256")
            if path in by_path and by_path[path] != digest:
                raise ValueError(f"conflicting digests for manifest path: {path}")
            by_path[path] = digest

    records = [{"path": path, "sha256": digest} for path, digest in sorted(by_path.items())]
    encoded = json.dumps(records, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_permission_fields_sha256(fields: dict[str, Any]) -> str:
    encoded = json.dumps(fields, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate(
    raw: Any,
    scanner_exit: int,
    ledger: Any,
    candidate_root: Path,
    inventory: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate a successful `semgrep scan --json` run (without `--error`)."""
    errors: list[str] = []
    unresolved: list[dict[str, Any]] = []
    reviewed: set[tuple[Any, ...]] = set()
    production_inventory = inventory is None
    pinned = PINNED_INVENTORY if production_inventory else inventory

    # Semgrep's normal JSON scan exits 0 when findings exist. `--error` is not
    # supported here: a nonzero scanner code is an execution failure, not a finding signal.
    if type(scanner_exit) is not int or scanner_exit != 0:
        errors.append(
            f"scanner exit must be 0 (got {scanner_exit!r}); run semgrep scan --json without --error"
        )
    if not isinstance(raw, dict) or not isinstance(raw.get("results"), list):
        errors.append("Semgrep JSON must be an object with a results array")
        raw_results = []
    else:
        raw_results = raw["results"]
    scanner_errors = raw.get("errors") if isinstance(raw, dict) else None
    if not isinstance(scanner_errors, list):
        errors.append("Semgrep JSON errors must be an array")
        scanner_errors = []
    elif scanner_errors:
        errors.append(f"Semgrep reported {len(scanner_errors)} scanner error(s)")

    if not isinstance(ledger, dict) or ledger.get("schema_version") != 1:
        errors.append("ledger schema_version must be 1")
        ledger = {}
    targets, entries = ledger.get("required_targets"), ledger.get("entries")
    if not isinstance(targets, list) or not isinstance(entries, list):
        errors.append("ledger must contain required_targets and entries arrays")
        targets, entries = [], []

    try:
        pinned_by_key = {key_for_target(item): item for item in pinned}
        if len(pinned_by_key) != len(pinned) or (production_inventory and len(pinned_by_key) != 5):
            errors.append("pinned inventory must contain exactly five unique findings")
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(f"invalid pinned inventory: {exc}")
        pinned_by_key = {}

    target_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, item in enumerate(targets):
        try:
            key = identity(item)
            if key in target_by_key:
                errors.append(f"duplicate required target at index {index}")
            target_by_key[key] = item
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"invalid required target at index {index}: {exc}")
    if target_by_key.keys() != pinned_by_key.keys():
        errors.append("ledger target inventory differs from the independently pinned five findings")

    entry_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        try:
            if not isinstance(entry, dict) or not isinstance(entry.get("finding"), dict):
                raise ValueError("entry finding must be an object")
            key = identity(entry["finding"])
            if key in entry_by_key:
                errors.append(f"duplicate ledger entry at index {index}")
            entry_by_key[key] = entry
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"invalid ledger entry at index {index}: {exc}")
    if target_by_key.keys() - entry_by_key.keys():
        errors.append(
            f"missing {len(target_by_key.keys() - entry_by_key.keys())} required ledger entry/entries"
        )
    if entry_by_key.keys() - target_by_key.keys():
        errors.append(f"{len(entry_by_key.keys() - target_by_key.keys())} stale/extra ledger entry/entries")

    raw_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, finding in enumerate(raw_results):
        try:
            if not isinstance(finding, dict):
                raise ValueError("finding must be an object")
            key = identity(finding)
            if key in raw_by_key:
                errors.append(f"duplicate Semgrep finding identity at result index {index}")
            raw_by_key[key] = finding
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"invalid Semgrep finding at result index {index}: {exc}")
    absent_targets = target_by_key.keys() - raw_by_key.keys()
    if absent_targets:
        errors.append(f"{len(absent_targets)} pinned finding(s) absent from scan (stale target)")

    bad_entries: dict[tuple[Any, ...], list[str]] = {}
    for key, entry in entry_by_key.items():
        problems: list[str] = []
        finding = raw_by_key.get(key)
        pinned_item = pinned_by_key.get(key)
        if finding is None:
            problems.append("stale ledger entry: no exact finding in raw scan")
        if pinned_item is None:
            problems.append("entry is outside independently pinned inventory")
        else:
            permission = entry.get("permission_record")
            expected_perm = {
                "document_path": pinned_item["finding"]["path"],
                "index": pinned_item["permission_index"],
                "canonical_fields_sha256": canonical_permission_fields_sha256(
                    pinned_item["canonical_fields"]
                ),
            }
            if permission != expected_perm:
                problems.append("permission record index/canonical fields differ from pinned inventory")
        if finding is not None:
            rel = key[1]
            try:
                source = safe_file(candidate_root, rel)
                if entry.get("source_sha256") != sha256_file(source):
                    problems.append("source SHA-256 mismatch")
                if pinned_item is not None:
                    doc = json.loads(source.read_text(encoding="utf-8"))
                    records = doc.get("permissions")
                    pi = pinned_item["permission_index"]
                    if (
                        not isinstance(records, list)
                        or pi >= len(records)
                        or records[pi] != pinned_item["canonical_fields"]
                    ):
                        problems.append(
                            "candidate DocType permission record no longer matches pinned index/fields"
                        )
                elif not isinstance(json.loads(source.read_text(encoding="utf-8")).get("permissions"), list):
                    problems.append("finding source is not a DocType permissions JSON")
            except (ValueError, OSError, json.JSONDecodeError, TypeError) as exc:
                problems.append(f"invalid source reference: {exc}")

        for ref_name in ("guards", "tests"):
            refs = entry.get(ref_name)
            if not isinstance(refs, list) or not refs:
                problems.append(f"{ref_name} must be a non-empty file-reference array")
                continue
            for ref_index, ref in enumerate(refs):
                try:
                    if not isinstance(ref, dict):
                        raise ValueError("reference must be an object")
                    ref_file = safe_file(candidate_root, ref.get("path"))
                    digest = ref.get("sha256")
                    if (
                        not isinstance(digest, str)
                        or not SHA256_RE.fullmatch(digest)
                        or sha256_file(ref_file) != digest
                    ):
                        problems.append(f"{ref_name}[{ref_index}] file SHA-256 mismatch")
                except (ValueError, OSError) as exc:
                    problems.append(f"invalid {ref_name}[{ref_index}] reference: {exc}")

        if entry.get("status") == "REVIEWED":
            if entry.get("decision") != "ACCEPT":
                problems.append("REVIEWED requires decision ACCEPT")
            gate = entry.get("review_gate")
            if not isinstance(gate, dict) or not all(
                gate.get(k) for k in ("parent_review_id", "combined_qualification_id", "native_rest_run_id")
            ):
                problems.append(
                    "REVIEWED requires parent review, local qualification, and native REST run references"
                )
            else:
                if not SHA256_RE.fullmatch(str(gate.get("combined_qualification_sha256", ""))):
                    problems.append("REVIEWED requires combined local qualification SHA-256")
                try:
                    manifest_sha = reviewed_source_manifest_sha256(entry)
                    if gate.get("reviewed_source_manifest_sha256") != manifest_sha:
                        problems.append("REVIEWED source manifest SHA-256 mismatch")
                except (ValueError, TypeError, KeyError) as exc:
                    problems.append(f"invalid REVIEWED source manifest: {exc}")
                if not SHA256_RE.fullmatch(str(gate.get("native_rest_log_sha256", ""))):
                    problems.append("REVIEWED requires native REST log SHA-256")
            test_paths = {ref.get("path") for ref in entry.get("tests", []) if isinstance(ref, dict)}
            if "construction/tests/test_native_security_rest_authorization.py" not in test_paths:
                problems.append("REVIEWED requires the native REST authorization test source reference")
        elif entry.get("status") != "PENDING":
            problems.append("status must be PENDING or REVIEWED")
        elif entry.get("decision") is not None:
            problems.append("PENDING entry must have decision null")

        if problems:
            bad_entries[key] = problems

    for key, finding in raw_by_key.items():
        entry = entry_by_key.get(key)
        if entry is None:
            unresolved.append(
                {
                    "finding": identity_record(finding),
                    "reason": "unreviewed finding has no exact ledger entry",
                }
            )
        elif (
            entry.get("status") == "REVIEWED"
            and key not in bad_entries
            and key in pinned_by_key
            and not errors
        ):
            reviewed.add(key)
        else:
            reasons = bad_entries.get(key, ["manual-review entry is PENDING"])
            if errors and not bad_entries.get(key):
                reasons = ["global validation failed; see ledger_errors"]
            unresolved.append({"finding": identity_record(finding), "reason": "; ".join(reasons)})

    for key in absent_targets:
        entry = entry_by_key.get(key)
        if entry:
            unresolved.append(
                {
                    "finding": identity_record(entry["finding"]),
                    "reason": "pinned finding missing from raw scan",
                }
            )

    return {
        "raw_findings_total": len(raw_results),
        "reviewed_findings": len(reviewed),
        "unresolved_findings": len(unresolved),
        "unresolved": unresolved,
        "ledger_errors": errors,
        "scanner_errors": scanner_errors,
        "exit_code": 0 if not errors and not unresolved else 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-semgrep-json", required=True, type=Path)
    parser.add_argument("--scanner-exit", required=True, type=int)
    parser.add_argument("--review-ledger", required=True, type=Path)
    parser.add_argument("--candidate-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = json.loads(args.raw_semgrep_json.read_text(encoding="utf-8"))
        ledger = json.loads(args.review_ledger.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"cannot parse input: {exc}", "exit_code": 1}))
        return 1
    report = validate(raw, args.scanner_exit, ledger, args.candidate_root)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
