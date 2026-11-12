# VERIFIER BRIEFING — `vfc-gate-off-and-p0-fixes`

> **Audience:** an independent verification agent with **fresh context**.
> This document is self-contained. You are not expected to have read the chat,
> the plan, or the audit before starting — everything you need is here or is
> reached by a command in this file.
>
> **Your role:** independent final verifier (ARCHITECT → REVIEWER → BUILDER →
> **VERIFIER**). You did not build this. You must not build it.
> Per `AGENT_WORKFLOW.md` §3.2 the builder **cannot** mark its own work
> `VERIFIED_FOR_RELEASE` — that is the entire reason you exist.

---

## 0. Mission in one paragraph

A VFC (Form Layout Engine) work item fixed three P0 defects, one P1 defect, added
an off-by-default site gate, retired two dead subsystems, and deleted 202 stray
test rows from the live database. Everything below is **claimed** verified by
the builder. Your job is to independently confirm, refute, or qualify each claim,
with special attention to one gap the builder identified but could not close
(§5). Produce `FINAL_REVIEW.md` with a release-readiness verdict.

**Nothing has been committed.** The work sits as uncommitted modifications on
`develop`.

---

## 1. Environment (verify these before you trust anything else)

| Fact | Value |
|---|---|
| Repo root | `/home/mohamed/frappe-bench/apps/construction` |
| Bench root | `/home/mohamed/frappe-bench` |
| `bench` binary | `/home/mohamed/.local/bin/bench` (**not** `env/bin/bench`) |
| Branch | `develop` |
| Base commit | `9796c5f27bc899867699b81d3e89d6dd5c62710f` |
| Site | `v16.localhost` |
| Database | `_6d52b48c328b294e` |
| Python checks | `python3` (repo scripts) |
| DB access | `mysql -u root -proot -h localhost` |

**Startup — run these first and record actual output:**

```bash
cd /home/mohamed/frappe-bench/apps/construction
git rev-parse --abbrev-ref HEAD          # expect: develop
git rev-parse HEAD                       # expect: 9796c5f27bc899867699b81d3e89d6dd5c62710f
git status --porcelain                   # see §3 — mixed worktree
python3 scripts/schema_drift_checker.py  # expect: PASS, exit 0
python3 scripts/ai_context_check.py      # expect: 11 passed, 0 failed
```

If either checker fails, **stop and report** — do not proceed on drifted facts.

---

## 2. Authority and scope

**Authorised:** fix the three P0 defects + P1-1, gate VFC off by default, retire
the two dead subsystems, delete the 202 `_Test_` rows under D3 conditions.

**Explicitly NOT authorised / NOT in scope:**

* no commit, push, merge, or deploy — **you have no commit authority**
* no frontend rewrite (Phase 2+ deferred by the owner)
* no schema change beyond the single `enable_form_config` Check already added
* no change to the theme system (126 selectors, zero Frappe internals)
* no change to deprecated `modern_form_api.py` (ADR-008)
* no relaxation of `save_layout`'s `_require_system_manager()`

---

## 3. Working tree — READ THIS BEFORE `git diff`

**`git status` is mixed. Only part of it is this work item.**

### 3a. THIS work item (verify these)

| File | Δ lines | Change |
|---|---|---|
| `construction/public/js/vfc_layout_engine.js` | +91 / −48 | P0-2 hide-control · D2 gate · D4 tab skip + patch removal · `_clearSections` un-hide |
| `construction/public/js/vite_layout_controls.js` | +64 / −34 | P0-3 merge fix · D2 gate · D4 Sections editor retirement · Revert relocation |
| `construction/construction/api/layout_api.py` | +121 / −0 | new `save_my_native_layout` narrow endpoint |
| `construction/construction/doctype/form_layout_profile/form_layout_profile.py` | +31 / −6 | `before_insert` personal-profile exemption |
| `construction/tests/test_vfc_backend.py` | +214 / −2 | 12 new tests + 2 `tearDown` leak fixes |
| `construction/boot.py` | +8 / −0 | `bootinfo["vfc_enabled"]` |
| `construction/public/js/vfc_config.js` | +23 / −0 | `window.VFCisEnabled()` |
| `construction/construction/doctype/construction_settings/construction_settings.json` | +15 / −1 | `enable_form_config` Check, default `"0"` |
| `construction/hooks.py` | +3 / −3 | cache busters |
| `docs/ai/SCHEMA_FACTS.md` | +5 / −3 | regenerated after reviewed schema change |

