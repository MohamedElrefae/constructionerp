# VFC — Keep / Fix / Retire decision analysis

**Companion to:** `docs/ai/VFC_AND_UI_OVERRIDE_AUDIT_2026-11-11.md`
**Date:** 2026-11-11
**Question posed by owner:** *Modify the frontend, discard the feature, or make it optional per user?
ERPNext/Frappe UI updates make this feature expensive to maintain.*

---

## 1. Recommendation (read this first)

**Do all three, in a specific order. The three options are not mutually exclusive.**

| | Decision |
|---|---|
| **1. Ship the P0 fixes now** | Mandatory and non-negotiable. Three of them are **live defects affecting real users today**, independent of the feature's future. |
| **2. Make the feature opt-in per user, immediately** | This is the answer to the maintenance-cost worry. It converts an app-wide liability into a per-user preference. Cheap to build; removes the upgrade-risk pressure. |
| **3. Freeze the frontend at "stable subset"** | Stop extending it. Do **not** "fix" the section editor or the tab support. Retire those two subsystems. |
| **4. Keep the backend** | It is clean, permission-guarded and tested. It is also the thing that makes step 2 possible. Do not delete it. |

**The one-line version:** *Gate it off by default, fix the three live bugs, keep the backend,
stop growing the frontend.* The feature stops being a liability the next time Frappe changes its
DOM — which it will, and has.

**What I am explicitly NOT recommending:** "rewrite the frontend properly" and "delete the whole
feature including the theme work." Both are worse than what is proposed here, for reasons in §6.

---

## 2. The decisive facts

These four facts determine the answer. All are verified against the live site and the source.

### Fact 1 — The blast radius is currently the entire app; the actual usage is 8 doctypes

```
492  non-child doctypes exist on the site
  8  have a real Form Layout Profile
202  of the 210 profile rows are leftover `_Test_*` garbage
  0  profiles are per-user or per-role
```

The engine and the panel attach via `frappe.ui.form.on("*")`
(`vite_layout_controls.js:1931`, `vfc_layout_engine.js:1415`) — **every form, no exceptions**.
There is **no site setting, no feature flag, and no per-doctype opt-out anywhere** in the codebase
(verified: `grep` for `enable_vfc` / `vfc_enabled` / `allow_vfc` returns nothing but the
unrelated debug flag).

So today: **492 forms carry a "Form Config" button and run the engine**, to serve **8 doctypes**
that are mostly construction's own (BOQ Header, BOQ Item, BOQ Item Stage, BOQ Structure,
User Scope Context, Variation Order) plus two ERPNext-core ones (Budget, Project).

That ratio — 492 exposed, 8 used — is the whole argument. The exposure is 60× the usage.

### Fact 2 — The real user engagement is near zero

The `__UserSettings` rows that carry VFC keys:

```
vfc_hidden_fields = []            → 2 rows   (nobody hid anything)
vfc_hidden_fields = ["description"] → 1 row  (one user, one field, one doctype)
vfc_preset = "Default"            → 2 rows   (the default value)
vfc_native_collapsed_sections     → 1 row   (DEAD KEY — see Fact 3)
```

Across the entire site, **one user hid one field on one doctype.** Nobody has used the section
editor, the presets, or the density control in a way that persisted to the server.

`vfc_native_collapsed_sections` is written by an **older code path that no longer exists** — it is
in the database but **no current JS reads it** (verified with `git log -S`). It is orphaned state
from a feature that was already removed once.

### Fact 3 — The feature has already been abandoned and restarted once

The git history of the two frontend files shows a clear arc:

```
6800d33  feat: Stage 2 - expand VFC layout engine to entire ERPNext app   ← the "whole app" push
4f0ff2d  feat: enable VFC Layout Engine on tabbed forms ...              ← tab support bolted on
7aadbdd  feat: VFC Phase 3 stabilization - WP0-WP5                     ← stabilization after that
698ea94  feat: VFC full reset - density, hidden fields, preset, and layout
```

The "entire ERPNext app" claim was made, and **it did not hold** — which is exactly the symptom
being reported now. The tab work was added afterwards and destabilized it again. This pattern is
the strongest available evidence about what happens next time Frappe changes its form DOM: the
feature gets patched again, and the maintenance cost is paid again.

### Fact 4 — The maintenance coupling is to *Frappe internals*, not to your app

This is the crux of the owner's concern, and it is **correct**.

