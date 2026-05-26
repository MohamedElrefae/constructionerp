# BOQ Integration Implementation Plan

## Purpose

This document describes the proposed implementation sequence for BOQ integration. It is a technical plan for review before code changes. Implementation should not begin until this file, the requirements file, and the tasks/tests/verification file are approved.

## Guiding Principles

1. Extend the current BOQ module instead of replacing it.
2. Keep `BOQ Item` as the GL-level accounting dimension.
3. Keep `BOQ Item Stage` operational in this stage.
4. Preserve the existing BOQ lifecycle:
   - Draft
   - Pricing
   - Frozen
   - Locked
5. Use ERPNext native Accounting Dimension setup.
6. Add server-side validation for all critical business rules.
7. Keep implementation migration-safe and idempotent.

## Stage 1: Confirm Local Baseline

Before changing files, re-check these local files:

1. `construction/hooks.py`
2. `construction/construction/doctype/boq_header/boq_header.py`
3. `construction/construction/doctype/boq_header/boq_header.json`
4. `construction/construction/doctype/boq_structure/boq_structure.py`
5. `construction/construction/doctype/boq_structure/boq_structure.json`
6. `construction/construction/doctype/boq_item/boq_item.py`
7. `construction/construction/doctype/boq_item/boq_item.json`
8. `construction/patches.txt`
9. Current BOQ and scope tests.

Baseline confirmations:

1. App namespace is `construction`.
2. BOQ Header lifecycle remains unchanged.
3. BOQ Structure parent field is `parent_structure`.
4. BOQ Item is linked to BOQ Structure through unique `structure`.
5. BOQ Item pricing fields remain unchanged.
6. Wildcard scope validation hook exists and must be preserved.

## Stage 2: Add BOQ Item Stage

Create a new DocType:

1. Name: `BOQ Item Stage`
2. Module: `construction`
3. Naming: stable generated naming pattern or field-based naming after review.
4. Purpose: operational progress phasing under a BOQ Item.

Recommended fields:

1. `boq_item`
   - Type: Link
   - Options: `BOQ Item`
   - Required: yes
2. `boq_header`
   - Type: Link
   - Options: `BOQ Header`
   - Read-only or fetched from BOQ Item
   - Purpose: easier filtering and reporting
3. `project`
   - Type: Link
   - Options: `Project`
   - Read-only or fetched through BOQ Header
   - Purpose: validation and reporting
4. `stage_code`
   - Type: Data
   - Required: yes
5. `stage_name`
   - Type: Data
   - Required: yes
6. `planned_qty`
   - Type: Float
   - Non-negative
7. `measured_executed_qty`
   - Type: Float
   - Non-negative
8. `certified_qty`
   - Type: Float
   - Non-negative
9. `percent_complete`
   - Type: Percent
   - Range: 0 to 100
10. `stage_status`
   - Type: Select
   - Proposed options:
     - Not Started
     - In Progress
     - Completed
     - Certified
     - On Hold
11. `description`
   - Type: Small Text
   - Optional

Controller validation:

1. Fetch or validate `boq_header` from the selected BOQ Item.
2. Fetch or validate `project` from the BOQ Header.
3. Reject negative quantities.
4. Reject certified quantity greater than measured executed quantity.
5. Reject percent complete outside 0 to 100.
6. Reject total planned quantity across stages greater than parent BOQ Item quantity.
7. Apply existing BOQ lifecycle behavior for stage authoring. Proposed first rule:
   - Draft and Pricing allow stage authoring.
   - Frozen and Locked block stage authoring.

Open review decision:

1. Should `BOQ Item Stage` be allowed in Pricing status?
2. Should `stage_code` be unique per BOQ Item?
3. Should `planned_qty` sum equal parent quantity or only be less than or equal to parent quantity?

## Stage 3: Extend BOQ Item

Add one field to `BOQ Item`:

1. `has_stages`
   - Type: Check
   - Default: 0
   - Purpose: indicates that the BOQ Item is planned through operational stages.

Rules:

1. Do not make stages mandatory in this stage.
2. Do not alter current BOQ Item pricing or rollup calculations.
3. Do not add automatic stage templates until a template design is approved.
4. Do not use stage totals in header financial rollups.

## Stage 4: Accounting Dimension Setup

Add an idempotent setup function for the BOQ Item Accounting Dimension.

Expected behavior:

1. Check if `Accounting Dimension` exists for `document_type = "BOQ Item"`.
2. If missing, create it with:
   - `document_type = "BOQ Item"`
   - `label = "BOQ Item"`
3. Let ERPNext set `fieldname` to `boq_item`.
4. Call ERPNext native dimension field creation with the correct v16 signature:
   - `make_dimension_in_accounting_doctypes(doc=dimension_doc)`
