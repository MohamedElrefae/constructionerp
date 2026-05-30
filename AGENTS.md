# Construction ERP — AI Agent Context File
> READ THIS FIRST at the start of every session.

## 1. Project Identity
- **Name:** Construction ERP (Frappe/ERPNext custom app)
- **App name:** `construction` (used in imports: `from construction.xxx import yyy`)
- **Repo root:** `/home/mohamed/frappe-bench/apps/construction`
- **Author:** Mohamed Elrefae (solo civil engineer developer)
- **License:** MIT
- **Current branch:** `feature/vite-ui-v1`
- **Total commits:** 117
- **Latest commit:** `d7b5186` — fix: f-strings compatible with Python 3.10 quote nesting rules

## 2. Tech Stack
- **Backend:** Python 3.14 (venv), Frappe Framework (v15/v16 dual-compat); code must remain Python 3.10 quote-nesting compatible
- **Frontend:** Vanilla JS + JSX components (Vite bundle), CSS Variables
- **Database:** MariaDB 10.6+, Redis (scope hierarchy cache, 5-min TTL)
- **Bundler:** Vite (`construction.bundle.XR6HIDAQ.js`)
- **Testing:** Python `unittest` (12 top-level + 8 DocType test files), `fast-check` (JS property tests)

## 3. Architecture — Four Core Systems

### 3A. Theme System
- **22 CSS files** exist in `public/css/`, **14,884 total lines**
- **Only 6 CSS files are registered in `hooks.py` `app_include_css`** (see §6). The rest are generated themes, login/email/print themes, or test files.
- Three-layer cascade:
  1. `modern_theme_tokens.css` (284 lines, 54 CSS variables)
  2. `modern_theme_base.css` (5,101 lines, component overrides)
  3. `modern_theme_v16_adapter.css` (2,144 lines, v16 DOM mapping)
- Combined file: `modern_theme.css` (4,258 lines) — this is what Frappe actually loads
- Dark mode namespace: `html.ct-enterprise[data-theme="dark"]`
- Server-side resolution via `boot_session` hook (`construction.api.theme_api.add_theme_to_boot`) — no FOUC
- **17 whitelisted endpoints** / **34 functions total** in `api/theme_api.py`
- Per-user: **User Desk Theme** DocType (25 fields); site-wide: **Construction Theme** DocType (94 fields) + **Modern Theme Settings** DocType

### 3B. Scope Context System
- **User Scope Context** DocType: company, cost_center, project, department, branch
- Query injection via `permission_query_conditions` hook (`overrides/scope_query.py`)
- NestedSet `lft`/`rgt` expansion for cost center descendants
- Redis cache (5-min TTL), column-existence guards, admin bypass
- Integration tests: 13 passed (documented in prior report)

### 3C. BOQ System (Bill of Quantities)
- **BOQ Header** (master) → **BOQ Structure** (WBS tree, NestedSet) → **BOQ Item** (line item)
- **CRITICAL — BOQ Item schema:**
  - Uses `cost_item` (Data field — free text), **NOT** `item_code` (Link→Item)
  - Uses `structure` (Link→BOQ Structure), `quantity`, `unit` (Link→UOM)
  - Cost fields: `est_unit_cost`, `est_unit_price`, `contract_unit_price`, `line_total`
  - Margin fields: `overhead_pct`, `profit_pct`, `overhead_amount`, `profit_amount`, `calculated_sell_price`
  - Progress fields: `quantity_executed`, `quantity_certified`
  - **There is NO `item_code` or `item_name` field.** BOQ items are specification lines, not ERPNext Items.
- 12 service modules in `services/` (lifecycle, accounting, export, import, migration, operational, lookups, scope filters, transaction validation, scope resolution, WBS generator)
- BOQ API (`api/boq_api.py`): 9 whitelisted endpoints
- BOQ Structure uses NestedSet (`lft`, `rgt`, `old_parent`, `is_group`, `wbs_code`)

### 3D. Form Layout Engine (VFC)
- **Form Layout Profile** DocType: stores `sections_json` for each `reference_doctype`
- `vfc_layout_engine.js` (847 lines): runtime field re-parenting into custom sections
- `vite_layout_controls.js` (dynamic): drag/resize panel + Sections Editor tab
- `vfc_sections.css` (177 lines): section card styles
- Status: Phase 1+2 complete (drag/resize + section editor), Phase 3+ in progress

