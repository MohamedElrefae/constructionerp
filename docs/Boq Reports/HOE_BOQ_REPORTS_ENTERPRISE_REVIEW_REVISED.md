# Head of Engineering Review Report: Enterprise BOQ Reports

Date: 2026-06-28

Prepared for: Head of Engineering Department  
Prepared by: Codex, acting as software consultant for construction ERP planning and implementation  
Repository reviewed: `/home/mohamed/frappe-bench/apps/construction`  
Status: **Revised for implementation planning with business decisions incorporated**

---

## 1. Executive Decision

The current Construction ERP app has a strong BOQ structural foundation: BOQ headers, WBS structures, leaf BOQ items, stage quantities, variation quantity revisions, scope-aware transaction attribution, and original/revised BOQ query services are already present in the live codebase.

However, the app is not yet an enterprise BOQ reporting engine. The missing layer is the construction cost-control backbone: resource-level rate analysis, price history, committed/actual cost aggregation, allowable cost, and exception reporting.

The recommended direction is to build the next phase around **Unified ERPNext Item Mapping**:

- Materials, labor trades, plant/equipment services, subcontract packages, and overhead resources should be represented as standard ERPNext `Item` records.
- `BOQ Cost Analysis Detail` should link directly to ERPNext `Item.item_code`.
- Empty custom masters `CostItem` and `PlantResource` should be removed or deprecated through a controlled patch based on confirmed no-data status. `Direct Labor Designation` may remain as a labor policy/gating helper, but costing should use ERPNext Items.
- Enterprise reports should reconcile **budget, allowable, committed, actual, certified revenue, and exceptions** by `Project -> BOQ Header -> BOQ Structure -> BOQ Item -> ERP Item`.

This recommendation aligns with construction ERP practice seen in RIB/CCS Candy resource cost-code control, Procore budget-code/direct-cost visibility, Oracle-style cost breakdown discipline, and ERPNext's own Item, Item Price, Stock, and Accounting Dimension model.

---

## 2. Verified Live Codebase Findings

### 2.1 BOQ Header and Lifecycle

Verified file: `construction/construction/doctype/boq_header/boq_header.py`

- `BOQ Header` uses forward-only statuses: `Draft -> Pricing -> Frozen -> Locked`.
- On lock, it writes `locked_by`, `locked_date`, and creates baseline quantity revisions.
- It rolls up:
  - `total_contract_value`
  - `total_estimated_value`
  - `total_budgeted_cost`
  - `total_revised_value`
- Structure rollups are recalculated for WBS display.

Consultant assessment:

- Good foundation for contract control.
- Report design must respect status semantics. Reports may read all statuses, but transaction cost attribution should be allowed only where the current validation rules allow it.
- Do not build cost reports that silently mix Draft/Pricing estimate rows with Locked contract actuals without a status column and warning.

### 2.2 BOQ Item

Verified files:

- `construction/construction/doctype/boq_item/boq_item.json`
- `construction/construction/doctype/boq_item/boq_item.py`

Current fields include:

- Commercial and quantity fields: `quantity`, `original_qty`, `current_revised_qty`, `contract_unit_price`, `current_revised_unit_price`, `line_total`.
- Cost fields: `est_unit_cost`, `est_unit_price`, `est_line_total`, `overhead_pct`, `profit_pct`, `calculated_sell_price`.
- Control fields: `has_stages`, `quantity_executed`, `quantity_certified`.
- Placeholder field: `cost_item` is currently `Data`, not a structured Link.

Current behavior:

- BOQ Items are allowed only on leaf WBS nodes.
- Frozen/Locked BOQs block direct BOQ Item modification.
- In Pricing status, only selected pricing-related fields can be changed.
- `fetch_cost_item_data()` tries to read `CostItem.total_direct_cost` when `cost_item` is populated, but because `cost_item` is a `Data` field, this is weakly typed and not enterprise-safe.

Consultant assessment:

- `BOQ Item` is ready to be the commercial BOQ leaf.
- It should not become the resource catalog.
- The `cost_item` text placeholder should be deprecated or converted during migration to a formal `BOQ Cost Analysis` relationship.

### 2.3 BOQ Item Stage

Verified files:

- `construction/construction/doctype/boq_item_stage/boq_item_stage.json`
- `construction/construction/doctype/boq_item_stage/boq_item_stage.py`
- `construction/services/boq_operational.py`

Current fields include:

