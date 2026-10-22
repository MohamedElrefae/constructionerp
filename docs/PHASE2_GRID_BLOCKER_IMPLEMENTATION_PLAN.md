# Phase 2 — Grid Blocker Implementation Plan
# Transaction Child Table Cascade Blocker (8 DocTypes)

**Author:** Mohamed Elrefae
**Date:** 2026-06-12
**Status:** Planning — execution pending
**Prerequisites:** Phase 1 (master form blocker/accent) complete; `ct_link_control.js` v13 deployed; `boq_filters.js` v4 baseline
**Approval:** Pending Engineering Manager sign-off

---

## 1. Architecture Overview

### What Phase 2 adds

Phase 1 added visual blocker/accent to **master form fields** (BOQ Item Stage, BOQ Header, Variation Order). Phase 2 adds the same visual feedback to **grid rows in child tables** across 8 transaction DocTypes.

The grid rows already have cascade-clearing logic (when `boq_header` changes, downstream `boq_structure`/`boq_item`/`boq_item_stage` are cleared). What's missing: **visual indication** (red accent on the active step, orange blocker with label on blocked fields) within each grid row.

### Cascade chain (same as Phase 1)

```
project (parent form or row-level)
  → boq_header (grid row)
    → boq_structure (grid row)
      → boq_item (grid row)
        → boq_item_stage (grid row)
```

### Gate mechanism (unique to transactions)

Each row has a gate field that must be set before BOQ fields are relevant:

| DocType | Gate Field | Gate Value |
|---------|------------|------------|
| Purchase Order Item | `expense_category` | "Direct" |
| Purchase Receipt Item | `expense_category` | "Direct" |
| Purchase Invoice Item | `expense_category` | "Direct" |
| Sales Invoice Item | `is_progress_billing` | 1 (checked) |
| Stock Entry Detail | `expense_category` | "Direct" |
| Timesheet Detail | `designation` | In `direct_labor_designations` |
| Journal Entry Account | `expense_category` | "Direct" |
| Material Request Item | `expense_category` | "Direct" |

When the gate is **closed** (not in Direct mode), all BOQ fields should be visually **muted/hidden** — no accent, no blocker, just inert.

When the gate is **open**, the cascade blocker chain activates identically to Phase 1.

### Key file

- **`boq_filters.js`** — central hub (470 lines, v4). All 8 transaction DocTypes are wired from this single file. Parent DocTypes get `setup`/`onload`/`refresh` handlers. Child DocTypes get field change handlers (`boq_header`, `boq_structure`, etc.).

---

## 2. Task Tracker

| ID | Task | File | Est. Effort | Depends On | Verification Tests | Status |
|----|------|------|-------------|------------|-------------------|--------|
| **T1** | Add `setGridBlocked()` helper with debounce + `applyGridGuidance(frm, cdt, cdn)` | `boq_filters.js` | 2 hr | None | V1–V5 | ⬜ Pending |
| **T2** | Wire `form_render` + change handlers into all 8 transaction DocTypes | `boq_filters.js` | 1.5 hr | T1 | V1–V5 | ⬜ Pending |
| **T3** | Bump version + build + clear caches | `hooks.py` | 0.25 hr | T1, T2 | V6 | ⬜ Pending |
| **T4** | End-to-end test suite (V1–V6) | — | 1.5 hr | T3 | V1–V6 | ⬜ Pending |
| **T5** | Evidence capture & sign-off | `evidence/` | 0.25 hr | T4 | — | ⬜ Pending |

**Total estimated:** ~5.5 hours
**Critical path:** T1 → T2 → T3 → T4 → T5

---

## 3. Task Specifications

### T1 — `setGridBlocked()` Helper with Debounce

**File:** `apps/construction/construction/public/js/boq_filters.js`

**Current state:** Has `clearDownstream()`, `clearAllBoqFields()`, `setChildQueries()` for grid filtering. NO visual blocker/accent/hint on grid fields.

**Changes to make:**

#### 3.1 Add debounce utility

```javascript
function debounce(fn, wait) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), wait);
    };
}
```

Place at module top, after `"use strict"`.

#### 3.2 Add `setGridAccent(frm, cdt, cdn, fieldname, active, blocked)`