5. Do not manually create the accounting dimension custom fields unless ERPNext native setup fails.
6. Do not use `mandatory_for_pl` or `mandatory_for_bs` on the parent Accounting Dimension.

Install and migrate integration:

1. Add the setup function to after-install flow.
2. Add the setup function to after-migrate flow.
3. Make it safe to run repeatedly.

Open review decision:

1. Should BOQ Item be mandatory for any companies in this stage?
2. If yes, which company and which account type rules should be configured through Accounting Dimension Detail?

## Stage 5: Operational Custom Fields

Add custom fields for operational BOQ stage tracking.

Recommended transaction child doctypes:

1. `Purchase Order Item`
2. `Purchase Receipt Item`
3. `Purchase Invoice Item`
4. `Stock Entry Detail`
5. `Timesheet Detail`
6. `Journal Entry Account`
7. `Sales Invoice Item`

Field: `boq_item_stage`

1. Type: Link
2. Options: `BOQ Item Stage`
3. Required: no
4. Allow on submit: should follow the parent doctype pattern and be reviewed per doctype
5. Purpose: operational attribution only

Field: `expense_category`

1. Add only if transaction validation requires it.
2. Keep it optional in the first stage unless a clear procurement/accounting rule is approved.

Open review decision:

1. Is `expense_category` required now?
2. If yes, what are the allowed values and which transaction rows need it?
3. Should Direct Purchase rows require BOQ Item, or should BOQ Item remain optional with warnings?

## Stage 6: Transaction Validation Service

Create a central validation service under the existing app namespace.

Recommended location:

1. `construction/services/boq_transaction_validation.py`

Responsibilities:

1. Inspect relevant transaction rows.
2. Validate BOQ Item links.
3. Validate BOQ Item Stage links.
4. Validate project consistency.
5. Validate BOQ Header status.
6. Avoid changing quantities, progress, or GL amounts.

Validation details:

1. If a row has no `boq_item` and no `boq_item_stage`, skip row-level BOQ validation.
2. If a row has `boq_item_stage` but no `boq_item`, reject it.
3. If a row has both fields, confirm the stage belongs to the BOQ Item.
4. If the row or parent document has a project, confirm it matches the BOQ Header project for the BOQ Item.
5. If BOQ Header status is not approved for transaction attribution, reject the row.

Proposed status rule for review:

1. Draft: do not allow financial transaction attribution.
2. Pricing: do not allow financial transaction attribution.
3. Frozen: allow transaction attribution.
4. Locked: allow transaction attribution.

Alternative status rule:

1. Pricing, Frozen, and Locked are allowed.
2. Draft is blocked.

Open review decision:

1. Which BOQ statuses should allow ERPNext transactions?
2. Should Sales Invoice attribution follow the same status rule as cost transactions?

## Stage 7: Hook Integration

Modify hooks only after review.

Rules:

1. Preserve existing wildcard scope validation.
2. Add BOQ validation under specific ERPNext parent doctypes.
3. Do not overwrite `doc_events`.
4. Do not add wildcard BOQ validation.

Candidate doctypes for hooks:

1. `Purchase Order`
2. `Purchase Receipt`
3. `Purchase Invoice`
4. `Stock Entry`
5. `Timesheet`
6. `Journal Entry`
7. `Sales Invoice`

Recommended event:

1. `validate`

Possible later event:

1. `before_submit`, if validation needs to be stricter at submission than draft save.

## Stage 8: Reporting Boundary

Do not build reports in the first implementation unless separately approved.

Planned later reports:

1. BOQ Cost Variance Report
   - Source: GL Entry
   - Dimension: `boq_item`
   - Must classify cost, WIP, inventory, revenue, and billing accounts carefully
2. BOQ Stage Operational Report
   - Source: operational transaction rows and BOQ Item Stage
   - Dimension: `boq_item_stage`
   - Not GL truth in this stage

## Stage 9: Migration Safety

Migration rules:

1. Add a new patch only for idempotent metadata/setup work.
2. Do not run destructive migrations.
3. Do not rename BOQ fields.
4. Do not rewrite existing BOQ records.
5. Do not create raw database columns manually when ERPNext custom field APIs can do it.

## Stage 10: Review Gates Before Coding

The following decisions must be reviewed before implementation:

1. Allowed BOQ Header statuses for ERPNext transactions.
2. Whether stage planned quantity must equal or only not exceed BOQ Item quantity.
3. Whether `stage_code` must be unique per BOQ Item.
4. Whether `expense_category` is needed now.
5. Which transaction doctypes receive `boq_item_stage`.
6. Whether BOQ Item is mandatory on any transaction rows in this stage.
7. Whether Accounting Dimension mandatory rules are configured now or deferred.
