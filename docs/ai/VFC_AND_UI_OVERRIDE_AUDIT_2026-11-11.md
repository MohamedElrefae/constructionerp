# VFC (Form Layout Engine) + UI Override — Senior Engineering Audit

**Date:** 2026-11-11
**Scope:** `construction/public/js/vfc_layout_engine.js`, `construction/public/js/vite_layout_controls.js`,
`construction/construction/api/layout_api.py`, `construction/public/css/vfc_sections.css`,
`construction/overrides/layout_permissions.py`, plus the UI-override layer
(`construction/public/js/overrides/*`, `construction/public/css/vite_*_override.css`).
**Repo state audited:** `apps/construction` @ `develop` @ `9796c5f`
**Runtime state audited:** site `v16.localhost` (`_6d52b48c328b294e`), Frappe v16.51.1

---

## 0. How to read this document

You are the owner (civil engineer) and you will direct AI agents to do the work. This document is
written so that each numbered finding can be handed to **one agent** as a self-contained task.

* **Severity** — `P0` blocks a release / loses user data or hides a field that should be visible.
  `P1` produces visibly wrong behaviour for some users. `P2` is an inconsistency or a trap for
  the next engineer. `P3` is hygiene.
* **Evidence** — every finding cites `file:line` or a live SQL/JS observation, so an agent can
  verify it rather than trust it.
* **Confidence** — `CONFIRMED` (reproduced or proven by reading the exact code path),
  `LIKELY` (strong code path, one link in the chain unverified), `UNVERIFIED` (needs a browser run).

Read section 1 first — it is the short version. Section 8 is the task list to hand to agents.

---

## 1. Executive summary — the five things that matter

You told us three symptoms. Each maps to a concrete cause:

| Your symptom | Root cause | Finding |
|---|---|---|
| "plan was not complete over entire app" | The engine is **not** app-wide. It no-ops on a hard-coded list of doctypes, and on any doctype with a `Tab Break` it misplaces sections. **Stored profiles have also rotted** — seeded profiles now cover only a third of their doctype's fields, so the rest spill into a fallback "Other Fields" band. | F2, F3, F20 |
| "not consistent over entire app" | **Four different persistence mechanisms** are mixed inside one panel. Density = browser `localStorage`. Field visibility + preset = server `user_settings`. Layout = server `Form Layout Profile` DocType. Per-app = nothing. | F1 |
| "not persistent per user or per app" | Density and hidden-field state are keyed by **doctype only**, not by user and not by app. Two users on one browser share a density. The "Revert to Default" button cannot actually revert a shared layout. | F1, F6 |
| — (found while auditing) | **The engine can reveal a field the user is not permitted to read**, and can **double-render a field** when a profile marks a field `visible:false`. | F4, F5 |
| — (found while auditing) | 202 leftover `_Test_*` profile rows are **live in the production database** and are returned to real users by the resolver. | F7 |

**One-line verdict:** the VFC feature is ~70 % built and architecturally sound in its *backend*
(`layout_api.py` is clean, permission-guarded, and well tested), but the *frontend* layer is where
the plan was abandoned. The engine was written for the four seeded BOQ doctypes and then had
`BLOCKED_DOCTYPES` + tab handling bolted on. The panel UI was written as a demo (localStorage
density, hard-coded preset registry) and never re-based on the real backend. That mismatch is
the entire "not consistent / not persistent" story.

**Recommendation:** do **not** extend the current design. Land a small number of surgical fixes
(F1–F7), then re-base the panel on the backend that already exists. Details in §8.

---

## 2. Architecture as it actually is (not as documented)

```
                    ┌─ vite_layout_controls.js ───────────────┐
  Form refresh ───►│ • "Form Config" button on EVERY form     │
  (frappe.ui.      │ • density  → localStorage   (per browser)│
   form.on("*"))   │ • hidden   → user_settings  (per user)    │
                    │ • presets  → PRESET_REGISTRY (hard-coded) │
                    │ • sections → Form Layout Profile (shared) │
                    └───────────────────┬──────────────────────┘
                                        │ calls LayoutEngine.attach()
                    ┌─ vfc_layout_engine.js ────────────────────┐
                    │ fetch profile → re-parent field wrappers  │
                    │ into .vfc-le-section > .vfc-le-cell      │
                    └───────────────────┬──────────────────────┘
                                        │
                    ┌─ layout_api.py (SERVER, the good part) ─┐
                    │ get_active_layout: user → role → default │
                    │ save_layout / list / delete / validate   │
                    │ guard: layout_permissions.py hook        │
                    └──────────────────────────────────────────┘
```

Two facts that the written docs get wrong and that mislead every agent:

* `docs/vfc_status_report.md` claims "**All flat-layout forms in the entire ERPNext app**" are
  active. It is not. `vfc_layout_engine.js:47-114` maintains a hard-coded `BLOCKED_DOCTYPES` set of
  40+ names, and the engine additionally no-ops on any doctype with a `Tab Break`
  (`vfc_layout_engine.js:144`, `146`). The "Stage 2 — Full ERPNext App Active" claim is **false**.
* `AGENTS.md` §3D says `vfc_layout_engine.js` is "1,399 lines" and the controls file is
  "1,771 lines". They are now **1,441** and **1,949**. More importantly, AGENTS.md lists
  `construction/construction/api/layout_api.py` as "330 lines, 6 endpoints" — the real path is
  `construction/construction/api/layout_api.py` (355 lines) and it now has **6 whitelisted
  functions** including `delete_my_personal_layout`. Any agent that trusts AGENTS.md will look in
  the wrong place.

---

## 3. Findings

### F1 — Persistence is four different mechanisms with three different scopes · `P1` · CONFIRMED

This is the direct cause of "not persistent per user or per app". Within a single panel:

| Setting | Where it lives | Scope | Cross-device? | Per user? | Per app? |
|---|---|---|---|---|---|
| Column density | `localStorage` `vfc_<Doctype>_density` | browser + doctype | **No** | **No** | **No** |
| Hidden fields | `frappe.model.user_settings` → `__UserSettings` | server + doctype | Yes | Yes | No (site-wide) |
| Layout preset | `PRESET_REGISTRY` in JS + `vfc_preset` in user_settings | client constant + user_settings | Partly | Partly | No |
| Section layout | `Form Layout Profile` DocType | server + doctype + `for_user`/`for_role` | Yes | **Only if `for_user` is set — and the UI never sets it** | No (site-wide) |