VFC does not re-render forms. It **physically moves Frappe's own DOM nodes** — the `.frappe-control`
wrappers that Frappe created — out of Frappe's `.form-section` / `.section-body` / `.form-column`
containers and into VFC's own `.vfc-le-cell` grid. It then patches `Tab.prototype.refresh`
(`vfc_layout_engine.js:146-188`) on a **Frappe vendor class**, permanently, for the session.

Every one of these is an undocumented internal:

```
.form-layout  .form-section  .section-head  .section-body  .form-column
.frappe-column  .frappe-control  .tab-pane  .tab-content  .form-dashboard-section
```

**None of these are public API.** Frappe gives no stability guarantee on them. The moment Frappe
renames a class, changes the section DOM, or changes how tabs are built, VFC silently mis-renders
forms — for every user, on every doctype, with no error.

**The contrast that proves the point:** the **theme/UI-override layer is low-risk** because it is
CSS-only (`vite_form_override.css` — 126 selectors against Frappe classes, **zero** references to
`frappe.ui.*` / `frappe.model.*` internals). CSS that targets a class name degrades gracefully —
if the class disappears, the rule stops matching and nothing breaks. **JS that re-parents Frappe's
nodes does not degrade gracefully** — if the DOM changes, fields land in the wrong place or vanish.

So the owner's instinct is right, and it applies to **VFC's DOM-surgery specifically**, not to the
theme work.

---

## 3. The three options, honestly assessed

### Option A — "Modify the frontend" (fix everything properly)

| | |
|---|---|
| **Cost** | Highest. Realistically 3–6 weeks of careful work: tab resolution, permission-safe visibility, the section editor's data-loss bug (F13), the merge semantics, the grid math, the persistence consolidation (§5 of the audit). Then it must be re-done every time Frappe changes its DOM. |
| **Risk** | Highest. Every change touches the exact code that moves fields — the same code path where the P0 permission bug (F4) and the field-double-render (F5) live. You would be re-fixing the same fragile code. |
| **Benefit** | A genuinely better feature. But see Fact 2: **one user hid one field**. The benefit is currently ~0. |
| **Verdict** | **Reject for now.** Fix the P0s, but do not attempt a general repair. The value case does not exist yet. |

### Option B — "Discard the feature completely"

| | |
|---|---|
| **Cost** | Low technically (delete 3 files, 5 patches, 1 DocType). But see below. |
| **Risk** | Medium, and mostly **not** technical. |
| **Benefit** | Zero maintenance cost. |
| **Verdict** | **Reject as a whole, but accept the parts.** Two specific problems: |

**Problem 1 — the theme/UI-override work is not VFC and would be collateral damage.** The theme
system (`modern_theme.css` 4,798 lines, `modern_theme_base.css` 5,101 lines, the token system, the
dark/light engine, `User Desk Theme` with per-user overrides) is a **separate, valuable, working
feature**. It is CSS-based and therefore low-maintenance (Fact 4). It also delivers "per user"
theming — the exact capability the owner wants — with no DOM surgery. **Do not let a VFC decision
delete the theme system.** They share a name and a folder; they share almost nothing else.

**Problem 2 — deleting the backend throws away the good part.** `layout_api.py` is the cleanest
code in the whole feature: whitelists deliberately, validates input, never trusts the client for
authorization, has a proper 3-tier resolver, and is guarded by `overrides/layout_permissions.py`
(a `has_permission` hook *and* a `query_conditions` hook). It has 39 tests. It is also **what makes
the opt-in path cheap** — the per-user and per-role layers already exist and are just not
reachable from the UI.

**What to actually discard (this is the honest answer):** the **section editor** and the
**tab support** — i.e. audit findings F3, F13, F14, F15, and the whole
`vite_layout_controls.js` sections-tab machinery (~700 lines). Nobody uses it (Fact 2), it is the
part with the data-loss bug (F13), and it is the part that couples hardest to Frappe internals.
That is a genuine simplification, not a cosmetic one.

### Option C — "Make it optional per user"

| | |
|---|---|
| **Cost** | **Lowest.** One site setting + one per-user toggle, both of which the backend already nearly supports. See §4. |
| **Risk** | Low. The blast radius shrinks from "492 forms, all users" to "opt-in users, opt-in doctypes". |
| **Benefit** | **This is the one that directly answers the maintenance worry.** |
| **Verdict** | **Adopt — and do it first, before any other work.** |

Why it answers the worry so directly: **an opt-in feature that a user turns on is a feature that
can break without breaking anyone's site.** If Frappe changes the DOM, the damage is confined to
users who opted in, and the fix can wait for a Frappe upgrade cycle instead of an emergency release.
That is the difference between "we must patch this week" and "we will patch this in the next
maintenance window" — and it is the difference that makes a feature like this sustainable at all.

