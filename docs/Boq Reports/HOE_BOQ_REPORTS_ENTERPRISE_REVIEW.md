# Head of Engineering Review Report: Enterprise BOQ Reports

Date: 2026-06-25

Prepared for: Head of Engineering Department

Prepared by: Codex, acting as software consultant for ERP construction planning and implementation

Repository: `/home/mohamed/frappe-bench/apps/construction`

Primary request: Review the current BOQ report proposal, inspect the implemented BOQ/accounting integration code, and prepare an approval-ready plan for enterprise BOQ reports that give project teams and project managers meaningful project overview, BOQ progress, cost, revenue, and profitability insight.

---

## 1. Executive Summary

The current Construction app already has a strong BOQ foundation. The BOQ model is not just a document list; it includes BOQ Header, BOQ Structure, BOQ Item, BOQ Item Stage, Variation Order, quantity revision support, and transaction attribution into ERPNext documents.

The attached report, `basic boq reports .md`, is directionally correct: the system is ready for a BOQ reporting layer. However, the actual code review shows an important engineering boundary:

- The system validates BOQ attribution on ERPNext transaction rows.
- The system does not yet aggregate committed cost, actual cost, revenue, billed quantities, or profitability into dedicated BOQ reports.
- The system has stage measurement fields, but it intentionally does not let Timesheet, Stock Entry, or Purchase Invoice automatically overwrite executed or certified progress.

Recommendation: approve an Enterprise Core BOQ Reports release before implementing progress invoicing. This release should build reliable reporting services and Script Reports first, while preserving the existing source-of-truth model.

---

## 2. Review Scope

### Documents Reviewed

- `/home/mohamed/frappe-bench/apps/construction/docs/Boq Reports/basic boq reports .md`
- `/home/mohamed/frappe-bench/apps/construction/docs/02BOQ Integratiom/boq_integration_requirements.md`
- `/home/mohamed/frappe-bench/apps/construction/docs/03 ACCOUNTING INTEGRATAION/ERPNext_Accounting_BOQ_Learning_Roadmap.md`
- `/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/00_feature_review_index.md`

### Code Areas Reviewed

- BOQ DocTypes:
  - `BOQ Header`
  - `BOQ Structure`
  - `BOQ Item`
  - `BOQ Item Stage`
  - `Variation Order`
  - `VO Line`
  - `BOQ Quantity Revision`
- BOQ services:
  - `boq_accounting.py`
  - `boq_transaction_validation.py`
  - `boq_scope_registry.py`
  - `boq_operational.py`
  - `variation_orders.py`
  - `quantity_revisions.py`
- Setup and hooks:
  - `construction/install.py`
  - `construction/hooks.py`
  - `construction/public/js/boq_filters.js`
- Existing tests:
  - `test_transaction_validation.py`
  - related BOQ/stage/variation tests found in the app test suite

---

## 3. Work Performed During This Review

### 3.1 Repository and Document Discovery

I inspected the `docs` folder and confirmed that the repository contains separate BOQ integration, accounting integration, feature review, evidence, and handover documents. The BOQ report document provided by the owner is currently a planning document, not an implemented report module.

### 3.2 Current Report Implementation Check

I searched the app for implemented report modules. Result:

- No dedicated BOQ Script Report package currently exists.
- The app has a BOQ print format.
- The app has scope report enforcement utilities.
- The app does not yet have the enterprise BOQ reports described in the attached plan.

This means the next implementation should create a new reporting layer rather than modify existing BOQ report code.

### 3.3 BOQ Data Model Verification

Verified from DocType JSON and controller code:

- `BOQ Header` has rollup totals:
  - `total_contract_value`
  - `total_estimated_value`
  - `total_budgeted_cost`
  - `total_revised_value`
- `BOQ Item` has pricing and revision fields:
  - `quantity`
  - `original_qty`
  - `current_revised_qty`
  - `current_revised_unit_price`
  - `contract_unit_price`
  - `line_total`
  - `est_unit_cost`
  - `est_line_total`
- `BOQ Item` also has hidden/read-only future control fields:
  - `quantity_executed`
  - `quantity_certified`
