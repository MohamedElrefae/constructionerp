# Builder Handoff: Phase 1 End-to-End BOQ Cost Estimation Engine

**Role:** Builder handoff  
**Repo:** `/home/mohamed/frappe-bench/apps/construction`  
**Branch:** `develop`  
**Start Commit:** `f6c239a`  
**Plan:** `docs/ai/active/PLAN.md`  
**Review:** `docs/ai/active/REVIEW.md`  
**Requested By:** Mohamed Elrefae / Codex

## Mission

Implement the estimation backbone according to the approved plan (`docs/ai/active/PLAN.md`) and the approved plan review (`docs/ai/active/REVIEW.md`). Do not implement out-of-scope features. Write the official implementation log to `docs/ai/active/IMPLEMENTATION.md` using `docs/ai/templates/IMPLEMENTATION.md`.

## Required Pre-Build Gate

Run from repo root:

```bash
python3 scripts/schema_drift_checker.py
python3 scripts/ai_context_check.py
git status --short
```

Hard stop if either checker fails. Preserve unrelated dirty worktree changes.

## Required Files to Read

- `AGENTS.md`
- `SESSION_MEMORY.md`
- `docs/ai/CONTEXT_INDEX.md`
- `docs/ai/AGENT_WORKFLOW.md`
- `docs/ai/SCHEMA_FACTS.md`
- `docs/ai/templates/IMPLEMENTATION.md`
- `docs/ai/active/PLAN.md`
- `docs/ai/active/REVIEW.md`
- `construction/construction/doctype/boq_item/boq_item.py`
- `construction/construction/doctype/boq_item/boq_item.json`
- `construction/construction/doctype/boq_header/boq_header.py`
- `construction/install.py`
- `construction/hooks.py`
- `construction/services/boq_accounting.py`
- `construction/services/boq_transaction_validation.py`
- `construction/services/revised_boq_queries.py`
- `docs/Boq Reports/HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md`
- `docs/Boq Reports/HOE_BOQ_REPORTS_PHASE0_GATE_MENA.md`

## Build Focus & Boundaries

Strictly adhere to the following guidelines from the approved plan:
- **Idempotent Item fields**: Add custom construction fields to standard `Item` via Custom Field setup or migration patches in the `construction` app. Do not touch core `erpnext` files.
- **New DocTypes**: Register new DocTypes (`BOQ Cost Analysis`, `BOQ Cost Analysis Detail`, `Resource Price History`) in the `Construction` module with the designated naming rules and `DocPerm` roles.
- **Scope Verification**: Carry and validate `company` and `project` parameters inside new DocTypes to support scope-context rules.
- **PO/PI Rate Capture Hooks**: Wire hook events for PO/PI history capture on `on_submit` and mark history records as inactive/cancelled on `on_cancel` transitions.
- **Validation Fallback**: Refactor `BOQItem.fetch_cost_item_data()` to query the approved `BOQ Cost Analysis` or preserve the current `est_unit_cost` during saves, avoiding any query to `CostItem`.
- **SQL parameterization**: Enforce parameterized SQL only.
- **Labor Policy Protection**: Retain `Direct Labor Designation` untouched when deprecating `CostItem`/`PlantResource`.

## Expected Output

Create:
```text
docs/ai/active/IMPLEMENTATION.md
```

## Testing Strategy

Run the test suite:
```bash
bench --site v16.localhost run-tests --app construction --module construction.tests.test_boq_properties
bench --site v16.localhost run-tests --app construction --module construction.tests.test_boq_item_properties
bench --site v16.localhost run-tests --app construction --module construction.tests.test_transaction_validation
```

Add the new tests specified in the testing section of `PLAN.md`.
