# AI Context Index

This file maps all persistent memory files for the Construction ERP project.
Use this to navigate the memory architecture quickly.

## Repository Context and Instructions

Use the current source/schema, explicit owner instructions, and applicable governed state to resolve dated or conflicting narrative claims. This index locates context; it does not grant operations or declare workflow state.

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `AGENTS.md` | Project identity, tech stack, core systems, conventions | Rarely (architecture changes only) |
| `SESSION_MEMORY.md` | Current sprint, active tasks, blockers, session log | Every session |
| `docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md` | Required startup checklist and professional Frappe development instructions | When engineering instructions change |
| `AGENT_WORKFLOW.md` | Root-level governed workflow entry point; consult applicable contracts/state | When approved workflow instructions change |
| `ADR.md` | Accepted architecture decision records; verify the current decisions in the file | When new ADRs are accepted |

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
| `scripts/schema_drift_checker.py` | Compares schema facts with current repository DocType JSON; no database validation |
| `docs/ai/work-items/engineering-startup-gates/IMPLEMENTATION.md` | Automatic coordinator startup policy, required context, exact factual write scope, and legacy-task behavior |
| `docs/ai/work-items/engineering-startup-gates/REVIEW.md` | Independent review and verification of startup integration; qualification limits |

For every session, follow [the standard's startup checklist](PROFESSIONAL_ENGINEERING_STANDARD.md): read actual context files, capture checkout/branch/HEAD/status, and run both checkers before planning or editing. Record results and a truthful Files Read list. Recheck affected facts after concurrent changes. These are local checks, not proof of latest remote code or deployed schema.

Legacy references to `docs/ai/AGENT_WORKFLOW.md` should resolve to the existing root [workflow](../../AGENT_WORKFLOW.md). `docs/ai/templates/PLAN.md` is absent; use the applicable approved work-item/role artifacts rather than claiming that file was read. The existing [architect inbox template](templates/inbox-architect.md) serves governed role packets, not a general PLAN template.

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
