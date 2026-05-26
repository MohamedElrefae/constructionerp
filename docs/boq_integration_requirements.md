# BOQ Integration Requirements

## Purpose

This document defines the requirements for integrating the existing Construction BOQ module with ERPNext accounting and operational transactions. It is intentionally limited to planning. No implementation should begin until this document, the implementation plan, and the task/test checklist are reviewed and approved.

## Current System Baseline

The local app is an existing Phase 1 BOQ system. The implementation must extend it, not replace it.

1. App namespace is `construction`.
2. Existing BOQ Header lifecycle is authoritative:
   - Draft
   - Pricing
   - Frozen
   - Locked
3. Existing BOQ Structure tree field is `parent_structure`.
4. Existing BOQ Item is linked one-to-one with a leaf BOQ Structure through `structure`.
5. Existing BOQ Item records are auto-created from leaf BOQ Structure nodes.
6. Existing pricing and quantity fields must remain unchanged:
   - `quantity`
   - `unit`
   - `factor`
   - `contract_unit_price`
   - `line_total`
   - `est_unit_cost`
   - `est_unit_price`
   - `est_line_total`
7. Existing BOQ rollups, import/export flows, print formats, and tests must continue to work.
8. Existing wildcard scope validation in hooks must remain active.

## Business Goals

1. Track financial actuals against BOQ Items using ERPNext accounting dimensions.
2. Keep `BOQ Item` as the GL-level dimension for actual cost and billing attribution.
3. Add operational execution phasing through `BOQ Item Stage`.
4. Keep `BOQ Item Stage` operational only in this stage. It must not become a GL dimension yet.
5. Allow ERPNext transaction rows to reference BOQ Items and, where useful, BOQ Item Stages.
6. Enforce server-side consistency so invalid BOQ links cannot enter submitted business documents.
7. Preserve all existing Phase 1 BOQ behavior unless a separate migration is approved.

## In Scope

1. Add a new DocType named `BOQ Item Stage`.
2. Add `has_stages` to `BOQ Item`.
3. Create an ERPNext Accounting Dimension for `BOQ Item`.
4. Let ERPNext create the native `boq_item` custom fields for accounting doctypes.
5. Add operational `boq_item_stage` fields to selected transaction child tables.
6. Add server-side validation for BOQ links on selected ERPNext transactions.
7. Add idempotent setup for install and migrate.
8. Add tests for stage validation, dimension setup, transaction validation, and hook regression.

## Out of Scope

1. Replacing the BOQ lifecycle with Draft, Active, and Closed.
2. Renaming existing BOQ fields.
3. Replacing existing BOQ Item pricing fields with `rate` or `budget_amount`.
4. Replacing `parent_structure` with another parent field.
5. Auto-deriving physical progress directly from Stock Entry quantities.
6. Making `BOQ Item Stage` an accounting dimension.
7. IPC or progress billing.
8. Revision cloning and archived version reporting.
9. Raw SQL schema alteration for accounting dimension indexes unless later profiling proves it is needed.
10. Any change that disables existing scope enforcement.

## Required Data Model Rules

1. A BOQ Item must continue to link only to a leaf BOQ Structure.
2. A BOQ Item must continue to belong to one BOQ Header.
3. A BOQ Item Stage must belong to exactly one BOQ Item.
4. A BOQ Item Stage must not be linked to a transaction row unless the row also references the same BOQ Item.
5. BOQ Item Stage planned quantities for a BOQ Item must not exceed the parent BOQ Item quantity.
6. BOQ Item Stage measured and certified quantities must be non-negative.
7. BOQ Item Stage certified quantity must not exceed measured executed quantity.
8. BOQ Item Stage percent complete must be between 0 and 100.

## Required Accounting Rules

1. `BOQ Item` is the accounting dimension.
2. The Accounting Dimension record must use:
   - `document_type = "BOQ Item"`
   - `label = "BOQ Item"`
3. ERPNext must generate the `boq_item` field through its native Accounting Dimension mechanism.
4. Mandatory accounting dimension rules are not part of the parent Accounting Dimension record. If needed later, they must be configured through Accounting Dimension Detail rows per company.
5. `BOQ Item Stage` must not be used as the GL-level source of truth in this stage.

## Required Transaction Coverage

The integration should support BOQ validation for these transaction areas:

1. Purchase Order
2. Purchase Receipt
3. Purchase Invoice
4. Stock Entry
5. Timesheet
6. Journal Entry
7. Sales Invoice

The expected BOQ fields are:

1. Native accounting dimension field:
   - `boq_item`
2. Operational field:
   - `boq_item_stage`
3. Optional classification field only where needed:
   - `expense_category`

## Required Validation Rules

Validation must run server-side. Link filters are helpful for user experience but are not sufficient.

1. If `boq_item_stage` is set, `boq_item` must also be set.
2. If both `boq_item` and `boq_item_stage` are set, the stage must belong to the BOQ Item.
3. If a document row has a project and BOQ Item has a project through its BOQ Header, they must match.
4. BOQ Header status must be checked before accepting a BOQ Item on transactions.
5. The first implementation should avoid blocking budget overruns. Budget overrun checks should be warnings only unless a later setting makes them blocking.
6. Stock Entry quantities must not be written directly into BOQ executed quantity.
7. Timesheet or Task progress must not overwrite stage executed quantity unless an approved source-of-truth rule exists.

## Required Hook Rules

1. Existing wildcard scope hook must remain:
   - `*`
   - `validate`
   - `construction.overrides.scope_enforcement.validate`
2. BOQ transaction hooks must be added without replacing the wildcard hook.
3. Hook additions must be limited to specific ERPNext doctypes.
4. Tests must prove scope validation still runs after BOQ hooks are added.

## Required Migration Rules

1. All setup must be idempotent.
2. Running install or migrate multiple times must not duplicate Custom Fields or Accounting Dimension records.
3. Existing records must not be renamed or deleted.
4. Existing BOQ Item fields must not be removed or repurposed.
5. Existing BOQ Header statuses must not be migrated.

## Acceptance Criteria

The stage is accepted only when all of the following are true:

1. Existing BOQ tests still pass.
2. Existing scope context tests still pass.
3. `BOQ Item Stage` can be created and validated.
4. Invalid stage quantity totals are rejected.
5. Invalid stage-to-item links are rejected.
6. `BOQ Item` Accounting Dimension setup is idempotent.
7. ERPNext-generated `boq_item` fields exist on expected doctypes after setup.
8. Operational `boq_item_stage` fields exist on expected transaction rows.
9. Transaction validation rejects mismatched project links where project is available.
10. Transaction validation rejects a BOQ Item Stage that belongs to another BOQ Item.
11. No existing BOQ fields are renamed, removed, or made incompatible.
12. No existing wildcard hook is overwritten.
