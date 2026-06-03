# Form Config / VFC Layout Engine Debug Report

**Date:** 2026-06-03  
**Project:** Construction ERPNext / Frappe v16  
**Area:** Form Config, VFC Layout Engine, BOQ forms, RTL dark theme  
**Prepared for:** Engineering Manager  
**Status:** Implementation is partially working, but the current rendering still has visible layout defects and needs stabilization before wider rollout.

---

## 1. Executive Summary

The Form Config implementation is not deleted and is not just a styling issue. The current implementation is an overlay engine that re-parents native Frappe field wrappers into custom VFC section cards. This approach can work, but the current behavior shown in the screenshots indicates that the overlay is leaving native Frappe layout artifacts behind, especially on RTL BOQ forms.

The screenshots under `/home/mohamed/Pictures/forum config/` show:

- Empty horizontal bands before the real fields.
- Section labels such as `OTHER FIELDS`, `OWNER REFERENCES`, `HEADER LINK`, and `ITEM CLASSIFICATION` appearing in awkward locations.
- Native form spacing still occupying vertical space after fields are moved.
- RTL alignment inconsistencies in the generated sections.
- Sidebar navigation correctly selects the BOQ pages, so the defect is inside form rendering, not routing.

The highest-confidence diagnosis is:

1. The VFC engine moves fields out of native Frappe sections, but for tabbed/RTL forms it intentionally preserves native tab containers.
2. Because native containers are preserved, empty `.form-section`, `.section-body`, `.form-column`, and related wrappers can remain visible as blank bands.
3. The engine skips layout-only DocFields (`Section Break`, `Column Break`, `Tab Break`, `HTML`, `Heading`), but the saved profile still has section labels that create new VFC headers even when the native layout has already created comparable grouping.
4. The active fix in `vfc_layout_engine.js?v=1.29` solved earlier disappearing-form/tab race problems, but it did not fully solve empty native shell cleanup for tabbed forms.

This should be treated as a stabilization task, not a full rewrite.

---

## 2. Evidence Reviewed

### Screenshots

Local evidence:

- `/home/mohamed/Pictures/forum config/desktop gap.png`
- `/home/mohamed/Pictures/forum config/forum config gap.png`
- `/home/mohamed/Pictures/forum config/forum config gap2.png`

Observed pages:

- `BOQ Structure` / `هيكل جدول الكميات`
- `BOQ Item` / `بند جدول الكميات`
- RTL Arabic desk UI with Construction Dark theme

### Implementation Files

Primary files:

- `construction/public/js/vfc_layout_engine.js`
- `construction/public/js/vite_layout_controls.js`
- `construction/public/css/vfc_sections.css`
- `construction/hooks.py`
- `construction/construction/api/layout_api.py`
- `construction/doctype/form_layout_profile/form_layout_profile.py`

Current asset versions in `construction/hooks.py`:

- `vite_layout_controls.js?v=1.13`
- `vfc_layout_engine.js?v=1.29`
- `vfc_sections.css?v=1.5`

Existing related reports:

- `VFC_PROJECT_TABS_DEBUG_REPORT.md`
- `VFC_DENSITY_DEBUG_REPORT.md`
- `docs/form_layout_engine_team_letter.md`

---

## 3. Current Architecture

The implementation has two layers:

### A. Form Config Panel

File: `construction/public/js/vite_layout_controls.js`

Responsibilities:

- Adds the `Form Config` button to Frappe forms.
- Stores density selection.
- Stores user-hidden fields.
- Allows System Manager users to save section layout.
- Calls the layout engine after density or section changes.

Important current behavior:

- `_applyDensity()` adds `vfc-density-1`, `vfc-density-2`, or `vfc-density-3`.
- For tabbed forms, it adds `vfc-native-density`.
- It then calls `VFCLayoutEngine.restoreNative(frm)` and `VFCLayoutEngine.attach(frm)`.

### B. VFC Layout Engine

File: `construction/public/js/vfc_layout_engine.js`

Responsibilities:

- Fetches the active `Form Layout Profile`.
- Builds VFC section containers.
- Moves native Frappe field wrappers into VFC grid cells.
- Preserves Frappe field objects, permissions, events, depends_on, and validation.

Important current behavior:

- Tabbed DocTypes are detected by the presence of `Tab Break`.
- On tabbed forms, VFC sections are mounted inside native tab panes.
- Native shell hiding is skipped when `preserveTabContainers` is true.

This last point is the key tradeoff: preserving tab containers avoids disappearing forms, but it also means empty native wrappers can remain visible.

---

## 4. High-Confidence Root Causes

### Root Cause 1 — Native shells are preserved on tabbed forms, causing blank bands

In `vfc_layout_engine.js`, `_render()` calls:

```js
this._hideNativeLayoutShells(layoutRoot, { preserveTabContainers: hasTabs });
```

But `_hideNativeLayoutShells()` immediately returns if `preserveTabContainers` is true:

