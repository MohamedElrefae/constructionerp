# AI Memory System — User Guide

> **For:** Mohamed Elrefae (solo developer)  
> **Purpose:** How to use the Construction ERP persistent memory & AI agent integration  
> **Last updated:** 2026-05-31

---

## Quick Start (30 Seconds)

Every time you start a new AI coding session, paste this prompt into your agent:

```
Read /home/mohamed/frappe-bench/apps/construction/AGENTS.md for project context,
then read SESSION_MEMORY.md for current state.
Summarize: (1) what systems exist, (2) what's in progress, (3) what to work on next.
```

The agent will immediately know:
- This is a Frappe/ERPNext construction app
- BOQ Item uses `cost_item` (Data), NOT `item_code`
- Only 6 CSS files are registered in `hooks.py`
- Current branch is `feature/vite-ui-v1`
- Active workstreams (Form Layout Engine Phase 3+, BOQ Accounting)

---

## Supported Agents & Starter Prompts

### Kimi Code
```bash
cd /home/mohamed/frappe-bench/apps/construction
kimi
```

**Starter prompt:**
```
You are working on the Construction ERP project at /home/mohamed/frappe-bench/apps/construction.
Read AGENTS.md first, then SESSION_MEMORY.md.
Current branch: feature/vite-ui-v1.
Do not re-explain project architecture. Jump directly into the task.
```

### Codex (OpenAI)
```bash
cd /home/mohamed/frappe-bench/apps/construction
codex
```

**Starter prompt:**
```
Project: Construction ERP (Frappe/ERPNext app).
Repo: /home/mohamed/frappe-bench/apps/construction.
Read AGENTS.md and SESSION_MEMORY.md before writing any code.
Critical: BOQ Item has no item_code — use cost_item (Data field).
```

### Claude Code (if installed)
```bash
claude
```

**Starter prompt:**
```
/agents Read /home/mohamed/frappe-bench/apps/construction/AGENTS.md and SESSION_MEMORY.md for project context.
```

### Windsurf (Cascade)
Open the repo in Windsurf. The `.cursorrules` equivalent is implicit via `AGENTS.md`.

### Antigravity (Google)
Open the repo directory in Antigravity IDE.

---

## MCP Features (For MCP-Enabled Agents)

### 1. Memory Recall
Ask the agent naturally:
> "What was I working on last session?"
> "How do I add a new CSS file?"
> "What fields does BOQ Item have?"

The agent will query the `memorygraph` MCP server and answer from stored memories.

### 2. ERPNext Data Queries
Ask the agent naturally:
> "Show me the active construction themes"
> "Get the BOQ Item schema"
> "List users in the system"
> "What is the WBS tree for BOQ-001?"

The agent will call the `erpnext-construction` MCP server and query live ERPNext data.

### 3. Natural Language to SQL
> "Run a query to find all BOQ Items with quantity > 100"

The agent will use `run_safe_select` (read-only, allowlist enforced).

---

## Session End Protocol (Mandatory)

After every coding session, run:

```bash
cd /home/mohamed/frappe-bench/apps/construction
python3 scripts/session_end.py
```

This will:
1. Prompt you for what you worked on
2. Store the session summary to MCP memory
3. Append the session to `SESSION_MEMORY.md`

**Why:** Non-MCP agents (and future you) need the written record.

---

## Git Auto-Capture (Automatic)

Every `git commit` automatically stores a memory via the post-commit hook.

**You don't need to do anything.** Just commit normally:
```bash
git add .
git commit -m "feat: add new feature X"
```

The hook captures:
- Commit hash
- Author
- Commit message
- Changed files

**To reinstall hooks** (if lost):
```bash
bash scripts/install_git_hooks.sh
```

---

## Validation (Run Before Major Changes)

Before seeding MCP memory or after schema changes:

```bash
cd /home/mohamed/frappe-bench/apps/construction
python3 scripts/ai_context_check.py
```

Expected: `✅ ALL CHECKS PASSED — Safe to seed AI memory.`

This verifies:
- BOQ Item has `cost_item`, no `item_code`
- CSS registration list is correct
- Theme API has 17 endpoints
- All 14 DocTypes exist
- Patches v6.0–v6.6 exist
- ADR.md has 7+ ADRs

---

## Manual Memory Helpers

### Store a memory manually
```bash
python3 scripts/mcp_store.py \
  --type fix \
  --title "Fixed scope filter race condition" \
  --content "Problem: ... Solution: ..." \
  --tag scope --tag fix \
  --importance 0.9
```

### Recall memories manually
```bash
python3 scripts/mcp_recall.py "BOQ Item schema" --limit 3
python3 scripts/mcp_recall.py --tag construction --tag boq
```

---

## File Reference Quick Map

| Need | File |
|------|------|
| Project identity & conventions | `AGENTS.md` |
| Current sprint & blockers | `SESSION_MEMORY.md` |
| DocType schemas | `docs/ai/SCHEMA_FACTS.md` |
| Code patterns | `docs/ai/CODING_PATTERNS.md` |
| Memory file map | `docs/ai/CONTEXT_INDEX.md` |
| Validation script | `scripts/ai_context_check.py` |
| Session capture | `scripts/session_end.py` |
| MCP store helper | `scripts/mcp_store.py` |
| MCP recall helper | `scripts/mcp_recall.py` |
| Git hook installer | `scripts/install_git_hooks.sh` |
| ERPNext MCP server | `erpnext-mcp-server/server.py` |
| Architecture plan | `CONSTRUCTION_ERP_AI_MEMORY_PLAN_v2.2.md` |

---

## Troubleshooting

### Agent doesn't know about the project
- Did you paste the starter prompt?
- Is `AGENTS.md` readable? Run: `cat AGENTS.md | head -20`

### MCP tools not available
- Check: `kimi mcp list` (or equivalent for your agent)
- If missing, re-register using the commands in the agent-specific sections above

### Validation script fails
- Do not seed memory until checks pass
- Fix the underlying repo issue first

### Frappe connection errors from ERPNext MCP
- Ensure MariaDB is running
- Ensure site `v16.localhost` is accessible
- Check logs: `tail -f logs/ai_mcp_audit.log`

### Git hook not firing
- Check hook exists: `ls .git/hooks/post-commit`
- Reinstall: `bash scripts/install_git_hooks.sh`

---

## Rules for All Sessions

1. **Repo files are source of truth.** If MCP memory conflicts with `AGENTS.md` or live code, the repo wins.
2. **Always run `ai_context_check.py` after schema changes.**
3. **Always run `session_end.py` after every session.**
4. **Never register all 22 CSS files in `hooks.py`.** Only 6 are production-registered.
5. **BOQ Item has no `item_code`.** Use `cost_item` (Data field).

---

*For the full architecture plan, see `CONSTRUCTION_ERP_AI_MEMORY_PLAN_v2.2.md`.*
