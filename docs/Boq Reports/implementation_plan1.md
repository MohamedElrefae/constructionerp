# Head of Engineering Revision: Enterprise BOQ Reports (Revised Plan)

This plan integrates the user's strategic feedback into the BOQ Reports and Accounting integration roadmap:
1. **Actual Cost-First Approach**: Build and deploy the cost-collection transactions (Plant Log, Subcontractor Certificates, Classification Service) *before* building the reports, ensuring data is populated.
2. **Separate Plant/Machine Logs**: Create a separate `Plant Timesheet` to log equipment dry/wet hours, keeping it distinct from human timesheets.
3. **Subcontractor Payment Certificates**: Implement a custom DocType to track subcontractor progress, retention, and back-charges, which then maps to standard accounting.
4. **Consistent Owner Billing**: Maintain standard `Sales Invoice` with custom progress billing fields for client-side invoicing, avoiding any architectural changes to the client revenue loop.
5. **No Mutation of Original Review**: Create a new file [HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md](file:///home/mohamed/frappe-bench/apps/construction/docs/Boq%20Reports/HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md) to keep the original report intact.

## User Review Required

> [!IMPORTANT]
> **Key Architecture Decisions Approved:**
> 1. **Equipment vs. Labor separation**: Machines will be logged hourly/daily on a dedicated `Plant Timesheet` rather than employee timesheets, linking to `PlantResource` for cost rates (`ownership_cost_hourly`, `operating_cost_hourly`).
> 2. **Subcontractor Claim Flow**: A `Subcontractor Payment Certificate` DocType will be introduced. It calculates Certified Work, Retentions, Advance Recoveries, and Back-charges, and automatically generates a standard ERPNext `Purchase Invoice` upon submission to book the liability.
> 3. **Owner Billing Flow**: No new DocType for owner billing. The existing `Sales Invoice` with `is_progress_billing = 1` remains the single point of revenue billing.
> 4. **Sequence**: Cost capture components will be developed and deployed first, followed by script reports.

---

## Technical Design of Construction-Specific Cost Objects

To align with Gulf ERP standards (like Candy/CCS, RIB iTWO, and NetSuite), we will introduce two new DocTypes and a shared cost classification service.

### 1. Plant Timesheet (Equipment Log)
A new DocType `Plant Timesheet` will log machine hours separately from employees.

*   **Header Fields**:
    *   `project` (Link -> Project)
    *   `posting_date` (Date)
    *   `operator` (Link -> Employee, optional)
*   **Child Table Fields (Plant Timesheet Detail)**:
    *   `plant_resource` (Link -> PlantResource)
    *   `boq_header` (Link -> BOQ Header)
    *   `boq_structure` (Link -> BOQ Structure)
    *   `boq_item` (Link -> BOQ Item)
    *   `boq_item_stage` (Link -> BOQ Item Stage)
    *   `hours` (Float)
    *   `rate_type` (Select -> Dry, Wet)
    *   `costing_rate` (Currency - fetched from `PlantResource` ownership/operating rates)
    *   `amount` (Currency - `hours * costing_rate`)

### 2. Subcontractor Payment Certificate (SPC)
A custom DocType to certify subcontractor works.

*   **Header Fields**:
    *   `project` (Link -> Project)
    *   `supplier` (Link -> Supplier - gated to Subcontractors)
    *   `purchase_order` (Link -> Purchase Order - Subcontract Agreement)
    *   `certificate_date` (Date)
    *   `valuation_date` (Date)
    *   `retention_pct` (Percent - default from PO)
*   **Child Table (SPC Detail)**:
    *   `boq_header`, `boq_structure`, `boq_item`, `boq_item_stage`
    *   `unit` (Link -> UOM)
    *   `contract_qty`, `contract_rate`
    *   `total_qty_to_date` (QS-measured subcontractor quantity)
    *   `certified_qty_to_date` (Certified subcontractor quantity)
    *   `gross_value_to_date` (`certified_qty_to_date * contract_rate`)
    *   `previous_gross_value` (Calculated from previous certificates)
    *   `net_certified_value` (`gross_value_to_date - previous_gross_value`)
*   **Summary & Deductions**:
    *   `gross_value` (Sum of `net_certified_value`)
    *   `retention_withheld` (`gross_value * retention_pct`)
    *   `advance_recovery` (Currency)
    *   `back_charges` (Currency - from material/plant issued to sub)
    *   `net_payable` (`gross_value - retention_withheld - advance_recovery - back_charges`)
*   **Automation on Submit**:
    *   Generates a standard `Purchase Invoice` with a row for `gross_value`, a debit/credit row for back-charges, and a retention liability allocation.

### 3. Dynamic Cost Classification Service
A python module `construction/services/cost_classification.py` to classify transaction lines:

*   **Labour (L)**: Attributed from `Timesheet Detail` where designation is marked direct labor.
*   **Material (M)**: Attributed from `Purchase Invoice Item` and `Stock Entry Detail` where item's Item Group is material-based.
*   **Plant/Equipment (P)**: Attributed from new `Plant Timesheet Detail`, or PI items with equipment category.
*   **Subcontractor (S)**: Attributed from `Subcontractor Payment Certificate` (Purchase Invoice link) or Supplier Group is "Subcontractor".
*   **Overhead (O)**: Default category for JEs or other indirect expense lines.

---

## Proposed Changes

We will create a new revised review report and define the shared python aggregation code.

### 1. Create Revised HOE Review Report
#### [NEW] [HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md](file:///home/mohamed/frappe-bench/apps/construction/docs/Boq%20Reports/HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md)
We will create this new document inside the docs repository. It leaves the original document untouched and contains the finalized Head of Engineering review, including:
- Concrete codebase validations.
- Explicit comparisons with NetSuite, Candy/CCS, and RIB iTWO cost objects.
- Specifications for the 5 Cost Streams (L-M-P-S-O).
- Detailed report outlines with EVM metrics.
- The updated implementation order (cost-capture first, reports second).

### 2. Implement Aggregation Service (Stub)
#### [NEW] [boq_report_data.py](file:///home/mohamed/frappe-bench/apps/construction/construction/services/boq_report_data.py)
We will implement the initial data aggregation structures supporting the reports.

---

## Verification Plan

### Automated Tests
- `test_plant_timesheet_costs()`: Verify hours * rate calculations for dry/wet equipment logs.
- `test_subcontractor_certificate_invoice()`: Verify that SPC submission creates a valid `Purchase Invoice` with proper retention and back-charge deductions.
- `test_cost_classification()`: Verify that transactions map correctly to L-M-P-S-O buckets.

### Manual Verification
- Verify the new file `HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md` is present in `/home/mohamed/frappe-bench/apps/construction/docs/Boq Reports/`.