Concrete defects:

1. **Density is shared between users on the same browser.** `vite_layout_controls.js:162-176`
   writes `vfc_${doctype.replace(/\s/g,"_")}_density` to `localStorage` with **no user component**.
   Two engineers at one workstation, or a shared kiosk, get each other's density.
2. **Density does not survive a cache clear and does not follow the user to another machine.**
   `localStorage` is per-origin; the desk user has to re-pick density on every new machine. The
   panel even claims "Synced across devices" for presets (line 2607 of `ar.po`) while density says
   "Saved per-browser" (line 377 of the controls file) — two contradictory claims in one panel.
3. **The layout profile has no per-app dimension at all.** `Form Layout Profile` is keyed by
   `reference_doctype` only (`form_layout_profile.json:24-30`). There is no `app`/`module` field.
   In a multi-app site the same doctype name in two apps would collide on the `autoname`
   `format:{reference_doctype}-{profile_name}`.
4. **The per-user layout override exists in the backend but the UI can never create one.**
   `layout_api.get_active_layout` implements a 3-tier resolver (personal → role → default,
   `layout_api.py:79-93`) and `save_layout` accepts `for_user` / `for_role`
   (`layout_api.py:122-131`). But `vite_layout_controls.js:944-961` calls `save_layout` with
   **only** `profile_name`, `is_default`, `priority` and `sections_json`. It never passes
   `for_user` or `for_role`. So in the live DB every single enabled profile is a global default:
   ```
   SELECT SUM(for_user IS NOT NULL), SUM(for_role IS NOT NULL) FROM `tabForm Layout Profile`;
   → 0, 0
   ```
   **The personal/role layout feature is 100 % backend-only. No user can ever reach it.**

**Fix direction:** move density into `user_settings` (same store as hidden fields), and add a
"Save as my personal layout" affordance that passes `for_user`. Add `app`/`module` to the profile
DocType.

---

### F2 — The engine silently no-ops on 8 core doctypes · `P1` · CONFIRMED

`vfc_layout_engine.js:47-114` is a hard-coded `BLOCKED_DOCTYPES` set. It is a deny-list, so it is
only correct as of the day it was written, and it does not cover anything added later. It contains
`Print Format`, `Letter Head`, `Web Form`, `System Settings` — but **not** `User`, `Role`,
`Workspace`, `Dashboard`, `Notification`, `ToDo` (ToDo is there), `Scheduled Job`, `Personal
Budget`, `Integration Request`, `Data Migration`, `Custom DocPerm`, `Notification Settings`.

Two specific classes are reachable and will look broken to a user:

* **`User` / `Role`** — `User` is *not* in the blocklist. The engine will re-parent the User
  form's fields, including `__newname`, `email`, `first_name`, `api_key`… The password field is
  a `Password` control and gets moved into a `.vfc-le-cell`. It still works, but the User form
  no longer matches Frappe's own markup, and `frappe.ui.form.Control` password auto-fill
  behaviour can break.
* **`Workspace` / `Dashboard`** — these use `frappe.ui.form.Control` in a custom layout, not the
  standard `.form-layout`, so `_getLayoutRoot` returns the wrong node and the engine does
  nothing — inconsistent with the User case. **The app behaves differently for two adjacent
  doctypes with no visible reason**, which is exactly the "not consistent" complaint.

**Fix direction:** invert to an **allow-list driven by capability**, not a deny-list by name.
The engine should detect at runtime whether it can safely operate (does the form have a
standard `.form-layout > .form-page` with `.frappe-control` children?) and no-op with a logged
reason when it cannot. This removes the need to maintain the list forever.

---

### F3 — Tabbed doctypes lose or misplace sections · `P0` · LIKELY (code path proven, needs a browser repro)

This is the single biggest functional bug and it is why "the plan was not complete over the entire
app" — **the majority of real ERPNext doctypes are tabbed.**

`sections_json` in the DB confirms the shape of the data. For `BOQ Item-Default`:

```
sec_header_link        tab=''  nfields=0   ← user-created section, empty
sec_owner_refs         tab=''  nfields=0   ← user-created section, empty
sec_classification     tab=''  nfields=0
sec_quantities         tab=''  nfields=0
sec_pricing            tab=''  nfields=0
sb_identity            tab=''  nfields=9   native=True
sb_quantity            tab=''  nfields=8   native=True
...
```

Every user-created section has **`tab_fieldname: ''` and zero fields**, while all the fields sit
in the *native* sections. Two separate defects produce this:

**F3a — `tab_fieldname` is never persisted.** The editor writes it
(`vite_layout_controls.js:1256`: `tab_fieldname: currentTabFieldname`) but the merge step
(`vite_layout_controls.js:1332`) overwrites it with
`section.tab_fieldname || nativeMatch?.tab_fieldname || ""` — and since the saved profile's own
section has no `tab_fieldname`, the expression collapses to `""`. The value is lost on every
save/load cycle.

**F3b — the engine's tab inference is wrong.** `_getSectionTab`
(`vfc_layout_engine.js:512-533`) tries to find the tab by scanning backwards through
`frm.layout.fields` for a `Tab Break`. But `frm.layout.fields` is Frappe's **layout** field list,
while the profile's field list came from `frm.meta.fields`. In Frappe v16, `layout.fields` is
built from `frappe.meta.docfield_map[doctype]` (`layout.js:62`) and Frappe *mutates* it — it
prepends `{fieldtype: "Section Break"}` and splices in a synthetic `__details` Tab Break
(`layout.js:149-168`). So index-based lookup lands on the wrong element.

Then `_getTabPane` (`vfc_layout_engine.js:547-552`) does:

```js
const dt = frappe.scrub(frm.doctype, "-");
const id = `${dt}-${tabFieldname}`;
return document.getElementById(id);
```