Toggles `ct-boq-step-accent` / `ct-boq-step-blocked` CSS classes on a grid row cell's `.frappe-control` wrapper.

```javascript
function setGridAccent(frm, cdt, cdn, fieldname, active, blocked) {
    const grid = frm.fields_dict[tableFieldFor(frm)] && frm.fields_dict[tableFieldFor(frm)].grid;
    if (!grid) return;
    const gridRow = grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn];
    if (!gridRow) return;
    const $wrapper = gridRow.wrapper && $(gridRow.wrapper).find(`.frappe-control[data-fieldname="${fieldname}"]`);
    if (!$wrapper || !$wrapper.length) return;
    $wrapper.toggleClass("ct-boq-step-accent", !!active);
    $wrapper.toggleClass("ct-boq-step-blocked", !!blocked);
}
```

#### 3.3 Add `markGridFieldBlocked(frm, cdt, cdn, fieldname, blocked, hint)`

Sets `__ct_boq_blocked`, `only_select`, `filter_description` on the grid field instance. Also calls `set_description()` for native Frappe description display.

```javascript
function markGridFieldBlocked(frm, cdt, cdn, fieldname, blocked, hint) {
    const tableField = tableFieldFor(frm);
    if (!tableField) return;
    const grid = frm.fields_dict[tableField] && frm.fields_dict[tableField].grid;
    if (!grid) return;
    const gridRow = grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn];
    if (!gridRow || !gridRow.fields_dict) return;
    const field = gridRow.fields_dict[fieldname];
    if (!field) return;
    field.df.only_select = !!blocked;
    field.__ct_boq_blocked = !!blocked;
    field.df.filter_description = blocked ? hint : "";
    if (typeof field.set_description === "function") {
        field.set_description(blocked ? hint : "");
    }
}
```

> **IMPORTANT:** `grid.get_field(fieldname)` returns the **column-level definition** shared across all rows — setting flags on it would cross-contaminate all rows. Use `gridRow.fields_dict[fieldname]` for the per-row field instance. Note: `gridRow.fields_dict` is only populated when the row is **expanded** (in form-style editing, not inline). The CSS class approach (`setGridAccent`) works reliably in both modes. This is a known Frappe constraint.

#### 3.4 Add `setGridInlineHint(frm, cdt, cdn, fieldname, hint, blocked)`

Injects/removes `.ct-boq-inline-hint` pill badge in the grid cell's help area.

```javascript
function setGridInlineHint(frm, cdt, cdn, fieldname, hint, blocked) {
    const grid = frm.fields_dict[tableFieldFor(frm)] && frm.fields_dict[tableFieldFor(frm)].grid;
    if (!grid) return;
    const gridRow = grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn];
    if (!gridRow) return;
    const $wrapper = gridRow.wrapper && $(gridRow.wrapper).find(`.frappe-control[data-fieldname="${fieldname}"]`);
    if (!$wrapper || !$wrapper.length) return;
    const $help = $wrapper.find(".help").first();
    if (!$help.length) return;
    $wrapper.toggleClass("ct-boq-has-inline-hint", !!hint);
    $wrapper.toggleClass("ct-boq-inline-hint-blocked", !!blocked);
    $help.find(".ct-boq-inline-hint").remove();
    if (hint) {
        $help.append(
            $("<span>", {
                class: "ct-boq-inline-hint",
                text: hint,
                title: hint,
            })
        );
    }
}
```

#### 3.5 Add `applyGridGuidance(frm, cdt, cdn)` — central guidance function

