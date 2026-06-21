# VFC Phase 3+ Revision Plan

> **Date:** 2026-06-21
> **Status:** Draft for next sprint
> **Scope:** Full revision of the current Form Layout Engine implementation before any new VFC expansion work
> **Related docs:** `docs/handover/VFC_PROJECT_TABS_DEBUG_REPORT.md`, `docs/FEATURE_STATUS_REPORT_2026-05-31.md`, `docs/handover/SESSION_REPORT_2026-06-21_WP1-WP7.md`

## 1. Purpose

The current VFC / Form Layout Engine works, but it is carrying accumulated design debt:

- stale presets tied to older BOQ field names
- duplicate attachment paths and refresh races
- uneven behavior across tabbed and non-tabbed forms
- missing or thin test coverage around the runtime engine and the config panel
- two overlapping layout approaches in the codebase

This plan starts with a full revision of the current implementation so we can stabilize the engine before adding new Phase 3+ capabilities.

## 2. Goals

- Make the current VFC implementation predictable and supportable.
- Remove stale assumptions about BOQ field names and form shapes.
- Eliminate duplicate attach / refresh behavior.
- Decide one primary architecture for layout control and keep the other path subordinate.
- Add enough tests that future changes do not silently break tabbed forms or field visibility.
- Only after stabilization, expand Phase 3+ to additional doctypes and profile features.

## 3. Non-Goals

- Do not mix this plan with BOQ report work.
- Do not mix this plan with accounting integration work.
- Do not introduce new unrelated form systems.
- Do not broaden scope to visual redesign work unless it directly supports layout stability.

## 4. Current State Summary

The live implementation already includes:

- `construction/public/js/vfc_layout_engine.js`
- `construction/public/js/vite_layout_controls.js`
- `construction/public/js/vfc_layout_engine_tests.js`
- `construction/construction/api/layout_api.py`
- `construction/construction/doctype/form_layout_profile/`
- `construction/public/js/vfc_config.js`

The implementation is functional, but the current code and prior review notes show the following risks:

- stale BOQ presets in the config panel
- duplicate `attach()` behavior on refresh
- tabbed-form fragility and DOM cleanup edge cases
- a split between the database-backed overlay and the newer React-based form work
- no clearly enforced schema path for personal overrides

## 5. Recommended Direction

Use the **database-backed Frappe overlay** as the primary architecture for the next stage.

Why:

- it already stores layout state in the database
- it aligns with current `Form Layout Profile` records and backend APIs
- it is easier to reason about for support, QA, and migrations
- it can be validated with server-side tests and browser smoke checks

The React-based layout work should be treated as secondary unless we deliberately re-scope it into a read-only or utility layer.

## 6. Work Packages

### WP1 - Stabilize the Existing Engine

Objective:
- make the current engine safe to keep using while we revise it

Tasks:
- audit all current VFC entry points
- remove stale BOQ preset references
- add an unknown-field guard that logs once and skips invalid fields
- make attach behavior idempotent and debounce repeated refresh triggers
- ensure tabbed-form cleanup restores native wrappers safely
- keep the debug-gated logging model intact

Deliverables:
- updated `vfc_layout_engine.js`
- updated `vite_layout_controls.js`
- updated `vfc_layout_engine_tests.js`
- any hook or asset version bumps required by changed JS

Acceptance criteria:
- no duplicate attach on a single refresh cycle
- no silent failure when a preset references a missing field
- tabbed forms remain visible and usable after repeated refreshes
- debug logging remains silent unless explicitly enabled

### WP2 - Decide and Document the Architecture

Objective:
- close the loop on the two-path architecture and prevent future drift

Tasks:
- confirm the overlay is the production path for VFC Phase 3+
- document whether the React layout layer is:
  - deprecated
  - kept as read-only tooling
  - or reworked to read from `Form Layout Profile`
- write the decision into the repo docs so later work does not re-open the debate

Deliverables:
- a short architecture decision note
- any doc updates needed in `AGENTS.md`, `SESSION_MEMORY.md`, or the VFC handover docs

Acceptance criteria:
- one clear primary architecture is documented
- future feature work has a single source of truth

### WP3 - Harden the Profile Schema and Editor

Objective:
- make the saved layout data more expressive and less brittle

Tasks:
- review whether `for_user` is needed for personal overrides
- review whether section-level fields like `column_count`, `collapsible`, and `collapsed_by_default` are fully wired end-to-end
- confirm layout save/restore behavior is stable across reloads
- ensure profile validation rejects or normalizes invalid field references

Deliverables:
- updated profile schema if needed
- updated layout API/controller logic
- migration or patch support if schema changes are introduced

Acceptance criteria:
- profile data can represent both shared and personal layouts cleanly
- invalid layout data is rejected or normalized before it reaches runtime

### WP4 - Seed and Expand in a Controlled Way

Objective:
- expand beyond the current BOQ pilot only after the core engine is stable

Tasks:
- seed a small set of role-based profiles for one or two high-value doctypes
- confirm fallback to native Frappe rendering when no profile exists
- verify the layout engine behaves correctly on both tabbed and flat doctypes
- keep the expansion list small and testable

Suggested expansion targets:
- `Project`
- `Cost Item`
- one additional high-value construction DocType if the first two are stable

Deliverables:
- seeded profile fixtures or patch
- test coverage for the new profile paths

Acceptance criteria:
- new profiles render correctly
- native forms remain untouched when no profile exists
- no regressions in current BOQ forms

### WP5 - Verification and Cleanup

Objective:
- leave the VFC stack in a state that is easy to support

Tasks:
- run the browser smoke checks for tab switching, visibility, and orphan cleanup
- run the existing JS verification suite
- run the relevant backend tests for layout profile and API behavior
- remove or archive any obsolete debug notes that are now superseded

Deliverables:
- updated test evidence
- final cleanup notes in the handover docs

Acceptance criteria:
- layout tests pass
- browser smoke checks pass on both tabbed and non-tabbed forms
- no unresolved stale preset references remain

## 7. Suggested Sequence

1. WP1 - Stabilize the existing engine
2. WP2 - Decide and document the architecture
3. WP3 - Harden the profile schema and editor
4. WP4 - Seed and expand in a controlled way
5. WP5 - Verification and cleanup

## 8. Key Risks

- Refresh races can still hide fields if attach behavior is not fully deterministic.
- The two-architecture split can reappear if we do not document the decision clearly.
- New seeded profiles can create false confidence if the fallback path is not verified.
- Schema expansion can destabilize existing saved profiles if migration behavior is not tested.

## 9. Definition of Done

The VFC Phase 3+ revision is complete when:

- the current engine is stable and debounced
- stale presets and invalid field references are handled cleanly
- the architecture decision is documented
- at least a small set of new profiles is seeded and tested
- existing BOQ forms still behave correctly
- browser and backend verification evidence is captured

## 10. Next-Sprint Boundary

This plan intentionally stops at VFC stabilization and controlled expansion.

BOQ reports and Accounting Integration should each get their own separate plans after this one is approved, so those backbone items do not blur together with VFC revision work.