```js
const preserveTabContainers = Boolean(options.preserveTabContainers);
if (preserveTabContainers) return 0;
```

This means tabbed forms keep the native `.form-section`, `.section-body`, `.frappe-column`, and `.form-column` shells visible. After fields are moved into VFC containers, those shells can become empty but still consume height.

This matches the screenshots: wide empty horizontal bands appear above the real fields.

### Root Cause 2 — Empty-section hiding is disabled for tabbed forms

In `_render()`, validation state is built with:

```js
skipEmptySectionAutoHide: hasTabs
```

Then `_verifyAndRetry()` does:

```js
const hiddenEmptySectionCount = state.skipEmptySectionAutoHide
    ? 0
    : this._hideEmptyCustomSections(layoutRoot);
```

For tabbed forms, empty VFC sections are not auto-hidden. This was likely added to avoid hiding inactive tabs by mistake, but the side effect is that empty or visually empty VFC sections can remain on screen.

This matches the screenshots where section rows appear with little or no useful content.

### Root Cause 3 — Section mounting is inferred from the first field wrapper

Tabbed placement uses `_getSectionTabPane()`:

```js
const wrapper = frm.fields_dict?.[fld.fieldname]?.wrapper;
const tabPane = nativeEl?.closest?.(".tab-pane");
if (tabPane) return tabPane;
```

If a section contains fields that have already been moved, hidden, or restored to fallback parents, the inferred tab pane can be wrong. The fallback is the active tab pane or first tab pane. That can place a section into the wrong visual area.

This explains why headers like `OTHER FIELDS` and `HEADER LINK` can look visually detached from the intended fields.

### Root Cause 4 — Unassigned fields are appended to `layoutRoot`, not the correct tab pane

`_appendUnassigned()` appends the `Other Fields` section directly to `layoutRoot`:

```js
layoutRoot.appendChild(secEl);
```

On tabbed forms, this bypasses tab-aware mounting. If a profile does not include every field, the engine creates `Other Fields` at the global form root. That is likely why `OTHER FIELDS` appears as a broad misplaced section in screenshots.

### Root Cause 5 — RTL polish exists but is incomplete

`vfc_sections.css` has basic RTL support:

```css
[dir="rtl"] .vfc-le-section {
  direction: rtl;
  text-align: right;
}
```

But the section accent border is always `border-left`, and the grid/header layout does not fully account for Arabic/right-to-left visual direction. This is lower risk than the DOM issue, but it contributes to the unpolished look.

---

## 5. What Is Already Fixed

The previous tab disappearance issue appears to have been addressed in `vfc_layout_engine.js?v=1.29`.

Already applied improvements:

- Debounced global attach flow.
- Attach tokens to avoid stale async renders.
- Safer `_clearSections()` restore path.
- Tab pane visibility watcher.
- Lighter `_restoreVisibleFieldWrapper()` behavior.
- `VFCLayoutEngine.disable()` and `enable()` helpers.

These changes reduced the risk of fields disappearing completely. The current problem is now mostly visual structure and shell cleanup, not total data loss.

---

## 6. Recommended Fix Plan

### Priority 1 — Add safe cleanup for empty native shells in tabbed mode

Do not hide entire tab containers. Instead, hide only empty native shells inside the active tab after field re-parenting.

Target behavior:

- Keep `.tab-content` and `.tab-pane`.
- Keep active/inactive tab behavior native.
- Hide native `.form-section` / `.form-column` only when they contain no visible `.frappe-control`.
- Never hide a shell that still contains a visible field wrapper.

Suggested new helper:

```js
_hideEmptyNativeShellsInsideTabs(layoutRoot) {
  layoutRoot.querySelectorAll(".tab-pane .form-section, .tab-pane .section-body, .tab-pane .form-column").forEach((el) => {
    if (el.closest(".vfc-le-section")) return;
    const visibleControl = [...el.querySelectorAll(".frappe-control")].some((ctrl) => {
      if (ctrl.closest(".vfc-le-cell")) return false;
      const style = getComputedStyle(ctrl);
      const rect = ctrl.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 1 && rect.height > 1;
    });
    if (!visibleControl) {
      el.style.setProperty("display", "none", "important");
      el.setAttribute("data-vfc-empty-native", "1");
    }
  });
}
```

Call this after section rendering when `hasTabs` is true.

### Priority 2 — Make `Other Fields` tab-aware

Change `_appendUnassigned()` so unassigned fields are grouped by their current native tab pane before being moved.

Target behavior:

- If unassigned field originally belongs to `BOQ Item` tab, append `Other Fields` inside that tab's VFC host.
- Do not append tabbed unassigned fields directly to `layoutRoot`.

This should remove the misplaced global `OTHER FIELDS` band.

### Priority 3 — Add tab id to saved section profiles

The current implementation infers tab placement from DOM state. That is fragile.

Better profile format:

```json
{
  "label": "Header Link",
  "tab_fieldname": "main_tab",
  "fields": [...]
}
```

