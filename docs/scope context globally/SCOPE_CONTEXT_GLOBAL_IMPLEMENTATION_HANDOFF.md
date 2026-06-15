# Engineering Handoff: Global Scope Context Standardization

**To:** Open Code AI Agent
**From:** Head of Engineering
**Subject:** App-Wide Standardization of Scope Context & Elimination of 403 Permission Errors

## 1. Context & Mission

We are standardizing the **Scope Context** system across the entire `construction` app. The Scope Context (Company, Cost Center, Project) must serve as the absolute **Single Source of Truth** for user session context.

**The Mission:** Scale the architectural fixes we applied to `BOQ Structure` to all other Doctypes (e.g., Daily Progress Report, Variation Order, Subcontractor Billing, etc.) in the app. We must completely eliminate `403 Forbidden` console errors that occur when restricted users (like Site Engineers or Accountants) attempt to load lists, trees, or forms containing `Project`, `Company`, or `Cost Center` fields.

## 2. The Root Cause of the 403 Forbidden Errors

Through deep debugging, we found the definitive root cause of the client-side permission errors. **You must deeply understand this before writing code:**

1. **The Trap:** A DocType has a field like `project` set as `fieldtype: "Link"`, `options: "Project"`, and **`in_standard_filter: 1`**.
2. **The Mechanism:** When Frappe loads a list or tree view, it autonomously reads the DocType metadata and initializes a native `ControlLink` for any field with `in_standard_filter: 1`. 
3. **The Failure:** During initialization, this native control immediately fires an AJAX request: `/api/method/frappe.desk.search.search_link?doctype=Project`.
4. **The Consequence:** Because restricted users do not have read/select access to the generic `Project` doctype, the server returns `403 Forbidden`.
5. **The Mitigation Fallacy:** Our client-side JS overrides (like `ct_link_control.js` prototype patching) **cannot stop this**. Frappe's filter instantiation happens at a lower level and earlier in the lifecycle, and our patches explicitly skip `read_only` fields anyway. 

**The only reliable fix is at the DocType metadata level.**

## 3. Architecture: The Single Source of Truth

The Scope Context architecture relies on a strict flow of authority:

- **Server-Side Authority:** `construction/api/scope_context_api.py` securely determines what the user is allowed to see via `get_user_scope_hierarchy(ignore_permissions=False)`.
- **Boot Hydration:** This data is injected into `frappe.boot.scope_context`.
- **Client-Side API:** `window.scopeContext.getValidatedCurrentScope()` is the ONLY acceptable way to read the active scope in JavaScript. LocalStorage is strictly a short-lived cache/cross-tab channel and is validated against the boot state.

## 4. Execution Directives: What TO DO

You are tasked with auditing and updating all relevant DocTypes and client scripts in the `construction` app.

### Step 1: DocType Metadata Audit & Fixes
Find all fields representing scope dimensions (`project`, `company`, `cost_center`) across all `construction` app DocTypes.
- **Action:** Set `"in_standard_filter": 0` in the DocType JSON for these fields. This is the primary fix to stop the autonomous 403 requests.
- **Action:** If the field is purely for displaying the scope on a document, consider changing its `fieldtype` from `"Link"` to `"Data"`, or keep it as `"Link"` but ensure it is `"read_only": 1` and `"in_standard_filter": 0`. 
- **Action:** Run `bench migrate` to apply metadata changes.

### Step 2: Client-Side JS Refactoring (Forms, Lists, Trees)
Audit all `.js` files in `apps/construction/construction/public/js/` and `apps/construction/construction/doctype/*/*.js`.
- **Action:** Replace any direct `frappe.db.get_value("Project", ...)` or `frappe.db.get_value("Company", ...)` calls. Restricted users cannot execute these.
- **Action:** Instead of querying the `Project` doctype directly, read data from a parent document the user *does* have access to (e.g., reading the company from `BOQ Header`), or write a new `ignore_permissions=False` whitelisted API method that safely returns the required data without exposing the whole `Project` doctype.
- **Action:** Ensure all client-side logic reads the active scope exclusively via:
  ```javascript
  const scope = window.scopeContext && window.scopeContext.enabled 
      ? window.scopeContext.getValidatedCurrentScope() 
      : {};
  const currentProject = scope.project;
  ```

### Step 3: UI Sync & Cleanup
- **Action:** Ensure any custom JS filters (like `scope_project` in tree views) use `fieldtype: "Data"` to prevent native link validation.
- **Action:** Consolidate duplicate scripts. If you find duplicate logic (e.g., a tree script in `public/js` and one in the `doctype` folder), delete the orphan and ensure `hooks.py` points to the canonical doctype version.
- **Action:** After updating JS files, always bump the cache buster versions (`?v=XX`) in `hooks.py` (`app_include_js`) to ensure clients receive the fix.

## 5. Anti-Patterns: What NOT TO DO (STRICT)

- 🚫 **DO NOT grant restricted roles read/select permission on the `Project`, `Company`, or `Cost Center` doctypes.** This violates the security model. Scope must be enforced dynamically.
- 🚫 **DO NOT rely on `ct_link_control.js` or CSS tricks to fix the 403 errors.** While we use CSS to visually hide UI elements, the network request must be stopped at the metadata level (`in_standard_filter: 0`).
- 🚫 **DO NOT use `frappe.db.get_value("Project", ...)` in client scripts.** It will fail for restricted users.
- 🚫 **DO NOT let LocalStorage dictate the scope.** Always validate against `frappe.boot.scope_context` using `getValidatedCurrentScope()`.
- 🚫 **DO NOT blindly change fieldtypes to "Data" without auditing reports.** If you change a `Link` field to `Data`, check if any SQL reports or Python scripts rely on it being a Link. If it's too risky, keep it as `Link` but set `in_standard_filter: 0` and `read_only: 1`.

## 6. Definition of Done

1. A restricted user (e.g., Site Engineer) can log in, navigate to any list, form, or tree view in the Construction app, and experience **zero** `403 Forbidden` errors in the network tab or console.
2. The active project/company context is seamlessly applied to list filters and form defaults using `window.scopeContext`.
3. All metadata changes are synced to JSON files.
4. `hooks.py` cache busters are updated.

Please begin by running a `grep` or script audit across `apps/construction/construction/doctype/` to identify all DocTypes with `project`, `company`, or `cost_center` fields that have `in_standard_filter: 1`. Let's get to work.
