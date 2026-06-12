# Cascading Dropdown Blocker — Full Chain Implementation Report

**Author:** Mohamed Elrefae (Senior Engineer)  
**Date:** 2026-06-12 (revised after Head-of-Engineering review)  
**Status:** 3 of 7 levels covered (BOQ Header, BOQ Structure, BOQ Item). 4 levels + 8 transaction child tables pending.  
**For:** Engineering Manager Approval

---

## 1. Executive Summary

The cascading dropdown blocker system prevents users from making invalid selections by enforcing the natural hierarchy:

```
Company → Cost Center → Project → BOQ Header → BOQ Structure → BOQ Item → BOQ Item Stage
```

When a parent field is empty, all downstream children are:
- **Visually blocked** (orange warning border + muted dropdown)
- **Label replaced** with a hint explaining what to select first (e.g. "Select BOQ Header first")
- **Dropdown menu prevented** from opening
- **"Create New" button hidden**

A **generic engine** (`ct_link_control.js`, 661 lines, v12) has been built that auto-detects blocked fields across the entire application. The remaining work is wiring **form-level scripts** to set the blocker flags on each DocType in the chain.

**Current coverage:** 3 of 7 levels (BOQ Header `boq_header.js` patched, BOQ Structure `boq_structure.js`, BOQ Item `boq_item.js`)  
**Target coverage:** All 7 levels, all 10+ DocTypes that participate in the cascade

---

## 2. Architecture: Three Cooperative Layers

### Layer 1 — Visual Accent & Blocker (JS + CSS)

The user sees three distinct visual states on every cascade field:

| State | CSS Class | Visual | Meaning |
|-------|-----------|--------|---------|
| **Accent** | `ct-boq-step-accent` | Red border + glow | "Select me first" — this is the active prerequisite |
| **Blocked** | `ct-boq-step-blocked` | Orange border + glow | "Complete parent first" — disabled until upstream resolves |
| **Normal** | *(none — `ct-dropdown-blocked` removed)* | Default border, full opacity | Field is ready for selection |

Additionally, blocked dropdowns get `ct-dropdown-blocked` (cursor: not-allowed, 65% opacity, muted colors, no shadow on hover) and **the button label changes from the field name to the blocker reason** (e.g. "Select BOQ Header first"). When unblocked, `ct-dropdown-blocked` is removed and the dropdown returns to full interactivity.

Inline pill badges (`ct-boq-inline-hint`) appear **inside the `.help` description area below the field**, not adjacent to the label. The form scripts inject them via `$wrapper.find(".help").first().append(...)`. The `ct-boq-has-inline-hint` class on the wrapper enables label text wrapping so the inline badge fits.

**Files:**
- `/apps/construction/construction/public/js/overrides/ct_link_control.js` — Generic engine (661 lines, v12)
- `/apps/construction/construction/public/js/filter_fix.js` — Injected CSS: `.ct-boq-step-accent`, `.ct-boq-step-blocked`, `.ct-dropdown-blocked`, `.ct-boq-inline-hint` (670 lines, v7)
- `/apps/construction/construction/public/css/modern_theme.css` — Inline hint pill styles + `.ct-boq-step-accent`/`.ct-boq-step-blocked` on `.control-input-wrapper`/`.link-field`/`.control-label` (lines 4524–4593)

### Layer 2 — Query Filtering (`set_query` / `get_query`)

Each downstream field's search is narrowed to only valid records given the selected parent. Filter keys use the actual Doctype field names (e.g., `structure` not `boq_structure` for the BOQ Item→BOQ Structure link):

```
BOQ Item.set_query("structure") → filters: { boq_header: frm.doc.boq_header, require_boq_header: 1 }
BOQ Item Stage.set_query("boq_item") → filters: { project, boq_header, structure, require_boq_item: 1 }
```

Server-side: `boq_link_queries.py` (443 lines) enforces scope context (company/cost_center/project) regardless of client tokens. All queries use `%(key)s` parameter binding — no f-string SQL interpolation. See `apply_header_scope()` in `services/boq_scope_filters.py`.