It also gives you the honest answer to *who wants this*: if after a quarter nobody has turned it
on, you have your evidence to delete it cleanly, having cost nothing.

---

## 4. What "optional per user" concretely means here

Good news: **the backend already has the shape for this. Only the UI wiring is missing.**

### 4.1 Turn it off by default (site-wide)

Add to `Modern Theme Settings` (or a new single doctype):

```
enable_form_config      Check   default 0   ← site owner opts in
vfc_allowed_doctypes     Table   optional              ← empty = all (once enabled)
```

Effect in `vite_layout_controls.js`:
- Skip `_injectButton` entirely → **no "Form Config" button** on any form.
- Skip `LayoutEngine.attach()` → the engine never runs → **zero DOM risk**.

This alone removes 60× of the current blast radius (Fact 1) and makes every future Frappe upgrade
a non-event. **This is the single highest-value change in this document.**

### 4.2 Then a per-user opt-in

Reuse the existing `user_settings` store that the feature already uses — but note the audit's F1:
`user_settings` is keyed by **doctype**, so it is per-user but not per-doctype-scoped in a way that
survives a fresh browser (the value lives in the user's `__UserSettings` row for that doctype, so it
does survive — but it collides with Frappe's own use of the same row).

Add to the panel (only reachable when the site has enabled it):
```
Form Config → toggle "enable on this form"
```

Store as `vfc_enabled` in the same per-doctype `user_settings` row. `frappe.model.user_settings`
is already per-user and per-doctype, and the read path
(`frappe.get_user_settings(doctype)`, `model.js:51-56`) is already wired.

### 4.3 Fix the resolver so it can express "off"

The backend resolver (`layout_api.py:79-93`) is a 3-tier lookup: **personal → role → default**.
It has no "disabled" concept. Add one:

```
Form Layout Profile.enabled = 0   →  already respected by the resolver ✓
```

But a *user-level* "off" needs one more thing: a personal profile that means "native layout, not
my default". The cleanest expression, which needs **no schema change**:

```
for_user = <me>, profile_name = "__native__", enabled = 1, sections_json = {"sections": []}
```

Empty sections ⇒ the engine renders the native layout untouched. The resolver already prefers
`for_user` over everything else, so this works **today** with the existing code. An agent can
implement this in one small function.

### 4.4 What the user experience becomes

```
Site setting "Enable Form Config" = OFF (default)
  → nobody sees the button, nothing renders, zero risk
  → owner flips it on when they want to try it

Per user, per doctype:
  → "Form Config" button appears only where enabled
  → density, hidden fields, presets, layout all scoped to that user
```

---

## 5. The P0 fixes — do these regardless of the decision

These are **live defects**. They affect users today and they are not hypothetical. Whether the
feature is kept, gated, or retired, they must not be left in place.

| # | Audit ref | The live problem | Fix | Effort |
|---|---|---|---|---|
| **P0-1** | F7 | **202 `_Test_*` profile rows are live in the production database** and are returned to real users by the resolver (the resolver filters on `reference_doctype` + `enabled` only). The test suite writes to the live site DB and cleans up only 2 of 202 rows. | Patch to delete `profile_name LIKE '_Test_%'` on every site. Make the test suite run against a disposable DB. Add a guard in `save_layout` refusing `_Test_` names. | S |
| **P0-2** | F4 | **The engine can reveal a field the user is not permitted to read.** `_restoreVisibleFieldWrapper` strips Frappe's `hide-control` class (`vfc_layout_engine.js:853-879`) — but `hide-control` is exactly what Frappe uses to enforce field-level read permission (`base_control.js:141` + `perm.js:232-263`). A `permlevel` field the user cannot read becomes visible. | Stop stripping `hide-control`. Skip fields whose `disp_status === "None"`. Add a browser test: under-privileged user on a VFC form with a `permlevel` field → field stays hidden. | M |
| **P0-3** | F6 | **"Revert to Default / Native" does not revert.** It calls `delete_my_personal_layout`, which looks for a `for_user` profile — and **no personal profile can ever exist**, because the UI never sends `for_user` (`vite_layout_controls.js:944-961`). The button reports success while the shared profile stays active. | With the `__native__` sentinel from §4.3 this becomes correct for free. Until then: fix the success message to say what actually happened, and make revert write a `__native__` personal profile. | S |

**Why P0-2 is the one to worry about most:** it is a *permission* defect, not a cosmetic one. It is
currently unreachable only by luck — the four seeded BOQ doctypes happen to have no `permlevel > 0`
fields. The moment an ERPNext doctype with `permlevel` fields gets a profile (Budget and Project
already have profiles and are ERPNext-core), it becomes live.

---

## 6. Why "rewrite it properly" is the wrong call — the honest argument

The tempting plan is: *the backend is good, so rewrite the frontend properly against the backend
and we get a first-class feature.* Against that:

1. **No demonstrated demand.** Fact 2: one user hid one field in the site's entire history. A
   rewrite serves a need that has not been shown to exist.
2. **The rewrite inherits the same fragility.** Any frontend that re-parents Frappe's DOM nodes is
   coupled to Frappe's DOM. A beautiful rewrite is still coupled. The rewrite changes *when you
   pay*, not *whether you pay*.
3. **Every previous "expand it" push failed.** Fact 3: "entire ERPNext app" → didn't hold; tab
   support → destabilized again; "full reset" → rewrote state handling and left the section editor
   with a data-loss bug (F13). Three attempts, three cycles of breakage. The pattern suggests the
   design, not the execution, is the limit.
4. **A gated feature is strictly better than a fixed feature for this use case**, because the
   maintenance cost is only paid by people who use it.

**Where I would push back on my own recommendation:** if the owner genuinely wants *per-role field
layouts across many ERPNext doctypes* — a real ERP requirement — then option A is unavoidable, but
it should be done on **Frappe's own `DocType Layout`** (which exists, is maintained by Frappe, and
supports `document_type` + `fields` + per-doctype routes — `frappe/custom/doctype/doctype_layout/`)
rather than on a parallel DOM-surgery engine. That is a genuinely different design and it is the
one path that Frappe upgrades will not break. **Note `DocType Layout` does not support per-user
layouts** — it is per-doctype — so if per-user is a hard requirement, the honest answer is that
you need a small amount of custom code, but it should be a *much smaller* amount than VFC is today.