- `boq_item`, `boq_header`, `project`, `boq_structure`
- `stage_code`, `stage_name`, `stage_status`
- `planned_qty`, `measured_executed_qty`, `certified_qty`, `percent_complete`

Current behavior:

- `certified_qty` cannot exceed `measured_executed_qty`.
- Percent complete is constrained to 0-100.
- Frozen/Locked BOQs protect planning fields.
- Certified stages are effectively immutable; adjustment stages are expected.
- `on_doctype_update()` adds uniqueness and indexes for `(boq_item, stage_code)`.

Consultant assessment:

- This is the correct source for physical progress and certification.
- Timesheets, stock entries, purchase invoices, and plant logs must not overwrite QS measurement fields.
- Allowable cost should be derived from `BOQ Item Stage.measured_executed_qty` or `certified_qty`, depending on report purpose.

### 2.4 Transaction Attribution

Verified files:

- `construction/install.py`
- `construction/hooks.py`
- `construction/services/boq_transaction_validation.py`
- `construction/api/boq_link_queries.py`
- `construction/public/js/boq_filters.js`

Current behavior:

- `BOQ Item` is provisioned as an ERPNext Accounting Dimension.
- Eight child tables receive BOQ cascade fields: Purchase Order Item, Purchase Receipt Item, Purchase Invoice Item, Stock Entry Detail, Timesheet Detail, Journal Entry Account, Sales Invoice Item, and Material Request Item.
- Operational cascade fields are:
  - `boq_header`
  - `boq_structure`
  - `boq_item`
  - `boq_item_stage`
  - hidden `boq_selection_scope_type`
- Direct-cost gate behavior exists:
  - Procurement and stock rows use `expense_category == Direct`.
  - Sales Invoice Item uses `is_progress_billing`.
  - Timesheet Detail uses configured direct labor designations.
- Server-side validation enforces:
  - stage requires item
  - incomplete BOQ attribution is rejected
  - selected stage must belong to selected BOQ Item
  - BOQ project must match transaction project where available
  - only allowed BOQ statuses can receive transaction attribution
- Current server-side validation does not yet hard-reject direct-cost gate bypasses for `expense_category`, `is_progress_billing`, or direct labor designation membership. Those gates are currently UI/metadata-driven and need Phase 0 hardening before actual-cost reports are trusted.

Consultant assessment:

- The system already has a serious attribution backbone.
- The report phase should reuse these fields rather than inventing new transaction links.
- A BOQ Attribution Exceptions Report is mandatory because any missing `boq_item` on direct project cost will distort actual cost and margin.
- A server-side direct-cost gate hardening ticket is mandatory before using the attributed rows as financial truth.

### 2.5 Existing Report Query Layer

Verified file: `construction/services/revised_boq_queries.py`

Existing query functions:

- `get_original_boq(boq_header)`
- `get_revised_boq(boq_header)`
- `get_quantity_history(boq_item)`
- `get_vo_impact(boq_header)`
- `get_omitted_items(boq_header)`
- `get_variation_items(boq_header)`

Consultant assessment:

- The current report layer is commercial-quantity focused.
- It does not yet aggregate purchase orders, purchase invoices, stock entries, timesheets, journal entries, or sales invoices.
- A new shared service such as `construction/services/boq_report_data.py` is justified.

### 2.6 Existing Custom Resource Masters

Verified files:

- `construction/construction/doctype/costitem/cost_item.json`
- `construction/construction/doctype/plantresource/plant_resource.json`
- `construction/construction/doctype/direct_labor_designation/direct_labor_designation.json`

Current state:

- `CostItem` has code, category, unit, productivity, wastage, status, and `total_direct_cost`.
- `PlantResource` has resource code, equipment type, ownership hourly cost, operating hourly cost, and mobilization cost.
- `Direct Labor Designation` gates timesheet BOQ requirements by ERPNext Designation. Its default rows are seeded conditionally: the matching ERPNext `Designation` master records must exist before those child rows are appended.

Consultant assessment:

- These are not wrong, but they are not enough for enterprise actual-cost reconciliation.
- Keeping them as final source-of-truth creates double masters: estimators maintain custom resources while procurement/accounting use ERPNext Items.
- Business decision received: `CostItem` and `PlantResource` have no production data and should not remain in the target architecture.
- Recommended path: document the confirmed no-data status, backup, then controlled removal/deprecation of `CostItem` and `PlantResource`; keep labor policy configuration separate from cost/resource identity.

