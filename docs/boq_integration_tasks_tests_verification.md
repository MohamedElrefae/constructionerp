# BOQ Integration Tasks, Tests, and Verification

## Purpose

This document defines the execution checklist, test plan, and verification gates for BOQ integration. It is for review before implementation. No code task should begin until the requirements and implementation plan are approved.

## Review Checklist

Before implementation starts, review and approve:

1. `docs/boq_integration_requirements.md`
2. `docs/boq_integration_implementation.md`
3. `docs/boq_integration_tasks_tests_verification.md`

Required review decisions:

1. Allowed BOQ statuses for ERPNext transaction attribution.
2. Whether `BOQ Item Stage.planned_qty` totals must equal or only not exceed BOQ Item quantity.
3. Whether `stage_code` must be unique per BOQ Item.
4. Whether `expense_category` is required in this stage.
5. Which transaction child doctypes receive `boq_item_stage`.
6. Whether BOQ Item should be mandatory on any transaction rows.
7. Whether Accounting Dimension mandatory rules are deferred or configured now.

## Implementation Task List

### Task 1: Baseline Inspection

1. Re-read BOQ Header controller and metadata.
2. Re-read BOQ Structure controller and metadata.
3. Re-read BOQ Item controller and metadata.
4. Re-read hooks to confirm wildcard scope validation.
5. Re-read current BOQ tests.
6. Re-read ERPNext Accounting Dimension controller for the installed version.

Exit criteria:

1. Existing lifecycle and field names are confirmed.
2. Existing scope hook is confirmed.
3. ERPNext Accounting Dimension API signature is confirmed.

### Task 2: Add BOQ Item Stage Metadata

1. Create `BOQ Item Stage` DocType metadata.
2. Add fields approved during review.
3. Add permissions aligned with existing BOQ doctypes.
4. Add list/search fields useful for BOQ Item and stage name lookup.

Exit criteria:

1. DocType is installable.
2. Metadata follows local app namespace and module conventions.
3. No existing BOQ metadata is replaced.

### Task 3: Add BOQ Item Stage Controller

1. Add validation for required BOQ Item.
2. Fetch or validate BOQ Header from BOQ Item.
3. Fetch or validate Project from BOQ Header.
4. Validate non-negative quantities.
5. Validate certified quantity.
6. Validate percent complete.
7. Validate total planned stage quantity against BOQ Item quantity.
8. Validate status restrictions according to the approved rule.

Exit criteria:

1. Valid stages save.
2. Invalid quantities are rejected.
3. Invalid status edits are rejected.
4. Existing BOQ Item behavior is unchanged.

### Task 4: Extend BOQ Item Metadata

1. Add `has_stages` checkbox.
2. Place the field in a reviewed section of BOQ Item.
3. Keep it optional.
4. Do not change pricing fields.
5. Do not change rollup logic.

Exit criteria:

1. Existing BOQ Item tests still pass.
2. Existing import/export assumptions are not broken.

### Task 5: Add BOQ Accounting Dimension Setup

1. Add idempotent setup function.
2. Create `Accounting Dimension` for `BOQ Item` only if missing.
3. Use ERPNext native `make_dimension_in_accounting_doctypes(doc=...)`.
4. Add setup to after-install.
5. Add setup to after-migrate.
6. Avoid raw SQL schema changes.

Exit criteria:

1. Running setup once creates the dimension.
2. Running setup again does not duplicate it.
3. Generated `boq_item` fields exist on expected ERPNext doctypes.

### Task 6: Add Operational Custom Fields

1. Add `boq_item_stage` field to approved transaction child doctypes.
2. Add `expense_category` only if approved.
3. Use Frappe custom field APIs.
4. Make setup idempotent.
5. Place fields near accounting dimensions or project fields where practical.

Exit criteria:

1. Custom fields are created once.
2. Re-running setup does not duplicate custom fields.
3. Fields are visible on expected transaction rows.

### Task 7: Add Transaction Validation Service

1. Create central validation service.
2. Validate BOQ Item existence.
3. Validate BOQ Header status.
4. Validate BOQ Item Stage belongs to BOQ Item.
5. Validate project consistency where project is available.
6. Leave budget checks warning-only unless a blocking rule is approved.
7. Do not write progress quantities.
8. Do not write GL fields manually.

Exit criteria:

1. Valid transaction rows pass.
2. Invalid BOQ Item Stage links fail.
3. Project mismatches fail.
4. Missing BOQ Item with stage fails.

### Task 8: Merge Hooks

1. Preserve existing wildcard scope validation.
2. Add specific validate hooks for approved parent doctypes.
3. Do not replace `doc_events`.
4. Confirm hook syntax supports both wildcard and specific doctype handlers.

Exit criteria:

1. BOQ transaction validation runs.
2. Wildcard scope validation still runs.

### Task 9: Add Tests

1. Add BOQ Item Stage unit/integration tests.
2. Add Accounting Dimension setup tests.
3. Add operational custom field setup tests.
4. Add transaction validation tests.
5. Add hook regression tests.
6. Keep existing BOQ tests passing.

Exit criteria:

1. New tests fail before implementation where appropriate.
2. New tests pass after implementation.
3. Existing tests still pass.

## Test Plan

### Existing Regression Tests

