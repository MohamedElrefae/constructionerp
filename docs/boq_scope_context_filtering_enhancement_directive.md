# Engineering Directive — Enhancements to BOQ Scope Context Filtering Implementation Plan

**To:** Implementation Agent  
**From:** Software Consultant — Architecture, Security & Operational Readiness  
**Date:** 2026-05-26  
**Re:** Approved with Mandatory Revisions to `boq_scope_context_filtering_implementation_plan.md`

---

The cascade UX design in your plan is solid. The "Prevent First, Reject Last" principle is the correct enterprise posture, and the approved chain (Company → Cost Center → Project → BOQ Header → BOQ Structure → BOQ Item → BOQ Item Stage) is logically sound.

However, **do not begin implementation until the following revisions are incorporated into the plan document.** The gaps below are operational, security, and production-readiness issues that cause "successful implementation, failed deployment" scenarios in ERP customizations. I have grouped them by the section they belong in.

---

## 1. Add New Section: Phase 0 — Engineering Decisions (Continued)

Insert the following sub-section immediately after the existing "No-project behavior" block:

### Feature Flag and Rollback Strategy

All cascade functionality must be gated by a new single-document setting:

- **Path:** `Construction Settings.enable_boq_cascade_filtering`
- **Type:** Select
- **Options:** `Off` \n `On` \n `Strict`
- **Default:** `Off`

| State | Behavior |
|-------|----------|
| `Off` | Backend validation only (preserves current behavior). Client-side cascade UI is dormant. |
| `On` | Full client-side cascade filtering + backend validation. |
| `Strict` | Full client-side cascade + backend rejects any row where `boq_header` / `boq_structure` / `boq_item` / `boq_item_stage` chain is invalid or out of active scope. |

**Implementation requirement:**
- Read this flag in `frappe.boot` so `boq_filters.js` can check `frappe.boot.enable_boq_cascade_filtering` before registering cascade handlers.
- Read this flag server-side in `boq_scope_filters.py` and `boq_accounting.py`.
- The `scope_enforcement.py` pattern (try/except around `Construction Settings` with graceful fallback to `enabled = False`) must be replicated exactly.

**Rollback procedure (add to Phase 7):**
1. Patch `construction/patches/v6_6/revert_boq_cascade_fields.py` must be written and tested before deployment.
2. The patch marks `boq_header` and `boq_structure` fields as hidden via Property Setter; it does not delete data.
3. Idempotency: running the patch twice must not error.

---

## 2. Revise Section: Phase 0 — Engineering Decisions

Replace the `ALLOWED_TRANSACTION_BOQ_STATUSES` constant definition with this exact version:

```python
# Statuses approved for cost attribution on transactions.
# Draft/Pricing: not yet finalized — attribution not permitted.
# Closed: no further transactions allowed per business rule.
# This constant is intentionally exhaustive to prevent inline string checks.
ALLOWED_TRANSACTION_BOQ_STATUSES = ["Locked", "Frozen"]
EXCLUDED_TRANSACTION_BOQ_STATUSES = ["Draft", "Pricing", "Closed"]
```

**Rationale:** `Closed` must be explicitly documented as excluded so a future engineer does not assume it was forgotten.

Also replace the `get_scope_token` implementation with:

```python
def get_scope_token(user):
    """Return a deterministic token representing the user's active scope.
    
    Includes the User Scope Context `modified` timestamp so in-place
    updates invalidate the token without requiring a value change.
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

**Rationale:** MD5 is cryptographically broken and flagged by compliance scanners. SHA-256 is the minimum acceptable hash. Including `modified` prevents stale-token collisions.

---

## 3. Revise Section: 1. Shared Scope Filter Builder

Add the following paragraph after the sentence "This avoids duplicating hierarchy logic across whitelisted query methods."

> **Security mandate:** All SQL condition builders must use dictionary parameter binding (`%(key)s`) with a consolidated `values` dict. f-string interpolation for **values** is forbidden. f-string interpolation for column or table names is permitted **only** against an explicit allow-list of known table/column strings. All user-facing filter inputs must pass through `frappe.parse_json()` and type validation before reaching SQL builders. The existing `scope_query.py` pattern using `frappe.db.escape()` inside f-strings is **not** acceptable for new code.

Provide the mandated code pattern in the plan:

```python
# ✅ Mandated pattern
conditions = ["docstatus < 2"]
values = {"txt": f"%{txt}%", "start": start, "page_len": page_len}

