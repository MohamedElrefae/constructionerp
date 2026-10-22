# Construction ERP — AI Agent Context File
> READ THIS FIRST at the start of every session.

## 0. Required Engineering Standard

- **Read [Professional Engineering Standard](docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md) at the start of every session.** It contains the owner's instructions for professional Frappe development, proportional verification, financial integrity, permissions, migrations, and maintenance.
- Follow its section 3 startup checklist: read the context index, relevant schema facts and workflow/plan references; capture actual checkout/branch/HEAD/status; run `python3 scripts/schema_drift_checker.py` and `python3 scripts/ai_context_check.py` before relying on context for planning or edits. Record actual files read and results. These checks establish local facts, not remote freshness or deployed-site correctness.
- New orchestrator tasks enforce `engineering-startup/v1` automatically. Read the supplied immutable snapshots and candidate-bound coordinator evidence as described in standard section 3; identify coordinator-executed checks accurately. Existing initialized tasks remain legacy until separately reconciled. See [startup implementation and operating instructions](docs/ai/work-items/engineering-startup-gates/IMPLEMENTATION.md).
- For commercial correctness or customer release work, also read the relevant gaps in [Customer Release Gap Report](docs/ai/CUSTOMER_RELEASE_GAPS_2026-10-04.md). Recheck findings against current source; the report is a dated assessment, not a release approval.
- The standard refines the broad templates below and in `CODING_PATTERNS.md`. Follow current owner instructions and applicable scoped governance; preserve unrelated work and report actual evidence.
- Keep private findings local unless an external destination and scope are authorized. If external memory is unavailable or rejected, use `SESSION_MEMORY.md`; do not bypass that decision through another tool or automatic hook.

## 1. Project Identity
- **Name:** Construction ERP (Frappe/ERPNext custom app)
- **App name:** `construction` (used in imports: `from construction.xxx import yyy`)
- **Repo root:** `/home/mohamed/frappe-bench/apps/construction`
- **Author:** Mohamed Elrefae (solo civil engineer developer)
- **License:** MIT
- **Current branch:** `develop`
- **Total commits:** 369+ (run `git rev-list --count HEAD`; not maintained here)
- **Latest commit:** see `git log -1` (as of 2026-09-25 the tip is the W6-6 CRM closure `3344546` plus handoff/reconciliation docs commits)
- **Branch state:** `develop` tracks `origin/develop`; verify with `git rev-list --left-right --count origin/develop...HEAD` before assuming anything is unpushed

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

### 3D. Form Layout Engine (VFC) ✅ Phase 1+2+3
- **Form Layout Profile** DocType: stores `sections_json` for each `reference_doctype`
- `vfc_layout_engine.js` (1,399 lines): runtime field re-parenting into custom sections
- `vite_layout_controls.js` (1,771 lines): drag/resize panel + Sections Editor tab + density controls + revert
- `vfc_sections.css` (177 lines): section card styles
- `vfc_config.js` (23 lines): debug flag gating
- `construction/construction/api/layout_api.py` (330 lines, 6 whitelisted endpoints): backend layout CRUD + `delete_my_personal_layout`
- `construction/api/modern_form_api.py` (454 lines): React form API — **deprecated**, System Manager only (ADR-008)
- 37 backend tests in `tests/test_vfc_backend.py`; browser test suite in `vfc_layout_engine_tests.js`
- Status: Phase 3 stabilization complete (WP0–WP5). Includes:
  - Cache TTL (60s client-side), revert-to-default button
  - Project layout seed, `hidden_due_to_dependency` guard
  - Non-admin personal layout deletion via `delete_my_personal_layout`
  - Full reset (density, hidden fields, preset, layout)

## 4. Critical Conventions (Non-Negotiable)
1. **All SQL:** parameterized queries ONLY — never f-string SQL injection
   - ✅ `frappe.db.sql("SELECT * FROM \`tabBOQ Item\` WHERE name = %(name)s", {"name": name})`
   - ❌ `frappe.db.sql(f"SELECT * FROM \`tabBOQ Item\` WHERE name = '{name}'")`