---

## 3. Competitor and ERP Benchmark Conclusions

### 3.1 RIB/CCS Candy Benchmark

Construction estimating systems such as Candy support resource-based estimating and cost-code/group-code summaries. The key lesson is not the exact UI; it is the discipline of linking bill items to resource build-ups and summarizing those resources for cost control.

Implication for this app:

- A BOQ item must have a rate analysis worksheet.
- The worksheet must decompose the BOQ item into material, labor, plant, subcontract, and overhead rows.
- Reports should support both BOQ/WBS views and resource views.

### 3.2 Procore Benchmark

Procore financial workflows emphasize budget-code visibility, committed cost, direct cost, revised budget, and current over/under. This is important because construction teams need to see exposure before invoices arrive.

Implication for this app:

- BOQ reports must separate:
  - Budgeted cost
  - Committed cost from Purchase Orders and subcontract commitments
  - Actual cost from Purchase Invoices, Stock Entries, Timesheets, Journal Entries, and plant logs
  - Unallocated direct cost

### 3.3 Oracle/Enterprise Cost Control Benchmark

Enterprise construction systems separate work breakdown, cost breakdown, commitments, actuals, changes, and forecasts.

Implication for this app:

- `BOQ Structure` remains WBS.
- ERPNext `Item` should become the resource/cost object.
- `BOQ Item` remains the commercial quantity and valuation object.
- Reporting must preserve audit traceability from summary rows back to source documents.

### 3.4 ERPNext Benchmark

ERPNext already supports Items for products and services, Item Prices by UOM and validity, Stock movements, Purchase documents, Sales documents, Projects, Cost Centers, and Accounting Dimensions.

Implication for this app:

- Do not create isolated construction resource masters when ERPNext `Item` can carry the purchasing, stock, service, price, and accounting identity.
- Use custom fields on `Item` for construction-specific attributes.
- Use a custom `Resource Price History` ledger only where ERPNext Item Price is not enough: source document trace, vendor, project/location, effective date, currency, exchange rate, and audit trail.

---

## 4. Target Architecture

```text
[Client/Owner BOQ]
       |
       v
[BOQ Header] -> [BOQ Structure WBS]
       |
       v
[BOQ Item: commercial leaf, quantity, unit, contract rate]
       |
       v
[BOQ Cost Analysis: rate build-up for one BOQ Item]
       |
       v
[BOQ Cost Analysis Detail: ERPNext Item + qty factor + rate + wastage + stream]
       |
       +--> Budget / Allowable Resource Consumption
       |
       +--> Actual Resource Consumption from PO, PI, Stock Entry, Timesheet, Plant Log, JE
```

### 4.1 Standard Cost Streams

Use a consistent stream code in every cost-analysis and actual-cost row:

- `M`: Material
- `L`: Labor
- `P`: Plant/Equipment
- `S`: Subcontract
- `O`: Overhead/Other

This stream should be stored on the resource Item or cost-analysis detail and should be resolvable for actual-cost rows.

### 4.2 ERPNext Item Extensions

Recommended custom fields on standard `Item`:

- `is_construction_resource` Check
- `construction_resource_type` Select: Material, Labor, Plant, Subcontract, Overhead
- `default_cost_stream` Select: M, L, P, S, O
- `default_wastage_pct` Percent
- `default_productivity_qty_per_day` Float
- `default_output_uom` Link UOM
- `plant_ownership_cost_hourly` Currency
- `plant_operating_cost_hourly` Currency
- `plant_mobilization_cost` Currency
- `linked_asset` Link Asset, for company-owned equipment where applicable
- `labor_trade_designation` Link Designation
- `default_purchase_uom` Link UOM, if not already covered by ERPNext UOM rules

Business decisions:

- Company-owned equipment should use ERPNext Asset plus service Item costing.
- Rented or hired equipment can use service Item costing without Asset.
- Company employees and site labor must be separated in cost capture and reporting.
- Subcontractor package allocation and subcontractor item/sub-item measured work must be separated in cost capture and reporting.
- Site/Gang Timesheet minimum fields are labor name, project, BOQ Item, description, UOM, price, and total.
- Subcontractor reports must be separate reports that match the owner certificate structure while showing main-contractor margin.
- Main-contractor margin must support both percentage margin and price-difference margin.
- Subcontractor certificates follow owner certificates exactly, with the administration/main-contractor cut as the key difference.

