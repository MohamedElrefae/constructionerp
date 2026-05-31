#!/usr/bin/env python3
"""
AI Context Check — Construction ERP
====================================
Validates critical facts against live repo files before seeding AI memory.

Run this script before:
- Seeding MCP memory databases
- Generating skill files
- Starting a new agent session after significant repo changes

Usage:
    cd /home/mohamed/frappe-bench/apps/construction
    python3 scripts/ai_context_check.py

Exit code:
    0 = all checks passed
    1 = one or more checks failed
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

REPO_ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
CONSTRUCTION_PKG = REPO_ROOT / "construction"
DOCTYPES = CONSTRUCTION_PKG / "construction" / "doctype"

CHECKS_PASSED = 0
CHECKS_FAILED = 0


def ok(msg: str):
    global CHECKS_PASSED
    CHECKS_PASSED += 1
    print(f"  ✅ {msg}")


def fail(msg: str):
    global CHECKS_FAILED
    CHECKS_FAILED += 1
    print(f"  ❌ {msg}")


def info(msg: str):
    print(f"  ℹ️  {msg}")


def section(title: str):
    print(f"\n{'─' * 60}")
    print(title)
    print("─" * 60)


# ═══════════════════════════════════════════════════════════════
# Check 1: Core memory files exist
# ═══════════════════════════════════════════════════════════════

section("1. Core Memory Files")

for fname in ("AGENTS.md", "SESSION_MEMORY.md"):
    fpath = REPO_ROOT / fname
    if fpath.exists():
        ok(f"{fname} exists ({fpath.stat().st_size} bytes)")
    else:
        fail(f"{fname} missing at {fpath}")

# ═══════════════════════════════════════════════════════════════
# Check 2: Git state
# ═══════════════════════════════════════════════════════════════

section("2. Git State")

try:
    branch = (
        subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        )
        .strip()
    )
    commit = (
        subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        )
        .strip()
    )
    commit_count = (
        subprocess.check_output(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        )
        .strip()
    )
    ok(f"Branch: {branch}")
    ok(f"Latest commit: {commit}")
    ok(f"Total commits: {commit_count}")
except Exception as e:
    fail(f"Git check failed: {e}")

# ═══════════════════════════════════════════════════════════════
# Check 3: BOQ Item Schema (Critical)
# ═══════════════════════════════════════════════════════════════

section("3. BOQ Item Schema (Critical)")

boq_item_json = DOCTYPES / "boq_item" / "boq_item.json"
try:
    with open(boq_item_json, "r") as f:
        boq_item = json.load(f)
    fieldnames = {f["fieldname"] for f in boq_item.get("fields", [])}

    if "cost_item" in fieldnames:
        ok("'cost_item' field exists")
    else:
        fail("'cost_item' field MISSING")

    if "item_code" not in fieldnames:
        ok("'item_code' correctly ABSENT")
    else:
        fail("'item_code' unexpectedly PRESENT — schema changed!")

    if "item_name" not in fieldnames:
        ok("'item_name' correctly ABSENT")
    else:
        fail("'item_name' unexpectedly PRESENT — schema changed!")

    if "structure" in fieldnames:
        ok("'structure' field exists")
    else:
        fail("'structure' field MISSING")

    info(f"Total fields: {len(fieldnames)}")
except Exception as e:
    fail(f"BOQ Item schema check failed: {e}")

# ═══════════════════════════════════════════════════════════════
# Check 4: BOQ Structure NestedSet
# ═══════════════════════════════════════════════════════════════

section("4. BOQ Structure NestedSet")

boq_struct_json = DOCTYPES / "boq_structure" / "boq_structure.json"
try:
    with open(boq_struct_json, "r") as f:
        boq_struct = json.load(f)
    fieldnames = {f["fieldname"] for f in boq_struct.get("fields", [])}
    required = {"lft", "rgt", "old_parent", "is_group", "wbs_code"}
    for req in required:
        if req in fieldnames:
            ok(f"'{req}' field exists")
        else:
            fail(f"'{req}' field MISSING")
except Exception as e:
    fail(f"BOQ Structure schema check failed: {e}")

# ═══════════════════════════════════════════════════════════════
# Check 5: CSS Registration in hooks.py
# ═══════════════════════════════════════════════════════════════

section("5. CSS Registration in hooks.py")

hooks_py = CONSTRUCTION_PKG / "hooks.py"
try:
    hooks_text = hooks_py.read_text()
    css_list_start = hooks_text.find("app_include_css = [")
    css_list_end = hooks_text.find("]", css_list_start)
    css_block = hooks_text[css_list_start:css_list_end]

    registered_css = [line.strip() for line in css_block.splitlines() if ".css" in line]
    ok(f"app_include_css has {len(registered_css)} CSS file registrations")

    expected_css = [
        "modern_theme.css",
        "scope_context.css",
        "vite_extensions.css",
        "vite_form_override.css",
        "vite_list_override.css",
        "vfc_sections.css",
    ]
    for expected in expected_css:
        if expected in css_block:
            ok(f"'{expected}' registered")
        else:
            fail(f"'{expected}' NOT registered in app_include_css")
except Exception as e:
    fail(f"CSS registration check failed: {e}")

# ═══════════════════════════════════════════════════════════════
# Check 6: Theme API Endpoint Count
# ═══════════════════════════════════════════════════════════════

section("6. Theme API Endpoints")

theme_api = CONSTRUCTION_PKG / "api" / "theme_api.py"
try:
    text = theme_api.read_text()
    whitelist_count = text.count("@frappe.whitelist")
    func_count = len([line for line in text.splitlines() if line.startswith("def ") or line.startswith("async def ")])
    if whitelist_count == 17:
        ok(f"Whitelisted endpoints: {whitelist_count}")
    else:
        fail(f"Whitelisted endpoints: {whitelist_count} (expected 17)")
    if func_count == 34:
        ok(f"Total functions: {func_count}")
    else:
        info(f"Total functions: {func_count} (expected 34 — may have changed)")
except Exception as e:
    fail(f"Theme API check failed: {e}")

# ═══════════════════════════════════════════════════════════════
# Check 7: Patches Directory
# ═══════════════════════════════════════════════════════════════

section("7. Migration Patches")

patches_dir = CONSTRUCTION_PKG / "patches"
try:
    patch_versions = sorted(
        d.name for d in patches_dir.iterdir()
        if d.is_dir() and d.name.startswith("v6_")
    )
    expected = ["v6_0", "v6_1", "v6_2", "v6_3", "v6_4", "v6_5", "v6_6"]
    for exp in expected:
        if (patches_dir / exp).exists():
            ok(f"Patch dir '{exp}' exists")
        else:
            fail(f"Patch dir '{exp}' MISSING")
except Exception as e:
    fail(f"Patch check failed: {e}")

# ═══════════════════════════════════════════════════════════════
# Check 8: DocType Registry Completeness
# ═══════════════════════════════════════════════════════════════

section("8. DocType Registry")

expected_doctypes = {
    "boq_header",
    "boq_item",
    "boq_item_stage",
    "boq_structure",
    "construction_settings",
    "construction_theme",
    "costitem",
    "direct_labor_designation",
    "form_layout_profile",
    "journal_entry",
    "modern_theme_settings",
    "plantresource",
    "user_desk_theme",
    "user_scope_context",
}

try:
    found = {d.name for d in DOCTYPES.iterdir() if d.is_dir() and not d.name.startswith("_")}
    missing = expected_doctypes - found
    extra = found - expected_doctypes
    if not missing:
        ok(f"All {len(expected_doctypes)} expected DocTypes present")
    else:
        for m in missing:
            fail(f"DocType '{m}' MISSING")
    if extra:
        for e in extra:
            info(f"Extra DocType found: '{e}'")
except Exception as e:
    fail(f"DocType registry check failed: {e}")

# ═══════════════════════════════════════════════════════════════
# Check 9: CostItem & PlantResource Schema
# ═══════════════════════════════════════════════════════════════

section("9. CostItem & PlantResource")

for dt_name, json_name, key_field in [
    ("costitem", "cost_item.json", "cost_item_code"),
    ("plantresource", "plant_resource.json", "resource_code"),
]:
    try:
        path = DOCTYPES / dt_name / json_name
        with open(path, "r") as f:
            data = json.load(f)
        fieldnames = {f["fieldname"] for f in data.get("fields", [])}
        if key_field in fieldnames:
            ok(f"{dt_name}: '{key_field}' field exists")
        else:
            fail(f"{dt_name}: '{key_field}' field MISSING")
    except Exception as e:
        fail(f"{dt_name} schema check failed: {e}")

# ═══════════════════════════════════════════════════════════════
# Check 10: ADR.md
# ═══════════════════════════════════════════════════════════════

section("10. Architecture Decisions")

adr_md = REPO_ROOT / "ADR.md"
try:
    text = adr_md.read_text()
    adr_count = text.count("## ADR-")
    if adr_count >= 7:
        ok(f"ADR.md contains {adr_count} ADRs")
    else:
        fail(f"ADR.md contains only {adr_count} ADRs (expected 7+)")
except Exception as e:
    fail(f"ADR check failed: {e}")

# ═══════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print("SUMMARY")
print("=" * 60)
print(f"Checks passed: {CHECKS_PASSED}")
print(f"Checks failed: {CHECKS_FAILED}")

if CHECKS_FAILED == 0:
    print("\n✅ ALL CHECKS PASSED — Safe to seed AI memory.")
    sys.exit(0)
else:
    print(f"\n❌ {CHECKS_FAILED} CHECK(S) FAILED — Review failures before seeding memory.")
    sys.exit(1)
