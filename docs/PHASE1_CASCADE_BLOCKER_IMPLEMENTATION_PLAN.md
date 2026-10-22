# Phase 1 — Cascade Blocker Implementation Plan
# BOQ Item Stage, BOQ Header, Variation Order

**Author:** Mohamed Elrefae  
**Date:** 2026-06-12  
**Status:** Planning — execution pending  
**Prerequisites:** Generic engine `ct_link_control.js` v12 deployed; Gold Standard `boq_item.js` + `boq_structure.js` v12 patterns finalized  
**Approval:** Pending Engineering Manager sign-off

---

## 1. Task Tracker

| ID | Task | Doctype | File | Est. Effort | Depends On | Verification Tests | Status |
|----|------|---------|------|-------------|------------|-------------------|--------|
| **T1** | Add blocker/accent guidance to BOQ Item Stage form | BOQ Item Stage | `boq_item_stage.js` | 1.5 hr | None | V1–V5 | ⬜ Pending |
| **T2** | Add project accent to BOQ Header form | BOQ Header | `boq_header.js` | 0.5 hr | None (sequential by choice; independent of T1) | V6–V7 | ⬜ Pending |
| **T3** | Add boq_header accent to Variation Order form | Variation Order | `variation_order.js` | 0.5 hr | None (sequential by choice; independent of T1,T2) | V8–V9 | ⬜ Pending |
| **T4** | Cache bust & deploy | — | `hooks.py` | 0.25 hr | T1,T2,T3 | V10 | ⬜ Pending |
| **T5** | End-to-end regression test suite | All 3 doctypes | — | 1.0 hr | T4 | V1–V10 (full suite) | ⬜ Pending |
| **T6** | Evidence capture & sign-off package | — | `evidence/` | 0.25 hr | T5 | — | ⬜ Pending |

**Total estimated:** ~4 hours  
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6

---

## 2. Task Specifications

### T1 — BOQ Item Stage: 4-Level Cascade Blocker

**File:** `apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.js`

**Current state:** Has `set_query` filtering on all 4 cascade fields and downstream clearing on parent change. NO visual blocker/accent/hint guidance.

**Cascade chain:** `project` → `boq_header` → `boq_structure` → `boq_item`

**Changes to make:**

1. Wrap existing code in an IIFE `(function () { ... })()` (matching `boq_structure.js` v12 pattern)

2. Add helper functions (outside `frappe.ui.form.on(...)`):
   - `setFieldAccent(frm, fieldname, active, blocked)` — toggles `ct-boq-step-accent` / `ct-boq-step-blocked` on DOM wrapper
   - `setFieldInlineHint(frm, fieldname, hint, blocked)` — injects/removes `.ct-boq-inline-hint` pill badge in `.help`
   - `markFieldBlocked(frm, fieldname, blocked, hint)` — sets `__ct_boq_blocked`, `only_select`, `filter_description`, calls `set_description()`
   - `updateStageGuidance(frm)` — central function applying all blocker/accent logic

3. Add `updateStageGuidance(frm)` logic:
   ```
   project:         accent when empty (red border — "start here")
   boq_header:      blocked when project empty (orange — "complete parent")
                    accent when project set but header empty (red — "now select this")
   boq_structure:   blocked when header empty
   boq_item:        blocked when structure empty
   ```

4. Wire `updateStageGuidance(frm)` to:
   - `refresh` event
   - `onload_post_render` with 150ms and 600ms `setTimeout` delays
   - `project`, `boq_header`, `boq_structure` change handlers (add `updateStageGuidance(frm)` call after existing `set_value` clears)
   - **Do NOT call from `setup`** — the Gold Standard pattern does not use `setup` for guidance because queries run on dropdown open, not on form setup, so pre-setting flags is unnecessary.

**Inline hints to inject:**
| Field | When Empty | Hint Text |
|-------|-----------|-----------|
| `project` | Yes | "Select Project first" |
| `boq_header` | project set, header empty | "Select BOQ Header first" |
| `boq_structure` | blocked | "Select BOQ Header first" |
| `boq_item` | blocked | "Select BOQ Structure first" |

