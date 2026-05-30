# Session Memory — Construction ERP
**LAST UPDATED:** 2026-05-31
**UPDATED BY:** Kimi Code (review + Phase 1A–D implementation)

---

## 1. Project Snapshot
- **Total commits:** 117
- **Current branch:** `feature/vite-ui-v1`
- **Last session date:** 2026-05-31
- **Python version:** 3.14 (venv: `/home/mohamed/frappe-bench/env`)
- **AGENTS.md status:** Rewritten from Scope Context dev report → agent context file
- **New files created:** `SESSION_MEMORY.md`, `docs/ai/CONTEXT_INDEX.md`, `docs/ai/SCHEMA_FACTS.md`, `docs/ai/CODING_PATTERNS.md`, `scripts/ai_context_check.py`

---

## 2. Completed Work (Stable — Do Not Modify Without Approval)

### Theme System ✅
- 22 CSS files, 14,884 total lines
- Three-layer architecture: tokens → base → v16_adapter
- 54-token CSS variable system, dark/light modes, RTL support
- Server-side theme resolution via `boot_session` hook (no FOUC)
- 17 whitelisted endpoints / 34 functions total in `api/theme_api.py`
- Per-user: User Desk Theme DocType (25 fields); site-wide: Construction Theme DocType (94 fields)
- **Note:** Only 6 CSS files are registered in `hooks.py` `app_include_css`. The remaining 16 are generated themes, login/email/print themes, or test files.

### Scope Context ✅
- User Scope Context DocType: company, cost_center, project, department, branch
- Query injection via `permission_query_conditions` (`overrides/scope_query.py`)
- NestedSet lft/rgt expansion for cost center descendants
- Redis caching (5-min TTL), admin bypass, column guards
- 13 integration tests + 10 unit tests passing (documented in prior report)

### BOQ Foundation ✅
- BOQ Header, BOQ Item, BOQ Structure, BOQ Item Stage DocTypes
- 12 service modules: lifecycle, accounting, export, import, migration, operational, lookups, scope filters, transaction validation, scope resolution, WBS generator
- BOQ API (CRUD + tree operations) in `api/boq_api.py` (9 whitelisted endpoints)
- **WARNING:** BOQ Item uses `cost_item` (Data), NOT `item_code` (Link→Item)

### Searchable Dropdown ✅
- Global override for all Link fields (`ct_link_control.js`)
- Global override for all Select fields (`ct_select_control.js`)
- SearchableDropdownEnhancer class auto-applies to all form fields

### Arabic Localization ✅
- Full RTL support, Arabic translations seeded via patches v6.0–v6.6
- `translated_doctypes` in `hooks.py` covers 12 DocTypes

### Form Layout Engine (VFC) ✅ Phase 1+2
- Form Layout Profile DocType (`sections_json` blob, 12 fields)
- `vfc_layout_engine.js` (847 lines): runtime field re-parenting
- `vite_layout_controls.js`: drag/resize panel + Sections Editor tab
- `vfc_sections.css` (177 lines): section card styles
- Phase 3+: additional layout features (in progress)

### Vite UI ✅ Phase 0+1+2
- Visual foundation (`vite_form_override.css`, `vite_list_override.css`)
- Form config panel redesigned as centered dialog modal
- Dynamic layout controls via `frappe.require`
- DraggablePanel.jsx with panel dragging/resizing
- Built bundle: `construction.bundle.XR6HIDAQ.js`

---

## 3. In Progress (Active Work — Updated After Every Session)

### Current Sprint: Form Layout Engine Phase 3+ / BOQ Accounting
#### Task 1: AI Memory Architecture Implementation — Status: In Progress
- **Started:** 2026-05-31
- **Files being modified:** `AGENTS.md`, `SESSION_MEMORY.md`, `docs/ai/*`, `scripts/*`, `construction-erp-coder/*`
- **Decisions made:**
  - Repo files are source of truth; MCP/skills are adapters only
  - `AGENTS.md` rewritten from dev report to agent context
  - `SESSION_MEMORY.md` created as living sprint document
  - `docs/ai/` created for deep references (schemas, patterns, index)
  - Validation script created to prevent stale memory
  - Git post-commit hook installed for auto-capture
  - `mcp_store.py`, `mcp_recall.py`, `session_end.py` helpers created
- **Blockers:** None
- **Next action:** Phase 2 MCP auto-capture operational; proceed to Phase 3 (ERPNext read-only MCP server) when needed

#### Task 2: Form Layout Engine Phase 3+ — Status: In Progress
- **Started:** Prior to 2026-05-30
- **Files being modified:** `vfc_layout_engine.js`, `vite_layout_controls.js`, `vfc_sections.css`
- **Blockers:** None
- **Next action:** Continue layout feature expansion

#### Task 3: BOQ Accounting Integration — Status: In Progress
- **Started:** Prior to 2026-05-30
- **Files being modified:** `services/boq_accounting.py`, `services/boq_transaction_validation.py`
- **Blockers:** None
- **Next action:** Continue integration with Purchase Order / Invoice / Stock Entry hooks

---

