# End-to-End Test Report — AI Memory System

> **For:** AI QA / Verification Agent  
> **Purpose:** Verify all phases of the Construction ERP AI memory system are operational  
> **Repo:** `/home/mohamed/frappe-bench/apps/construction`  
> **Last updated:** 2026-05-31

---

## Test Environment Prerequisites

```bash
cd /home/mohamed/frappe-bench/apps/construction
# Ensure branch is feature/vite-ui-v1
git branch --show-current
# Ensure memorygraph is installed
memorygraph --version
# Ensure mcp is installed in bench venv
/home/mohamed/frappe-bench/env/bin/python -c "import mcp; print('mcp ok')"
```

---

## Phase 1: Static File Memory

### T1.1 — AGENTS.md Integrity

| Step | Command / Action | Expected Result |
|------|------------------|-----------------|
| 1 | `test -f AGENTS.md && echo "exists"` | `exists` |
| 2 | `grep -c "Project Identity" AGENTS.md` | `>= 1` |
| 3 | `grep -c "NO item_code or item_name" AGENTS.md` | `>= 1` |
| 4 | `grep -c "Only 6 CSS files" AGENTS.md` | `>= 1` |
| 5 | `grep -c "ADR.md.*7" AGENTS.md` | `>= 1` |
| 6 | `wc -l < AGENTS.md` | Between 100–200 |

**Pass criteria:** All steps match expected results.

---

### T1.2 — SESSION_MEMORY.md Integrity

| Step | Command / Action | Expected Result |
|------|------------------|-----------------|
| 1 | `test -f SESSION_MEMORY.md && echo "exists"` | `exists` |
| 2 | `grep -c "Session Log" SESSION_MEMORY.md` | `>= 1` |
| 3 | `grep -c "2026-05-31" SESSION_MEMORY.md` | `>= 3` (Phases 1, 2, 3) |
| 4 | `grep -c "In Progress" SESSION_MEMORY.md` | `>= 1` |

**Pass criteria:** All steps match expected results.

---

### T1.3 — docs/ai/ Reference Folder

| Step | Command / Action | Expected Result |
|------|------------------|-----------------|
| 1 | `test -f docs/ai/CONTEXT_INDEX.md` | File exists |
| 2 | `test -f docs/ai/SCHEMA_FACTS.md` | File exists |
| 3 | `test -f docs/ai/CODING_PATTERNS.md` | File exists |
| 4 | `grep -c "cost_item" docs/ai/SCHEMA_FACTS.md` | `>= 1` |
| 5 | `grep -c "parameterized" docs/ai/CODING_PATTERNS.md` | `>= 1` |

**Pass criteria:** All files exist and contain expected content.

---

### T1.4 — Validation Script (`ai_context_check.py`)

```bash
cd /home/mohamed/frappe-bench/apps/construction
python3 scripts/ai_context_check.py
```

| Check Group | Expected |
|-------------|----------|
| Core Memory Files | 2 passed |
| Git State | 3 passed |
| BOQ Item Schema (Critical) | 4 passed + 1 info |
| BOQ Structure NestedSet | 5 passed |
| CSS Registration | 7 passed |
| Theme API Endpoints | 1 passed + 1 info |
| Migration Patches | 7 passed |
| DocType Registry | 1 passed |
| CostItem & PlantResource | 2 passed |
| Architecture Decisions | 1 passed |
| **Total** | **33 passed, 0 failed** |

**Pass criteria:** Exit code 0, summary says `✅ ALL CHECKS PASSED`.

---

### T1.5 — Skill Files

| Step | Command / Action | Expected Result |
|------|------------------|-----------------|
| 1 | `test -f construction-erp-coder/SKILL.md` | File exists |
| 2 | `test -f construction-erp-coder/references/project-context.md` | File exists |
| 3 | `test -f construction-erp-coder/references/doctype-schema.md` | File exists |
| 4 | `test -f construction-erp-coder/references/coding-patterns.md` | File exists |
| 5 | `grep -c "construction-erp-coder" construction-erp-coder/SKILL.md` | `>= 1` |