Run existing BOQ tests:

1. BOQ Header lifecycle.
2. BOQ Structure tree creation.
3. Leaf-node BOQ Item auto-creation.
4. Header rollups.
5. Pricing locks.
6. Import/export service availability.

Run existing scope tests:

1. Scope context behavior.
2. Wildcard validation behavior.
3. Permission query behavior where currently covered.

### BOQ Item Stage Tests

Add tests for:

1. Valid BOQ Item Stage creation.
2. Negative planned quantity rejected.
3. Negative measured executed quantity rejected.
4. Negative certified quantity rejected.
5. Certified quantity greater than measured executed quantity rejected.
6. Percent complete below 0 rejected.
7. Percent complete above 100 rejected.
8. Sum of planned stage quantities greater than BOQ Item quantity rejected.
9. Stage BOQ Header matches parent BOQ Item BOQ Header.
10. Stage Project matches parent BOQ Header Project.
11. Frozen and Locked status behavior follows approved rule.

### Accounting Dimension Tests

Add tests for:

1. BOQ Item Accounting Dimension creation.
2. Dimension setup idempotency.
3. Dimension fieldname is `boq_item`.
4. Generated fields exist on expected doctypes after setup.
5. No duplicate Custom Fields are created after repeated setup.

### Operational Custom Field Tests

Add tests for:

1. `boq_item_stage` exists on approved doctypes.
2. `boq_item_stage` links to `BOQ Item Stage`.
3. `expense_category` exists only on approved doctypes, if approved.
4. Re-running setup does not duplicate fields.

### Transaction Validation Tests

Add tests for each approved parent doctype where practical:

1. Purchase Order
2. Purchase Receipt
3. Purchase Invoice
4. Stock Entry
5. Timesheet
6. Journal Entry
7. Sales Invoice

Validation scenarios:

1. No BOQ fields set: allowed unless BOQ is approved as mandatory.
2. Valid BOQ Item: allowed.
3. Valid BOQ Item and matching BOQ Item Stage: allowed.
4. BOQ Item Stage without BOQ Item: rejected.
5. BOQ Item Stage belonging to a different BOQ Item: rejected.
6. BOQ Item project mismatch: rejected.
7. BOQ Header status not allowed for transactions: rejected.

### Hook Regression Tests

Add tests for:

1. BOQ transaction validation hook is registered.
2. Existing wildcard scope validation hook remains registered.
3. Saving a document that triggers scope validation still calls the scope validator.
4. BOQ hook additions do not replace wildcard hooks.

## Verification Commands

Final commands should be selected based on available test site and approved scope.

Recommended targeted verification:

1. Run BOQ integration tests.
2. Run BOQ property tests.
3. Run scope context tests.
4. Run new BOQ Item Stage tests.
5. Run new transaction validation tests.

Recommended migration verification on a test site:

1. Run migrate.
2. Confirm Accounting Dimension exists.
3. Confirm `boq_item` custom fields exist.
4. Confirm `boq_item_stage` custom fields exist.
5. Re-run migrate.
6. Confirm no duplicate records were created.

Recommended metadata inspection:

1. Inspect `Accounting Dimension` for `BOQ Item`.
2. Inspect Custom Fields for:
   - `boq_item`
   - `boq_item_stage`
3. Inspect hooks.
4. Inspect modified files.

## Manual Verification Checklist

### BOQ Authoring

1. Create a Project.
2. Create a BOQ Header for the Project.
3. Create a BOQ Structure group.
4. Create a BOQ Structure leaf.
5. Confirm BOQ Item is auto-created.
6. Enter BOQ Item quantity and pricing.
7. Confirm header rollups still work.

### Stage Tracking

1. Enable `has_stages` on BOQ Item.
2. Create one BOQ Item Stage.
3. Create multiple BOQ Item Stages.
4. Confirm valid planned quantities are accepted.
5. Confirm over-planning is rejected.
6. Confirm invalid certified quantity is rejected.
7. Confirm invalid percent complete is rejected.

### Accounting Dimension

1. Confirm `BOQ Item` Accounting Dimension exists.
2. Confirm generated fieldname is `boq_item`.
3. Open a supported transaction row.
4. Confirm `boq_item` is available.
5. Confirm `boq_item_stage` is available where approved.

### Transaction Validation

1. Save a transaction row with a valid BOQ Item.
2. Save a transaction row with a valid BOQ Item and matching stage.
3. Try a stage from another BOQ Item and confirm rejection.
4. Try a BOQ Item from another Project and confirm rejection.
5. Confirm Stock Entry does not update stage executed quantity automatically.
6. Confirm Timesheet does not overwrite stage executed quantity automatically.

### Scope Regression

1. Use an existing scope-sensitive document.
2. Trigger validation.
3. Confirm scope validation still applies.
4. Confirm BOQ hook changes did not disable wildcard validation.

## Release Readiness Checklist

Before merging or deploying:

1. Requirements reviewed and approved.
2. Implementation plan reviewed and approved.
3. Task/test checklist reviewed and approved.
4. All approved tests pass.
5. Test-site migrate passes.
6. Repeated setup is idempotent.
7. Existing BOQ workflows still work.
8. Existing scope validation still works.
9. No unintended files changed.
10. Open decisions are documented if deferred.
