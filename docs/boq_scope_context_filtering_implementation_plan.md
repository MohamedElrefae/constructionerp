# BOQ Scope Context Filtering Implementation Plan

Date: 2026-05-26  
Audience: Head of Engineering, ERP/Product Engineering, QA  
Scope: Construction app BOQ Phase 1 transaction attribution and Scope Context integration

## Executive Summary

The current BOQ Phase 1 verification relies too heavily on backend rejection:

- Try a stage from a different BOQ Item and confirm rejected.
- Try a BOQ Item from a different Project and confirm rejected.

That is necessary as a safety net, but it is not sufficient for an enterprise UX. The correct target behavior is preventive scoping: users should only see valid options in each dropdown according to the active Scope Context and the previous selections in the chain.

The proposed implementation keeps backend validation intact, but moves most data-quality prevention earlier into the user flow:

Company -> Cost Center -> Project -> BOQ Header -> BOQ Structure -> BOQ Item -> BOQ Item Stage

This reduces ambiguity, improves performance on large datasets, and prevents improper assignments before save.

## Revision Directive Summary

The following decisions are approved and incorporated into this plan:

- The `Prevent First, Reject Last` design principle remains mandatory.
- Backend validation remains the final integrity layer.
- The approved cascade is Company -> Cost Center -> Project -> BOQ Header -> BOQ Structure -> BOQ Item -> BOQ Item Stage.
- `boq_header` and `boq_structure` will be added as operational transaction child fields.
- `boq_item` remains the only Phase 1 accounting dimension.
- `boq_structure` queries must return leaf nodes only with `is_group = 0`.
- BOQ Header status handling must use one shared constant, not repeated string literals.
- Index creation is part of the migration, not a deferred optimization.
- A rollout feature flag is mandatory: `Construction Settings.enable_boq_cascade_filtering` with `Off`, `On`, and `Strict`.
- `Sales Invoice Item` uses `is_progress_billing` as the cascade gate, not `expense_category`.
- Scope-token drift protection must use SHA-256 and include the `User Scope Context.modified` timestamp.
- A rollback patch is required before deployment.

## Mandatory Pre-Implementation Conditions

Implementation may start only after the plan and first implementation commit include:

1. Replace MD5 scope token hashing with SHA-256 and include `modified` in the payload.
2. Add `BOQ_CASCADE_INSERT_AFTER` per-DocType map in `install.py`.
3. Add `Construction Settings.enable_boq_cascade_filtering` with `Off`, `On`, `Strict`, default `Off`.
4. Add `read_only_depends_on` to all BOQ cascade fields.
5. Add pre-save `guardSaveAgainstScopeDrift(frm)` in `boq_filters.js`, covering save and submit.
6. Add rollback patch `construction/patches/v6_6/revert_boq_cascade_fields.py`.
7. Add `EXCLUDED_TRANSACTION_BOQ_STATUSES` companion constant.
8. Split scope logic into `scope_resolution.py` and `boq_scope_filters.py`.
9. Add `BOQ_CASCADE_DEPENDS_ON` per-DocType map; `Sales Invoice Item` must use `eval:doc.is_progress_billing`.

## Current State

### Existing Scope Context

The app already has a Scope Context layer:

- `construction/public/js/scope_context.js`
- `construction/public/js/scope_context_ui.js`
- `construction/public/js/scope_context_form_defaults.js`
- `construction/api/scope_context_api.py`
- `construction/overrides/scope_query.py`
- `construction/overrides/scope_enforcement.py`
- `construction/boot.py`

Current behavior:

- The user selects Company, Cost Center, Project, and Department in the top bar.
- Cost Centers are filtered by Company.
- Projects are filtered by Company and selected Cost Center including descendant cost centers.
- New forms receive defaults for matching standard fields.
- List/query permissions are partially scope-filtered when the target DocType has matching columns.

### Existing BOQ Link Filtering

The app already has a BOQ link query module:

- `construction/api/boq_link_queries.py`

Current behavior:

- `get_boq_headers` supports filtering by Project.
- `get_boq_structures` supports filtering by BOQ Header.
- `get_boq_items` supports filtering by Project, BOQ Header, Structure, and allowed BOQ Header statuses.
- `get_boq_item_stages` supports filtering by BOQ Item.

The transaction UI hook exists here:

- `construction/public/js/boq_filters.js`

Current behavior:

- On transaction child rows, `boq_item` is filtered by row/project or parent project.
- `boq_item_stage` is filtered by selected `boq_item`.
- If `expense_category` is not `Direct`, BOQ fields are cleared.
- If `boq_item` is cleared, `boq_item_stage` is cleared.

### Existing Backend Validation

Backend validation exists here:

- `construction/services/boq_accounting.py`
- `construction/services/boq_transaction_validation.py`

Current behavior:

- Rejects `boq_item_stage` without `boq_item`.
- Rejects missing or invalid BOQ Item.
- Rejects attribution to Draft/Pricing BOQ Headers.
- Rejects BOQ Project mismatch with transaction Project.
- Rejects BOQ Item Stage that does not belong to selected BOQ Item.

This backend validation must remain. The change requested is not to remove rejection; it is to prevent invalid selections from appearing.

## Problem Statement

The current UX lets users search a broad BOQ Item set and relies on backend validation to reject invalid combinations. In an enterprise app, this is suboptimal because:

- Users can select data outside their active working scope.
- Dropdowns can show too many irrelevant records.
- Errors appear late, only after save.
- The system encourages trial-and-error instead of guided data entry.
- Large deployments will suffer from noisy search results and slower selection.

The target model must be guided, hierarchical, and deterministic.

## Target Enterprise Behavior

The expected user flow is:

1. User selects Company in Scope Context.
2. Cost Center dropdown shows only cost centers linked to the selected Company.
3. User selects Cost Center.
4. Project dropdown shows only projects linked to selected Company and selected Cost Center, including configured descendant Cost Centers where applicable.
5. User selects Project.
6. Transaction form defaults Company/Project where available.
7. BOQ Header dropdown shows only BOQ Headers linked to selected Project.
8. BOQ Structure dropdown shows only leaf BOQ Structures linked to selected BOQ Header.
9. BOQ Item dropdown shows only BOQ Items linked to selected BOQ Header and selected BOQ Structure.
10. BOQ Item Stage dropdown shows only stages linked to selected BOQ Item.
11. When an upstream selection changes, downstream values are cleared if no longer valid.
12. Backend validation still rejects any invalid values introduced through API/import/concurrency.

## Design Principles

### Prevent First, Reject Last

Dropdown filtering is the primary user-facing control. Backend rejection remains the final integrity layer.

### Scope Context Is the Source of User Intent

The top-bar Scope Context should drive form defaults and BOQ dropdowns. Transaction row fields should not independently bypass the active scope.

### Cascading Filters Must Be Explicit

Each link field query must receive all relevant upstream keys, not infer weakly from only one field.

### No Silent Cross-Scope Attribution

If a user changes Company, Cost Center, Project, BOQ Header, BOQ Structure, or BOQ Item, stale downstream values must be cleared.

### Server-Side Queries Must Enforce the Same Scope

Client filters improve UX, but whitelisted query methods must also apply scope constraints based on the user session/defaults.

## Proposed Architecture

### 1. Shared Scope Resolution And Filter Builders

Create two reusable server-side helper modules for BOQ queries:

Proposed file:

- `construction/services/scope_resolution.py`
- `construction/services/boq_scope_filters.py`

`scope_resolution.py` responsibilities:

- Read active user scope from `User Scope Context` or session defaults.
- Resolve descendant cost centers for selected cost center.
- Compute deterministic scope tokens.
- Expose pure Python helpers that can be tested without SQL string assertions.

`boq_scope_filters.py` responsibilities:

- Build safe SQL conditions for:
  - Company
  - Cost Center
  - Project
  - BOQ Header
  - BOQ Structure
  - BOQ Item
- Normalize and validate incoming filter values.
- Expose canonical active scope metadata for client-side drift checks.

This avoids duplicating hierarchy logic across whitelisted query methods.

Approved status constants:

```python
# Statuses approved for cost attribution on transactions.
# Draft/Pricing: not yet finalized - attribution not permitted.
# Closed: no further transactions allowed per business rule.
ALLOWED_TRANSACTION_BOQ_STATUSES = ["Locked", "Frozen"]
EXCLUDED_TRANSACTION_BOQ_STATUSES = ["Draft", "Pricing", "Closed"]
```

This constant must be imported anywhere BOQ transaction eligibility is evaluated. Inline status string checks are not allowed in the BOQ transaction attribution pipeline.

Scope token behavior:

```python
def get_scope_token(user):
    """Return a deterministic token representing the user's active scope.

    Includes the User Scope Context modified timestamp so in-place updates
    invalidate the token even when values are rewritten to the same fields.
    """
    scope = frappe.db.get_value(
        "User Scope Context",
        {"user": user},
        ["company", "cost_center", "project", "modified"],
        as_dict=True,
    )
    if not scope:
        return None
    payload = f"{scope.company}|{scope.cost_center}|{scope.project}|{scope.modified}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]
```

Implementation note: Frappe standard Link query methods are expected to return row tuples. Returning metadata in the same payload can break Link controls. To preserve the directive without breaking Frappe's Link API contract, the implementation must provide a lightweight `get_boq_scope_token` endpoint and compare that token before/rebinding BOQ queries. If a custom link control path later supports metadata responses safely, the same token may also be returned with those custom responses.

SQL security rule:

