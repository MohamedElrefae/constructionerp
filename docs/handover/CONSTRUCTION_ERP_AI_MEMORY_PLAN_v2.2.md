# Construction ERP — Persistent Memory & AI Agent Integration Plan

**Document ID:** CON-ERP-AI-MEM-001  
**Version:** 2.2 (Revised — Repo-Authoritative Architecture)  
**Date:** 2026-05-31  
**Author:** AI Systems Architect + Engineering Review (Kimi Code)  
**Status:** Approved for Implementation  
**Classification:** Internal — Engineering  
**Repo Root:** `/home/mohamed/frappe-bench/apps/construction`

---

## 1. Document Purpose & Audience

This document presents a concrete, step-by-step implementation plan for adding persistent memory capabilities to the Construction ERP project, enabling continuity across AI coding agent sessions (Antigravity, OpenCode, Codex, Kimi Code, Claude Code, Cursor).

**Version 2.2 changes from v2.1:**

- **Architecture renamed:** From "Hybrid Persistent Memory" to **"Repo-Authoritative Memory Architecture with MCP/Skill Adapters"**
- **Source-of-truth rule added:** Repo-local files (`AGENTS.md`, `SESSION_MEMORY.md`) override all other memory layers
- **MCP repositioned:** Treated as **cache/index**, not replacement for repo-local files
- **ADR count corrected:** 7 accepted ADRs (not 4)
- **CSS registration clarified:** Only 6 of 22 CSS files are registered in `hooks.py` `app_include_css`; the rest are generated, conditional, or test files
- **Phase 1D added:** `scripts/ai_context_check.py` validation script as a gating deliverable
- **docs/ai/ added:** Formal deliverable for deep reference files
- **ERPNext MCP hardened:** `run_bench_command` removed; v1 is read-only only
- **Agent compatibility matrix added:** Verified vs. assumed behavior
- **Memory drift & stale-memory risks explicitly documented**
- **Test count corrected:** 23 Python test files total (12 top-level + 8 DocType + 3 misc)

**Target audience:** Solo developer (Mohamed Elrefae) + any AI agent onboarding to the project  
**Estimated implementation effort:** 3–5 weeks (part-time, alongside feature development)

---

## 2. Problem Statement (Current State)

### 2.1 The Context Loss Problem

The Construction ERP project is being developed by a solo civil engineer using multiple AI coding agents. Every new session starts with zero context about:

