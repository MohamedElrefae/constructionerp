# Phase 1 Implementation — BOQ Cost Estimation Engine

## Summary

Implemented the full Phase 1 End-to-End BOQ Cost Estimation Engine per PLAN.md, replacing the legacy CostItem lookup with BOQ Cost Analysis DocType, Resource Price History ledger, and PO/PI price capture hooks.

## What Was Built

### New DocTypes
1. **BOQ Cost Analysis** — Submittable analysis per BOQ Item with details child table, cost rollup, overhead/profit calculation, and approval workflow
2. **BOQ Cost Analysis Detail** — Child table with cost_stream, item_code, qty, wastage, cost_rate, amount
3. **Resource Price History** — Auditable price ledger captured from Purchase Invoice/Order submissions

### Service Modules
4. **resource_price_service.py** — `get_suggested_rate()` (PI→PO→Item Price priority), `capture_price_from_purchase_document()` (on_submit hook), `cancel_price_history_for_document()` (on_cancel hook)
5. **boq_cost_analysis_service.py** — Query helpers for approved analysis lookups and header budget refresh
6. **boq_report_service.py** — 5 estimation reports (summary, cost vs contract, resource requirements, price history, missing analysis)

### Patches
7. **v8_0/add_item_construction_fields.py** — Idempotent 7 Custom Fields on Item (resource type, cost stream, wastage, etc.)
8. **v8_1/deprecate_costitem_plantresource.py** — Non-destructive deprecation of CostItem/PlantResource

### Refactoring
9. **boq_item.py** — `fetch_cost_data()` now queries approved BOQ Cost Analysis instead of CostItem; preserves est_unit_cost on save
10. **hooks.py** — PO/PI doc_events, desk_links, translations, patches registration, `after_migrate` hook
11. **install.py** — `setup_item_construction_fields()` for idempotent Item custom fields

### Tests
12. **test_cost_analysis_engine.py** — 9 tests covering single/composite analysis, wastage, approval, deprecated CostItem fallback, only-one-approved enforcement, missing analysis report, and Resource Price History capture

## Test Results

```
test_cost_analysis_engine.py — 9/9 passed ✓
  ✔ test_single_component_analysis_rolls_up
  ✔ test_composite_analysis_rolls_up
  ✔ test_wastage_affects_detail_amount
  ✔ test_approval_refreshes_boq_item_est_unit_cost
  ✔ test_saving_boq_item_preserves_approved_est_unit_cost
  ✔ test_deprecated_costitem_lookup_no_longer_zeros_estimates
  ✔ test_only_one_approved_analysis_per_boq_item
  ✔ test_missing_analysis_report
  ✔ test_resource_price_history_capture

VFC backend tests (test_vfc_backend.py) — 39/39 passed ✓ (no regressions)
```

## Review Findings — All Resolved

### Phase 1 Final Review (6 findings)

| Finding | Fix Applied |
|---------|-------------|
| P1: DocPerms — Project Manager missing submit/cancel/amend; Site Engineer had write | Updated `boq_cost_analysis.json`: Project Manager gets submit/cancel/amend; Site Engineer loses write (read-only) |
| P1: Approval doesn't refresh BOQ Header budget totals | `update_boq_item_estimated_cost()` now calls `_refresh_boq_header_totals()` after persisting cost fields |
| P1: `get_resource_price_history()` ignores date/supplier filters, Python-side filtering | Rewritten using `frappe.qb` query builder with in-database filtering for all 4 optional params |
| P1: `ignore_links=True` bypasses Link validation for Item/UOM/Supplier | Removed `ignore_links=True`; changed `source_name` from Dynamic Link to Data (reference string, not navigable link); capture function now derives `currency` from doc or company default |
| P2: Cancellation search used `docstatus=2` (never matched) | Changed to `docstatus=1` (submitted + superseded) in `restore_prior_analysis_if_any()` |
| P2: Approval didn't persist overhead_amount, profit_amount, calculated_sell_price | `update_boq_item_estimated_cost()` now persists all 3 fields via `db_set` dict |

### Cost Database Handoff Consultant Review

The handoff document `docs/ai/active/COST_DATABASE_HANDOFF.md` was reviewed and the following high-risk issues were fixed in code and/or documentation:

| Issue | Fix |
|-------|-----|
| Resource type enum mismatch (`Other` vs `Overhead`) | Document corrected; actual DocType/patch already used `Material / Labor / Plant / Subcontract / Overhead` |
| `Resource Price History` permissions misdocumented | Document corrected to match actual DocType (System Manager full; Construction Owner + Project Manager read/report only) |
| Imported/manual prices did not drive `get_suggested_rate()` | Rewrote service to check Last PI → Last PO → Last other source → Item Price; added `region` and `as_of_date` parameters |
| `region` mapped to `project` | Added real `region` Data field to `Resource Price History`; updated report filter |
| BOQ Item master/template confusion | Document now recommends `BOQ Cost Analysis.is_template=1` and labels live BOQ Item bilingual support as a schema gap |
| `description_en` mapped to `BOQ Item.item_type` | Removed; `item_type` is Select (`Measured Work`, etc.) |
| Arabic fields aspirational | Added `item_name_ar` custom field to Item patch and `install.py` setup; documented BOQ item Arabic gap |
| Missing required fields in import schema | Added `company`, `currency`, `exchange_rate`, `source_doctype`, `source_name` to all schemas |
| Seed prices not marked illustrative | Added explicit disclaimers and labeled all example prices as placeholders |
| No dry-run/validation stage | Added dry-run stage and automated import validation report deliverable |
| Missing source citations | Added requirement to cite every source with URL and access date |
| Price locking not modeled | Documented existing `as_of_date` parameter in `get_suggested_rate()` |

## Files Modified

- `construction/construction/doctype/boq_cost_analysis/boq_cost_analysis.py` — New
- `construction/construction/doctype/boq_cost_analysis/boq_cost_analysis.json` — New
- `construction/construction/doctype/boq_cost_analysis_detail/boq_cost_analysis_detail.py` — New
- `construction/construction/doctype/boq_cost_analysis_detail/boq_cost_analysis_detail.json` — New
- `construction/construction/doctype/resource_price_history/resource_price_history.py` — New
- `construction/construction/doctype/resource_price_history/resource_price_history.json` — New
- `construction/services/resource_price_service.py` — New
- `construction/services/boq_cost_analysis_service.py` — New
- `construction/services/boq_report_service.py` — New
- `construction/construction/doctype/boq_item/boq_item.py` — Modified
- `construction/hooks.py` — Modified
- `construction/install.py` — Modified
- `construction/patches.txt` — Modified
- `construction/construction/patches/v8_0/add_item_construction_fields.py` — New
- `construction/construction/patches/v8_1/deprecate_costitem_plantresource.py` — New
- `construction/tests/test_cost_analysis_engine.py` — New
- `construction/tests/test_cost_database_api.py` — New
- `construction/api/cost_database_api.py` — New
- `construction/services/cost_database_service.py` — Modified (template generator)
- `construction/construction/doctype/boq_cost_analysis/boq_cost_analysis.json` — Modified (template `boq_item` no longer mandatory)
- `construction/construction/doctype/boq_cost_analysis/boq_cost_analysis.py` — Modified (conditional `boq_item` validation)
- `construction/construction/doctype/boq_cost_analysis_detail/boq_cost_analysis_detail.json` — Modified (added `Import` rate source)
- `scripts/ai_context_check.py` — Modified
- `docs/ai/SCHEMA_FACTS.md` — Modified
- `docs/ai/active/COST_DATABASE_HANDOFF.md` — New (Egyptian cost database handoff for online agent)
- `docs/ai/active/IMPLEMENTATION.md` — Modified (Phase 2 summary)

## Phase 2 — Cost Database Import API & Excel Template (Completed, Reviewed & Restored)

> **Provenance note (2026-08-19):** Phase 2 was originally implemented in the dirty worktree and
> preserved in WIP snapshot branch `wip/dirty-snapshot-2026-07-01` (commit `edccbf3`), NOT on `develop`.
> A consultant review correctly rejected the original completion report because the work was not on the
> target branch. This section documents the reviewed restoration onto `feat/cost-database-phase2`
> (parent: `develop` @ `f6c239a`, cherry-pick of `edccbf3` plus review fixes below).

### What Was Built
1. **Whitelisted import API** (`construction.api.cost_database_api.import_cost_database`)
   - Multipart upload endpoint wrapping the existing `import_cost_database_from_excel` service.
   - Supports `dry_run`, `auto_submit`, `region`, and `price_date` parameters.
   - Permission-gated by `Resource Price History` create permission.

2. **Whitelisted template download API** (`construction.api.cost_database_api.download_cost_database_template`)
   - `mode=blank`: headers, column styling, and data validation only.
   - `mode=sample`: pre-filled illustrative Egyptian resources, BOQ item templates, and rate-analysis recipes.

3. **Excel template generator** (`construction.services.cost_database_service.generate_cost_database_template`)
   - Creates a workbook with `Resources`, `BOQItemTemplates`, `RateAnalysis`, `PriceHistory`, and hidden `_Metadata` sheets.
   - Adds dropdown validation for `resource_type`, `cost_stream`, and `rate_source`.
   - Auto-sizes columns and applies header styling.

