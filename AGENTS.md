# Construction App — Development Report

## Overview

Implementation of the **Scope Context** subsystem across 5 phases. This feature provides multi-dimensional scoping (company, cost center, project, department) for user-level data access in Frappe/ERPNext, replacing the legacy single-company model.

---

## Phase 1: Foundation — Scope Context DocType & API

### Objective
Create the core data model and CRUD API for user scope management.

### Deliverables

| Artifact | Path |
|---|---|
| DocType JSON | `construction/doctype/user_scope_context/user_scope_context.json` |
| Python Controller | `construction/doctype/user_scope_context/user_scope_context.py` |
| API Module | `api/scope_context_api.py` |

### DocType Fields
- `user` (Link → User, reqd, unique, autoname field)
- `company` (Link → Company, reqd)
- `cost_center` (Link → Cost Center)
- `project` (Link → Project)
- `department` (Link → Department)
- `scope_version` (Int, auto-incremented on each save)
- `last_active_at` (Datetime, auto-set via `now_datetime()`)
- `client_id` (Data, for multi-tab browser support)
- `track_changes` enabled for version history

### API Endpoints (whitelisted)
- `set_scope_context()` — Dual-write: canonical DocType + session defaults sync
- `get_scope_hierarchy_detail()` — Full hierarchy tree for management UI
- `quick_create()` — Generic quick-add for management UI
- `get_active_scope_summary()` — Active sessions (System Manager only)

### Validation Rules
- Cross-dimension validation via `scope_validation.py`
- User existence check
- Permission boundary: non-admins cannot create records for other users

---

## Phase 2: Overrides & Boot — Query Injection & Session Sync

### Objective
Integrate scope context into Frappe's query layer and boot sequence.

### Deliverables

| Artifact | Path |
|---|---|
| Query Override | `overrides/scope_query.py` |
| Boot Extension | `boot.py` |
| Validation Utility | `construction/utils/scope_validation.py` |

### `add_scope_conditions(user, doctype)`
- Injects SQL WHERE clauses for ALL doctype queries via `permission_query_conditions` hook
- NestedSet expansion: cost center filter includes descendants via `lft/rgt`
- Column-existence guards prevent invalid SQL
- Per-request column cache avoids repeated `information_schema` queries
- Administrator bypasses all filters
- System doctypes (User, Role, DocType, etc.) skipped

### Bootinfo Extension
- `scope_context_enabled` flag from Construction Settings
- `scope_context_enabled_dimensions` — per-dimension toggle
- `scope_context.current` — user's current scope document
- `scope_context.hierarchy` — permitted hierarchy (companies, cost centers, projects, departments)
- `scope_context._version` — cache-busting version key

### Session Defaults Sync
On scope change: `set_scope_context()` writes to User Scope Context DocType, then syncs to `frappe.defaults.set_user_default()` for company, cost_center, project, department. Cleared when null/unset.

---

## Phase 3: NestedSet Expansion & Query Filters

### Objective
Implement NestedSet descendant expansion for cost center filtering.

### Deliverables
- Integrated into `add_scope_conditions()` in `overrides/scope_query.py`

### Implementation
```sql
`tab{doctype}`.`cost_center` IN (
    SELECT `name` FROM `tabCost Center`
    WHERE `lft` >= {lft} AND `rgt` <= {rgt}
)
```
- Selected cost center AND all descendants are included
- Works with Frappe's NestedSet model (lft/rgt tree encoding)
- Covers list views, reports, charts, dashboards, recent documents

### Hierarchy API
- `get_user_scope_hierarchy(user)` returns all permitted entities
- Includes NestedSet `lft/rgt/is_group` for cost centers
- Redis-cached with 5-minute TTL
- Cache invalidation via `invalidate_scope_cache(user)` on User Permission changes

---

## Phase 4: Unit Tests & Permission Model

### Objective
Comprehensive unit test suite for User Scope Context DocType.

### Deliverables

| Artifact | Path |
|---|---|
| Unit Tests | `construction/doctype/user_scope_context/test_user_scope_context.py` |

### Test Cases