### 4.3 BOQ Cost Analysis

New parent DocType: `BOQ Cost Analysis`

Recommended fields:

- `project` Link Project
- `boq_header` Link BOQ Header
- `boq_item` Link BOQ Item
- `boq_structure` Link BOQ Structure
- `analysis_status` Select: Draft, Approved, Superseded
- `is_template` Check
- `template_name` Data
- `analysis_uom` Link UOM
- `analysis_qty` Float, default 1
- `total_direct_cost` Currency
- `overhead_pct` Percent
- `profit_pct` Percent
- `total_unit_cost` Currency
- `suggested_sell_rate` Currency
- `effective_date` Date
- `currency` Link Currency

New child table: `BOQ Cost Analysis Detail`

Recommended fields:

- `cost_stream` Select: M, L, P, S, O
- `item_code` Link Item
- `item_name` Data, fetch from Item
- `resource_uom` Link UOM
- `qty_per_boq_unit` Float
- `wastage_pct` Percent
- `cost_rate` Currency
- `rate_source` Select: Manual, Item Price, Last PI, Last PO, Weighted Average, Supplier-Specific, Project-Specific, Resource Price History, Template
- `amount` Currency
- `supplier` Link Supplier
- `remarks` Small Text

Business rule:

- For composite items, use multiple detail rows.
- For single-component BOQ items, still create one cost-analysis detail row with `qty_per_boq_unit = 1`.
- Approved cost analysis rolls up to `BOQ Item.est_unit_cost` and `BOQ Item.est_line_total`.

### 4.4 Resource Price History

New DocType: `Resource Price History`

Purpose:

- Provide an auditable price ledger for volatile markets such as Egypt and Gulf projects with fast-moving material, currency, and subcontract rates.

Recommended fields:

- `item_code` Link Item
- `resource_type` Select
- `price_date` Date
- `rate` Currency
- `currency` Link Currency
- `exchange_rate` Float
- `uom` Link UOM
- `supplier` Link Supplier
- `project` Link Project
- `source_doctype` Data
- `source_name` Dynamic Link
- `source_row` Data
- `company` Link Company

Write-back sources:

- Purchase Invoice Item on submit
- Purchase Order Item on submit/update after submit
- Optional: Stock Entry valuation where the valuation is reliable for the use case

Rate policy:

- Default suggestion hierarchy should be last submitted Purchase Invoice, then last submitted Purchase Order.
- The user must be able to edit the suggested rate before approval.
- The user should be able to select alternate suggestion bases where available, including supplier-specific, project-specific, weighted average, and manually approved catalog rates.

---

## 5. Enterprise Report Set

### 5.1 Project BOQ Executive Overview

Purpose:

- One-page project commercial and cost-control dashboard.

Core columns:

- Project
- BOQ Header
- Contract Value
- Revised Contract Value
- Budgeted Cost
- Committed Cost
- Actual Cost
- Certified Revenue
- Billed Revenue
- Gross Margin Amount
- Gross Margin %
- Unallocated Direct Cost
- CPI: `Earned Value / Actual Cost`
- SPI: `Earned Value / Planned Value`
- EAC and VAC

Hard rule:

- Display unallocated direct cost as a warning line, not as hidden noise.
- Do not treat Sales Invoice billed-revenue values as live until the Phase 4 progress-billing wiring is implemented.

### 5.2 Revised BOQ Report

Current source:

- `construction/services/revised_boq_queries.py`

Recommended columns:

- WBS Code
- BOQ Item
- Description/Title
- Unit
- Original Qty
- Contract Unit Price
- Original Value
- Approved Variation Qty
- Revised Qty
- Revised Unit Price
- Revised Value
- Delta Qty
- Delta Value
- Variation Order reference

Enhancement:

- Add filters for omitted items, variation items, status, WBS node, and owner page/reference.

### 5.3 BOQ Stage Measurement Report

Source:

- `BOQ Item Stage`

Recommended columns:

- Project
- BOQ Header
- WBS Code
- BOQ Item
- Stage Code
- Stage Name
- Planned Qty
- Measured Executed Qty
- Certified Qty
- Percent Complete
- Stage Status
- Remaining to Measure
- Remaining to Certify

### 5.4 BOQ Progress and Billing Report

Purpose:

- Connect physical measurement to client billing.
- Status: blocked until the Phase 4 progress-billing flow wires BOQ Stage/client certification to Sales Invoice creation or reconciliation.