## 4. Critical Conventions (Non-Negotiable)
1. **All SQL:** parameterized queries ONLY — never f-string SQL injection
   - ✅ `frappe.db.sql("SELECT * FROM \`tabBOQ Item\` WHERE name = %(name)s", {"name": name})`
   - ❌ `frappe.db.sql(f"SELECT * FROM \`tabBOQ Item\` WHERE name = '{name}'")`
2. **All API endpoints:** `@frappe.whitelist()` decorator required
3. **CSS:** always `!important` for Frappe cascade override
4. **New CSS file?** Register in `hooks.py` `app_include_css` AND bump `?v=` param to bust cache
5. **DOM selectors:** must work on both v15 AND v16 (dual-compat)
6. **Theme writes:** use `frappe.db.set_value(..., update_modified=False)` not `doc.save()` (avoids TimestampMismatchError)
7. **Scope tests:** always test as non-admin user (admin bypasses all scope filters)
8. **Python compatibility:** venv is Python 3.14, but code must remain Python 3.10 quote-nesting safe

## 5. Active Workstreams
> Read `SESSION_MEMORY.md` for the current sprint state.
>
> As of last update (2026-05-30):
> - Form Layout Engine Phase 3+ — in progress
> - BOQ Accounting Integration — in progress
> - Cost Estimation (CostItem) — not started
> - Procurement (PlantResource) — not started

## 6. Key Files
| Purpose | Path |
|---------|------|
| **All CSS/JS registrations** | `construction/hooks.py` (app_include_css has 6 files; app_include_js has 20+ files) |
| **Boot session hook** | `construction/boot.py` |
| **BOQ CRUD API** | `construction/api/boq_api.py` (9 whitelisted endpoints) |
| **Theme API** | `construction/api/theme_api.py` (17 whitelisted endpoints) |
| **Scope query injection** | `construction/overrides/scope_query.py` |
| **Form Layout API** | `construction/construction/api/layout_api.py` |
| **Architecture decisions** | `ADR.md` (7 accepted ADRs), `docs/ADR-001-accounting-dimension.md` |
| **CSS token reference** | `docs/token_reference.md` (54 tokens) |
| **Hook matrix** | `docs/hook_matrix.md` |
| **Developer onboarding** | `docs/onboarding.md` |
| **Session state** | `SESSION_MEMORY.md` (living document) |
| **Schema facts** | `docs/ai/SCHEMA_FACTS.md` |
| **Coding patterns** | `docs/ai/CODING_PATTERNS.md` |

## 7. Memory Protocol

### For All Agents (Static Files)
1. Read this file (`AGENTS.md`) first.
2. Read `SESSION_MEMORY.md` for current sprint state.
3. If you need schema details, read `docs/ai/SCHEMA_FACTS.md`.
4. If you need code patterns, read `docs/ai/CODING_PATTERNS.md`.

### For MCP-Enabled Agents (Auto-Capture)

**MCP memory is a cache, not authority.** If recalled memory conflicts with live repo files, **live repo files win**.

#### Session Start (MANDATORY)
1. Execute `recall_memories` with query "construction erp current state"
2. Summarize recalled context before starting work
3. Verify critical facts against the live repo before acting

#### During Work (Automatic — No Prompting Needed)
Store memory on ANY of these events:
- **Git commit**: what changed and why
- **Bug fix**: problem description + solution applied
- **Architecture decision**: decision + rationale
- **Pattern discovery**: reusable code pattern found
- **Error encountered**: error message + how it was fixed

Use these helpers when available:
```bash
# Store a memory manually
python3 scripts/mcp_store.py --type fix --title "..." --content "..." --tag python --importance 0.9

# Recall memories
python3 scripts/mcp_recall.py "BOQ Item schema" --limit 3
```

#### Session End (MANDATORY)
1. Store summary of what was accomplished
2. Update `SESSION_MEMORY.md` §3 and §6 as fallback

```bash
# Interactive session capture
python3 scripts/session_end.py
```

### External Auto-Capture (Git Hooks)
A `post-commit` git hook is installed. Every commit automatically stores a memory to MCP with:
- Commit hash, author, message
- List of changed files
- Type: `code_pattern` | Importance: 0.6

To install/reinstall hooks:
```bash
bash scripts/install_git_hooks.sh
```

### Conflict Resolution
If MCP memory conflicts with any live repo file (`AGENTS.md`, `SESSION_MEMORY.md`, DocType JSON), **the repo file wins.** Always re-run `scripts/ai_context_check.py` when schemas change.

---
*Last updated: 2026-05-31*  
*Update this file only when project identity, tech stack, or core architecture changes.*
