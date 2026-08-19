# Feature Plan: Phase 1 End-to-End BOQ Cost Estimation Engine

**Role:** Architect  
**Status:** DRAFT  
**Repo:** `/home/mohamed/frappe-bench/apps/construction`  
**Branch:** `develop`  
**Start Commit:** `f6c239a`  
**Requested By:** Mohamed Elrefae / Codex request: "create plan for now for review before implementation"

## Objective

Build the estimation backbone before progressive billing, subcontractor certificates, or actual site-cost capture. The completed feature must let users build, approve, and report resource-based unit-rate analysis for every BOQ Item using ERPNext Item as the unified resource master.

## Files Read

- `AGENTS.md`
- `SESSION_MEMORY.md`
- `docs/ai/CONTEXT_INDEX.md`
- `docs/ai/AGENT_WORKFLOW.md`
- `docs/ai/SCHEMA_FACTS.md`
- `docs/ai/templates/PLAN.md`
- `construction/construction/doctype/boq_item/boq_item.py`
- `construction/construction/doctype/boq_item/boq_item.json`
- `docs/Boq Reports/HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md`
- `docs/Boq Reports/HOE_BOQ_REPORTS_PHASE0_GATE_MENA.md`
- `/home/mohamed/.gemini/antigravity/brain/ed6ead0c-a9e6-4c4d-a1a9-837a15d011af/implementation_plan.md`

## Commands Run

```bash
python3 scripts/schema_drift_checker.py
python3 scripts/ai_context_check.py
git status --short
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
```

Result:

- `schema_drift_checker.py`: passed; schema facts match live DocType JSON.
- `ai_context_check.py`: passed; 40 checks passed, 0 failed.
- Worktree is dirty before this plan; preserve unrelated existing changes.
- Reviewer completed `docs/ai/active/REVIEW.md` with `NEEDS_REVISION`; this plan revision incorporates all required reviewer changes.

## Live Schema Evidence

- `BOQ Item` currently uses `cost_item` as a `Data` placeholder and has no `item_code` or `item_name`.
- `BOQ Item.est_unit_cost` and `est_line_total` are read-only fields that must be written by controller/service logic.
- `BOQ Item.fetch_cost_item_data()` currently reads deprecated `CostItem.total_direct_cost` and must be replaced by approved BOQ Cost Analysis rollup.
- `CostItem` and `PlantResource` exist in schema facts but are confirmed empty scaffolds and must not remain the estimation source of truth.
- `Direct Labor Designation` remains a labor policy/gating child table; do not remove it.
- Standard ERPNext `Item` custom fields must be provisioned from this app only through idempotent Custom Field setup or migration patches; do not edit ERPNext core DocType JSON.

## Scope Decision

This phase is estimation-only.

Included:

- ERPNext Item construction resource metadata.
- Resource Price History and PI-then-PO suggested rates with manual override.
- BOQ Cost Analysis parent/detail DocTypes.
- Approved cost-analysis rollup into BOQ Item estimated cost fields.
- Estimation reports and missing-analysis exception report.
- Safe deprecation path for `CostItem` and `PlantResource`.

Excluded:

- Owner progressive billing.
- Sales Invoice progress-billing generation/reconciliation.
- Subcontractor Payment Certificate.
- Site/Gang Timesheet.
- Plant Timesheet.
- Actual cost capture and allowable-vs-actual variance.
- Retention, advance recovery, VAT/e-invoice, social insurance, and other MENA certificate mechanics.

## Technical Approach

- DocTypes modified:
  - Standard ERPNext `Item`: add construction custom fields for estimation only.
  - `BOQ Item`: remove active dependency on `CostItem` lookup; keep `cost_item` only as deprecated/import trace text unless a later migration removes it.
  - New `BOQ Cost Analysis`: module `Construction`, naming series `BCA-.YYYY.-.#####`, one active approved unit-rate analysis per BOQ Item.
  - New child table `BOQ Cost Analysis Detail`: module `Construction`, child table, resource build-up rows linked to ERPNext Item.
  - New `Resource Price History`: module `Construction`, naming series `RPH-.YYYY.-.#####`, auditable suggested-rate source from Purchase Invoice and Purchase Order rows.

