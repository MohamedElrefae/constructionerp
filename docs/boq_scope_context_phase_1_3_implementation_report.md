# BOQ Scope Context Filtering — Phase 1-3 Implementation Report

**Date:** 2026-05-26  
**App:** `construction`  
**Bench site used for verification:** `v16.localhost`  
**Current rollout flag:** `Construction Settings.enable_boq_cascade_filtering = Off`

## 1. Implementation Summary

Phases 1, 2, and 3 of BOQ Scope Context Filtering have been implemented locally.

The implementation follows the approved enterprise pattern:

> Prevent invalid BOQ attribution through filtered dropdowns first, then keep backend validation as the final integrity layer.

The feature is currently installed and built, but safely disabled by the feature flag until `enable_boq_cascade_filtering` is changed from `Off` to `On`.

## 2. Phase 1 — Data Model and Rollout Foundation

### Added Settings

`Construction Settings` now includes:

- `enable_boq_cascade_filtering`
- Options: `Off`, `On`, `Strict`
- Default and verified local value: `Off`
- `direct_labor_designations` child table

### Added Child DocType

Added child table DocType:

- `Direct Labor Designation`

Fields:

- `designation`
- `boq_requirement`

Seed behavior is defensive: only Designation records that already exist on the site are inserted. This avoids migration failure on sites that do not yet define roles like Mason, Carpenter, or Site Worker.

### Added Transaction Fields

The following BOQ cascade fields are provisioned on the approved transaction child DocTypes:

- `boq_header`
- `boq_structure`
- `boq_item`
- `boq_item_stage`
- `boq_selection_scope_type`

Target child DocTypes:

- `Purchase Order Item`
- `Purchase Receipt Item`
- `Purchase Invoice Item`
- `Stock Entry Detail`
- `Timesheet Detail`
- `Journal Entry Account`
- `Sales Invoice Item`
- `Material Request Item`

### Per-DocType Visibility Gates

Procurement / expense rows:

```text
expense_category == "Direct"
```

Sales Invoice Item:

```text
is_progress_billing == true
```

Timesheet Detail:

```text
row.designation is in frappe.boot.direct_labor_designations
```

Journal Entry Account:

- Added `expense_category`
- Default is blank, not `Direct`

Sales Invoice Item:

- Added `is_progress_billing`

Timesheet Detail:

- Added hidden cached `designation` field so the direct-labor gate can evaluate on child rows.

### Added Indexes

Verified local indexes:

| Table | Index | Columns |
|---|---|---|
| `tabBOQ Header` | `idx_boq_header_project` | `project` |
| `tabBOQ Structure` | `idx_boq_structure_header_group` | `boq_header, is_group` |
| `tabBOQ Item` | `idx_boq_item_header_structure` | `boq_header, structure` |
| `tabBOQ Item Stage` | `idx_boq_item_stage_item` | `boq_item` |

### Added Patches

Listed migration patch:

```text
construction.patches.v6_6.add_boq_cascade_transaction_fields
```

Manual rollback patch, intentionally not listed in `patches.txt`:

```text
construction.patches.v6_6.revert_boq_cascade_fields
```

Rollback hides cascade fields and sets the feature flag back to `Off`. It preserves captured `boq_item` data.

## 3. Phase 2 — Server Scope Filtering

### Added Service Modules

Added:

```text
construction/services/scope_resolution.py
construction/services/boq_scope_filters.py
```

`scope_resolution.py` handles:

- Active `User Scope Context` resolution
- SHA-256 scope token generation
- Rollout mode lookup
- Cost-center descendant expansion
- `enforce_scope` compatibility handling

`boq_scope_filters.py` handles:

- SQL-aware scope condition builders
- BOQ allowed/excluded status constants
- Project-scoped and company/cost-center-scoped BOQ filtering

### Added Status Constants

```python
ALLOWED_TRANSACTION_BOQ_STATUSES = ["Locked", "Frozen"]
EXCLUDED_TRANSACTION_BOQ_STATUSES = ["Draft", "Pricing", "Closed"]
```

`boq_accounting.py` now uses the shared allowed-status constant instead of inline status strings.

### Hardened Query APIs

Updated:

```text
construction/api/boq_link_queries.py
```

Implemented scoped query support for:

- `get_boq_headers`
- `get_boq_structures`
- `get_boq_items`
- `get_boq_item_stages`

Added endpoints:

- `get_boq_scope_token`
- `get_allowed_transaction_boq_statuses`

Important implementation note:

- `enforce_scope` is read from `filters.enforce_scope` because Frappe Link queries reliably pass `filters`, while extra top-level query args are not reliable in every Link control path.

### Scope Behavior

If active scope has a project:

```text
BOQ Header filters strictly by Project.
```

If active scope has no project:

```text
BOQ Header filters by Company and Cost Center where possible.
A warning is exposed in the server response metadata:
"No project selected — BOQ results are not project-scoped."
```

## 4. Phase 3 — Client Cascade Controller

Updated:

```text
construction/public/js/boq_filters.js
```

### Implemented Cascade

The client now controls the full chain:

