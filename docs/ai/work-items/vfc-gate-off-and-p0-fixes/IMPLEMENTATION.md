# IMPLEMENTATION — Phase 1 (builder record)

| | |
|---|---|
| **Work item** | `vfc-gate-off-and-p0-fixes` |
| **Role** | Builder |
| **Date** | 2026-11-12 |
| **Base commit** | `9796c5f27bc899867699b81d3e89d6dd5c62710f` |
| **Branch** | `develop` |
| **Status** | P0-2 ✅ · P0-3 ✅ (code) · D2 ✅ · **P1-1 ⏳ pending** |

> Per AGENT_WORKFLOW §3.2 the builder **cannot** mark its own work
> `VERIFIED_FOR_RELEASE`. This file records what was changed and what ran;
> the verdict belongs to an independent verifier.

---

## 1. Changed files

| File | Change |
|---|---|
| `construction/public/js/vfc_layout_engine.js` | **P0-2** never strip `hide-control` · **D2** gate `_vfcGateOpen()` on attach hooks |
| `construction/public/js/vite_layout_controls.js` | **P0-3** never remove a user-placed field · **D2** gate attach hook |
| `construction/public/js/vfc_config.js` | **D2** add `window.VFCisEnabled()` (lazy) |
| `construction/boot.py` | **D2** `bootinfo["vfc_enabled"]` via `cint()` |
| `construction/construction/doctype/construction_settings/construction_settings.json` | **D2** `enable_form_config` Check, default `"0"` + section |
| `construction/hooks.py` | cache busters ×3 |
| `docs/ai/SCHEMA_FACTS.md` | regenerated (`--update`) after reviewed schema change |

**No SQL, no data repair, no permission change, no scope change.**

---

## 2. P0-2 — never strip `hide-control` ✅

`_restoreVisibleFieldWrapper` previously removed `hide-control` from the wrapper
and all descendants. The guard above it only tests
`df.hidden | df.invisible | hidden_due_to_dependency`, and **none is set** when
Frappe hides a control for `disp_status === "None"` (permlevel, or empty
read-only under `hide_empty_read_only_fields`).

**Change:** if the wrapper already carries `hide-control`, mark it managed and
return — Frappe's decision stands. Descendants with the class are skipped too.

**Scope proof:** `grep -rn 'classList.remove([^)]*hide' construction/ --include=*.js`
→ **no matches**. Every remaining `hide-control` reference is a read
(`.contains`, `:not(.hide-control)`).

**Verified** — `evidence/P02_FIX_VERIFICATION.md`:

| metric | pre-fix | post-fix | VFC-OFF control |
|---|---:|---:|---:|
| managed WITH `hide-control` | 0 | **4** | n/a |
| `hide-control` total | 18 | **22** | 22 |
| `actual_start_date` | visible | **hidden** | hidden |

Negative controls (`expected_start_date` writable; `total_costing_amount`,
`gross_margin`, `actual_time` with value `0`) stayed **visible** in both arms —
the fix preserves Frappe's rule rather than blanket-hiding.

---

## 3. P0-3 — section editor stops destroying user placement ✅ (code)

`_mergeProfileWithNativeSections` built `nativeFieldnames` from **all** fields of
a native section the profile didn't carry, then filtered those names out of
**every** merged section before pushing the native one. Any field a user had
deliberately placed elsewhere was pulled back to native.

