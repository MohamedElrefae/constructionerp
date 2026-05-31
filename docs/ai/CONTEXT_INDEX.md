# AI Context Index

This file maps all persistent memory files for the Construction ERP project.
Use this to navigate the memory architecture quickly.

## Source of Truth (Repo-Local — Always Authoritative)

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `AGENTS.md` | Project identity, tech stack, core systems, conventions | Rarely (architecture changes only) |
| `SESSION_MEMORY.md` | Current sprint, active tasks, blockers, session log | Every session |
| `ADR.md` | Architecture decision records (7 accepted ADRs) | When new ADRs are accepted |

## Deep Reference (Repo-Local — Curated)

| File | Purpose | Source |
|------|---------|--------|
| `docs/ai/SCHEMA_FACTS.md` | Verified DocType schemas and field lists | Generated from `*/doctype/*/*.json` |
| `docs/ai/CODING_PATTERNS.md` | Reusable code patterns for BOQ, theme, scope | Curated from actual codebase |
| `docs/onboarding.md` | Developer onboarding guide | Human-written |
| `docs/token_reference.md` | 54 CSS design tokens | Human-written |
| `docs/hook_matrix.md` | Frappe hook registration reference | Human-written |
| `docs/troubleshooting.md` | Known issues and fixes | Human-written |

## Validation & Safety

| File | Purpose |
|------|---------|
| `scripts/ai_context_check.py` | Validates critical facts against live repo files before memory seeding |

## Adapter Layers (Derived from Source of Truth)

| Layer | Location | Notes |
|-------|----------|-------|
| MCP memory database | `~/.memorygraph/construction-erp.db` (proposed) | Seeded from repo files; treated as cache |
| Agent skills/rules | `construction-erp-coder/SKILL.md` (proposed) | Should link to canonical docs, not duplicate large sections |
| ERPNext MCP server | `erpnext-mcp-server/` (proposed Phase 3) | Read-only v1; no command execution |

## Update Rules

1. **If a fact changes in the repo** (e.g., new DocType field), update:
   - `docs/ai/SCHEMA_FACTS.md` first
   - `SESSION_MEMORY.md` if it affects active work
   - `AGENTS.md` only if it changes core architecture

2. **If MCP memory conflicts with any repo file**, the repo file wins.

3. **Before seeding MCP memory**, run `scripts/ai_context_check.py` and confirm all checks pass.

4. **Agent compatibility:**
   - All agents can read `AGENTS.md` and `SESSION_MEMORY.md`.
   - MCP-enabled agents (Claude Code, OpenCode, Antigravity) may also query MCP memory.
   - Non-MCP agents (Codex, Kimi Code, Cursor) rely on repo-local files only.