```text
BOQ Header → BOQ Structure → BOQ Item → BOQ Item Stage
```

Dropdown behavior:

- BOQ Header filters by active scope.
- BOQ Structure filters by selected BOQ Header and leaf nodes only.
- BOQ Item filters by BOQ Header and BOQ Structure.
- BOQ Item Stage filters by selected BOQ Item.

### Downstream Clearing

When `boq_header` changes:

```text
boq_structure, boq_item, boq_item_stage are cleared.
```

When `boq_structure` changes:

```text
boq_item, boq_item_stage are cleared.
```

When `boq_item` changes:

```text
boq_item_stage is cleared.
```

When `expense_category` changes away from `Direct`:

```text
All BOQ fields are cleared.
```

Sales Invoice Item and Timesheet Detail use their own gates and do not depend on `expense_category`.

### User Notices

The client uses `frappe.show_alert`, not `frappe.msgprint`, for non-blocking guidance.

An `aria-live="polite"` live region is created for accessibility.

### Scope Drift Guard

The client fetches a scope token from:

```text
construction.api.boq_link_queries.get_boq_scope_token
```

Before save or submit:

- Current token is compared with the last known token.
- If different, the form reloads and save/submit is blocked.
- This prevents multi-tab stale scope attribution.

### Scope Change Rebinding

The client listens for:

```text
scope:changed
```

When fired:

- BOQ queries are rebound.
- Child table fields refresh.
- User sees a non-blocking notice that BOQ dropdowns refreshed.

## 5. Local Verification Already Completed

Commands run successfully:

```bash
bench --site v16.localhost migrate
bench --site v16.localhost clear-cache
bench build --app construction
node --check construction/public/js/boq_filters.js
python -m py_compile construction/install.py construction/api/boq_link_queries.py construction/services/scope_resolution.py construction/services/boq_scope_filters.py construction/public/js/boq_filters.js
```

Note: the last command above should not normally include JS in `py_compile`; use `node --check` for JS. The actual JS syntax check was run with `node --check`.

Phase 2 query tests passed through direct site-bound unittest execution:

```bash
bench --site v16.localhost execute "(__import__('unittest').TextTestRunner(verbosity=1).run(__import__('unittest').defaultTestLoader.loadTestsFromName('construction.tests.test_boq_link_queries')).wasSuccessful() or (_ for _ in ()).throw(Exception('tests failed')))"
```

Result:

```text
Ran 3 tests
OK
```

Standard Frappe test runner currently has an unrelated blocker:

```text
ModuleNotFoundError: No module named 'pytest'
```

Cause:

```text
construction_theme/test_css_generator_properties.py imports pytest
```

This blocks `bench run-tests` before the BOQ test module runs.

## 6. How To Test Locally In Bench

### 6.1 Prepare Bench

Run:

```bash
cd /home/mohamed/frappe-bench
bench --site v16.localhost migrate
bench build --app construction
bench --site v16.localhost clear-cache
```

Restart bench if running in development mode:

```bash
bench start
```

In the browser, hard refresh:

```text
Ctrl + Shift + R
```

### 6.2 Confirm Feature Flag Is Off

Run:

```bash
bench --site v16.localhost mariadb -N -e "select field, value from tabSingles where doctype='Construction Settings' and field='enable_boq_cascade_filtering'"
```

Expected:

```text
enable_boq_cascade_filtering    Off
```

With `Off`, legacy behavior should remain active.

### 6.3 Enable Pilot Mode Locally

In Desk:

```text
Construction Settings → Enable BOQ Cascade Filtering → On → Save
```

Or from bench:

```bash
bench --site v16.localhost set-config developer_mode 1
bench --site v16.localhost execute "frappe.db.set_single_value('Construction Settings', 'enable_boq_cascade_filtering', 'On')"
bench --site v16.localhost clear-cache
```

Then hard refresh browser.

### 6.4 Confirm Boot Values In Browser Console

Open Desk browser console and run:

```javascript
frappe.boot.enable_boq_cascade_filtering
```

Expected:

```text
"On"
```

Run:

```javascript
frappe.boot.direct_labor_designations
```

Expected:

```text
Array of mandatory direct-labor designations, possibly empty depending on master data.
```

### 6.5 Test Purchase Invoice Cascade

Use a Purchase Invoice or Purchase Order with item rows.

Steps:

1. Set Scope Context Company.
2. Set Scope Context Cost Center if available.
3. Set Scope Context Project.
4. Open a new Purchase Invoice.
5. In an item row, set `expense_category = Direct`.
6. Open `boq_header` dropdown.
7. Confirm only BOQ Headers for the selected project appear.
8. Select a BOQ Header.
9. Open `boq_structure` dropdown.
10. Confirm only leaf BOQ Structures for that BOQ Header appear.
11. Select BOQ Structure.
12. Open `boq_item` dropdown.
13. Confirm only BOQ Items linked to the selected BOQ Header and Structure appear.
14. Select BOQ Item.
15. Open `boq_item_stage` dropdown.
16. Confirm only stages for the selected BOQ Item appear.