- `BOQ Item Stage` has operational progress fields:
  - `planned_qty`
  - `measured_executed_qty`
  - `certified_qty`
  - `percent_complete`
- `Variation Order` and `VO Line` support approved contract deltas.

### 3.4 Transaction Attribution Verification

Verified that BOQ attribution is already added and validated for these ERPNext documents:

- Material Request
- Purchase Order
- Purchase Receipt
- Purchase Invoice
- Stock Entry
- Timesheet
- Journal Entry
- Sales Invoice

The child row fields include:

- `boq_header`
- `boq_structure`
- `boq_item`
- `boq_item_stage`
- `boq_selection_scope_type`
- `expense_category` on cost-side doctypes where applicable
- `is_progress_billing` on Sales Invoice Item

### 3.5 Labour, Material, Equipment, Subcontractor, and Expense Review

The owner specifically raised concern that all expense streams must affect both BOQ and Project reporting:

- Labour / Timesheet
- Equipment
- Subcontractors
- Expenses
- Materials

Current implementation coverage:

- Materials are covered through Material Request, PO, PR, PI, and Stock Entry attribution.
- Labour is covered through Timesheet Detail with direct-labour designation gating.
- Equipment can be captured through PI, Stock Entry, and JE attribution, but no dedicated equipment report classification service exists yet.
- Subcontractors can be captured through PO, PI, and JE attribution, but no dedicated subcontractor classification service exists yet.
- Expenses are partially covered through PI and JE. Expense Claim is not currently present in this local bench because only `construction`, `erpnext`, and `frappe` apps are installed. HRMS is not installed.

Recommendation: include Expense Claim support conditionally. If Expense Claim DocTypes exist in a deployment, add BOQ attribution to `Expense Claim Detail`. If not, continue using Journal Entry and Purchase Invoice as the fallback expense path.

---

## 4. Engineering Findings

### Finding 1: BOQ report data foundation exists

The app already has the important BOQ commercial structure: original contract quantities, revised quantities, stage measurements, approved variation impact, and BOQ-linked ERPNext transactions.

Impact: The reports can be built without replacing the BOQ model.

### Finding 2: Report modules do not exist yet

There are no dedicated BOQ Script Reports currently implemented.

Impact: Implementation should create new report modules and shared aggregation services.

### Finding 3: Transaction validation is link validation, not cost aggregation

Current server-side validation checks that BOQ Item, BOQ Header, BOQ Structure, Stage, and Project relationships are valid. It does not calculate actual cost or committed cost.

Impact: Cost and profitability reports need a reporting service that reads ERPNext transaction rows and GL Entries.

### Finding 4: Stage progress is intentionally protected

The existing design blocks automatic overwriting of `measured_executed_qty` and `certified_qty` from Stock Entry or Timesheet without an approved source-of-truth policy.

Impact: Reports should read BOQ Item Stage progress as the operational measurement truth. They should not mutate progress quantities.

### Finding 5: Expense Claim needs conditional handling

Expense Claim is not available in this local bench, but it is a common enterprise requirement for site expenses, petty cash, travel, and reimbursables.

Impact: Add conditional setup only when Expense Claim DocTypes exist. Do not make the construction app fail on benches without HRMS.

---

## 5. Recommended Enterprise Core Report Set

### 5.1 Project BOQ Overview

Purpose: Give project managers a single overview of commercial status by project and BOQ.

Key metrics:

- Contract value
- Revised value
- Budgeted cost
- Measured value
- Certified value
- Billed revenue
- Actual cost
- Committed cost
- Gross margin
- Missing BOQ attribution count

### 5.2 Revised BOQ Report

Purpose: Show original contract BOQ versus approved revised BOQ.

Data sources:

- `BOQ Item`
- `BOQ Structure`
- approved `Variation Order`
- `VO Line`
- `BOQ Quantity Revision`

Columns:

- WBS code
- BOQ item
- Original quantity
- Original unit rate
- Original value
- Approved variation quantity
- Revised quantity
- Revised unit rate
- Revised value
- Delta value

### 5.3 BOQ Stage Measurement Report

