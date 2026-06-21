# VFC Phase 3+ Stabilization Implementation Plan

> **Status:** Approved — in execution
> **Date:** 2026-06-21
> **Branch:** `feat/vfc-phase3-stabilization` (from `develop`)
> **Companion docs:** `VFC_PHASE_3_PLUS_REVISION_PLAN.md`, `VFC_PHASE_3_PLUS_ENHANCEMENT_REVIEW.md`
> **Estimated effort:** 10.5–15.5 days

## Locked Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| React path | **Deprecate runtime loading** | Remove `components/index.js?v=4.6` from `hooks.py`; restrict `modern_form_api.py` to System Manager. Keep source files in place. |
| Cache strategy | **60 s client-side TTL** | Simplest approach; covers cross-user changes without backend invalidation calls. |
| Recovery | **Simple revert button** | "Revert to default/native" in Sections editor. Full profile version history deferred. |
| Expansion | **Project + BOQ Item Stage** | Add `DEFAULT_PROJECT_LAYOUT` seed; verify existing `DEFAULT_BOQ_ITEM_STAGE_LAYOUT`. Cost Item not implemented; VO not UI-tested yet. |

## Merge Order

```
develop → feat/vfc-phase3-stabilization
   WP0 → WP1 → WP2 → WP3 → WP4 → WP5 → develop
```

## Evidence Files

| ID | File | WP |
|----|------|----|
| EV-068 | `docs/feature_reviews/evidence/EV-068-vfc-doc-hygiene.md` | WP0 |
| EV-069 | `docs/feature_reviews/evidence/EV-069-vfc-engine-stabilization.md` | WP1 |
| EV-070 | `docs/feature_reviews/evidence/EV-070-vfc-architecture-decision.md` | WP2 |
| EV-071 | `docs/feature_reviews/evidence/EV-071-vfc-schema-editor-hardening.md` | WP3 |
| EV-072 | `docs/feature_reviews/evidence/EV-072-vfc-controlled-expansion.md` | WP4 |
| EV-073 | `docs/feature_reviews/evidence/EV-073-vfc-verification-gate.md` | WP5 |

## WP0 — Doc Hygiene and N1 Patch

Tasks:
- update `AGENTS.md` §3D with current file sizes, asset versions, `for_user` status, blocklist behavior
- update `SESSION_MEMORY.md:59-64` VFC section
- resolve N1: remove dangling `patches = [...]` entry in `hooks.py:265-267` since the patch directory does not exist and `for_user` is already in the DocType JSON
- fix N2: implement public `invalidateCache(doctype)` alias on `LayoutEngine`; call the alias from `vite_layout_controls.js:801`
- update any stale `VFC_DISABLED` references across docs

## WP1 — Engine Stabilization

Tasks:
- harden `_restoreVisibleFieldWrapper()` to respect Frappe `depends_on`, permission, and runtime hidden state
- remove density-triggered double attach in `_applyDensity()` (`vite_layout_controls.js:718-720`); use controlled reattach
- scope `MutationObserver` to layout root with `childList:true` only; add debug-gated callback counter
- clean retry timers and observers on `restoreNative()` and form navigation
- bump JS cache busters in `hooks.py` for changed VFC files

## WP2 — Deprecate React Runtime Path

Tasks:
- grep for `ModernThemeComponents`, `UnifiedCRUDForm`, `FormField` runtime references
- remove `components/index.js?v=4.6` from `hooks.py` `app_include_js`
- restrict all whitelisted endpoints in `modern_form_api.py` to System Manager
- keep source files in place; do not delete React components
- write ADR-008 recording the deprecation decision

## WP3 — Profile Cache, Schema, and Recovery

Tasks:
- implement 60 s TTL on `LayoutEngine._cache` entries
- verify `get_active_layout()` precedence: `for_user` > role > default
- add "Revert to default/native" button in Sections editor
- replace CDN SortableJS with local asset fallback

## WP4 — Controlled Expansion

Tasks:
- verify existing seeds (BOQ Header, BOQ Item Stage, BOQ Structure, User Scope Context) against current DocType JSONs
- audit `BLOCKED_DOCTYPES` with per-category comments
- add `DEFAULT_PROJECT_LAYOUT` to `install.py` and register in `seed_form_layout_profiles()`
- verify existing `DEFAULT_BOQ_ITEM_STAGE_LAYOUT` fieldnames against `boq_item_stage.json`
- prove native fallback (no profile → no-op)

## WP5 — Verification Gate

Tasks:
- fix `VFCTest.checkDebounce()` — remove stale `window.VFC_DISABLED` assertion
- add backend tests for `layout_api.py`, `Form Layout Profile`, `modern_form_api.py` restrictions, 60 s cache, revert behavior, seed fieldnames
- register `run_vfc_tests()` runner in `construction/tests/__init__.py`
- capture evidence and verify no console errors from removed React globals

## Key Verification Commands

```bash
# After every WP
bench --site v16.localhost migrate

# Backend tests (WP5)
bench --site v16.localhost execute construction.tests.run_vfc_tests

# Build after JS/hook changes
bench build --app construction

# Browser gate (manual)
VFCTest.runAll()   # after fix
```