**Field flags to set (`__ct_boq_blocked`):**
| Field | Flag | When |
|-------|------|------|
| `boq_header` | `true` | project is empty |
| `boq_structure` | `true` | boq_header is empty |
| `boq_item` | `true` | boq_structure is empty |

**Expected visual results after T1:**
| Form State | project | boq_header | boq_structure | boq_item |
|-----------|---------|------------|---------------|----------|
| New form, nothing selected | Red accent — "Select Project first" | Orange blocked — "Select Project first" | Orange blocked — muted | Orange blocked — muted |
| Project selected, nothing else | Normal | Red accent — "Select BOQ Header first" | Orange blocked — "Select BOQ Header first" | Orange blocked — muted |
| Project + Header selected | Normal | Normal | Red accent — "Select BOQ Structure first" | Orange blocked — "Select BOQ Structure first" |
| Project + Header + Structure selected | Normal | Normal | Normal | Red accent — select item |

---

### T2 — BOQ Header: Project Accent

**File:** `apps/construction/construction/construction/doctype/boq_header/boq_header.js`

**Current state:** 623 lines. Has export menus, status advancement, VO creation dialog. NO visual blocker/accent on `project` field. `scope_context_form_defaults.js` pre-fills `project` from user scope context, but if cleared manually, no recovery hint.

**Changes to make:**

1. Wrap helper functions in IIFE at top of file (before `frappe.ui.form.on(...)`):
   - `setFieldAccent(frm, fieldname, active, blocked)`
   - `setFieldInlineHint(frm, fieldname, hint, blocked)`
   - `applyProjectGuidance(frm)`

2. Add `applyProjectGuidance(frm)` — accent `project` when empty, clear when set:
   ```javascript
   function applyProjectGuidance(frm) {
       const hasProject = Boolean(frm.doc.project);
       setFieldAccent(frm, "project", !hasProject, false);
       setFieldInlineHint(frm, "project", hasProject ? null : __("Select Project first"), false);
   }
   ```

3. Wire to `refresh` and add `onload_post_render` with 150ms/600ms delays (race condition mitigation: `scope_context_form_defaults.js` pre-fills `project` asynchronously).

4. Note: `project` is the top of the BOQ chain. There's NO downstream blocking needed — this is an accent-only form.

**Expected visual results after T2:**
| Form State | project field |
|-----------|--------------|
| New BOQ Header, project empty | Red accent border + "Select Project first" badge |
| New BOQ Header, project auto-filled by scope | Normal dropdown |
| Existing BOQ Header, project set | Normal dropdown (read-only after save) |

---

### T3 — Variation Order: BOQ Header Accent

**File:** `apps/construction/construction/construction/doctype/variation_order/variation_order.js`

**Current state:** 396 lines. Has `set_query` filtering on `boq_header` (Locked only), per-row `set_query` on child table `boq_structure` and `boq_item`. NO visual blocker/accent.

**Changes to make:**

1. Wrap helper functions in IIFE at top of file:
   - `setFieldAccent(frm, fieldname, active, blocked)`
   - `setFieldInlineHint(frm, fieldname, hint, blocked)`
   - `markFieldBlocked(frm, fieldname, blocked, hint)`
   - `applyVOBoqGuidance(frm)`

2. Add `applyVOBoqGuidance(frm)`:
   ```javascript
   function applyVOBoqGuidance(frm) {
       const hasHeader = Boolean(frm.doc.boq_header);
       setFieldAccent(frm, "boq_header", !hasHeader, false);
       setFieldInlineHint(frm, "boq_header", hasHeader ? null : __("Select a locked BOQ Header"), false);
       // Set flag so generic engine blocks dropdown until header is selected
       const field = frm.fields_dict.boq_header;
       if (field) {
           field.__ct_boq_blocked = false;  // Not blocked — accent only (no parent to block it)
           field.df.only_select = false;
       // Safety: existing variation_order.js has NO `only_select` or `__ct_boq_blocked`
       // on boq_header (confirmed by grep). Setting false is safe — no conflict.
       }
   }
   ```