- New SQL-aware helpers must use dict parameter binding with `%(key)s`.
- Do not construct user-controlled predicates with f-string interpolation.
- `frappe.db.escape()` is acceptable for existing permission-query hook fragments, but BOQ whitelisted query methods must follow parameter binding.

### 2. Harden BOQ Link Query APIs

Update:

- `construction/api/boq_link_queries.py`

Required behavior:

- `get_boq_headers` filters by Project and active Scope Context.
- `get_boq_structures` requires or strongly prefers BOQ Header and filters leaf structures only.
- `get_boq_items` filters by active scope, BOQ Header, BOQ Structure, Project, and allowed statuses.
- `get_boq_item_stages` filters by BOQ Item, and optionally validates that the BOQ Item is still inside active scope.

Server query methods must not trust client-provided filters alone.

### 3. Add Transaction BOQ Cascade UI Controller

Replace or expand:

- `construction/public/js/boq_filters.js`

Target behavior:

- Derive effective scope from `window.scopeContext.getCurrentScope()`.
- Track the last known server scope token.
- Refresh the server scope token before or during BOQ query rebinding.
- If the token differs from the last known token, run `rebindOnScopeChange()` and refresh BOQ query bindings.
- Before save or submit, run `guardSaveAgainstScopeDrift(frm)`.
- If pre-save scope drift is detected, show a non-blocking alert, reload the form, and reject the save/submit attempt before a failed backend validation creates poor UX.
- Derive row Project from row or parent document.
- Prefer active Scope Context Project over empty form state.
- Add `get_query` for all BOQ fields that exist on the current form/child table.
- Clear downstream fields on upstream changes.
- Reapply queries on:
  - `setup`
  - `refresh`
  - row render
  - `scope:changed`
  - parent `company`, `cost_center`, `project`
  - child row `project`, `boq_header`, `boq_structure`, `boq_item`

Accessibility:

- Cascade clear notices must render in an `aria-live="polite"` region.
- Notices must stay visible for at least 5 seconds.
- Use `frm.dashboard.add_comment()` or `frappe.show_alert()` for non-blocking guidance.
- Do not use `frappe.msgprint()` for routine scope warnings.

### 4. Add Missing Cascade Fields Where Needed

Current Phase 1 child rows contain:

- `boq_item`
- `boq_item_stage`
- `expense_category`

The requested cascade includes:

- BOQ Header
- BOQ Structure
- BOQ Item
- BOQ Item Stage

Approved enterprise option:

- Add `boq_header` and `boq_structure` as optional operational fields before `boq_item`.
- Keep `boq_item` as the accounting dimension.
- Keep `boq_header` and `boq_structure` as operational helper fields only, not accounting dimensions.

Rationale:

- Users asked for explicit BOQ Header and BOQ Structure dropdowns.
- It gives a clear cascade and smaller dropdowns.
- It avoids forcing users to search all items under a project.
- It supports large BOQs better.

Proposed child field order:

1. `expense_category`
2. `boq_header`
3. `boq_structure`
4. `boq_item`
5. `boq_item_stage`

If existing layout requires keeping `expense_category` after BOQ fields, the dependency logic can still work, but the recommended UX is category first.

### 5. Keep Backend Validation Authoritative

Enhance:

- `construction/services/boq_accounting.py`

Validation should check:

- BOQ Header belongs to selected/active Project.
- BOQ Structure belongs to BOQ Header.
- BOQ Item belongs to BOQ Header.
- BOQ Item belongs to BOQ Structure when Structure is provided.
- BOQ Item Stage belongs to BOQ Item.
- Transaction Project matches BOQ Header Project.
- Transaction Company/Cost Center remain inside active Scope Context when relevant.

Backend validation must cover:

- Manual API insert.
- Data import.
- Background integrations.
- Race conditions where BOQ records change after form load.

## Detailed Implementation Plan

### Phase 0: Engineering Decisions

Resolved decisions before implementation:

- Transaction child rows will get `boq_header` and `boq_structure` fields.
- Transaction child rows will also get hidden `boq_selection_scope_type` for audit.
- `boq_item` remains the only Phase 1 accounting dimension.
- `boq_structure` will show leaf nodes only with `is_group = 0`.
- Selected Cost Center will include descendant Cost Centers for Project and BOQ scoping.
- Allowed BOQ Header statuses are `Locked` and `Frozen`, defined by `ALLOWED_TRANSACTION_BOQ_STATUSES`.
- Transaction child doctypes receiving the cascade remain the existing BOQ Phase 1 doctypes unless a specific DocType is unavailable on the installed ERPNext version.
- `Journal Entry Account` will receive `expense_category` as a custom field, inserted after `account`, with blank default.
- `Timesheet Detail` will not use `expense_category`; its BOQ visibility/mandatory behavior is designation-based.
- `Sales Invoice Item` BOQ cascade is intentional for progress billing and must be gated by `is_progress_billing`.