---

## 7. The plan

### Phase 0 — Stop the bleeding (this week)

| Task | Audit ref | Done when |
|---|---|---|
| Delete the 202 `_Test_*` rows on every site; make the test suite use a disposable DB; block `_Test_` names in `save_layout` | F7 | No `_Test_*` row exists on any site. A test run leaves the DB byte-identical. |
| Stop stripping `hide-control`; skip fields with `disp_status === "None"` | F4 | An under-privileged user on a VFC form cannot see a `permlevel` field. Browser test included. |
| Make "Revert to Default / Native" truthful and functional | F6 | Reverting actually restores native rendering, and the message matches reality. |

### Phase 1 — Gate it off by default (this week, same release as Phase 0)

| Task | Done when |
|---|---|
| Add `enable_form_config` (default **0**) to a site setting | — |
| Skip `_injectButton` and `LayoutEngine.attach()` when the setting is off | With the setting off, **zero** VFC code runs and **zero** forms are affected. Verified by `grep` of the console + a DOM snapshot diff. |
| Show a clear in-product state when it is off | The owner can tell, from the UI, that the feature is off site-wide. |

**After Phase 1 the maintenance pressure is gone.** Everything below is optional work on an
opt-in feature, at the owner's chosen pace.

### Phase 2 — Per-user opt-in and the persistence fix (next release)

| Task | Audit ref | Done when |
|---|---|---|
| Per-user, per-doctype "enable Form Config on this form" | F1 | Two users on one browser can have different layouts on the same doctype. |
| Move density from `localStorage` into `user_settings` | F1 | Density follows the user across devices and is not shared between users on one machine. |
| Add the `__native__` personal-profile sentinel so "revert" means native | F6 | Revert restores the native layout without touching the shared profile. |
| Key the client profile cache by user | F12 | A role change or an admin edit is reflected within one refresh. |

### Phase 3 — Retire the two dead subsystems (deliberately, do not skip)

| Task | Audit ref | Done when |
|---|---|---|
| **Retire the section editor** — remove the Sections tab, its drag/drop, `_mergeProfileWithNativeSections`, `_buildNativeSectionsProfile`, and the `fld.visible` handling | F13, F14, F15 | The Sections tab is gone. No code path can destroy a user's field arrangement, because there are no user field arrangements. `visible` is removed from the profile schema. |
| **Retire tabbed-doctype support** until Frappe's tab DOM is stable | F3 | The engine no-ops on tabbed doctypes with a clear reason logged, instead of misplacing sections. |
| Delete the orphaned `vfc_native_collapsed_sections` data | Fact 3 | No dead keys remain in `__UserSettings`. |