- Python files modified:
  - `boq_item.py`: replace `fetch_cost_item_data()` behavior with cost-analysis-safe logic.
  - New services for cost-analysis calculation, approval, rate suggestion, and report data.
  - Install/patch code for custom fields, DocTypes, indexes, and controlled scaffold deprecation.
  - `hooks.py`: add only submit/cancel price-capture doc events needed for PO/PI history, with no GL/stock side effects.

- JavaScript/CSS files modified:
  - Only add form helpers if needed for rate suggestion buttons and BOQ Item filtered links.
  - No theme/VFC/CSS work unless required by standard Frappe form behavior.

- Database changes:
  - Add custom fields to ERPNext `Item`:
    `is_construction_resource`, `construction_resource_type`, `default_cost_stream`, `default_wastage_pct`, `default_productivity_qty_per_day`, `labor_trade_designation`, `linked_asset`.
  - Add these Item fields through construction app Custom Field setup or migration patches only; never edit ERPNext core `item.json`.
  - Create `Resource Price History` with Link fields for `company`, `project`, `item_code`, `supplier`, and source document metadata.
  - Create `BOQ Cost Analysis` with Link fields for `company`, `project`, `boq_header`, `boq_structure`, and `boq_item`.
  - Create `BOQ Cost Analysis Detail` with `item_code`, UOM, stream, qty/rate/wastage/amount fields, and supplier/source fields where needed.
  - DocPerms:
    - `BOQ Cost Analysis`: System Manager full; Construction Owner and Project Manager create/read/write/submit/cancel/amend/report/export; read/report/export for other existing construction read roles only if already present.
    - `BOQ Cost Analysis Detail`: child table; no standalone permissions.
    - `Resource Price History`: System Manager full; Construction Owner and Project Manager read/report/export; write only through service/hooks unless System Manager.
  - Add indexes for `boq_item`, `item_code`, `analysis_status`, and price-history lookup fields after final query shape is implemented.
  - Deprecate/remove `CostItem` and `PlantResource` only after BOQ Item no longer depends on them and zero-row SQL evidence is attached. This patch must not touch `Direct Labor Designation` or `Construction Settings.direct_labor_designations`.

## Implementation Steps

1. Add Item construction custom fields idempotently.
2. Create `Resource Price History` and rate suggestion service.
3. Add `on_submit` and `on_cancel` handlers for Purchase Invoice and Purchase Order price history:
   - `on_submit`: insert immutable Resource Price History rows for submitted child rows with item/rate/UOM.
   - `on_cancel`: mark matching history rows as cancelled/excluded from suggestions; do not delete historical rows.
   - suggestion queries must ignore cancelled/excluded history rows.
   - this is for estimation history only, not actual-cost reporting.
4. Create `BOQ Cost Analysis` and `BOQ Cost Analysis Detail`.
5. Implement calculation service:
   - detail amount = `qty_per_boq_unit * cost_rate * (1 + wastage_pct / 100)`
   - total direct unit cost = sum detail amounts
   - overhead/profit calculations remain compatible with existing BOQ Item fields
6. Implement approval workflow:
   - only one active approved analysis per BOQ Item
   - approval writes `BOQ Item.est_unit_cost` and `BOQ Item.est_line_total`
   - header/structure budget rollups are refreshed through existing BOQ Header rollup behavior
7. Refactor `BOQ Item.fetch_cost_item_data()` so validation never overwrites approved analysis results with deprecated CostItem values:
   - If an active approved `BOQ Cost Analysis` exists, set `est_unit_cost` from its approved total direct unit cost.
   - If none exists, preserve the current `est_unit_cost` value during normal saves; initialize empty values to 0 only for new/blank records.
   - Never query `CostItem` from BOQ Item validation after this phase.
