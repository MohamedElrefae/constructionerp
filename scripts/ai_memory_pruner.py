#!/usr/bin/env python3
"""
AI Memory Pruner - Construction ERP
===================================
Summarizes older SESSION_MEMORY.md session-log entries when the log grows large.

Usage:
    python3 scripts/ai_memory_pruner.py --dry-run
    python3 scripts/ai_memory_pruner.py --auto

The script is deterministic by default. It writes a timestamped backup before
modifying SESSION_MEMORY.md.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION_MEMORY = REPO_ROOT / "SESSION_MEMORY.md"
ARCHIVE_DIR = REPO_ROOT / "docs" / "ai" / "archive" / "session-history"
SESSION_MARKER = "## 6. Session Log (Append-Only"
COMPRESSED_MARKER = "## 7. Compressed Session History"


def find_session_section(text: str) -> tuple[str, str, str]:
    marker_index = text.find(SESSION_MARKER)
    if marker_index == -1:
        raise ValueError(f"Could not find session log marker containing: {SESSION_MARKER}")

    section_start = text.rfind("\n", 0, marker_index)
    if section_start == -1:
        section_start = marker_index
    else:
        section_start += 1

    next_heading = re.search(r"\n##\s+", text[section_start + 1 :])
    if next_heading:
        section_end = section_start + 1 + next_heading.start()
    else:
        section_end = len(text)

    return text[:section_start], text[section_start:section_end], text[section_end:]


def split_entries(section: str) -> tuple[str, list[str]]:
    match = re.search(r"\n###\s+", section)
    if not match:
        return section.rstrip() + "\n", []

    header = section[: match.start()].rstrip() + "\n"
    body = section[match.start() + 1 :]
    raw_entries = re.split(r"(?m)^###\s+", body)
    entries = []
    for entry in raw_entries:
        entry = entry.strip()
        if entry:
            entries.append("### " + entry + "\n")
    return header, entries


def summarize_entry(entry: str) -> str:
    heading = entry.splitlines()[0].replace("###", "").strip()
    bullets = []
    for line in entry.splitlines()[1:]:
        stripped = line.strip()
        if stripped.startswith("- **Worked on:**"):
            bullets.append(stripped.replace("- **Worked on:**", "worked on").strip())
        elif stripped.startswith("- **Decisions:**"):
            bullets.append(stripped.replace("- **Decisions:**", "decision").strip())
        elif stripped.startswith("- **Issues found:**"):
            bullets.append(stripped.replace("- **Issues found:**", "issue").strip())
        elif stripped.startswith("- **Next steps:**"):
            bullets.append(stripped.replace("- **Next steps:**", "next").strip())
    summary = "; ".join(part for part in bullets if part)
    if not summary:
        summary = "Archived session entry."
    return f"- {heading}: {summary}"


def build_compressed_section(entries: list[str]) -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        COMPRESSED_MARKER,
        "",
        f"### Pruned on {date_str}",
        "",
        "Older raw session entries were compressed by `scripts/ai_memory_pruner.py`.",
        "",
    ]
    lines.extend(summarize_entry(entry) for entry in entries)
    lines.append("")
    return "\n".join(lines)


def prune_text(text: str, threshold: int, keep_entries: int) -> tuple[str, dict]:
    prefix, section, suffix = find_session_section(text)
    header, entries = split_entries(section)
    section_line_count = len(section.splitlines())
    stats = {
        "section_line_count": section_line_count,
        "entry_count": len(entries),
        "pruned_count": 0,
        "changed": False,
    }

    if section_line_count <= threshold or len(entries) <= keep_entries:
        return text, stats

    keep = entries[:keep_entries]
    prune = entries[keep_entries:]
    stats["pruned_count"] = len(prune)
    stats["changed"] = True

    new_section = header + "\n" + "\n".join(entry.rstrip() for entry in keep).rstrip() + "\n"

    if COMPRESSED_MARKER in suffix:
        compressed = build_compressed_section(prune)
        suffix = suffix.replace(COMPRESSED_MARKER, compressed + "\n" + COMPRESSED_MARKER, 1)
    else:
        suffix = suffix.rstrip() + "\n\n" + build_compressed_section(prune) + "\n"

    return prefix + new_section + suffix, stats


def backup_file(path: Path) -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = ARCHIVE_DIR / f"{path.stem}.{timestamp}{path.suffix}.bak"
    shutil.copy2(path, backup)
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune SESSION_MEMORY.md session log")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    parser.add_argument("--auto", action="store_true", help="Write changes when pruning is needed")
    parser.add_argument("--threshold", type=int, default=300, help="Session section line threshold")
    parser.add_argument("--keep-entries", type=int, default=12, help="Recent raw session entries to preserve")
    parser.add_argument(
        "--ollama-model",
        help="Reserved for future LLM summarization; deterministic summarization is used today",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.auto:
        args.dry_run = True

    if not SESSION_MEMORY.exists():
        print(f"Missing {SESSION_MEMORY}")
        return 1

    text = SESSION_MEMORY.read_text()
    try:
        new_text, stats = prune_text(text, args.threshold, args.keep_entries)
    except ValueError as exc:
        print(str(exc))
        return 1

    print(f"Session log lines: {stats['section_line_count']}")
    print(f"Session entries: {stats['entry_count']}")
    print(f"Entries to prune: {stats['pruned_count']}")

    if not stats["changed"]:
        print("No pruning needed.")
        return 0

    if args.dry_run:
        print("Dry run only. Re-run with --auto to write changes.")
        return 0

    backup = backup_file(SESSION_MEMORY)
    SESSION_MEMORY.write_text(new_text)
    print(f"Backup written: {backup}")
    print(f"Updated {SESSION_MEMORY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