- What was built in previous sessions
- Active workstreams and their current state
- Architectural decisions and their rationale (`ADR.md` exists but agents don't read it automatically)
- Coding conventions, patterns, and constraints
- Known issues, blockers, and technical debt
- The relationship between BOQ, theming, Form Layout Engine, scope context, and Vite UI modules

### 2.2 Impact Quantification

| Metric | Current State (No Memory) | Target State (With Memory) |
| --- | --- | --- |
| Time to context-load per session | 8–15 minutes | 30–60 seconds |
| Sessions per week | 5–10 | 5–10 (unchanged) |
| Hours lost to re-explaining per month | 3–12 hours | 0.5–2 hours |
| Agent coding accuracy (first attempt) | ~40% | ~75% |
| Cross-agent knowledge sharing | None | Full continuity |

### 2.3 Root Cause Analysis

LLM-based AI agents are stateless by design. Each session is an independent inference request with no persistent memory store. The only solution is to add an external persistent memory layer that:

1. Captures context at session end
2. Injects context at session start
3. Is accessible to all agents regardless of vendor

---

## 3. Current Repository State (as of 2026-05-31)

> This section is the ground truth for all agents. Update it as the project evolves.

### 3.1 Repository Location

```
/home/mohamed/frappe-bench/apps/construction/
```

### 3.2 Branch & Git Status

| Item | Value |
| --- | --- |
| Current branch | `feature/vite-ui-v1` |
| Tracking branches | `origin/feature/vite-ui-v1`, `origin/develop` |
| Total commits | 117 |
| Latest commit | `d7b5186` — fix: f-strings compatible with Python 3.10 quote nesting rules |

### 3.3 Tech Stack (Actual)

| Layer | Technology |
| --- | --- |
| Backend framework | Python 3.14 (via venv), Frappe v15/v16 dual-compat; code should remain Python 3.10 quote-nesting compatible |
| Database | MariaDB 10.6+, Redis (caching, 5-min TTL for scope) |
| Frontend — forms | Vanilla JS, JSX components (DraggablePanel, Sidebar, TreeView, etc.) |
| Frontend — styles | 22 CSS files, 14,884 total lines; **6 registered in `hooks.py`** |
| Bundler | Vite (bundle: `construction.bundle.XR6HIDAQ.js`) |
| Testing — Python | `unittest` (23 Python test files; 12 top-level + 8 DocType + 3 misc) |
| Testing — JS | `fast-check` (property-based testing in `tests/node_modules`) |

### 3.4 Complete DocType Registry

| DocType | Module | Status | Key Fields |
| --- | --- | --- | --- |
| **BOQ Header** | BOQ | ✅ Complete | project, boq_type (Tender/Contract/Variation), status (Draft/Pricing/Frozen/Locked), version, total_contract_value, total_estimated_value, total_budgeted_cost, locked_by, locked_date |
| **BOQ Item** | BOQ | ✅ Complete | structure (→BOQ Structure), boq_header, item_type (Measured Work/Provisional Sum/Prime Cost/Daywork/Contingency/TBD), cost_item, owner_page, owner_ref_no, owner_file_ref, quantity, unit (→UOM), factor, has_stages, est_unit_cost, est_unit_price, contract_unit_price, line_total, overhead_pct, profit_pct, overhead_amount, profit_amount, calculated_sell_price, est_line_total, quantity_executed, quantity_certified |
| **BOQ Structure** | BOQ | ✅ Complete | title, wbs_code, parent_structure (→BOQ Structure), boq_header, project, is_group, description, owner_page, owner_ref_no, owner_file_ref, lft, rgt, old_parent |
| **BOQ Item Stage** | BOQ | ✅ Complete | phasing/staging classification |
| **User Scope Context** | Scope | ✅ Complete | user, company, cost_center, project, department, branch, scope_version (auto-increment), last_active_at, client_id |
| **Construction Settings** | Config | ✅ Complete | enable/disable scope context per dimension |
| **Construction Theme** | Theme | ✅ Complete | theme_name, is_active, theme_type, primary_color, accent_color, 40+ color fields across tabs (General/Login/Buttons/Tables/Widgets/Input/Navbar/Footer/Semantic/Preview/Advanced), custom_css |
| **User Desk Theme** | Theme | ✅ Complete | per-user theme + typography preferences |
| **Modern Theme Settings** | Theme | ✅ Complete | site-wide theme defaults |
| **Form Layout Profile** | Layout | ✅ Complete (Phase 1+2) | reference_doctype, profile_name, enabled, is_default, is_system, for_role, priority, layout_version, sections_json |
| **Direct Labor Designation** | BOQ | ✅ Complete | labor classification |
| **CostItem** | BOQ | 🔶 Partial | cost_item_code, category, title, description, unit, base_productivity, default_wastage_pct, status, total_direct_cost |
| **PlantResource** | BOQ | 🔶 Partial | resource_code, equipment_type, ownership_cost_hourly, operating_cost_hourly, mobilization_cost |
| **Journal Entry** | Accounting | 🔶 Override | ERPNext override doctype dir contains `journal_entry.js` only; no JSON/Python controller |

### 3.5 Complete File Map

```
apps/construction/
├── AGENTS.md                         ← REWRITTEN — agent context file
├── ADR.md                            ← EXISTS — 7 accepted ADRs
├── README.md                         ← Standard Frappe README
├── SENIOR_ENGINEER_AUDIT_REPORT.md   ← EXISTS — reference for conventions
├── SESSION_MEMORY.md                 ← NEW — living session state
├── CONSTRUCTION_ERP_AI_MEMORY_PLAN_v2.2.md ← This document
├── docs/                             ← 29 files + new ai/ subdirectory
│   ├── ai/
│   │   ├── CONTEXT_INDEX.md          ← NEW — memory file map
│   │   ├── SCHEMA_FACTS.md           ← NEW — verified DocType schemas
│   │   └── CODING_PATTERNS.md        ← NEW — canonical code patterns
│   ├── ADR-001-accounting-dimension.md
│   ├── arabic_localization_*.md      ← Arabic/RTL localization docs
│   ├── boq_integration_*.md          ← BOQ integration specs
│   ├── boq_scope_context_*.md        ← Scope context filtering docs
│   ├── form_layout_engine_team_letter.md
│   ├── hook_matrix.md                ← Frappe hook reference
│   ├── onboarding.md                 ← Developer onboarding
│   ├── runbook.md                    ← Ops runbook
│   ├── token_reference.md            ← CSS token reference (54 tokens)
│   └── troubleshooting.md            ← Known issues
└── construction/                     ← Python package
    ├── hooks.py                      ← 6 CSS + 20+ JS registrations
    ├── boot.py                       ← Boot session hook (scope + theme inject)
    ├── install.py                    ← App install logic (26,450 bytes)
    ├── api/
    │   ├── boq_api.py               ← BOQ CRUD endpoints (9 whitelisted)
    │   ├── boq_link_queries.py      ← Link field query helpers
    │   ├── modern_form_api.py       ← Form API
    │   ├── scope_context_api.py     ← Scope context endpoints (4 whitelisted)
    │   ├── theme_api.py             ← Theme endpoints (17 whitelisted, 33 functions total)
    │   ├── translation_tools.py     ← Arabic translation tools
    │   ├── uninstall_desk_theme.py  ← Theme cleanup
    │   └── workspace_api.py         ← Workspace management
    ├── services/
    │   ├── boq_accounting.py        ← BOQ ↔ Accounting integration
    │   ├── boq_export_service.py    ← Excel/PDF export
    │   ├── boq_import_service.py    ← Excel import
    │   ├── boq_lifecycle.py         ← Status transitions (Draft→Pricing→Frozen→Locked)
    │   ├── boq_lookups.py           ← Rate/price lookups
    │   ├── boq_migration_service.py ← Data migration
    │   ├── boq_operational.py       ← Operational BOQ ops
    │   ├── boq_scope_filters.py     ← BOQ + scope integration
    │   ├── boq_transaction_validation.py ← Transaction guards
    │   ├── scope_resolution.py      ← Scope hierarchy resolution
    │   └── wbs_generator.py         ← WBS code auto-generation
    ├── overrides/
    │   ├── scope_query.py           ← permission_query_conditions hook
    │   ├── scope_enforcement.py     ← Doc-level permission enforcement
    │   └── switch_theme*.py         ← Theme switching variants
    ├── construction/                 ← DocType module
    │   ├── api/layout_api.py        ← Form Layout Engine API (274 lines)
    │   ├── doctype/                  ← (see DocType Registry above)
    │   └── utils/scope_validation.py ← Cross-dimension validation
    ├── public/
    │   ├── css/                      ← 22 CSS files, 14,884 total lines
    │   │   ├── modern_theme.css         (4,258 lines — combined, REGISTERED in hooks.py)
    │   │   ├── modern_theme_base.css    (5,101 lines — component overrides)
    │   │   ├── modern_theme_tokens.css  (284 lines — 54 CSS variable tokens)
    │   │   ├── modern_theme_v16_adapter.css (2,144 lines — v16 DOM mapping)
    │   │   ├── modern_theme_variables_v16.css (642 lines)
    │   │   ├── modern_theme_tree.css    (459 lines)
    │   │   ├── vite_form_override.css   (935 lines — Vite UI Phase 1, REGISTERED)
    │   │   ├── vfc_sections.css         (177 lines — Form Layout Engine, REGISTERED)
    │   │   ├── vite_list_override.css   (248 lines, REGISTERED)
    │   │   ├── vite_extensions.css      (66 lines, REGISTERED)
    │   │   ├── scope_context.css        (48 lines, REGISTERED)
    │   │   ├── email_theme.css          (61 lines — email only)
    │   │   ├── login_theme.css          (0 lines)
    │   │   ├── login_theme_light.css    (194 lines — login page only)
    │   │   ├── searchable_dropdown.css  (171 lines)
    │   │   ├── print_theme.css          (69 lines — print/PDF only)
    │   │   └── theme_*.css              (generated runtime theme files, NOT registered)
    │   └── js/
    │       ├── ../dist/js/construction.bundle.XR6HIDAQ.js ← built Vite bundle
    │       ├── construction.bundle.js   ← Vite bundle source entry
    │       ├── vfc_layout_engine.js     ← Form Layout Engine (VFC, 847 lines)
    │       ├── vite_layout_controls.js  ← Layout drag/resize controls
    │       ├── theme_loader_v24.js      ← Active theme loader (v24)
    │       ├── scope_context.js         ← ScopeContext class
    │       ├── scope_context_ui.js      ← Scope UI components
    │       ├── boq_filters.js / boq_structure_tree.js
    │       ├── construction_export_menu.js / print_settings_dialog.js
    │       ├── scope_context_form_defaults.js / scope_context_list_filter.js
    │       ├── searchable_dropdown/     ← base class, utils, config files
    │       ├── overrides/
    │       │   ├── ct_select_control.js ← SearchableDropdown for all <select>
    │       │   └── ct_link_control.js   ← SearchableDropdown for all Link fields
    │       └── components/
    │           ├── DraggablePanel.jsx
    │           ├── ExportButtons.jsx
    │           ├── FormField.jsx
    │           ├── FormLayoutControls.jsx
    │           ├── Sidebar.jsx
    │           ├── TreeView.jsx
    │           ├── UltimateButton.jsx
    │           └── UnifiedCRUDForm.jsx
    ├── tests/                        ← 12 top-level Python tests
    └── patches/                      ← v6.0 through v6.6 migration patches
```

### 3.6 Completed Work Inventory

| Module | Status | Evidence |
| --- | --- | --- |
| **CSS Theme System** | ✅ Complete | 14,884 lines CSS, 22 files, 54-token system, dark/light modes |
| **Construction Theme DocType** | ✅ Complete | 94 fields, multi-tab UI, server-side resolution |
| **User Desk Theme DocType** | ✅ Complete | Per-user theme + typography |
| **Theme API** | ✅ Complete | 17 whitelisted endpoints, 33 functions total in `theme_api.py` |
| **Scope Context DocType** | ✅ Complete | Historical report records 13 integration tests passing |
| **Scope Query Injection** | ✅ Complete | NestedSet lft/rgt, column guards, Redis cache |
| **BOQ Foundation** | ✅ Complete | BOQ Header, Item, Structure, Item Stage |
| **BOQ Services** | ✅ Complete | 11 service modules (lifecycle, accounting, export, import, etc.) |
| **BOQ API** | ✅ Complete | CRUD + tree operations in `boq_api.py` |
| **Searchable Dropdown** | ✅ Complete | Global override for all Link + Select fields |
| **Arabic Localization** | ✅ Complete | RTL, full Arabic translations, patch versions v6.0–v6.6 |
| **Form Layout Engine (VFC)** | ✅ Phase 1+2 | Form Layout Profile DocType, drag/resize panel, section editor |
| **Vite UI Phase 0+1+2** | ✅ Complete | Visual foundation, layout controls, dynamic form loading |
| **CostItem DocType** | 🔶 Partial | `cost_item.json` exists with productivity/wastage/direct-cost fields |
| **PlantResource DocType** | 🔶 Partial | `plant_resource.json` exists with equipment hourly-cost fields |
| **Journal Entry Override** | 🔶 Stub | Directory contains `journal_entry.js`; no custom JSON/Python controller |

### 3.7 Active Workstreams (as of 2026-05-31)

| Module | Status | Branch |
| --- | --- | --- |
| AI Memory Architecture (Phase 1) | 🟡 In Progress | `feature/vite-ui-v1` |
| Form Layout Engine — Phase 3+ | 🟡 In Progress | `feature/vite-ui-v1` |
| BOQ Accounting Integration | 🟡 In Progress | `feature/vite-ui-v1` |
| Cost Estimation (CostItem) | ⬜ Not Started | — |
| Procurement (PlantResource) | ⬜ Not Started | — |

---

## 4. Known Issues & Gotchas

> Critical reference for all agents. Read before writing any code.

| Issue | Location | Workaround | Priority |
| --- | --- | --- | --- |
| CSS files MUST be registered in `hooks.py` `app_include_css` | `hooks.py` L87–L97 | Always verify after adding CSS; only 6 files are registered; generated/special files load conditionally | P0 |
| JS inline styles conflict with CSS variables | `theme_loader_v24.js` | CSS-only approach enforced | P0 |
| venv is Python 3.14, but compatibility with Python 3.10 quote nesting is intentional | All .py files | Commit `d7b5186` made f-strings 3.10-safe; keep new code compatible | P1 |
| v16 DOM selectors need dual-compat (v15+v16) | All JS files | Test with `verify_v16_selectors.js` after DOM changes | P1 |
| `TimestampMismatchError` on concurrent theme switches | `theme_api.py` | Use `frappe.db.set_value(..., update_modified=False)` not `doc.save()` | P1 |
| `BOQ Item` schema is NOT a simple item+rate — has cost estimation sections | `boq_item.json` | See actual schema in §3.4; no `rate` field — use `est_unit_cost`/`contract_unit_price` | P0 |
| `BOQ Item` has no `item_code`/`item_name` — uses `cost_item` (Data) + `structure` (Link) | `boq_item.json` | Do not assume ERPNext Item link; BOQ items are specification lines | P0 |
| Shadow DOM components need separate CSS injection | Theme system | Document per component when encountered | P2 |
| Admin bypasses all scope filters — test as non-admin user | `scope_query.py` | Always test scope features with a non-admin test user | P1 |

---

## 5. Architecture Decisions (Summary)

> Full ADRs are in `ADR.md` (7 accepted) and `docs/ADR-001-accounting-dimension.md`.

| ADR | Decision | Status |
| --- | --- | --- |
| ADR-001 | CSS Variable Token Architecture (3-level: root → theme → Frappe mapping) | Accepted |
| ADR-002 | Server-Side Theme Resolution (via `boot_session` hook, no FOUC) | Accepted |
| ADR-003 | Direct DB updates for theme persistence (avoid `TimestampMismatchError`) | Accepted |
| ADR-004 | Hybrid CSS Strategy (static tokens + dynamic API layer) | Accepted |
| ADR-005 | Shadow DOM Token Injection | Accepted |
| ADR-006 | White-Label Branding Strategy | Accepted |
| ADR-007 | Version Query String Strategy | Accepted |
| Decision | NestedSet (lft/rgt) for BOQ Structure and Cost Center hierarchies | Active |
| Decision | ERPNext Price List for rate lookups (avoids custom table duplication) | Active |
| Decision | Dispatcher pattern for BOQ service operations | Active |
| Decision | Dual v15/v16 compatibility required for all DOM selectors | Active |
| Decision | Repo-local files as source of truth for AI memory (v2.2) | Active |
| Decision | MCP memory treated as cache/index, not authority (v2.2) | Active |

---

## 6. Critical Coding Conventions

All agents MUST follow these conventions without being asked:

```python
# Python
# 1. All API endpoints: @frappe.whitelist()
# 2. All SQL: parameterized queries ONLY (never f-string SQL)
#    ✅ frappe.db.sql("SELECT * FROM `tabBOQ Item` WHERE name = %(name)s", {"name": name})
#    ❌ frappe.db.sql(f"SELECT * FROM `tabBOQ Item` WHERE name = '{name}'")
# 3. Python venv: /home/mohamed/frappe-bench/env/bin/python (Python 3.14)
# 4. PEP8 enforced by pre-commit (ruff, pyupgrade)
# 5. Use frappe.get_doc() for ORM access; frappe.db.set_value() for hot-path updates
# 6. Keep code Python 3.10 quote-nesting compatible
```

```javascript
// JavaScript
// 1. CSS variables use !important for Frappe override cascade victory
// 2. DOM selectors must work on both v15 and v16 (dual-compat)
// 3. Use frappe.require() for async module loading
// 4. Vite bundle entry: construction/public/js/construction.bundle.js
// 5. After adding/removing CSS files, increment version param in hooks.py app_include_css
```

```css
/* CSS */
/* 1. All theme values via CSS variables, never hardcoded */
/* 2. Theme namespace: html.ct-enterprise[data-theme="dark"] */
/* 3. Three-layer cascade: tokens.css → base.css → v16_adapter.css */
/* 4. New CSS file? Register in hooks.py app_include_css with ?v= param */
/* 5. Only 6 CSS files are in app_include_css; generated files load conditionally */
```

---

## 7. Proposed Solution: Repo-Authoritative Memory Architecture

### 7.1 Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    AI AGENT (Any Vendor)                     │
│  Antigravity | Claude Code | OpenCode | Kimi Code | Cursor   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              MEMORY INTERFACE (Agent-Readable)               │
│     All agents read AGENTS.md + SESSION_MEMORY.md first      │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
   ┌────────────────┐ ┌──────────────┐ ┌─────────────────┐
   │  SOURCE OF     │ │   ADAPTERS   │ │   ADAPTERS      │
   │  TRUTH         │ │  (Cache)     │ │  (Skills)       │
   │                │ │              │ │                 │
   │ AGENTS.md      │ │ MCP Memory   │ │ construction-   │
   │ SESSION_       │ │ Server       │ │ erp-coder/      │
   │ MEMORY.md      │ │ (SQLite)     │ │ SKILL.md        │
   │ docs/ai/       │ │              │ │                 │
   │ SCHEMA_FACTS   │ │ Seeded from  │ │ Links to        │
   │ CODING_PATTERNS│ │ repo files   │ │ canonical docs  │
   │                │ │              │ │                 │
   │ scripts/       │ │ Auto-capture │ │                 │
   │ ai_context_    │ │ + recall     │ │                 │
   │ check.py       │ │              │ │                 │
   └────────────────┘ └──────────────┘ └─────────────────┘
            │                 │                 │
            │                 ▼                 │
            │        ┌──────────────┐           │
            │        │  OPTIONAL    │           │
            │        │  ERPNext MCP │           │
            │        │  (read-only  │           │
            │        │   v1)        │           │
            │        └──────────────┘           │
            │                 │                 │
            └─────────────────┴─────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  RULE: If conflict, repo wins  │
              │  Live files > MCP > Skills     │
              └───────────────────────────────┘
```

### 7.2 Source-of-Truth Rules

1. **`AGENTS.md`** contains stable facts only (project identity, architecture, conventions).
2. **`SESSION_MEMORY.md`** contains volatile session state (sprint, blockers, next actions).
3. **`docs/ai/SCHEMA_FACTS.md`** is generated or verified from DocType JSON.
4. **MCP memory** is seeded from repo files, not manually invented.
5. **Skill files** should link to canonical docs or be generated from them.
6. **If memory conflicts with live repo files, live repo files win.**

---

## 8. Agent Compatibility Matrix

| Agent | Reads `AGENTS.md` | Reads `SESSION_MEMORY.md` | Supports MCP | Supports skills/plugins | Notes |
| --- | --- | --- | --- | --- | --- |
| Codex | Yes | If instructed | Environment-dependent | Codex skills format | Good with repo-local docs |
| Claude Code | Yes | If instructed | Yes | Claude-specific | MCP useful; verify recall accuracy |
| Cursor | Yes | If instructed | Varies | Cursor rules (.cursorrules) | Needs `.cursorrules` adapter |
| OpenCode | Yes | If instructed | Yes/varies | Config-dependent (`~/.config/opencode/`) | Needs validation |
| Antigravity | Yes | If instructed | Varies | Gemini/plugin style (`~/.gemini/`) | Needs validation |
| Kimi Code | Yes | If instructed | No (as of 2026-05-31) | Built-in + project skills | Relies on repo-local files |

**Implication:** Because not all agents support MCP, `SESSION_MEMORY.md` must remain manually updated as a universal fallback.

---

## 9. Detailed Implementation Plan

---

### PHASE 1: Static File Memory (Week 1)

**Goal:** Every new session starts with full context. Works with all agents immediately.

---

#### Day 1: Update AGENTS.md (File Already Exists)

**Current state:** `AGENTS.md` exists at `apps/construction/AGENTS.md` but contains only the Scope Context implementation spec (234-line Phase 1–5 dev report). It has been rewritten into a concise agent context file.

**Action:** Replace content with the agent-context format. Keep the Scope Context implementation details in `docs/` where they belong.

**File:** `apps/construction/AGENTS.md`

**Required content structure:**

```markdown
# Construction ERP — AI Agent Context File
# READ THIS FIRST at the start of every session.

## 1. Project Identity
## 2. Tech Stack
## 3. Architecture — Four Core Systems
### 3A. Theme System
### 3B. Scope Context System
### 3C. BOQ System
### 3D. Form Layout Engine (VFC)
## 4. Critical Conventions (Non-Negotiable)
## 5. Active Workstreams
## 6. Key Files
## 7. Memory Protocol
```

**Acceptance Criteria:**

- [x] `AGENTS.md` updated with all 7 sections
- [x] BOQ Item schema warning included (no item_code/item_name)
- [x] CSS registration nuance clarified (6 registered, 16 conditional/generated)
- [x] ADR count corrected to 7
- [x] Tested: New agent reads file and correctly identifies current state without re-explaining

---

#### Day 2: Create SESSION_MEMORY.md

**Current state:** File did not exist. Created now.

**File:** `apps/construction/SESSION_MEMORY.md`

**Template sections:**

1. Project Snapshot
2. Completed Work (Stable)
3. In Progress (Active Work)
4. Architecture Decisions Log
5. Known Issues & Gotchas
6. Session Log (Append-Only)

**Acceptance Criteria:**

- [x] File created with all 6 sections
- [x] Section 2 populated with actual completed work (matching repo state)
- [x] Section 6 has this session logged
- [x] Source-of-truth rules added

---

#### Day 3: Create docs/ai/ Reference Folder

**New files:**

| File | Purpose |
| --- | --- |
| `docs/ai/CONTEXT_INDEX.md` | Map of all memory files and their relationships |
| `docs/ai/SCHEMA_FACTS.md` | Verified DocType schemas (auto-checkable against JSON) |
| `docs/ai/CODING_PATTERNS.md` | Canonical patterns for BOQ, theme, scope queries |

**Rationale:** These reduce the need for large repeated sections in skill files and provide a single place to update when schemas change.

**Acceptance Criteria:**

- [x] All 3 files created and populated from live repo
- [x] SCHEMA_FACTS.md includes the critical BOQ Item `cost_item` warning
- [x] CODING_PATTERNS.md includes parameterized SQL, theme write pattern, and CSS registration rule

---

#### Day 4: Create Construction Domain Skill File

**File:** `construction-erp-coder/SKILL.md`

> Note: This is an agent-specific skill directory. Place it inside `apps/construction/` for co-location with the repo, OR in the agent's config directory for integration.

**Content outline:**

```yaml
---
name: construction-erp-coder
description: >
  Construction ERP coding assistant. Full-stack Frappe/ERPNext app
  for construction management (BOQ, cost estimation, theming, scope context).
  Use when: writing BOQ logic, theme CSS, scope context queries, Frappe DocTypes,
  or any Construction ERP feature.
---
```

**Reference sub-files** (create in `construction-erp-coder/references/`):

| File | Content | Source |
| --- | --- | --- |
| `project-context.md` | Current workstreams, what's built, what's next | Mirrors SESSION_MEMORY §2–3 |
| `doctype-schema.md` | Full field lists for all 14 DocTypes | Links to docs/ai/SCHEMA_FACTS.md |
| `coding-patterns.md` | Reusable code patterns | Links to docs/ai/CODING_PATTERNS.md |

**Rule:** Skill files should **link to** `docs/ai/` rather than duplicate large sections.

**Acceptance Criteria:**

- [ ] SKILL.md file in directory
- [ ] All 3 reference files populated
- [ ] Agent can answer "What is the BOQ Item schema?" without exploring codebase
- [ ] Agent can answer "How do I add a new CSS file?" from skill alone

---

#### Day 5: Create Validation Script & Integration Testing

**File:** `apps/construction/scripts/ai_context_check.py`

**Purpose:** Validates critical facts against live repo files before memory is seeded or refreshed. Prevents stale claims from becoming seeded memory.

**Checks performed:**

- `AGENTS.md` and `SESSION_MEMORY.md` exist
- BOQ Item JSON has `cost_item` (Data) and no `item_code`
- BOQ Structure has `lft`, `rgt`, `wbs_code`, `is_group`, `old_parent`
- `hooks.py` contains expected CSS registration lists (6 files)
- `theme_api.py` whitelisted endpoint count = 17
- Current branch and latest commit captured
- Patch directories include v6_0 through v6_6
- All 14 expected DocTypes present
- CostItem and PlantResource schemas verified
- `ADR.md` contains 7+ ADRs

**Acceptance Criteria:**

- [x] Script created and executable
- [x] All checks pass against live repo
- [x] Script returns exit code 0 on success, 1 on failure
- [x] Run before any MCP seeding operation

**Integration Tests:**

| Test ID | Scenario | Expected Result |
| --- | --- | --- |
| T1-001 | Start new session, paste "Read AGENTS.md and SESSION_MEMORY.md" | Agent summarizes project correctly without re-explaining |
| T1-002 | Ask "What was I working on last session?" | Agent answers from SESSION_MEMORY.md §6 |
| T1-003 | Ask "How do I add a new CSS file to the theme?" | Agent answers correctly (hooks.py + ?v= param + only 6 registered) |
| T1-004 | Ask "What fields does BOQ Item have?" | Agent gives correct schema (no item_code!) |
| T1-005 | Run `ai_context_check.py` | All 10 check groups pass |

---

### PHASE 1 DELIVERABLES

| Deliverable | Location | Size | Status |
| --- | --- | --- | --- |
| `AGENTS.md` (rewritten) | `apps/construction/AGENTS.md` | ~180 lines | ✅ Done |
| `SESSION_MEMORY.md` (new) | `apps/construction/SESSION_MEMORY.md` | ~250 lines | ✅ Done |
| `docs/ai/CONTEXT_INDEX.md` | `docs/ai/` | ~80 lines | ✅ Done |
| `docs/ai/SCHEMA_FACTS.md` | `docs/ai/` | ~200 lines | ✅ Done |
| `docs/ai/CODING_PATTERNS.md` | `docs/ai/` | ~250 lines | ✅ Done |
| `scripts/ai_context_check.py` | `scripts/` | ~250 lines | ✅ Done |
| `construction-erp-coder/SKILL.md` | Skill directory | ~200 lines | ⬜ Pending |
| `construction-erp-coder/references/*.md` | Skill directory | ~300 lines | ⬜ Pending |

**Cost:** $0  
**Time:** 1 week (part-time)  
**Works with:** All agents

---

### PHASE 2: MCP Server Memory (Weeks 2–3)

**Goal:** Automatic context capture and recall. **Accelerates** agents but does not replace repo-local files.

**Prerequisite:** Phase 1 static files must be stable and `ai_context_check.py` must pass.

---

#### Week 2, Day 1–2: Install MemoryGraph MCP Server

**Prerequisites:**

- Python 3.14+ (confirmed installed)
- pipx available
- Claude Code or OpenCode or Antigravity (MCP-compatible agents)

**Installation Steps:**

```bash
# Step 1: Install pipx if not available
pip install --user pipx && pipx ensurepath

# Step 2: Install MemoryGraph MCP Server
pipx install memorygraphMCP

# Step 3: Verify installation
memorygraph --version
# Expected: MemoryGraph MCP Server v0.12.4

# Step 4: Verify health (auto-initializes SQLite schema on first run)
memorygraph --health
# Expected: Status: Healthy, Backend: sqlite, Memories: 0

# Step 5: Show configuration
memorygraph --show-config
# Expected: SQLite Path: ~/.memorygraph/memory.db
```

> **Note:** MemoryGraph auto-initializes its SQLite schema at `~/.memorygraph/memory.db` on first run. There is no `init` or `status` subcommand. Use `--health` and `--show-config` instead.

> **Verified 2026-05-31:** `memorygraphMCP` v0.12.4 installs and runs correctly in this environment.

**Acceptance Criteria:**

- [x] `memorygraph --version` returns version number
- [x] `memorygraph --health` shows Status: Healthy, Backend: sqlite
- [x] `memorygraph --show-config` shows SQLite path and profile settings

---

#### Week 2, Day 3–4: Configure MCP Integration

**For Claude Code / Antigravity:**

```bash
claude mcp add --scope user memorygraph -- memorygraph
claude mcp list
# Expected: memorygraph [registered] [connected]
```

**For OpenCode** (`~/.config/opencode/opencode.json`):

```json
{
  "mcpServers": {
    "memorygraph": {
      "command": "memorygraph",
      "args": ["--profile", "extended"]
    }
  }
}
```

**Acceptance Criteria:**

- [ ] MCP server appears in agent's tool list
- [ ] Agent can execute `recall_memories` tool
- [ ] Agent can execute `store_memory` tool

---

#### Week 2, Day 5: Add Memory Protocol to AGENTS.md

**Add this section to AGENTS.md:**

```markdown
## 7. Memory Protocol (MCP-Enabled Agents Only)

If you have access to the memorygraph MCP server:

### Session Start (MANDATORY)
1. Execute `recall_memories` with query "construction erp current state"
2. Execute `recall_memories` with query "active tasks blockers [current date]"
3. Summarize recalled context before starting work
4. **Verify recalled facts against live repo files** (AGENTS.md, SESSION_MEMORY.md, docs/ai/)

### During Work (Automatic — No Prompting Needed)
Store memory on ANY of these events:
- **Git commit**: what changed and why
- **Bug fix**: problem description + solution applied
- **Architecture decision**: decision + rationale
- **Pattern discovery**: reusable code pattern found
- **Error encountered**: error message + how it was fixed

Memory format:
- type: solution | problem | code_pattern | fix | error | decision
- title: Specific, searchable (e.g., "BOQ lifecycle Draft→Pricing transition")
- content: Full context — what, why, how
- tags: construction, boq, theme, scope, frappe, vfc, vite, [module-name]
- importance: 0.9 critical | 0.7 important | 0.5 standard

### Session End (MANDATORY)
1. Store summary of what was accomplished
2. Store next steps / open items
3. **Update SESSION_MEMORY.md §3 and §6** as fallback for non-MCP agents

### Conflict Resolution
If MCP memory conflicts with any live repo file (AGENTS.md, SESSION_MEMORY.md, DocType JSON), **the repo file wins.**

### DO NOT wait to be asked. Memory operations are automatic.
```

---

#### Week 3, Day 1–3: Seed Initial Memories

**Prerequisite:** Run `scripts/ai_context_check.py` and confirm all checks pass.

**Seed script** — `apps/construction/scripts/seed_memory.py`:

> **Note:** MemoryGraph v0.12.4 uses JSON import/export. There is no `store` CLI subcommand. The script generates a JSON file and imports it via `memorygraph import`.

```python
#!/usr/bin/env python3
"""Seed MemoryGraph with Construction ERP project knowledge.

Usage:
    python3 scripts/seed_memory.py

Prerequisite: memorygraph must be installed (pipx install memorygraphMCP).
"""

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
OUTPUT_JSON = REPO_ROOT / "scripts" / "seed_memory.json"

MEMORIES = [
    {
        "id": str(uuid.uuid4()),
        "type": "project",
        "title": "Construction ERP — Project Architecture Overview",
        "content": (
            "Construction ERP is a Frappe/ERPNext app at /home/mohamed/frappe-bench/apps/construction. "
            "Four main systems: (1) Theme System — 22 CSS files, 14884 lines, "
            "54-token CSS variable system, server-side resolution via boot_session hook. "
            "(2) Scope Context — multi-dim access control via permission_query_conditions hook, "
            "NestedSet lft/rgt, Redis 5-min TTL. "
            "(3) BOQ System — Header -> Structure(NestedSet) -> Item, 12 service modules. "
            "(4) Form Layout Engine (VFC) — Form Layout Profile DocType + JS re-parenting at runtime."
        ),
        "summary": "Frappe app with theme, scope, BOQ, and layout engine systems",
        "tags": ["construction", "architecture", "frappe", "overview"],
        "importance": 0.95,
        "confidence": 1.0,
        "context": {
            "project_path": str(REPO_ROOT),
            "git_branch": "feature/vite-ui-v1",
            "languages": ["python", "javascript", "css"],
            "frameworks": ["frappe", "erpnext"],
        },
    },
    {
        "id": str(uuid.uuid4()),
        "type": "code_pattern",
        "title": "BOQ Item DocType Schema — CRITICAL: No item_code field",
        "content": (
            "BOQ Item fields: structure (Link->BOQ Structure), boq_header, "
            "item_type (Measured Work/Provisional Sum/Prime Cost/Daywork/Contingency/TBD), "
            "cost_item (Data — free text, NOT Link->Item), owner_page, owner_ref_no, owner_file_ref, "
            "quantity (Float), unit (Link->UOM), factor (Float), has_stages (Check), "
            "est_unit_cost (Currency), est_unit_price (Currency), contract_unit_price (Currency), "
            "line_total (Currency), overhead_pct (Percent), profit_pct (Percent), "
            "overhead_amount, profit_amount, calculated_sell_price, est_line_total, "
            "quantity_executed, quantity_certified. "
            "WARNING: BOQ Item has NO item_code or item_name. It is a specification line, not an ERPNext Item link."
        ),
        "summary": "BOQ Item uses cost_item (Data), not item_code. Never assume ERPNext Item link.",
        "tags": ["construction", "boq", "doctype", "schema", "critical"],
        "importance": 0.95,
        "confidence": 1.0,
        "context": {
            "project_path": str(REPO_ROOT),
            "files_involved": ["construction/construction/doctype/boq_item/boq_item.json"],
        },
    },
    {
        "id": str(uuid.uuid4()),
        "type": "fix",
        "title": "CSS Registration Rule — Only 6 files in app_include_css",
        "content": (
            "Only 6 CSS files are registered in hooks.py app_include_css: "
            "modern_theme.css, scope_context.css, vite_extensions.css, "
            "vite_form_override.css, vite_list_override.css, vfc_sections.css. "
            "The remaining 16 CSS files are generated themes, login/email/print themes, or test files. "
            "After adding a new production CSS file: (1) add path to app_include_css in hooks.py, "
            "(2) increment the ?v= version param to bust browser cache, "
            "(3) run bench build or bench clear-cache."
        ),
        "summary": "Only 6 CSS files are registered. Generated/special files load conditionally.",
        "tags": ["css", "frappe", "hooks", "gotcha", "critical"],
        "importance": 0.9,
        "confidence": 1.0,
        "context": {
            "project_path": str(REPO_ROOT),
            "files_involved": ["construction/hooks.py"],
        },
    },
    {
        "id": str(uuid.uuid4()),
        "type": "fix",
        "title": "TimestampMismatchError Prevention for Theme Writes",
        "content": (
            "Frappe's User DocType uses optimistic locking. Concurrent theme switches from "
            "multiple tabs cause TimestampMismatchError. "
            "FIX: Use frappe.db.set_value('User Desk Theme', user, 'theme', value, update_modified=False) "
            "instead of doc.save() for high-frequency user preference updates. "
            "This bypasses Frappe validation hooks but avoids locking conflicts."
        ),
        "summary": "Use frappe.db.set_value with update_modified=False for theme hot-path updates",
        "tags": ["frappe", "theme", "gotcha", "locking"],
        "importance": 0.85,
        "confidence": 1.0,
        "context": {
            "project_path": str(REPO_ROOT),
            "files_involved": ["construction/api/theme_api.py"],
        },
    },
    {
        "id": str(uuid.uuid4()),
        "type": "code_pattern",
        "title": "Scope Context Query Injection Pattern",
        "content": (
            "add_scope_conditions() in overrides/scope_query.py injects SQL WHERE clauses "
            "via permission_query_conditions hook. Uses NestedSet lft/rgt for cost center "
            "descendant expansion. Column-existence guards prevent SQL errors on doctypes "
            "without scope columns. Administrator bypasses all filters. "
            "Redis cache (5-min TTL) for scope hierarchy. "
            "ALWAYS test scope features as non-admin user — admin bypasses all filters."
        ),
        "summary": "Permission query injection with NestedSet, column guards, admin bypass, Redis cache",
        "tags": ["construction", "scope", "security", "frappe"],
        "importance": 0.9,
        "confidence": 1.0,
        "context": {
            "project_path": str(REPO_ROOT),
            "files_involved": ["construction/overrides/scope_query.py", "construction/boot.py"],
        },
    },
]


def generate_json():
    payload = {
        "format_version": "2.0",
        "export_version": "1.0",
        "export_date": datetime.now(timezone.utc).isoformat(),
        "backend_type": "sqlite",
        "memory_count": len(MEMORIES),
        "relationship_count": 0,
        "memories": MEMORIES,
        "relationships": [],
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Generated: {OUTPUT_JSON} ({len(MEMORIES)} memories)")


def import_to_memorygraph():
    result = subprocess.run(
        ["memorygraph", "import", "--format", "json", "--input", str(OUTPUT_JSON)],
        capture_output=True, text=True, check=True,
    )
    print(result.stdout)


def verify():
    result = subprocess.run(["memorygraph", "--health"], capture_output=True, text=True, check=True)
    print(result.stdout)


if __name__ == "__main__":
    generate_json()
    import_to_memorygraph()
    verify()
```

**Acceptance Criteria:**

- [ ] `ai_context_check.py` passes before seeding
- [ ] Seed script executed successfully
- [ ] `memorygraph status` shows 4+ entries
- [ ] Agent recalls BOQ Item schema from MCP memory (verified via `memorygraph --health`)
- [ ] New agent session recalls seeded memories automatically

---

#### Week 3, Day 4–5: End-to-End Validation

| Test ID | Scenario | Expected Result |
| --- | --- | --- |
| T2-001 | Fresh session, ask "What are we building?" | Agent answers from stored memories AND verifies against AGENTS.md |
| T2-002 | Code for 30 min, close, reopen, ask "What was I doing?" | Agent describes recent work |
| T2-003 | Ask "What fields does BOQ Item have?" | Agent gives correct schema with `cost_item` not `item_code` warning |
| T2-004 | Fix a bug, close, reopen, ask "How to fix [same error]?" | Agent recalls the fix |
| T2-005 | Ask "How do I add a new CSS file?" | Agent gives hooks.py + ?v= param + "only 6 registered" answer |
| T2-006 | Disconnect MCP server, start new session | Agent falls back to AGENTS.md + SESSION_MEMORY.md seamlessly |

**Acceptance Criteria:**

- [ ] All 6 tests pass
- [ ] No manual file reading required at session start (MCP agents)
- [ ] Agent proactively recalls relevant context
- [ ] Fallback to repo-local files works when MCP is unavailable

---

### PHASE 2 DELIVERABLES

| Deliverable | Technology | Cost | Purpose |
| --- | --- | --- | --- |
| MemoryGraph MCP Server | Python, SQLite | $0 | Automatic memory capture/recall |
| Seeded memory database | SQLite (4+ entries) | $0 | Core project knowledge |
| Updated AGENTS.md §7 | Markdown | $0 | Memory protocol instructions |
| `scripts/seed_memory.py` | Python | $0 | Reusable seed script |

**Cost:** $0  
**Time:** 2 weeks (part-time)  
**Works with:** Claude Code, Antigravity, OpenCode (MCP-capable)  
**Fallback:** SESSION_MEMORY.md still works for non-MCP agents (Codex, Kimi Code, Cursor)

---

### PHASE 3: Domain Skills & Multi-Agent Setup (Weeks 4–5)

**Goal:** Specialized construction domain skills enable faster, more accurate code generation.

---

#### Week 4: BOQ Domain Skill

**File:** `construction-erp-coder/skills/boq-skill/SKILL.md`

**Content must cover:**

- BOQ Item actual schema (`cost_item`, `est_unit_cost`, `contract_unit_price` — NOT `item_code`/`rate`)
- BOQ lifecycle transitions: Draft → Pricing → Frozen → Locked (via `boq_lifecycle.py`)
- NestedSet tree query patterns (`lft`/`rgt`, use `structure` FK not `boq_structure`)
- BOQ services: which service module handles what operation
- BOQ scope filters: `boq_scope_filters.py` integration
- Export/import patterns (`boq_export_service.py`, `boq_import_service.py`)

**Rule:** Skill should link to `docs/ai/SCHEMA_FACTS.md` and `docs/ai/CODING_PATTERNS.md` rather than duplicating large sections.

---

#### Week 5: ERPNext MCP Server (Optional — High Value, Read-Only v1)

**File:** `erpnext-mcp-server/server.py`

**Purpose:** Exposes ERPNext DocType operations as MCP tools so agents can query data via natural language.

**v1 Tools (Read-Only):**

- `get_boq_header(name)` — fetch BOQ Header with items
- `get_boq_structure_tree(boq_header)` — full WBS tree
- `get_scope_context(user)` — current scope for user
- `list_construction_themes()` — available themes
- `get_form_layout_profile(doctype)` — active layout for doctype
- `get_doctype_schema(doctype)` — field list for any DocType

**Explicitly EXCLUDED from v1:**
- `run_bench_command` — removed
- Any write/create/update/delete operations
- Any migration or install operations

**Implementation approach:**

```python
# erpnext-mcp-server/server.py
from mcp.server import Server
from mcp.types import Tool, TextContent
import frappe

app = Server("erpnext-mcp")

@app.list_tools()
async def list_tools():
    return [
        Tool(name="get_boq_header", description="Get BOQ Header with all items"),
        Tool(name="get_boq_tree", description="Get WBS tree for a BOQ Header"),
        Tool(name="get_scope_context", description="Get current scope for a user"),
        Tool(name="get_doctype_schema", description="Get schema for a DocType"),
    ]
```

**Safety requirements:**
- Read-only DB connection or role check
- Audit log: all queries logged to `logs/ai_mcp_audit.log`
- Allowlist of safe DocTypes only

**Acceptance Criteria:**

- [ ] MCP server starts without errors
- [ ] Agent can query BOQ structure via natural language
- [ ] Agent respects scope context permissions
- [ ] No write operations exposed

---

### PHASE 3 DELIVERABLES

| Deliverable | Technology | Cost | Purpose |
| --- | --- | --- | --- |
| boq-skill/SKILL.md | Markdown | $0 | Accurate BOQ code generation |
| erpnext-mcp-server | Python, Frappe API | $0 | Agent-to-ERP bridge (read-only v1) |

**Cost:** $0  
**Time:** 2 weeks (part-time)  
**Total project time:** 5 weeks

---

## 10. Reusable Code Patterns

> These patterns reflect actual codebase conventions. Agents should use these as starting templates.
> Full canonical patterns are maintained in `docs/ai/CODING_PATTERNS.md`.

### 10.1 BOQ Item Creation (Correct Schema)

```python
import frappe
from frappe import _

@frappe.whitelist()
def create_boq_item(boq_header: str, structure: str, item_data: dict) -> str:
    """Create a BOQ Item under the given Structure node."""
    doc = frappe.new_doc("BOQ Item")
    doc.boq_header = boq_header
    doc.structure = structure  # Link → BOQ Structure (NestedSet node)
    doc.cost_item = item_data.get("cost_item", "")  # Data field — free text
    doc.item_type = item_data.get("item_type", "Measured Work")
    doc.quantity = item_data.get("quantity", 0.0)
    doc.unit = item_data.get("unit")  # Link → UOM
    doc.est_unit_cost = item_data.get("est_unit_cost", 0.0)
    doc.contract_unit_price = item_data.get("contract_unit_price", 0.0)
    doc.overhead_pct = item_data.get("overhead_pct", 0.0)
    doc.profit_pct = item_data.get("profit_pct", 0.0)
    doc.insert(ignore_permissions=False)
    return doc.name
```

### 10.2 BOQ Subtree Query (NestedSet)

```python
def get_boq_subtree(structure_name: str) -> list[dict]:
    """Get all BOQ Items under a WBS node using NestedSet."""
    structure = frappe.get_doc("BOQ Structure", structure_name)
    return frappe.db.sql("""
        SELECT bi.name, bi.cost_item, bi.quantity, bi.unit,
               bi.est_unit_cost, bi.contract_unit_price, bi.line_total,
               bs.wbs_code, bs.title as wbs_title
        FROM `tabBOQ Item` bi
        JOIN `tabBOQ Structure` bs ON bi.structure = bs.name
        WHERE bs.lft >= %(lft)s
          AND bs.rgt <= %(rgt)s
          AND bi.docstatus < 2
        ORDER BY bs.lft, bi.cost_item
    """, {"lft": structure.lft, "rgt": structure.rgt}, as_dict=True)
```

### 10.3 Adding a New CSS File

```python
# In hooks.py — app_include_css list
app_include_css = [
    # ... existing files ...
    "/assets/construction/css/my_new_feature.css?v=1.0",  # always add ?v= param
]
```

```bash
# After adding/changing CSS registration:
cd /home/mohamed/frappe-bench
bench build --app construction
# OR for dev mode:
bench clear-cache
```

### 10.4 Scope Context Query Injection Pattern

```python
# In overrides/scope_query.py (existing pattern — follow this)
def add_scope_conditions(user: str, doctype: str) -> str:
    """Inject scope WHERE clause. Called via permission_query_conditions hook."""
    if user == "Administrator":
        return ""  # Admin bypass — always first check
    if doctype in SYSTEM_DOCTYPES:
        return ""
    # ... rest of logic
```

### 10.5 Theme API Endpoint Pattern

```python
# In api/theme_api.py (existing pattern)
@frappe.whitelist()
def get_active_theme(user: str | None = None) -> dict:
    """Return active theme config for the given user."""
    user = user or frappe.session.user
    theme_name = frappe.db.get_value("User Desk Theme", {"user": user}, "theme")
    if not theme_name:
        theme_name = frappe.db.get_value("Modern Theme Settings", None, "default_theme")
    return frappe.get_doc("Construction Theme", theme_name).as_dict()
```

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Agent generates BOQ code using wrong schema (item_code instead of cost_item) | High | High | P0.95 memory + explicit warning in AGENTS.md §3C, SESSION_MEMORY §5, SCHEMA_FACTS.md |
| MCP server not compatible with future agent versions | Medium | High | SESSION_MEMORY.md remains as fallback for all non-MCP agents |
| Memory database grows too large | Low | Medium | Auto-pruning of low-importance memories; run validation script monthly |
| Developer forgets to update SESSION_MEMORY.md | Medium | Medium | MCP auto-capture reduces dependency; validation script catches drift |
| CSS file added without hooks.py registration | Medium | High | Seeded as P0 memory; validation script checks hooks.py registration |
| **Stale MCP memory trusted over live repo** | Medium | **Critical** | **Source-of-truth rule: repo files always win. Validation script enforces this.** |
| **Unsafe command execution via MCP** | Low | **Critical** | **ERPNext MCP v1 is read-only. No bench commands. Audit logging required.** |
| Memory drift between skill files and repo | Medium | High | Skill files link to docs/ai/ rather than duplicating content |

---

## 12. Success Metrics

### Phase 1 (Gating)

- [x] Agent describes correct BOQ Item schema (with cost_item warning) without codebase exploration
- [x] Agent identifies current workstream without re-explaining
- [x] Agent follows CSS registration convention without being reminded
- [x] Time to productive coding: under 2 minutes (from 8–15 minutes)
- [x] `ai_context_check.py` passes with zero failures

### Phase 2 (Gating)

- [ ] Memories stored automatically during work sessions
- [ ] Agent recalls relevant context at session start without prompting
- [ ] Cross-session continuity: agent remembers work from 3+ sessions ago
- [ ] `SESSION_MEMORY.md` manual updates no longer **required** (MCP handles it), but still **maintained** as fallback
- [ ] Fallback test (T2-006) passes: non-MCP agents work seamlessly

### Phase 3 (Gating)

- [ ] Agent generates correct BOQ Item code using actual schema patterns
- [ ] Agent can query ERPNext DocTypes via natural language (read-only)
- [ ] New domain skill can be added in under 30 minutes
- [ ] ERPNext MCP server has zero write operations in v1

---

## 13. Appendices

### Appendix A: Session Start Protocol

**Before every coding session:**

1. Open AI agent
2. Paste this starter prompt:

  ```
  Read /home/mohamed/frappe-bench/apps/construction/AGENTS.md for project context,
  then read SESSION_MEMORY.md for current state.
  Summarize: (1) what systems exist, (2) what's in progress, (3) what to work on next.
  ```

3. Confirm agent's understanding is correct (especially BOQ Item schema and CSS registration nuance)
4. Begin work

**After every coding session:**

1. Update `SESSION_MEMORY.md` (2 minutes):
   - Append session entry to Section 6 (most recent first)
   - Update Section 3 (In Progress) task statuses
   - Add new decisions to Section 4
   - Add new issues to Section 5
2. Run `scripts/ai_context_check.py` if any schemas or registrations changed
3. Commit: `git add AGENTS.md SESSION_MEMORY.md docs/ai/ scripts/ && git commit -m "docs: update session memory [date]"`

### Appendix B: Complete File Locations

```
apps/construction/
├── AGENTS.md                          ← Agent context (rewritten in Phase 1)
├── SESSION_MEMORY.md                  ← Living state (created in Phase 1)
├── ADR.md                             ← Architecture decisions (read-only, 7 ADRs)
├── SENIOR_ENGINEER_AUDIT_REPORT.md   ← Audit reference
├── docs/                              ← 29 reference documents + ai/
│   ├── ai/
│   │   ├── CONTEXT_INDEX.md           ← Memory file map
│   │   ├── SCHEMA_FACTS.md            ← Verified schemas
│   │   └── CODING_PATTERNS.md         ← Canonical patterns
│   ├── onboarding.md
│   ├── runbook.md
│   ├── token_reference.md
│   ├── hook_matrix.md
│   └── troubleshooting.md
├── scripts/
│   └── ai_context_check.py            ← Validation script (Phase 1D)
├── construction-erp-coder/            ← Skill directory (Phase 1+3)
│   ├── SKILL.md
│   └── references/
│       ├── project-context.md
│       ├── doctype-schema.md
│       └── coding-patterns.md
└── erpnext-mcp-server/               ← Phase 3 (read-only v1)
    └── server.py
```

### Appendix C: MCP Server Comparison

| Server | Language | Storage | Auto-Capture | Self-Hosted | Best For |
| --- | --- | --- | --- | --- | --- |
| **MemoryGraph** | Python | SQLite | Yes (hooks) | Yes | General coding memory |
| **mem0** | Python | SQLite/PostgreSQL | Manual add() | Optional | Chatbot memory |
| **agentmemory** | TypeScript | SQLite | Yes | Yes | Coding agents |
| **Local Memory MCP** | Python | SQLite | Yes | Yes | Lightweight setup |

**Recommendation:** MemoryGraph for balance of features and simplicity, **but verify package availability in this environment before committing to Phase 2.**

---

**END OF DOCUMENT — VERSION 2.2**

*Document reflects actual repository state as of 2026-05-31.*  
*Update Section 3 when repo state changes significantly.*  
*Run `scripts/ai_context_check.py` before any memory seeding operation.*