3. Wire to `refresh` and `onload_post_render` with 150ms/600ms delays.

4. Note: `boq_header` is the top of the VO chain. Only accent is needed. No downstream blocking because the child table fields are in `VO Line` rows.

**Expected visual results after T3:**
| Form State | boq_header field |
|-----------|-----------------|
| New VO, header empty | Red accent border + "Select a locked BOQ Header" badge |
| New VO, header selected | Normal dropdown |
| VO Line child table | No visual change (covered in Phase 2 — grid blocker support) |

---

### T4 — Cache Bust & Deploy

**File:** `apps/construction/construction/hooks.py`

Bump version parameters:
- `ct_link_control.js`: `?v=12` → `?v=13`
- `filter_fix.js`: `?v=7` (unchanged — no CSS changes in Phase 1)
- `modern_theme.css` (app_include_css): `?v=2.5.6` (unchanged)
- `modern_theme.css` (web_include_css): `?v=2.5.5` (unchanged)

```bash
# Commands to execute:
bench build --app construction
bench clear-cache
bench clear-website-cache
```

Instruct all users to **hard refresh** (`Ctrl+Shift+R` / `Cmd+Shift+R`).

---

## 3. End-to-End Test Plan

### Test Prerequisites

```
☐ frappe-bench running locally
☐ At least one BOQ Header with status "Locked" or "Frozen"
☐ At least one BOQ Structure under that header (leaf node, is_group=0)
☐ At least one BOQ Item under that structure
☐ At least one BOQ Item Stage existing for reference
☐ User Scope Context configured with Project
☐ Browser DevTools open on Console + Elements tabs
```

### V1 — BOQ Item Stage: Empty Form — All Fields Blocked

**Steps:**
1. Navigate to: `/app/boq-item-stage/new`
2. Observe the 4 cascade fields: `project`, `boq_header`, `boq_structure`, `boq_item`

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V1.1 | `project` has red border (`ct-boq-step-accent` class on wrapper) | Elements tab: inspect `.frappe-control[data-fieldname="project"]` |
| V1.2 | `project` has pill badge "Select Project first" | Elements tab: inspect `.frappe-control[data-fieldname="project"] .help .ct-boq-inline-hint` |
| V1.3 | `boq_header` dropdown is orange-blocked (`ct-dropdown-blocked` class) | Elements tab: inspect `.frappe-control[data-fieldname="boq_header"] .ct-unified-dropdown` |
| V1.4 | `boq_header` dropdown button shows "Select Project first" (not field name) | Visual: read the button label text |
| V1.5 | `boq_structure` dropdown is orange-blocked | Visual: orange border, muted appearance |
| V1.6 | `boq_structure` dropdown button shows "Select BOQ Header first" | Visual: read the button label |
| V1.7 | `boq_item` dropdown is orange-blocked | Visual: orange border, muted appearance |
| V1.8 | `boq_item` dropdown button shows "Select BOQ Structure first" | Visual: read the button label |

**Console check:** No JavaScript errors related to `updateStageGuidance`, `markFieldBlocked`, or `setFieldAccent`.

---

### V2 — BOQ Item Stage: Select Project — Header Accent Appears

**Steps:**
1. Continue from V1 state
2. Select a Project in the `project` dropdown
3. Observe the 4 cascade fields update

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V2.1 | `project` field returns to normal (no accent border) | Visual |
| V2.2 | `project` pill badge removed | Elements tab: no `.ct-boq-inline-hint` inside `.help` |
| V2.3 | `boq_header` now has RED accent border (ct-boq-step-accent) | Elements tab |
| V2.4 | `boq_header` dropdown button shows "Select BOQ Header first" or field label | Visual |
| V2.5 | `boq_header` dropdown IS openable (click to verify) | Interaction test |
| V2.6 | `boq_structure` and `boq_item` remain orange-blocked | Visual |