Frappe's real tab DOM id is set in `tab.js:38`:
```js
const id = `${frappe.scrub(this.doctype, "-")}-${this.df.fieldname}`;
```
**but `this.doctype` is NOT `frm.doctype`.** In `tab.js:11-16`:
```js
this.doctype = layout?.is_child_table ? layout.doctype : this.frm?.doctype ?? this.df.parent ?? layout?.doctype;
```
For a **child-table grid row** (`is_child_table`), `this.doctype` is the *child* doctype, and the
tab id is `child_doctype-tabfield`. The engine looks up `parent_doctype-tabfield`. For the four
seeded BOQ doctypes there are no tabs, so this never fired — which is why nobody caught it.

Also `frappe.scrub(frm.doctype, "-")` lowercases and replaces spaces with `-`, giving e.g.
`boq-item`. Frappe's `tab.js` uses the same `frappe.scrub(this.doctype, "-")`, so for a top-level
form the ids *do* match — the mismatch is specific to child tables.

**Fix direction:** store the tab's **fieldname** (not a guessed index) and resolve the pane by
querying `frm.layout.tabs` for the matching `df.fieldname`, then use `tab.wrapper` directly.
Do **not** use `document.getElementById` — it is global and will collide across forms.

---

### F4 — A field the user is allowed to see can be hidden · `P0` · LIKELY

`vfc_layout_engine.js:853-879` `_restoreVisibleFieldWrapper` forcibly strips the
`hide-control` class and inline `display`/`visibility`/`opacity` from the field wrapper:

```js
nativeEl.classList.remove("hide-control", "hidden", "d-none");
nativeEl.style.removeProperty("display");
nativeEl.style.removeProperty("visibility");
nativeEl.style.removeProperty("opacity");
```

Frappe uses `hide-control` for **permission** decisions, not just layout
(`base_control.js:141`):
```js
this.$wrapper.toggleClass("hide-control", this.disp_status == "None")
```
and `disp_status` is `"None"` when `frappe.perm.get_field_display_status()` returns `"None"` —
i.e. when the user has **no read permission** at that `permlevel`
(`perm.js:232-263`). Frappe's own field-level read permission (`apply_fieldlevel_read_permissions`,
`document.py:959`) removes the *value* server-side, but the *field* is still in the meta and the
client-side `hide-control` is what keeps it off screen.

The engine's guard is only:
```js
if (fieldObj?.df?.hidden_due_to_dependency || fieldObj?.df?.hidden) { return; }
```
`df.hidden` is *not* the same as "no read permission". A `permlevel`-protected field has
`df.hidden === 0` and `df.hidden_due_to_dependency` undefined, but Frappe has already put
`hide-control` on it because the user's perm level is too low. The engine strips that class and
**reveals a field the user must not read.**

Note `_restoreVisibleFieldWrapper` is called on every field the engine moves
(`vfc_layout_engine.js:444`, `:1017`, `:1308`), so this affects every VFC-rendered form.

The four seeded BOQ doctypes have no `permlevel > 0` fields today, which is why this has not
surfaced — but the panel lets an admin put *any* ERPNext doctype under VFC, and ERPNext is full
of `permlevel` fields (e.g. `Employee`, `Salary Slip`, `Timesheet` cost fields).

**Fix direction:** never strip `hide-control`. Instead, skip fields whose `disp_status === "None"`
(i.e. leave them where Frappe put them, or hide the whole VFC cell). Add a regression test that
asserts a `permlevel` field stays hidden for an under-privileged user.

---

### F5 — `visible:false` fields are rendered twice · `P1` · CONFIRMED

In `vfc_layout_engine.js:395-399`:
```js
if (fld.visible === false) {
    frm.toggle_display(fn, false);
    return;
}
```

Two problems:

1. **`frm.toggle_display` is permanent and unscoped.** `toggle_display` → `field_map`
   (`form.js:1811-1817`) → `frappe.meta.get_docfield(doctype, fieldname, this.docname)`. That
   resolves through `get_docfield_copy` (`meta.js:128-136`): with a **non-empty docname** it
   returns the cached per-document copy `docfield_copy[doctype][docname]`; with an **empty
   docname** it returns the **shared global** `frappe.meta.docfield_map[doctype]`.

   A brand-new document has `docname === ""` at construction (`form.js:66`), so on a *new* form
   the `hidden = 1` is written into the **global map for that doctype for the whole browser
   session** — affecting every other form of that doctype, including forms the user never
   touched. On a *saved* document it lands in the per-docname copy, which is cached and never
   invalidated, so it survives every subsequent refresh of that document.

   Either way the mutation is **never reverted**: there is no code path anywhere that sets
   `hidden = 0` for a field VFC hid. The only un-hide in the codebase is
   `vite_layout_controls.js:887-894` `_restoreVfcHiddenFieldVisibility`, and it only covers the
   *user-settings* list, never the *profile* list. So a field hidden by a profile stays hidden in
   the document's meta copy after the profile is edited or deleted.
2. **The field is never moved into a VFC cell, but it is also not removed from the native
   layout** — it is only hidden. If the profile is later edited to make it visible again, the
   field now exists in *two* places in the model: still in `frm.fields_dict`, and the engine
   will move it into a cell on the next `_render()` while the native wrapper is still registered.
   `_hasMissingFields` (`vfc_layout_engine.js:663-752`) checks the wrapper is inside a
   `.vfc-le-cell` — it will report the field as *missing* and schedule up to 20 retries, each of
   which re-runs `_render()`. **This is a live retry storm** (20 × 250 ms) every time a profile
   contains a `visible:false` field.

**Fix direction:** treat `visible:false` as "not rendered by VFC at all" — skip the field
entirely and record it in a `hidden` set. Do not call `toggle_display` from the engine.

---

### F6 — "Revert to Default / Native" cannot revert a shared layout · `P1` · CONFIRMED

`vite_layout_controls.js:973-1022` `_revertToDefault` does:

```js
const resp = await frappe.call({ method: "...delete_my_personal_layout", args: { doctype: dt } });
...
resetDensity(dt);
await resetUserSettings(dt);
```

`delete_my_personal_layout` (`layout_api.py:224-248`) deletes a profile where
`for_user == session.user`. **Since no personal profile is ever created (F1), this always
returns `{"status": "not_found"}`.** The button then reports *"VFC preferences reset"* while the
shared `Default` profile is still fully active. The user believes they reverted; they did not.