No-project behavior is now fixed:

```text
IF project is empty in active Scope Context:
    BOQ Header query filters by Company + Cost Center only.
    The form displays a visible warning:
    "No project selected - BOQ results are not project-scoped."

IF project is set in active Scope Context:
    BOQ Header query filters strictly by Project.
    No warning is displayed.
```

This behavior must be implemented explicitly in:

- `construction/public/js/boq_filters.js`
- `construction/services/boq_scope_filters.py`

### Phase 1: Data Model and Custom Fields

Update:

- `construction/install.py`
- `construction/construction/doctype/construction_settings/construction_settings.json`

Add feature flag:

- Field: `enable_boq_cascade_filtering`
- Type: `Select`
- Options: `Off\nOn\nStrict`
- Default: `Off`
- Behavior:
  - `Off`: Fields exist but cascade controller is disabled; backend validation remains existing-safe.
  - `On`: Preventive dropdown filtering and warnings enabled; backend remains final integrity layer.
  - `Strict`: All `On` behavior plus stricter mandatory enforcement after data quality gate passes.

Expose via:

- `construction/boot.py` as `frappe.boot.enable_boq_cascade_filtering`

Add operational custom fields:

- `boq_header`
  - Type: Link
  - Options: `BOQ Header`
  - Depends on: per-DocType gate from `BOQ_CASCADE_DEPENDS_ON`
  - Read-only depends on: inverse of the same gate or missing upstream dependency
- `boq_structure`
  - Type: Link
  - Options: `BOQ Structure`
  - Depends on: selected `boq_header` and per-DocType gate
  - Read-only depends on: missing `boq_header` or inactive gate
- Keep `boq_item`
  - Depends on: selected `boq_structure` and per-DocType gate
  - Read-only depends on: missing `boq_structure` or inactive gate
- Keep `boq_item_stage`
  - Depends on: selected `boq_item` and per-DocType gate
  - Read-only depends on: missing `boq_item` or inactive gate
- Add hidden `boq_selection_scope_type`
  - Type: Select
  - Hidden: 1
  - Options: blank, `Project-Scoped`, `Company-CostCenter-Scoped`
  - Purpose: audit trail for whether the BOQ chain was selected under strict project scope or broader company/cost-center scope.

Required placement map:

```python
BOQ_CASCADE_INSERT_AFTER = {
    "Purchase Order Item": "expense_category",
    "Purchase Receipt Item": "expense_category",
    "Purchase Invoice Item": "expense_category",
    "Stock Entry Detail": "expense_category",
    "Timesheet Detail": "activity_type",
    "Journal Entry Account": "account",
    "Sales Invoice Item": "is_progress_billing",
    "Material Request Item": "expense_category",
}
```

Required gate map:

```python
BOQ_CASCADE_DEPENDS_ON = {
    "Purchase Order Item": "eval:doc.expense_category == 'Direct'",
    "Purchase Receipt Item": "eval:doc.expense_category == 'Direct'",
    "Purchase Invoice Item": "eval:doc.expense_category == 'Direct'",
    "Stock Entry Detail": "eval:doc.expense_category == 'Direct'",
    "Journal Entry Account": "eval:doc.expense_category == 'Direct'",
    "Material Request Item": "eval:doc.expense_category == 'Direct'",
    "Sales Invoice Item": "eval:doc.is_progress_billing",
    "Timesheet Detail": "eval:frappe.boot.direct_labor_designations && frappe.boot.direct_labor_designations.includes(doc.designation)",
}
```

Notes:

- `Sales Invoice Item` must not be gated by `expense_category`.
- If `Sales Invoice Item.is_progress_billing` is not already present, Phase 1 must provision it as a Check custom field before the BOQ cascade fields.
- `Journal Entry Account` gets `expense_category` because JEs are mixed-purpose and the accountant must explicitly mark direct-cost rows.
- `Timesheet Detail` does not get `expense_category`; direct-labor obligation is designation-based.
- Generic `_resolve_insert_after` must not be used for cascade field placement.

Direct labor settings:

- Add a child table in `Construction Settings`: `Direct Labor Designations`.
- Seed default designations such as Site Worker, Mason, Carpenter, Steel Fixer, Operator, Electrician, and Plumber as mandatory direct labor.
- Expose `frappe.boot.direct_labor_designations`.

Add migration patch:

- `construction/patches/v6_6/add_boq_cascade_transaction_fields.py`
- `construction/patches/v6_6/revert_boq_cascade_fields.py`

Patch responsibilities:

- Run `setup_boq_custom_fields()`.
- Add required BOQ cascade indexes.
- Add feature flag and direct labor settings metadata.
- Clear DocType caches for affected child doctypes.
- Commit idempotently.

Rollback patch responsibilities:

- Remove or disable cascade custom fields created by `v6_6`.
- Preserve existing `boq_item` accounting-dimension behavior unless explicitly approved otherwise.
- Be idempotent and safe to run if some fields are already absent.

Required indexes in the same migration:

| Table | Index Columns | Rule |
|---|---|---|
| `BOQ Header` | `project` | Add always |
| `BOQ Structure` | `boq_header, is_group` | Add always - used in every leaf query |
| `BOQ Item` | `boq_header, structure` | Add always - composite filter on every row |
| `BOQ Item Stage` | `boq_item` | Add always |

### Phase 2: Server Query Hardening

Update:

- `construction/api/boq_link_queries.py`

Add or update APIs:

- `get_boq_headers`
- `get_boq_structures`
- `get_boq_items`
- `get_boq_item_stages`

Add helper:

- `construction/services/boq_scope_filters.py`

Required constants and functions:

- `ALLOWED_TRANSACTION_BOQ_STATUSES`
- `EXCLUDED_TRANSACTION_BOQ_STATUSES`
- `get_scope_token(user)`
- `get_current_scope(user)`
- `get_descendant_cost_centers(cost_center)`
- `get_boq_cascade_mode()`
- `build_boq_header_conditions(filters, user)`
- `build_boq_structure_conditions(filters, user)`
- `build_boq_item_conditions(filters, user)`
- `build_boq_item_stage_conditions(filters, user)`

Required feature-flag pattern:

```python
try:
    cascade_mode = frappe.db.get_single_value(
        "Construction Settings", "enable_boq_cascade_filtering"
    ) or "Off"
except Exception:
    cascade_mode = "Off"
```

Query APIs should accept `enforce_scope=True` for external integration compatibility. If `enforce_scope=False` is used, log a deprecation warning and still apply permission checks appropriate to the user. This bypass must not be available in `Strict` mode.

Expected filtering:

#### BOQ Header

Filters:

- `docstatus < 2`
- If active scope has project, enforce that project strictly.
- If active scope project is empty, filter by active Company + Cost Center.
- If active scope has company/cost center, enforce through linked Project.
- Status in allowed transaction statuses when used from transaction forms.
- No-project mode must be visible to the user through the client warning.

#### BOQ Structure

Filters:

- `docstatus < 2`
- `is_group = 0`
- `boq_header = selected_boq_header`
- BOQ Header must still be in active scope.

#### BOQ Item

Filters:

- `docstatus < 2`
- `boq_header = selected_boq_header`
- `structure = selected_boq_structure`
- BOQ Header Project in active scope.
- BOQ Header status in `ALLOWED_TRANSACTION_BOQ_STATUSES`.

#### BOQ Item Stage

Filters:

- `docstatus < 2`
- `boq_item = selected_boq_item`
- BOQ Item -> BOQ Header -> Project in active scope.

Scope drift protection:

- The server computes a canonical scope token from `User Scope Context`.
- The client stores the last known token.
- Before/rebinding BOQ queries, the client calls the lightweight token endpoint.
- If the token differs, the client runs `rebindOnScopeChange()`, clears stale downstream BOQ fields where necessary, and refreshes queries.
- Link query methods must still enforce canonical server scope even if the client token is stale.
- Pre-save guard is mandatory because token polling alone does not close the multi-tab save race.

### Phase 3: Client Cascade Controller

Update:

- `construction/public/js/boq_filters.js`

Required functions:

- `getActiveScope()`
- `getEffectiveCompany(frm, row)`
- `getEffectiveCostCenter(frm, row)`
- `getEffectiveProject(frm, row)`
- `getLastKnownScopeToken()`
- `refreshScopeTokenAndRebindIfNeeded(frm)`
- `fetchScopeToken()`
- `guardSaveAgainstScopeDrift(frm)`
- `setChildQueries(frm, tableField)`
- `clearDownstream(cdt, cdn, changedField)`
- `showBoqScopeWarning(frm, message)`
- `showRowCascadeNotice(frm, cdt, cdn, message)`
- `validateVisibleDependencies(frm, tableField, cdt, cdn)`
- `rebindOnScopeChange()`

Required save/submit guard:

```javascript
async function guardSaveAgainstScopeDrift(frm) {
    const currentToken = await fetchScopeToken();
    if (currentToken && currentToken !== lastKnownScopeToken) {
        frappe.show_alert({
            message: __("Your scope context has changed. Reloading form to prevent invalid attribution."),
            indicator: "orange",
        });
        frm.reload_doc();
        return Promise.reject("scope_drift");
    }
}
```

This guard must wrap save and submit for all transaction doctypes covered by the cascade. The implementation must avoid infinite recursion when wrapping Frappe form methods.

Required `get_query` behavior:

- `boq_header`
  - Filters by effective Project and active Scope Context.
  - If active Scope Project is empty, filters by Company + Cost Center and shows: "No project selected - BOQ results are not project-scoped."
