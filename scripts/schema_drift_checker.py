#!/usr/bin/env python3
"""
Schema Drift Checker - Construction ERP
=======================================
Verifies docs/ai/SCHEMA_FACTS.md against live Frappe DocType JSON files.

Usage:
    cd /home/mohamed/frappe-bench/apps/construction
    python3 scripts/schema_drift_checker.py
    python3 scripts/schema_drift_checker.py --update

Exit code:
    0 = schema facts match live DocType JSON
    1 = drift or invariant failure found
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCTYPES = REPO_ROOT / "construction" / "construction" / "doctype"
SCHEMA_FACTS = REPO_ROOT / "docs" / "ai" / "SCHEMA_FACTS.md"
OVERRIDE_ONLY_FOLDERS = {"journal_entry"}


def load_schema_files() -> list[dict]:
    schemas: list[dict] = []
    for path in sorted(DOCTYPES.glob("*/*.json")):
        data = json.loads(path.read_text())
        fields = []
        for field in data.get("fields", []):
            if not field.get("fieldname"):
                continue
            fields.append(
                {
                    "fieldname": field.get("fieldname", ""),
                    "fieldtype": field.get("fieldtype", ""),
                    "options": field.get("options", ""),
                    "reqd": int(field.get("reqd") or 0),
                    "unique": int(field.get("unique") or 0),
                    "hidden": int(field.get("hidden") or 0),
                    "read_only": int(field.get("read_only") or 0),
                }
            )
        schemas.append(
            {
                "folder": path.parent.name,
                "json_file": path.name,
                "doctype": data.get("name") or data.get("doctype") or path.parent.name,
                "module": data.get("module", ""),
                "istable": int(data.get("istable") or 0),
                "fields": fields,
            }
        )
    return schemas


def live_folders() -> set[str]:
    return {path.name for path in DOCTYPES.iterdir() if path.is_dir() and not path.name.startswith("_")}


def schema_folders(schemas: list[dict]) -> set[str]:
    return {schema["folder"] for schema in schemas}


def options_text(value: str) -> str:
    if not value:
        return ""
    return str(value).replace("\n", " / ")


def render_schema_facts(schemas: list[dict]) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    folders = live_folders()
    override_only = sorted(folders - schema_folders(schemas))

    lines = [
        "# Schema Facts - Verified DocType Schemas",
        "",
        "> Generated from live DocType JSON by `scripts/schema_drift_checker.py --update`.",
        "> Do not hand-edit field tables. Update the DocType JSON, then regenerate this file.",
        f"> Last verified: {generated_at}",
        "",
        "## Summary",
        "",
        f"- Schema-owning DocTypes: {len(schemas)}",
        f"- Override-only DocType folders: {len(override_only)}",
        f"- Source path: `construction/construction/doctype/*/*.json`",
        "",
        "| Folder | DocType | JSON | Fields | Notes |",
        "|---|---|---|---:|---|",
    ]

    for schema in schemas:
        note = "Child table" if schema["istable"] else ""
        lines.append(
            f"| `{schema['folder']}` | {schema['doctype']} | `{schema['json_file']}` | "
            f"{len(schema['fields'])} | {note} |"
        )

    for folder in override_only:
        note = "Override only; no local schema JSON"
        lines.append(f"| `{folder}` | {folder.replace('_', ' ').title()} | - | - | {note} |")

    lines.extend(
        [
            "",
            "## Critical Invariants",
            "",
            "- `BOQ Item` uses `cost_item` as a `Data` field and must not define `item_code` or `item_name`.",
            "- `BOQ Structure` must keep NestedSet fields: `lft`, `rgt`, `old_parent`, `is_group`, `wbs_code`.",
            "- `CostItem` uses `cost_item_code`; it must not be confused with ERPNext `Item.item_code`.",
            "- `PlantResource` uses `resource_code`, `equipment_type`, and hourly cost fields.",
            "- `journal_entry` is override-only in this app; its schema belongs to ERPNext core.",
            "",
            "## Field Snapshot",
            "",
        ]
    )

    for schema in schemas:
        lines.extend(
            [
                f"### {schema['doctype']} (`{schema['folder']}/{schema['json_file']}`) - {len(schema['fields'])} fields",
                "",
                "| Field | Type | Options | Flags |",
                "|---|---|---|---|",
            ]
        )
        for field in schema["fields"]:
            flags = []
            for flag in ("reqd", "unique", "hidden", "read_only"):
                if field[flag]:
                    flags.append(flag)
            flag_text = ", ".join(flags)
            lines.append(
                f"| `{field['fieldname']}` | {field['fieldtype']} | "
                f"{options_text(field['options'])} | {flag_text} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Validation Checklist",
            "",
            "- [ ] Run `python3 scripts/schema_drift_checker.py` before agent planning.",
            "- [ ] Run `python3 scripts/schema_drift_checker.py --update` only after reviewing intended schema changes.",
            "- [ ] Run `python3 scripts/ai_context_check.py` after schema facts are regenerated.",
            "",
        ]
    )
    return "\n".join(lines)


def validate_invariants(schemas: list[dict]) -> list[str]:
    errors: list[str] = []
    by_doctype = {schema["doctype"]: schema for schema in schemas}

    boq_item = by_doctype.get("BOQ Item")
    if not boq_item:
        errors.append("BOQ Item schema is missing")
    else:
        fields = {field["fieldname"]: field for field in boq_item["fields"]}
        if fields.get("cost_item", {}).get("fieldtype") != "Data":
            errors.append("BOQ Item.cost_item must exist and remain a Data field")
        for forbidden in ("item_code", "item_name"):
            if forbidden in fields:
                errors.append(f"BOQ Item must not define {forbidden}")

    boq_structure = by_doctype.get("BOQ Structure")
    if not boq_structure:
        errors.append("BOQ Structure schema is missing")
    else:
        fields = {field["fieldname"] for field in boq_structure["fields"]}
        for required in ("lft", "rgt", "old_parent", "is_group", "wbs_code"):
            if required not in fields:
                errors.append(f"BOQ Structure missing required field {required}")

    cost_item = by_doctype.get("CostItem")
    if not cost_item:
        errors.append("CostItem schema is missing")
    else:
        fields = {field["fieldname"] for field in cost_item["fields"]}
        if "cost_item_code" not in fields:
            errors.append("CostItem missing cost_item_code")

    plant_resource = by_doctype.get("PlantResource")
    if not plant_resource:
        errors.append("PlantResource schema is missing")
    else:
        fields = {field["fieldname"] for field in plant_resource["fields"]}
        for required in ("resource_code", "equipment_type", "ownership_cost_hourly"):
            if required not in fields:
                errors.append(f"PlantResource missing required field {required}")

    folders = live_folders()
    missing_expected_override = OVERRIDE_ONLY_FOLDERS - folders
    for folder in sorted(missing_expected_override):
        errors.append(f"Expected override-only folder missing: {folder}")

    unexpected_no_json = folders - schema_folders(schemas) - OVERRIDE_ONLY_FOLDERS
    for folder in sorted(unexpected_no_json):
        errors.append(f"Folder has no schema JSON and is not marked override-only: {folder}")

    return errors


def normalize_for_compare(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("> Last verified:"):
            lines.append("> Last verified: <ignored>")
        else:
            lines.append(line)
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify SCHEMA_FACTS.md against live DocType JSON")
    parser.add_argument("--update", action="store_true", help="Regenerate docs/ai/SCHEMA_FACTS.md")
    args = parser.parse_args()

    schemas = load_schema_files()
    rendered = render_schema_facts(schemas)
    invariant_errors = validate_invariants(schemas)
    if invariant_errors:
        print("Schema invariant failures:")
        for error in invariant_errors:
            print(f"  - {error}")
        return 1

    if args.update:
        SCHEMA_FACTS.write_text(rendered)
        print(f"Updated {SCHEMA_FACTS}")
        print(f"Schema-owning DocTypes: {len(schemas)}")
        print(f"Override-only folders: {len(live_folders() - schema_folders(schemas))}")
        return 0

    if not SCHEMA_FACTS.exists():
        print(f"Missing {SCHEMA_FACTS}. Run with --update to create it.")
        return 1

    current = SCHEMA_FACTS.read_text()
    if normalize_for_compare(current) != normalize_for_compare(rendered):
        print("Schema drift detected: docs/ai/SCHEMA_FACTS.md does not match live DocType JSON.")
        print("Run `python3 scripts/schema_drift_checker.py --update` after reviewing intended schema changes.")
        return 1

    print("Schema facts match live DocType JSON.")
    print(f"Schema-owning DocTypes: {len(schemas)}")
    print(f"Override-only folders: {len(live_folders() - schema_folders(schemas))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
