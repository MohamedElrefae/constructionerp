# VFC Phase 3+ Revision Plan - Enhancement Review

> **Reviewer:** Engineering management review
> **Date:** 2026-06-21
> **Method:** Code-grounded review of VFC files, hooks, test coverage, and related handover docs
> **Reviewed document:** `docs/handover/VFC_PHASE_3_PLUS_REVISION_PLAN.md`
> **Status:** Revised report for planning approval
>
> This document is a companion to `VFC_PHASE_3_PLUS_REVISION_PLAN.md` and should be read alongside it.

## Executive Summary

The VFC Phase 3+ plan is directionally correct. Stabilizing the current implementation before adding new capabilities is the right next sprint move.

The attached review also identifies several real gaps that should be folded into the plan before implementation starts. The most important are:

- the current VFC runtime is larger and newer than the docs say
- the React-based form path is still loaded and should receive an explicit disposition
- backend test coverage for `layout_api.py` and `Form Layout Profile` is missing
- the browser verification suite contains stale assumptions
- the runtime still has likely correctness and performance risks around field visibility, observers, retries, and profile caching

Manager recommendation: approve the VFC plan only after adding a short WP0 doc hygiene pass and strengthening WP1-WP5 with the specific items below.

## 1. Verified Current-State Corrections

| # | Correction | Evidence | Impact |
|---|------------|----------|--------|
| C1 | `vfc_layout_engine.js` is now ~1,340 lines, not 847. | `wc -l construction/public/js/vfc_layout_engine.js` | Docs and planning estimates should be updated. |
| C2 | `vite_layout_controls.js` is now ~1,690 lines. | `wc -l construction/public/js/vite_layout_controls.js` | WP1 is a larger stabilization effort than the draft plan implies. |
| C3 | `modern_form_api.py` still exists and is 431 lines. | `construction/api/modern_form_api.py` | The React/modern form path needs an explicit architecture decision. |
| C4 | `components/index.js?v=4.6` still loads from `hooks.py`. | `construction/hooks.py` | If React is deprecated, hooks should stop loading it globally. |
| C5 | `for_user` exists on `Form Layout Profile`. | `form_layout_profile.json` and patch `v6_7.add_for_user_to_form_layout_profile` | The plan should change from "review whether needed" to "verify resolution order and behavior." |
| C6 | SortableJS is still loaded from CDN. | `vite_layout_controls.js` uses `cdn.jsdelivr.net` | Offline and restricted-network environments remain at risk. |
| C7 | The browser test still checks `window.VFC_DISABLED`. | `vfc_layout_engine_tests.js` | The test suite needs maintenance before it can be a release gate. |
| C8 | No tests were found under `construction/tests` for `layout_api.py` or `Form Layout Profile`. | `rg layout_api construction/tests` | VFC backend behavior needs new test coverage. |

## 2. Material Risks To Add

### R1 - Field Visibility Correctness

`_restoreVisibleFieldWrapper()` currently removes hidden classes and sets moved field wrappers to visible/block with `!important`. This overrides Frappe `depends_on`, permission, and runtime hide/show behavior unless guarded carefully.

Required plan change:
- add a WP1 task to verify and fix field visibility behavior
- add a browser test for a field hidden by `depends_on`
- acceptance must prove VFC does not force hidden fields visible

### R2 - Observer Scope and Performance

The runtime observes a broad DOM subtree and may reattach when Frappe moves controls. This is useful, but it can be expensive on large forms or child-table-heavy workflows.

Required plan change:
- add a WP1 task to scope observers as narrowly as practical
- add a simple benchmark or debug counter for observer callbacks during form load

### R3 - Retry and Timer Cleanup

The engine has retry logic for missing layout roots and delayed verification behavior. The plan should explicitly require timer cleanup on navigation, refresh, and restore.

Required plan change:
- add a WP1 task to clear stale timers and observers when leaving a form or restoring native layout
- acceptance should include "no stale timer reattaches after navigation"

### R4 - CDN Dependency

The Sections editor depends on external SortableJS. That is fragile for client deployments that are offline, firewalled, or locked down.

Required plan change:
- move SortableJS to a local bundled asset or add a documented local fallback
- acceptance should verify the editor works without internet access

### R5 - Profile Cache Invalidation

`VFCLayoutEngine._cache` stores active profiles per doctype. There is an invalidation helper, but no cross-user invalidation path or TTL.

Required plan change:
- choose a simple invalidation strategy first, preferably a short TTL
- acceptance should prove profile changes become visible without a manual hard refresh

### R6 - Bad Profile Recovery

If a saved profile is valid JSON but visually bad, there is no obvious recovery path for users.

Required plan change:
- add a minimal "revert to default/native" path before building full version history
- keep full profile versioning as optional future work

## 3. Work Package Enhancements

### Add WP0 - VFC Doc Hygiene

Objective:
- align the docs with the current codebase before implementation starts