- `boq_structure`
  - Filters by selected BOQ Header.
- `boq_item`
  - Filters by selected BOQ Header and BOQ Structure.
- `boq_item_stage`
  - Filters by selected BOQ Item.

Required clearing behavior:

- Change Company: clear Cost Center, Project, BOQ Header, BOQ Structure, BOQ Item, BOQ Item Stage.
- Change Cost Center: clear Project if no longer valid; clear BOQ cascade.
- Change Project: clear BOQ Header, BOQ Structure, BOQ Item, BOQ Item Stage.
- Change BOQ Header: clear BOQ Structure, BOQ Item, BOQ Item Stage, then show row-level notice: "BOQ Structure, Item, and Stage have been cleared."
- Change BOQ Structure: clear BOQ Item, BOQ Item Stage.
- Change BOQ Item: clear BOQ Item Stage.
- Change Expense Category away from `Direct`: clear all BOQ fields, then show row-level notice: "All BOQ fields have been cleared. Re-select if needed."
- For `Sales Invoice Item`, changing `is_progress_billing` to false clears all BOQ fields and shows the same all-fields-cleared notice.
- For `Timesheet Detail`, changing employee/designation out of direct-labor eligibility clears all BOQ fields and shows the same all-fields-cleared notice.

Clearing is irreversible:

- The client must not implement undo.
- The client must not silently restore previously cleared BOQ values when the upstream value is reselected.
- Users must reselect the cascade from the first valid field.

### Phase 4: Parent Form Defaults

Update:

- `construction/public/js/scope_context_form_defaults.js`

Current behavior defaults only parent fields that exist. Add support for common child-row defaults when new rows are created:

- If child row has `project`, default from active Scope Context Project.
- If child row has `cost_center`, default from active Scope Context Cost Center.
- If child row has `company`, default from parent Company or active Scope Context Company.

This should be conservative and not overwrite user-entered values.

### Phase 5: Backend Validation Enhancements

Update:

- `construction/services/boq_accounting.py`

Add validation for optional new fields:

- If `boq_structure` exists, `boq_header` is required.
- If `boq_item` exists and `boq_header` exists, item header must match.
- If `boq_item` exists and `boq_structure` exists, item structure must match.
- If `boq_item_stage` exists, selected stage must match item.
- If transaction Project exists, BOQ Header Project must match.
- If active Scope Context exists, selected BOQ chain must be within scope unless user is Administrator or feature disabled.
- BOQ Header status validation must use `ALLOWED_TRANSACTION_BOQ_STATUSES`.
- Draft, Pricing, and Closed BOQ Headers must not be accepted for transaction attribution.
- Populate or validate `boq_selection_scope_type`.
- Structured backend rejection logging is required before `Strict` mode:

```python
frappe.logger("boq_validation").warning({
    "event": "boq_backend_rejection",
    "user": frappe.session.user,
    "doctype": parent_doc.doctype,
    "row": row.idx,
    "reason": reason,
})
```

Timesheet direct labor rule:

- If employee designation is in `Direct Labor Designations`, `boq_item` is mandatory.
- If employee designation is optional or not configured, BOQ attribution remains optional unless another rule requires it.

Sales Invoice progress billing rule:

- If `is_progress_billing` is true, BOQ cascade fields are visible and attribution is mandatory according to billing policy.
- If `is_progress_billing` is false, BOQ fields must clear and remain hidden/read-only.

### Phase 6: Tests

Add or update tests:

- `construction/tests/test_boq_link_queries.py`
- `construction/tests/test_boq_scope_cascade.py`
- `construction/tests/test_boq_transaction_validation.py`
- `construction/tests/test_scope_context.py`

Minimum test cases:

- Company A scope does not return Project from Company B.
- Cost Center parent scope returns Projects under descendant Cost Centers.
- Project A scope returns only BOQ Headers for Project A.
- BOQ Header A returns only leaf structures under Header A.
- BOQ Structure A returns only BOQ Items linked to Structure A.
- BOQ Item A returns only stages linked to Item A.
- Changing BOQ Header clears Structure/Item/Stage.
- Changing BOQ Structure clears Item/Stage.
- Changing BOQ Item clears Stage.
- Backend still rejects API-created cross-project BOQ Item.
- Backend still rejects stage from different BOQ Item.
- Backend rejects API-created row with valid `boq_item` but mismatched `boq_structure`.
- No-project active scope returns BOQ Headers scoped by Company + Cost Center only.
- Project active scope returns BOQ Headers scoped strictly by Project.
- Scope token mismatch triggers query rebind and stale BOQ values are cleared where necessary.
- SHA-256 scope token changes when `User Scope Context.modified` changes.
- `Sales Invoice Item` cascade is visible only when `is_progress_billing` is true.
- `Journal Entry Account` cascade is visible only when `expense_category == 'Direct'`.
- `Timesheet Detail` cascade follows direct labor designation rules.
- `Off` mode disables preventive cascade UI.
- `On` mode enables preventive cascade UI and backend final validation.
- `Strict` mode refuses approved bypasses and requires data-quality gate success.
- Revert patch can be run idempotently.