### 3b. NOT this work item — **preserve, do not touch, do not flag as findings**

```
 M SESSION_MEMORY.md
 M dashboard/app.py
 M dashboard/tests/conftest.py
 M orchestrator/candidates.py
 M orchestrator/engine.py
?? dashboard/tests/_test_root_state.py
?? dashboard/tests/test_approval_token_producer.py
?? dashboard/tests/test_conftest_isolation.py
?? orchestrator/engineering_control_contracts/
?? orchestrator/tests/test_engineering_control_contracts*.py
?? docs/ai/work-items/t3-engineering-control-wp1/
```

These belong to a **different, concurrent task** (`t3-engineering-control-wp1`).
They were present before this work started. Including them in your diff review
or flagging them would be a false finding.

### 3c. Untracked docs from this work item

```
?? docs/ai/work-items/vfc-gate-off-and-p0-fixes/
?? docs/ai/VFC_AND_UI_OVERRIDE_AUDIT_2026-11-11.md
?? docs/ai/VFC_DECISION_KEEP_FIX_RETIRE_2026-11-11.md
?? docs/ai/MEMO_GM_VFC_DECISION_2026-11-11.md
?? docs/ai/ENG_REVIEW_OF_GM_REPLY_VFC_2026-11-11.md
```

(GM-side documents live outside the repo at
`/home/mohamed/frappe-bench/docs/ai/`.)

---

## 4. What is claimed — with evidence to re-check

Read these before forming a view; they are the builder's own records and may be
wrong. Verify, don't trust.

| # | Claim | Evidence file |
|---|---|---|
| **P0-1** | 202 `_Test_` rows deleted under D3 conditions; `210→8, 202→0, 8→8` | `evidence/P01_ROW_LIST_BEFORE_DELETION.md`, `P01_DRY_RUN_LOG.txt`, `P01_DELETE_EXECUTION_LOG.txt` |
| **P0-2** | `hide-control` never stripped; A/B showed managed-with-class `0→4`, matching the VFC-OFF arm | `evidence/P02_FIX_VERIFICATION.md` |
| **P0-3** | Merge no longer strips user-placed fields; old algorithm arm reproduces the defect | `evidence/P11_P03_VERIFICATION.md` |
| **P1-1** | Narrow `save_my_native_layout` endpoint; revert honest; root cause = creation blocked for non-admins | `evidence/P11_P03_VERIFICATION.md` |
| **D2** | Gate off by default; OFF → no button, no engine; ON → button + engine | `evidence/P02_FIX_VERIFICATION.md`, `IMPLEMENTATION.md` §4 |
| **D4** | Sections editor + `Tab.prototype` patch retired; Revert relocated | `evidence/D4_VERIFICATION.md` |
| **P0-1 root cause** | `tearDown`'s `except: pass` leaked `is_system=1` fixtures → fixed; full run now leaves zero pollution | `evidence/D4_VERIFICATION.md` §4 |

---

## 5. ⚠️ THE PRIMARY GAP — your most important task

**Browser evidence for P0-2, D2 and P1-1 was gathered on `PROJ-0002` *before*
D4 was implemented. D4 made VFC skip every tabbed doctype — and `Project` has
4 `Tab Break` fields.**

