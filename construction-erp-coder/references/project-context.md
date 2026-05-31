# Project Context — Construction ERP

> **Source of truth:** `SESSION_MEMORY.md` in repo root.  
> This file is a skill-local snapshot. If conflict, `SESSION_MEMORY.md` wins.

---

## Current Sprint (2026-05-31)

| Task | Status | Next Action |
|------|--------|-------------|
| AI Memory Architecture Phase 1 | ✅ Done | Run validation script; proceed to Phase 2 if stable |
| Form Layout Engine Phase 3+ | 🟡 In Progress | Continue layout feature expansion |
| BOQ Accounting Integration | 🟡 In Progress | Continue integration with Purchase Order / Invoice / Stock Entry hooks |
| Cost Estimation (CostItem) | ⬜ Not Started | — |
| Procurement (PlantResource) | ⬜ Not Started | — |

## Active Branches

- `feature/vite-ui-v1` (current)
- `develop`
- `main`

## Blockers

None as of 2026-05-31.

## Recently Completed

- `AGENTS.md` rewritten from Scope Context dev report → agent context file
- `SESSION_MEMORY.md` created
- `docs/ai/` reference folder created (CONTEXT_INDEX, SCHEMA_FACTS, CODING_PATTERNS)
- `scripts/ai_context_check.py` validation script created and passing

---

## Module Health

| Module | Health | Note |
|--------|--------|------|
| Theme System | 🟢 Healthy | 22 CSS files, 17 theme API endpoints, stable |
| Scope Context | 🟢 Healthy | Query injection tested, Redis cache stable |
| BOQ Foundation | 🟢 Healthy | 14 DocTypes, 12 services, tree operations working |
| VFC Layout Engine | 🟡 Active dev | Phase 3+ features in progress |
| Vite UI | 🟢 Healthy | Bundle stable, controls working |
| Arabic Localization | 🟢 Healthy | Patches v6.0–v6.6 applied |
| Searchable Dropdown | 🟢 Healthy | Global Link + Select overrides active |

---

*For full session log and decision history, see `SESSION_MEMORY.md` §6.*
