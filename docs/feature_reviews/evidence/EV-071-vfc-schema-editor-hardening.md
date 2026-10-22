# EV-071 — VFC Schema, Cache, and Recovery Hardening (WP3)

**Date:** 2026-06-21
**WP:** WP3 — Schema and Editor Hardening
**Branch:** `feat/vfc-phase3-stabilization`

## Changes Applied

### 1. Cache TTL — 60-second expiry on profile fetches
- **File:** `vfc_layout_engine.js`
- Added `CACHE_TTL_MS: 60000` constant on the LayoutEngine singleton
- Changed `_cache` format from `doctype → profile` to `doctype → { value, ts }`
- `_fetchProfile()` now checks `Date.now() - entry.ts < CACHE_TTL_MS` before returning cached value
- `invalidateCache()` still performs immediate deletion (for same-session saves)

### 2. get_active_layout Precedence Verified
- **File:** `layout_api.py:72-88` (no change needed)
- Order confirmed: (1) `for_user` match → (2) `for_role` match → (3) `is_default` → (4) `None` (native)
- Field exists on profile JSON (`for_user` at `form_layout_profile.json:77-82`)

### 3. Revert to Default / Native UI
- **File:** `vite_layout_controls.js`
- Added "Revert to Default / Native" button in the Sections editor tab (renders below the sections list)
- Added `_revertToDefault(frm, dtId)` method:
  - Confirms with the user via `frappe.confirm`
  - Lists all profiles for the doctype via `list_layouts` API
  - Finds and deletes the current user's `for_user` profile via `delete_layout` API
  - Calls `invalidateCache(doctype)` and `attach(frm)` to re-render with the role/default match
  - Shows success/failure alert
- Click handler wired in the panel initialization block

### 4. SortableJS — CDN dependency removed
- **File:** `construction/public/js/vendor/sortablejs.min.js` (new, 44 KB)
- **File:** `vite_layout_controls.js`
- Replaced `frappe.require("https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js")` with local path `/assets/construction/js/vendor/sortablejs.min.js`
- Sections editor now works without internet access
