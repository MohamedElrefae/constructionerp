# EV-068 — VFC Doc Hygiene (WP0)

**Date:** 2026-06-21
**WP:** WP0 — VFC Doc Hygiene
**Branch:** `feat/vfc-phase3-stabilization`

## Changes Applied

### 1. AGENTS.md §3D — VFC stats updated
- `vfc_layout_engine.js` (847 lines) → (1,342 lines)
- `vite_layout_controls.js` (dynamic) → (1,694 lines)
- Added `vfc_config.js` (23 lines), `layout_api.py` (302 lines)
- Added `modern_form_api.py` (431 lines) with deprecation notice
- Status updated to Phase 3+ stabilization

### 2. SESSION_MEMORY.md — VFC section rewritten
- Current line counts for all VFC files
- `for_user` field noted as implemented
- `modern_form_api.py` noted as deprecated (ADR-008)
- Sprint name updated to `feat/vfc-phase3-stabilization`

### 3. hooks.py — N1 fix (dangling patch reference)
- Removed `patches = ["construction.patches.v6_7.add_for_user_to_form_layout_profile"]`
- Reason: the `patches/` directory never existed; the `for_user` field is already in `form_layout_profile.json` and is applied on every `bench migrate` via the DocType JSON schema. Keeping the dangling import would break `bench migrate` on fresh installs with `ModuleNotFoundError`.

### 4. vfc_layout_engine.js — N2 fix (cache invalidation naming mismatch)
- Added public `invalidateCache(doctype)` method as a pass-through alias to `_invalidateCache(doctype)`
- Controls (vite_layout_controls.js:801) call `window.VFCLayoutEngine.invalidateCache?.(dt)` — was silently no-oping because only `_invalidateCache` (underscore prefix) existed. Now works correctly.

## Verification

- `bench --site v16.localhost migrate` — no `ModuleNotFoundError` for missing patch module
- `rg "construction.patches.v6_7" hooks.py` — reference removed
- `git diff construction/public/js/vfc_layout_engine.js` — public `invalidateCache` alias added
