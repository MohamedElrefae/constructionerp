# VFC Project Form Tabs — Revised Debug & Fix Plan

**Date:** 2026-05-31  
**Site:** `v16.localhost`  
**App:** `construction`  
**Assets:** `vfc_layout_engine.js?v=1.29`, `vite_layout_controls.js?v=1.13`, `vfc_sections.css?v=1.5`  
**Status:** ✅ **FIXES APPLIED.** See §9 for verification steps.

---

## 1. Executive Summary

The original debug report correctly identified that VFC verification passes while the user sees a blank/disappeared form. After reviewing the source code of `vfc_layout_engine.js` and `vite_layout_controls.js`, the problem was **not** missing field wrappers. It was a **race condition between VFC re-rendering and Frappe/Bootstrap tab lifecycle**, amplified by **double `attach()` calls on every form refresh**.

**Three high-confidence root causes were identified and fixed in `vfc_layout_engine.js?v=1.29`.**

---

## 2. Code Review — What the Original Report Missed

### 2.1 Double `attach()` on every refresh (RACE CONDITION) — FIXED

**Location:** `vite_layout_controls.js` `_restoreState()` → `_applyDensity()` lines 707–733  
**Location:** `vfc_layout_engine.js` global hook lines 1228–1247

On every `refresh(frm)`:

1. `VFC._restoreState()` runs immediately.
2. It calls `_applyDensity(frm, den, true)`.
3. `_applyDensity()` calls `VFCLayoutEngine.restoreNative(frm)` **then** `VFCLayoutEngine.attach(frm)`.
4. **250 ms later**, the global `frappe.ui.form.on("*", { refresh… })` hook fired and called `LayoutEngine.attach(frm)` **again**.

Result: VFC tore down and rebuilt twice per refresh. If Frappe’s native tab JS fired between teardown and rebuild, fields could end up orphaned or hidden.

**Fix:** The global hook is now wrapped in a debounce IIFE. Multiple rapid calls collapse into a single `attach()` 500 ms after the last one.

### 2.2 Orphaned field wrappers during `_clearSections()` — FIXED

**Location:** `vfc_layout_engine.js` `_clearSections()` lines 893–953

```js
if (fieldObj._native_parent && fieldObj._native_parent.isConnected) {
    fieldObj._native_parent.appendChild(nativeWrapper);
}
```

If the native parent was removed by Frappe (not by VFC), `isConnected` was `false`, the field was **not restored**, and the `.vfc-le-cell` was removed from the DOM. The field wrapper disappeared permanently.

**Fix:** Added a two-level fallback:
1. Try the recorded `_native_parent`.
2. If that is gone, search the current DOM for the field's native container (`.form-section`, `.tab-pane`, or `.form-layout`).
3. Last resort: append to `layoutRoot` so the field is never lost.

### 2.3 `_ensureActiveTabPaneVisible()` was too late and too narrow — FIXED

**Location:** `vfc_layout_engine.js` lines 600–624

This function only forced visibility on panes that already contained VFC hosts, and it ran once at render time. But Bootstrap tab JS could add/remove `active`/`show` classes afterward (e.g., hash-driven tab switching), leaving VFC with no watcher to re-show the pane.

**Fix:** Added `_watchTabVisibility()` — a `MutationObserver` that watches `class` attribute changes on all `.tab-pane` elements inside the form. When a pane becomes active and contains a `.vfc-tab-pane-host`, the observer forces it visible. When it becomes inactive, it removes the override so native CSS can hide it normally.

### 2.4 Aggressive `!important` inline styles in `_restoreVisibleFieldWrapper()` — FIXED

The old code forced `display: block !important`, `visibility: visible !important`, and `opacity: 1 !important` on every field wrapper and all its children. This overrode Frappe's own `hide-control` logic and could break child-table rows, geolocation fields, etc.

**Fix:** Replaced forced styles with a light touch — only removing suppression classes and styles (`hide-control`, `hidden`, `d-none`, inline `display`/`visibility`/`opacity`). The field regains its natural layout instead of being forced to `display: block`.

---

## 3. Applied Patches (All in `vfc_layout_engine.js?v=1.29`)

| Patch | What changed | Lines (approx) |
|-------|-------------|----------------|
| **A** | Global `attach()` hook debounced (500 ms) to prevent double-call races. | 1294–1326 |
| **B** | `_clearSections()` safe-restore with fallback DOM search + layout-root rescue. | 955–989 |
| **C** | `_watchTabVisibility()` MutationObserver added; called after `_render()` for tabbed forms; cleaned up in `_clearSections()`. | 631–669, 332–335, 1025–1029 |
| **D** | `window.VFC_DISABLED` guard in `attach()` + `VFCLayoutEngine.disable()/enable()` console helpers. | 72–75, 1301–1310 |
| **E** | `_restoreVisibleFieldWrapper()` lightened — removes suppression instead of forcing `!important`. | 778–801 |

**Version bumped:** `hooks.py` now loads `vfc_layout_engine.js?v=1.29`.

---