**Regression check:** `set_query` on `boq_header` still filters by selected `project` (open dropdown, verify only that project's headers appear).

---

### V3 — BOQ Item Stage: Select BOQ Header — Structure Accent Appears

**Steps:**
1. Continue from V2 state
2. Select a BOQ Header in the `boq_header` dropdown
3. Observe cascade update

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V3.1 | `project` remains normal | Visual |
| V3.2 | `boq_header` returns to normal (accent removed) | Visual |
| V3.3 | `boq_header` pill badge removed | Elements tab |
| V3.4 | `boq_structure` changed from orange-blocked to RED accent (now the active step) | Visual |
| V3.5 | `boq_structure` dropdown IS openable | Interaction test |
| V3.6 | `boq_structure` `set_query` filters by `boq_header` | Open dropdown; verify only that header's structures appear |
| V3.7 | `boq_item` remains orange-blocked | Visual |
| V3.8 | `boq_item` dropdown button shows "Select BOQ Structure first" | Visual |

---

### V4 — BOQ Item Stage: Select BOQ Structure — Item Accent Appears

**Steps:**
1. Continue from V3 state
2. Select a BOQ Structure (leaf node)
3. Observe cascade update

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V4.1 | `boq_structure` returns to normal | Visual |
| V4.2 | `boq_item` changed from orange-blocked to red accent | Visual |
| V4.3 | `boq_item` dropdown IS openable | Interaction test |
| V4.4 | `boq_item` `set_query` filters by project, boq_header, structure | Open dropdown; verify filtered |
| V4.5 | `boq_item` auto-fetch: selecting a BOQ Item fills `boq_header` and `boq_structure` from DB | Select an item; verify fields populate |

---

### V5 — BOQ Item Stage: Clear Parent — Downstream Clears + Re-Block

**Steps:**
1. From a fully-populated state (all 4 fields filled)
2. Clear the `boq_structure` field (click "Clear All" or set to empty)
3. Verify downstream clears and blocks re-appear
4. Clear the `boq_header` field
5. Verify ALL downstream clears and blocks re-appear
6. Clear the `project` field
7. Verify ALL downstream clears and state returns to V1

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V5.1 | Clear `boq_structure` → `boq_item` clears + re-blocks | Visual |
| V5.2 | Clear `boq_header` → `boq_structure` + `boq_item` clear + re-block | Visual |
| V5.3 | Clear `project` → all 3 downstream fields clear + re-block (V1 state) | Visual |
| V5.4 | No `frm.dirty()` false negatives — dirty flag shows form is modified | Visual check: `frm.dirty()` is true |
| V5.5 | No JavaScript errors in console | Console |

---

### V6 — BOQ Header: Project Accent on New Form

**Steps:**
1. Navigate to: `/app/boq-header/new`
2. Observe the `project` field

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V6.1 | `project` field has red accent border when empty | Visual / Elements tab |
| V6.2 | `project` field has "Select Project first" pill badge | Elements tab: `.ct-boq-inline-hint` |
| V6.3 | After selecting a project, accent + badge clear | Visual |
| V6.4 | If user had scope context, project is pre-filled → NO accent (correct) | Visual |

**Race condition test:** Open a new BOQ Header form when the user HAS a scope context set. The project should auto-fill from scope. Verify NO red flash (150ms/600ms delayed re-check handles the async pre-fill).

---

### V7 — BOQ Header: Accent Persists After Save with Empty Field

**Steps:**
1. Create a new BOQ Header with NO project selected
2. Save the form (allow save if `project` is non-mandatory; if mandatory, test with a different optional Link field)
3. Observe `project` field after save

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V7.1 | If `project` is still empty after save, accent persists | Visual |
| V7.2 | Accent is NOT gated on `frm.is_new()` — independent condition | Verify in source: `!frm.doc.project` not `frm.is_new() && !frm.doc.project` |

---

### V8 — Variation Order: BOQ Header Accent on New Form

**Steps:**
1. Navigate to: `/app/variation-order/new`
2. Observe the `boq_header` field

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V8.1 | `boq_header` has red accent border when empty | Visual |
| V8.2 | `boq_header` has "Select a locked BOQ Header" pill badge | Elements tab |
| V8.3 | After selecting a BOQ Header, accent + badge clear | Visual |
| V8.4 | Selected BOQ Header must have status "Locked" (existing `set_query` enforcement) | Verify dropdown only shows Locked headers |
| V8.5 | Selecting a Locked header → accent disappears → field is normal | Visual |

---

### V9 — Variation Order: Dropdown is NOT Blocked (Accent-Only)

**Steps:**
1. New VO form, `boq_header` empty
2. Click the `boq_header` dropdown button

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V9.1 | Dropdown OPENS (not blocked — `__ct_boq_blocked` is false) | Interaction test |
| V9.2 | "Create a new BOQ Header" option is HIDDEN (only_select may apply) | Open dropdown; verify no "Create New" |
| V9.3 | Only Locked BOQ Headers appear in the dropdown list | Visual verification of options |

---

### V10 — Cache Bust Verification

**Steps:**
1. In DevTools → Network tab, refresh the page
2. Find `ct_link_control.js` in the network request list
3. Verify the URL includes `?v=13` (or current version)
4. Find `filter_fix.js` — verify `?v=7`
5. Find `modern_theme.css` — verify `?v=2.5.6`

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V10.1 | `ct_link_control.js` loaded with `?v=13` | Network tab |
| V10.2 | `filter_fix.js` loaded with `?v=7` | Network tab |
| V10.3 | `modern_theme.css` loaded with `?v=2.5.6` | Network tab |
| V10.4 | Response status is 200 (not 304 cached) | Network tab |

---

## 4. Evidence Capture Protocol

Create directory: `apps/construction/docs/evidence/phase1/`

### Per-Task Evidence Files

| ID | File | Content |
|----|------|---------|
| **E1** | `T1_boq_item_stage_diff.patch` | `git diff` output of `boq_item_stage.js` + `git log --oneline -3` for commit context |
| **E2** | `T2_boq_header_diff.patch` | `git diff` output of `boq_header.js` + `git log --oneline -3` for commit context |
| **E3** | `T3_variation_order_diff.patch` | `git diff` output of `variation_order.js` + `git log --oneline -3` for commit context |
| **E4** | `T4_hooks_diff.patch` | `git diff` output of `hooks.py` + `git log --oneline -3` for commit context |
| **E5** | `T5_test_results.md` | Pass/fail log for V1–V10 |
| **E6** | `screenshots/` | Browser screenshots of each verification state |

### Screenshot Checklist (Capture .png per test)

| Screenshot | Test Step | What to Capture |
|-----------|-----------|----------------|
| SS1 | V1 | Full BOQ Item Stage form — empty, all 4 fields with blocker states visible |
| SS2 | V2.3–V2.4 | Close-up of `boq_header` with red accent + "Select BOQ Header first" text |
| SS3 | V3.4–V3.5 | Close-up of `boq_structure` with red accent, dropdown open showing filtered results |
| SS4 | V4.2–V4.3 | Close-up of `boq_item` with red accent, dropdown open |
| SS5 | V5.3 | Form after clearing `project` — back to V1 state |
| SS6 | V6.1–V6.2 | BOQ Header form — `project` with red accent + "Select Project first" |
| SS7 | V7.1 | BOQ Header after save with empty project — accent persists |
| SS8 | V8.1–V8.2 | Variation Order form — `boq_header` with red accent + "Select a locked BOQ Header" |
| SS9 | V8.4 | Variation Order — `boq_header` dropdown open showing only Locked headers |
| SS10 | V10 | Network tab showing `?v=13`, `?v=7`, `?v=2.5.6` |

### Console Log Capture

Before starting tests, add this to browser Console and run:

```javascript
// Capture all console errors and warnings during testing
const errors = [];
const origError = console.error;
const origWarn = console.warn;
console.error = function(...args) {
    errors.push('[ERROR] ' + args.join(' '));
    origError.apply(console, args);
};
console.warn = function(...args) {
    errors.push('[WARN] ' + args.join(' '));
    origWarn.apply(console, args);
};
// After testing, dump:
// console.log('Captured messages:', errors);
```

Capture the `errors` array output at the end of each test session.

---

## 5. Go/No-Go Criteria for Manager Sign-Off

### Exit Criteria — ALL must pass

| # | Criteria | Verification |
|---|----------|-------------|
| GO1 | V1–V10 all pass with NO failures | `T5_test_results.md` shows 100% pass |
| GO2 | Zero JavaScript errors in Console across all tests | Console log capture clean |
| GO3 | Screenshots SS1–SS10 captured and clear | `evidence/screenshots/` populated |
| GO4 | Diff patches E1–E4 match approved pseudocode | Manual review of `.patch` files |
| GO5 | Existing functionality NOT broken — BOQ Item Stage set_query still works | V2.6, V3.6, V4.4 |
| GO6 | Existing functionality NOT broken — BOQ Header export menus, status advance, VO creation still work | Manual smoke test on BOQ Header |
| GO7 | Existing functionality NOT broken — Variation Order child table set_query still works | Manual smoke test on VO Lines |
| GO8 | No accent flicker on forms where scope context pre-fills fields | V6.4, V2.2 |
| GO9 | Blocked dropdowns do NOT open on click | V1.4–V1.8: click blocked dropdowns, verify menu does not appear |
| GO10 | `bench build` succeeds with zero errors | Build output |

### Rollback Plan

If any GO criteria fails:
1. Revert the specific file(s) via `git checkout -- <file>`
2. Decrement `hooks.py` version params back to previous values
3. `bench build --app construction && bench clear-cache`
4. Re-run the failing test(s) to confirm pre-change state is restored
5. Document failure in `T5_test_results.md` with root cause
6. Re-plan and re-submit for approval

---

## 6. Execution Sequence

```
┌─────────────────────────────────────────────────────────┐
│  PRE-FLIGHT (before any code)                           │
│  ☐ Read current source files (all 3)                    │
│  ☐ Set up evidence/ directory                           │
│  ☐ Open browser, clear console, prepare for screenshots │
├─────────────────────────────────────────────────────────┤
│  T1 — BOQ Item Stage (largest, most complex)            │
│  ☐ Implement helpers + updateStageGuidance              │
│  ☐ Wire to refresh, onload_post_render, change handlers │
│  ☐ Run V1–V5 tests → capture evidence                  │
│  ☐ If any V1–V5 fails → fix before proceeding           │
├─────────────────────────────────────────────────────────┤
│  T2 — BOQ Header                                       │
│  ☐ Implement helpers + applyProjectGuidance             │
│  ☐ Wire to refresh, onload_post_render                  │
│  ☐ Run V6–V7 tests → capture evidence                  │
├─────────────────────────────────────────────────────────┤
│  T3 — Variation Order                                   │
│  ☐ Implement helpers + applyVOBoqGuidance               │
│  ☐ Wire to refresh, onload_post_render                  │
│  ☐ Run V8–V9 tests → capture evidence                  │
├─────────────────────────────────────────────────────────┤
│  T4 — Deploy                                            │
│  ☐ Bump hooks.py versions                              │
│  ☐ bench build + clear-cache + clear-website-cache      │
│  ☐ Run V10 test → capture evidence                     │
├─────────────────────────────────────────────────────────┤
│  T5 — Full Regression                                   │
│  ☐ Re-run V1–V10 in sequence                            │
│  ☐ Smoke-test existing features on all 3 doctypes       │
│  ☐ Document results in T5_test_results.md              │
├─────────────────────────────────────────────────────────┤
│  T6 — Sign-Off Package                                  │
│  ☐ Organize all evidence files                          │
│  ☐ Write summary for manager                           │
│  ☐ Archive evidence/phase1/                             │
└─────────────────────────────────────────────────────────┘
```

---

*Plan version 1.0. Execution begins upon Engineering Manager approval.*