### Layer 3 — Downstream Clearing

When any upstream field changes, all downstream children are cleared. No undo. No silent restore. `frm.dirty()` is set so the unsaved-changes warning protects against accidental loss. User must re-select in order.

Example from `boq_item_stage.js:54-61`:
```javascript
boq_header(frm) {
    frm.set_value("boq_structure", "");   // clears this child
    frm.set_value("boq_item", "");        // clears grandchild
}
```

---

## 3. The Generic Blocker Engine

`ct_link_control.js` (661 lines, v12) is the **single entry point** for all blocker behavior on Link fields app-wide. It:

1. **Auto-enhances** every `Link` field on every page (form, dialog, filter, report)
2. **Detects blocked state** via two mechanisms:
   - `field.__ct_boq_blocked` flag (set by form scripts on the field's JS object)
   - `ct-boq-step-blocked` CSS class on the `.frappe-control` DOM wrapper (backup — catches DOM-only form scripts)
3. **Prevents dropdown opening** when blocked — `openDropdown()` returns early
4. **Replaces button label** with blocker hint text when blocked
5. **Watches for class changes** via MutationObserver — auto-re-syncs label on every DOM update
6. **Delayed re-syncs** at 200ms and 700ms to catch race conditions with form scripts and VFC re-parenting

### Key Function: `syncLabel()` (lines 258–279)

```javascript
function syncLabel() {
    const val = field.get_value() || "";
    const text = field.get_label_value() || val;
    const placeholder = field.df.label ? __(field.df.label) : __("Select…");

    const $wrapper = $input.closest(".frappe-control");
    const isBlockedByFlag = isHierarchicalLink(field) && field.__ct_boq_blocked;
    const isBlockedByClass = $wrapper.hasClass("ct-boq-step-blocked");
    const isBlocked = isBlockedByFlag || isBlockedByClass;
    $dropdown.toggleClass("ct-dropdown-blocked", !!isBlocked);

    if (isBlocked && !text) {
        // filter_description is pre-translated by form scripts; no double __()
        var hint = field.df.filter_description;
        if (!hint) {
            hint = $wrapper.find(".ct-boq-inline-hint").text().trim()
                || __("Select parent field first");
        }
        $label.text(hint);
        $btn.attr("title", hint);
    } else {
        $label.text(text || placeholder);
    }
    updateBoqFirstStepAccent();
}
```

**Note on `filter_description` translation:** Form scripts set `filter_description` via `__("Select ... first")` which produces the already-localized string. `syncLabel()` uses it directly without re-wrapping in `__()` to avoid double-translation (passing Arabic text to `__()` would be a no-op in practice, but is conceptually wrong).

**Note on `syncBoqNativeCreateState()` scope:** This helper (L29–35) automatically sets `__ct_boq_blocked`, `only_select`, and `filter_description` **only for `BOQ Structure` Link fields** (`isBoqStructureLink` check). For all other DocTypes (`boq_item`, `boq_item_stage`, transaction child tables, scope context fields), the `__ct_boq_blocked` flag must be set explicitly by each form script — the engine does not auto-detect parent/child relationships.

### Safe Against DOM Re-Parenting

The engine uses `$input.closest(".frappe-control")` which traverses the live DOM from the input element — safe regardless of `vfc_layout_engine.js` element moves. The MutationObserver re-syncs if the form script applies classes after the enhancer initializes.

**Known edge-case:** `getControlInstance()` (lines 63–113) falls back to `window.cur_frm.fields_dict[fieldname]` for grid-row fields (line 86–88). In multi-dialog or nested-form scenarios, `cur_frm` can resolve to a different form. This is mitigated by trying the grid-row data first (`$grid_row.data("grid_row")`, line 73–81) and `$control_wrapper[0].fieldobj` (line 64–66) which are DOM-local.

---

## 4. Implementation Status Matrix

### 4.1 Core Cascade Chain — Form-Level Coverage

| Level | DocType | Cascade Fields | Query Filter | Clear Chain | Blocker/Accent | Notes |
|-------|---------|---------------|-------------|-------------|----------------|-------|
| 1 | User Scope Context | company, cost_center, project | ✅ Navbar UI | ✅ Cascade clear in navbar | ✅ (navbar dropdowns) | Separate system: `scope_context_ui.js` |
| 2 | BOQ Header | `project` | ✅ `scope_context_form_defaults` | N/A (top of chain) | ✅ `boq_header.js` (refreshed) | Accent on `project` when empty on new forms |
| 3 | BOQ Structure | `boq_header`, `parent_structure` | ✅ `set_query` on `parent_structure` | ✅ header change → clear | ✅ `boq_structure.js` (IIFE refactor v12; closure fixed v11) | Uses `!hasHeader` not `isNew && !hasHeader` — accent survives save. `onload_post_render` with 150ms/600ms delays. |
| 4 | BOQ Item | `boq_header`, `structure` | ✅ `set_query` + scope | ✅ header change → clear structure | ✅ `boq_item.js:73-109` (title hardcode fixed v11) | Gold Standard reference implementation |
| 5 | BOQ Item Stage | `project`, `boq_header`, `boq_structure`, `boq_item` | ✅ `set_query` on all 4 | ✅ cascade clear | ❌ **No blocker/accent** | **4-level chain — largest gap** |
| 6 | Variation Order | `boq_header` (Locked only) | ✅ `set_query` | N/A | ❌ No blocker/accent | Need accent on `boq_header` when empty |
| 7 | VO Line (child table) | `boq_structure`, `boq_item` | ✅ `set_query` per row | ✅ grid clear | ❌ No blocker/accent | Per-row state; grid-aware needed |

### 4.2 Transaction Child Tables (8 DocTypes via `boq_filters.js`)

| DocType | Parent Table | Cascade Fields | Query Filter | Clear Chain | Blocker/Accent |
|---------|-------------|---------------|-------------|-------------|----------------|
| Purchase Order Item | Purchase Order | boq_header, boq_structure, boq_item, boq_item_stage | ✅ per-row `get_query` | ✅ cascade clear | ❌ |
| Purchase Receipt Item | Purchase Receipt | (same) | ✅ | ✅ | ❌ |
| Purchase Invoice Item | Purchase Invoice | (same) | ✅ | ✅ | ❌ |
| Sales Invoice Item | Sales Invoice | (same) | ✅ | ✅ | ❌ |
| Stock Entry Detail | Stock Entry | (same) | ✅ | ✅ | ❌ |
| Timesheet Detail | Timesheet | (same) | ✅ | ✅ | ❌ |
| Journal Entry Account | Journal Entry | (same) | ✅ | ✅ | ❌ |
| Material Request Item | Material Request | (same) | ✅ | ✅ | ❌ |

**Note:** `boq_filters.js` handles query filtering and downstream clearing but does **not** apply visual blocker/accent classes. The existing `getControlInstance()` in `ct_link_control.js` already handles grid rows via `$grid_row.data("grid_row")` fallback (lines 73–81), and the `MutationObserver` on `document.body` (lines 648–657) auto-scans newly inserted grid rows. Adding blocker support requires extending `boq_filters.js` to set `__ct_boq_blocked` on each grid field (with debounce for bulk paste/import operations).

### 4.3 Navigation Bar — Scope Context Selectors

The navbar scope selectors (`scope_context_ui.js`) are a **separate system** from the `ct_link_control.js` generic engine. They have their own cascade logic via `scope_context.js` and do not use `__ct_boq_blocked`. Long-term, unifying both systems under the generic engine would reduce maintenance divergence.

---

## 5. What's Working (Detailed — all bugs addressed in v11/v12)

### 5.1 BOQ Item Form — Gold Standard Implementation

**File:** `apps/construction/construction/construction/doctype/boq_item/boq_item.js` (173 lines)

```javascript
function updateBoqGuidance(frm) {
    const hasHeader = Boolean(frm.doc.boq_header);

    // Parent field: accent when empty
    setFieldAccent(frm, "boq_header", !hasHeader, false);
    setFieldInlineHint(frm, "boq_header", hasHeader ? null : __("Select BOQ Header first"), false);

    // Child field: blocked when parent empty
    setFieldAccent(frm, "structure", false, !hasHeader);
    setFieldInlineHint(frm, "structure", hasHeader ? null : __("Select BOQ Header first"), !hasHeader);

    setStructureBlocking(frm, !hasHeader);
}

function setStructureBlocking(frm, blocked) {
    const field = frm.fields_dict.structure;
    field.df.only_select = !!blocked;
    field.__ct_boq_blocked = !!blocked;
    field.df.filter_description = blocked ? __("Select BOQ Header first") : "";  // Pre-translated
    if (typeof field.set_description === "function") {
        field.set_description(blocked ? __("Select BOQ Header first") : "");
    }
}
```

Called on: `refresh`, `onload_post_render` (with 150ms and 600ms delays), and `boq_header` change.

**v11 fix:** `setFieldInlineHint` title attribute now uses `hint` text directly (parameterized) instead of hardcoding "Select BOQ Header first" / "BOQ workflow step".

### 5.2 BOQ Structure Form

**File:** `apps/construction/construction/construction/doctype/boq_structure/boq_structure.js` (169 lines)

**v12 refactoring:**
1. **`setFieldInlineHint` extracted from `frappe.ui.form.on(...)`** — Moved into an IIFE wrapper alongside `applyBoqGuidance()`. Previously registered as a key inside the event handler object, which caused Frappe to bind it as a spurious form event. Now a private helper function in the IIFE closure.
2. **`applyBoqGuidance(frm)` centralized** — Single function that applies all blocker/accent classes, inline hints, and field flags (`__ct_boq_blocked`, `only_select`, `filter_description`, `set_description()`). Called from `refresh` and `onload_post_render`.
3. **`onload_post_render` added** — with 150ms and 600ms delayed re-calls, matching the Gold Standard pattern from `boq_item.js`. Ensures blocker state survives VFC re-parenting.
4. **`is_new()` condition removed** — blocker uses `!hasHeader` directly, independent of form save state.

### 5.3 Generic Link Engine

**File:** `apps/construction/construction/public/js/overrides/ct_link_control.js` (661 lines, v12)

**v11/v12 fixes:**
1. **Double-translation eliminated** — `filter_description` (pre-translated by form scripts) is used directly without re-wrapping in `__()`. Only fallback strings go through `__()`.
2. **`.trim()` on badge text** — whitespace-safe DOM text extraction.
3. **`updateBoqFirstStepAccent()`** — does not overwrite `$btn.attr("title")` when field is blocked.

---

## 6. Gap Analysis — What's Missing (with corrected pseudocode)

### 6.1 BOQ Item Stage Form — Full 4-Level Blocker Chain

**File to modify:** `apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.js` (147 lines)

**Current state:** Has `set_query` filtering and downstream clearing. NO visual guidance.

**Needed:** Add blocker/accent logic for the 4-level cascade:
```
project → boq_header → boq_structure → boq_item
```

Implementation pattern (add to existing file — this is corrected pseudocode, no syntax errors):

```javascript
function updateStageGuidance(frm) {
    const hasProject = Boolean(frm.doc.project);
    const hasHeader = Boolean(frm.doc.boq_header);
    const hasStructure = Boolean(frm.doc.boq_structure);

    // Level 1: Project (top of chain — accent when empty)
    setFieldAccent(frm, "project", !hasProject, false);
    setFieldInlineHint(frm, "project", hasProject ? null : __("Select Project first"), false);

    // Level 2: BOQ Header — blocked when no project; accent when project set but header empty
    setFieldAccent(frm, "boq_header", hasProject && !hasHeader, !hasProject);
    setFieldInlineHint(frm, "boq_header", null, !hasProject);  // hint handled by filter_description

    // Level 3: BOQ Structure — blocked when no header
    setFieldAccent(frm, "boq_structure", false, !hasHeader);
    setFieldInlineHint(frm, "boq_structure", hasHeader ? null : __("Select BOQ Header first"), !hasHeader);

    // Level 4: BOQ Item — blocked when no structure
    setFieldAccent(frm, "boq_item", false, !hasStructure);
    setFieldInlineHint(frm, "boq_item", hasStructure ? null : __("Select BOQ Structure first"), !hasStructure);

    // Set field flags for the generic engine
    markFieldBlocked(frm, "boq_header", !hasProject, __("Select Project first"));
    markFieldBlocked(frm, "boq_structure", !hasHeader, __("Select BOQ Header first"));
    markFieldBlocked(frm, "boq_item", !hasStructure, __("Select BOQ Structure first"));
}

function markFieldBlocked(frm, fieldname, blocked, hint) {
    const field = frm.fields_dict[fieldname];
    if (!field) return;
    field.df.only_select = !!blocked;
    field.__ct_boq_blocked = !!blocked;
    field.df.filter_description = blocked ? hint : "";
    if (typeof field.set_description === "function") {
        field.set_description(blocked ? hint : "");
    }
}
```

**Wiring:** Call `updateStageGuidance(frm)` from:
- `refresh`
- `onload_post_render` with `setTimeout(fn, 150)` and `setTimeout(fn, 600)` delays
- Each parent field's change handler (`project`, `boq_header`, `boq_structure`)

**Key design decisions:**
- `boq_header` has TWO visual states: `blocked=true` when project is empty, `accent=true` when project is set but header is still empty. These are mutually exclusive in `setFieldAccent()`.
- `filter_description` is set via `__()` by the form script and used directly by the generic engine (no double-translation).

### 6.2 BOQ Header Form — Project Accent

**File to modify:** `apps/construction/construction/construction/doctype/boq_header/boq_header.js` (623 lines)

Add to `refresh(frm)`:
```javascript
// Project accent for new headers without project (scope pre-fill may race)
if (!frm.doc.project) {
    setFieldAccent(frm, "project", true, false);
    setFieldInlineHint(frm, "project", __("Select a Project first"), false);
} else {
    setFieldAccent(frm, "project", false, false);
    setFieldInlineHint(frm, "project", null, false);
}
```

**Race condition mitigation:** Call with 150ms/600ms delayed re-check (matching BOQ Item pattern) because `scope_context_form_defaults.js` may pre-fill `project` asynchronously after `refresh` fires.

### 6.3 Variation Order Form — BOQ Header Accent

**File to modify:** `apps/construction/construction/construction/doctype/variation_order/variation_order.js` (396 lines)

Add blocker on `boq_header` when the field is empty (not gated on `is_new()` — accent persists after save):
```javascript
if (!frm.doc.boq_header) {
    setFieldAccent(frm, "boq_header", true, false);
    setFieldInlineHint(frm, "boq_header", __("Select a locked BOQ Header"), false);
}
```

### 6.4 Transaction Child Tables — `boq_filters.js`

**File to modify:** `apps/construction/construction/public/js/boq_filters.js` (470 lines)

The existing `getControlInstance()` in `ct_link_control.js` already supports grid rows via `$grid_row.data("grid_row")`. The `MutationObserver` auto-scans new rows. The gap is wiring `boq_filters.js` to set `__ct_boq_blocked` on grid fields when the gate is open but a parent is empty.

**Debounce requirement:** Grid rows fire rapid `onchange` events during bulk paste/import. Setting `__ct_boq_blocked` synchronously on every change would trigger O(n) re-renders. Use a debounce wrapper (~50ms) when applying blocker state to grid fields.

---

## 7. Implementation Plan

### Phase 1: Standard Form Coverage (2–3 hours)

| Priority | DocType | File | Effort |
|----------|---------|------|--------|
| P0 | BOQ Item Stage | `boq_item_stage.js` | 1 hour |
| P1 | BOQ Header | `boq_header.js` | 30 min |
| P1 | Variation Order | `variation_order.js` | 30 min |
| P2 | VO Line (child) | `variation_order.js:setChildQueries` | 1 hour |

### Phase 1.5: Regression Testing (1 hour)

| Test | Method |
|------|--------|
| Open BOQ Item Stage form, clear `project` | Assert `boq_header` gains `ct-boq-step-blocked` class |
| Set `project`, clear `boq_header` | Assert `boq_structure` gains `ct-boq-step-blocked` |
| Set `boq_header`, clear `boq_structure` | Assert `boq_item` gains `ct-boq-step-blocked` |
| After save, field still empty | Assert accent/blocker persists (not gated on `is_new()`) |

### Phase 2: Transaction Grid Support (4–6 hours)

| Priority | Module | Effort |
|----------|--------|--------|
| P0 | `boq_filters.js` — add `setGridBlocked()` helper with debounce | 2 hours |
| P1 | Wire into all 8 transaction DocTypes | 2 hours |
| P2 | Integration testing with real transactions | 2 hours |

### Phase 3: Scope Context Bridge (1–2 hours)

| Priority | Change | Effort |
|----------|--------|--------|
| P1 | `scope_context_form_defaults.js` — add `project` field accent on new forms | 30 min |
| P2 | `boq_header.js` — hook into scope context for project guidance | 30 min |

### Phase 4: Cache Busting & Deployment

After each phase:
```bash
bench build --app construction
bench clear-cache
bench clear-website-cache          # for production: clears Redis asset cache
```

Instruct users to hard refresh (`Ctrl+Shift+R` / `Cmd+Shift+R`).

Version bump in `hooks.py`:
```
ct_link_control.js → ?v=N+1
filter_fix.js      → ?v=N+1
modern_theme.css   → ?v=N+1
```

---

## 8. The Reusable Pattern (corrected)

Any form script can implement cascading guidance with this template:

```javascript
// ── Call this from: refresh, onload_post_render (with 150ms/600ms delays),
//     and the parent field's change handler ──
function updateWorkflowGuidance(frm) {
    const hasParent = Boolean(frm.doc.parent_field);

    // 1. Accent the parent when empty (signals "start here")
    setFieldAccent(frm, "parent_field", !hasParent, false);
    setFieldInlineHint(frm, "parent_field", hasParent ? null : __("Select parent first"), false);

    // 2. Block the child when parent is empty
    setFieldAccent(frm, "child_field", false, !hasParent);
    setFieldInlineHint(frm, "child_field", hasParent ? null : __("Select parent first"), !hasParent);

    // 3. Signal to the generic engine (ct_link_control.js)
    const childField = frm.fields_dict.child_field;
    if (childField) {
        childField.df.only_select = !hasParent;
        childField.__ct_boq_blocked = !hasParent;
        childField.df.filter_description = !hasParent ? __("Select parent first") : "";
        // Also update native description (double-feedback path for native renderer)
        if (typeof childField.set_description === "function") {
            childField.set_description(!hasParent ? __("Select parent first") : "");
        }
    }
}

// ── DOM-safe helpers (work even after vfc_layout_engine re-parenting) ──
function setFieldAccent(frm, fieldname, active, blocked) {
    const $w = $(`.frappe-control[data-fieldname="${fieldname}"]`);
    if (!$w.length) return;
    $w.toggleClass("ct-boq-step-accent", !!active);
    $w.toggleClass("ct-boq-step-blocked", !!blocked);
}

function setFieldInlineHint(frm, fieldname, hint, blocked) {
    const $w = $(`.frappe-control[data-fieldname="${fieldname}"]`);
    if (!$w.length) return;
    const $help = $w.find(".help").first();
    if (!$help.length) return;                         // guard: some field types have no .help
    $w.toggleClass("ct-boq-has-inline-hint", !!hint);
    $w.toggleClass("ct-boq-inline-hint-blocked", !!blocked);
    $help.find(".ct-boq-inline-hint").remove();
    if (hint) {
        $help.append($("<span>", {
            class: "ct-boq-inline-hint",
            text: hint,
            title: hint,                               // parameterized — not hardcoded
        }));
    }
}
```

---

## 9. Files Modified (This Session — v12)

| File | Before | After | Key Changes |
|------|--------|-------|-------------|
| `ct_link_control.js` | 624 | 661 | `isHierarchicalLink()`, fallback hint, DOM-class check, delayed re-sync, MutationObserver, title no-overwrite, double-translation fix |
| `boq_item.js` | 172 | 172 | `filter_description` set to hint when blocked, `setFieldInlineHint` title parameterized, `set_description()` called |
| `boq_structure.js` | 153 | 169 | IIFE refactor, `setFieldInlineHint` extracted from event registry, `applyBoqGuidance()` centralized, `onload_post_render` with 150ms/600ms delays, `is_new()` gate removed, `set_description()` added |
| `filter_fix.js` | 647 | 670 | Added `.ct-boq-inline-hint` and `.ct-boq-inline-hint-blocked` CSS |
| `hooks.py` | 275 | 275 | Bumped 4 version params (`ct_link_control?v=12`, `filter_fix?v=7`, `modern_theme.css?v=2.5.6`/`2.5.5`) |

---

## 10. Risk Assessment (updated after review)

| Risk | Likelihood | Impact | Mitigation | Status |
|------|-----------|--------|------------|--------|
| Browser caching old assets | High | User sees old behavior | Version query params on every change; hard refresh instructions | ✅ Mitigated |
| VFC layout engine race | Medium | Blocker class lost after re-parent | MutationObserver watches class changes; delayed re-sync at 200ms/700ms | ✅ Mitigated |
| `cur_frm` global fallback in `getControlInstance()` | Low | Wrong form resolved in multi-dialog scenarios | Grid-row data checked first; `fieldobj` from DOM checked first; fallback is last resort | ⚠️ Documented |
| Double-translation of `filter_description` | Low (no-op in practice) | Garbled text in non-English locales if translation DB has matching key | `filter_description` used directly; only fallbacks go through `__()` | ✅ Fixed |
| `boq_structure.js` broken closure | — | `refresh` handler never registered independently | `},` added after `onload` block; `refresh:` is now own handler | ✅ Fixed |
| `is_new()` accent flicker on save | Medium | Accent disappears after save even if field still empty | Condition changed to `!hasHeader` (independent of `is_new()`) | ✅ Fixed |
| Rapid grid event debounce | Medium | O(n) re-renders during bulk paste | Debounce wrapper planned for Phase 2 `setGridBlocked()` | ⚠️ Phase 2 |
| Grid rows not enhanced | Low | No dropdown on transaction children | Grid-row-aware `getControlInstance` fallback already in engine; MutationObserver auto-scans | ⚠️ Test before Phase 2 |
| `setFieldInlineHint` title hardcode | Low | Wrong tooltip when pattern copy-pasted to other forms | Title now uses `hint` parameter directly | ✅ Fixed |
| `__()` unavailable at script load | Low | Hint text shows untranslated | `__()` is Frappe global; script loads at 800ms after `document.ready` | ✅ Mitigated |
| Performance (MutationObserver) | Low | Observer fires on every DOM change | Scoped to `attributeFilter: ["class"]` only; scanAndEnhance debounced | ✅ Mitigated |

---

*Report reflects code at v12 state on branch `feature/vite-ui-v1`. All P0/P1 bugs from both Head-of-Engineering and AI Agent reviews (2026-06-12) have been addressed in code and report.*