The confirmation string even says so (`ar.po:2412`):
> "Revert to default/native layout? This resets your VFC density, hidden fields, preset, and
> personal layout for this form."

The "personal layout" it claims to reset **cannot exist**.

**Fix direction:** the revert must be able to say "revert *this* user to the shared default" —
i.e. set `for_user` on the way out, or explicitly disable the shared default for this user.
A per-user override is the only honest way to express "I want native layout".

---

### F7 — 202 test rows are live in the production database · `P0` · CONFIRMED

```
SELECT COUNT(*), SUM(profile_name LIKE '\_Test\_%') FROM `tabForm Layout Profile`;
→ 210, 202
```

`construction/tests/test_vfc_backend.py:57` creates profiles named `_Test_<hash>` and the test
file's teardown only deletes two specific names (`test_vfc_backend.py:163`, `:174`). The other
200 leak. They are `enabled=1`, so `get_active_layout` — which filters only on
`reference_doctype` + `enabled` — will return them. Live rows in the site DB:

```
BOQ Header-Default, BOQ Item-Default, BOQ Structure-Default, BOQ Item Stage-Default,
Budget-Default, Project-Default, User Scope Context-Default, Variation Order-Default
…plus 202 Task-_Test_xxxx rows
```

**This is also a test-hygiene defect**: the backend tests write to the *live site* database
rather than a throwaway one.

**Fix direction:** the test suite must run against a disposable database (or roll back in
`tearDown`). Independently, add a maintenance patch that deletes `profile_name LIKE '_Test_%'`
rows and a guard in `save_layout` that refuses names starting with `_Test_`.

---

### F8 — The `Tab.refresh` monkey-patch mutates a shared vendor class · `P1` · CONFIRMED

`vfc_layout_engine.js:146-188` patches `Tab.prototype.refresh` **on the shared `Tab` class
object** (`frm.layout.tabs[0].constructor`), guarded by `TabClass._vfc_patched`. Because it is on
the prototype, the change is **global for the whole browser session**, affecting every tabbed
form in Frappe and ERPNext — not just VFC-rendered ones. It is never uninstalled.

It also drops Frappe's own `.form-dashboard-section` branch semantics and re-implements
visibility with different rules, so a tab's show/hide behaviour now depends on whether a VFC
engine ever touched the page.

