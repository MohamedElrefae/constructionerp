# EV-069 — VFC Engine Stabilization (WP1)

**Date:** 2026-06-21
**WP:** WP1 — Engine Stabilization
**Branch:** `feat/vfc-phase3-stabilization`

## Changes Applied

### 1. Field Visibility — `_restoreVisibleFieldWrapper()` hardened
- **File:** `vfc_layout_engine.js`
- Removed `!important` flags from `visibility` and `opacity` inline styles — Frappe's runtime `toggle_display()` and `depends_on` evaluation can now override VFC visibility.
- Replaced `style.setProperty("display", "block")` with `style.removeProperty("display")` — lets the field's natural display state apply.
- Child element visibility cleanup also deescalated from `!important` to normal cascade.
- **Rationale:** `!important` was preventing Frappe from re-hiding fields after `depends_on` evaluation.

### 2. Guard Checks — `hidden_due_to_dependency` added
- **File:** `vfc_layout_engine.js` — 4 locations updated:
  - `_render()` — profile section iteration
  - `_hasMissingFields()` — verification pass
  - `_appendUnassigned()` — unassigned fields at bottom
  - `renderWithDensity()` — density-only rendering
- All now check `fieldObj.df.hidden_due_to_dependency` in addition to `df.hidden` and `df.invisible`.
- **Rationale:** `depends_on` can evaluate asynchronously after the engine renders; `hidden_due_to_dependency` marks fields hidden by dependencies.

### 3. Double Attach — `_applyDensity()` fixed
- **File:** `vite_layout_controls.js`
- Removed `restoreNative(frm)` call from `_applyDensity()`. The `attach()` call already triggers `_render()` which calls `_clearSections()` internally, making the explicit restore redundant and causing flicker.
- Density changes now go through a single controlled reattach cycle.

### 4. Observer Scoping — narrowed to layout root
- **File:** `vfc_layout_engine.js`
- Observer target changed from `this._getObserverRoot(frm, layoutRoot)` (which returned `frm.wrapper?.[0] || frm.page?.main?.[0] || layoutRoot`) to just `layoutRoot`.
- `subtree: true` removed — observer now watches direct `childList` changes on the layout root only.
- Added debug-gated callback counter: `window.__VFC_OBSERVER_COUNT` increments on each mutation callback when `VFC_DEBUG` is on.

### 5. Timer Cleanup — retry timers cleared on section teardown
- **File:** `vfc_layout_engine.js` — `_clearSections()`
- Added cleanup of `_retryTimers` and `_retryCounts` entries for the form key when `_clearSections` runs (on restore, navigation, re-attach).
- Previously only `_validationTimers` were cleared; stale `_retryTimers` could fire on detached form instances after navigation.

### 6. JS Cache Busters Bumped
- **File:** `hooks.py`
- `vfc_layout_engine.js?v=1.43` (was 1.42)
- `vite_layout_controls.js?v=1.19` (was 1.18)
