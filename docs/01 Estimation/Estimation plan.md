# Phase 1: End-to-End BOQ Cost Estimation Engine

## 1. Summary

Build only the estimation backbone now. Do **not** implement owner progressive billing, subcontractor certificates, actual site labor/plant/material cost, allowable-vs-actual variance, or site execution workflows in this phase.

The completed Phase 1 flow will be:

```text
ERPNext Item resource master
-> Resource Price History / suggested rate
-> BOQ Cost Analysis
-> BOQ Cost Analysis Detail
-> Approved unit cost rollup
-> BOQ Item.est_unit_cost / est_line_total
-> BOQ Header budget totals
-> Estimation reports
```

Primary goal: Every BOQ Item has a defensible unit-rate build-up using ERPNext Items, with manual override and PI-then-PO suggested rates.

---

## 2. Key Changes & DocType Definitions

### 2.1 ERPNext Item Custom Fields
Add the following fields to standard `Item` via a custom field schema:
* `is_construction_resource` (Check)
* `construction_resource_type` (Select: Material, Labor, Plant, Subcontract, Overhead)
* `default_cost_stream` (Select: M, L, P, S, O)
* `default_wastage_pct` (Percent, default 0.0)
* `default_productivity_qty_per_day` (Float, default 0.0)
* `default_output_uom` (Link → UOM)
* `plant_ownership_cost_hourly` (Currency)
* `plant_operating_cost_hourly` (Currency)
* `plant_mobilization_cost` (Currency)
* `labor_trade_designation` (Link → Designation)
* `linked_asset` (Link → Asset, for company-owned plant)

### 2.2 Resource Price History DocType
Create an auditable price ledger for historical transactions to handle price volatility.
* `item_code` (Link → Item, required, search_index)
* `resource_type` (Select: Material, Labor, Plant, Subcontract, Overhead)
* `price_date` (Date, required)
* `rate` (Currency, required)
* `currency` (Link → Currency, required)
* `exchange_rate` (Float, default 1.0)
* `uom` (Link → UOM, required)
* `supplier` (Link → Supplier)
* `project` (Link → Project)
* `company` (Link → Company, required)
* `source_doctype` (Data, e.g., "Purchase Invoice", "Purchase Order")
* `source_name` (Data, name of source document)
* `source_row` (Data, row ID of source document)

### 2.3 BOQ Cost Analysis & Detail DocTypes
Create a worksheet to decompose a BOQ Item rate into component costs.
* **BOQ Cost Analysis (Parent):**
  * `project` (Link → Project, required)
  * `boq_header` (Link → BOQ Header, required)
  * `boq_structure` (Link → BOQ Structure, required)
  * `boq_item` (Link → BOQ Item, required, unique)
  * `analysis_status` (Select: Draft, Approved, Superseded, default "Draft")
  * `analysis_uom` (Link → UOM, fetched from BOQ Item)
  * `total_direct_cost` (Currency, read_only, sum of details)
  * `overhead_pct` (Percent, default 0.0)
  * `profit_pct` (Percent, default 0.0)
  * `total_unit_cost` (Currency, read_only, total direct + overhead + profit)
  * `suggested_sell_rate` (Currency, read_only)
  * `effective_date` (Date, required)
  * `company` (Link → Company)
* **BOQ Cost Analysis Detail (Child Table):**
  * `cost_stream` (Select: M, L, P, S, O, required)
  * `item_code` (Link → Item, required)
  * `item_name` (Data, read-only)
  * `resource_uom` (Link → UOM, required)
  * `qty_per_boq_unit` (Float, default 1.0, required)
  * `wastage_pct` (Percent, default 0.0)
  * `cost_rate` (Currency, required)
  * `rate_source` (Select: Manual, Last PI, Last PO, Weighted Average, Supplier-Specific, Project-Specific, Price History, default "Manual")
  * `amount` (Currency, read_only, formula: `qty_per_boq_unit * cost_rate * (1 + wastage_pct / 100)`)
  * `supplier` (Link → Supplier)