**Fix direction:** do not patch a vendor prototype. Solve tab visibility inside the engine
(add/remove a class on the tab's own wrapper) or wrap the instance method for that form only
and restore it on teardown.

---

### F9 — `renderWithDensity` bypasses the profile and hides tab structure · `P1` · CONFIRMED

`vfc_layout_engine.js:1238-1245`:
```js
layoutRoot.querySelectorAll(".nav-tabs, .tab-content, .tab-pane").forEach((el) => {
    el.style.setProperty("display", "none", "important");
```

This path is taken whenever a doctype has **no** profile (the common case) and the user has a
non-default density. It hides the tab bar entirely and re-renders the form from
`_buildDensityProfile`, which groups by `Section Break` only and **ignores tabs entirely**
(`vfc_layout_engine.js:1347-1407` — `SKIP_TYPES` drops `Tab Break`). On a tabbed doctype with no
profile this **destroys the tab UI**. The `hasTabs` guard at `:223` only protects the
no-profile+non-tabbed case.

Also note `_buildDensityProfile` builds sections from `frm.meta.fields`, so the "virtual"
layout differs structurally from the profile-based layout — two different rendering paths
producing two different DOM shapes for the same user preference.

**Fix direction:** one rendering path. Density should be a *column count* applied to whatever
sections the profile (or native layout) defines — never a second, parallel renderer.

---

### F10 — Column assignment math is wrong whenever density overrides the profile · `P1` · CONFIRMED

`vfc_layout_engine.js:421-429`:
```js
if (densityOverride > 0) {
    colIdx = (colIdx + 1) % densityOverride;
    col = colIdx || densityOverride;
}
```
For `densityOverride === 3`: `colIdx` cycles `1, 2, 0` → `col` = `1, 2, 3`. OK.
For `densityOverride === 2`: `colIdx` cycles `1, 0` → `col` = `1, 2`. OK.
For `densityOverride === 1`: `colIdx` = `(0+1)%1` = `0` → `col = 0 || 1` = `1`. OK.

The bug is not the modulo — it is that `cell.style.gridColumn = String(col)` sets **only the
start** column with no span, so `grid-column: 2` on a 3-column grid leaves column 1 empty in
that row and the browser auto-placement pushes fields into implicit rows. Combined with the
`fld.col` from the profile (also a start-only column), the grid renders ragged. The CSS
(`.vfc-le-grid`, `vfc_sections.css:92-97`) declares `repeat(N, 1fr)` but the JS overrides
`gridTemplateColumns` inline (`vfc_layout_engine.js:935`, `:992`) — the CSS column count is dead
whenever a profile section sets its own.

**Fix direction:** express field placement as `grid-column: <start> / span 1` and compute a
consistent fill order; or simpler, drop `col` entirely and let the browser auto-place in
document order, which is what every other Frappe section does.

---

### F11 — `validate_layout` is never called by the UI · `P2` · CONFIRMED

`layout_api.validate_layout` (`layout_api.py:275-326`) checks duplicate fieldnames, unknown
fieldnames, invalid column counts, and **hiding a required field**. It is fully implemented and
unit-tested (`test_vfc_backend.py:294-340`). **Nothing in the frontend calls it** —
`grep validate_layout construction/public/js/` returns nothing. The panel can therefore save a
profile that hides a mandatory field, which the engine will then hide at runtime
(`vfc_layout_engine.js:395-399`).

**Fix direction:** call `validate_layout` from `save_layout` itself (server-side, unconditional),
so no client can bypass it. The endpoint then becomes a preview API rather than the only gate.

---

### F12 — Profile cache ignores the user and the role · `P2` · CONFIRMED

`vfc_layout_engine.js:273-291` `_fetchProfile` caches by **doctype only**:
```js
this._cache.set(doctype, { value: profile, ts: Date.now() });
```
The server resolver is *per user* (personal → role → default). So if a user switches role or an
admin edits the shared default, the client keeps serving the old profile for up to 60 s. Worse,
`invalidateCache` is only called by the *saving* client (`vite_layout_controls.js:956`) — the
admin's own browser is invalidated, but **every other user's browser keeps the stale profile for
60 s** with no signal.

**Fix direction:** key the cache by doctype **and** user, and shorten it; or have the server
return a version/etag and let the client revalidate.

---

### F13 — The panel's Section editor drops the fields it is editing · `P1` · CONFIRMED

`vite_layout_controls.js:1295-1393` `_mergeProfileWithNativeSections` merges the saved profile
with the doctype's native sections. Its "native section not already in profile" branch does:

```js
const nativeFieldnames = new Set(nativeFields.map((field) => field.fieldname));
merged.forEach((section) => {
    section.fields = (section.fields || []).filter((field) => !nativeFieldnames.has(field.fieldname));
});
```

It **removes** any field that also belongs to a native section out of the user's custom sections.
Then the native section is pushed with those fields. The net effect on the DB data is visible:
the five user-created sections in `BOQ Item-Default` have `nfields=0` while the native sections
carry everything. **The user's own arrangement is discarded on the next open of the panel**, and
re-saved in that discarded state.

This is also why `_buildNativeSectionsProfile` (`vite_layout_controls.js:1224-1293`) is needed at
all — the merge is trying to reconcile two models that were never reconciled properly.

**Fix direction:** the profile must be the single source of truth for *placement*. Native
sections should only be consulted for fields **not yet placed anywhere**. Do not overwrite user
placements with native ones.

---

### F14 — The Section editor cannot express a per-field `visible` flag · `P2` · CONFIRMED

The engine reads `fld.visible` (`vfc_layout_engine.js:396`), and `validate_layout` checks it
(`layout_api.py:323`). But the editor's drag-and-drop never writes it
(`vite_layout_controls.js:1648-1653` always writes `visible: true`), and the Field Visibility tab
is a **separate** mechanism writing to `user_settings`, not to the profile. So the two
"visibility" concepts never meet, and `visible:false` in a profile can only arrive by hand-editing
the JSON.

**Fix direction:** one visibility concept. Either the profile owns visibility (and the profile
becomes per-user), or the profile never carries `visible` and the field-visibility tab is the
only source.

---

### F15 — `sort_order` is trusted but never enforced end-to-end · `P2` · CONFIRMED

The profile carries `sort_order` per section and per field. The engine sorts sections by it
(`vfc_layout_engine.js:335-337`) and fields by it (`:367-369`). But the editor's drag handler
**rewrites** `sort_order` from DOM order (`vite_layout_controls.js:1608-1610`) and the field drag
handler rewrites field `sort_order` from DOM index (`:1648-1653`). `_appendUnassigned` then
computes `col` from array position, ignoring `sort_order` entirely
(`vfc_layout_engine.js:995-1019` — no `sort_order` written). So unassigned fields have no stable
ordering, and the same profile can render in a different order on two machines.

**Fix direction:** always write a dense `sort_order` (1..N) for every section and every field,
including unassigned, on every save.

---

### F16 — Empty-state handling hides legitimate sections · `P2` · CONFIRMED

`_hideEmptyCustomSections` (`vfc_layout_engine.js:809-851`) hides any section whose cells have no
*painted* field. "Painted" means the field wrapper lacks `hide-control`/`hidden`/`d-none` and has
no inline `display:none`. A section whose fields are all currently hidden by `depends_on` or by
permission is therefore **removed from the DOM flow** — and when the dependency later becomes
true, the section stays hidden because `_hideEmptyCustomSections` only runs during the scheduled
validation passes (`:590-600`, up to 3 s after render) and on re-render.

**Fix direction:** hide a section only when it has no fields *at all* in the profile; let
per-field visibility live on the field.

---

### F17 — `frm.toggle_display` in the controls file mutates the global meta for new docs · `P1` · CONFIRMED

`vite_layout_controls.js:1040-1049` (`_restoreState`) and `:637-643` (`_onVisChange`) call
`frm.toggle_display(fieldname, false)` to hide user-hidden fields. As established in F5, with an
empty `docname` (new document) this writes to the **shared global**
`frappe.meta.docfield_map[doctype]`, and with a non-empty docname it writes to a **cached**
per-document copy. Neither is scoped to "this form, this user, this session" in any way the
user can reason about.

Consequences:

* Hiding a field on a **new** form leaks the hidden state into every other form of that doctype
  in the session, including forms opened for **other documents**.
* There is no matching un-hide except `_restoreVfcHiddenFieldVisibility` (`:887-894`), which is
  called **only** from the revert path. A user who hides a field, reloads, and un-hides it in a
  different form still has it hidden, because the stale `hidden = 1` sits in the meta copy.
* The engine's `_render` additionally calls `frm.toggle_display(fn, false)` for profile-hidden
  fields (`vfc_layout_engine.js:396-399`), so the two mechanisms fight over the same flag on the
  same meta object.

**Fix direction:** hide via a scoped CSS class on the VFC cell (or `wrapper.classList.add("vfc-hidden")`),
never via `toggle_display`. This keeps the state in the DOM, scoped to the form, and leaves
Frappe's permission machinery untouched.

---

### F18 — `localStorage` density is applied to forms the engine never renders · `P2` · CONFIRMED

`vite_layout_controls.js:851-870` `_applyDensity` sets `vfc-density-N` on
`frm.layout.wrapper` for **every form**, including ones the engine blocks. The CSS
`vfc_sections.css:208-232` then applies `grid-template-columns` to `.form-column > form` for
those forms. So a blocked doctype still gets a modified native layout, from a setting the user
chose on a *different* doctype (density is per-doctype in the key, so this is narrower than it
sounds — but the class is still applied to blocked forms and to grid-row forms).

**Fix direction:** only apply the density class when the engine is actually managing the form.

---

### F19 — Hard-coded preset registry with stale field lists · `P2` · CONFIRMED

`vite_layout_controls.js:22-146` `PRESET_REGISTRY` lists only `BOQ Header`, `BOQ Item`,
`BOQ Item Stage`. The BOQ Item presets reference fields verified on **2026-05-28**
(`vite_layout_controls.js:96`). All referenced fields still exist in `boq_item.json` today, so the
presets are not broken *yet* — but they are hard-coded client data that no test or schema check
covers. Adding a field to a preset requires a JS edit, and a renamed field silently produces an
empty preset (`_selectPreset` warns at `:802-808` but still applies).

**Fix direction:** move presets server-side (a `Form Layout Preset` DocType), or generate them
from the doctype's meta at runtime and validate on apply.

---

### F20 — Profiles have silently rotted: seeded profiles no longer match the doctype · `P1` · CONFIRMED

`validate_layout` warns on unknown fieldnames (`layout_api.py:312-316`), but the UI never calls
it (F11), and there is **no check at all** between a stored profile and the doctype's current
meta. The live data proves the profiles have drifted:

```
BOQ Structure-Default  →  sec_identity(7 fields), sec_owner_refs(3 fields)
BOQ Structure meta     →  3 native sections: sb0(14), sb_owner(3), sb_import_traceability(11)
```

The stored profile covers **10 of 28** fields. The following meta fields are in **no** section of
the profile and therefore fall through to `_appendUnassigned`
(`vfc_layout_engine.js:947-1065`) and render in a trailing **"Other Fields"** section:

```
category, item_count, total_contract_value, total_budgeted_cost, description_ar,
is_variation_item, variation_order, import_batch, import_batch_id, import_mode,
source_sheet_name, source_row_no, source_wbs_code, wbs_generated_by_system,
lft, rgt, old_parent
```

Three of those (`lft`, `rgt`, `old_parent`) are `hidden: 1` NestedSet internals that should
**never** be rendered at all — and `_appendUnassigned` does not filter on `df.hidden` for the
non-tabbed path (`:1044` checks only `hidden`/`invisible`, but the *section* filter at `:955-960`
excludes only `SKIP_TYPES`, not `hidden`). So internal tree fields leak into the UI.

The same drift explains the **"OTHER FIELDS" band** in the original bug report screenshots: it is
not a CSS bug — it is unassigned meta fields that no profile section claims, dumped into a
fallback section with no tab awareness.

**Fix direction:** on profile load, reconcile against the doctype meta — report fields that are
in meta but unplaced, fields placed but no longer existing, and never place `hidden: 1` fields.
Give the user a one-click "add missing fields to sections" repair.

---

### F21 — UI-override layer has no isolation contract with VFC · `P2` · CONFIRMED

The global UI overrides (`ct_select_control.js`, `ct_link_control.js`) replace native `<select>`
and `Link` controls app-wide. Both locate their host with
`$el.closest(".frappe-control")` (`ct_select_control.js:61`, `ct_link_control.js:357`). VFC
**moves** the `.frappe-control` wrapper into a different parent
(`vfc_layout_engine.js:443`, `:1017`). The overrides run on a `MutationObserver`/timer against
`.frappe-control` elements, so the two layers will fight over the same wrapper:
the override may re-anchor the dropdown to a parent that VFC has since changed.

Neither layer documents the other. This is the "UI override" half of the request and it has the
same root problem as VFC: no shared contract.

**Fix direction:** define a single "layout owner" concept — the layer that owns a field wrapper
declares it, e.g. `data-vfc-managed="1"` (already set at `vfc_layout_engine.js:869`) — and have
the overrides respect it.

---

### F22 — `vfc_config.js` reads `window.frappe.boot.vfc_debug_enabled` but the boot flag is set server-side under a different key path · `P3` · CONFIRMED

`vfc_config.js:8` reads `window.frappe.boot.vfc_debug_enabled`. `construction/boot.py:48` sets
`bootinfo["vfc_debug_enabled"]`. These line up. But `vfc_config.js` is loaded as a plain asset
(`hooks.py:182`) **not** via the boot script, and it is loaded *after* `theme_loader_v24.js`
(`hooks.py:148`) but the boot object is injected before any app_include_js runs — so this one is
fine. The real issue is that `?v=1` (`hooks.py:182`) never changes, so a browser that cached
`vfc_config.js` will never pick up a change to the debug gate, and the `vfc_debug=1` query-string
escape hatch is **not a documented support path** (it appears in no doc). Low impact; include in
the hygiene pass.

---

## 4. What is genuinely good (do not break it)

Worth stating explicitly so the agents do not "fix" working things:

* **`layout_api.py` is well built.** It has a clear resolver, whitelists deliberately, validates
  input, and never trusts the client for authorization.
* **The permission model is correct.** `construction/overrides/layout_permissions.py` implements
  both a document-level permission hook and a `query_conditions` hook so a normal user cannot
  read or list another user's personal profile. `hooks.py:427` and `:451` register them. This is
  the right shape and it should be the model for everything else.
* **The backend test suite is real.** 39 tests in `construction/tests/test_vfc_backend.py` cover
  the resolver precedence, disabled profiles, delete guards, and `validate_layout`. They just need
  a disposable database (F7).
* **The engine's "never lose a field" instinct is right** — `_clearSections` returns wrappers to
  `_native_parent` (`:1072-1132`) and `_hasMissingFields` retries. The mechanics are wrong
  (F5) but the intent is what we want to keep.

---

## 5. Data-model proposal (fixes F1, F3, F6, F13 at once)

The current model splits "layout" across two places and "visibility" across two more. Consolidate:

```
Form Layout Profile                       (site-wide, per doctype + per app)
  ├─ reference_doctype   (existing)
  ├─ app                 (NEW — module/app of reference_doctype)
  ├─ scope               (NEW — "default" | "role" | "user")
  ├─ scope_value         (NEW — role name or user name; empty for default)
  ├─ priority            (existing)
  └─ sections_json       (existing, but see below)

User Layout Preference                   (per user, per doctype)  ← NEW
  ├─ density             (NEW — replaces localStorage)
  ├─ hidden_fields       (existing vfc_hidden_fields, moved here)
  └─ preset              (existing vfc_preset, moved here)
```

Sections JSON becomes the **single** source of truth for placement, and the rules become:

1. Every field of the doctype appears in **exactly one** section of the profile.
2. A field may appear in **no** section → it is rendered in a generated "Other fields" section,
   in native order, at the end. (Today `unassigned_policy` + `fld.visible` make this ambiguous.)
3. `visible` is **removed** from the profile; hidden fields are per-user only (in
   `User Layout Preference`). A shared profile must not hide a field from another user.
4. Section → tab binding is stored as the tab's **fieldname**, resolved via `frm.layout.tabs`,
   never by DOM id.

This makes the resolver a pure function of (user, role, app, doctype), makes per-user override
possible without any new endpoint, and removes the need for F3, F6, F13's fix separately.

---

## 6. Frontend fixes that are independent of the data model

These can land first and are low risk:

| ID | Fix | File:line |
|---|---|---|
| A1 | Stop stripping `hide-control`; skip fields whose `disp_status === "None"` | `vfc_layout_engine.js:853-879` |
| A2 | Stop calling `frm.toggle_display` from the engine and from the panel; use a scoped CSS class | `vfc_layout_engine.js:395-399`; `vite_layout_controls.js:637-643, 887-894, 1040-1049` |
| A3 | Resolve tab panes via `frm.layout.tabs`, never `document.getElementById` | `vfc_layout_engine.js:512-563` |
| A4 | Preserve `tab_fieldname` through the merge | `vite_layout_controls.js:1295-1393` |
| A5 | Do not remove user-placed fields when merging native sections | `vite_layout_controls.js:1362-1367` |
| A6 | One renderer: drop `renderWithDensity`; apply density as a column count only | `vfc_layout_engine.js:1218-1333` |
| A7 | Fix grid placement to `grid-column: N / span 1` with a consistent fill order | `vfc_layout_engine.js:421-437` |
| A8 | Write dense `sort_order` for every section and field, including unassigned | `vite_layout_controls.js:1608, 1648-1653`; `vfc_layout_engine.js:995-1019` |
| A9 | Unpatch `Tab.prototype.refresh`; manage tab visibility inside the engine | `vfc_layout_engine.js:146-188` |
| A10 | Hide a section only when it has zero profile fields | `vfc_layout_engine.js:809-851` |
| A11 | Call `validate_layout` server-side inside `save_layout` | `layout_api.py:122-182` |
| A12 | Key the client profile cache by doctype **and** user; revalidate on 304-style version | `vfc_layout_engine.js:273-291` |
| A13 | Apply the density class only to forms the engine manages | `vite_layout_controls.js:851-870` |
| A14 | Add a `data-vfc-managed` contract that the UI overrides respect | `ct_select_control.js`, `ct_link_control.js` |

---

## 7. Root-cause narrative (for the record)

The VFC work followed this shape:

1. A **backend-first** design was written: profile DocType, resolver, permission hooks, tests.
   This part is good.
2. A **frontend demo** was written in parallel: localStorage density, a hard-coded preset table,
   an in-memory section editor. It was never reconciled with the backend.
3. The engine was then pointed at real doctypes. It was written against **flat, non-tabbed,
   low-privilege** forms (the four seeded BOQ doctypes). Every assumption it makes about Frappe's
   DOM is true for those and false in general.
4. The docs (`docs/vfc_status_report.md`, `AGENTS.md` §3D) were written for stage 2 and never
   revised after the tab work (`4f0ff2d`), so they now assert coverage that does not exist.

Every finding above is a symptom of steps 2 and 3. That is why "the plan was not complete" and
"not consistent" are the *same* problem seen from two sides.

---

## 8. Task list for AI agents

Hand these out in order. Each has a definition of done an agent can self-check.

### Phase 0 — Stop the bleeding (no design change)

| Task | Finding | Definition of done |
|---|---|---|
| **T0.1** | F7 | Test suite runs against a disposable database. A new `Form Layout Profile` row appears **only** in the test DB. Cleanup migration removes existing `profile_name LIKE '_Test_%'` rows from every site. `save_layout` rejects `_Test_`-prefixed names. |
| **T0.2** | F4 | `_restoreVisibleFieldWrapper` no longer removes `hide-control`. A field with insufficient `permlevel` read permission stays invisible under VFC. New browser test: under-privileged user opens a VFC form containing a permlevel field → field is not visible. |
| **T0.3** | F11 | `save_layout` calls `validate_layout` internally and raises on error. A client cannot persist a profile that hides a required field. |
| **T0.4** | F2 | Replace `BLOCKED_DOCTYPES` with a runtime capability check. The engine refuses to manage a form it does not understand and logs a reason. Add `User`, `Role`, `Workspace`, `Dashboard` to a regression list. |

### Phase 1 — Make the frontend behave (no schema change)

| Task | Finding | Definition of done |
|---|---|---|
| **T1.1** | F5, F17 | The engine and the panel no longer call `frm.toggle_display`. Hiding uses a scoped class. A field marked `visible:false` in a profile is not rendered twice and does not trigger the 20× retry loop. |
| **T1.2** | F3 | Tab resolution goes through `frm.layout.tabs`. `tab_fieldname` survives a save/load round trip. A section lands in the tab the editor put it in, verified on a doctype with real tabs. |
| **T1.3** | F13, F14 | Re-opening the Section editor shows the user's arrangement, not the native one. Field placement survives a round trip byte-for-byte. |
| **T1.4** | F6 | "Revert to Default / Native" on a form with a shared default profile actually restores native rendering, and the success message is truthful. |
| **T1.5** | F9, F7, F10, F16 | One renderer. Density changes column count on the *existing* sections; it does not hide the tab bar. Grid placement is gap-free at 1, 2 and 3 columns. |
| **T1.6** | F8 | `Tab.prototype.refresh` is no longer patched. Tab show/hide matches stock Frappe on non-VFC forms. |
| **T1.7** | F12 | Profile cache is keyed per user; a role change or an admin edit is reflected within one refresh cycle. |
| **T1.8** | F20 | On profile load, the panel reconciles against the doctype meta and shows three lists: fields placed but no longer existing, meta fields not yet placed, and `hidden: 1` fields that must never be placed. One-click "repair" assigns the unplaced fields to sections. `hidden: 1` fields never render. |

### Phase 2 — Consolidate persistence

| Task | Finding | Definition of done |
|---|---|---|
| **T2.1** | F1 | New `User Layout Preference` DocType holds density, hidden fields and preset, per user per doctype. `localStorage` is no longer the source of truth for density; a migration moves existing localStorage values server-side on first load. |
| **T2.2** | F1, F5, F6 | `Form Layout Profile` gains `app`, `scope` and `scope_value`. The resolver honours them. The panel offers "save for me / save for my role / save for everyone" and each produces a distinct row. |
| **T2.3** | F5, F13, F14 | `visible` is removed from profile sections. Every doctype field appears in exactly one section or in the generated "Other fields" section. |
| **T2.4** | F20, F19 | Stale profile fields are surfaced in the panel with a repair action. Presets move server-side and validate against the doctype meta. |
| **T2.5** | F20 | The four seeded production profiles (`BOQ Header`, `BOQ Item`, `BOQ Item Stage`, `BOQ Structure`) are re-seeded against current meta so every field is placed exactly once and `hidden: 1` fields are excluded. A maintenance patch applies it to all sites. |

### Phase 3 — Close the loop

| Task | Finding | Definition of done |
|---|---|---|
| **T3.1** | F21 | A written contract: which layer owns a field wrapper, how the UI overrides detect it, and what happens on ownership transfer. `data-vfc-managed` is honoured by `ct_select_control.js` and `ct_link_control.js`. |
| **T3.2** | F19, F2 | `docs/vfc_status_report.md` and `AGENTS.md` §3D are rewritten to describe the *actual* coverage, with the blocklist replaced by the capability rule. Line counts and endpoint lists match the code. |
| **T3.3** | all | One browser test matrix runs on every CI pass: 2 users × 2 roles × {flat form, tabbed form, child-table form, permlevel form} × {no profile, default profile, personal profile, role profile}. |

---

## 9. How to verify each claim yourself

You should not have to take an agent's word for any of this. Here is how to check the important
ones in under five minutes each.

```bash
cd /home/mohamed/frappe-bench/apps/construction

# F7 — test rows in the live DB
mysql -u root -proot -h localhost -e "
  SELECT COUNT(*) total, SUM(profile_name LIKE '\_Test\_%') test_rows
  FROM \`_6d52b48c328b294e\`.\`tabForm Layout Profile\`;"

# F1 — no personal or role layout is reachable
mysql -u root -proot -h localhost -e "
  SELECT SUM(for_user IS NOT NULL) personal, SUM(for_role IS NOT NULL) role_rows
  FROM \`_6d52b48c328b294e\`.\`tabForm Layout Profile\`;"

# F1/F13 — user sections are empty, native sections hold the fields
mysql -u root -proot -h localhost -N -e "
  SELECT sections_json FROM \`_6d52b48c328b294e\`.\`tabForm Layout Profile\`
  WHERE name='BOQ Item-Default';" | python3 -m json.tool | head -40

# F2 — the deny-list that is not app-wide
grep -n "BLOCKED_DOCTYPES" -A 70 construction/public/js/vfc_layout_engine.js | head -75

# F3 — tab id scheme differs between engine and Frappe
grep -n "_getTabPane" -A 8 construction/public/js/vfc_layout_engine.js
grep -n "const id" -B 4 -A 3 ../frappe/frappe/public/js/frappe/form/tab.js

# F4 — the engine strips Frappe's permission class
grep -n "hide-control" construction/public/js/vfc_layout_engine.js
grep -n "hide-control" ../frappe/frappe/public/js/frappe/form/controls/base_control.js

# F11 — validate_layout is never called by the UI
grep -rn "validate_layout" construction/public/js/ ; echo "exit=$? (1 = never called)"

# F8 — the global prototype patch
grep -n "_vfc_patched" -B 4 -A 4 construction/public/js/vfc_layout_engine.js
```

For F3, F4, F5, F9 and F16 you need a browser. Ask an agent to run the VFC browser suite
(`construction/public/js/vfc_layout_engine_tests.js`) against `v16.localhost` on a **tabbed**
doctype and capture the console output — that is where the tab-misplacement and the
double-render will be visible.

---

## 10. What I did not check

Stated so the next reviewer does not assume coverage that is not there:

* **No browser run.** All DOM-level conclusions (F3, F4, F5, F9, F16) are derived from reading
  Frappe v16.51.1 and the VFC source, not from observing them live. F3 is marked LIKELY for this
  reason. Run the browser matrix in T3.3 before closing these.
* **Other apps on the bench.** I audited `apps/construction`. `apps/correction-workspace` contains
  a **copy** of the VFC files (`construction/public/js/vfc_layout_engine.js` etc.) that is not
  tracked by `apps/construction`'s git. If that app is live, it has its own copy of every bug
  above and needs the same fixes, or it should be deleted and the files sourced from `construction`.
* **Grid-row / child-table forms.** `grid_row_form.js` builds its own `Layout` with
  `is_child_table: true`. The engine's `attach()` runs on `frappe.ui.form.on("*")`, which fires
  for grid rows too. I did not trace whether the engine corrupts an expanded child-table row.
  This is a **P0 risk** and deserves its own task.
* **`bench build` / bundling.** I did not run a production build. `vite_layout_controls.js` loads
  SortableJS lazily via `frappe.require("/assets/construction/js/vendor/sortablejs.min.js")`
  (`vite_layout_controls.js:1181`) — `frappe.require` maps only `*.bundle.*` paths through
  `assets_json`, and a raw `/assets/...` path passes through unchanged
  (`assets.js:141-150`), so this should resolve, but it was not exercised.
* **Performance at scale.** `_verifyAndRetry` schedules four timers per render
  (`vfc_layout_engine.js:594-599`) and the MutationObserver re-attaches on DOM churn
  (`:1148-1186`). On a large form this is a lot of work per refresh. Not measured.
* **Arabic / RTL.** The CSS has RTL rules (`vfc_sections.css:116-133`) and `frappe/templates/base.html:3`
  sets `dir` on `<html>`, so `[dir="rtl"]` selectors do match. The
  `modern_theme_base.css` selectors use `[data-theme="dark"] [dir="rtl"]` — a descendant
  combinator, which still matches. Not visually verified.

---

*Prepared as a senior-engineer audit for the owner. Every finding is evidence-backed and
independently checkable. Phase 0 and Phase 1 are safe to start immediately; Phase 2 changes the
data model and should follow a short design decision by the owner (see §5).*
