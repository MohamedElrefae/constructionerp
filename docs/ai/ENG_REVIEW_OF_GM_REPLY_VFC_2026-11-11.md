# Engineering Lead — Review of the GM Reply (VFC)

| | |
|---|---|
| **To** | General Manager |
| **From** | Head of Engineering |
| **Date** | 11 November 2026 |
| **Re** | `docs/ai/GM_REPLY_VFC_NEXT_STEPS_2026-11-11.md` — corrections before execution |
| **Status** | **Approval accepted. Three corrections required before the team starts.** |

---

## 1. Position

**The decision is accepted in full and I will execute it.** Gate off by default, fix the live
defects, keep the backend, retire the dead subsystems. The reasoning in the reply — particularly
"that's a posture, not a feature" and "one user's setup breaks, one user fixes it" — is correct and
I have nothing to add.

**However, three items in the reply do not match the evidence.** I am raising them now rather than
after the team has started, because one of them would send engineers to chase a defect that does not
exist, while the defect that *does* exist gets renumbered out of the urgent list.

I am not reopening the decision. I am correcting the work list.

---

## 2. Correction 1 — "P0-1: section-open crash on `undefined` field wrapper" is not a real finding

**The reply states:**

> **Fix P0-1** (section-open crash on `undefined` field wrapper). It's a `TypeError` on a live form.

**This defect does not exist in the code, and it was not in my memo.**

Every access to a field wrapper in both files is guarded. Verified line by line:

| File:line | Access | Guard |
|---|---|---|
| `vfc_layout_engine.js:390-393` | `fieldObj` | `if (!fieldObj) { … return; }` |
| `vfc_layout_engine.js:415-419` | `fieldObj.wrapper` | `if (!wrapper) { … return; }` |
| `vfc_layout_engine.js:684-690` | `fieldObj.wrapper` | `if (!fieldObj) continue;` then `if (!wrapper) { … return true; }` |
| `vfc_layout_engine.js:997` | `fieldObj.wrapper` | `if (!fieldObj \|\| !fieldObj.wrapper) return;` |
| `vfc_layout_engine.js:1042` | `fieldObj.wrapper` | `if (!fieldObj \|\| !fieldObj.wrapper) return;` |
| `vfc_layout_engine.js:1085-1087` | `fieldObj.wrapper` | guarded by `if (nativeWrapper && …)` |
| `vfc_layout_engine.js:1281-1291` | `fieldObj.wrapper` | `if (!fieldObj) return;` then `if (!wrapper) return;` |
| `vfc_layout_engine.js:146-147` | `frm.layout.tabs[0]` | `if (hasTabs && frm.layout.tabs && frm.layout.tabs.length)` |
| `vite_layout_controls.js:852` | `frm.layout?.wrapper` | optional chaining, then `if (!container) return;` |

I also searched for any other `.wrapper` access in both files; there are no unguarded ones.

**Risk if this goes out as written:** an engineer spends a day hunting a `TypeError` that cannot
occur, while the actual P0 (202 test rows in production) is no longer labelled P0-1 in the reply's
numbering. That is a wasted day and a diluted priority signal.

**What I need:** if this came from a support report, a console trace, or an observed failure, please
send it to me and I will investigate immediately — it may be a real defect in a code path I have not
seen. If it came from the audit document, it was not in it, and I would like to know how it entered
the reply so the same thing does not happen again.

**Until then: strike P0-1 as written.** The real urgent list is §4 below.

---

## 3. Correction 2 — "Budget and Project are already on the list" is half wrong

**The reply states:**

> Flag any doctype where `permlevel > 0` fields exist under a VFC-managed profile — Budget and
> Project are already on the list.

I checked both doctypes directly:

| Doctype | Fields | `permlevel > 0` fields | VFC-managed? | Affected? |
|---|---|---|---|---|
| **Budget** | 40 | **none** | Yes (enabled default profile) | **No** |
| **Project** | 59 | **`users` (Table, permlevel 1)**, `copied_from` (Data, permlevel 1, `hidden: 1`) | Yes (enabled default profile) | **Yes — live today** |

**Budget is clean.** It has no permlevel fields, so it is not a case for this defect.

**Project is the live case, and it is worse than "on the list":**

* `Project.users` is a **Table** (`Project User`) at `permlevel 1`, and its meta `hidden` is **not
  set** — so the engine's skip-guard (`vfc_layout_engine.js:402-413`, which checks
  `df.hidden` / `df.invisible` / `hidden_due_to_dependency`) does **not** skip it.
* `Table` is **not** in the engine's `SKIP_TYPES` set, so the engine moves it into a VFC cell.
* `_restoreVisibleFieldWrapper` then strips the `hide-control` class that Frappe applied because the
  user lacks permlevel-1 read access.
* **Net effect: the "Users" table becomes visible to a user who is not permitted to see it.**

I checked what the server does with the data. `apply_fieldlevel_read_permissions`
(`frappe/model/document.py:974-980`) deletes the parent attribute for a permlevel field the user
cannot read, so the client receives **no child rows**. The exposure is therefore the field itself —
its label and an empty grid — **not the email addresses** in it. I want to be precise about that: this
is a **UI permission regression**, not a data breach. My earlier memo said the same; the reply's §1
item 2 repeats it correctly. I am restating it here because "Project is on the list" understates that
it is **live now**, not a future risk.

**Action:** Project moves from "flag for review" to **the first browser test case** in Phase 0.4.
The test is: a user with Project read at permlevel 0 only opens Project → the "Users" table must not
be visible.

---

## 4. Correction 3 — the P0 numbering does not match my memo

The reply's P0 list and mine differ. Neither is wrong on substance, but the team will work from the
reply, so the numbers must be right.

