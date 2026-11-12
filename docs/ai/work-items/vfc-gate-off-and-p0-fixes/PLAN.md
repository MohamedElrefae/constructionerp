# PLAN — VFC Gate Off by Default + Three P0 Fixes

| | |
|---|---|
| **Work item** | `vfc-gate-off-and-p0-fixes` |
| **Author role** | Architect |
| **Date** | 2026-11-12 |
| **Base ref** | `develop` |
| **Base commit** | `9796c5f27bc899867699b81d3e89d6dd5c62710f` |
| **Authority** | Owner/GM authorisation: `docs/ai/GM_EXECUTION_AUTHORISED_VFC_2026-11-11.md` |
| **Prior evidence** | `docs/ai/VFC_AND_UI_OVERRIDE_AUDIT_2026-11-11.md` (F1–F22) |

---

## 1. Objective

Ship the GM-approved **Option C**: gate the Form Layout Engine (VFC) off by default,
fix the three confirmed P0 defects, keep the backend, and retire the two dead
subsystems (Sections editor, tabbed-doctype support).

Execution is gated. **No fix is written until the Phase 0 browser tests run**, because
two findings were marked `LIKELY` and one has since been reclassified.

## 2. Non-goals

- No frontend rewrite (Phase 2+ explicitly deferred by the GM).
- No schema change beyond Phase 1's `enable_form_config` site setting.

  > **CLARIFIED 2026-11-12 (architect, after independent review NOTE-1).**
  > This means two DocType fields, not one: `vfc_form_config_section`
  > (Section Break, UI grouping only) **and** `enable_form_config` (Check,
  > default `"0"`). 28 → 30 fields, which is the entire `SCHEMA_FACTS.md` delta.
  > No data migration, no backfill, no DDL beyond the Singles row.
- No extension of VFC to new doctypes.
- No commit, push, deploy, or migration without separate owner authorisation.
- No change to the theme system (126 selectors, zero Frappe internals — carve-out confirmed).
- No change to the React `modern_form_api.py` (deprecated, ADR-008).

## 3. Affected paths

| Path | Change |
|---|---|
| `construction/public/js/vfc_layout_engine.js` | **P0-2** — stop stripping `hide-control`; skip-guard on `disp_status` |
| `construction/public/js/vite_layout_controls.js` | **P0-3** — destructive merge at 1362–1367; **D4** retire Sections editor |
| `construction/construction/api/layout_api.py` | **P1-1** — `delete_my_personal_layout` (224–248) never matches |
| `construction/hooks.py` | **D2** — register `enable_form_config` gating; bump `?v=` cache busters |
| `construction/construction/doctype/construction_settings/` | **D2** — new `enable_form_config` Check, default **OFF** |
| `construction/public/js/vfc_config.js` | **D2** — gate flag plumbed to boot |
| `docs/ai/work-items/vfc-gate-off-and-p0-fixes/` | this work item |

**No DocType JSON change** for P0-1/P0-2/P0-3. P0-1 is a data operation, not code.

## 4. Schema / migration impact

- **P0-1 (data):** deletes 202 `_Test_*` rows from `tabForm Layout Profile` in site
  `_6d52b48c328b294e`. **Destructive.** Governed by D3's three conditions (§7).
- **D2 (schema):** one new `Check` field on `Construction Settings`. Additive, idempotent,
  no backfill, no DDL beyond the column. Safe on repeated migration.
- **D6 (guard):** CI-only; no runtime effect.

## 5. Permission and scope-context impact

- **P0-2** is a *permission display* defect: `_restoreVisibleFieldWrapper`
  (`vfc_layout_engine.js:853-879`) strips the `hide-control` class Frappe applies when
  `disp_status === "None"`.
- `disp_status === "None"` arises in **two** cases — permlevel restriction **and**
  `hide_empty_read_only_fields` (default `"1"`). Both must close.
