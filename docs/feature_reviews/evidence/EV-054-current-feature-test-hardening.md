# EV-054 - Current Feature Test Hardening

Date: 2026-06-10

## Purpose

Record the test-hardening work done after the formal runner moved past the original ERPNext Fiscal Year bootstrap blocker and exposed real construction test failures.

The recommendation was to fix only failures that block the current Improve Now value stream: BOQ, WBS, Excel import/export, stage measurement, scope context, and transaction scope. Legacy Construction Theme and v6.0 migration tests remain deferred because they are outside the current BOQ execution plan.

## Changes Made

- Added shared BOQ test helper: `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_helpers.py`.
- Updated BOQ tests to create `BOQ Header` records with a valid `Project`, matching the current mandatory schema.
- Aligned BOQ Structure tests with the current controller contract: `is_group = 1` for sections and `is_group = 0` for leaf/items.
- Updated WBS health tests so DB-level uniqueness remains the source of truth for duplicate WBS prevention, while the health checker still verifies corrupt legacy data scenarios.
- Updated `User Scope Context` track-change test to save with `ignore_version=False`, because Frappe suppresses Version records in test mode unless explicitly overridden.

## Verification Command

```bash
bench --site v16.localhost run-tests --app construction --skip-before-tests --lightmode
```

## Verified Passing Current-Feature Areas

The run reached construction tests and the following critical suites passed in the visible output:

- `construction.tests.test_boq_item_stage.TestBOQItemStage`
- `construction.tests.test_boq_wbs_generation.TestBOQWBSGeneration`
- `construction.tests.test_boq_structure_delete_safety.TestBOQStructureDeleteSafety`
- `construction.tests.test_boq_properties.TestBOQProperties`
- `construction.tests.test_boq_integration.TestBOQIntegration`
- `construction.tests.test_boq_excel_parser.TestBOQExcelParser`
- `construction.tests.test_boq_link_queries.TestBOQLinkQueries`
- `construction.tests.test_boq_wbs_resequence.TestBOQWBSResequence`
- `construction.tests.test_boq_wbs_health.TestBOQWBSHealth`
- `construction.tests.test_boq_structure_conversion.TestBOQStructureConversion`
- `construction.tests.test_accounting_dimension.TestBOQAccountingDimension`
- `construction.tests.test_transaction_validation.TestBOQTransactionValidation`
- `construction.searchable_dropdown.tests.*`
- `construction.construction.doctype.user_scope_context.test_user_scope_context.TestUserScopeContext`

Python syntax verification also passed for the patched test files.

## Remaining Deferred Failures

The full lightmode run still exits red:

```text
Ran 204 tests in 53.756s
FAILED (failures=15, errors=27)
```

The remaining failures are concentrated in the deferred Construction Theme and v6.0 migration test lane:

- Missing stylesheet fixture: `construction/construction/public/css/construction_theme_components.css`.
- Login background tests require `test_login_bg.jpg` under the test site's public files.
- Construction Theme validation expectations no longer match current behavior for login background type requirements.
- v6.0 migration tests expect old auto-population behavior and older color rounding results.
- `list_active_themes` test expects `is_active`, but the returned theme dict in the current implementation does not include that key.

## Decision

Current Improve Now BOQ/WBS/import/stage/scope functionality is no longer blocked by construction test failures under the lightmode runner.

The remaining red tests should be handled in a separate Theme/Migration cleanup work package after the BOQ/VO execution plan, unless management decides the theme system is part of the immediate release gate.

## Notes

Standard non-lightmode `bench run-tests` still depends on a fully provisioned ERPNext test environment. In this site it previously progressed past Fiscal Year overlap only after site data fixes, then can hit optional dependency/test bootstrap problems such as missing payment gateway doctypes. For current construction verification, `--skip-before-tests --lightmode` is the practical local runner.