The Form Config panel should store which tab a section belongs to. The engine should mount by `tab_fieldname` first, and use DOM inference only as a fallback.

### Priority 4 — Improve RTL section CSS

Fix direction-specific styling:

```css
[dir="rtl"] .vfc-le-section-head {
  border-left: 0;
  border-right: var(--ct-section-accent-border);
}

[dir="rtl"] .vfc-le-grid {
  direction: rtl;
}
```

Also reduce the visual weight of auto-generated/unassigned headers in dark theme.

### Priority 5 — Add a focused browser diagnostic

Add one helper to `vfc_layout_engine_tests.js`:

```js
VFCTest.checkEmptyNativeShells()
```

It should report:

- Empty native shells still visible.
- VFC sections with zero painted fields.
- Sections mounted outside tab panes on tabbed DocTypes.
- Unassigned fields appended to `layoutRoot`.

---

## 7. Debug Commands For Developer Console

Run these on the affected BOQ form.

### Check current VFC asset version

```js
[...performance.getEntriesByType("resource")]
  .filter((r) => r.name.includes("vfc_layout_engine") || r.name.includes("vite_layout_controls") || r.name.includes("vfc_sections"))
  .map((r) => r.name);
```

Expected:

- `vfc_layout_engine.js?v=1.29`
- `vite_layout_controls.js?v=1.13`
- `vfc_sections.css?v=1.5`

### Check empty visible native shells

```js
(() => {
  const root = cur_frm?.wrapper?.find(".form-layout")?.[0];
  return [...root.querySelectorAll(".form-section, .section-body, .form-column")].map((el) => {
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    const controls = [...el.querySelectorAll(".frappe-control")].filter((ctrl) => !ctrl.closest(".vfc-le-cell"));
    return {
      cls: el.className,
      visible: style.display !== "none" && style.visibility !== "hidden" && rect.height > 1,
      size: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
      nativeControls: controls.length
    };
  }).filter((x) => x.visible && x.nativeControls === 0);
})();
```

If this returns rows, those are the blank bands seen in the screenshots.

### Check VFC sections with no visible fields

```js
(() => {
  const root = cur_frm?.wrapper?.find(".form-layout")?.[0];
  return [...root.querySelectorAll(".vfc-le-section")].map((section) => {
    const label = section.querySelector(".vfc-le-section-head")?.textContent?.trim() || "(no label)";
    const cells = [...section.querySelectorAll(".vfc-le-cell")];
    const painted = cells.filter((cell) => {
      const field = cell.querySelector("[data-vfc-managed='1']");
      if (!field) return false;
      const style = getComputedStyle(field);
      const rect = field.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 1 && rect.height > 1;
    }).length;
    return { label, cells: cells.length, painted };
  }).filter((x) => x.cells === 0 || x.painted === 0);
})();
```

### Disable VFC to confirm native Frappe layout is healthy

```js
VFCLayoutEngine.disable();
VFCLayoutEngine.restoreNative(cur_frm);
cur_frm.refresh();
```

If native layout becomes correct after disabling VFC, the defect is confirmed in the VFC overlay layer.

---

## 8. Acceptance Criteria For The Fix

The fix is complete only when all of the following pass on `BOQ Structure`, `BOQ Item`, and `BOQ Item Stage` in RTL and LTR:

- No blank horizontal bands above or between VFC sections.
- `Other Fields` appears only inside the relevant tab, or not at all when every field is assigned.
- No VFC section is visible with zero painted fields.
- Active tab content remains visible after 3 seconds.
- Inactive tabs remain hidden by native Bootstrap/Frappe behavior.
- `VFCLayoutEngine.restoreNative(cur_frm)` restores the original Frappe layout without lost fields.
- Console reports one debounced attach path per refresh, not repeated attach loops.
- Hard reload picks up the expected asset versions.

---

## 9. Risk Assessment

| Risk | Level | Notes |
|---|---:|---|
| Re-parenting native Frappe wrappers | High | Powerful but fragile around tabs, depends_on, child tables, and refresh cycles. |
| Tabbed DocTypes | High | Must preserve native tab behavior while hiding empty native shells. |
| RTL/dark theme visual QA | Medium | Mostly CSS, but current screenshots show poor visual output. |
| Saved profiles with missing fields | Medium | Creates `Other Fields`; must be tab-aware. |
| Full rewrite | High | Not recommended now. Stabilize current overlay first. |

---

## 10. Manager Decision Needed

Recommended decision:

Approve a short stabilization sprint focused only on VFC tabbed-form rendering:

1. Patch empty native shell cleanup.
2. Make unassigned fields tab-aware.
3. Add diagnostics/tests.
4. Verify BOQ forms in Arabic RTL dark theme.

Do not expand Form Config to more DocTypes until these acceptance criteria are met.

Estimated effort: 1-2 engineering days for the patch, plus 0.5 day for browser verification and screenshots.