if filters.get("project"):
    conditions.append("project = %(project)s")
    values["project"] = filters["project"]

where_clause = " AND ".join(conditions)

# ❌ Forbidden pattern
conditions.append(f"project = {frappe.db.escape(project)}")
```

---

## 4. Revise Section: Phase 1 — Data Model and Custom Fields

### 4.1 Field Definitions

Replace the operational custom field definitions with these exact versions:

```python
{
    "fieldname": "boq_header",
    "fieldtype": "Link",
    "options": "BOQ Header",
    "label": "BOQ Header",
    "insert_after": "expense_category",
    "depends_on": "eval:doc.expense_category == 'Direct'",
    "read_only_depends_on": "eval:doc.expense_category != 'Direct'",
},
{
    "fieldname": "boq_structure",
    "fieldtype": "Link",
    "options": "BOQ Structure",
    "label": "BOQ Structure",
    "insert_after": "boq_header",
    "depends_on": "eval:doc.boq_header && doc.expense_category == 'Direct'",
    "read_only_depends_on": "eval:!doc.boq_header || doc.expense_category != 'Direct'",
},
{
    "fieldname": "boq_item",
    "fieldtype": "Link",
    "options": "BOQ Item",
    "label": "BOQ Item",
    "insert_after": "boq_structure",
    "depends_on": "eval:doc.boq_structure && doc.expense_category == 'Direct'",
    "read_only_depends_on": "eval:!doc.boq_structure || doc.expense_category != 'Direct'",
},
{
    "fieldname": "boq_item_stage",
    "fieldtype": "Link",
    "options": "BOQ Item Stage",
    "label": "BOQ Item Stage",
    "insert_after": "boq_item",
    "depends_on": "eval:doc.boq_item && doc.expense_category == 'Direct'",
    "read_only_depends_on": "eval:!doc.boq_item || doc.expense_category != 'Direct'",
},
```

**Change rationale:**
- `expense_category` must appear **first** in the field order so downstream `depends_on` logic is visually coherent.
- `read_only_depends_on` is required to prevent user edits when upstream conditions are not met.

### 4.2 Insert-After Resolution

Add this note:

> `install.py` must define `BOQ_CASCADE_INSERT_AFTER` mapping per target DocType. The generic `_resolve_insert_after` fallback is insufficient for this release because `boq_header` must appear **after** `expense_category` on all child tables. On `Journal Entry Account`, where `project` may be absent, the fallback must be `account`, not the last field.

Add this table to the plan:

```python
BOQ_CASCADE_INSERT_AFTER = {
    "Purchase Order Item": "expense_category",
    "Purchase Receipt Item": "expense_category",
    "Purchase Invoice Item": "expense_category",
    "Stock Entry Detail": "expense_category",
    "Timesheet Detail": "expense_category",
    "Journal Entry Account": "account",
    "Sales Invoice Item": "expense_category",
    "Material Request Item": "expense_category",
}
```

### 4.3 Add Audit Field

Add to the same migration:

```python
{
    "fieldname": "boq_selection_scope_type",
    "fieldtype": "Select",
    "options": "\nProject-Scoped\nCompany-CostCenter-Scoped",
    "label": "BOQ Selection Scope Type",
    "insert_after": "boq_item_stage",
    "read_only": 1,
    "hidden": 1,
    "no_copy": 1,
}
```

> This field is populated server-side during query selection or save validation. It creates an immutable audit trail of whether the BOQ selection was made under Project scope or the broader Company+Cost Center scope.

### 4.4 Index Additions

Expand the Required Indexes table to:

| Table | Index Columns | Type | Rationale |
|-------|--------------|------|-----------|
| `BOQ Header` | `project, status, docstatus` | Composite | Covers the dominant transaction query pattern |
| `BOQ Structure` | `boq_header, is_group, lft` | Composite | Leaf-node lookup with tree ordering |
| `BOQ Item` | `boq_header, structure, docstatus` | Composite | Full cascade resolution in one index scan |
| `BOQ Item Stage` | `boq_item, stage_code` | Composite | Accelerates stage search by code |

Add this note:

> Index creation must use `ALGORITHM=INPLACE, LOCK=NONE` on MariaDB 10.3+ / MySQL 8.0+ where supported. If online DDL is unavailable, index creation must be scheduled in a maintenance window or executed via `pt-online-schema-change` for tables larger than 1 million rows.

---

## 5. Revise Section: Phase 2 — Server Query Hardening

### 5.1 Module Split

Replace the single `construction/services/boq_scope_filters.py` with two modules:

- **`construction/services/scope_resolution.py`** — Pure Python, no SQL. Responsible for:
  - `get_current_scope(user)`
  - `get_descendant_cost_centers(cost_center)`
  - `get_scope_token(scope_dict)` (accepts dict, not user, for testability)
  - `normalize_filters(raw_filters)`

- **`construction/services/boq_scope_filters.py`** — SQL-aware. Responsible for:
  - `build_boq_header_conditions(filters, scope)`
  - `build_boq_structure_conditions(filters, scope)`
  - `build_boq_item_conditions(filters, scope)`
  - `build_boq_item_stage_conditions(filters, scope)`

> **Rationale:** `scope_resolution.py` can be unit-tested with mocked data and zero database transactions. `boq_scope_filters.py` requires DB integration tests only for SQL generation, not scope logic.

### 5.2 No-Project Leaf Validity

Add to the `get_boq_structures` specification:

> If the selected BOQ Header contains no leaf structures (all rows have `is_group = 1`, or all leaf rows have `docstatus = 2`), the query must return an empty result set. The client must display: **"This BOQ Header has no selectable leaf structures."**

### 5.3 API Backward Compatibility

Add:

> Whitelisted query methods must remain backward-compatible for external integrations. Add an optional boolean parameter `enforce_scope` defaulting to `False`. When `False`, the method applies DocType filters but does **not** inject active Scope Context constraints. When `True` (used by the new transaction UI), full scope enforcement applies. Log a deprecation warning when `enforce_scope` is omitted so external callers migrate.

---

## 6. Revise Section: Phase 3 — Client Cascade Controller

### 6.1 Query Registration Pattern

Replace the repeated rebind-on-every-event approach with this requirement:

> `get_query` for BOQ fields must be registered **once** during `setup`. The registered function must read `window.scopeContext.getCurrentScope()` dynamically at call time rather than capturing scope in a closure. This eliminates the need to rebind on every `scope:changed` event and prevents memory leaks from stacked function references.

Rebinding is only required when:
- The form is loaded (initial setup).
- The set of available fields changes (e.g., after a patch installs new fields).

### 6.2 Pre-Save Synchronous Scope Drift Guard

Add this required function to the Phase 3 specification:

```javascript
async function guardSaveAgainstScopeDrift(frm) {
    const currentToken = await fetchScopeToken();
    if (currentToken && currentToken !== lastKnownScopeToken) {
        frappe.show_alert({
            message: __("Your scope context has changed. Reloading form to prevent invalid attribution."),
            indicator: "orange"
        });
        frm.reload_doc();
        return Promise.reject("scope_drift");
    }
}
```

> This guard must be wrapped around `frm.save` and `frm.submit` for all transaction DocTypes in the cascade list. It prevents the race condition where a user clicks Save after changing Scope Context in another tab but before the async rebinding completes.

### 6.3 Warning UI Standard

Add:

> Scope warnings (e.g., "No project selected — BOQ results are not project-scoped.") must use `frm.dashboard.add_comment(message, "yellow")` or `frappe.show_alert({ indicator: "orange" })`. Inline `msgprint` is forbidden for non-blocking guidance because it interrupts data entry.

### 6.4 Accessibility Requirement

Add:

> Cascade clear notifications must be injected into an `aria-live="polite"` container so screen readers announce them. The notification banner must remain in the DOM for at least 5 seconds or until explicitly dismissed.

---

## 7. Revise Section: Phase 5 — Backend Validation Enhancements

Add these validation rules explicitly:

```text
1. If `boq_structure` exists on the row and `boq_header` exists:
   - `boq_structure.boq_header` MUST equal `row.boq_header`.