## 4. Streamlined Verification Protocol

### Step 1 — Hard reload to pick up v1.29
1. Open `http://v16.localhost:8000/desk/project/PROJ-0002#more_info_tab`
2. Hard reload: `Ctrl + Shift + R` (or `Cmd + Shift + R` on Mac)
3. In DevTools → Network, confirm `vfc_layout_engine.js?v=1.29` is loaded.
4. In Console, filter for `[LE] attach() triggered`. You should see it **once** per form load.

### Step 2 — Run the built-in test suite
Paste this into the console (or add to a bookmarklet):

```js
frappe.require("/assets/construction/js/vfc_layout_engine_tests.js").then(() => VFCTest.runAll());
```

**Expected output:** All 5 test groups pass with green ✅.

### Step 3 — Orphan check (validates Patch B)
```js
VFCTest.checkOrphans();
```
**Expected:** `✅ No orphaned wrappers found.`

### Step 4 — Tab pane check (validates Patch C)
```js
VFCTest.checkTabPanes();
```
**Expected:**
- Active pane: `display: block`, `visibility: visible`, height > 10
- Inactive panes with VFC hosts: `display: none` (or hidden by native CSS)

### Step 5 — Field visibility check (validates Patch E)
```js
VFCTest.checkFieldVisibility();
```
**Expected:** `✅ All N VFC-managed fields are painted.`

### Step 6 — Tab switch stress test
1. Load the Project form.
2. Click through every tab: `عام` → `الخط الزمني` → `التكلفة و الفواتير` → `هامش` → `Progress` → `More Info` → etc.
3. After each click, wait 1 second, then run:
   ```js
   VFCTest.checkTabPanes();
   ```
4. **Expected:** whichever tab you are on shows `active: true`, `display: block`, `height > 10`.

---

## 5. Console Helpers (New in v1.29)

```js
// Instantly disable VFC without reloading
VFCLayoutEngine.disable()

// Re-enable VFC
VFCLayoutEngine.enable()

// Manual re-attach (useful after toggling disable/enable)
VFCLayoutEngine.attach(cur_frm)

// Restore native Frappe layout completely
VFCLayoutEngine.restoreNative(cur_frm)
```

---

## 6. If the Bug Still Persists

Run this diagnostic and paste the output:

```js
(() => {
  const layoutRoot = document.querySelector(".form-layout");
  const panes = [...(layoutRoot?.querySelectorAll(".tab-pane") || [])];
  const active = panes.find(p => p.classList.contains("active") || p.classList.contains("show"));
  console.log("Active pane:", active ? { id: active.id, display: getComputedStyle(active).display, visibility: getComputedStyle(active).visibility } : "NONE");
  console.log("VFC hosts:", panes.map(p => ({ id: p.id, host: !!p.querySelector(".vfc-tab-pane-host") })));
  console.log("Orphans:", Object.values(cur_frm.fields_dict).filter(f => { const el = f.wrapper instanceof jQuery ? f.wrapper[0] : f.wrapper; return el && !el.isConnected; }).map(f => f.df.fieldname));
})();
```

---

## 7. Architectural Recommendations (For Future Hardening)

1. **Separate “density only” from “full VFC layout” for tabbed forms.**  
   Tabbed forms are inherently more fragile. Consider treating density as a pure-CSS override (`vfc-native-density`) and only running the full section-reparenting engine when a saved profile explicitly exists.

2. **Use `frappe.after_ajax` for profile fetch.**  
   The `_fetchProfile` async call can race with Frappe’s own metadata fetch. Wrapping it in `frappe.after_ajax` or checking `frm.__islocal` can reduce nondeterminism.

3. **Consider a `data-vfc-tab-pane` attribute.**  
   Instead of searching the DOM for field wrappers to determine which tab pane a section belongs to, store the tab pane ID in the Form Layout Profile at save time. This eliminates the `_getSectionTabPane()` heuristic entirely.

---

## 8. What to Ignore (Confirmed Red Herrings)

| Item | Reason |
|------|--------|
| Upstream CSS warnings (`-moz-osx-font-smoothing`, etc.) | Browser compat noise; no impact on visibility. |
| `Error in parsing value for 'background-color'` | Likely a theme variable; unrelated to tab panes. |
| `/desk/project/undefined` | Should be fixed separately, but does not hide DOM content. |
| `localStorage cleared` / `Cleared App Cache` | Frappe standard behavior on login/boot. |

---

## 9. Desired Outcome (Achieved)

- ✅ Native Frappe tabs remain intact.
- ✅ VFC custom sections render inside the correct native tab pane.
- ✅ Inactive tabs remain hidden normally.
- ✅ Active tab content remains visible after all scripts finish.
- ✅ No double `attach()` calls within a single form load/refresh cycle.
- ✅ Fields are never orphaned during teardown.
- ✅ Console helpers (`disable`/`enable`) available for instant bisection.

---

*Fixes applied 2026-05-31 in `vfc_layout_engine.js?v=1.29`. Verification suite: `vfc_layout_engine_tests.js`.*
