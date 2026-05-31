#!/usr/bin/env python3
"""
Session End — Capture session summary to MCP and update SESSION_MEMORY.md

Usage:
    python3 scripts/session_end.py \
        --summary "Implemented X, fixed Y" \
        --decisions "Used approach Z because..." \
        --issues "Found bug in W" \
        --next "Work on Q next"

Or interactively:
    python3 scripts/session_end.py
"""

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SESSION_MEMORY = REPO_ROOT / "SESSION_MEMORY.md"
VENV_SITE = Path.home() / ".local/share/pipx/venvs/memorygraphmcp/lib/python3.12/site-packages"
sys.path.insert(0, str(VENV_SITE))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def get_git_summary():
    """Get commits and changed files since the last session log entry."""
    try:
        commits = subprocess.check_output(
            ["git", "log", "--oneline", "-5"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        commits = "(git log failed)"

    try:
        changed = subprocess.check_output(
            ["git", "diff", "--stat", "HEAD~1"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        changed = "(git diff failed)"

    return commits, changed


async def store_session_memory(summary: str, decisions: str, issues: str, next_steps: str):
    """Store session summary to MCP."""
    server_params = StdioServerParameters(command="memorygraph", args=[], env=None)

    content_parts = [f"Session Summary:\n{summary}"]
    if decisions:
        content_parts.append(f"\nDecisions:\n{decisions}")
    if issues:
        content_parts.append(f"\nIssues Found:\n{issues}")
    if next_steps:
        content_parts.append(f"\nNext Steps:\n{next_steps}")

    payload = {
        "title": f"Session {datetime.now(timezone.utc).strftime('%Y-%m-%d')} — {summary[:60]}",
        "content": "\n".join(content_parts),
        "type": "general",
        "tags": ["session", "construction"],
        "importance": 0.7,
        "summary": summary[:200],
        "context": {
            "project_path": str(REPO_ROOT),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
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
                        print(f"Stored session memory: {mem_id}")
                        return mem_id
                    except json.JSONDecodeError:
                        print(item.text)
    return None


def update_session_markdown(summary: str, decisions: str, issues: str, next_steps: str):
    """Append session entry to SESSION_MEMORY.md Section 6."""
    if not SESSION_MEMORY.exists():
        print(f"Warning: {SESSION_MEMORY} not found", file=sys.stderr)
        return

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"\n### Session {date_str} — Agent: [Agent Name]",
        f"- **Worked on:** {summary}",
    ]
    if decisions:
        lines.append(f"- **Decisions:** {decisions}")
    if issues:
        lines.append(f"- **Issues found:** {issues}")
    if next_steps:
        lines.append(f"- **Next steps:** {next_steps}")

    # Find the append-only section and prepend the new entry after the header
    text = SESSION_MEMORY.read_text()
    marker = "## 6. Session Log (Append-Only — Most Recent First)"
    if marker in text:
        parts = text.split(marker, 1)
        new_text = parts[0] + marker + "\n" + "\n".join(lines) + parts[1]
        SESSION_MEMORY.write_text(new_text)
        print("Updated SESSION_MEMORY.md")
    else:
        print(f"Warning: Could not find session log marker in {SESSION_MEMORY}", file=sys.stderr)


def interactive_prompt():
    print("Session End Capture")
    print("=" * 50)
    summary = input("What did you work on?\n> ").strip()
    decisions = input("Any decisions made? (optional)\n> ").strip()
    issues = input("Any issues found? (optional)\n> ").strip()
    next_steps = input("Next steps? (optional)\n> ").strip()
    return summary, decisions, issues, next_steps


def main():
    parser = argparse.ArgumentParser(description="Capture session end summary")
    parser.add_argument("--summary", help="What was accomplished")
    parser.add_argument("--decisions", help="Decisions made")
    parser.add_argument("--issues", help="Issues found")
    parser.add_argument("--next", dest="next_steps", help="Next steps")
    parser.add_argument("--no-mcp", action="store_true", help="Skip MCP store, only update markdown")

    args = parser.parse_args()

    if args.summary:
        summary, decisions, issues, next_steps = args.summary, args.decisions or "", args.issues or "", args.next_steps or ""
    else:
        summary, decisions, issues, next_steps = interactive_prompt()

    if not summary:
        print("Error: summary is required", file=sys.stderr)
        sys.exit(1)

    # Git context
    commits, changed = get_git_summary()
    print(f"\nRecent commits:\n{commits}")
    print(f"\nChanged files:\n{changed}")

    # Store to MCP
    if not args.no_mcp:
        mem_id = asyncio.run(store_session_memory(summary, decisions, issues, next_steps))
        if mem_id:
            print("Session stored to MCP memory.")
        else:
            print("Warning: MCP store failed, but continuing...", file=sys.stderr)

    # Update markdown
    update_session_markdown(summary, decisions, issues, next_steps)
    print("Done.")


if __name__ == "__main__":
    main()
