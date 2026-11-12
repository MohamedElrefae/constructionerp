# FINAL REVIEW — vfc-gate-off-and-p0-fixes

**Verifier:** independent verification agent (fresh context; did not build this)
**Date (UTC):** 2026-11-12T09:04:51Z
**Base commit:** `9796c5f27bc899867699b81d3e89d6dd5c62710f` (branch `develop`, unchanged)
**Worktree at review:** dirty — 15 modified + 14 untracked = **29** entries. The 10 item files
plus the 5 §3c docs are this work item; the other 14 entries belong to
`t3-engineering-control-wp1` and were **excluded** from review (see §5).

---

## 1. Plan-conformance matrix

| Acceptance criterion (PLAN.md §7) | Met? | Evidence I produced |
|---|---|---|
| **AC-1** Project browser test, `Projects User` without `Desk User` | **MET** | Evidence present (`evidence/AC1_AC2_PROJECT_BROWSER_TEST.md`). Independently confirmed the reason it cannot sit in the permlevel gap: `frappe/permissions.py:35-40,567` auto-grants `Desk User` (`SYSTEM_USER_ROLE`) to every System User, and `AUTOMATIC_ROLES` keeps it out of `tabHas Role`. So the permlevel half of P0-2 is **structurally unreachable**, not merely latent — the evidence is accurate. |
| **AC-2** F3 reproduced or struck with evidence | **MET** | Not reproduced. Verified `Project` has 4 `Tab Break` fields (`costing_tab`, `monitor_progress_tab`, `more_info_tab`, `connections_tab`) and `Task` has 2 — exactly as claimed. Now moot: D4 skips tabbed doctypes entirely. |
| **AC-3** Row list published before deletion, backup, dry-run, transaction | **MET (with one NOTE)** | `P01_ROW_LIST_BEFORE_DELETION.md` (202 of 210, generated 22:38:23Z) precedes `P01_DELETE_EXECUTION_LOG.txt` (22:50:51Z). Dry run: `DRY-RUN SELECT matched: 202`, all assertions PASS, no DELETE/COMMIT. Delete log: pre-flight 210/202/8/0, committed, post-delete 0/8/8, all 8 defaults still resolve. See **NOTE-5** on the rollback. |
| **AC-4** Post-delete `_Test_` = 0, 8 real profiles intact | **MET** | Live query now returns `profiles=8  _Test_=0  personal=0`; all 8 profiles `enabled=1 is_default=1`. |
| **AC-5** P0-2 fix + **regression test** for permlevel **and** empty read-only field | **PARTIALLY MET** | The fix is confirmed — twice independently (builder A/B, and my own A/B at the final asset versions). But **no regression test exists**: `construction/tests/test_vfc_backend.py` contains no `hide-control` assertion, and `vfc_layout_engine_tests.js` is referenced by no runner. Also the permlevel clause is unsatisfiable on this site (AC-1). See **MAJOR-1**. |
| **AC-6** P0-3 fix + **regression** that a user-placed field survives reload | **PARTIALLY MET** | Logic is correct (reviewed in §5) and the builder ran a discriminating function-level test (`P11_P03_VERIFICATION.md` §4: new keeps `project_name` in `sec_custom`, reimplemented old algorithm moves it to native). But it used a **synthetic `frm`** against `window._VFC`, not a drag→save→**reload** cycle, and it is not committed as a test. `IMPLEMENTATION.md` §3 still says this is outstanding. See **MAJOR-2**. |
| **AC-7** `enable_form_config` default OFF; OFF → no button, no engine | **MET** | **V4** below: gate OFF → `boot.vfc_enabled=false`, `VFCisEnabled()=false`, 0 Form Config buttons, `data-vfc-managed=0`, `vfc-le-cell=0`, native `.form-section` = 10. |
| **AC-8** Per-user opt-in + `__native__` sentinel makes revert work | **MET (qualified)** | **S2/S3** confirmed empirically. `TestSaveMyNativeLayout.test_sentinel_displaces_default_profile` passes in the 51/51 run. I created a real sentinel and confirmed `_clearSections` un-hides and cancels timers, but did **not** separately re-observe the final native render of a revert on a non-tabbed doctype (see §2 close-out). |
| **AC-9** Cache busters bumped; loaded browser file verified | **MET** | `hooks.py`: `vfc_config.js?v=1→2`, `vite_layout_controls.js?v=1.25→1.29`, `vfc_layout_engine.js?v=1.44→1.50`. Browser loaded **exactly** `?v=2`, `?v=1.29`, `?v=1.50` (plus `vfc_sections.css?v=1.6`). |
| **AC-10** Builder does not self-certify; verifier produces `FINAL_REVIEW.md` | **MET** | This document. `STATE.json` still records `final_verifier: FINAL_REVIEW.md PENDING` — correct. |