Recommended columns:

- BOQ Item
- Unit
- Revised Qty
- Measured Qty
- Certified Qty
- Billed Qty
- Certified Value
- Billed Value
- Unbilled Certified Value
- Remaining Contract Qty

Source expectation:

- Measured/certified from `BOQ Item Stage`.
- Billed from `Sales Invoice Item` where `is_progress_billing = 1` and BOQ attribution is present.

### 5.5 BOQ Cost Variance: Allowable vs Actual

Purpose:

- The key construction cost-control report.

Recommended columns:

- BOQ Item
- Cost Stream
- ERP Item
- Budget Qty
- Budget Cost
- Executed Qty
- Allowable Qty
- Allowable Cost
- Committed Qty
- Committed Cost
- Actual Qty
- Actual Cost
- Quantity Variance
- Cost Variance
- Rate Variance
- Cost Performance Flag

Calculation principle:

- Allowable Qty = executed BOQ quantity x `qty_per_boq_unit` from approved cost analysis.
- Allowable Cost = allowable qty x approved cost rate.
- Actual comes from ERPNext transaction rows carrying `boq_item` and `item_code`.

### 5.6 BOQ Attribution Exceptions Report

Purpose:

- Protect report credibility.

Exceptions:

- Direct cost row with project but no `boq_item`.
- Row has `boq_item_stage` but no `boq_item`.
- Row BOQ project differs from parent project.
- Row BOQ Header status not allowed for transaction attribution.
- Row has `boq_header` or `boq_structure` but no `boq_item`.
- Actual row item code cannot map to construction resource type.
- Cost-analysis resource has no active ERPNext Item.

### 5.7 Resource Price Movement Report

Purpose:

- Egypt/Gulf price volatility control.

Recommended columns:

- ERP Item
- Resource Type
- UOM
- Supplier
- Last Rate
- Previous Rate
- Rate Change %
- Last Source Document
- Last Purchase Date
- Project/Company
- Currency

### 5.8 Forecast and Margin Report

Purpose:

- Forecast project profit before final account.

Recommended columns:

- Revised Contract Value
- Budgeted Cost
- Committed Cost
- Actual Cost
- Cost to Complete
- Forecast Cost at Completion
- Forecast Margin
- Margin %
- Risk Allowance
- Unallocated Cost Deduction

---

## 6. Shared Report Data Service

Create: `construction/services/boq_report_data.py`

Recommended functions:

- `get_boq_scope(filters)`
- `get_revised_boq_rows(filters)`
- `get_stage_progress(filters)`
- `get_cost_analysis_rows(filters)`
- `get_committed_cost_rows(filters)`
- `get_actual_cost_rows(filters)`
- `get_sales_billing_rows(filters)`
- `get_unallocated_direct_cost_rows(filters)`
- `calculate_allowable_cost(filters)`
- `calculate_evm_metrics(rows)`
- `build_attribution_exceptions(filters)`

Implementation notes:

- Use SQL for high-volume aggregation.
- Keep source-document drill-down fields in every row.
- Do not duplicate report math inside individual report scripts.
- Add indexes after confirming the final query shapes.

---

## 7. Implementation Roadmap

### Phase 0: Verification and Data Policy

Required before coding:

- Confirm whether `BOQ Item` remains an Accounting Dimension at an expected project scale of about 1,000 BOQ Items.
- Document confirmed no-data status and backup before removing/deprecating `CostItem` and `PlantResource`.
- Use confirmed Site/Gang Timesheet fields: labor name, project, BOQ Item, description, UOM, price, and total.
- Use separate subcontractor reports that match owner certificate structure and expose main-contractor margin/admin cut.
- Add server-side direct-cost gate hardening for `expense_category`, `is_progress_billing`, and direct labor designation membership.
- Decide whether to seed the 11 default ERPNext `Designation` masters needed for full Direct Labor Designation setup, or document conditional setup behavior.
- Replace hard-coded social-insurance law/rate assumptions with configurable rules subject to current law and advisor confirmation.
- Attach reproducible evidence artifacts for no-data checks, field citations, and the 1,000 BOQ Item benchmark.

### Phase 1: Unified Item Mapping

Deliverables:

- Add construction custom fields to ERPNext `Item`.
- Remove/deprecate empty `CostItem` and `PlantResource` scaffolds through a controlled patch.
- Add resource type validation.
- Add setup report showing construction resources represented as ERPNext Items and company-owned plant linked to ERPNext Assets.

