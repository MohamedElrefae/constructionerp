# P1-1 + P0-3 Verification — revert to native, and section-editor data loss

| | |
|---|---|
| **Work item** | `vfc-gate-off-and-p0-fixes` |
| **Phase** | 1 — fixes |
| **Executed** | 2026-11-12 |
| **Verdict** | **P1-1 PASS (with two plan corrections) · P0-3 PASS** |

---

## 1. P1-1 — root cause, proven

`save_layout` is `_require_system_manager()`, and the DocType controller's
`before_insert()` threw for any non-System-Manager. Meanwhile:

| component | intended audience |
|---|---|
| resolver **Step 1** (`layout_api.py:80-83`) | personal `for_user` profile |
| `delete_my_personal_layout` (`layout_api.py:224`) | explicitly **non-admin** |

So the two halves of "personal layout" existed, but **nothing non-admin could
ever create the row they act on**. Confirmed live:

```
DocPerm Form Layout Profile:  System Manager create=1  ·  All create=0
personal profiles (for_user set) site-wide: 0
```

That is why revert answered `not_found` while the UI still showed green.

---

## 2. Two corrections to the approved plan

### Correction A — "empty sections gives revert for free" is false as written

The plan asserted an empty-sections `__native__` profile would render natively
with no schema change. Tracing `_render`:

```js
this._clearSections(frm);            // 301
layoutRoot.classList.add("vfc-active");
...
this._hideNativeLayoutShells(layoutRoot);   // 343  ← BEFORE the loop
...
sections.forEach((sec) => { ... });         // 358  ← zero iterations if empty
```

`_hideNativeLayoutShells` sets `display:none !important` + `data-vfc-hidden`
on **every** native section shell (line 593). With no sections to build, the
form would be left **blank**.

**Fix:** in `attach`, treat an empty-sections profile exactly like no profile —
run the density fallback, call `_clearSections`, and return before `_render`.

### Correction B — `_clearSections` never un-hid native shells

Its doc comment has always said *"Also un-hide any native Frappe section
elements we hid."* It did not. `grep` for `data-vfc-hidden` found only
**set** (593, 1276) and **read** (739) sites — no removal anywhere.

This was dormant only because revert used to be a no-op, so the
"VFC-rendered → native" transition never happened. My sentinel exposed it.

**Measured before the fix (sentinel active):**

| Check | Before | After |
|---|---:|---:|
| shells with `data-vfc-hidden` | **42** | **0** |
| shells `display:none` | **42 / 42** | **0** |
| `.form-section` `display:none` | **11 / 11** | **3** (all `empty-section`, CSS-hidden by Frappe, no VFC marker) |
| VFC cells / sections | 0 / 0 | 0 / 0 |
| `leftover_vfc_markers` | 42 | **0** |

**Fix:** `_clearSections` now removes the inline `display` and the
`data-vfc-hidden` attribute from every element it previously hid.

---

## 3. What was built

### Narrow endpoint — `layout_api.save_my_native_layout(doctype)`

| Constraint | How |
|---|---|
| cannot target another user | signature is **`doctype` only** — asserted by test |
| payload cannot be shaped by caller | fixed sentinel `{"version":1, …, "sections":[]}` |
| doctype restricted | must exist in `DocType` **and** caller must hold `read` |
| Guest rejected | explicit check |
| unique per user | `profile_name = "__native__:{user}"` — required because `autoname = format:{reference_doctype}-{profile_name}`; a bare `__native__` would collide on the PK for a second user |
| wins resolution | `priority=1000` (Step 1 returns first personal match in priority-desc order) |

`save_layout` and `_require_system_manager()` were **left untouched**, as ruled.

### Controller guard reconciled (permission change — flag for review)

`before_insert` previously blocked *all* non-System-Manager creation, which made
the personal-profile design unreachable. It now exempts a row **only** when all
of these hold:

```
for_user == frappe.session.user  AND  is_default=0  AND  is_system=0  AND  for_role empty
```

Shared profiles remain System Manager only. **Four negative-control tests**
assert the guard still rejects default, role-targeted, system-flagged, and
other-user profiles from an ordinary account.

### Revert button

Now calls `save_my_native_layout` instead of `delete_my_personal_layout`, and
the alert is **conditional** — green only when the server confirms
`created`/`updated`, orange otherwise. The unconditional green "reset" was the
visible half of the false success.

---

## 4. P0-3 — section editor data loss

Tested directly in-browser against `window._VFC`, using a synthetic `frm`
(`_buildNativeSectionsProfile` reads only `frm.meta.fields`).

Scenario: user places `project_name` in their own `sec_custom`; natively that
field belongs to `sb1`. The old algorithm strips it out of `sec_custom`.

| | `project_name` in user's `sec_custom` | in native `sb1` |
|---|---|---|
| **new code** | **`true`** ✓ | `false` |
| **old algorithm (reimplemented)** | `false` | **`true`** ← reproduces the defect |

The old-algorithm arm proves the test **would have failed pre-fix** — it is not
a test that passes either way.

---

## 5. Test & check results

| Check | Result |
|---|---|
| `bench … run-tests --module construction.tests.test_vfc_backend` | **51 / 51 OK**, exit 0 (39 existing + **12 new**) |
| `node --check` × 3 JS | **PASS** |
| `py_compile` × 4 Python | **PASS** |
| `schema_drift_checker.py` | **PASS exit 0** |
| `ai_context_check.py` | **PASS 11/11** |
| `lint_scope_metadata.py` | **PASS exit 0** |

New tests: signature-is-doctype-only · creates-for-caller-only · fixed empty
payload · idempotent · **sentinel displaces default in the resolver** · rejects
unknown doctype · rejects unreadable doctype (with live precondition assert) ·
rejects Guest · **4 guard negative controls**.

---

## 6. Environment restored

| Item | Final state |
|---|---|
| `enable_form_config` | **0** (shipped default) |
| profiles total | **8** |
| personal profiles | **0** |
| `_Test_` rows | **0** |
| test users (`vfc.%`) | **0** |
| `schema_drift` / `ai_context` / `lint_scope` | **0 / 11-of-11 / 0** |

Cache busters now: `vfc_layout_engine.js?v=1.48`, `vite_layout_controls.js?v=1.28`,
`vfc_config.js?v=2`.

**Nothing committed.**
