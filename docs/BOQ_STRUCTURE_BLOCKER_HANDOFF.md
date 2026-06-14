# Handoff & Technical Briefing: Scope Context Standardization & Permission Hardening

**To**: Senior Engineer  
**From**: Development Team / AI Assistant  
**Date**: June 14, 2026  
**Subject**: Issues Standardizing Scope Context Hydration & Eliminating `403 (Forbidden) Project` Permissions Blocker on BOQ Structure Tree View

---

## 1. Objective
Our goal is to standardize the client-side **Scope Context** hydration contract to follow a strict **server-first** model, hide the local project filter in the `BOQ Structure` tree view (especially in Firefox), and prevent `403 Forbidden` console errors for restricted roles (e.g., Accountant, Site Engineer) who lack read/select permissions on the `Project` doctype.

---

## 2. Completed Implementation & Architecture

We have implemented changes across the following layers to build a clean authority path:

### A. Server-Side Changes (`apps/construction/construction/api/scope_context_api.py`)
1. **Strict Permission Enforcement**: Added `ignore_permissions=False` in `get_user_scope_hierarchy` when fetching companies, cost centers, projects, and departments. This keeps restricted users from receiving unauthorized records.
2. **Sentinel-based Parameter Handling (`_UNSPECIFIED` pattern)**:
   - Modified `set_scope_context` to use a sentinel object instead of `None` as the default argument value.
   - This resolves a critical issue where explicitly clearing dimensions (e.g., passing `project=None`) was ignored because `frappe.new_doc()` initialized fields with database defaults (e.g. `PROJ-0002`), which bypassed the standard `project is not None` truthiness check.
   - Values are now validated directly on the final resolved document fields before saving.

### B. Client-Side Hydration (`apps/construction/construction/public/js/scope_context.js`)
- **Server-First Hydration**: On page load, `this.current` in-memory state is strictly initialized from `frappe.boot.scope_context`.
- **Validation Rules**: Cached `localStorage` keys are merged *only* if they match the server boot `scope_version` and the current `window.location.origin`. Mismatched or stale dimensions are discarded and flushed immediately.
- **Single Authority Path**: Added `getValidatedCurrentScope()` helper API on `window.scopeContext`. All consumers have been updated to read the validated scope through this interface.

### C. Treeview UI Hardening (`boq_structure_tree.js` — Public and Doctype Settings)
- **Rename Project Filter to `scope_project`**: Renaming the filter to a standard `Data` field type prevents Frappe's tree engine from converting it to a `Link` control and calling `/api/method/frappe.desk.search.search_link?doctype=Project`.
- **CSS Injection (Firefox Display Leak)**: Added a dynamic style tag on `onload` (`.page-form [data-fieldname="scope_project"] { display: none !important; }`) to guarantee the field wrapper is hidden in all browsers.

### D. Client-Side Class-Level Overrides (`ct_link_control.js` Prototype Patching)
- **Defensive Prototype Overrides**: We patched the native `frappe.ui.form.ControlLink` prototype methods:
  - `validate(value)`
  - `validate_link_and_fetch(value)`
  - `get_search_args(txt)`
  - `on_input(e)`
- **Behavior**: If the user lacks read/select permission on `df.options`, these overrides return immediately (resolving validation promises locally) without making any server-side AJAX requests.
- **UI State**: The native input field is disabled and set to `readonly`, and its event listeners (`focus`, `input`) are removed.

---

## 3. Current Status

1. **Integration Tests**: All 14 integration tests inside `test_scope_context.py` pass successfully:
   ```bash
   bench --site v16.localhost execute construction.tests.test_scope_context.run_all_tests
   ```
2. **The Problem**: Despite the code being successfully compiled and server cache cleared, the user reports the changes are **"not working yet"**.
3. **Console Symptoms**: The browser console still logs `403 Forbidden` on:
   ```
   GET http://v16.localhost:8000/api/method/frappe.desk.search.search_link?txt=&doctype=Project&ignore_user_permissions=0&reference_doctype=BOQ%20Structure&page_length=10&link_fieldname=project
   ```

---

## 4. Areas Requiring Senior Engineering Guidance

We suspect a caching, environment, or asset pipeline issue is preventing the client overrides from taking effect. We would appreciate guidance on:

### 1. Asset Pipeline & Asset Cache-Busting
- We incremented the asset version in `hooks.py` to `v=15` for `/assets/construction/js/overrides/ct_link_control.js`.
- Are there nginx-level, Cloudflare, or browser-level caching rules preventing `hooks.py` asset versions from updating?
- Does the dev environment serve pre-bundled production scripts (like `desk.bundle.js`) where our custom overrides are not merged, or is it reloading dynamic assets correctly?

### 2. Native Frappe Control Initialization Timing
- Our prototype patches run on `$(document).ready()`. Is it possible that the tree view page or standard page loaders initialize native `ControlLink` instances *before* our script has been executed/patched?
- If so, should we move the prototype overrides to an earlier boot sequence hook (e.g. `desk_javascript` or standard desk boot hooks in `hooks.py`)?

### 3. Route Options & Global Route Parsing
- When loading `/desk/boq-structure?boq_header=BOQ-2026-0006&project=PROJ-0002`, Frappe reads `project=PROJ-0002` from route options.
- Since we renamed the filter to `scope_project`, what is triggering the validation of `project` under the hood? Is it a default field layout in the `BOQ Structure` Doctype, or list-settings query caching?

---

## 5. File References
All modifications have been committed locally. The relevant files are:
1. **Python API / Server-Side**: [scope_context_api.py](file:///home/mohamed/frappe-bench/apps/construction/construction/api/scope_context_api.py)
2. **Client-Side Prototype Patch**: [ct_link_control.js](file:///home/mohamed/frappe-bench/apps/construction/construction/public/js/overrides/ct_link_control.js)
3. **Doctype Tree Settings**: [boq_structure_tree.js (doctype)](file:///home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure_tree.js)
4. **Public JS Tree Settings**: [boq_structure_tree.js (public)](file:///home/mohamed/frappe-bench/apps/construction/construction/public/js/boq_structure_tree.js)
5. **App Hooks**: [hooks.py](file:///home/mohamed/frappe-bench/apps/construction/construction/hooks.py)

---
Please let us know if there is a specific asset pipeline flag we should clear or if we should run an alternate asset compiler.