4. **API tests** (`construction/tests/test_cost_database_api.py`)
   - 10 tests: blank/sample template generation, header validation, sample data presence, API response
     shape, invalid-mode rejection, dry-run import, real import with schema persistence, idempotent
     re-import, and draft-template upsert on changed rates.

### Review Fixes Applied During Restoration (2026-08-19)

Consultant review of the snapshot identified gaps; all fixed and tested:

1. **Schema-validity fix — template fields silently dropped.** The importer wrote `description_ar`
   and `category` on `BOQ Cost Analysis`, but those fields did not exist on the DocType, so the
   values were silently discarded. Added `category` (Data, filterable) and `description_ar`
   (Small Text) to the DocType; importer values now persist (verified by test).
2. **Header-collision fix — `category` alias hijack.** `COLUMN_ALIASES` mapped `category` as an
   alias of `resource_type`, so the `BOQItemTemplates` category column was mis-canonicalized and
   lost. Removed the alias; added a dedicated `category` canonical column.
3. **Import idempotency.** Re-importing the same file no longer duplicates `Resource Price History`
   rows (identical-row skip) or `BOQ Cost Analysis` templates (Draft templates are updated in
   place; Submitted templates are skipped with a warning). Result dict now reports
   `records_updated` and `records_skipped` alongside `records_created`.
4. **Missing engine dependencies restored.** The snapshot commit was incomplete relative to its own
   test suite: `test_cost_analysis_engine.py` requires `BOQ Structure.category` /
   `BOQ Structure.description_ar` fields and the `boq_item.py` `fetch_cost_data()` refactor
   (approved-analysis cost fetch). Extracted exactly these from snapshot commit `ea3b53b`
   (deliberately excluding its known-broken JS/scope-context changes) and updated the
   Property 17 test accordingly.
5. **VFC test isolation fix.** `test_vfc_backend.py` `TestLayoutAPI` could fail on repeated runs
   because `save_layout()` commits mid-test, defeating rollback isolation; setUp/tearDown now
   purge the specific test profiles (`Task-_Test_UpdateMe`, `Task-_Test_SaveNew`).

### Phase 2 Test Results (re-run from feature branch, 2026-08-19)

```
test_cost_analysis_engine.py — 17/17 passed ✓
test_cost_database_api.py — 10/10 passed ✓
test_vfc_backend.py — 39/39 passed ✓ (verified stable across consecutive runs)
test_boq_properties.py — 17 pre-existing scope-context setUp errors (identical on clean develop; not Phase 2 scope)
```

### Site Test-Bootstrap Blocker Resolved (2026-08-19)

Consultant review could not reproduce the cost-database / cost-analysis runs via the standard
`bench run-tests`: bootstrap aborted with `DocType Payment Gateway not found` before any test ran.

Root cause (verified, pre-existing on `develop` @ `f6c239a` — reproduced with pre-merge code):
ERPNext v16 moved `Payment Gateway` into the standalone `payments` app; this site intentionally
does not install it, leaving `Payment Gateway Account.payment_gateway` a dangling Link field.
Frappe's test-record generator walks Link dependencies depth-first and crashes on the missing
DocType, aborting the entire bootstrap. Chain: `User Scope Context → User → Email Account →
Company → … → Subscription Plan → Payment Gateway Account → Payment Gateway`.

Resolution (no core changes, no `payments` install — deliberate scope decision): added
`construction/tests/test_bootstrap_guard.py`, applied from `construction/tests/__init__.py`
(imported by the runner before record preloading). It wraps the generator to skip missing
DocTypes with a one-time logged warning instead of crashing. Test-infrastructure only — never
active in production.

Post-fix evidence (standard `bench run-tests` on merged `develop`):

```
test_cost_database_api.py — 10/10 OK
test_cost_analysis_engine.py — 17/17 OK
test_vfc_backend.py — 39/39 OK
```

## Final Review Verdict

**PASS** — All 6 findings (4 P1, 2 P2) from FINAL_DIFF.md have been fixed and verified.
Restoration review: 5 additional findings fixed (see "Review Fixes Applied During Restoration").

## Gate Check Status

- Schema drift checker: ✅ PASS (regenerated; BOQ Cost Analysis now 30 fields)
- AI context check: ✅ 40/40 passed
- New test suite: ✅ 27/27 passed (Phase 2: 10, existing cost-analysis: 17)
- Regression: ✅ No regressions — VFC backend 39/39; all other app-suite failures are pre-existing
  scope-context setUp errors, verified byte-identical on clean `develop` (test_boq_properties 17,
  test_boq_integration 10, test_boq_link_queries 8, test_boq_item_stage 7,
  test_boq_structure_conversion 1).