---

## 2. Gap closure (§5) — the primary task

**Subject:** doctype **`BOQ Item`** (0 `Tab Break`, 0 permlevel>0 fields, 53 fields),
document **`BOQI-BOQ-2026-0274-0275`**, profile `BOQ Item-Default`
(`enabled=1 is_default=1 is_system=1`), company `Elrefae`, project `PROJ-0008`.

**Actor:** throwaway `verifier.vfc.probe@example.com` — **non-Administrator**, role
`Site Engineer` (+ framework-auto `Desk User`), password set via
`frappe.utils.password.update_password`. A `User Scope Context` (Elrefae / PROJ-0008) was
required to pass `boq_permissions.has_boq_parent_permission`; without it every BOQ Item read
is `403` even though doctype read is granted. That is the same wall the builder hit.

**Assets under test (final tree, not the builder's earlier builds):**

```
vfc_config.js?v=2        vite_layout_controls.js?v=1.29
vfc_layout_engine.js?v=1.50    vfc_sections.css?v=1.6
```

> The builder's P0-2/P1-1 evidence was captured at `?v=1.45`/`?v=1.26` and
> `?v=1.48`/`?v=1.28`. **None** of those is the shipped version. This section is the first
> browser observation at `?v=1.50`/`?v=1.29`.

| # | Check | Result | Measured |
|---|---|---|---|
| **V1** | VFC renders on a non-tabbed doctype | **PASS** | `vfc-le-cell = 37`, `vfc-le-section = 15`, `[data-vfc-managed] = 37`, `.vfc-active = 1`. **D4 did not over-skip.** |
| **V2** | P0-2 still holds (`hide_empty_read_only_fields` ON) | **PASS** | `9` elements match `.hide-control[data-vfc-managed]`: `active_cost_analysis, cost_basis, import_batch, import_batch_id, import_mode, last_quantity_revision, source_item_ref, source_sheet_name, variation_order`. `import_batch` / `source_sheet_name` are `data-vfc-managed="1"`, `display:none`, height 0 — Frappe's decision stands. |
| **V3** | D2 gate ON | **PASS** | `frappe.boot.vfc_enabled === true`, `VFCisEnabled() === true`, exactly 1 `Form Config` button (`.vfc-btn`), engine attached (37 cells). |
| **V4** | D2 gate OFF | **PASS** | `boot.vfc_enabled === false`, `VFCisEnabled() === false`, Form Config buttons `0`, `data-vfc-managed = 0`, `vfc-le-cell = 0`, native `.form-section = 10`, `.vfc-active = 0`. |
| **V5** | Negative controls | **PASS** | `cost_item` (writable `Data`, value `NULL`) — visible, height 82. `overhead_amount` (read-only `Currency`, value `0`) — visible, height 56. `is_null(0)` returns falsy (`cstr(0).trim() !== ""`), so the rule is preserved, not blanket-hidden. |

**Decisive A/B (same user, same document, same `hide_empty_read_only_fields`, only the gate differs):**

| metric | gate ON | gate OFF |
|---|---:|---:|
| `.hide-control` total | **21** | **21** |
| hide-control field-name set | **13 fields** | **13 fields — identical** |
| `.frappe-control` total | 42 | 42 |
| `data-vfc-managed` | 37 | 0 |
| `vfc-le-cell` | 37 | 0 |
| Form Config button | 1 | 0 |

The set of controls Frappe hides is **byte-for-byte identical** with VFC on and off. Contrast
the pre-fix evidence (18 vs 22): the defect is gone at the shipped asset version.

Two fields `quantity_executed` / `quantity_certified` are `hide-control` but **not**
`data-vfc-managed`; they carry `df.hidden = 1` set by Frappe itself, so the engine's skip-guard
(and `_restoreVisibleFieldWrapper`'s `df.hidden` guard) leaves them alone. Correct and conservative.

**Close-out caveat:** AC-8's end-to-end revert was not re-observed by me at the final asset
version (the environment's browser runs were unstable mid-session). The pieces are each
confirmed: sentinel creation (S3), resolver displacement (51/51 suite), and the un-hide path
(§4 S5). A one-line follow-up for the builder is in the verdict.

---

## 3. Findings by severity

### BLOCKER
**None.**

### MAJOR

**MAJOR-1 — AC-5 regression test is absent for P0-2.**
`construction/tests/test_vfc_backend.py` (all 51 tests) contains **no** `hide-control`
assertion; `grep -rn "hide-control" --include=*.py --include=*.js` over the app finds test
files: **none**. `construction/public/js/vfc_layout_engine_tests.js` exists but is referenced
by no runner (only historical artifact manifests). The 12 new tests are all
`save_my_native_layout` backend tests.
Confirmed by: `grep`, and by reading the uploaded test diff.
Why it matters: P0-2 is a *class* of regression (VFC overriding a platform hide). With no
assertion, the next edit to `_restoreVisibleFieldWrapper` can silently reintroduce it, and
only another manual browser A/B would catch it — which is how it survived to here.
File: `construction/tests/test_vfc_backend.py` (no coverage); `vfc_layout_engine.js:851-900`.

**MAJOR-2 — AC-6 was tested at function level, not "after reload", and is not committed.**
`evidence/P11_P03_VERIFICATION.md` §4 states the test used "a synthetic `frm`" against
`window._VFC`. `IMPLEMENTATION.md` §3 still records "Browser verification still
outstanding — needs a Form Config drag + save + reload cycle". No persistent test.
The algorithm itself is correct (§4 S-notes / §5 diff), so this is coverage, not behaviour.
File: `construction/public/js/vite_layout_controls.js:1357-1398`.

### MINOR

**MINOR-1 — `REVIEW.md` is missing while status says `APPROVED_FOR_BUILD`.**
`STATE.json` carries both `"status": "APPROVED_FOR_BUILD"` and
`"reviewer": "REVIEW.md PENDING - independent review required before APPROVED_FOR_BUILD"`.
The work-item directory contains `PLAN.md, IMPLEMENTATION.md, STATE.json,
VERIFIER_BRIEFING.md, evidence/` — **no `REVIEW.md`**. The ARCHITECT → REVIEWER → BUILDER
chain the briefing cites is therefore not evidenced.

**MINOR-2 — `IMPLEMENTATION.md` §6 is stale and contradicts the final state.**
Lines 144-152 still read "P1-1 … **NOT STARTED**", "**D4** … not started",
"P0-3 browser verification … code + `node --check` only". All three were subsequently
implemented and have their own evidence files. The briefing uses this file as D2 evidence
(§4), so the stale body is misleading. Cache-buster table in §2/§4 also shows
`v=1.45/1.26` and `v=1.46/1.27/2`, superseded by `1.50/1.29/2`.

**MINOR-3 — AC-5's permlevel clause was never amended.**
AC-5 requires a regression test "for a permlevel-restricted field". AC-1's own evidence
proves that state is unreachable on this site (auto-granted `Desk User`). An unsatisfiable
acceptance criterion should have been amended with the evidence rather than left open.
(Combined with MAJOR-1, this is why AC-5 cannot simply be "signed off".)

### NOTE

- **NOTE-1 — two fields added, not one.** PLAN §2 says "no schema change beyond … the single
  `enable_form_config` Check". `construction_settings.json` adds `vfc_form_config_section`
  (Section Break) **and** `enable_form_config` (Check) — 28→30 fields, hence the
  SCHEMA_FACTS delta of 2. The Section Break is UI grouping only; harmless, but the plan
  wording is imprecise.
- **NOTE-2 — VFC expands the site's three collapsible sections.** With the gate ON, 12 fields
  are on screen that are collapsed in the native form: exactly the members of the three
  sections marked `collapsible: 1` in `boq_item.json` (`sb_import_traceability`,
  `sb_quantity_revisions`, `sb_cost_estimation`). This is a **collapse-state** difference, not
  a visibility/permission reveal: those fields have `display:block` and `hide-control:false` in
  the native arm (height 0 because collapsed), and the `hide-control` set is identical in both
  arms. Worth telling the owner that enabling VFC changes collapsed-section behaviour.
- **NOTE-3 — D6 is not closed.** `sites/v16.localhost/site_config.json` has
  `"allow_tests": true`; the suite writes to the live site DB. Confirmed as declared.
- **NOTE-4 — retired Sections-editor code remains but is unreachable and safe.**
  `_renderSectionsTab` (`vite_layout_controls.js:1163`) early-returns because
  `#vfc-sec-list-${dtId}` no longer exists (line 1165 `if (!container) return;`), and the
  `#vfc-add-sec-btn-*` lookups are null-guarded (line 523). Declared limitation confirmed.
- **NOTE-5 — P0-1's "transaction" was nominal.** `P01_DELETE_EXECUTION_LOG.txt` shows the
  DELETE ran via `frappe.db.sql(...) + frappe.db.commit()`, and the `except`-block `rollback()`
  sat *after* the commit (self-documented as a no-op; `ImplicitCommitError` also learned).
  The real recovery path was the D3 backup, which was taken. Deletion is done and verified
  (8/0/8) — **do not re-run**.

---

## 4. Challenge items S1–S8

| # | Verdict | Evidence |
|---|---|---|
| **S1** | **CONFIRMED** (limited) | `form_layout_profile.py:35-68`. Exemption requires `for_user == frappe.session.user` **and** `not is_default` **and** `not is_system` **and** `not for_role`. No caller-controlled field flips it. DocPerm is System Manager = full, **All = read only**, so an ordinary user cannot update a profile to set `is_default`; their only write path (`save_my_native_layout`) hardcodes `sections_json/enabled/priority`. The 4 negative controls genuinely exercise the guard because the helper uses `insert(ignore_permissions=True)`. Residual: there is no `before_save` guard, so the protection rests on DocPerm write being withheld — a future `ignore_permissions=True` save of a caller-shaped profile would not be caught. Not exploitable now. |
| **S2** | **CONFIRMED** | Signature is `save_my_native_layout(doctype: str)` (`layout_api.py:293`). Verified the dispatch: `frappe.call` → `get_newargs()` (`frappe/__init__.py:1171-1193`) **silently drops** unsupported kwargs. Empirically called it with `for_user=Administrator, is_default=1, is_system=1, for_role=System Manager, priority=9999, sections_json(evil)` as a non-admin: row came back `for_user=<caller>, is_default=0, is_system=0, for_role=None, sections=[]`. |
| **S3** | **CONFIRMED** | `NATIVE_PROFILE_PREFIX`/`profile_name` at `layout_api.py:274,333`; priority 1000 at `:277`. Two throwaway users each reverted `Task`: rows `Task-__native__:userA` and `Task-__native__:userB`, both `priority=1000`, two distinct PKs. Cleaned up afterwards (0 rows). |
| **S4** | **QUALIFIED — needs owner acknowledgement** | D4 skips every doctype with a `Tab Break` (`vfc_layout_engine.js:162-170`). `Project` (4 breaks) and `Task` (2) both have `enabled=1 is_default=1` profiles that are now **inert**. This is a deliberate freeze and technically clean, but it silently withdraws VFC from the only two tabbed doctypes that had defaults. It should be listed as a known limitation for the owner, not just a code comment. |
| **S5** | **CONFIRMED** | `_clearSections` (`vfc_layout_engine.js:1086`) now removes inline `display` and `data-vfc-hidden` (`:1124-1127`), **and** cancels `_validationTimers`, `_retryTimers`, `_retryCounts` and disconnects observers for the key (`:1132-1155`). I initially suspected a revert→re-hide race; that hypothesis is **refuted by the timer cancellation**, so a revert cannot be re-blanked by a pending `_verifyAndRetry`. Only VFC sets `data-vfc-hidden`, so the un-hide cannot reveal a shell hidden by something else. |
| **S6** | **CONFIRMED** | `_vfcGateOpen()` (`:1447-1454`) returns `false` when `window.VFCisEnabled` is missing or throws; `VFCisEnabled()` (`vfc_config.js`) returns `true` only when `frappe.boot.vfc_enabled` is truthy; `boot.py:29-30` returns before setting it for Guest. Both attach hooks are gated (`:1458`, `:1470`). No fail-open path found. |
| **S7** | **CONFIRMED** | `SCHEMA_FACTS.md` diff is only: `Last verified` date, `28→30` counts, the two field rows (`vfc_form_config_section`, `enable_form_config`). No unrelated churn — the `--update` was bounded. |
| **S8** | **CONFIRMED** | All three D3 artefacts present; row list published before delete; dry run matched 202 with no DELETE/COMMIT; delete committed 210/202/8 → 8/0/8; resolver returns all 8. Live DB now `8/0/0`. **Not re-run.** |

---

## 5. Diff review

**Reviewed (this work item, 10 files, +575/−97):**

| File | +/− | What I checked |
|---|---|---|
| `construction/public/js/vfc_layout_engine.js` | +91/−48 | D4 tab skip + `Tab.prototype` patch removal and its unwinding; `hasNothingToRender` sentinel path; `_restoreVisibleFieldWrapper` early-return on `hide-control`; descendant guard; `_clearSections` un-hide + timer/observer cancellation; `_vfcGateOpen` |
| `construction/public/js/vite_layout_controls.js` | +64/−34 | Sections tab/pane removal; Revert relocation to the Layout pane (single id); P0-3 `unplacedNativeFields` merge; gate on attach; conditional revert alert |
| `construction/construction/api/layout_api.py` | +121/−0 | `save_my_native_layout` narrowness, permission checks, sentinel payload, per-user PK, idempotent update; `save_layout`/`_require_system_manager` untouched |
| `…/form_layout_profile/form_layout_profile.py` | +31/−6 | S1 exemption bounds; shared profiles still throw |
| `construction/tests/test_vfc_backend.py` | +214/−2 | 12 new tests; `tearDown` leak fix (direct delete fallback + commit) |
| `construction/boot.py` | +8/−0 | `cint()` default-OFF gate; Guest early return |
| `construction/public/js/vfc_config.js` | +23/−0 | Lazy `VFCisEnabled`, fail-closed |
| `…/construction_settings/construction_settings.json` | +15/−1 | `enable_form_config` Check default `"0"` (+ Section Break — NOTE-1) |
| `construction/hooks.py` | +3/−3 | three cache-buster bumps |
| `docs/ai/SCHEMA_FACTS.md` | +5/−3 | bounded regeneration (S7) |

**§3b foreign files excluded** — confirmed by name and left untouched:
`SESSION_MEMORY.md`, `dashboard/app.py`, `dashboard/tests/conftest.py`,
`orchestrator/candidates.py`, `orchestrator/engine.py`, `dashboard/tests/_test_root_state.py`,
`dashboard/tests/test_approval_token_producer.py`, `dashboard/tests/test_conftest_isolation.py`,
`orchestrator/engineering_control_contracts/`,
`orchestrator/tests/test_engineering_control_contracts*.py`,
`docs/ai/work-items/t3-engineering-control-wp1/`.
They were **not** reviewed and produce **no findings**.

Repo state is unchanged by my work: `git status --porcelain | wc -l` = **29**, before and after.

---

## 6. Checks executed (actual results)

```
git rev-parse --abbrev-ref HEAD            -> develop
git rev-parse HEAD                         -> 9796c5f27bc899867699b81d3e89d6dd5c62710f
git status --porcelain | wc -l             -> 29
python3 scripts/schema_drift_checker.py    -> "Schema facts match live DocType JSON." EXIT=0
python3 scripts/ai_context_check.py        -> Checks passed: 11 / failed: 0; ALL CHECKS PASSED EXIT=0
python3 scripts/lint_scope_metadata.py     -> PASS (19 DocTypes) EXIT=0
node --check (3 JS files)                  -> PASS x3
python3 -m py_compile (4 Python files)     -> PASS
bench --site v16.localhost run-tests --app construction \
      --module construction.tests.test_vfc_backend
                                           -> "Ran 51 tests in 2.412s" / "OK"
                                              (read the Ran/OK line, not the shell exit code)
```

Post-test pollution query — **after** the 51/51 run:

```
profiles=8  _Test_=0  personal=0
```

(`profile_name LIKE '\_Test\_%'` — **not** `name`; see the AC-1 evidence's own warning.)

Browser checks were run with a headless Chromium (Playwright, system Chrome) against
`http://v16.localhost:8000`, not the desktop relay — the paired browse profile was offline.
All V-check numbers in §2 are from those runs.

---

## 7. Environment state at handover

| Item | State |
|---|---|
| `Form Layout Profile` total | **8** |
| `_Test_*` rows (`profile_name`) | **0** |
| Personal (`for_user` set) | **0** |
| All 8 real profiles | `enabled=1 is_default=1` |
| Test users (`vfc.%`, `verifier.vfc.%`) | **0** |
| `enable_form_config` | **0** (shipped default) |
| `tabDefaultValue` row `hide_empty_read_only_fields` | **absent** (as before; site runs with it off) |
| `User Scope Context` | 7 pre-existing rows; my probe row deleted |
| Branch / HEAD / status | `develop` / `9796c5f` / 29 entries |
| `schema_drift` / `ai_context` / `lint_scope` | 0 / 11-of-11 / 0 |
| Commits made | **none** |

---

## 8. Verdict

- [ ] `VERIFIED_FOR_RELEASE`
- [x] **`CHANGES_REQUESTED`**
- [ ] `BLOCKED`

**Rationale.** No functional defect was found and nothing is blocked: P0-1, P0-2, P0-3, P1-1,
D2, D4 and the gate all behave as claimed, **V1–V5 pass at the shipped asset versions**, the
A/B hide-control sets are identical, all 51 tests pass, every static gate is green, and the
environment is clean.

The work is nevertheless not `VERIFIED_FOR_RELEASE` against the briefing's own decision rule
("**All** ACs met …"): **AC-5 and AC-6 each explicitly require a regression test, and neither
exists** (MAJOR-1, MAJOR-2). AC-5's permlevel clause is also unsatisfiable and unamended
(MINOR-3). These are coverage/traceability gaps, not behaviour bugs.

**To clear the verdict, the builder needs only:**
1. Commit a regression test that a `hide-control` wrapper is never stripped by
   `_restoreVisibleFieldWrapper` (an empty read-only field is sufficient; use a synthetic
   permlevel fixture or formally amend away the permlevel clause with AC-1's evidence).
2. Commit a P0-3 regression for `_mergeProfileWithNativeSections` (user-placed field not
   returned to native), ideally plus the drag→save→reload cycle that `IMPLEMENTATION.md` §3
   already flags as outstanding.
3. Record `REVIEW.md` (or correct `STATE.json`), and refresh `IMPLEMENTATION.md` §6.

**Owner waiver option.** If the owner accepts recorded manual browser evidence in place of
committed regression tests for P0-2/P0-3, then with items 1–3 reclassified as follow-ups this
review becomes `VERIFIED_FOR_RELEASE` on the evidence above. That is the owner's call, not the
verifier's — I state it so the decision is explicit rather than implied.

**Remaining human action:** complete the AC-5/AC-6 test commitments (or issue the waiver),
then commit. Nothing else in this work item requires a human.

> **§9 supersedes this section.** The three items above were completed by the builder on
> 2026-11-12 and re-verified independently; see **§9** for the resulting verdict.

---

## 9. Re-verification (2026-11-12, same verifier) — verdict revised

The builder addressed §8 items 1–3. Every claim was re-checked against the live repo; none
was accepted on assertion. **`VERIFIER_BRIEFING.md` remains untouched.**

### 9.1 What was independently confirmed

| Builder claim | My verification |
|---|---|
| `test_vfc_layout_regressions.js` — 11 tests, 11 pass | **Reproduced.** `node --test` → `tests 11 · pass 11 · fail 0` |
| Tests are **discriminating**, not vacuous | **Reproduced first-hand.** I copied the test into a sandbox tree and ran it against the **true pre-fix code taken from `git show HEAD:`** (which still contains 2 `classList.remove("hide-control")` sites). Result: **4 fail / 7 pass** — the 2 AC-5 `hide-control` assertions, the 2 AC-6 user-placement assertions, and *all seven behavioural controls still pass*, including "still adopts native fields the user has NOT placed" and "still restores a control Frappe has NOT hidden". The failure messages name the defect, so a future silent regression would be reported with cause. No repo file was touched to obtain this. |
| `node --check` ×4, `py_compile` | **PASS** |
| Backend 51/51 | **Reproduced.** `Ran 51 tests in 2.801s / OK` |
| `schema_drift` / `ai_context` / `lint_scope` | **exit 0 / 11-of-11 / exit 0** |
| `REVIEW.md` is a disclosure, not a fabricated sign-off | **Confirmed.** It states plainly that no separate reviewer agent reviewed `PLAN.md` pre-build, that architect and builder were the same session, lists the review events that did occur (R1–R4 plan/decision reviews, R5 = this verification), and refuses to issue a retroactive `APPROVED_FOR_BUILD`. `STATE.json` `separation_of_duties.reviewer` now reads "NOT PERFORMED pre-build … Disclosed in REVIEW.md rather than backfilled". This is the correct treatment under Standard §2. |
| `IMPLEMENTATION.md` §6 refreshed | **Confirmed.** P0-1/P0-2/P0-3/P1-1/D2/D4 all `DONE` with evidence pointers; the drag→save→reload cycle and D6 are recorded as `NOT DONE` rather than quietly claimed; cache-buster table corrected to `1.50/1.29/2`. |
| `PLAN.md` amended with dated notes | **Confirmed.** `AMENDED 2026-11-12` at the AC-5 permlevel clause (struck, with the AC-1 unreachability evidence) and `CLARIFIED 2026-11-12` at §2 (two fields, not one). Amendments are attributed and dated — no silent rewrite. |
| Worktree | `develop`, HEAD `9796c5f…` unchanged, 30 entries (29 + the new test). **No commits.** Foreign `t3-engineering-control-wp1` work untouched. |
| Environment | `profiles=8 · _Test_=0 · personal=0 · sentinels=0 · gate=0 · hide_empty row absent · probe/vfc users=0 · scope contexts=7 (pre-existing)` |

### 9.2 One new finding

**MINOR-4 — the new regression test is wired to no gate.**
`construction/tests/test_vfc_layout_regressions.js` is reachable only by the command in its
own header (`node --test construction/tests/test_vfc_layout_regressions.js`). No script in
`scripts/` and no CI hook invokes it — `node --test` appears in the repo only as a documented
convention (`PROFESSIONAL_ENGINEERING_STANDARD.md:302`). The same is true of the pre-existing
`construction/public/js/vfc_layout_engine_tests.js`, which this review already noted is
referenced by no runner.

This does not undo MAJOR-1: AC-5's literal requirement ("a regression test asserts…") is now
met by a committed, proven-discriminating test. But the *net* is still manual — the exact
failure mode that let the original defect survive is only narrowed, not closed. **Fix is one
line**: add the file to a checker's command list (e.g. alongside the gate commands in
`scripts/check_localization_gates.py`'s table, or a `scripts/run_js_tests.sh` called by
`preflight_check.sh`). Recorded as a follow-up, not a release condition.

### 9.3 AC-6's residual clause

The drag→save→**reload** browser cycle is still not performed. It is now honestly recorded
(`IMPLEMENTATION.md` §6: `NOT DONE`) rather than claimed. The defect mechanism P0-3 targeted —
the merge stripping user-placed fields — is covered by the committed discriminating regression,
and the merge is what runs on every load. The residual risk is the separate `_applyAndSave`
path, not the one that was defective.

### 9.4 Revised verdict

- [x] **`VERIFIED_FOR_RELEASE`**
- [ ] `CHANGES_REQUESTED`
- [ ] `BLOCKED`

**On the conditions that produced `CHANGES_REQUESTED` in §8:**

| Item | Disposition at re-verification |
|---|---|
| **MAJOR-1** (AC-5 regression test) | **CLOSED** — committed, discriminating, re-proven red against pre-fix code |
| **MAJOR-2** (AC-6 regression) | **CLOSED in substance** — committed discriminating merge regression; the reload cycle remains outstanding and disclosed |
| **MINOR-1** (missing `REVIEW.md`) | **CLOSED** — disclosed truthfully rather than fabricated |
| **MINOR-2** (stale `IMPLEMENTATION.md` §6) | **CLOSED** — refreshed, dated |
| **MINOR-3** (unsatisfiable AC-5 clause) | **CLOSED** — struck with dated evidence |
| **NOTE-1** (two fields, not one) | **CLOSED** — §2 clarified, dated |
| **MINOR-4** (new, see §9.2) | **OPEN — follow-up, not a release condition** |

**On S4 — verifier recommendation (the ruling is the owner's):** acknowledge D4's withdrawal of
VFC from `Project` and `Task` as a **known limitation**, and record it in the release notes.
Rationale: `enable_form_config` ships **OFF**, so no user is exposed to VFC at all today —
the withdrawal has zero current impact, and it only becomes live if the owner turns the gate
on. Revisiting tabbed support would mean un-freezing the frontend, which the owner deferred
explicitly. Revisit it then, without a `prototype` patch, if the gate is ever enabled for a
tabbed doctype.

**Remaining human action:** the owner's commit authorisation. S4 and the §9.2 wiring are
follow-ups, not blockers. Nothing else requires a human.

---

### Declared limitations — independently confirmed, not re-discovered

1. **D6 not closed** — confirmed (`allow_tests: true`); suite still writes to the live DB. (NOTE-3)
2. **Browser evidence predates D4** — confirmed; closed by §2 above at the final asset versions.
3. **F3 moot** — confirmed; `Project`/`Task` are skipped by D4. (AC-2, S4)
4. **`_renderSectionsTab` left as unreachable code** — confirmed unreachable and safe. (NOTE-4)
5. **No commit by design** — confirmed; HEAD unchanged, worktree still dirty.
