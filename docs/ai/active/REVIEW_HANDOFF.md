# Reviewer Handoff: Phase 1 End-to-End BOQ Cost Estimation Engine

**Role:** Reviewer handoff  
**Repo:** `/home/mohamed/frappe-bench/apps/construction`  
**Branch:** `develop`  
**Start Commit:** `f6c239a`  
**Plan:** `docs/ai/active/PLAN.md`  
**Requested By:** Mohamed Elrefae / Codex

## Mission

Perform an adversarial review of `docs/ai/active/PLAN.md` before any Builder starts implementation. Do not implement code. Write the official review output to `docs/ai/active/REVIEW.md` using `docs/ai/templates/REVIEW.md`.

## Required Pre-Review Gate

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
- `docs/ai/templates/REVIEW.md`
- `docs/ai/active/PLAN.md`
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

## Review Focus

Attack the plan for implementation safety:

- Schema drift or invented fields.
- Whether `BOQ Item.fetch_cost_item_data()` deprecation is sequenced safely.
- Whether `BOQ Item.est_unit_cost` and `est_line_total` rollup can work without fighting existing controller behavior.
- Whether Item custom fields should be custom fields on standard ERPNext `Item` or app-owned fixtures/patches.
- Whether new DocTypes need permissions, modules, naming rules, indexes, workflow/status fields, and tests.
- Whether PI/PO rate capture is safe as estimation history only and does not create accounting or stock side effects.
- Whether `CostItem` and `PlantResource` removal/deprecation is safe with confirmed no-data evidence and does not touch `Direct Labor Designation`.
- Whether scope context is correctly handled for new estimation DocTypes and reports.
- Whether SQL aggregation/report plans avoid N+1 queries and f-string SQL.
- Whether progress billing, subcontractor certificates, Site/Gang Timesheet, Plant Timesheet, and actual-cost variance remain truly out of scope.

## Expected Output

Create:

```text
docs/ai/active/REVIEW.md
```

Use verdict exactly:

- `APPROVED`
- `NEEDS_REVISION`

Use `NEEDS_REVISION` if the Builder would need to make architecture decisions not already locked by the plan.

## Known Context for Reviewer

- The human explicitly chose estimation-first.
- Progressive billing and actual site cost are later phases.
- `CostItem` and `PlantResource` are confirmed empty scaffolds, but controller and schema references still exist.
- `Direct Labor Designation` remains and must not be removed.
- Current worktree was already dirty before this plan/handoff.