**Pass criteria:** All files exist.

---

## Phase 2: MCP Memory & Auto-Capture

### T2.1 — MemoryGraph Health

```bash
memorygraph --health
```

| Expected Output |
|-----------------|
| Status: Healthy |
| Backend: sqlite |
| Memories: `>= 10` |

**Pass criteria:** Healthy status, 10+ memories.

---

### T2.2 — MCP Store Helper

```bash
cd /home/mohamed/frappe-bench/apps/construction
/home/mohamed/.local/share/pipx/venvs/memorygraphmcp/bin/python scripts/mcp_store.py \
  --type general \
  --title "E2E Test Memory" \
  --content "This is a test memory created by the E2E verification agent." \
  --tag e2e --tag test \
  --importance 0.5
```

**Pass criteria:** Output contains `Stored memory:` with a UUID.

---

### T2.3 — MCP Recall Helper

```bash
cd /home/mohamed/frappe-bench/apps/construction
/home/mohamed/.local/share/pipx/venvs/memorygraphmcp/bin/python scripts/mcp_recall.py \
  "E2E Test Memory" --limit 1
```

**Pass criteria:** Output contains the title `"E2E Test Memory"`.

---

### T2.4 — Git Post-Commit Hook

| Step | Command / Action | Expected Result |
|------|------------------|-----------------|
| 1 | `test -x .git/hooks/post-commit && echo "executable"` | `executable` |
| 2 | `grep -c "mcp_store.py" .git/hooks/post-commit` | `>= 1` |
| 3 | Make a test commit | Hook runs silently |
| 4 | Recall last commit | `mcp_recall.py "Commit $(git log -1 --pretty=%H)"` returns memory |

**Pass criteria:** Commit auto-captured in MCP memory.

---

### T2.5 — Session End Script

```bash
cd /home/mohamed/frappe-bench/apps/construction
echo -e "E2E test session\nDecision: test\nNone\nNone" | \
  python3 scripts/session_end.py --summary "E2E test session" --decisions "test" --no-mcp
```

**Pass criteria:**
- Script completes without error
- `SESSION_MEMORY.md` contains new entry with "E2E test session"

---

## Phase 3: ERPNext MCP Server

### T3.1 — Server Startup

```bash
/home/mohamed/frappe-bench/env/bin/python \
  /home/mohamed/frappe-bench/apps/construction/erpnext-mcp-server/server.py &
# Should start without error. Kill after a few seconds.
kill %1 2>/dev/null || true
```

**Pass criteria:** No startup errors (Frappe initializes, connects to DB).

---

### T3.2 — Tool Listing

Use an MCP client to connect and list tools.

```bash
cd /home/mohamed/frappe-bench
/home/mohamed/frappe-bench/env/bin/python -c "
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test():
    params = StdioServerParameters(
        command='/home/mohamed/frappe-bench/env/bin/python',
        args=['/home/mohamed/frappe-bench/apps/construction/erpnext-mcp-server/server.py']
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f'Tools: {len(tools.tools)}')
            for t in tools.tools:
                print(f'  - {t.name}')

asyncio.run(test())
"
```

**Pass criteria:** 9 tools listed:
- `get_boq_header`
- `get_boq_structure_tree`
- `get_scope_context`
- `list_construction_themes`
- `get_form_layout_profile`
- `get_doctype_schema`
- `get_document`
- `get_doctype_list`
- `run_safe_select`

---

### T3.3 — Read Queries

Run the following via MCP client:

| Tool | Arguments | Expected Result |
|------|-----------|-----------------|
| `list_construction_themes` | `{}` | Array with `>= 1` theme objects |
| `get_doctype_schema` | `{"doctype": "BOQ Item"}` | Object with `fields` array, `>= 30` fields |
| `get_doctype_list` | `{"doctype": "BOQ Item", "limit": 3}` | Array with `<= 3` items |
| `run_safe_select` | `{"sql": "SELECT name FROM tabUser LIMIT 3"}` | Array with `<= 3` user rows |
| `get_doctype_schema` | `{"doctype": "User"}` | Object with `fields` array |