```javascript
function applyGridGuidance(frm, cdt, cdn) {
    const row = getRow(cdt, cdn);
    if (!row) return;
    const gateIsOpen = gateOpen(frm, row);
    const hasProject = Boolean(rowProject(frm, row));
    const hasBoqHeader = Boolean(row.boq_header);
    const hasBoqStructure = Boolean(row.boq_structure);
    const hasBoqItem = Boolean(row.boq_item);
    const hasBoqItemStage = Boolean(row.boq_item_stage);

    // Gate closed → all BOQ fields muted (no accent, not blocked — just visually inert)
    if (!gateIsOpen) {
        ["boq_header", "boq_structure", "boq_item", "boq_item_stage"].forEach((fn) => {
            setGridAccent(frm, cdt, cdn, fn, false, false);
            markGridFieldBlocked(frm, cdt, cdn, fn, false, "");
            setGridInlineHint(frm, cdt, cdn, fn, null, false);
        });
        return;
    }

    // boq_header: accent when project set but header empty; blocked when project empty
    setGridAccent(frm, cdt, cdn, "boq_header", !hasBoqHeader && hasProject, !hasProject);
    markGridFieldBlocked(frm, cdt, cdn, "boq_header", !hasProject, __("Select Project first"));
    setGridInlineHint(
        frm, cdt, cdn, "boq_header",
        !hasProject ? __("Select Project first") : (!hasBoqHeader ? __("Select BOQ Header first") : null),
        !hasProject
    );

    // boq_structure: blocked when header empty; accent when header set but structure empty
    setGridAccent(frm, cdt, cdn, "boq_structure", !hasBoqStructure && hasBoqHeader, !hasBoqHeader);
    markGridFieldBlocked(frm, cdt, cdn, "boq_structure", !hasBoqHeader, __("Select BOQ Header first"));
    setGridInlineHint(
        frm, cdt, cdn, "boq_structure",
        !hasBoqHeader ? __("Select BOQ Header first") : (!hasBoqStructure ? __("Select BOQ Structure first") : null),
        !hasBoqHeader
    );

    // boq_item: blocked when structure empty; accent when structure set but item empty
    setGridAccent(frm, cdt, cdn, "boq_item", !hasBoqItem && hasBoqStructure, !hasBoqStructure);
    markGridFieldBlocked(frm, cdt, cdn, "boq_item", !hasBoqStructure, __("Select BOQ Structure first"));
    setGridInlineHint(
        frm, cdt, cdn, "boq_item",
        !hasBoqStructure ? __("Select BOQ Structure first") : (!hasBoqItem ? __("Select BOQ Item first") : null),
        !hasBoqStructure
    );

    // boq_item_stage: accented when item is set but stage not yet chosen; blocked when no item
    setGridAccent(frm, cdt, cdn, "boq_item_stage", !hasBoqItemStage && hasBoqItem, !hasBoqItem);
    markGridFieldBlocked(frm, cdt, cdn, "boq_item_stage", !hasBoqItem, __("Select BOQ Item first"));
    setGridInlineHint(
        frm, cdt, cdn, "boq_item_stage",
        !hasBoqItem ? __("Select BOQ Item first") : null,
        !hasBoqItem
    );
}
```

> **Note:** `boq_item_stage` uses `hasBoqItemStage` as an explicit variable (`!hasBoqItemStage && hasBoqItem`) instead of the opaque `!hasBoqItem && hasBoqItem`. This makes intent clear: accent appears when item is selected AND stage is not yet chosen; blocked when no item.

#### 3.6 Add debounced version for rapid-change events

```javascript
const applyGridGuidanceDebounced = debounce(function (frm, cdt, cdn) {
    applyGridGuidance(frm, cdt, cdn);
}, 50);
```

#### 3.7 Wire `form_render` in child events

Add `form_render` handler to the child DocTypes event block (existing `wireChildEvents` function):

```javascript
form_render(frm, cdt, cdn) {
    applyGridGuidance(frm, cdt, cdn);
},
```

Add `applyGridGuidance` calls alongside existing `clearDownstream` calls in change handlers:

```javascript
boq_header(frm, cdt, cdn) {
    clearDownstream(frm, cdt, cdn, "boq_header");
    applyGridGuidance(frm, cdt, cdn);
},
boq_structure(frm, cdt, cdn) {
    clearDownstream(frm, cdt, cdn, "boq_structure");
    applyGridGuidance(frm, cdt, cdn);
},
boq_item(frm, cdt, cdn) {
    clearDownstream(frm, cdt, cdn, "boq_item");
    applyGridGuidance(frm, cdt, cdn);
},
```

Also wire gate change handlers to re-evaluate guidance:

```javascript
expense_category(frm, cdt, cdn) {
    // existing gate-clearing code...
    applyGridGuidanceDebounced(frm, cdt, cdn);
},
is_progress_billing(frm, cdt, cdn) {
    applyGateClearing(frm, cdt, cdn);
    applyGridGuidance(frm, cdt, cdn);
},
employee(frm, cdt, cdn) {
    applyGateClearing(frm, cdt, cdn);
    applyGridGuidanceDebounced(frm, cdt, cdn);
},
designation(frm, cdt, cdn) {
    applyGateClearing(frm, cdt, cdn);
    applyGridGuidance(frm, cdt, cdn);
},
```

