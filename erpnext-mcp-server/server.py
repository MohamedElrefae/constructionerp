#!/usr/bin/env python3
"""
ERPNext MCP Server — Construction ERP Read-Only Bridge
=======================================================
Exposes Construction ERP DocTypes as MCP tools for agent querying.

Safety rules:
- Read-only ONLY. No writes, no deletes, no migrations.
- DocType allowlist enforced on all generic queries.
- SQL is parsed to block INSERT/UPDATE/DELETE/DROP/ALTER.
- All queries logged to logs/ai_mcp_audit.log.

Usage (launched by MCP client agent):
    /home/mohamed/frappe-bench/env/bin/python \
        /home/mohamed/frappe-bench/apps/construction/erpnext-mcp-server/server.py

Prerequisites:
- Run inside Frappe bench environment (needs frappe import)
- mcp package installed in bench venv
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

REPO_ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
BENCH_PATH = Path("/home/mohamed/frappe-bench")
SITES_PATH = BENCH_PATH / "sites"
SITE_NAME = "v16.localhost"
AUDIT_LOG = REPO_ROOT / "logs" / "ai_mcp_audit.log"

# DocTypes that are safe to query via generic tools
ALLOWLIST = {
    "BOQ Header",
    "BOQ Item",
    "BOQ Structure",
    "BOQ Item Stage",
    "CostItem",
    "PlantResource",
    "User Scope Context",
    "Construction Theme",
    "User Desk Theme",
    "Modern Theme Settings",
    "Form Layout Profile",
    "Construction Settings",
    "Direct Labor Designation",
    "Company",
    "Cost Center",
    "Project",
    "Department",
    "UOM",
    "Item",
    "Customer",
    "Supplier",
    "Purchase Order",
    "Purchase Invoice",
    "Sales Invoice",
    "Journal Entry",
    "Stock Entry",
    "Material Request",
    "Timesheet",
    "User",
    "Role",
    "DocType",
}

# ═══════════════════════════════════════════════════════════════
# Audit Logging
# ═══════════════════════════════════════════════════════════════

audit_logger = logging.getLogger("erpnext_mcp_audit")
audit_logger.setLevel(logging.INFO)
handler = logging.FileHandler(AUDIT_LOG)
handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
audit_logger.addHandler(handler)


def audit(tool: str, args: dict, result_status: str):
    audit_logger.info(f"TOOL={tool} | ARGS={json.dumps(args)} | STATUS={result_status}")


# ═══════════════════════════════════════════════════════════════
# Frappe Initialization
# ═══════════════════════════════════════════════════════════════

def init_frappe():
    """Initialize Frappe connection."""
    os.chdir(BENCH_PATH)
    sys.path.insert(0, str(BENCH_PATH / "apps" / "frappe"))
    sys.path.insert(0, str(BENCH_PATH / "apps" / "erpnext"))
    sys.path.insert(0, str(BENCH_PATH / "apps" / "construction"))

    # Frappe logger expects site/logs/ relative to cwd
    (BENCH_PATH / SITE_NAME / "logs").mkdir(parents=True, exist_ok=True)

    import frappe

    if not frappe.db:
        frappe.init(site=SITE_NAME, sites_path="sites")
        frappe.connect()
    return frappe


# ═══════════════════════════════════════════════════════════════
# Safety Guards
# ═══════════════════════════════════════════════════════════════

FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def guard_doctype(doctype: str) -> str:
    """Enforce DocType allowlist."""
    if doctype not in ALLOWLIST:
        raise PermissionError(
            f"DocType '{doctype}' is not in the read-only allowlist. "
            f"Allowed: {sorted(ALLOWLIST)}"
        )
    return doctype


def guard_sql(sql: str) -> str:
    """Block any SQL that modifies data."""
    if FORBIDDEN_SQL_PATTERN.search(sql):
        raise PermissionError(
            "Write SQL detected. This MCP server is read-only. "
            f"Blocked query: {sql[:200]}"
        )
    return sql


# ═══════════════════════════════════════════════════════════════
# Tool Implementations
# ═══════════════════════════════════════════════════════════════

import threading

_thread_local = threading.local()


def get_frappe():
    if not hasattr(_thread_local, "frappe"):
        _thread_local.frappe = init_frappe()
    return _thread_local.frappe


def tool_get_boq_header(name: str) -> dict:
    """Get BOQ Header with child items."""
    f = get_frappe()
    guard_doctype("BOQ Header")
    doc = f.get_doc("BOQ Header", name)
    return {
        "name": doc.name,
        "project": doc.project,
        "boq_type": doc.boq_type,
        "status": doc.status,
        "version": doc.version,
        "total_contract_value": doc.total_contract_value,
        "total_estimated_value": doc.total_estimated_value,
        "items": [
            {
                "name": item.name,
                "structure": item.structure,
                "cost_item": item.cost_item,
                "item_type": item.item_type,
                "quantity": item.quantity,
                "unit": item.unit,
                "est_unit_cost": item.est_unit_cost,
                "contract_unit_price": item.contract_unit_price,
                "line_total": item.line_total,
            }
            for item in doc.get("items", [])
        ],
    }


def tool_get_boq_structure_tree(boq_header: str) -> list[dict]:
    """Get full WBS tree for a BOQ Header."""
    f = get_frappe()
    guard_doctype("BOQ Structure")
    structures = f.get_all(
        "BOQ Structure",
        filters={"boq_header": boq_header},
        fields=["name", "title", "wbs_code", "parent_structure", "is_group", "lft", "rgt"],
        order_by="lft",
    )
    return structures


def tool_get_scope_context(user: str | None = None) -> dict | None:
    """Get current scope context for a user."""
    f = get_frappe()
    guard_doctype("User Scope Context")
    user = user or f.session.user
    ctx = f.db.get_value(
        "User Scope Context",
        {"user": user},
        ["company", "cost_center", "project", "department", "branch", "scope_version"],
        as_dict=True,
    )
    return ctx


def tool_list_construction_themes() -> list[dict]:
    """List available Construction Themes."""
    f = get_frappe()
    guard_doctype("Construction Theme")
    themes = f.get_all(
        "Construction Theme",
        filters={"is_active": 1},
        fields=["name", "theme_name", "theme_type", "primary_color", "is_system_theme"],
    )
    return themes


def tool_get_form_layout_profile(doctype: str) -> dict | None:
    """Get active Form Layout Profile for a DocType."""
    f = get_frappe()
    guard_doctype("Form Layout Profile")
    guard_doctype(doctype)
    profile = f.db.get_value(
        "Form Layout Profile",
        {"reference_doctype": doctype, "enabled": 1},
        ["profile_name", "sections_json", "layout_version", "is_default", "is_system"],
        as_dict=True,
    )
    return profile


def tool_get_doctype_schema(doctype: str) -> dict:
    """Get field schema for a DocType."""
    f = get_frappe()
    guard_doctype(doctype)
    meta = f.get_meta(doctype)
    return {
        "doctype": doctype,
        "fields": [
            {
                "fieldname": field.fieldname,
                "fieldtype": field.fieldtype,
                "label": field.label,
                "reqd": field.reqd,
                "options": field.options,
            }
            for field in meta.fields
        ],
    }


def tool_get_document(doctype: str, name: str) -> dict:
    """Generic read-only get_doc (allowlist enforced)."""
    f = get_frappe()
    guard_doctype(doctype)
    doc = f.get_doc(doctype, name)
    return doc.as_dict()


def tool_get_doctype_list(
    doctype: str,
    filters: dict | None = None,
    fields: list[str] | None = None,
    limit: int = 20,
) -> list[dict]:
    """Generic read-only list query (allowlist enforced)."""
    f = get_frappe()
    guard_doctype(doctype)
    if limit > 100:
        raise ValueError("Limit cannot exceed 100 for safety")
    default_fields = ["name"]
    return f.get_all(
        doctype,
        filters=filters or {},
        fields=fields or default_fields,
        limit=limit,
    )


def tool_run_safe_select(sql: str, params: dict | None = None) -> list[dict]:
    """Run a read-only SELECT query."""
    f = get_frappe()
    guard_sql(sql)
    return f.db.sql(sql, params or {}, as_dict=True)


# ═══════════════════════════════════════════════════════════════
# MCP Server Setup
# ═══════════════════════════════════════════════════════════════

from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("erpnext-construction-mcp")

TOOLS = [
    Tool(name="get_boq_header", description="Get BOQ Header with all items", inputSchema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}),
    Tool(name="get_boq_structure_tree", description="Get WBS tree for a BOQ Header", inputSchema={"type": "object", "properties": {"boq_header": {"type": "string"}}, "required": ["boq_header"]}),
    Tool(name="get_scope_context", description="Get current scope for a user", inputSchema={"type": "object", "properties": {"user": {"type": "string"}}}),
    Tool(name="list_construction_themes", description="List active Construction Themes", inputSchema={"type": "object", "properties": {}}),
    Tool(name="get_form_layout_profile", description="Get active layout profile for a DocType", inputSchema={"type": "object", "properties": {"doctype": {"type": "string"}}, "required": ["doctype"]}),
    Tool(name="get_doctype_schema", description="Get field schema for a DocType", inputSchema={"type": "object", "properties": {"doctype": {"type": "string"}}, "required": ["doctype"]}),
    Tool(name="get_document", description="Generic read-only get_doc (allowlist enforced)", inputSchema={"type": "object", "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}}, "required": ["doctype", "name"]}),
    Tool(name="get_doctype_list", description="Generic read-only list query (allowlist enforced)", inputSchema={"type": "object", "properties": {"doctype": {"type": "string"}, "filters": {"type": "object"}, "fields": {"type": "array", "items": {"type": "string"}}, "limit": {"type": "integer", "default": 20}}, "required": ["doctype"]}),
    Tool(name="run_safe_select", description="Run a read-only SELECT SQL query", inputSchema={"type": "object", "properties": {"sql": {"type": "string"}, "params": {"type": "object"}}, "required": ["sql"]}),
]


@app.list_tools()
async def list_tools():
    return TOOLS


_tool_map = {
    "get_boq_header": lambda a: tool_get_boq_header(a["name"]),
    "get_boq_structure_tree": lambda a: tool_get_boq_structure_tree(a["boq_header"]),
    "get_scope_context": lambda a: tool_get_scope_context(a.get("user")),
    "list_construction_themes": lambda a: tool_list_construction_themes(),
    "get_form_layout_profile": lambda a: tool_get_form_layout_profile(a["doctype"]),
    "get_doctype_schema": lambda a: tool_get_doctype_schema(a["doctype"]),
    "get_document": lambda a: tool_get_document(a["doctype"], a["name"]),
    "get_doctype_list": lambda a: tool_get_doctype_list(
        a["doctype"], a.get("filters"), a.get("fields"), a.get("limit", 20)
    ),
    "run_safe_select": lambda a: tool_run_safe_select(a["sql"], a.get("params")),
}


import concurrent.futures

# Dedicated executor that does NOT copy asyncio contextvars over thread context
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="erpnext_mcp")


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    import asyncio
    try:
        func = _tool_map.get(name)
        if not func:
            raise ValueError(f"Unknown tool: {name}")

        loop = asyncio.get_running_loop()
        # Use executor directly (without context copy) to preserve per-thread Frappe state
        result = await loop.run_in_executor(_executor, func, arguments)

        audit(name, arguments, "success")
        return [TextContent(type="text", text=json.dumps(result, default=str))]

    except Exception as e:
        audit(name, arguments, f"error: {e}")
        error_payload = {"error": str(e), "tool": name}
        return [TextContent(type="text", text=json.dumps(error_payload))]


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read, write):
            await app.run(read, write, app.create_initialization_options())

    asyncio.run(main())
