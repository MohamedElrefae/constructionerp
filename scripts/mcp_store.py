#!/usr/bin/env python3
"""
Store a memory in MemoryGraph via MCP.

Usage:
    python3 scripts/mcp_store.py \
        --type code_pattern \
        --title "Fix for X" \
        --content "Detailed description..." \
        --tag python --tag frappe \
        --importance 0.9

Types: task, code_pattern, problem, solution, project, technology,
       error, fix, command, file_context, workflow, general, conversation

If no content is provided via --content, reads from stdin.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Use memorygraph's venv Python path to ensure pydantic works
VENV_SITE = Path.home() / ".local/share/pipx/venvs/memorygraphmcp/lib/python3.12/site-packages"
sys.path.insert(0, str(VENV_SITE))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path("/home/mohamed/frappe-bench/apps/construction")


async def store_memory(
    title: str,
    content: str,
    type_: str,
    tags: list[str],
    importance: float,
    summary: str | None = None,
    files_involved: list[str] | None = None,
):
    server_params = StdioServerParameters(
        command="memorygraph",
        args=[],
        env=None,
    )

    context = {
        "project_path": str(REPO_ROOT),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if files_involved:
        context["files_involved"] = files_involved

    payload = {
        "title": title,
        "content": content,
        "type": type_,
        "tags": tags,
        "importance": importance,
        "summary": summary or content[:200],
        "context": context,
    }

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("store_memory", payload)
            for item in result.content:
                if item.type == "text":
                    try:
                        data = json.loads(item.text)
                        mem_id = data.get("id", "unknown")
                        print(f"Stored memory: {mem_id}")
                        return mem_id
                    except json.JSONDecodeError:
                        print(item.text)
                        return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Store a memory in MemoryGraph")
    parser.add_argument("--type", required=True, help="Memory type (code_pattern, fix, etc.)")
    parser.add_argument("--title", required=True, help="Short title")
    parser.add_argument("--content", help="Memory content (or read from stdin)")
    parser.add_argument("--summary", help="Optional brief summary")
    parser.add_argument("--tag", action="append", default=[], help="Tags (repeatable)")
    parser.add_argument("--importance", type=float, default=0.7, help="Importance 0.0-1.0")
    parser.add_argument("--file", action="append", default=[], help="Files involved (repeatable)")

    args = parser.parse_args()

    content = args.content
    if not content:
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            print("Error: --content required or pipe content via stdin", file=sys.stderr)
            sys.exit(1)

    mem_id = asyncio.run(
        store_memory(
            title=args.title,
            content=content,
            type_=args.type,
            tags=[t.lower() for t in args.tag],
            importance=args.importance,
            summary=args.summary,
            files_involved=args.file or None,
        )
    )

    if mem_id:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