### 6.6 Test Downstream Clearing

In the same row:

1. Select full BOQ chain.
2. Change `boq_header`.
3. Confirm these fields clear:

```text
boq_structure
boq_item
boq_item_stage
```

Expected alert:

```text
BOQ Structure, Item, and Stage have been cleared.
```

Then:

1. Select full BOQ chain again.
2. Change `expense_category` from `Direct` to `Indirect`.
3. Confirm all BOQ fields clear.

Expected alert:

```text
All BOQ fields have been cleared. Re-select if needed.
```

### 6.7 Test No Project Selected Behavior

1. Set Scope Context Company.
2. Set Scope Context Cost Center.
3. Clear Scope Context Project.
4. Open transaction row `boq_header` dropdown.

Expected behavior:

- BOQ Header results are not project-scoped.
- Server response exposes warning metadata:

```text
No project selected — BOQ results are not project-scoped.
```

### 6.8 Test Multi-Tab Scope Drift Guard

1. Open Purchase Invoice in Tab A.
2. Set `expense_category = Direct`.
3. Select BOQ chain.
4. Open another Desk tab, Tab B.
5. Change Scope Context Project in Tab B.
6. Return to Tab A.
7. Try to Save or Submit.

Expected:

- Save/Submit is blocked.
- Form reloads.
- User sees alert:

```text
Your scope context has changed. Reloading form to prevent invalid attribution.
```

### 6.9 Test Sales Invoice Gate

1. Open Sales Invoice.
2. In an item row, confirm the `Progress Billing` check field is available.
3. Confirm BOQ fields are hidden/read-only and their dropdowns return no options while `Progress Billing` is unchecked.
4. Check `Progress Billing`.
5. Confirm BOQ cascade fields become available.
6. Test Header → Structure → Item → Stage chain.
7. Uncheck `Progress Billing`.
8. Confirm BOQ fields clear.

### 6.10 Test Timesheet Gate

Precondition:

- Add at least one existing Employee designation to `Construction Settings → Direct Labor Designations` with `boq_requirement = Mandatory`.
- Assign that designation to an Employee.

Steps:

1. Open Timesheet.
2. Select the Employee.
3. Add a time log row.
4. Confirm hidden child-row `designation` is populated internally.
5. Confirm BOQ cascade fields become available for direct-labor designation.
6. Select BOQ chain.

If Employee designation is not in `direct_labor_designations`, BOQ fields should remain hidden/read-only.

### 6.11 Test Server Query Endpoint Directly

Run from bench:

```bash
bench --site v16.localhost execute "construction.api.boq_link_queries.get_boq_scope_token"
```

Expected:

```python
{
    "scope": {
        "company": ...,
        "cost_center": ...,
        "project": ...,
        "scope_type": ...
    },
    "scope_token": "..."
}
```

### 6.12 Run Phase 2 Query Tests

Use direct unittest execution until the unrelated `pytest` dependency issue is fixed:

```bash
bench --site v16.localhost execute "(__import__('unittest').TextTestRunner(verbosity=1).run(__import__('unittest').defaultTestLoader.loadTestsFromName('construction.tests.test_boq_link_queries')).wasSuccessful() or (_ for _ in ()).throw(Exception('tests failed')))"
```

Expected:

```text
Ran 3 tests
OK
```

## 7. Rollback Procedure

If local testing shows a blocking issue, set the feature flag back to `Off`:

```bash
bench --site v16.localhost execute "frappe.db.set_single_value('Construction Settings', 'enable_boq_cascade_filtering', 'Off')"
bench --site v16.localhost clear-cache
bench build --app construction
```

The manual rollback patch exists but should only be run intentionally:

```bash
bench --site v16.localhost execute construction.patches.v6_6.revert_boq_cascade_fields.execute
```

This hides cascade fields but preserves data.

## 8. Files Changed Or Added

Key modified files:

- `construction/install.py`
- `construction/boot.py`
- `construction/hooks.py`
- `construction/patches.txt`
- `construction/api/boq_link_queries.py`
- `construction/services/boq_accounting.py`
- `construction/public/js/boq_filters.js`
- `construction/construction/doctype/construction_settings/construction_settings.json`

Key new files:

- `construction/services/scope_resolution.py`
- `construction/services/boq_scope_filters.py`
- `construction/tests/test_boq_link_queries.py`
- `construction/patches/v6_6/add_boq_cascade_transaction_fields.py`
- `construction/patches/v6_6/revert_boq_cascade_fields.py`
- `construction/construction/doctype/direct_labor_designation/direct_labor_designation.json`
- `construction/construction/doctype/direct_labor_designation/direct_labor_designation.py`

## 9. Known Follow-Up

The standard Frappe test command should be restored by fixing or installing the missing `pytest` dependency used by an unrelated construction theme test.

Until then, BOQ query tests can be run with the direct unittest command shown above.

## 10. Recommended Next Phase

Proceed to Phase 4:

- Child-row scope defaults for `company`, `cost_center`, and `project`
- Ensure new transaction rows inherit current Scope Context consistently
- Verify no regression on existing form defaults
