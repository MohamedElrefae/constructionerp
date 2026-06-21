# EV-073 — VFC Verification Gate (WP5)

**Date:** 2026-06-21
**WP:** WP5 — Verification Gate
**Branch:** `feat/vfc-phase3-stabilization`

## Changes Applied

### 1. Browser Test Suite Rewrite (`vfc_layout_engine_tests.js`)
- Replaced `checkDebounce()` stub with `checkEngineLoaded()` — verifies:
  - `window.VFCLayoutEngine` exists
  - Key methods: `attach`, `restoreNative`, `invalidateCache`, `_fetchProfile`
  - `CACHE_TTL_MS` constant equals `60000`
- Updated `runAll()` entry point and doc comment to reference the new test method

### 2. Backend Test Suite (`tests/test_vfc_backend.py`)
- Three test classes covering all WP0–WP4 backend changes:

#### `TestFormLayoutProfile` (DocType validation)
| Test | What it verifies |
|------|------------------|
| `test_single_default_enforced` | Only one `is_default=1` per reference_doctype allowed |
| `test_single_default_allows_different_doctype` | Different doctypes can each have a default |
| `test_malformed_sections_json_raises` | Non-JSON sections_json raises ValidationError |
| `test_empty_sections_json_raises` | Empty sections_json raises ValidationError |
| `test_duplicate_fieldname_rejected` | Same fieldname in two sections rejected |
| `test_is_system_delete_guard` | System profiles cannot be deleted |
| `test_unknown_field_warns` | Unknown fieldnames produce a warning, not an error |
| `test_invalid_column_count_rejected` | column_count must be 1, 2, or 3 |

#### `TestLayoutAPI` (layout_api endpoints)
| Test | What it verifies |
|------|------------------|
| `test_get_active_layout_returns_none_when_no_profile` | Unknown doctype → None |
| `test_get_active_layout_returns_default` | Default profile returned |
| `test_get_active_layout_prefers_for_user` | for_user overrides default |
| `test_get_active_layout_prefers_role` | for_role overrides default |
| `test_get_active_layout_disabled_profiles_ignored` | enabled=0 profiles not returned |
| `test_get_active_layout_returns_sections` | Response includes parsed sections list |
| `test_save_layout_creates_new` | Creates new profile → status "created" |
| `test_save_layout_updates_existing` | Updates existing profile → status "updated" |
| `test_list_layouts_returns_profiles` | Returns matching profiles |
| `test_list_layouts_returns_empty_for_unknown` | Unknown doctype → empty list |
| `test_delete_layout_removes_profile` | Deletes profile |
| `test_delete_layout_blocks_is_system` | System profiles raise PermissionError |
| `test_validate_layout_valid` | Valid layout → valid=True, no errors/warnings |
| `test_validate_layout_invalid_json` | Invalid JSON → valid=False |
| `test_validate_layout_unknown_field_warns` | Unknown field → warning |
| `test_validate_layout_duplicate_fieldname_errors` | Duplicate field → valid=False |
| `test_validate_layout_hidden_required_errors` | Hidden required field → valid=False |

#### `TestSeedValidity` (seed fieldname verification)
| Test | What it verifies |
|------|------------------|
| `test_boq_header_seed` | All fieldnames in DEFAULT_BOQ_HEADER_LAYOUT exist in BOQ Header meta |
| `test_boq_item_stage_seed` | All fieldnames in DEFAULT_BOQ_ITEM_STAGE_LAYOUT exist in BOQ Item Stage meta |
| `test_boq_structure_seed` | All fieldnames in DEFAULT_BOQ_STRUCTURE_LAYOUT exist in BOQ Structure meta |
| `test_user_scope_context_seed` | All fieldnames in DEFAULT_USER_SCOPE_CONTEXT_LAYOUT exist in User Scope Context meta |
| `test_project_seed` | All fieldnames in DEFAULT_PROJECT_LAYOUT exist in Project meta |

#### `TestModernFormAPIRestrictions` (System Manager gate)
| Test | What it verifies |
|------|------------------|
| 7 tests (get_form_config, get_document, create_document, update_document, delete_document, validate_field, search_link) | Each raises `frappe.PermissionError` when `_require_system_manager()` gate is triggered |

### 3. Test Runner (`tests/__init__.py`)
- Added `run_vfc_tests()` function matching the existing `run_quantity_revision_tests()` pattern
- Can be invoked via: `bench --site v16.localhost execute construction.tests.run_vfc_tests`

## Known Gaps
- **Cache TTL expiry**: The browser test suite checks the `CACHE_TTL_MS` constant value (60s) but does
  not exercise the actual expiry/refetch behaviour. Proving the 60-second cache invalidation at runtime
  requires a manual browser test: (1) load a form with a custom layout, (2) modify the profile server-side,
  (3) verify within 60s the old layout is served, and (4) verify after 60s+ the new layout appears. This
  gap is acceptable because cache TTL is a performance optimisation, not a correctness constraint.

## Test Count
- **37 backend tests** across 4 test classes
- **1 browser test** (`checkEngineLoaded`)
- All tests documented and ready for execution