### Phase 2: Price Ledger

Deliverables:

- Create `Resource Price History`.
- Write hooks for PO/PI price capture.
- Build suggested-rate API.
- Add price movement report.

### Phase 3: BOQ Cost Analysis

Deliverables:

- Create `BOQ Cost Analysis` and detail child table.
- Implement approval workflow.
- Roll up approved analysis into `BOQ Item.est_unit_cost`.
- Add template library and bulk rate refresh.

### Phase 4: Cost Capture Extensions

Deliverables:

- Implement employee company timesheet flow for salaried employees with HR, salary, and insurance context.
- Implement Site/Gang Timesheet for daily, weekly, or monthly site labor with labor name, project, BOQ Item, description, UOM, price, and total.
- Implement Plant Timesheet against ERPNext Item and ERPNext Asset for company-owned equipment.
- Implement separate subcontractor package allocation reports for work split across villas/areas/packages, matching owner certificate structure.
- Implement subcontractor item/sub-item measured work reports for concrete by m3, pouring-only, pump-only, and similar packages.
- Implement Subcontractor Payment Certificate that follows owner certificates exactly, applies administration/main-contractor cut, and supports Purchase Invoice generation/reconciliation after approval.

### Phase 5: Reporting Engine

Deliverables:

- Create `boq_report_data.py`.
- Implement the report set listed in Section 5.
- Add tests for calculations and exception detection.
- Add performance tests on realistic project volume.

---

## 8. Risks and Controls

| Risk | Impact | Control |
|---|---:|---|
| BOQ Item as Accounting Dimension becomes too high-cardinality | Slow GL and report queries | Benchmark with realistic BOQ size; add indexes; consider analytical link fields for non-GL detail if needed |
| Disconnected resource masters remain in use | Budget vs actual mismatch | Remove/deprecate empty CostItem and PlantResource scaffolds; use ERPNext Item as the resource master |
| Direct-cost gates remain UI-only | Client bypass can poison actual-cost reports | Add server-side validation and bypass tests before reporting |
| Billed-revenue report is enabled before progress billing is wired | False revenue/progress reporting | Mark report blocked until Sales Invoice progress-billing flow exists |
| Social-insurance/tax rates are hard-coded from outdated assumptions | Legal and payroll compliance risk | Use configurable rules with advisor confirmation |
| Actual costs missing BOQ attribution | False margin | Mandatory exceptions report and direct-cost gates |
| Price history polluted by unusual purchases | Bad suggested rates | Add rate-source hierarchy, outlier flag, and manual approval |
| QS progress mixed with cost logs | Invalid earned value | Keep BOQ Stage as only physical progress source |
| Subcontract certification duplicated with Purchase Invoice | Double cost | SPC must create or reconcile PI, not coexist unmanaged |

---

## 9. Immediate Engineering Actions

1. Replace the current future-state wording with this verified state and roadmap.
2. Create a technical design ticket for `BOQ Cost Analysis` and `BOQ Cost Analysis Detail`.
3. Create a controlled removal/deprecation ticket for empty `CostItem` and `PlantResource` scaffolds.
4. Create a proof-of-concept query for actual cost aggregation using existing transaction child `boq_item` fields.
5. Add a benchmark task for BOQ Item Accounting Dimension performance on about 1,000 BOQ Items.
6. Add server-side direct-cost gate hardening tests.
7. Add progress-billing wiring decision before enabling billed-revenue columns.
8. Add current social-insurance/tax configuration decision with advisor sign-off.

---

## 10. Sources Used for Benchmarking

- RIB/CCS Candy forecasting and resource/cost-code control: `https://constructioncomputersoftware.com/home/products/candy/candy-features/forecasting/`
- RIB CostX BOQ and estimating workflow reference: `https://www.rib-software.com/en/rib-costx`
- Procore budget/direct cost and committed cost references: `https://v2.support.procore.com/faq-which-budget-views-should-i-add-to-my-projects`, `https://www.procore.com/project-financials/direct-costs`, `https://www.procore.com/library/committed-costs`
- ERPNext Item, Item Price, Stock, and Accounting Dimension references: `https://docs.frappe.io/erpnext/item`, `https://docs.frappe.io/erpnext/item-price`, `https://docs.frappe.io/erpnext/stock`, `https://docs.frappe.io/erpnext/accounting-dimensions`
