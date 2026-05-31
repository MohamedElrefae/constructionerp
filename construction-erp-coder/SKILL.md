# construction-erp-coder

## Description

Construction ERP coding assistant. Full-stack Frappe/ERPNext custom app for construction management: BOQ (Bill of Quantities), cost estimation, theming, scope context, and form layout engine.

**Use when:** writing BOQ logic, theme CSS, scope context queries, Frappe DocTypes, or any Construction ERP feature.

**Triggers on:** `boq`, `construction erp`, `frappe`, `cost item`, `scope context`, `construction theme`, `vite`, `vfc`, `form layout`

**Repo root:** `/home/mohamed/frappe-bench/apps/construction`

---

## Quick Start for Agents

At the start of every session involving this codebase:

1. **Read** `AGENTS.md` — project identity, tech stack, 4 core systems, critical conventions
2. **Read** `SESSION_MEMORY.md` — current sprint, active workstreams, blockers
3. **Read** `docs/ai/CONTEXT_INDEX.md` — map of all memory files

If you need deep details:
- Schemas → `docs/ai/SCHEMA_FACTS.md`
- Code patterns → `docs/ai/CODING_PATTERNS.md`

---

## Critical Rules (Never Break)

1. **BOQ Item has NO `item_code` or `item_name`.** It uses `cost_item` (Data — free text). Never assume an ERPNext Item link.
2. **Only 6 CSS files are registered in `hooks.py` `app_include_css`.** Generated themes and special-purpose files (login, email, print) load conditionally. Do not register all 22 CSS files.
3. **All SQL must be parameterized.** Never use f-strings in SQL queries.
4. **Theme hot-path updates** must use `frappe.db.set_value(..., update_modified=False)`, not `doc.save()`.
5. **Test scope features as non-admin.** Administrator bypasses all scope filters.
6. **Python 3.10 quote-nesting compatibility** is required even though venv is 3.14.

---

## Core Systems

| System | Status | Key Files |
|--------|--------|-----------|
| **Theme** | ✅ Complete | `modern_theme.css` (registered), `theme_api.py` (17 whitelisted endpoints), `boot.py` |
| **Scope Context** | ✅ Complete | `user_scope_context.json`, `overrides/scope_query.py`, `scope_context.js` |
| **BOQ** | ✅ Foundation complete | `boq_api.py`, `services/` (12 modules), NestedSet WBS tree |
| **Form Layout Engine (VFC)** | 🟡 Phase 1+2 done, 3+ in progress | `vfc_layout_engine.js`, `vite_layout_controls.js`, `Form Layout Profile` DocType |

---

## Reference Files

| File | Purpose |
|------|---------|
| `references/project-context.md` | Current workstreams, active tasks, blockers |
| `references/doctype-schema.md` | DocType field lists (links to canonical `docs/ai/SCHEMA_FACTS.md`) |
| `references/coding-patterns.md` | Reusable code templates (links to canonical `docs/ai/CODING_PATTERNS.md`) |

---

## Validation

Before generating code that touches schemas or registrations, run:

```bash
cd /home/mohamed/frappe-bench/apps/construction
python3 scripts/ai_context_check.py
```

If any check fails, stop and verify the live repo state before proceeding.

---

## Memory Protocol

- **Repo files are source of truth.** If this skill conflicts with `AGENTS.md`, `SESSION_MEMORY.md`, or live DocType JSON, the repo file wins.
- Update `SESSION_MEMORY.md` after every session.
- Run `ai_context_check.py` when schemas change.

---

*Skill version: 1.0*  
*Last updated: 2026-05-31*  
*Canonical docs: `docs/ai/CONTEXT_INDEX.md`*