| | My memo | GM reply | Corrected |
|---|---|---|---|
| **P0-1** | 202 `_Test_*` rows live in production (F7) | "section-open crash" | **202 test rows in production** |
| **P0-2** | Permission regression (F4) | Permission regression | **Permission regression** |
| **P0-3** | "Revert to Default" does nothing (F6) | Section-editor data loss (F13) | **Section-editor data loss** |

Notes:

* **The 202 rows are still covered** — the reply handles them under D3 with backup/row-list/dry-run
  conditions. That is correct and I accept it. But they should remain **P0-1 in the numbering**, because
  they are live production data, not a UI bug.
* **The section-editor data loss (F13) is correctly elevated to P0.** I rated it P1 in the audit; the
  reply is right to treat it as P0 because it is **reproduced in the live database** and it destroys
  user work. I accept the upgrade.
* **"Revert to Default" (F6)** drops to the P1 list. Acceptable — it is a false-success message, not
  data loss. But it must be fixed in Phase 1 alongside the `__native__` sentinel, since the sentinel is
  what makes revert work.

**Corrected urgent list for the team:**

| # | Defect | Evidence | Where |
|---|---|---|---|
| **P0-1** | 202 `_Test_*` rows live in production; test suite writes to the live DB | `SELECT COUNT(*) … WHERE profile_name LIKE '\_Test\_%'` → 202 | `test_vfc_backend.py:57` |
| **P0-2** | Permission regression — `Project.users` (Table, permlevel 1) becomes visible | `project.json` `users` permlevel 1, `hidden` unset; engine `SKIP_TYPES` omits `Table`; `_restoreVisibleFieldWrapper` strips `hide-control` | `vfc_layout_engine.js:853-879` |
| **P0-3** | Section editor destroys the user's arrangement on every save/load | Live DB: 5 user sections with 0 fields; native sections hold all fields | `vite_layout_controls.js:1362-1367` |
| **P1-1** | "Revert to Default / Native" reports success while doing nothing | `delete_my_personal_layout` can never match; no personal profile is ever created | `layout_api.py:224-248`, `vite_layout_controls.js:944-961` |

---

## 5. Confirmations — what the reply gets right

So the record is balanced, these are correct and I want them kept:

| Reply item | My verification |
|---|---|
| "492 forms … served one user, one field, one time" | Confirmed. `COUNT(*) WHERE istable=0` → 492; 8 doctypes with profiles; `__UserSettings` shows one `["description"]` entry |
| "No flag anywhere" | Confirmed — `grep` for any enable/flag returns only the unrelated debug setting |
| "Backend shape is already there — resolver personal → role → default; wire `for_user`" | Confirmed. `layout_api.py:79-93`; the UI never passes `for_user` |
| "`__native__` personal profile with empty sections gives revert for free, no schema change" | Confirmed. Empty sections ⇒ native layout untouched; resolver prefers `for_user` |
| "The audit correction was the right call" | Confirmed. Two findings would have reached you as a security incident; they were a UI regression and a dropped guard |
| "The theme system is CSS-based … 126 selectors, zero references to Frappe internals" | Confirmed exactly — 126 `html.ct-enterprise` selectors, 0 references to `frappe.ui/model/form` |
| "Don't let the right long-term answer slow down the right immediate answer" | Agreed, and it is now explicit in the plan |

---

## 6. One operational concern with the D6 CI guard

The reply proposes:

> a CI check that prevents any test from writing to a database that doesn't have a `test_` or `_test`
> suffix in its name

**Direction is right; the rule as written will block legitimate work.** Our dev benches use
hash-named databases (e.g. `_6d52b48c328b294e`), which carry no `test_` suffix, so the guard would
fail every local and CI run on a normal bench.

**Refined rule I will implement:** block writes to a database **whose site is not the test site**,
i.e. key the guard on the site name / `site_config.json` rather than the database name, and allow the
standard bench databases. Same intent, no false positives. I will bring the exact implementation to
the D6 ticket.

---

## 7. Corrected execution order

Everything else in the reply stands. With the corrections above:

**Phase 0 — this week**

1. **Browser-verify F3 and F4 first.** F4 now has a specific, high-value test case: **Project /
   "Users" table**. F3 remains unverified — do not fix it until reproduced.
2. **P0-1** — delete the 202 test rows, under the three D3 conditions (backup → published row list →
   dry-run in a transaction).
3. **P0-2** — stop stripping `hide-control`; skip fields whose display status is "None".
4. **P0-3** — stop the section editor from removing user-placed fields.
5. **Strike the "section-open crash" item** pending evidence (§2).

**Phase 1 — parallel**

6. Site setting `enable_form_config`, default **OFF**; skip button injection and engine attachment.
7. Per-user opt-in; `__native__` sentinel; density moved to server-side user settings (also fixes P1-1).
8. Staging demo before any production deploy.

**Phase 2+ — deferred, as ruled.** No frontend rewrite, no schema change beyond Phase 1, no
extension to new doctypes.

---

## 8. What I need from you

| # | Request | Why |
|---|---|---|
| **C1** | Confirm the corrected P0 numbering in §4 | So the team works the right list |
| **C2** | Send me the source of the "section-open crash" claim, or confirm it is struck | Either it is a real defect I have not found, or it should not consume a day |
| **C3** | Confirm the D6 guard refinement in §6 | So the ticket is written correctly the first time |
| **C4** | Confirm Project as the first browser test case for P0-2 | It is the only live-affected doctype |

Nothing else. The decision stands; the plan stands; these are corrections to the work list, not to
the direction.

---

*Head of Engineering — 11 November 2026*
