# D4 Verification — frontend frozen: Sections editor and Tab.prototype patch retired

| | |
|---|---|
| **Work item** | `vfc-gate-off-and-p0-fixes` |
| **Phase** | 1 — D4 (freeze frontend) |
| **Executed** | 2026-11-12 |
| **Verdict** | **PASS — plus the root cause of P0-1 found and fixed** |

---

## 1. What D4 removed

### 1a. The `Tab.prototype.refresh` monkey-patch

The engine permanently replaced Frappe's own tab refresh behind a
`_vfc_patched` flag:

```js
TabClass._vfc_patched = true;
TabClass.prototype.refresh = function () { ... this.toggle(!hide); };
```

Consequences of keeping it:

* one VFC render on a tabbed doctype changed tab visibility on **every**
  form afterwards, including forms VFC never touched;
* it is the global prototype replacement Standard §13 warns against;
* it is a vendor patch — Frappe owns `Tab`, not this app.

**Removed.** The only remaining `TabClass` / `_vfc_patched` mentions are in the
comment explaining why it is gone:

```
$ grep -rn "TabClass.prototype|_vfc_patched = " construction/public/js/
no prototype patch code
```

### 1b. The Sections editor (panel tab + pane)

Removed: the `Sections` tab button, the `Manage Sections` pane, the
`+ Add Section` button, and the now-dead `if (name === "sections")` branch.

```
$ grep -n 'data-vfc-tab="sections"|data-vfc-pane="sections"' vite_layout_controls.js
no Sections tab/pane
```

**Not removed:** `_mergeProfileWithNativeSections` — it is what *loads* profiles
for rendering, not an editing surface, and it is the function P0-3 fixed.

---

## 2. Two things D4 forced, discovered by testing

### Finding A — retiring the patch alone produces a BLANK FORM

Removing only the patch and leaving VFC on tabbed doctypes was measured first:

| | with patch | patch removed, no skip |
|---|---|---|
| tabs visible | 5 / 5 | **0 / 5** |
| active tab | Details | Connections (stuck in `#connections_tab`) |
| form body | rendered | **blank — no fields in the a11y tree** |
| `shells display:none` | 42 | 42 |

**Why:** once VFC moved a tab's fields out of the native sections, Frappe's own
`Tab.refresh` saw those sections hidden and hid the tab itself. The patch
existed precisely to overrule that. With the patch gone there is nothing left to
overrule with — so **tabbed-doctype support had to retire together with the
patch**. Removing one without the other is not viable.

**Fix:** `attach` now returns early for any doctype with a `Tab Break`, after
unwinding prior state via `_clearSections`.

### Finding B — the Revert control lived inside the retired pane

`#vfc-revert-btn-*` was defined inside the Sections pane (P1-1's control).
Deleting the pane would have silently destroyed the P1-1 fix, so Revert was
**relocated to the Layout pane** before the pane was removed.

Verified: exactly **one** element with that id, in pane `layout`, and the
confirm dialog still fires end-to-end.

---

## 3. Verification (browser, non-admin `Projects User`, `PROJ-0002`)

### Tabbed doctype now renders natively

| Check | Result |
|---|---|
| tabs visible | **5 / 5** (Details active) |
| `vfc_cells` / `vfc_sections` / `vfc_managed` | **0 / 0 / 0** |
| `shells_vfc_hidden` | **0** |
| form body | rendered, native |
| engine asset | `vfc_layout_engine.js?v=1.50` |

### Panel after retirement

| Check | Result |
|---|---|
| tabs present | `layout`, `fields` — **no `sections`** |
| `sections_tab_exists` / `sections_pane_exists` | **false / false** |
| `add_section_btn` | **false** |
| Revert found + visible | **true / true** |
| `revert_in_pane` | **`["layout"]`** |
| `revert_count` | **1** (no duplicate id) |
| Revert end-to-end | confirm → Yes → executes; 5/5 tabs visible, `shells_vfc_hidden: 0` |

### Non-tabbed path unaffected — by construction

Both engine changes sit **inside `hasTabs` conditions** (the patch block and
the new skip). For a doctype with no `Tab Break` the executed code is
byte-identical to before D4. The only cross-cutting D4 change is panel UI,
verified above.

---

## 4. ROOT CAUSE OF P0-1 FOUND (and fixed)

While checking for pollution after the test run, **2 `_Test_` rows had
reappeared** — despite P0-1 having deleted 202 and verified 0.

Cause, in `test_vfc_backend.py`:

```python
def test_is_system_delete_guard(self):        # line 130
    p = self._make_profile(is_system=1)       # creates an is_system row
def test_delete_layout_blocks_is_system(self): # line 275
    p = self._make_profile(is_system=1)

def tearDown(self):
    for doc in self.profiles:
        try:
            frappe.delete_doc(...)
        except Exception:
            pass        # ← on_trash throws for is_system; swallowed → ROW LEAKS
```

`FormLayoutProfile.on_trash` refuses `is_system` rows. The bare
`except: pass` swallowed it, so **every run of those two tests left a row
behind**. Over months that is exactly how 202 rows accumulated in production.

**Fix:** fall back to a direct `frappe.db.delete` when `delete_doc` refuses —
the guard exists to protect *real* seeds, not test fixtures — and commit.

Also closed: `TestSaveMyNativeLayout` created a throwaway `User` in `setUp`
that `tearDown` never removed. It now deletes the user and its `Has Role` rows.

### Proof — zero pollution after a full run

```
before: profiles=8  _Test_=0  personal=0  users=0
run:    51 tests, OK, exit 0
after:  profiles=8  _Test_=0  personal=0  sentinels=0
        test users=0   Has Role rows for vfc users=0
```

All 8 real profiles intact, `enabled=1 is_default=1`.

> **Note for D6:** this closes the *leak*, but the suite still writes to the
> live site database (`allow_tests: true`). Test-to-production isolation remains
> D6's own ticket and is **not** closed by this.

---

## 5. One self-inflicted failure, reported

An intermediate version of `_purge` passed `or_filters` to `frappe.db.delete`,
which takes plain filters only — it treated the list as a field name
(`AttributeError: 'list' object has no attribute 'lower'`). All 12 tests of the
new class failed **in `setUp`**, before a single assertion ran, and the
throwaway user was left behind.

Corrected to two sequential deletes. The subsequent run is the 51/51 above.
This is recorded because a `setUp` failure can masquerade as "tests passed"
when only the tail of the output is read — the full result was `FAILED
(errors=12)`, not `OK`.

---

## 6. Checks

| Check | Result |
|---|---|
| `run-tests … test_vfc_backend` | **51 / 51 OK**, exit 0 |
| `node --check` × 3 | **PASS** |
| `py_compile` × 4 | **PASS** |
| `schema_drift_checker` | **PASS exit 0** |
| `ai_context_check` | **PASS 11/11** |
| `lint_scope_metadata` | **PASS exit 0** |
| prototype patch residue | **none** |
| Sections tab/pane residue | **none** |

Cache busters now: `vfc_layout_engine.js?v=1.50`,
`vite_layout_controls.js?v=1.29`, `vfc_config.js?v=2`.

Environment restored: `enable_form_config = 0`, 8 profiles, 0 personal, 0
`_Test_`, 0 test users.

**Nothing committed.**