## 4. Architecture Decisions Log

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2026-04-15 | CSS Variable Token Architecture (3-level) | Complete visual override without core Frappe edits | Active |
| 2026-04-20 | Server-side theme resolution | Prevent FOUC, cross-device sync | Active |
| 2026-04-22 | `frappe.db.set_value()` for theme writes | Avoid TimestampMismatchError on concurrent tab switches | Active |
| 2026-04-25 | Hybrid CSS strategy (static + dynamic) | Fast initial render + runtime customization | Active |
| 2026-05-01 | NestedSet (lft/rgt) for BOQ Structure | Better subtree queries vs adjacency list | Active |
| 2026-05-10 | ERPNext Price List for rate lookups | Avoids custom table duplication | Active |
| 2026-05-20 | BOQ Item uses `cost_item` (Data) not `item_code` (Link) | BOQ items are specification lines, not ERPNext items | Active |
| 2026-05-31 | Repo-local files as source of truth for AI memory | Prevents drift between MCP, skills, and repo state | Active |
| 2026-05-31 | MCP memory treated as cache/index, not authority | Safer fallback if MCP server is offline or stale | Active |

---

## 5. Known Issues & Gotchas

| Issue | Location | Workaround | Priority |
|-------|----------|-----------|----------|
| CSS not loading after adding new file | `hooks.py` `app_include_css` | Register file + bump `?v=` param | P0 |
| Only 6 of 22 CSS files are in `app_include_css` | `hooks.py` | Generated/special-purpose files load conditionally; do not blindly add all 22 | P0 |
| BOQ Item has no `item_code` / `item_name` | `boq_item.json` | Use `cost_item` (Data) + `structure` (Link→BOQ Structure) | P0 |
| JS inline styles conflict with CSS variables | `theme_loader_v24.js` | CSS-only approach enforced | P0 |
| TimestampMismatchError on concurrent theme switches | `theme_api.py` | `frappe.db.set_value(..., update_modified=False)` | P1 |
| v16 DOM selectors need verification | All JS files | Run `verify_v16_selectors.js` after DOM changes | P1 |
| Admin bypasses ALL scope filters | `scope_query.py` | Always test with non-admin user | P1 |
| Python 3.10 quote-nesting compatibility | All `.py` files | Commit `d7b5186` made f-strings safe; keep new code compatible | P1 |

---

## 6. Session Log (Append-Only — Most Recent First)

### Session 2026-05-31 — Agent: Kimi Code (Phase 2)
- **Worked on:** MCP auto-capture infrastructure (Phase 2)
- **Decisions:**
  - Created `scripts/mcp_store.py` — CLI to store memories via MCP stdio
  - Created `scripts/mcp_recall.py` — CLI to recall memories via MCP stdio
  - Created `scripts/session_end.py` — interactive session summary capture
  - Created `scripts/install_git_hooks.sh` + `.git/hooks/post-commit` — auto-capture on every commit
  - Updated `AGENTS.md` §7 with auto-capture protocol and helper script references
  - Verified `mcp_store.py` and `mcp_recall.py` work end-to-end
  - Verified git post-commit hook stores commit memory automatically
- **Issues found:**
  - Plain `python3` cannot import memorygraph's pydantic due to ABI mismatch
  - Fix: all MCP scripts and hooks use `/home/mohamed/.local/share/pipx/venvs/memorygraphmcp/bin/python`
- **Files changed:**
  - `scripts/mcp_store.py` (created)
  - `scripts/mcp_recall.py` (created)
  - `scripts/session_end.py` (created)
  - `scripts/install_git_hooks.sh` (created)
  - `.git/hooks/post-commit` (installed)
  - `AGENTS.md` (updated §7)
- **Next steps:** Use `session_end.py` after every session; commits auto-capture via hook

### Session 2026-05-31 — Agent: Kimi Code (Phase 1)
- **Worked on:** Engineering review + Phase 1A–D implementation
- **Decisions:**
  - Approved revised architecture: repo files authoritative, MCP/skills are adapters
  - Rewrote `AGENTS.md` from Scope Context report to agent context file
  - Created `SESSION_MEMORY.md`
  - Created `docs/ai/` reference folder
  - Created `scripts/ai_context_check.py`
  - Corrected plan: ADR count = 7 (not 4); CSS registration nuance added
- **Issues found:**
  - Original plan over-claimed MCP capability ("no manual updates needed")
  - Original plan included unsafe `run_bench_command` in ERPNext MCP v1
  - AGENTS.md was a 234-line dev report, not an agent onboarding file
- **Files changed:**
  - `AGENTS.md` (rewritten)
  - `SESSION_MEMORY.md` (created)
  - `docs/ai/CONTEXT_INDEX.md` (created)
  - `docs/ai/SCHEMA_FACTS.md` (created)
  - `docs/ai/CODING_PATTERNS.md` (created)
  - `scripts/ai_context_check.py` (created)
- **Next steps:**
  - Run validation script to verify ground truth
  - Seed MCP memory from repo files only (Phase 2)
  - Keep `SESSION_MEMORY.md` updated manually as fallback

### Session 2026-05-30 — Agent: Antigravity
- **Worked on:** Plan revision — `CONSTRUCTION_ERP_AI_MEMORY_PLAN.md` v2.1
- **Decisions:** Updated plan to reflect actual repo state
- **Issues found:** `AGENTS.md` exists but needs content overhaul; BOQ Item schema differs from v1.0 plan
- **Files changed:** `CONSTRUCTION_ERP_AI_MEMORY_PLAN.md`
- **Next steps:** Execute Phase 1 — update AGENTS.md, create SESSION_MEMORY.md