---

### T2 — Wire into Parent Events

**File:** `boq_filters.js` (same file)

#### 2.1 Add `onload_post_render` to parent DocType events

Add `onload_post_render` handler in `wireParent()` with delayed re-apply:

```javascript
onload_post_render(frm) {
    const tableField = tableFieldFor(frm);
    const grid = frm.fields_dict[tableField] && frm.fields_dict[tableField].grid;
    if (!grid) return;
    (frm.doc[tableField] || []).forEach((row) => {
        applyGridGuidance(frm, row.doctype, row.name);
    });
    setTimeout(() => {
        (frm.doc[tableField] || []).forEach((row) => {
            applyGridGuidance(frm, row.doctype, row.name);
        });
    }, 150);
    setTimeout(() => {
        (frm.doc[tableField] || []).forEach((row) => {
            applyGridGuidance(frm, row.doctype, row.name);
        });
    }, 600);
},
```

#### 2.2 Wire `project` change handler on parent

When parent `project` changes, all rows need re-guidance:

```javascript
project(frm) {
    const tableField = tableFieldFor(frm);
    if (!tableField) return;
    (frm.doc[tableField] || []).forEach((row) => {
        clearFields(row.doctype, row.name, ["boq_header", "boq_structure", "boq_item", "boq_item_stage"]);
        applyGridGuidance(frm, row.doctype, row.name);
    });
    frm.refresh_field(tableField);
},
```

---

### T3 — Cache Bust & Deploy

**File:** `apps/construction/construction/hooks.py`

Bump version parameter:
- `boq_filters.js`: `?v=4` → `?v=5`

```bash
bench build --app construction
bench clear-cache
bench clear-website-cache
```

Instruct users to **hard refresh** (`Ctrl+Shift+R` / `Cmd+Shift+R`).

---

## 4. End-to-End Test Plan

### Test Prerequisites

```
☐ frappe-bench running locally
☐ At least one project exists
☐ At least one BOQ Header with status "Locked"
☐ At least one BOQ Structure (leaf, is_group=0) under that header
☐ At least one BOQ Item under that structure
☐ User Scope Context configured with Project
☐ Browser DevTools open on Console + Elements tabs
☐ At least one Material Request (or any transaction DocType) with items
```

### V1 — Transaction Grid: Gate Closed — All BOQ Fields Muted

**Steps:**
1. Navigate to `/app/material-request/new`
2. Add a row in the Items child table
3. Leave `expense_category` as default (not "Direct")
4. Observe `boq_header`, `boq_structure`, `boq_item`, `boq_item_stage` columns

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V1.1 | `boq_header` has NO accent, NO blocker (visually inert) | Visual |
| V1.2 | `boq_structure` has NO accent, NO blocker | Visual |
| V1.3 | `boq_item` has NO accent, NO blocker | Visual |
| V1.4 | `boq_item_stage` has NO accent, NO blocker | Visual |
| V1.5 | `boq_header` dropdown opens normally (not blocked) | Interaction test |

### V2 — Transaction Grid: Gate Opens — Cascade Blocker Activates

**Steps:**
1. Continue from V1
2. Set `expense_category` to "Direct" on the row
3. Observe BOQ fields update

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V2.1 | `boq_header` now shows blocked state (orange, "Select Project first") if project empty | Visual |
| V2.2 | `boq_structure` shows blocked state | Visual |
| V2.3 | `boq_item` shows blocked state | Visual |
| V2.4 | `boq_item_stage` shows blocked state | Visual |
| V2.5a | Set `boq_header` → `boq_structure` accent appears (red) | Visual |
| V2.5b | Set `boq_structure` → `boq_item` accent appears (red) | Visual |
| V2.5c | Set `boq_item` → `boq_item_stage` accent appears (red) | Visual |
| V2.6 | Each downstream field blocks correctly when parent is cleared | Visual |

### V3 — Project Change Re-Blocks All Rows