**Change:** only fields absent from `usedFields` (which already records every
fieldname the user's own sections hold) are eligible. If none are, the native
section is not pushed. Nothing is removed from a section the user placed a field in.

**Verified:** `node --check` PASS. **Browser verification still outstanding** —
needs a Form Config drag + save + reload cycle (see §6).

---

## 4. D2 — VFC gated off by default ✅

Chain, following the existing `vfc_debug_enabled` pattern:

```
construction_settings.json  enable_form_config  default "0"
        ↓ migrate
boot.py  bootinfo["vfc_enabled"] = bool(cint(getattr(settings, "enable_form_config", 0)))
        ↓
vfc_config.js  window.VFCisEnabled()   // evaluated lazily at attach time
        ↓
vfc_layout_engine.js   _vfcGateOpen() → refresh / onload_post_render return early
vite_layout_controls.js _vfcGateOpen() → refresh returns before VFC.attach()
```

**`cint()` not `bool()`** — an unset Check can surface as the string `"0"` from
the DocType default and `bool("0")` is `True`, which would invert the default.
Probe confirmed: pre-migration `getattr` → missing (safe); post-migration → `int 0`.

**Fail-closed:** if `vfc_config.js` did not load, `_vfcGateOpen()` returns
`false`. The engine never fails open.

**Migration:** `bench --site v16.localhost migrate` → **exit 0**. DocField
registered (Single doctype values live in `tabSingles`, so there is no column to
add — verified `docfield=1`). Profile count unchanged at **8**.

### Verified both directions (browser, non-admin `Projects User`, `PROJ-0002`)

| | Gate **OFF** | Gate **ON** |
|---|---|---|
| `frappe.boot.vfc_enabled` | `false` | `true` |
| `VFCisEnabled()` | `false` | `true` |
| Form Config button | **`[]`** | `["Form Config46"]` |
| `vfc_managed` / cells / sections | **0 / 0 / 0** | 32 / 32 / 12 |
| native `.form-section` | 11 | 11 |
| assets loaded | `v=1.46`, `v=1.27`, `v=2` | same |

**AC-7 satisfied:** with the setting off there is no button injection and no
engine attachment, and the form renders exactly as Frappe would.

**Setting restored to `0` (shipped default) after measurement.**

---

## 5. Commands actually run

| Command | Result |
|---|---|
| `node --check` × 3 modified JS | **PASS** |
| `python3 -m py_compile construction/boot.py` | **PASS** |
| `python3 scripts/schema_drift_checker.py` | **PASS exit 0** (after reviewed `--update`) |
| `python3 scripts/ai_context_check.py` | **PASS 11/11** |
| `python3 scripts/lint_scope_metadata.py` | **PASS exit 0** |
| `bench --site v16.localhost migrate` | **exit 0** |

### The one gate failure encountered, and how it was handled

Adding the DocType field caused `schema_drift_checker` to **fail (exit 1)** and
`ai_context_check` SCP-C8B to fail — correctly, because `SCHEMA_FACTS.md` no
longer matched. Per Standard §95 the response is **not** to `--update` blindly:
the diff was reviewed first (15 insertions, 1 timestamp, purely additive, no
unrelated churn), and only then regenerated. Both checks re-run **green**.

---

## 6. Known limits / not yet done

> **REFRESHED 2026-11-12** — the first version of this section was written
> mid-sprint and still read "P1-1 NOT STARTED" / "D4 not started". Corrected
> after independent review (MINOR-2). Authoritative state is `STATE.json`.

| Item | State |
|---|---|
| **P0-2** fix | **DONE** — `evidence/P02_FIX_VERIFICATION.md`; regression test committed in `test_vfc_layout_regressions.js` |
| **P0-3** fix | **DONE** — function-level test in `evidence/P11_P03_VERIFICATION.md` §4; regression test committed. **Drag → save → reload cycle still not performed in a browser** (see below) |
| **P1-1** revert | **DONE** — narrow `save_my_native_layout` endpoint, controller guard reconciled, 12 backend tests; `evidence/P11_P03_VERIFICATION.md` |
| **D2** gate | **DONE** — verified OFF and ON in browser; `evidence/P02_FIX_VERIFICATION.md` |
| **D4** freeze | **DONE** — Sections editor + `Tab.prototype` patch retired, tabbed doctypes skipped, Revert relocated; `evidence/D4_VERIFICATION.md` |
| **P0-1** cleanup | **DONE** — deleted under D3 conditions; root cause (tearDown leak) found and fixed |
| **P0-3 browser reload cycle** | **NOT DONE** — AC-6's "after reload" wording was satisfied by a committed function-level regression instead. Acceptance wording vs. evidence gap recorded as `FINAL_REVIEW.md` MAJOR-2 |
| **D6** test/production isolation | **NOT DONE** — separate ticket; suite still writes to the live site DB (`allow_tests: true`) |
| Independent verifier pass | **DONE** — `FINAL_REVIEW.md`, verdict `CHANGES_REQUESTED` (coverage/traceability gaps only, no functional defect) |
| Owner decisions outstanding | **S4** (D4 silently withdraws VFC from `Project`/`Task`) and the **waiver option** in `FINAL_REVIEW.md` §8 — both are the owner's to make |

### Cache busters — final values

| File | Original | **Final** |
|---|---|---|
| `vfc_config.js` | `?v=1` | **`?v=2`** |
| `vite_layout_controls.js` | `?v=1.25` | **`?v=1.29`** |
| `vfc_layout_engine.js` | `?v=1.44` | **`?v=1.50`** |

Earlier tables in this file showed intermediate values (`1.45/1.26`, `1.46/1.27`)
from during-sprint checkpoints; those are superseded. The verifier confirmed the
browser loaded exactly `?v=2`, `?v=1.29`, `?v=1.50` (`FINAL_REVIEW.md` AC-9).

---

## 7. Working-tree disclosure

Modified (this work item): `vfc_layout_engine.js`, `vite_layout_controls.js`,
`vfc_config.js`, `boot.py`, `construction_settings.json`, `hooks.py`,
`SCHEMA_FACTS.md`, plus `docs/ai/work-items/vfc-gate-off-and-p0-fixes/`.

**Preserved, NOT mine:** `dashboard/app.py`, `dashboard/tests/conftest.py`,
`orchestrator/candidates.py`, `orchestrator/engine.py`, `SESSION_MEMORY.md`
(modified) and `dashboard/tests/*`, `orchestrator/tests/*`,
`orchestrator/engineering_control_contracts/` (untracked) — all belonging to
`t3-engineering-control-wp1`.

**Nothing has been committed.**