---

## 3. Deprecation and Cleanup of Legacy Code
To prevent runtime execution errors during Phase 1:
1. **Refactor `boq_item.py`:**
   * Remove `fetch_cost_item_data` from the `PHASE1_STEPS` validation pipeline.
   * Deprecate the `cost_item` field from `PRICING_EDITABLE` and mark the field as hidden/deprecated in `boq_item.json`.
   * Update the rollup logic to fetch the rate from the approved `BOQ Cost Analysis` record. If no analysis is approved, default `est_unit_cost` to `0`.
2. **Controlled Scaffolding Drop:**
   * Remove/deprecate `CostItem` and `PlantResource` DocTypes. Ensure the patch runs only after `boq_item.py` has been updated and verified.

---

## 4. Lifecycle Validation and Gating rules

### 4.1 BOQ Header Status Integration
* **Creation/Approval Limits:** `BOQ Cost Analysis` records can only be created, modified, or approved if the parent `BOQ Header` is in `Draft` or `Pricing` status.
* **Freeze/Lock Policy:** Once the `BOQ Header` transitions to `Frozen` or `Locked`, editing or approving any linked `BOQ Cost Analysis` is strictly blocked.
* **Programmatic Bypass:** When a `BOQ Cost Analysis` is approved, it updates `est_unit_cost` and `est_line_total` on the target `BOQ Item`. The `BOQ Item` controller must permit this update programmatically even if the BOQ Header status is in `Pricing` status (which normally restricts manual user edits).

### 4.2 Suggested Rate API Hierarchy
The suggested-rate endpoint must query the `Resource Price History` table in the following fallback order:
1. Last submitted `Purchase Invoice` for the same `item_code`, `project`, and `uom`.
2. Last submitted `Purchase Invoice` for the same `item_code` and `uom` across the `company`.
3. Last submitted `Purchase Order` for the same `item_code` and `uom`.
4. Fallback to standard ERPNext `Item Price` if no transaction history exists.
*The API must support multi-currency conversion, defaulting to the Company primary currency using exchange rates recorded at the transaction date.*

---

## 5. Estimation Report Set

Implement the following standard Frappe Script Reports querying the new analysis and history schemas:
1. **BOQ Cost Analysis Summary:** Displays approved rate build-ups showing component-wise totals (M, L, P, S, O) per BOQ Item.
2. **BOQ Item Estimated Cost vs Contract Rate:** Variance report comparing `est_unit_cost` against `contract_unit_price` to highlight projected line-item margins.
3. **Resource Requirement Summary:** Aggregates quantities and amounts of all resource `Items` across the project, filtered by cost stream (M, L, P, S, O).
4. **Resource Price History / Rate Movement:** Tracks purchasing rates over time, showing price volatility for materials and services.
5. **BOQ Items Missing Approved Cost Analysis:** Exception report showing all leaf BOQ Items that have no approved rate analysis.

---

## 6. Test and Verification Plan

* **Verification 1:** Verify custom `Item` fields install idempotently on fresh site creation and migrations.
* **Verification 2:** Verify that the price history suggested rate API successfully implements the fallback chain.
* **Verification 3:** Test that approving a `BOQ Cost Analysis` correctly recalculates the parent `BOQ Item.est_unit_cost` and triggers the `BOQ Header` rollup calculations.
* **Verification 4:** Verify that trying to save/approve a `BOQ Cost Analysis` throws a validation error when the `BOQ Header` is `Frozen` or `Locked`.
* **Verification 5:** Verify that `CostItem` and `PlantResource` removal patch executes without breaking `BOQ Item` validation or form rendering.
* **Verification 6:** Run a query performance test with ~1,000 BOQ Items to verify rollup calculations complete within acceptable limits (p95 < 2s).
