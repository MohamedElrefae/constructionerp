# Enterprise BOQ Reports & Accounting Integration Plan (Revised)

This revised plan outlines the strategic roadmap for transforming the Bill of Quantities (BOQ) from a data structure into the commercial control center of the construction business, while **carefully accounting for the extensive features already developed**.

## Current Implementation State (Baseline)
A review of the current implementation reveals that foundational data structures are **already in place**:
- **`boq_header`**: Already tracks `total_contract_value`, `total_estimated_value`, `total_budgeted_cost`, and dynamically calculates `total_revised_value`.
- **`boq_item`**: Already houses `original_qty`, `current_revised_qty`, `current_revised_unit_price`, and crucially, hidden fields for `quantity_executed` and `quantity_certified`.
- **`boq_item_stage`**: Already captures `planned_qty`, `measured_executed_qty`, `certified_qty`, and `percent_complete`.
- **`variation_order` & `vo_line`**: Fully implemented to manage contract deltas and variation tracking.

Given this robust foundation, the plan is accelerated. We do not need to build the data capture for progressive billing from scratch; we need to unhide/expose it, build the reports on top of it, and wire it to ERPNext accounting modules.

## Recommended Enterprise Execution Order
1. **BOQ Reports Foundation** (using existing models)
2. **Core BOQ Reports** (deploying Frappe standard/script reports utilizing existing BOQ data)
3. **Accounting Integration & Billing Bridge** (connecting existing certified quantities to Sales Invoices and GL)
4. **Advanced Financial Reports** (incorporating ERPNext GL actuals and billing data)
5. **Construction Profitability Report**

---

## Plan 1: BOQ Reports Enterprise Plan

**Objective:** Turn the existing BOQ data model into an executive project-control reporting layer.

### Phase 1: Reporting Foundation & Exposing Existing Fields
**Scope:**
- Unhide and validate the existing `quantity_executed` and `quantity_certified` fields in `boq_item` and UI layouts where applicable.
- Define shared BOQ report filters (Company, Project, BOQ, Revision, WBS, Stage, Date Range, Scope Type).
- Implement standard Frappe report permissions (by role: Project Manager, QS, Accountant, etc.).
- Ensure all Frappe reports have standard Arabic/English translations and export capabilities.

### Phase 2: Core BOQ Reports (Ready for Immediate Build)
*Because the data models exist, these reports can be built immediately.*

**1. Revised BOQ Report**
- **Purpose:** Show contract BOQ versus revised BOQ.
- **Source Data:** Pull directly from existing `boq_item` fields: `original_qty`, `contract_unit_price`, `current_revised_qty`, `current_revised_unit_price`. Join with `variation_order` for tracking deltas.

**2. BOQ Stage Measurement Report**
- **Purpose:** Show stage-level measurement and progress.
- **Source Data:** Pull from existing `boq_item_stage` fields: `planned_qty`, `measured_executed_qty`, `certified_qty`, and `percent_complete`.

**3. BOQ Progress Report**
- **Purpose:** Executive view of planned vs. executed vs. certified progress.
- **Source Data:** Aggregate existing `boq_item` fields (`quantity_executed`, `quantity_certified`) against `original_qty` / `current_revised_qty`. 
- **Next Step:** Add `billed_qty` and `billing_readiness` status once Phase 3 (Accounting) is complete.

### Phase 3: Reports That Need Accounting Integration
*To be designed now, but finalized after closing the GL loop.*

**4. BOQ Cost Variance Report**
- **Depends on:** Readback of Actual Cost from Purchase Invoices, Stock Entries, and Journal Entries linked to BOQ Items.
- **Goal:** Compare existing `total_budgeted_cost` vs. actual GL committed/incurred costs.

**5. Construction Profitability Report**
- **Depends on:** Progressive billing (Sales Invoices) and GL readback.
- **Goal:** Compare Revised Contract Value against Billed Revenue, Actual Cost, and Gross Margin.
> [!IMPORTANT]  
> We will build a uniquely BOQ-aware Custom Report for profitability, deliberately bypassing standard ERPNext Project-wise Profitability to avoid GL-only misrepresentations.

---

## Plan 2: BOQ Accounting Integration Enterprise Plan

**Objective:** Wire the existing BOQ data structure to ERPNext procurement, sales, and accounting modules.

### Phase 1: Accounting Data Model Decisions
**Open Questions to Resolve:**
- Do we store `boq_header` and `boq_item` as standard Accounting Dimensions, or stick to child table references on core transaction doctypes?
- How do we handle partial cost allocations (e.g., a bulk material purchase spanning multiple BOQ Items)?
- Do we lock down `quantity_certified` to be strictly updated via a dedicated 'Payment Certificate' Doctype, or allow manual override based on role?

### Phase 2: Procurement and Cost Attribution
**Scope:**
- Modify ERPNext procurement documents (Material Request, Purchase Order, Purchase Receipt, Purchase Invoice, Stock Entry) to carry `boq_header`, `boq_item`, and `boq_structure` links.
- Read committed cost from Purchase Orders directly into BOQ Item actuals/tracking.

### Phase 3: Progressive Billing Integration (The Bridge)
*Leveraging our existing data model to generate revenue.*

**Scope:**
- Create the final flow: `boq_item_stage.certified_qty` → **Billing Readiness Flag** → **Sales Invoice**.
- Create a mechanism (e.g., a button "Create Progress Invoice") that reads the existing `certified_qty` from BOQ Items and auto-populates a Sales Invoice.
- Write back to a new `billed_qty` field on `boq_item` once the Sales Invoice is submitted.
- Enforce validations to prevent billing beyond `current_revised_qty` or `certified_qty` (overbilling controls).

### Phase 4: GL Readback and Reconciliation
**Scope:**
- Query GL Entries filtering by BOQ context to summarize actual cost and revenue.
- Create an "Exceptions Report" to catch costs assigned to a Project without a mapped BOQ Item.

### Phase 5: Profitability and Executive Reporting
**Scope:**
- Finalize the Construction Profitability Report to ensure numbers perfectly reconcile with the BOQ baseline and the ERPNext General Ledger.

---

## User Review Required

**Approval Gates**
Please review this revised plan which acknowledges our current mature data models (`boq_item`, `boq_item_stage`, `total_revised_value`). Do you approve this revised direction?

> [!NOTE]  
> Once approved, we will begin the technical implementation of **Phase 1: Reporting Foundation & Exposing Existing Fields** immediately.
