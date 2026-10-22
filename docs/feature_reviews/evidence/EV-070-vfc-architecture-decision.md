# EV-070 — VFC Architecture Decision (WP2)

**Date:** 2026-06-21
**WP:** WP2 — Architecture Decision
**Branch:** `feat/vfc-phase3-stabilization`

## Changes Applied

### 1. ADR-008 — VFC Primary Architecture
- **File:** `ADR.md` (appended)
- Decision: DB-backed overlay (`Form Layout Profile` + `vfc_layout_engine.js`) is the production path
- React path deprecated: runtime include removed, API restricted, source retained

### 2. hooks.py — React Runtime Include Removed
- **Line:** `/assets/construction/js/components/index.js?v=4.6` removed from `app_include_js`
- Safety check: `grep` for `ModernThemeComponents`, `UnifiedCRUDForm`, `FormField`, `FormLayoutControls`, `DraggablePanel`, `ExportButtons`, `UltimateButton` across all JS files — no runtime consumers found beyond the definition file itself.
- **Note:** The React globals (`window.UnifiedCRUDForm`, etc.) are set by the Vite bundle (`construction.bundle.XR6HIDAQ.js`), not by `components/index.js`. The index.js only re-exports them under `window.ModernThemeComponents`. Removing the index.js include does not affect the globals.

### 3. modern_form_api.py — All Endpoints Restricted
- Added `_require_system_manager()` gate (same pattern as `layout_api.py`)
- Applied to all 7 whitelisted endpoints: get_form_config, get_document, create_document, update_document, delete_document, validate_field, search_link
- Source files retained per plan (no deletion)
