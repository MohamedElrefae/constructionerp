# Phase 1 — Manager Sign-Off Verification Checklist

**Plan:** PHASE1_CASCADE_BLOCKER_IMPLEMENTATION_PLAN.md  
**Evidence:** evidence/phase1/  
**Engineer:** Mohamed Elrefae  
**Date:** _______________

---

## Go Criteria (ALL must be checked)

### Code Quality

| # | Check | Source | Pass? |
|---|-------|--------|-------|
| C1 | `boq_item_stage.js` uses IIFE pattern (matching `boq_structure.js` v12) | `boq_item_stage.js` line 1 | [x] |
| C2 | `setFieldInlineHint` is private function inside IIFE, NOT a key in `frappe.ui.form.on(...)` | `boq_item_stage.js` — no `setFieldInlineHint:` key inside on() | [x] |
| C3 | `markFieldBlocked()` sets all 4 flags: `__ct_boq_blocked`, `only_select`, `filter_description`, `set_description()` | `boq_item_stage.js` — helper function body | [x] |
| C4 | `updateStageGuidance(frm)` called from `refresh`, `onload_post_render` (150ms/600ms), `project`/`boq_header`/`boq_structure` change handlers | `boq_item_stage.js` — wiring locations | [x] |
| C4b | `updateStageGuidance` is NOT called from `setup` (Gold Standard does not use `setup` for guidance — queries fire on open, not on setup) | `boq_item_stage.js` — grep for `setup` → no guidance call | [x] |
| C5 | `boq_header.js` `applyProjectGuidance` uses `!frm.doc.project` NOT `frm.is_new() && !frm.doc.project` | `boq_header.js` — condition check | [x] |
| C6 | `boq_header.js` has `onload_post_render` with 150ms/600ms delays | `boq_header.js` — handler | [x] |
| C7 | `variation_order.js` `applyVOBoqGuidance` uses `!frm.doc.boq_header` NOT `frm.is_new() && !frm.doc.boq_header` | `variation_order.js` — condition check | [x] |
| C8 | `variation_order.js` `boq_header.__ct_boq_blocked = false` (accent-only, not blocked) | `variation_order.js` — flag | [x] |
| C8b | `variation_order.js` existing `only_select` state verified: no conflict — existing file has zero `only_select` or `__ct_boq_blocked` references (confirmed by grep). Setting `false` is safe. | `variation_order.js` — grep output | [x] |
| C9 | All `filter_description` values set via `__(...)` (pre-translated — no double-translation in engine) | All 3 files — grep for `filter_description` | [x] |
| C10 | `hooks.py` versions bumped and consistent with evidence | `hooks.py` — version params | [x] |

### Test Results

| # | Check | Evidence | Pass? |
|---|-------|----------|-------|
| T1 | V1 (Empty form — all blocked) → 100% pass | `T5_test_results.md` §V1 | [x] |
| T2 | V2 (Select project — header accent) → 100% pass | `T5_test_results.md` §V2 | [x] |
| T3 | V3 (Select header — structure accent) → 100% pass | `T5_test_results.md` §V3 | [x] |
| T4 | V4 (Select structure — item accent) → 100% pass | `T5_test_results.md` §V4 | [x] |
| T5 | V5 (Clear parent — downstream re-block) → 100% pass | `T5_test_results.md` §V5 | [x] |
| T6 | V6 (BOQ Header project accent) → 100% pass | `T5_test_results.md` §V6 | [x] |
| T7 | V7 (Accent persists after save) → 100% pass | `T5_test_results.md` §V7 | [x] |
| T8 | V8–V9 (VO boq_header accent) → 100% pass | `T5_test_results.md` §V8–V9 | [x] |
| T9 | V10 (Cache bust) → 100% pass | `T5_test_results.md` §V10 | [x] |
| T10 | Regression smoke tests → 100% pass | `T5_test_results.md` §Regression | [x] |


### Evidence Completeness

| # | Check | Path | Present? |
|---|-------|------|----------|
| E1 | `T1_boq_item_stage_diff.patch` exists | `evidence/phase1/` | [x] |
| E2 | `T2_boq_header_diff.patch` exists | `evidence/phase1/` | [x] |
| E3 | `T3_variation_order_diff.patch` exists | `evidence/phase1/` | [x] |
| E4 | `T4_hooks_diff.patch` exists | `evidence/phase1/` | [x] |
| E5 | `T5_test_results.md` completed (all pass/fail cells filled) | `evidence/phase1/` | [x] |
| E6 | SS1–SS10 screenshots captured | `evidence/phase1/screenshots/` | [x] |
| E7 | Console error log captured and reviewed | `T5_test_results.md` §Console Error Log | [x] |


### Build & Deploy

| # | Check | Pass? |
|---|-------|-------|
| B1 | `bench build --app construction` exits 0 with no errors | [x] |
| B2 | `bench clear-cache` completes | [x] (skipped — no Redis) |
| B3 | `bench clear-website-cache` completes | [x] (skipped — no Redis) |
| B4 | Production hard-refresh instructions communicated to testers | [ ] |

---

## Sign-Off

**Branch:** `feature/vite-ui-v1` (verified: `git branch --show-current`)

**Phase 1 implementation approved for merge:**

- [ ] All Go Criteria pass
- [ ] Zero console errors
- [ ] All screenshots clear and show expected states
- [ ] No regression in existing features

**Approved by:** ___________________________ **Date:** _______________

**Merged by:** ___________________________ **Date:** _______________

---

*This checklist is part of the Phase 1 implementation plan. Do not execute code changes until all parties have signed.*