2. **RPC endpoints:** whitelist deliberately, validate input, enforce document permissions and scope, and restrict mutation methods. Whitelisting alone is not authorization.
3. **CSS:** use scoped selectors and tokens; retain `!important` where required by an intentional Frappe cascade override, not for every new declaration.
4. **New CSS file?** Register in `hooks.py` `app_include_css` AND bump `?v=` param to bust cache
5. **DOM selectors:** verify behavior on every advertised supported version. v15/v16 dual-compatibility needs evidence on both, not only a v16 build.
6. **Theme writes:** the narrow high-frequency preference path can use `frappe.db.set_value(..., update_modified=False)` after authorization and field validation. Business documents normally require their document lifecycle; bypasses need a specific reason and invariant coverage.
7. **Scope tests:** always test as non-admin user (admin bypasses all scope filters)
8. **Python compatibility:** venv is Python 3.14, but code must remain Python 3.10 quote-nesting safe
9. **New transactional DocType with scope dimensions?** Follow the Scope Context checklist:
   - Review `project`, `company`, `cost_center`, `department` fields.
   - Display-only / derived fields: `fieldtype: "Link"`, `"read_only": 1`, `"in_standard_filter": 0`.
   - User-selectable fields: `"in_standard_filter": 0`; drive selection via `window.scopeContext` or a scoped whitelisted API.
   - Never call `frappe.db.get_value("Project", ...)` / `"Company", ...` from client scripts.
   - Bump `hooks.py` `?v=` cache busters for any modified JS files.
   - Run `python3 scripts/lint_scope_metadata.py` locally before committing.

## 5. Active Workstreams
> Read `SESSION_MEMORY.md` for the current sprint state.
>
> As of last update (2026-06-21):
> - **Sprint: rc-1.1 Follow-up (WP1–WP7)** — All 7 work packages complete
> - WP1 (Broader-app audit) — ✅ Done
> - WP2 (Migration survival test) — ✅ Done
> - WP3 (Handover docs) — ✅ Done
> - WP4 (VFC debug flag) — ✅ Done
> - WP5 (Project-wise Profitability) — ⏳ Blocked (client gate)
> - WP6 (Option B admin toggle) — ✅ Done
> - WP7 (Audit logging) — ✅ Done
> - **VFC Phase 3 Stabilization (WP0–WP5)** — ✅ Complete (commits 7aadbdd, d55f6a2, 698ea94)
> - Scope report overrides patched at import via `construction/__init__.py`

## 6. Key Files
| Purpose | Path |
|---------|------|
| **All CSS/JS registrations** | `construction/hooks.py` (app_include_css has 6 files; app_include_js has 20+ files) |
| **Boot session hook** | `construction/boot.py` |
| **BOQ CRUD API** | `construction/api/boq_api.py` (9 whitelisted endpoints) |
| **Theme API** | `construction/api/theme_api.py` (17 whitelisted endpoints) |
| **Scope query injection** | `construction/overrides/scope_query.py` |
| **Form Layout API** | `construction/construction/api/layout_api.py` (6 endpoints) |
| **VFC backend tests** | `construction/tests/test_vfc_backend.py` (39 tests) |
| **VFC browser tests** | `construction/public/js/vfc_layout_engine_tests.js` |
| **Architecture decisions** | `ADR.md` (8 accepted ADRs), `docs/ADR-001-accounting-dimension.md` |
| **CSS token reference** | `docs/token_reference.md` (54 tokens) |
| **Hook matrix** | `docs/hook_matrix.md` |
| **Developer onboarding** | `docs/onboarding.md` |
| **Session state** | `SESSION_MEMORY.md` (living document) |
| **Schema facts** | `docs/ai/SCHEMA_FACTS.md` |
| **Coding patterns** | `docs/ai/CODING_PATTERNS.md` |
| **ERPNext MCP bridge** | `erpnext-mcp-server/server.py` (read-only DocType queries) |

## 7. Memory Protocol

### For All Agents (Static Files)
1. Read this file (`AGENTS.md`) first.
2. Read `docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md` for the owner's engineering requirements.
3. Read `SESSION_MEMORY.md` for current sprint state.
4. If you need schema details, read `docs/ai/SCHEMA_FACTS.md` and verify the live schema.
5. If you need code patterns, read `docs/ai/CODING_PATTERNS.md`; examples require the standard's authorization and invariant checks.

### For MCP-Enabled Agents (Auto-Capture)

**MCP memory is a cache, not authority.** If recalled memory conflicts with live repo files, **live repo files win**.

#### Session Start (MANDATORY)
1. Execute `recall_memories` with query "construction erp current state"
2. Summarize recalled context before starting work
3. Verify critical facts against the live repo before acting

#### During Work (Automatic — No Prompting Needed)
Only use external capture when its destination and scope are authorized. Otherwise record locally in `SESSION_MEMORY.md`. Within that authorized boundary, store memory on these events:
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
1. Store summary of what was accomplished locally, or externally only within an authorized destination and scope
2. Update `SESSION_MEMORY.md` §3 and §6 as fallback

```bash
# Interactive session capture
python3 scripts/session_end.py
```

### External Auto-Capture (Git Hooks)
A `post-commit` git hook is documented as installed. Inspect current hooks before any authorized commit and verify that external capture is within the authorized destination and scope. The documented hook stores a memory to MCP with:
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
*Engineering instructions updated: 2026-10-04. Historical architecture summaries above must be verified against live source.*

*Update this file when project identity, tech stack, core architecture, or standing engineering instructions change.*