**Pass criteria:** All queries return valid JSON with expected structure.

---

### T3.4 — Safety Guards

Run the following via MCP client:

| Tool | Arguments | Expected Result |
|------|-----------|-----------------|
| `run_safe_select` | `{"sql": "INSERT INTO tabUser (name) VALUES ('test')"}` | Error: *"Write SQL detected. This MCP server is read-only."* |
| `run_safe_select` | `{"sql": "DELETE FROM tabUser WHERE name='test'"}` | Error: *"Write SQL detected."* |
| `run_safe_select` | `{"sql": "DROP TABLE tabUser"}` | Error: *"Write SQL detected."* |
| `get_document` | `{"doctype": "UnknownDocType", "name": "x"}` | Error: *"not in the read-only allowlist"* |
| `get_doctype_schema` | `{"doctype": "UnknownDocType"}` | Error: *"not in the read-only allowlist"* |

**Pass criteria:** All blocked operations return permission errors. No data modified.

---

### T3.5 — Audit Logging

```bash
tail -20 /home/mohamed/frappe-bench/apps/construction/logs/ai_mcp_audit.log
```

**Pass criteria:** Log entries exist for recent tool calls. Format: `TOOL=name | ARGS={...} | STATUS=...`

---

## Agent Registration Verification

### T4.1 — Kimi Code

```bash
kimi mcp list
```

**Pass criteria:** Shows both:
- `memorygraph (stdio): memorygraph`
- `erpnext-construction (stdio): /home/mohamed/frappe-bench/env/bin/python ...`

---

### T4.2 — Codex

```bash
codex mcp list
```

**Pass criteria:** Shows both `memorygraph` and `erpnext-construction` as enabled.

---

### T4.3 — Antigravity

```bash
cat ~/.gemini/config/mcp_config.json | python3 -m json.tool
```

**Pass criteria:** JSON contains both `memorygraph` and `erpnext-construction` under `mcpServers`.

---

### T4.4 — Windsurf

```bash
cat ~/.config/Windsurf/User/settings.json | python3 -m json.tool
```

**Pass criteria:** JSON contains both under `mcp.servers`.

---

## Cross-Cutting Tests

### T5.1 — No Memory Drift

```bash
python3 scripts/ai_context_check.py
```

Then:
```bash
/home/mohamed/.local/share/pipx/venvs/memorygraphmcp/bin/python scripts/mcp_recall.py \
  "BOQ Item schema" --limit 1 | grep -c "cost_item"
```

**Pass criteria:**
- Validation script passes
- MCP recall returns `cost_item` warning
- Live repo schema matches memory

---

### T5.2 — Source-of-Truth Rule

| Step | Action | Expected |
|------|--------|----------|
| 1 | Read `AGENTS.md` | Contains BOQ Item schema warning |
| 2 | Read `docs/ai/SCHEMA_FACTS.md` | Contains same schema |
| 3 | Read `SESSION_MEMORY.md` §5 | Contains same warning |
| 4 | Recall MCP memory | Contains same warning |

**Pass criteria:** All four sources agree on the BOQ Item schema (no `item_code`).

---

### T5.3 — Git Integration

```bash
cd /home/mohamed/frappe-bench/apps/construction
git log --oneline -5
```

**Pass criteria:** Recent commits include:
- `docs: implement AI persistent memory architecture (Phase 1A-D)`
- `docs: implement MCP auto-capture (Phase 2)`
- `feat: implement ERPNext read-only MCP server (Phase 3)`

---

## Test Summary Template

Copy this table and fill in results:

| Phase | Test | Status |
|-------|------|--------|
| 1 | T1.1 AGENTS.md Integrity | ⬜ Pass / ⬜ Fail |
| 1 | T1.2 SESSION_MEMORY.md Integrity | ⬜ Pass / ⬜ Fail |
| 1 | T1.3 docs/ai/ Reference Folder | ⬜ Pass / ⬜ Fail |
| 1 | T1.4 Validation Script | ⬜ Pass / ⬜ Fail |
| 1 | T1.5 Skill Files | ⬜ Pass / ⬜ Fail |
| 2 | T2.1 MemoryGraph Health | ⬜ Pass / ⬜ Fail |
| 2 | T2.2 MCP Store Helper | ⬜ Pass / ⬜ Fail |
| 2 | T2.3 MCP Recall Helper | ⬜ Pass / ⬜ Fail |
| 2 | T2.4 Git Post-Commit Hook | ⬜ Pass / ⬜ Fail |
| 2 | T2.5 Session End Script | ⬜ Pass / ⬜ Fail |
| 3 | T3.1 Server Startup | ⬜ Pass / ⬜ Fail |
| 3 | T3.2 Tool Listing | ⬜ Pass / ⬜ Fail |
| 3 | T3.3 Read Queries | ⬜ Pass / ⬜ Fail |
| 3 | T3.4 Safety Guards | ⬜ Pass / ⬜ Fail |
| 3 | T3.5 Audit Logging | ⬜ Pass / ⬜ Fail |
| 4 | T4.1 Kimi Registration | ⬜ Pass / ⬜ Fail |
| 4 | T4.2 Codex Registration | ⬜ Pass / ⬜ Fail |
| 4 | T4.3 Antigravity Registration | ⬜ Pass / ⬜ Fail |
| 4 | T4.4 Windsurf Registration | ⬜ Pass / ⬜ Fail |
| 5 | T5.1 No Memory Drift | ⬜ Pass / ⬜ Fail |
| 5 | T5.2 Source-of-Truth Rule | ⬜ Pass / ⬜ Fail |
| 5 | T5.3 Git Integration | ⬜ Pass / ⬜ Fail |

**Overall Result:** `___ / 22 tests passed`

---

## Commands for Automated Execution

A single script to run all automated checks:

```bash
#!/bin/bash
cd /home/mohamed/frappe-bench/apps/construction

echo "=== T1.4 Validation Script ==="
python3 scripts/ai_context_check.py || exit 1

echo "=== T2.1 MemoryGraph Health ==="
memorygraph --health | grep -E "Status:|Memories:"

echo "=== T2.2 MCP Store ==="
/home/mohamed/.local/share/pipx/venvs/memorygraphmcp/bin/python scripts/mcp_store.py \
  --type general --title "E2E Test" --content "E2E test memory" --tag e2e --importance 0.5

echo "=== T2.3 MCP Recall ==="
/home/mohamed/.local/share/pipx/venvs/memorygraphmcp/bin/python scripts/mcp_recall.py "E2E Test" --limit 1

echo "=== T3.2-3.5 ERPNext MCP ==="
/home/mohamed/frappe-bench/env/bin/python -c "
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test():
    params = StdioServerParameters(
        command='/home/mohamed/frappe-bench/env/bin/python',
        args=['erpnext-mcp-server/server.py']
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f'Tools: {len(tools.tools)}')

            result = await session.call_tool('list_construction_themes', {})
            print(result.content[0].text[:200])

            result = await session.call_tool('get_doctype_schema', {'doctype': 'BOQ Item'})
            data = json.loads(result.content[0].text)
            print(f'BOQ Item fields: {len(data[\"fields\"])}')

            result = await session.call_tool('run_safe_select', {'sql': 'SELECT name FROM tabUser LIMIT 1'})
            print(result.content[0].text[:200])

            result = await session.call_tool('run_safe_select', {'sql': 'INSERT INTO tabUser (name) VALUES (\"test\")'})
            print(result.content[0].text[:200])

asyncio.run(test())
"

echo "=== T4.1-4.4 Agent Registrations ==="
kimi mcp list 2>/dev/null | grep -c "erpnext-construction" || echo "Kimi: missing"
codex mcp list 2>/dev/null | grep -c "erpnext-construction" || echo "Codex: missing"
grep -c "erpnext-construction" ~/.gemini/config/mcp_config.json || echo "Antigravity: missing"
grep -c "erpnext-construction" ~/.config/Windsurf/User/settings.json || echo "Windsurf: missing"

echo "=== Done ==="
```

---

*Run this report after any major change to verify system integrity.*
