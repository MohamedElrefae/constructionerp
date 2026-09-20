#!/usr/bin/env python3
"""Validate critical Construction ERP facts before seeding AI memory."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    check_id: str
    name: str
    passed: bool
    details: list[str]


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}, got {type(value).__name__}")
    return value


def _check(check_id: str, name: str, callback) -> CheckResult:
    try:
        passed, details = callback()
        return CheckResult(check_id, name, passed, list(details))
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return CheckResult(check_id, name, False, [f"{type(exc).__name__}: {exc}"])


def _memory_files(root: Path) -> tuple[bool, list[str]]:
    details = []
    for filename in ("AGENTS.md", "SESSION_MEMORY.md"):
        path = root / filename
        if path.is_file():
            details.append(f"{filename} exists ({path.stat().st_size} bytes)")
        else:
            return False, [*details, f"{filename} missing at {path}"]
    return True, details


def _git_state(root: Path) -> tuple[bool, list[str]]:
    values = []
    for args, label in (
        (("rev-parse", "--abbrev-ref", "HEAD"), "Branch"),
        (("rev-parse", "--short", "HEAD"), "Latest commit"),
        (("rev-list", "--count", "HEAD"), "Total commits"),
    ):
        result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
        if result.returncode:
            diagnostic = result.stderr.strip() or result.stdout.strip() or "no output"
            return False, [f"{label} query failed: {diagnostic}"]
        values.append(f"{label}: {result.stdout.strip()}")
    return True, values


def _boq_item(root: Path) -> tuple[bool, list[str]]:
    data = _read_json(root / "construction" / "construction" / "doctype" / "boq_item" / "boq_item.json")
    names = {field["fieldname"] for field in data.get("fields", [])}
    details = []
    passed = True
    for field in ("cost_item", "structure"):
        if field in names:
            details.append(f"'{field}' field exists")
        else:
            passed = False
            details.append(f"'{field}' field MISSING")
    for field in ("item_code", "item_name"):
        if field not in names:
            details.append(f"'{field}' correctly ABSENT")
        else:
            passed = False
            details.append(f"'{field}' unexpectedly PRESENT")
    details.append(f"Total fields: {len(names)}")
    return passed, details


def _boq_structure(root: Path) -> tuple[bool, list[str]]:
    path = root / "construction" / "construction" / "doctype" / "boq_structure" / "boq_structure.json"
    names = {field["fieldname"] for field in _read_json(path).get("fields", [])}
    required = {"lft", "rgt", "old_parent", "is_group", "wbs_code"}
    missing = sorted(required - names)
    return not missing, [
        f"'{name}' field {'MISSING' if name in missing else 'exists'}" for name in sorted(required)
    ]


def _css(root: Path) -> tuple[bool, list[str]]:
    path = root / "construction" / "hooks.py"
    text = path.read_text(encoding="utf-8")
    start = text.find("app_include_css = [")
    end = text.find("]", start)
    block = text[start:end]
    expected = (
        "modern_theme.css",
        "scope_context.css",
        "vite_extensions.css",
        "vite_form_override.css",
        "vite_list_override.css",
        "vfc_sections.css",
    )
    details = [f"app_include_css has {block.count('.css')} CSS file registrations"]
    missing = [name for name in expected if name not in block]
    details.extend(f"'{name}' {'NOT registered' if name in missing else 'registered'}" for name in expected)
    return not missing, details


def _theme_api(root: Path) -> tuple[bool, list[str]]:
    text = (root / "construction" / "api" / "theme_api.py").read_text(encoding="utf-8")
    whitelist_count = text.count("@frappe.whitelist")
    function_count = sum(
        line.startswith("def ") or line.startswith("async def ") for line in text.splitlines()
    )
    details = [f"Whitelisted endpoints: {whitelist_count}", f"Total functions: {function_count}"]
    return whitelist_count == 17 and function_count == 33, details


def _patches(root: Path) -> tuple[bool, list[str]]:
    path = root / "construction" / "patches"
    expected = ("v6_0", "v6_1", "v6_2", "v6_3", "v6_4", "v6_5", "v6_6", "v6_7", "v6_8", "v7_1", "v7_2")
    missing = [name for name in expected if not (path / name).exists()]
    file_name = "v7_0_migrate_quantity_revisions.py"
    if not (path / file_name).exists():
        missing.append(file_name)
    return not missing, [
        "All expected migration paths exist" if not missing else f"Missing: {', '.join(missing)}"
    ]


def _registry(root: Path) -> tuple[bool, list[str]]:
    expected = {
        "boq_header",
        "boq_import_batch",
        "boq_item",
        "boq_item_stage",
        "boq_cost_analysis",
        "boq_cost_analysis_detail",
        "boq_quantity_revision",
        "boq_structure",
        "construction_settings",
        "construction_theme",
        "costitem",
        "direct_labor_designation",
        "form_layout_profile",
        "journal_entry",
        "modern_theme_settings",
        "plantresource",
        "resource_price_history",
        "scope_report_access_log",
        "user_desk_theme",
        "user_scope_context",
        "variation_order",
        "vo_line",
    }
    folders = root / "construction" / "construction" / "doctype"
    found = {entry.name for entry in folders.iterdir() if entry.is_dir() and not entry.name.startswith("_")}
    missing, extra = sorted(expected - found), sorted(found - expected)
    details = [
        f"All {len(expected)} expected DocTypes present" if not missing else f"Missing: {', '.join(missing)}"
    ]
    details.extend(f"Unexpected DocType folder found: '{name}'" for name in extra)
    return not missing and not extra, details


def _schema_drift(root: Path) -> tuple[bool, list[str]]:
    child = root / "scripts" / "schema_drift_checker.py"
    try:
        result = subprocess.run(
            [sys.executable, str(child)], cwd=root, text=True, capture_output=True, check=False
        )
    except OSError as exc:
        return False, [f"schema drift checker could not launch: {type(exc).__name__}: {exc}"]
    if result.returncode == 0:
        return True, ["docs/ai/SCHEMA_FACTS.md matches live DocType JSON"]
    diagnostic = result.stdout.strip() or result.stderr.strip() or "child exited without diagnostics"
    return False, [f"docs/ai/SCHEMA_FACTS.md drift detected: {diagnostic}"]


def _resource_schema(root: Path) -> tuple[bool, list[str]]:
    base = root / "construction" / "construction" / "doctype"
    expected = (
        ("costitem", "cost_item.json", "cost_item_code"),
        ("plantresource", "plant_resource.json", "resource_code"),
    )
    details = []
    passed = True
    for folder, filename, key in expected:
        names = {field["fieldname"] for field in _read_json(base / folder / filename).get("fields", [])}
        if key in names:
            details.append(f"{folder}: '{key}' field exists")
        else:
            passed = False
            details.append(f"{folder}: '{key}' field MISSING")
    return passed, details


def _adr(root: Path) -> tuple[bool, list[str]]:
    count = (root / "ADR.md").read_text(encoding="utf-8").count("## ADR-")
    return count >= 7, [f"ADR.md contains {count} ADRs"]


def run_checks(root: Path) -> list[CheckResult]:
    checks = (
        ("SCP-C1", "Core Memory Files", _memory_files),
        ("SCP-C2", "Git State", _git_state),
        ("SCP-C3", "BOQ Item Schema", _boq_item),
        ("SCP-C4", "BOQ Structure NestedSet", _boq_structure),
        ("SCP-C5", "CSS Registration", _css),
        ("SCP-C6", "Theme API Endpoints", _theme_api),
        ("SCP-C7", "Migration Patches", _patches),
        ("SCP-C8", "DocType Registry", _registry),
        ("SCP-C8B", "Schema Facts Drift", _schema_drift),
        ("SCP-C9", "CostItem and PlantResource", _resource_schema),
        ("SCP-C10", "Architecture Decisions", _adr),
    )
    return [
        _check(check_id, name, lambda callback=callback: callback(root))
        for check_id, name, callback in checks
    ]


def _report(results: list[CheckResult], root: Path, json_mode: bool) -> int:
    passed = sum(result.passed for result in results)
    failed = len(results) - passed
    if json_mode:
        payload = {
            "repo_root": str(root),
            "checks": [
                {
                    "id": result.check_id,
                    "name": result.name,
                    "status": "PASS" if result.passed else "FAIL",
                    "details": result.details,
                }
                for result in results
            ],
            "passed": passed,
            "failed": failed,
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        for result in results:
            print(f"\n{'-' * 60}\n{result.check_id}. {result.name}\n{'-' * 60}")
            for detail in result.details:
                print(f"  {'PASS' if result.passed else 'FAIL'}: {detail}")
        print(f"\nChecks passed: {passed}\nChecks failed: {failed}")
        print("\nALL CHECKS PASSED" if not failed else f"\n{failed} CHECK(S) FAILED")
    return 0 if not failed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Construction ERP AI context")
    parser.add_argument("--repo-root", type=Path, help="repository root to validate")
    parser.add_argument("--json", action="store_true", help="emit one JSON result object")
    args = parser.parse_args(argv)
    root = (args.repo_root or Path(__file__).resolve().parents[1]).resolve()
    return _report(run_checks(root), root, args.json)


if __name__ == "__main__":
    sys.exit(main())