**Steps:**
1. Create a Material Request with 2+ items, each with a project set
2. Clear the parent `project` field
3. Observe all rows

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V3.1 | All rows' BOQ headers re-block to "Select Project first" | Visual |
| V3.2 | All rows' downstream fields return to blocked state | Visual |
| V3.3 | Set a new project → all rows' guidance updates | Visual |

### V4 — Repeat Across DocTypes (Sample Test)

Pick 3 of the 8 DocTypes and repeat V1–V3:

| Check | Assertion | Method |
|-------|-----------|--------|
| V4.1 | Purchase Order behavior matches V1–V3 | Visual |
| V4.2 | Sales Invoice (`is_progress_billing` gate) behavior matches | Visual |
| V4.3 | Journal Entry behavior matches | Visual |

### V5 — Console & DOM Verification

**Steps:**
1. Open one transaction form, trigger all cascade states
2. Capture console log

**Expected Results:**
| Check | Assertion | Method |
|-------|-----------|--------|
| V5.1 | No JavaScript errors related to `setGridAccent`, `markGridFieldBlocked`, `applyGridGuidance` | Console |
| V5.2 | `ct-boq-step-blocked` class present on blocked grid cells | Elements tab |
| V5.3 | `ct-boq-step-accent` class present on active-step grid cells | Elements tab |
| V5.4 | Inline hint `.ct-boq-inline-hint` present on blocked fields | Elements tab |

### V6 — Cache Bust

| Check | Assertion | Method |
|-------|-----------|--------|
| V6.1 | `boq_filters.js?v=5` loaded | Network tab |

---

## 5. Evidence Capture Protocol

Create directory: `apps/construction/docs/evidence/phase2/`

### Per-Task Evidence Files

| ID | File | Content |
|----|------|---------|
| **E1** | `T1_boq_filters_diff.patch` | `git diff` of `boq_filters.js` + `git log --oneline -3` |
| **E2** | `T3_hooks_diff.patch` | `git diff` of `hooks.py` + `git log --oneline -3` |
| **E3** | `T4_test_results.md` | Pass/fail log for V1–V6 |
| **E4** | `screenshots/` | Browser screenshots |

### Screenshot Checklist

| Screenshot | Test Step | What to Capture |
|-----------|-----------|----------------|
| SS1 | V1 | Material Request new form — gate closed, BOQ fields muted |
| SS2 | V2.1–V2.4 | After gate opens — all blocked with "Select Project first" |
| SS3 | V2.5 | After selecting cascade — header, structure, item, stage accent states |
| SS4 | V3 | After clearing project — all rows re-blocked |
| SS5 | V4 | Purchase Order or Sales Invoice — comparable state |
| SS6 | V5.2–V5.4 | Elements tab showing CSS classes on grid cells |

---

## 6. Manager Sign-Off Checklist

### Code Quality

| # | Check | Source | Pass? |
|---|-------|--------|-------|
| C1 | `setGridAccent` uses `grid.grid_rows_by_docname` — does NOT assume `grid_row.doc` exists | `boq_filters.js` — function body | [ ] |
| C2 | `markGridFieldBlocked` sets all 4 flags: `__ct_boq_blocked`, `only_select`, `filter_description`, `set_description()` | `boq_filters.js` — function body | [ ] |
| C3 | `applyGridGuidance` handles gate-closed state (all BOQ fields muted) | `boq_filters.js` — guidance function | [ ] |
| C4 | `applyGridGuidance` called from `form_render` + change handlers (`boq_header`, `boq_structure`, `boq_item`) | `boq_filters.js` — wiring | [ ] |
| C5 | `onload_post_render` on parent with 150ms/600ms delayed re-apply applied to ALL existing rows | `boq_filters.js` — `wireParent` | [ ] |
| C6 | Parent `project` change handler clears + re-guides ALL rows | `boq_filters.js` — `wireParent` | [ ] |
| C7 | Debounce wrapper (50ms) used for rapid-change events (`expense_category`, `employee`) | `boq_filters.js` — debounce utility | [ ] |
| C8 | Debounce utility defined at module top (not inside a loop) | `boq_filters.js` — placement | [ ] |
| C9 | All `filter_description` values set via `__(...)` (pre-translated) | `boq_filters.js` — grep | [ ] |
| C10 | Version bumped in `hooks.py`: `boq_filters.js?v=4` → `?v=5` | `hooks.py` — param | [ ] |