Purpose: Show stage-level progress for QS, project manager, and site team.

Data sources:

- `BOQ Item Stage`
- `BOQ Item`
- `BOQ Header`
- `BOQ Structure`

Columns:

- Project
- BOQ Header
- WBS
- BOQ Item
- Stage code
- Stage name
- Planned quantity
- Measured executed quantity
- Certified quantity
- Percent complete
- Stage status

### 5.4 BOQ Progress Report

Purpose: Aggregate planned, measured, certified, and remaining progress by BOQ item and structure.

Key calculations:

- Planned quantity from stage totals
- Measured quantity from stage totals
- Certified quantity from stage totals
- Remaining to measure
- Remaining to certify
- Measured value
- Certified value

### 5.5 BOQ Cost Variance Report

Purpose: Compare BOQ budget/revised value against committed and actual project cost.

Cost streams:

- Materials
- Labour / Timesheet
- Equipment
- Subcontractors
- Expenses

Data sources:

- Material Request Item
- Purchase Order Item
- Purchase Receipt Item
- Purchase Invoice Item
- Stock Entry Detail
- Timesheet Detail
- Journal Entry Account
- Expense Claim Detail, if installed

### 5.6 BOQ Attribution Exceptions Report

Purpose: Find project costs or revenue that will make reports misleading because they are missing BOQ attribution.

Exception examples:

- Project transaction row has no `boq_item`
- `boq_item_stage` is set without valid `boq_item`
- BOQ Item belongs to another project
- BOQ Header status does not allow transaction attribution
- Sales Invoice Item is marked progress billing but missing BOQ attribution
- Direct cost row has project but no BOQ attribution

### 5.7 BOQ Profitability Foundation Report

Purpose: Establish a BOQ-aware profitability view without relying only on standard ERPNext project profitability.

Key metrics:

- Revised contract value
- Certified value
- Billed revenue
- Actual cost
- Committed cost
- Cost to date
- Gross margin amount
- Gross margin percent
- Unattributed project cost

---

## 6. Proposed Technical Architecture

### 6.1 Shared Reporting Service

Create shared Python service helpers for BOQ report calculations.

Suggested module:

`construction/services/boq_report_data.py`

Responsibilities:

- Resolve report filters.
- Apply scope context filters.
- Aggregate BOQ item and stage quantities.
- Aggregate approved variation values.
- Read attributed transaction rows.
- Read revenue rows from progress billing Sales Invoices.
- Expose reusable functions for Script Reports.

### 6.2 Report Modules

Create Frappe Script Reports under the Construction module.

Each report should have:

- Python `execute(filters=None)` function
- JS filter definition
- JSON report definition
- Tests for calculation logic where practical

### 6.3 Expense Claim Conditional Setup

Update setup and registry logic to include Expense Claim only if DocTypes exist:

- Parent DocType: `Expense Claim`
- Child table: likely `expenses`
- Child DocType: `Expense Claim Detail`

Required behavior:

- If Expense Claim DocTypes exist, add the BOQ cascade fields.
- If they do not exist, skip without error.
- Report services must treat Expense Claim as optional.

### 6.4 No Automatic Quantity Mutation

Do not update these fields automatically from transaction documents in this release:

- `BOQ Item.quantity_executed`
- `BOQ Item.quantity_certified`
- `BOQ Item Stage.measured_executed_qty`
- `BOQ Item Stage.certified_qty`

Reason: transaction quantity is not always equal to physical construction progress. For example:

- A Stock Entry for steel does not prove the BOQ steel item is installed.
- A Timesheet proves labour time, not necessarily certified client progress.
- A Purchase Invoice proves supplier cost, not client-approved work.

---

## 7. Security and Scope Requirements

Reports must respect existing scope context and role access.

Required report controls:

- Company filter
- Cost Center filter
- Project filter
- BOQ Header filter
- BOQ Structure filter
- BOQ Item filter
- Date range filter
- Expense category filter

Recommended role access:

- System Manager: full access
- Construction Owner: full construction reporting access
- Project Manager: project-scoped access
- QS / Quantity Surveyor: BOQ progress and measurement access
- Accountant: financial and profitability access

