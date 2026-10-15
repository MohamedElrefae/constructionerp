# F23 — VFC and theme stabilization (evidence)

Date: 2026-10-14 · Site: `v16rehearsal.localhost` (serving verified before evidence)
Personas: `f04-pm` (Project Manager, **Arabic/RTL**) and `f04-engineer` (Site Engineer, **English/LTR**)

---

## 1. What F23 tested

Your six dimensions, each exercised through the real UI (not API calls) with ordinary
personas:

| Dimension | Check | Result |
|---|---|---|
| Arabic + RTL | `html lang=ar`, `dir=rtl` | pass |
| English + LTR | `html lang=en`, `dir=ltr` | pass |
| light/dark | switch to Dark → applied; reload → **persisted**; switch back to Light → applied | pass (both personas) |
| layout persistence | column density change → applied; reload → **persisted** (`vfc_BOQ_Item_density` in localStorage) | pass |
| layout reset | revert → default density restored and stored override cleared | pass |
| field visibility | visibility checkbox → applies live; persists through the documented Apply & Save flow | pass |
| dependent fields | report viewer: company supplied → view runs (`Page 1: 0 of 0 rows`, Arabic "no rows for these filters") | pass |
| permission-controlled field | `certified_qty` on BOQ Item Stage: PM editable, Site Engineer input disabled | pass |

**Result: PM 13/13, engineer 5/5 → 18/18.**

Screenshots: `/tmp/opencode/f23-shots/` (`a-dark-ar.png`, `a-stage-pm.png`,
`b-stage-engineer.png`).

### Permission-controlled fields, concretely

`apply_stage_measurement_ui` in `boq_item_stage.js` sets `certified_qty` read-only unless the
session holds System Manager, Construction Owner or Project Manager (F11-D003 measurement vs
certification). Measured as rendered, not assumed:

- `f04-pm` → `{"hasEditable": true}` — may certify.
- `f04-engineer` → `{"editableInput": false, "disabledInput": true}` — may record measurements,
  cannot certify.

## 2. Findings

**F23-D002 — VFC field-visibility changes apply live but persist only via "Apply & Save",
with no indication of the difference.** (owner decision 2026-10-14: keep explicit Apply & Save)

Fixed in `public/js/vite_layout_controls.js` + `public/css/vite_form_override.css`:
- **Unsaved-changes indicator** — the panel footer now shows `Unsaved changes: N field(s). Apply & Save to keep them.` in danger colour (with a matching `vfc-dirty` CSS rule), driven by `_updateDirtyStatus` / `_dirtyFields`, which compare the staged checkbox state against the saved `vfc_hidden_fields`.
- **Warn before closing** — the Close button, Escape key and backdrop all route through `_closeIfClean` / `_closeAllIfClean`, which ask "You have unsaved layout changes. Close and discard them?" and keep the panel open on decline.
- **Warn before leaving** — `_registerLeaveGuard` hooks `frappe.router.on("change")` and asks "You have unsaved layout changes. Leave and discard them?", restoring the previous URL on decline.
- **Density labelled** — "Density saves automatically when you pick it." above the control, since density and visibility now differ on purpose.

Implementation notes (recorded so the F38 review does not re-litigate them):
- The indicator call initially landed in `_renderFieldList` instead of `_onVisChange`, and a
  duplicate method definition shadowed the corrected one. Both fixed; the call now sits at the
  end of `_onVisChange` and the method is defined exactly once.
- `saveUserSettings` did not return the promise from `frappe.model.user_settings.save`, so
  `await` resolved immediately and the indicator read the pre-save state (still "unsaved" after
  Apply & Save). It now returns the promise, and `_applyAndSave` / `_revertToDefault` await it
  before refreshing the indicator.

Retested after the fix (one clean browser context, `f04-pm`, BOQ Item): 10/10 —
density label visible; indicator shows on change; discard on reload loses it and stores
nothing; indicator clears after Apply & Save; the change persists after reload; reset clears
it; close warning opens, decline keeps the panel, accept discards. The F23 suite still passes
18/18.

Fixture state (disclosed): the retest toggled `item_type` visibility for `f04-pm` on BOQ Item;
that user setting was reset afterwards (`vfc_hidden_fields → []`, `vfc_preset → Default`).

`_onVisChange` calls `cur_frm.toggle_display(...)` immediately, so hiding a field works at
once and looks saved. The preference is written by `_applyAndSave` → `saveUserSettings(dt,
"vfc_hidden_fields", …)` only. Verified both ways:

- change a checkbox, navigate/reload **without** Apply & Save → the field is visible again and
  nothing was stored;
- change, click **Apply & Save**, reload → the field stays hidden.

So the feature works as built, but the panel gives no unsaved-changes signal, and the
cheapest thing a user does (hide a field, move on) silently discards it. Density behaves the
same way in reverse — it saves on click, so the two halves of the same panel have different
durability rules. Recorded for a follow-up decision (an "unsaved" marker in the panel, or
persist visibility on change the way density does); not changed here because it is a
behaviour change to a working control, not a defect that blocks acceptance.

**No other F23 defects.** Theme, density, dependent fields and the permission-controlled
field all behaved as documented for both personas.

## 3. Fixture state (disclosed)

The browser suite toggled `item_type` visibility for `f04-pm` on BOQ Item to prove the
persistence path. That user setting was reset afterwards
(`vfc_hidden_fields → []`, `vfc_preset → Default`), verified by reading the stored settings.

`f23-scopeless@v16rehearsal.local` was created for the denial-test carry-forward (see the
register) and is left in place deliberately: Site Engineer role, Company user permission, and
no User Scope Context.

## 4. Status

F23 **Engineering verified** for the six dimensions you listed, across an Arabic/RTL and an
English/LTR ordinary persona. Owner acceptance (including your personal sign-off and the
Arabic reviewer's pass) stays in the consolidated final block. F23-D002 is open as a
usability decision, not a blocker.