### Test Results

| # | Check | Evidence | Pass? |
|---|-------|----------|-------|
| T1 | V1 (Gate closed — muted) → 100% pass | `T4_test_results.md` §V1 | [ ] |
| T2 | V2 (Gate opens — cascade activates) → 100% pass | `T4_test_results.md` §V2 | [ ] |
| T3 | V3 (Project change re-blocks all rows) → 100% pass | `T4_test_results.md` §V3 | [ ] |
| T4 | V4 (Cross-DocType consistency) → 100% pass | `T4_test_results.md` §V4 | [ ] |
| T5 | V5 (Console/DOM verification) → 100% pass | `T4_test_results.md` §V5 | [ ] |
| T6 | V6 (Cache bust) → 100% pass | `T4_test_results.md` §V6 | [ ] |

### Evidence Completeness

| # | Check | Path | Present? |
|---|-------|------|----------|
| E1 | `T1_boq_filters_diff.patch` exists | `evidence/phase2/` | [ ] |
| E2 | `T3_hooks_diff.patch` exists | `evidence/phase2/` | [ ] |
| E3 | `T4_test_results.md` completed | `evidence/phase2/` | [ ] |
| E4 | SS1–SS6 screenshots captured | `evidence/phase2/screenshots/` | [ ] |
| E5 | Console error log captured and clean | `T4_test_results.md` §Console | [ ] |

### Build & Deploy

| # | Check | Pass? |
|---|-------|-------|
| B1 | `bench build --app construction` exits 0 with no errors | [ ] |
| B2 | `bench clear-cache` completes | [ ] |
| B3 | `bench clear-website-cache` completes | [ ] |
| B4 | Hard-refresh instructions communicated | [ ] |

---

## 7. Implementation Notes

### CSS re-use

Phase 2 re-uses the same CSS classes from Phase 1:
- `ct-boq-step-accent` — red border on active field
- `ct-boq-step-blocked` — orange blocker state
- `ct-boq-inline-hint` — pill badge in `.help` area
- `ct-boq-inline-hint-blocked` — orange pill badge

No CSS changes needed. These are already in `filter_fix.js` and `modern_theme.css`.

### Grid field detection (DOM classes)

The DOM wrapper uses the same `[data-fieldname="..."]` selector pattern as master form fields, nested inside the grid row's wrapper element. `setGridAccent` and `setGridInlineHint` use this approach — they work on both expanded and inline rows.

### Grid field detection (instance flags)

Per-row field instances live at `gridRow.fields_dict[fieldname]`, NOT at `grid.get_field(fieldname)`. `grid.get_field()` returns the **column-level definition** shared across all rows — setting flags on it would cross-contaminate all rows. This is used by `markGridFieldBlocked`. See the warning in §3.3 above.

**Known constraint:** `gridRow.fields_dict` is only populated when the row is **expanded** (form-style editing mode). For collapsed/inline rows, `markGridFieldBlocked` will no-op (the guard `if (!gridRow || !gridRow.fields_dict) return;` handles this). The CSS class approach (`setGridAccent`) works reliably in both modes and is the primary visual signal.

### Virtual scrolling constraint

Frappe uses virtual scrolling for large grids (50+ rows). Only visible rows are rendered — `grid.grid_rows_by_docname[cdn]` returns `undefined` for off-screen rows. `applyGridGuidance` called from `onload_post_render` silently no-ops for non-visible rows (the `if (!gridRow) return;` guard in `setGridAccent` handles this). **This is intentional:** the `form_render` event fires when each row is expanded/edited — that's the reliable trigger for per-row guidance. `onload_post_render` is best-effort for visible rows only. QA: do not log failures for non-visible rows.

### Debounce rationale

Rapid change events (bulk paste, `expense_category` toggle, `employee` change) can fire many times per second. The 50ms debounce on `applyGridGuidanceDebounced` prevents unnecessary style recalculations while remaining responsive (<100ms visible delay).

### Timesheet special case

Timesheet's `employee` → `designation` sync (existing `syncTimesheetDesignation`) updates ALL rows' designations asynchronously. The `applyGridGuidanceDebounced` call on `employee` change handles this correctly by debouncing the guidance update after the sync completes.

---

*End of Phase 2 implementation plan.*
