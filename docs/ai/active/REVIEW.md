# Adversarial Plan Review

**Role:** Reviewer  
**Plan Status:** APPROVED  
**Repo:** `/home/mohamed/frappe-bench/apps/construction`  
**Branch:** develop  
**Start Commit:** f6c239a

## Files Read

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

## Findings

| Severity | Finding | Evidence | Required Change |
|---|---|---|---|
| None | All previously identified architectural gaps and implementation risks have been successfully addressed. | `docs/ai/active/PLAN.md` | None. Ready for Builder. |

## Security and Permission Review

- **Role Gating:** The updated plan correctly details that `BOQ Cost Analysis` will enforce role-gated access (System Manager, Construction Owner, and Project Manager). `Resource Price History` will only be writable via internal hooks/services unless the user is a System Manager.
- **Server-Side Gate Validation:** The plan has locked in the design requirement for server-side validation checks in `boq_transaction_validation.py` to prevent API-level bypasses of direct-cost gates.
- **SQL Safety:** The plan now explicitly mandates parameterized SQL queries for all calculations and reports.

## Schema and Migration Review

- **Core ERPNext Protection:** Custom fields on `Item` will be created idempotently using migration patches or Custom Field setup via the construction app, fully protecting standard `erpnext` code/JSON schemas.
- **Deprecation Patches:** The deprecation of `CostItem` and `PlantResource` is safely separated from the preservation of `Direct Labor Designation`.
- **Naming & Modules:** New DocTypes are cleanly structured within the `Construction` module and naming conventions (`BCA-.YYYY.-.#####`, `RPH-.YYYY.-.#####`) have been defined.

## Performance Review

- **Optimized Rollups:** WBS structures and `BOQHeader` rollups will utilize optimized, parameterized queries to avoid performance bottlenecks.
- **N+1 Avoidance:** The report data service (`boq_report_data.py`) will utilize parameterized SQL joins rather than in-loop `get_doc` requests.

## Required Revisions

All previously identified revision requirements are now resolved:
1. `fetch_cost_item_data()` refactoring has a clear fallback strategy that does not overwrite `est_unit_cost` during save operations once a cost analysis is approved.
2. Standard core protection for ERPNext `Item` fields is locked down.
3. DocPerm settings and modules are fully specified.
4. Hook events for price capture capture only `on_submit` states and handle `on_cancel` correctly.
5. Scope context fields (`company` and `project`) are required and validated.
6. Parameterized SQL is explicitly enforced.
7. Deprecation script safety guarantees the preservation of labor trade configurations.

## Approval Gate

[Human approval or explicit skip required before Builder starts.]