2. If `boq_item` exists on the row and `boq_structure` exists:
   - `boq_item.structure` MUST equal `row.boq_structure`.

3. If `boq_item` exists on the row and `boq_header` exists:
   - `boq_item.boq_header` MUST equal `row.boq_header`.

4. Transaction Company/Cost Center MUST be within active Scope Context 
   UNLESS the user is Administrator OR `enable_scope_context` is disabled.

5. `boq_selection_scope_type` must be populated server-side during save:
   - "Project-Scoped" if active Scope Context had a Project.
   - "Company-CostCenter-Scoped" if active Scope Context had no Project.
```

Also add the structured logging requirement:

> Every backend rejection must emit a structured log entry:
> ```python
> frappe.logger("boq_validation").warning({
>     "event": "boq_backend_rejection",
>     "user": frappe.session.user,
>     "doctype": parent_doc.doctype,
>     "docname": parent_doc.name,
>     "reason": "<rejection_reason>",
>     "scope": get_current_scope(frappe.session.user),
>     "row_project": row_project,
>     "boq_project": boq_project,
> })
> ```
> These logs are the primary metric for measuring frontend filter bypass rates.

---

## 8. Revise Section: Phase 6 — Tests

### 8.1 New Automated Test Cases

Add these minimum test cases:

| Test | Module |
|------|--------|
| `test_scope_resolution_is_pure_python_no_sql` | `test_scope_context.py` |
| `test_cascade_disabled_preserves_legacy_behavior` | `test_boq_scope_cascade.py` |
| `test_v66_patch_is_idempotent` | `test_boq_scope_cascade.py` |
| `test_api_backward_compat_without_enforce_scope` | `test_boq_link_queries.py` |
| `test_backend_rejection_logs_structured_event` | `test_boq_transaction_validation.py` |
| `test_no_leaf_structures_returns_empty_with_notice` | `test_boq_link_queries.py` |
| `test_pre_save_scope_drift_blocks_save` | `test_boq_scope_cascade.py` (UI test or mocked) |

### 8.2 Performance SLIs

Add this subsection:

#### Performance Acceptance Criteria

| Metric | Target | Test Dataset |
|--------|--------|--------------|
| BOQ Header dropdown render | < 300 ms | 10,000 headers |
| BOQ Item dropdown render | < 300 ms | 100,000 items |
| Cascade clear (client, 50 rows) | < 50 ms | 50 rows |
| Save validation (server, 100 rows) | < 200 ms | 100-row document |
| Scope token endpoint | < 50 ms | Any |

> Before cloud deployment, run `construction/tests/load/test_boq_cascade_load.py` (Locust) against a staging database with production-scale BOQ data. Results must be attached to the release approval.

### 8.3 Manual QA Additions

Add these scenarios:

1. **Feature flag Off:** Enable `enable_boq_cascade_filtering = Off`. Open Purchase Invoice, add row, confirm that `boq_item` dropdown is **not** scoped by active Scope Context and `boq_header`/`boq_structure` fields are hidden or non-functional.
2. **Historical row edit:** Open a saved Purchase Invoice created before the patch. Confirm that rows display correctly even though `boq_header` and `boq_structure` are empty.
3. **Mobile/smaller viewport:** Confirm that cascade clear alerts do not obscure the Save button.
4. **Keyboard-only navigation:** Tab through the cascade fields using only keyboard. Confirm focus is not trapped and clear notifications are readable.

---

## 9. Add New Section: Data Quality Report (Before Phase 7)

Insert after Phase 6:

### Phase 6.5: Pre-Production Data Quality Gate

Before enabling `Strict` mode in production, run the built-in report **BOQ Data Quality — Pre-Cascade Enforcement**.

**Report location:** `construction/construction/report/boq_data_quality_report/`

**Checks:**

1. BOQ Header rows where `project` is NULL or points to a non-existent Project.
2. BOQ Item rows where `boq_header` is NULL or mismatched with `structure.boq_header`.
3. BOQ Item Stage rows where `boq_item` is NULL.
4. Transaction child rows (last 90 days) where `boq_item` is set but parent `project` is empty.
5. BOQ Structure rows where `is_group = 0` but `docstatus = 2` (cancelled leaf nodes that may surprise users with empty dropdowns).

**Gate rule:** All `CRITICAL` findings must be resolved before `Strict` mode is enabled. `WARNING` findings may be waived with sign-off from the Data Steward.

---

## 10. Revise Section: Phase 7 — Migration and Deployment

Add these steps after step 8:

9. Verify `Construction Settings.enable_boq_cascade_filtering` is set to `Off` immediately after migration.
10. Run the Data Quality Report (Phase 6.5) and attach results to release notes.
11. Enable `On` for a pilot user group; monitor `boq_validation` logs for 48 hours.
12. Enable `Strict` only after zero backend rejections are observed for 48 hours under `On`.

Add rollback command:

```bash
bench --site <site> execute construction.patches.v6_6.revert_boq_cascade_fields.execute
bench --site <site> clear-cache
```

---

## 11. Add New Section: Out of Scope (Expansion)

Append to the existing Out of Scope list:

- Adding `boq_header` / `boq_structure` as Accounting Dimensions (Phase 1 only).
- Frappe Mobile App custom Link query support (mobile will rely on backend validation).
- Real-time collaborative editing of the same transaction document by multiple users.
- Automated backfill of historical transaction rows with `boq_header` / `boq_structure` (historical rows remain valid with only `boq_item` populated).

---

## 12. Add New Section: Mobile / Offline Compatibility Note

Add:

> **Mobile:** The Frappe Mobile application does not execute custom JavaScript `get_query` handlers in the same manner as the web desk. Therefore, mobile users will see unfiltered BOQ dropdowns and will continue to rely on backend validation. This is an acceptable degradation and does not block release.

---

## Summary of Files to Change (Update This List in the Plan)

**New files to add:**

- `construction/services/scope_resolution.py`
- `construction/patches/v6_6/revert_boq_cascade_fields.py`
- `construction/construction/report/boq_data_quality_report/`
- `construction/tests/load/test_boq_cascade_load.py`

**Files to update:**

- `construction/install.py` (field definitions, insert_after map)
- `construction/api/boq_link_queries.py` (enforce_scope param, scope checks)
- `construction/services/boq_scope_filters.py` (SQL builders only)
- `construction/services/boq_accounting.py` (new validation rules, structured logging)
- `construction/public/js/boq_filters.js` (pre-save guard, dynamic query pattern)
- `construction/public/js/scope_context_form_defaults.js` (child row defaults)
- `construction/patches.txt` (add v6_6 entries)
- `construction/patches/v6_6/add_boq_cascade_transaction_fields.py` (index additions, audit field)

---

## Final Instruction

Incorporate all revisions above into `docs/boq_scope_context_filtering_implementation_plan.md`. Do not remove existing content unless it directly conflicts with a replacement above. Preserve the current document structure; insert new sections at the indicated locations.

The plan is approved for implementation **only after these revisions are merged into the document and reviewed.**