Manual QA scenarios:

- Purchase Invoice item row full cascade.
- Purchase Order item row full cascade.
- Subcontract Invoice item row full cascade if the DocType exists in the installed ERPNext scope.
- Journal Entry account row full cascade.
- Timesheet row full cascade.
- Material Request item row full cascade.
- Scope Context changed while form is open.
- User changes Scope Context Project while a Purchase Invoice is open mid-entry.
- User has Company only, no Project selected.
- User has Company + Cost Center, no Project selected.
- User has Project selected.
- User sets `expense_category = Direct`, selects full BOQ chain, then changes to `expense_category = Indirect`; confirm all BOQ fields clear and switching back to `Direct` starts from empty state.
- API-level insert with valid `boq_item` but mismatched `boq_structure`; confirm backend rejects.
- Sales Invoice progress billing row full cascade.
- Sales Invoice non-progress-billing row hides and clears BOQ fields.
- Journal Entry Account row with blank `expense_category` hides BOQ fields.
- Journal Entry Account row with `expense_category = Direct` enables BOQ cascade.
- Timesheet row for configured direct-labor designation requires BOQ Item.
- Timesheet row for non-direct designation does not force BOQ Item.

### Phase 6.5: Data Quality Gate

Before enabling `Strict`, run a data quality gate.

Initial implementation:

- Python script or bench-executable function.
- Frappe Report DocType can follow in a later sprint.

Required checks:

- Transaction rows with `boq_item` but missing/mismatched `boq_header`.
- Transaction rows with `boq_item` but missing/mismatched `boq_structure`.
- Transaction rows with `boq_item_stage` not belonging to `boq_item`.
- BOQ Items whose Header Project does not match transaction Project.
- Sales Invoice progress-billing rows missing BOQ attribution.
- Direct-labor Timesheet rows missing BOQ attribution.

Severity:

- `CRITICAL`: data would be rejected in `Strict`.
- `WARNING`: data is valid but not ideal for reporting.

Gate rule:

- `Strict` mode cannot be enabled until the data quality gate returns zero `CRITICAL` findings.

### Phase 6.6: Performance SLI Tests

Add local seed-based performance tests before full rollout. Locust is not required for the first implementation.

Proposed file:

- `construction/tests/load/test_boq_cascade_load.py`

SLI targets:

| Metric | Target | Test Dataset |
|---|---|---|
| BOQ Header dropdown query | `< 300 ms` | 5,000 BOQ Headers |
| BOQ Item dropdown query | `< 300 ms` | 50,000 BOQ Items |
| Scope token endpoint | `< 50 ms` | Any active user |
| Save validation for 100 rows | `< 200 ms` | Seed transaction document |

Gate rule:

- These tests must pass locally before the `On` flag is enabled site-wide.
- Run the same suite against an anonymized production copy before `Strict`.

### Phase 7: Migration and Deployment

Deployment steps:

1. Merge implementation branch only after plan sign-off.
2. Run migration on target site with flag defaulting to `Off`.
3. Confirm patch `v6_6` executed.
4. Confirm rollback patch exists and is idempotent in test.
5. Clear Frappe cache.
6. Confirm custom fields exist on target transaction child doctypes.
7. Confirm queries return scoped results in development with `On`.
8. Run automated tests.
9. Run manual QA scenarios.
10. Run data quality and performance gates before rollout escalation.

Mandatory rollout sequence:

| Phase | Action | Gate |
|---|---|---|
| Migration | Run `v6_6`; fields hidden; flag `Off` | Patch idempotency test passes |
| Pilot On | Set flag `On` for pilot user group or pilot site | Monitor `boq_validation` log for 48 hours |
| Full On | Enable flag `On` site-wide | Zero backend rejections in pilot window |
| Strict | Set flag `Strict` | Data Quality Gate passes and 48-hour zero-rejection window under `On` |

Commands:

```bash
bench --site <site> migrate
bench --site <site> clear-cache
bench --site <site> execute construction.install.setup_boq_integration
bench --site <site> run-tests --app construction --module construction.tests.test_boq_transaction_validation
```

## Acceptance Criteria

The implementation is approved when:

- BOQ Header dropdown only shows headers for the selected Scope Project.
- If no Scope Project is selected, BOQ Header dropdown is scoped by Company + Cost Center and the warning is visible.
- BOQ Structure dropdown only shows leaf structures for the selected BOQ Header.
- BOQ Item dropdown only shows items for selected BOQ Header and BOQ Structure.
- BOQ Item Stage dropdown only shows stages for selected BOQ Item.
- Changing any upstream value clears invalid downstream values.
- Backend validation still rejects invalid cross-chain values.
- Query methods enforce scope server-side, not only in JavaScript.
- Existing Scope Context top-bar behavior remains unchanged.
- Existing wildcard scope validation hook remains registered.
- Scope token drift between tabs causes BOQ query rebinding.
- Pre-save scope drift guard blocks stale save/submit and reloads the form.
- Cascade clearing notices are displayed and cleared values are not restored automatically.
- Sales Invoice progress billing uses `is_progress_billing`; it never depends on `expense_category`.
- Timesheet direct labor mandatory behavior follows configured designations.
- Rollout flag supports `Off`, `On`, and `Strict`.
- Performance remains acceptable with large BOQs.

## Engineering Risks

### Risk: Too Many Custom Fields on ERPNext Child Tables

Impact: Medium  
Mitigation: Make fields operational and optional. Each DocType uses its own visibility gate defined in `BOQ_CASCADE_DEPENDS_ON`. Fields are hidden when the gate condition is not met.

### Risk: Query Performance on Large BOQs

Impact: Medium  
Mitigation: Add these indexes in the `v6_6` migration:

- `BOQ Header.project`
- `BOQ Structure.boq_header, is_group`
- `BOQ Item.boq_header, structure`
- `BOQ Item Stage.boq_item`

These indexes are mandatory for the approved cascade. The migration should be idempotent and tolerate an index that already exists.

### Risk: Scope Context Local Storage Drift

Impact: Medium  
Mitigation: Server query methods must read canonical scope/session defaults and enforce them. The client must also compare a server scope token against the last known token and rebind BOQ queries when the token changes.

### Risk: Existing Data Has Incomplete Project/Cost Center Links

Impact: High  
Mitigation: Add a data quality report before enforcing strict filtering in production.

### Risk: Users Need to Work Without Project Selected

Impact: Medium  
Mitigation: This behavior is approved. When Project is empty, BOQ Header results are scoped by Company + Cost Center and the form displays: "No project selected - BOQ results are not project-scoped."

### Risk: Sales Invoice BOQ Attribution Hidden By Wrong Gate

Impact: High  
Mitigation: `Sales Invoice Item` uses `is_progress_billing`, not `expense_category`, for visibility/read-only/mandatory behavior.

### Risk: Timesheet Users Bypass BOQ By Choosing Indirect Category

Impact: High  
Mitigation: `Timesheet Detail` uses designation-based direct labor rules from `Construction Settings`, not manual `expense_category`.

### Risk: Full Cascade Rollout Requires Emergency Disable

Impact: High  
Mitigation: Feature flag defaults to `Off`, supports `On` and `Strict`, and a rollback patch is delivered with the migration.

## Recommended Approval Decision

Approve implementation with the following engineering decisions:

- Add `boq_header` and `boq_structure` operational child fields.
- Keep `boq_item` as the only Phase 1 accounting dimension.
- Keep backend rejection validation as final protection.
- Implement server-side scoped query enforcement.
- Implement client-side cascade clearing and dropdown filtering.
- Add automated tests before cloud deployment.

## Out of Scope

- Making `BOQ Item Stage` an accounting dimension.
- Changing GL posting logic.
- Replacing ERPNext Accounting Dimension behavior.
- Removing backend validation.
- Full redesign of Scope Context UI.
- Real-time collaborative editing.
- Offline/mobile-first BOQ cascade support. Standard responsive behavior remains required, but offline conflict resolution is not part of this phase.
- Building the full Frappe Report DocType for data quality in the first implementation. Start with script/check first.

## Files Expected To Change

Implementation files:

- `construction/install.py`
- `construction/api/boq_link_queries.py`
- `construction/services/scope_resolution.py`
- `construction/services/boq_scope_filters.py`
- `construction/services/boq_accounting.py`
- `construction/services/boq_transaction_validation.py`
- `construction/public/js/boq_filters.js`
- `construction/public/js/scope_context_form_defaults.js`
- `construction/boot.py`
- `construction/construction/doctype/construction_settings/construction_settings.json`
- `construction/patches.txt`
- `construction/patches/v6_6/add_boq_cascade_transaction_fields.py`
- `construction/patches/v6_6/revert_boq_cascade_fields.py`

Test files:

- `construction/tests/test_boq_link_queries.py`
- `construction/tests/test_boq_scope_cascade.py`
- `construction/tests/test_boq_transaction_validation.py`
- `construction/tests/test_scope_context.py`
- `construction/tests/load/test_boq_cascade_load.py`

Data quality files:

- `construction/scripts/boq_data_quality_check.py`
- `construction/construction/report/boq_data_quality_report/` in a follow-on sprint if approved.

Documentation:

- `docs/boq_scope_context_filtering_implementation_plan.md`