Consequence: **there is currently no browser observation of VFC actually
rendering anywhere.** The builder's browser evidence is stale with respect to
the final code state.

Why the builder could not close this: the throwaway non-admin user held
`Projects User`, which can read only `Project` and `Task` — **both tabbed**. The
non-tabbed VFC-managed doctypes (`BOQ Item`, `BOQ Header`, `BOQ Item Stage`,
`BOQ Structure`, `Variation Order`) were not readable by that account, and one
attempt on `User Scope Context` hit a record-level `403`.

### What you must do

Establish fresh browser evidence that VFC **does** render on a non-tabbed
doctype, and that P0-2 and D2 still hold there.

**Ready-made test subject — all preconditions verified:**

| Property | Value |
|---|---|
| Doctype | **`BOQ Item`** |
| Tab Break fields | **0** (so D4's skip does not apply) |
| permlevel > 0 fields | **none** |
| VFC profile | `BOQ Item-Default`, `enabled=1`, `is_default=1` |
| read-only, no-default fields assigned in profile | **16** (e.g. `line_total`, `overhead_amount`, `calculated_sell_price`, `import_batch`, `source_sheet_name`) |
| Records available | 34 — e.g. `BOQI-BOQ-2026-0274-0275` |
| Role granting read | **`Site Engineer`** (also: `Construction Owner`, `Project Manager`, `Read-Only`, `Accountant`, `System Manager`) |

**Create a throwaway user** (do not reuse production accounts):

```
role   : Site Engineer          # grants read on BOQ Item, BOQ Header, BOQ Structure,
                                # BOQ Item Stage, Variation Order — all non-tabbed
email  : your choice, e.g. verifier.probe@example.com
```

Set the password with `frappe.utils.password.update_password(user, pwd)` — a
direct `doc.password = ...` assignment does **not** produce a valid hash and
login returns **403**. Delete the account and its `Has Role` rows when done.

### Browser checks required

Run each against `BOQ Item` (gate ON for 1–3, OFF for 4).

| # | Check | PASS criterion |
|---|---|---|
| **V1** | VFC renders | `document.querySelectorAll('.vfc-le-cell').length > 0` **and** `[data-vfc-managed]` > 0. If both are 0 with the gate ON and a non-tabbed doctype, **D4 over-skipped — FAIL** |
| **V2** | P0-2 still holds | with `hide_empty_read_only_fields` ON: some element matches `.hide-control[data-vfc-managed]` (the fix preserves the class). **Zero** such elements = the fix is not reaching the field = **FAIL** |
| **V3** | D2 gate ON | `frappe.boot.vfc_enabled === true`, a `Form Config` button exists, engine attached |
| **V4** | D2 gate OFF | `enable_form_config = 0` → **no** `Form Config` button, `vfc_managed === 0`, native form renders (`.form-section` present) |
| **V5** | Negative controls | a **writable** empty field stays visible; a read-only field whose value is `0` stays visible (`is_null(0)` is false). If these hide, the fix over-reached — **FAIL** |

**To enable `hide_empty_read_only_fields` for V2:** it must be written the way
Frappe does it. A raw `frappe.db.set_value` on the Singles row does **not**
reach the client — the client reads `frappe.boot.sysdefaults`, built from
`tabDefaultValue` in `boot.py`, written only by
`System Settings.on_update()`. Use:

```python
frappe.db.set_default("hide_empty_read_only_fields", 1); frappe.db.commit(); frappe.clear_cache()
```

**Restore it to `0` and delete the `tabDefaultValue` row afterwards** — the
site ships with this setting off (JSON default is `"1"`, this site has `0`).

### Also re-confirm (cheap, do not skip)

```bash
# after ANY test run — must be identical to before
mysql -u root -proot -h localhost -N -e "
SELECT CONCAT('profiles=', COUNT(*),
       '  _Test_=', SUM(profile_name LIKE '\\_Test\\_%'),
       '  personal=', SUM(for_user IS NOT NULL AND for_user<>''))
FROM \`_6d52b48c328b294e\`.\`tabForm Layout Profile\`;"
# expect: profiles=8  _Test_=0  personal=0
```

---

## 6. Exact commands to run

```bash
cd /home/mohamed/frappe-bench/apps/construction

# --- static gates ---
python3 scripts/schema_drift_checker.py            # PASS, exit 0
python3 scripts/ai_context_check.py                # 11 passed, 0 failed
python3 scripts/lint_scope_metadata.py             # PASS, exit 0

# --- syntax ---
for f in construction/public/js/vfc_layout_engine.js \
         construction/public/js/vite_layout_controls.js \
         construction/public/js/vfc_config.js; do node --check "$f"; done
python3 -m py_compile construction/boot.py \
    construction/construction/api/layout_api.py \
    construction/construction/doctype/form_layout_profile/form_layout_profile.py \
    construction/tests/test_vfc_backend.py

# --- backend tests (51 expected) ---
/home/mohamed/.local/bin/bench --site v16.localhost run-tests \
    --app construction --module construction.tests.test_vfc_backend
# expect: Ran 51 tests ... OK

# --- D6 guard sanity (builder's rule: key on SITE, not database name) ---
grep -rn "test_" scripts/ | head    # informational only; D6 is a separate ticket
```

**Known environment caveat:** this test run reports `TEST_EXIT=0` from the
shell even when the suite fails (the exit code captured is `tail`'s). Read the
`Ran N tests ... OK` / `FAILED (errors=N)` line, **not** the exit code. The
builder hit exactly this: a run printed `TEST_EXIT=0` while actually being
`FAILED (errors=12)`.

---

## 7. Specific things to challenge (the builder wants push-back here)

| # | Item | Why it deserves scrutiny |
|---|---|---|
| **S1** | `form_layout_profile.py` `before_insert` relaxed | A **permission rule change**. It now allows a non-System-Manager to insert a row when `for_user == caller AND is_default=0 AND is_system=0 AND for_role` empty. Confirm the exemption cannot be widened by any caller-controlled field, and that shared profiles (default/role/system/other-user) still throw. 4 negative-control tests claim this — verify they actually exercise the guard. |
| **S2** | `save_my_native_layout` accepts only `doctype` | Assert the signature yourself; confirm no path lets a caller set `for_user`, `for_role`, `is_default`, `is_system`, or `sections_json`. |
| **S3** | `profile_name = "__native__:{user}"` | Required because `autoname = format:{reference_doctype}-{profile_name}`. Confirm two users can both revert the same doctype without a PK collision. |
| **S4** | D4 skips **all** tabbed doctypes | This silently removes VFC from `Project` and `Task`, which have enabled default profiles. Is that acceptable, or should tabbed doctypes be listed as a known limitation for the owner? |
| **S5** | `_clearSections` now removes `data-vfc-hidden` | Its doc comment *always* claimed this but the code never did it. Confirm the new un-hide cannot reveal shells that should stay hidden. |
| **S6** | Engine "fail-closed" gate | If `vfc_config.js` fails to load, `_vfcGateOpen()` returns `false`. Confirm no path fails **open**. |
| **S7** | `SCHEMA_FACTS.md` regenerated | Standard §95 forbids blind `--update`. Confirm the diff is purely the `enable_form_config` addition. |
| **S8** | P0-1 deletion | Already executed and irreversible. Confirm the three D3 artifacts exist and that counts are `8 / 0 / 0`. Do **not** attempt to re-run the delete. |

---

## 8. STOP CONDITIONS — hard limits

**Stop immediately and report if you observe any of:**

1. `profiles` ≠ 8, or any `profile_name LIKE '_Test_%'` row exists after a test run
2. Any of the 8 real profiles missing, disabled, or `is_default` cleared
3. `enable_form_config` not `0` at the end
4. Any `tabUser` matching `vfc.%` remaining
5. A test run that does not report `Ran 51 tests ... OK`
6. Schema drift or context-check failure
7. Any attempt — yours or required by the task — to commit, push, or migrate

**You must NOT:**

* commit, push, merge, stash, reset, or checkout anything
* run `bench migrate` (already run once and verified; a second run is out of scope)
* delete or modify the 8 real profiles
* relax `_require_system_manager()` on `save_layout`
* "fix" anything you find — **report it, do not repair it**
* include §3b files in your findings

**Environment cleanup you must perform when finished:**

```python
# gate back to default
doc = frappe.get_single("Construction Settings"); doc.enable_form_config = 0
doc.save(ignore_permissions=True); frappe.db.commit()
# remove your throwaway user + its profiles
frappe.db.delete("Form Layout Profile", {"for_user": "<your user>"})
frappe.db.delete("Has Role", {"parent": "<your user>", "parenttype": "User"})
frappe.db.delete("User", {"name": "<your user>"}); frappe.db.commit(); frappe.clear_cache()
# restore hide_empty_read_only_fields to 0 and drop its DefaultValue row
```

---

## 9. Deliverable — `FINAL_REVIEW.md`

Create at
`docs/ai/work-items/vfc-gate-off-and-p0-fixes/FINAL_REVIEW.md` with:

```markdown
# FINAL REVIEW — vfc-gate-off-and-p0-fixes
Verifier: <identity>   Date: <UTC>   Base commit: 9796c5f...
Worktree at review: <clean / dirty — list>

## 1. Plan-conformance matrix
| Acceptance criterion (PLAN.md §7) | Met? | Evidence you produced |
(AC-1 … AC-10 — each must be answered; AC-7 needs the V3/V4 browser results)

## 2. Gap closure (§5 of the briefing)
V1 … V5 results, with the doctype and user you used.

## 3. Findings by severity
BLOCKER / MAJOR / MINOR / NOTE — each with file:line and how you confirmed.
If you find none in a class, say so explicitly.

## 4. Challenge items S1–S8
For each: CONFIRMED / REFUTED / QUALIFIED, with evidence.

## 5. Diff review
Files reviewed, and confirmation that §3b foreign files were excluded.

## 6. Checks executed
Exact commands + actual results (not "as expected").

## 7. Environment state at handover
profiles / _Test_ / personal / test users / enable_form_config / hide_empty_read_only_fields

## 8. Verdict
[ ] VERIFIED_FOR_RELEASE   [ ] CHANGES_REQUESTED   [ ] BLOCKED
Remaining human action:
```

---

## 10. Decision rule

| Condition | Verdict |
|---|---|
| All ACs met, V1–V5 pass, S1–S8 confirmed or reasonably qualified, zero pollution, all checks green | **`VERIFIED_FOR_RELEASE`** |
| Any BLOCKER, any failed V-check, pollution detected, or a check red | **`CHANGES_REQUESTED`** — return to builder with file:line |
| Environment unusable, or a STOP CONDITION triggered | **`BLOCKED`** — report, do not work around |

**Builder's known and declared limitations** (do not rediscover as new findings;
confirm or refute them):

1. D6 (test-to-production isolation) is **not** closed — the suite still writes
   to the live site DB. Separate ticket.
2. Browser evidence for P0-2/D2/P1-1 predates D4 — **this is §5, your job.**
3. F3 (tabbed-doctype support) was never reproduced as a defect; it is now moot
   because D4 skips tabbed doctypes entirely.
4. `_renderSectionsTab` and its helpers remain in the source as unreachable code
   (all entry points early-return on the absent container). Deliberate: D4 is a
   *freeze*, not a rewrite.
5. No commit has been made, by design.

---

*Briefing prepared for independent verification. Builder: do not edit this file
after handing it over — if you disagree with a framing, say so in
`FINAL_REVIEW.md` instead.*