Tasks:
- update VFC line counts and asset versions in `AGENTS.md`, `SESSION_MEMORY.md`, and VFC handover docs
- update the VFC plan to say `for_user` exists and must be verified
- update stale references to `VFC_DISABLED` if the current runtime no longer exposes it
- review `docs/VFC_FORM_CONFIG_DEBUG_REPORT_TO_MANAGER.md` for stale version references
- consolidate or archive the external planning docs at `/home/mohamed/frappe-bench/forms config/` into the repo or remove them

Acceptance criteria:
- VFC docs agree on current file sizes, asset versions, and current architecture state
- no stale "missing for_user" claim remains in active docs

Estimate:
- 0.5 day

### Strengthen WP1 - Engine Stabilization

Add tasks:
- verify `_restoreVisibleFieldWrapper()` respects Frappe hidden/depends_on behavior
- remove or fix the remaining `restoreNative()` -> `attach()` trigger in `_applyDensity()`
- scope MutationObserver usage and add callback-count instrumentation behind the VFC debug flag
- cap retries and clean stale timers/observers on form navigation
- update the code header version to match the asset version loaded by `hooks.py`

Acceptance additions:
- a field hidden by `depends_on` remains hidden under an active VFC profile
- attach runs once per stable refresh cycle
- no stale timers reattach a previous form after navigation
- observer callback volume is measured on at least one large BOQ form

Estimate:
- 3-5 days

### Strengthen WP2 - Architecture Decision

Add tasks:
- decide whether the React/modern form path is deprecated, retained as tooling, or reworked to use `Form Layout Profile`
- if deprecated, stop loading `components/index.js` globally
- if retained, document exactly when it loads and what data source it owns
- review `modern_form_api.py` endpoints and decide whether they remain exposed

Acceptance additions:
- only the chosen runtime path loads by default
- the secondary path is either disabled, gated, or documented as intentionally active

Estimate:
- 1 day

### Strengthen WP3 - Schema and Editor Hardening

Add tasks:
- verify `get_active_layout()` resolution order: `for_user` > role > default
- add malformed `sections_json` handling tests
- replace CDN SortableJS with a local asset or fallback
- implement a simple profile recovery path: "revert to default/native"
- add cache invalidation by TTL or explicit refresh after save

Acceptance additions:
- profile changes appear within an agreed window without hard refresh
- Sections editor works without external CDN access
- users can recover from a bad profile without database surgery

Estimate:
- 2-3 days

### Strengthen WP4 - Controlled Expansion

Add tasks:
- verify `seed_form_layout_profiles()` matches current DocType schemas
- audit `BLOCKED_DOCTYPES` and document why each blocked category exists
- expand to no more than two doctypes before the verification gate

Acceptance additions:
- seeded profiles contain only valid fieldnames
- unsupported doctypes fall back to native Frappe rendering

Estimate:
- 1-2 days

### Strengthen WP5 - Verification Gate

Add tasks:
- fix the stale `checkDebounce()` browser test
- add backend tests for all `layout_api.py` endpoints
- add backend tests for `Form Layout Profile` validation, default uniqueness, and delete guards
- add browser checks for tabbed forms, flat forms, hidden fields, orphan wrappers, native restore, and profile update behavior

Acceptance additions:
- VFC backend tests are part of the normal construction test run
- browser verification suite passes after its stale assumptions are fixed
- all JS cache busters are bumped for changed VFC assets

Estimate:
- 3-4 days

## 4. Revised Sprint Shape

| WP | Name | Estimate | Purpose |
|----|------|----------|---------|
| WP0 | Doc hygiene | 0.5 day | Align docs with current VFC state |
| WP1 | Engine stabilization | 3-5 days | Correctness, attach behavior, observers, timers |
| WP2 | Architecture decision | 1 day | Decide React/overlay relationship |
| WP3 | Schema and editor hardening | 2-3 days | `for_user`, cache, CDN, recovery |
| WP4 | Controlled expansion | 1-2 days | Seed and test a small expansion set |
| WP5 | Verification gate | 3-4 days | Backend and browser tests |

Total estimate:
- 10.5-15.5 working days

Recommended branch:
- `feat/vfc-phase3-stabilization`

Recommended merge order:
- WP0 -> WP1 -> WP2 -> WP3 -> WP4 -> WP5 -> `develop`

## 5. Decision Points

Before implementation starts, decide:

1. React path disposition: deprecate, gate, or rework to read `Form Layout Profile`.
2. Cache strategy: simple TTL first, or realtime invalidation.
3. Recovery scope: simple "revert to default/native" now, full profile history later.
4. Expansion targets: recommend `Project` and `Cost Item` only for the first expansion pass.

## 6. Manager Recommendation

Approve the VFC Phase 3+ plan with these enhancements.

The most important adjustment is to treat WP1 and WP5 as real engineering work, not housekeeping. The current VFC stack is useful and worth keeping, but it is now large enough that stabilization needs tests, measured browser behavior, and an explicit architecture call.