| ID | Test | Description |
|---|---|---|
| AC-001 | `test_01_doctype_exists` | DocType registered in system |
| AC-002 | `test_02_create_valid_record` | Valid user+company creation |
| AC-003 | `test_03_duplicate_user_fails` | Unique constraint on user |
| AC-004 | `test_04_scope_version_increments` | Auto-increment on save |
| AC-005 | `test_05_last_active_at_populates` | Datetime auto-set |
| AC-006 | `test_06_track_changes_enabled` | Version creation |
| AC-007 | `test_07_non_admin_permission_restriction` | Non-admin cannot read others |
| AC-008 | `test_08_cross_dimension_validation` | Mismatched cost_center/company rejected |
| — | `test_owner_can_modify_own_record` | Record owner write access |
| — | `test_required_fields` | Mandatory field metadata |

### Permission Model
DocType permission rules:
- **System Manager**: Full read/write/create/delete
- **All (including `__myself`)**: Read access to own record only
- Owner-based access enforced via `__myself` rule
- `validate()` method blocks cross-user creation for non-System Managers

---

## Phase 5: Integration Tests & Documentation

### Objective
End-to-end integration tests + final documentation.

### Deliverables

| Artifact | Path |
|---|---|
| Integration Tests | `tests/test_scope_context.py` |

### Integration Test Cases

| ID | Test | Description |
|---|---|---|
| T-001 | `test_create_scope_context` | Full creation flow via API |
| T-002 | `test_update_scope_context` | Update increments version |
| T-003 | `test_session_defaults_sync` | Session defaults mirror DocType |
| T-004 | `test_cross_validation` | Cross-dimension validation utility |
| T-005 | `test_authorization` | Non-admin unauthorized access |
| T-006 | `test_bootinfo_scope_context` | Bootinfo includes scope data |
| T-007 | `test_bootinfo_hierarchy` | Bootinfo includes NestedSet hierarchy |
| T-008 | `test_version_log` | Track Changes version log |
| T-009 | `test_concurrent_writes` | Sequential updates |
| T-010 | `test_first_time_user` | New user gets empty hierarchy |
| T-011 | `test_defaults_cleared_on_switch` | Unset fields cleared in defaults |
| T-012 | `test_nestedset_expansion` | NestedSet descendant logic verified |
| T-013 | `test_server_side_injection` | Query injection: admin bypass, skip doctypes, column guards, unscoped user |

### Replacement: Branch → Cost Center
- Legacy `Branch` doctype references replaced with `Employee` (has company, no cost_center)
- All dimension references normalized to cost_center throughout test suite

---

## Test Results

### Unit Tests (AC-001 through AC-008 + additional)
```
Ran 10 tests in 0.968s
OK
```

### Integration Tests (T-001 through T-013)
```
Results: 13 passed, 0 failed, 13 total
ALL TESTS PASSED
```

---

## Architecture Summary

```
User Action
    │
    ▼
set_scope_context() [whitelisted API]
    │
    ├─► get_user_scope_hierarchy() → Redis-cached permitted entities
    ├─► validate_scope_dimensions() → cross-dimension check
    ├─► User Scope Context DocType [canonical store]
    ├─► frappe.defaults.set_user_default() [session sync]
    └─► Cache invalidation
            │
            ▼
    add_scope_conditions() [on every DB query, via permission_query_conditions hook]
            │
            ├─► NestedSet expansion for cost_center → lft/rgt subquery
            ├─► Column-existence guard
            └─► Admin bypass + system doctype skip
            │
            ▼
    extend_bootinfo() [on every page load]
            │
            ├─► scope_context.current → user's scope document
            └─► scope_context.hierarchy → full permitted tree (lft/rgt for frontend expansion)
```

### Data Flow
1. User selects dimensions in UI → `set_scope_context()` API call
2. API validates authorization + cross-dimension consistency
3. Canonical record saved to User Scope Context DocType
4. Session defaults synced for immediate `frappe.defaults` reads
5. All subsequent doctype queries filtered via `add_scope_conditions()`
6. Bootinfo extended with scope + hierarchy for client-side rendering

### Key Design Decisions
- **Canonical + Cache**: DocType is source of truth; session defaults are convenience cache
- **NestedSet at query level**: Descendant expansion in SQL, not application code
- **Column-existence guard**: Prevents SQL errors on doctypes missing scope columns
- **Admin bypass**: Administrator always sees all data; filtering only for non-admin users
- **Per-request column cache**: Avoids repeated `information_schema` queries within same request
- **Redis caching of hierarchy**: 5-minute TTL with explicit invalidation on User Permission changes