8. Implement estimation reports:
   - BOQ Cost Analysis Summary
   - BOQ Item Estimated Cost vs Contract Rate
   - Resource Requirement Summary by resource stream
   - Resource Price History / Rate Movement
   - BOQ Items Missing Approved Cost Analysis
   - All report SQL must use parameterized inputs; f-string SQL and string-concatenated SQL are forbidden.
9. Prepare controlled deprecation/removal patch for `CostItem` and `PlantResource`.
10. Update docs/AI handoff files after implementation evidence exists.

## Risks and ERP Impact

- Permissions:
  - Cost-analysis edit/approval must be limited to System Manager, Construction Owner, and Project Manager.
  - Resource Price History is service-written; only System Manager can manually write, while Construction Owner and Project Manager can read/report/export.
  - Report read access should follow existing BOQ/project scope rules.

- Scope context:
  - `BOQ Cost Analysis` must carry `company`, `project`, `boq_header`, `boq_structure`, and `boq_item`.
  - `Resource Price History` must carry `company` and optional `project`.
  - `company` and `project` must be populated from the BOQ Header or source document and validated against selected BOQ/source context.
  - Link queries must filter BOQ Items by active scope and BOQ Header status.

- Accounting/inventory/ledger impact:
  - No GL, Stock Ledger, Sales Invoice, Purchase Invoice payable, or actual-cost report impact in this phase.
  - Purchase Invoice/Purchase Order hooks only copy item rates into Resource Price History for estimation suggestions.

- Migration/backfill:
  - Attach SQL count evidence for `tabCostItem` and `tabPlantResource`.
  - Do not drop/deprecate scaffolds until BOQ Item controller is safe without `CostItem`.
  - Existing BOQ Items without approved analysis remain valid but appear in the missing-analysis report.

- Performance:
  - Benchmark on approximately 1,000 BOQ Items.
  - Use SQL aggregation for reports; avoid per-row `frappe.get_doc` loops in summary reports.
  - All SQL must be parameterized.

## Testing Strategy

```bash
python3 scripts/schema_drift_checker.py
python3 scripts/ai_context_check.py
bench --site v16.localhost run-tests --app construction --module construction.tests.test_boq_properties
bench --site v16.localhost run-tests --app construction --module construction.tests.test_boq_item_properties
bench --site v16.localhost run-tests --app construction --module construction.tests.test_transaction_validation
```

Additional tests Builder must add:

- Item custom field setup is idempotent.
- Resource Price History returns last submitted Purchase Invoice before Purchase Order.
- Cancelled Purchase Invoice/Purchase Order rows are excluded from future rate suggestions while audit rows remain traceable.
- Manual rate override is used in cost-analysis approval.
- Single-component analysis rolls up to BOQ Item.
- Composite analysis rolls up to BOQ Item.
- Wastage affects detail amount correctly.
- Approval refreshes BOQ Header budget totals.
- Deprecated `CostItem` lookup no longer zeros out approved estimates.
- Saving a BOQ Item after analysis approval preserves the approved `est_unit_cost`.
- New DocPerms allow intended non-admin roles to create/approve/read cost analyses.
- Scope mismatch between BOQ/source document and cost analysis is rejected.
- Report SQL tests cover parameterized filtering and avoid N+1 loops where practical.
- Missing-analysis report lists BOQ Items without approved analysis.
- No owner billing, subcontract certificate, or actual site-cost behavior is introduced.

## Known Gaps / Not Now

- Server-side direct-cost gate hardening remains required before actual-cost reports, but it does not block estimation-only implementation.
- Progress billing remains blocked until a later phase wires BOQ certification to Sales Invoice creation/reconciliation.
- Subcontractor certificates, Site/Gang Timesheet, Plant Timesheet, retention, advance recovery, VAT/e-invoice, and social-insurance rules remain later phases.

## Approval

Human approval required before Reviewer and Builder start.
