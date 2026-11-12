# P0-2 Fix Verification — `hide-control` is never stripped

| | |
|---|---|
| **Work item** | `vfc-gate-off-and-p0-fixes` |
| **Phase** | 1 — fix |
| **Executed** | 2026-11-12 |
| **Site** | `v16.localhost` |
| **Document** | `PROJ-0002` |
| **Actor** | `vfc.p02.test@example.com` (role `Projects User`, non-admin) |
| **Verdict** | **PASS — fix confirmed by A/B against the pre-fix baseline** |

---

## 1. The change

`construction/public/js/vfc_layout_engine.js` — `_restoreVisibleFieldWrapper`

**Before:**

```js
if (fieldObj?.df?.hidden_due_to_dependency || fieldObj?.df?.hidden) {
    return;
}
nativeEl.classList.remove("hide-control", "hidden", "d-none");   // <-- defect
...
    .forEach((el) => {
        el.classList.remove("hide-control", "hidden", "d-none"); // <-- defect
```

**After:**

```js
if (fieldObj?.df?.hidden_due_to_dependency || fieldObj?.df?.hidden) {
    return;
}
// ... explanation of why the class is not ours to remove ...
if (nativeEl.classList.contains("hide-control")) {
    nativeEl.setAttribute("data-vfc-managed", "1");
    return;                       // leave the control exactly as Frappe left it
}
nativeEl.classList.remove("hidden", "d-none");
...
    .forEach((el) => {
        if (el.classList.contains("hide-control")) return;
        el.classList.remove("hidden", "d-none");
```

**Scope check — no other stripping site exists:**

```
$ grep -rn 'classList.remove([^)]*hide' construction/ --include=*.js
(no matches)

$ grep -rn "hide-control" construction/
vfc_sections.css:208-209   :not(.hide-control)          read-only selector
vfc_layout_engine.js:168   :not(.hide-control)          read-only selector
vfc_layout_engine.js:177   :not(.hide-control, ...)     read-only selector
vfc_layout_engine.js:794   classList.contains(...)      read-only counter
vfc_layout_engine.js:830   classList.contains(...)      read-only counter
vfc_layout_engine.js:870   classList.contains(...)      NEW guard
vfc_layout_engine.js:891   classList.contains(...)      NEW guard
```

All remaining references **read** the class; none remove it.

### Cache busters bumped (AGENTS.md convention 4, Standard §13)

| File | Before | After |
|---|---|---|
| `vfc_layout_engine.js` | `?v=1.44` | **`?v=1.45`** |
| `vite_layout_controls.js` | `?v=1.25` | **`?v=1.26`** |

---

## 2. Test conditions

To make the defect observable the `hide_empty_read_only_fields` setting had to be
**on** (it is `0` on this site; the DocType JSON default is `"1"`). It was enabled
the way Frappe itself propagates it — `frappe.db.set_default()`, which writes
`tabDefaultValue`, because `boot.py:49` builds `sysdefaults` from there and a raw
`db.set_value` on the Singles row never reaches the client.

Confirmed in-page before measuring:

```
is_enabled("hide_empty_read_only_fields") : true
engine asset  : vfc_layout_engine.js?v=1.45     <-- new code
controls asset: vite_layout_controls.js?v=1.26  <-- new code
vfc_managed_count : 32                          <-- VFC still active
```

---

## 3. Results

### Headline

| Metric | Pre-fix (VFC ON) | **Post-fix (VFC ON)** | VFC OFF (control) |
|---|---:|---:|---:|
| `hide-control` count | 18 | **22** | 22 |
| `vfc_managed` count | 32 | 32 | 0 |
| **managed WITH `hide-control`** | **0** | **4** | n/a |

**Post-fix matches the VFC-OFF control arm exactly** (22). That is the objective:
VFC must not change what Frappe decided.

### Fields that were being wrongly revealed — now correctly hidden

| field | Pre-fix | **Post-fix** | VFC OFF (control) |
|---|---|---|---|
| `actual_start_date` | `hide-control: false`, block, h=23 | **`true`, none, h=0** | `true`, none, h=0 |
| `actual_end_date` | `hide-control: false`, block, h=23 | **`true`, none, h=0** | `true`, none, h=0 |
| `project_template` | `false`, visible | **`true`, none, h=0** | — |
| `users` (permlevel-1 Table) | `false`, visible | **`true`, none, h=0** | — |

All four are `vfc_managed: "1"` — i.e. **the engine still manages them**; it simply
no longer overrides the platform's decision to hide them.

### Negative controls — must stay visible, and do

| field | why it must stay visible | Pre-fix | **Post-fix** |
|---|---|---|---|
| `expected_start_date` | writable → `status === "Write"`; hide-empty requires `"Read"` | visible | **visible** (block, h=56) |
| `total_costing_amount` | read-only but value `0`; `is_null(0)` is **false** | visible | **visible** |
| `gross_margin` | value `0` | visible | **visible** |
| `actual_time` | value `0` | visible | **visible** |

These prove the fix **preserves Frappe's rule** rather than blanket-hiding
read-only fields. If the fix over-reached, all four would have disappeared.

---

## 4. Why this also closes the original permlevel concern

`Project.users` is the permlevel-1 `Table` that started this finding. Under the
fix it now retains `hide-control` and renders `display:none`, `vfc_managed="1"`.

On this site it is hidden via the **hide-empty** path rather than the permlevel
path (the acting user holds `Desk User`, which ERPNext core grants permlevel-1
read on Project — see `AC1_AC2_PROJECT_BROWSER_TEST.md` §2). Either way the
outcome is the same: **the engine no longer reveals a control the platform hid.**

---

## 5. Regression coverage

| Check | Result |
|---|---|
| `node --check vfc_layout_engine.js` | **PASS** |
| `node --check vite_layout_controls.js` | **PASS** |
| A/B browser test, pre vs post fix | **PASS** (§3) |
| Negative controls unchanged | **PASS** (§3) |
| No remaining stripping site in app | **PASS** (§1) |
| Cache busters bumped + verified loaded | **PASS** (§2) |

---

*P0-2 complete. Environment restored after measurement (setting back to `0`,
throwaway user deleted) — see `PHASE1_IMPLEMENTATION.md`.*
