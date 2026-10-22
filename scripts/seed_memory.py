#!/usr/bin/env python3
"""Seed MemoryGraph with Construction ERP project knowledge.

Usage:
    python3 scripts/seed_memory.py

This generates scripts/seed_memory.json and imports it into MemoryGraph.
Prerequisite: memorygraph must be installed (pipx install memorygraphMCP).
"""

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
OUTPUT_JSON = REPO_ROOT / "scripts" / "seed_memory.json"

MEMORIES = [
    {
        "id": str(uuid.uuid4()),
        "type": "project",
        "title": "Construction ERP — Project Architecture Overview",
        "content": (
            "Construction ERP is a Frappe/ERPNext app at /home/mohamed/frappe-bench/apps/construction. "
            "Four main systems: (1) Theme System — 22 CSS files, 14884 lines, "
            "54-token CSS variable system, server-side resolution via boot_session hook. "
            "(2) Scope Context — multi-dim access control via permission_query_conditions hook, "
            "NestedSet lft/rgt, Redis 5-min TTL. "
            "(3) BOQ System — Header -> Structure(NestedSet) -> Item, 12 service modules, "
            "9 whitelisted API endpoints in boq_api.py. "
            "(4) Form Layout Engine (VFC) — Form Layout Profile DocType + JS re-parenting at runtime."
        ),
        "summary": "Frappe app with theme, scope, BOQ, and layout engine systems",
        "tags": ["construction", "architecture", "frappe", "overview"],
        "importance": 0.95,
        "confidence": 1.0,
        "context": {
            "project_path": str(REPO_ROOT),
            "git_branch": "feature/vite-ui-v1",
            "languages": ["python", "javascript", "css"],
            "frameworks": ["frappe", "erpnext"],
        },
    },
    {
        "id": str(uuid.uuid4()),
        "type": "code_pattern",
        "title": "BOQ Item DocType Schema — CRITICAL: No item_code field",
        "content": (
            "BOQ Item fields: structure (Link->BOQ Structure), boq_header, "
            "item_type (Measured Work/Provisional Sum/Prime Cost/Daywork/Contingency/TBD), "
            "cost_item (Data — free text, NOT Link->Item), owner_page, owner_ref_no, owner_file_ref, "
            "quantity (Float), unit (Link->UOM), factor (Float), has_stages (Check), "
            "est_unit_cost (Currency), est_unit_price (Currency), contract_unit_price (Currency), "
            "line_total (Currency), overhead_pct (Percent), profit_pct (Percent), "
            "overhead_amount, profit_amount, calculated_sell_price, est_line_total, "
            "quantity_executed, quantity_certified. "
            "WARNING: BOQ Item has NO item_code or item_name. It is a specification line, not an ERPNext Item link."
        ),
        "summary": "BOQ Item uses cost_item (Data), not item_code. Never assume ERPNext Item link.",
        "tags": ["construction", "boq", "doctype", "schema", "critical"],
        "importance": 0.95,
        "confidence": 1.0,
        "context": {
            "project_path": str(REPO_ROOT),
            "files_involved": ["construction/construction/doctype/boq_item/boq_item.json"],
        },
    },
    {
        "id": str(uuid.uuid4()),
        "type": "fix",
        "title": "CSS Registration Rule — Only 6 files in app_include_css",
        "content": (
            "Only 6 CSS files are registered in hooks.py app_include_css: "
            "modern_theme.css, scope_context.css, vite_extensions.css, "
            "vite_form_override.css, vite_list_override.css, vfc_sections.css. "
            "The remaining 16 CSS files are generated themes, login/email/print themes, or test files. "
            "After adding a new production CSS file: (1) add path to app_include_css in hooks.py, "
            "(2) increment the ?v= version param to bust browser cache, "
            "(3) run bench build or bench clear-cache."
        ),
        "summary": "Only 6 CSS files are registered. Generated/special files load conditionally.",
        "tags": ["css", "frappe", "hooks", "gotcha", "critical"],
        "importance": 0.9,
        "confidence": 1.0,
        "context": {
            "project_path": str(REPO_ROOT),
            "files_involved": ["construction/hooks.py"],
        },
    },
    {
        "id": str(uuid.uuid4()),
        "type": "fix",
        "title": "TimestampMismatchError Prevention for Theme Writes",
        "content": (
            "Frappe's User DocType uses optimistic locking. Concurrent theme switches from "
            "multiple tabs cause TimestampMismatchError. "
            "FIX: Use frappe.db.set_value('User Desk Theme', user, 'theme', value, update_modified=False) "
            "instead of doc.save() for high-frequency user preference updates. "
            "This bypasses Frappe validation hooks but avoids locking conflicts."
        ),
        "summary": "Use frappe.db.set_value with update_modified=False for theme hot-path updates",
        "tags": ["frappe", "theme", "gotcha", "locking"],
        "importance": 0.85,
        "confidence": 1.0,
        "context": {
            "project_path": str(REPO_ROOT),
            "files_involved": ["construction/api/theme_api.py"],
        },
    },
    {
        "id": str(uuid.uuid4()),
        "type": "code_pattern",
        "title": "Scope Context Query Injection Pattern",
        "content": (
            "add_scope_conditions() in overrides/scope_query.py injects SQL WHERE clauses "
            "via permission_query_conditions hook. Uses NestedSet lft/rgt for cost center "
            "descendant expansion. Column-existence guards prevent SQL errors on doctypes "
            "without scope columns. Administrator bypasses all filters. "
            "Redis cache (5-min TTL) for scope hierarchy. "
            "ALWAYS test scope features as non-admin user — admin bypasses all filters."
        ),
        "summary": "Permission query injection with NestedSet, column guards, admin bypass, Redis cache",
        "tags": ["construction", "scope", "security", "frappe"],
        "importance": 0.9,
        "confidence": 1.0,
        "context": {
            "project_path": str(REPO_ROOT),
            "files_involved": ["construction/overrides/scope_query.py", "construction/boot.py"],
        },
    },
]


def generate_json():
    """Generate the seed JSON file."""
    payload = {
        "format_version": "2.0",
        "export_version": "1.0",
        "export_date": datetime.now(timezone.utc).isoformat(),
        "backend_type": "sqlite",
        "memory_count": len(MEMORIES),
        "relationship_count": 0,
        "memories": MEMORIES,
        "relationships": [],
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Generated: {OUTPUT_JSON} ({len(MEMORIES)} memories)")


def import_to_memorygraph():
    """Import the generated JSON into MemoryGraph."""
    result = subprocess.run(
        ["memorygraph", "import", "--format", "json", "--input", str(OUTPUT_JSON)],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        raise RuntimeError("Import failed")
    print("Import complete.")


def verify():
    """Run health check to confirm memories were stored."""
    result = subprocess.run(
        ["memorygraph", "--health"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)


if __name__ == "__main__":
    generate_json()
    import_to_memorygraph()
    verify()