All report filters should work with the existing scope context enforcement instead of bypassing it.

---

## 8. Risks and Mitigations

### Risk: Large BOQs may be slow

Large enterprise BOQs can contain thousands or tens of thousands of items.

Mitigation:

- Use indexed fields.
- Aggregate with SQL, not Python loops over all documents.
- Reuse existing indexes on BOQ Header, BOQ Item, and BOQ Item Stage.
- Add indexes only after profiling proves need.

### Risk: GL and transaction rows may not reconcile

ERPNext GL Entries may not always carry the same custom fields as transaction child rows depending on Accounting Dimension propagation.

Mitigation:

- First report from source transaction rows where attribution exists.
- Add GL reconciliation as a later hardening step.
- Use exceptions report to detect missing attribution.

### Risk: Expense classification is not mature enough

Equipment, subcontractor, and expense categories may require account mapping or item group mapping.

Mitigation:

- Start with `expense_category`, account, item group, supplier group, and optional settings-based mapping.
- Avoid hard-coded assumptions.

### Risk: Reports could mislead if missing attribution is ignored

Costs without BOQ Item links will understate BOQ actual cost.

Mitigation:

- Build the Exceptions Report in the first release.
- Show unattributed project cost on overview and profitability reports.

---

## 9. Approval Gates for Head of Engineering

Please review and approve or reject each gate.

| Gate | Recommendation | HOE Decision |
| --- | --- | --- |
| Release shape | Enterprise Core reports first | Pending |
| Expense Claim | Include conditionally when DocTypes exist | Pending |
| Progress quantity source | Keep BOQ Item Stage as measurement truth | Pending |
| Transaction quantity mutation | Do not auto-update executed/certified quantities | Pending |
| BOQ Item financial key | Keep BOQ Item as attribution key | Pending |
| BOQ Item Stage GL dimension | Do not make it a GL dimension | Pending |
| Progress invoicing | Defer invoice generation until reports are stable | Pending |
| Exceptions report | Mandatory in first release | Pending |

---

## 10. AI Agent Review Checklist for HOE

The Head of Engineering AI reviewer should verify:

- The plan extends the current implementation instead of replacing it.
- The plan does not rename or repurpose existing BOQ fields.
- The plan keeps existing lifecycle statuses: Draft, Pricing, Frozen, Locked.
- The plan does not disable wildcard scope validation.
- The plan does not allow Stock Entry or Timesheet to overwrite certified progress.
- Expense Claim support is conditional and idempotent.
- The report set covers the owner concerns:
  - labour
  - equipment
  - subcontractors
  - expenses
  - materials
- The Project BOQ Overview includes unattributed cost warnings.
- Cost variance and profitability reports clearly separate:
  - committed cost
  - actual cost
  - billed revenue
  - certified value
- Reports are protected by role permissions and scope context.
- The first release can be tested without requiring progress invoice generation.

---

## 11. Recommended Implementation Order

1. Create shared BOQ report data service.
2. Create Revised BOQ Report.
3. Create BOQ Stage Measurement Report.
4. Create BOQ Progress Report.
5. Create BOQ Attribution Exceptions Report.
6. Add transaction cost aggregation for material, labour, equipment, subcontractor, and expense streams.
7. Add Project BOQ Overview.
8. Add BOQ Cost Variance Report.
9. Add BOQ Profitability Foundation Report.
10. Add conditional Expense Claim attribution support.
11. Add tests and manual QA evidence.
12. Only after the above is stable, plan progress invoicing.

---

## 12. Final Recommendation

Approve the Enterprise Core BOQ Reports plan with the following conditions:

1. Reports must be built from current BOQ and ERPNext attribution data.
2. Expense Claim must be supported conditionally, not as a hard dependency.
3. No transaction document should automatically mutate measured or certified progress.
4. The Exceptions Report must be part of the first release.
5. Profitability must be BOQ-aware and must expose unattributed costs instead of hiding them.

This gives project managers and enterprise leadership thoughtful, reliable data while protecting the engineering integrity of the BOQ model.
