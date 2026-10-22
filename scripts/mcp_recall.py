#!/usr/bin/env python3
"""
Recall memories from MemoryGraph via MCP.

Usage:
    python3 scripts/mcp_recall.py "BOQ Item schema"
    python3 scripts/mcp_recall.py "CSS registration" --limit 5
    python3 scripts/mcp_recall.py --tag construction --tag boq
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

VENV_SITE = Path.home() / ".local/share/pipx/venvs/memorygraphmcp/lib/python3.12/site-packages"
sys.path.insert(0, str(VENV_SITE))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def recall(query: str, tags: list[str], limit: int):
    server_params = StdioServerParameters(
        command="memorygraph",
        args=[],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if tags:
                result = await session.call_tool(
                    "search_memories",
                    {"tags": tags, "limit": limit},
                )
            else:
                result = await session.call_tool(
                    "recall_memories",
                    {"query": query, "limit": limit},
                )

            for item in result.content:
                if item.type == "text":
                    print(item.text)


def main():
    parser = argparse.ArgumentParser(description="Recall memories from MemoryGraph")
    parser.add_argument("query", nargs="?", default="", help="Search query")
    parser.add_argument("--tag", action="append", default=[], help="Filter by tag")
    parser.add_argument("--limit", type=int, default=5, help="Max results")

    args = parser.parse_args()
    asyncio.run(recall(args.query, args.tag, args.limit))


if __name__ == "__main__":
    main()