Retiring these removes roughly **1,200 lines** of the highest-risk code (the section editor and
the tab handling) and eliminates audit findings F3, F13, F14, F15 and F16 in one stroke — without
writing new code.

### Phase 4 — Decide with evidence (quarterly review)

Now that the feature is gated, its usage becomes measurable and honest:

* If real users are adopting it (per-user layouts on real doctypes) → consider Phase 5.
* If not → **delete the whole feature cleanly**, backend included, with a data migration that
  drops the profile rows. The theme/UI-override system is untouched and unaffected.

### Phase 5 — Only if there is demonstrated demand

Rebuild the section editor **on Frappe's `DocType Layout`** for the per-doctype case, and keep a
*minimal* custom layer only for the genuinely per-user case. Do not re-introduce DOM re-parenting
of Frappe nodes.

---

## 8. Decision summary

| Option | Verdict | Why |
|---|---|---|
| **Modify the frontend** | **Partially — only the P0s** | Full repair is 3–6 weeks, inherits the same DOM fragility, and serves a need not yet demonstrated (one user hid one field). |
| **Discard the feature** | **Partially — retire the section editor + tab support + the 202 test rows** | The theme/UI-override system is separate, valuable, CSS-based and low-maintenance; deleting it would be collateral damage. The backend is the good part and enables the opt-in path. |
| **Make it optional per user** | **Yes — and do it first** | Directly converts an app-wide upgrade liability into a per-user preference. Lowest cost, lowest risk, and it makes every future Frappe upgrade a non-event. |

**One sentence:** *gate it off by default, fix the three live bugs, keep the backend, stop growing
the frontend, and let usage data decide the rest in a quarter.*

---

## 9. Verify the facts in this document yourself

```bash
cd /home/mohamed/frappe-bench/apps/construction

# Fact 1 — exposure vs usage
mysql -u root -proot -h localhost -e "
  SELECT COUNT(*) AS non_child_doctypes FROM \`_6d52b48c328b294e\`.\`tabDocType\` WHERE istable=0;
  SELECT COUNT(DISTINCT reference_doctype) AS doctypes_with_profile
    FROM \`_6d52b48c328b294e\`.\`tabForm Layout Profile\` WHERE profile_name NOT LIKE '\_Test\_%';
  SELECT SUM(for_user IS NOT NULL) AS personal, SUM(for_role IS NOT NULL) AS role_rows
    FROM \`_6d52b48c328b294e\`.\`tabForm Layout Profile\`;"

# Fact 1 — no gate exists
grep -rn "enable_vfc\|vfc_enabled\|allow_vfc" construction/ --include=*.py --include=*.js \
  | grep -v enable_vfc_debug_logging; echo "exit=$? (1 = no gate exists)"

# Fact 2 — actual user engagement
mysql -u root -proot -h localhost -e "
  SELECT JSON_EXTRACT(data,'\$.\"vfc_hidden_fields\"') hf,
         JSON_EXTRACT(data,'\$.\"vfc_preset\"') preset, COUNT(*)
    FROM \`_6d52b48c328b294e\`.\`__UserSettings\` WHERE data LIKE '%vfc%'
    GROUP BY hf, preset;"

# Fact 2 — the dead key
grep -rn "vfc_native_collapsed_sections" construction/ --include=*.js; echo "exit=$? (1 = written but never read)"

# Fact 3 — the abandon/restart history
git log --oneline -6 -- construction/public/js/vfc_layout_engine.js

# Fact 4 — the coupling
grep -oE '\.form-[a-z-]+|\.tab-[a-z-]+|\.frappe-[a-z-]+|\.section-[a-z-]+' \
  construction/public/js/vfc_layout_engine.js | sort -u

# Fact 4 — contrast: the CSS override layer touches no Frappe JS internals
grep -cE 'frappe\.(ui|model|form)\.' construction/public/css/vite_form_override.css  # → 0

# P0-1 — the live garbage
mysql -u root -proot -h localhost -e "
  SELECT COUNT(*) FROM \`_6d52b48c328b294e\`.\`tabForm Layout Profile\`
   WHERE profile_name LIKE '\_Test\_%';"   # → 202
```

---

*Prepared as a decision brief for the owner. Every fact above is reproducible with the commands
in §9. Phase 0 and Phase 1 are safe to start immediately; Phase 2 onwards changes behaviour and
should follow a short owner decision.*