- **Fix rule (supersedes the GM's step 3): never strip `hide-control` on any field.**
- Scope Context is **not** touched. No `permission_query_conditions` change.

## 6. Findings in scope

| Label | Defect | Status at plan time |
|---|---|---|
| **P0-1** | 202 `_Test_*` rows live in production DB | CONFIRMED (SQL) |
| **P0-2** | `hide-control` stripped → field revealed | Mechanism CONFIRMED; **exploitability reclassified — see §9** |
| **P0-3** | Section editor destroys user arrangement (`vite_layout_controls.js:1362-1367`) | CONFIRMED (live DB: 5 sections with 0 fields) |
| **P1-1** | "Revert to Default" reports success while doing nothing | CONFIRMED (`layout_api.py:224-248`) |
| **F3** | Tabbed-doctype support | **UNVERIFIED — do not fix until reproduced** |
| **D4** | Sections editor + tabbed-doctype are dead subsystems | CONFIRMED dead (0 role/personal profiles) |

## 7. Acceptance criteria

**Phase 0 — verification gate (must pass before any fix is written)**

- [ ] **AC-1** Project browser test run with a user holding `Projects User` **without**
      `Desk User`; result recorded as evidence, PASS or FAIL.
- [ ] **AC-2** F3 reproduced on a doctype with real tabs, or explicitly struck with evidence.
- [ ] **AC-3** P0-1 row list **published before** deletion; backup taken; dry-run SELECT
      logged; then delete under a transaction.
- [ ] **AC-4** Post-delete count of `_Test_*` rows = 0; real profiles (8 doctypes) intact.

**Phase 1 — fixes**

- [ ] **AC-5** P0-2 fix: no field's `hide-control` is ever stripped by VFC. Regression test
      asserts the class survives for a permlevel-restricted field **and** an empty
      read-only field.

      > **AMENDED 2026-11-12 (architect, after independent review MINOR-3).**
      > The permlevel clause is **unsatisfiable on this site** and has been struck
      > rather than left open: `frappe/permissions.py:35-40,566-567` auto-grants
      > `Desk User` to every System User, ERPNext core grants `Desk User`
      > permlevel-1 read on `Project`, and the full sweep across all 9 VFC-managed
      > doctypes found **0 reachable permlevel gates** (see
      > `evidence/AC1_AC2_PROJECT_BROWSER_TEST.md` §2, confirmed independently in
      > `FINAL_REVIEW.md` AC-1). No test can construct that state.
      >
      > AC-5 therefore now requires: a regression asserting `hide-control`
      > survives for an **empty read-only field** (the reachable case), committed
      > as a test. Delivered as
      > `construction/tests/test_vfc_layout_regressions.js`.
- [ ] **AC-6** P0-3 fix: user-placed fields survive save/load. Regression asserts a field
      placed by the user is still present after reload.
- [ ] **AC-7** `enable_form_config` default **OFF**; with it off, no button injection and
      no engine attachment occurs (browser-verified).
- [ ] **AC-8** Per-user opt-in + `__native__` sentinel makes P1-1 revert actually work.
- [ ] **AC-9** Cache busters bumped for every modified JS file; loaded browser file verified.

**Release**

- [ ] **AC-10** Builder does **not** mark its own work `VERIFIED_FOR_RELEASE` — independent
      verifier produces `FINAL_REVIEW.md`.

## 8. Exact validation commands

```bash
# From /home/mohamed/frappe-bench/apps/construction
python3 scripts/schema_drift_checker.py          # expect EXIT=0
python3 scripts/ai_context_check.py              # expect EXIT=0, 11 checks
python3 scripts/lint_scope_metadata.py           # if DocType JSON touched

# Backend tests (site must be named explicitly — never assume a default)
bench --site v16.localhost run-tests --app construction --module construction.tests.test_vfc_backend

# Offline suite
/home/mohamed/frappe-bench/env/bin/python -m pytest tests_offline -q
```

**Environment note:** `bench` is at `/home/mohamed/.local/bin/bench` (uv tool venv), not
`env/bin/bench`. Site is `v16.localhost`, DB `_6d52b48c328b294e`.

## 9. Assumptions and open questions

**A1 — P0-2 reclassified as LATENT, not live (2026-11-12 evidence).**
Server-side sweep of every enabled non-guest user (`vfc_perm_check5.py`):

```
Users with Project permlevel-0 READ but NOT permlevel-1 read: 0
role combos granting Project permlevel-0 read: (ProjectsManager, ProjectsUser, DeskUser) -> 5
```

All 5 users who can read Project already hold `Desk User`, which grants permlevel-1 read.
`Project User` child table has **zero rows site-wide**. So the mechanism is CONFIRMED but
**no user currently sits in the gap**. The work order's "Live — Project confirmed affected
today" is accurate about the *code path* and inaccurate about *current exposure*.

→ **Consequence:** the browser test cannot be reproduced with an existing user. AC-1
requires creating a throwaway user (`Projects User` only), running the test, then deleting
the user. This is a controlled reproduction, not a production user.

**A2 — D6 guard must key on site, not database name.**
Dev benches use hash-named DBs (`_6d52b48c328b294e`) with no `test_` suffix. Keying on DB
name would fail every normal run. Implementation keys on site/`site_config.json`.

**O1 — Is P0-2 worth fixing if it is not live?**
Recommendation: **yes.** The gap opens the moment anyone creates a `Projects User` without
`Desk User` — the natural role assignment for a field engineer. Fix cost is one line; the
alternative is a latent permission defect waiting for a routine user creation.

**O2 — F3 tabbed-doctype.** Unverified. Per the GM's own instruction: *do not fix it until
reproduced.* If AC-2 fails to reproduce, F3 is struck with evidence.

## 10. Rollback approach

| Change | Rollback |
|---|---|
| P0-1 row deletion | Restore from the pre-deletion backup taken under D3. **No automatic rollback path — backup is the only one.** |
| P0-2 / P0-3 code | Revert the commit; cache buster bump makes the old asset unreachable immediately. |
| D2 `enable_form_config` | Set the checkbox OFF — no code rollback needed. Field is additive; leaving it is harmless. |
| Throwaway test user | `frappe.delete_doc("User", ...)` + confirm `Has Role` rows gone. |

## 11. Validation commands run at plan time (startup evidence)

| Command | Result | Exit |
|---|---|---|
| `git rev-parse --abbrev-ref HEAD` | `develop` | 0 |
| `git rev-parse HEAD` | `9796c5f27bc899867699b81d3e89d6dd5c62710f` | 0 |
| `git status --porcelain` | 4 modified + 12 untracked — **unrelated work present, must preserve** | 0 |
| `git rev-list --left-right --count origin/develop...HEAD` | `0 0` (in sync) | 0 |
| `python3 scripts/schema_drift_checker.py` | `Schema facts match live DocType JSON.` | **0** |
| `python3 scripts/ai_context_check.py` | `Checks passed: 11 / failed: 0 — ALL CHECKS PASSED` | **0** |

**Dirty-worktree disclosure:** `dashboard/app.py`, `dashboard/tests/conftest.py`,
`orchestrator/candidates.py`, `orchestrator/engine.py`, `SESSION_MEMORY.md` are modified
and `orchestrator/tests/*`, `dashboard/tests/*` are untracked. **These belong to another
task (`t3-engineering-control-wp1`) and are out of scope.** They must not be committed with
this work item.

---

*Architect — 2026-11-12. Submitted for independent review.*
