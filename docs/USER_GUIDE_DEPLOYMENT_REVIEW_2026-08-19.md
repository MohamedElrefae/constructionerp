# Historical Consultant Review — Superseded by 2026-08-20 Sign-Off

**Original review date:** 2026-08-19  
**Remediated and revalidated:** 2026-08-20
**Subject:** Original comparison of `docs/USER_GUIDE.md` (v1.2) vs. actual `construction` app code; current guide is v1.3
**Method:** Direct code/schema/JS/API inspection (no reliance on stored agent reports) + live test execution on the bench.
**Verdict:** ✅ **RELEASE-READY.** All findings in §4 were remediated and revalidated on 2026-08-20. The original observations and results below are retained as the audit baseline; see §7 for the current state.

> **Historical audit — not the deployment decision.** The red findings and failed-test results below describe the 2026-08-19 baseline only. Use [DEPLOYMENT_SIGN_OFF_2026-08-20.md](DEPLOYMENT_SIGN_OFF_2026-08-20.md) as the single authoritative handoff and deployment decision.

---

## 1. What Was Verified (and How)

| # | Claim | Verification method |
|---|-------|---------------------|
| 1 | All DocTypes/fields named in the guide exist | Read every DocType `.json` (schema fields, options) in `construction/construction/doctype/` |
| 2 | Status workflows (BOQ Header, VO, Cost Analysis) | Read Select options in JSON + controller logic in `.py` |
| 3 | Cascade blocker + grid blocker behavior | Read `boq_filters.js`, `ct_link_control.js`, doctype JS files |
| 4 | VO lifecycle (FIDIC rule, idempotency, PDF gate, P0-1) | Read `variation_order.py`, `vo_line.py`, `quantity_revisions.py` |
| 5 | Cost engine math + supersede/cancel logic | Read `boq_cost_analysis.py`, `resource_price_service.py` |
| 6 | Cost DB endpoints + idempotency | Read `cost_database_api.py`, `cost_database_service.py` |
| 7 | Report layer (5 functions) | Read `boq_report_service.py` |
| 8 | VFC endpoints + UI | Read `layout_api.py`, `vite_layout_controls.js` |
| 9 | Cache-bust versions (§12.2) | Diffed against `hooks.py` |
| 10 | Test-suite claims (Appendix A) | **Executed live** via `bench run-tests` (below) |
| 11 | Deployment state | Inspected bench sites, installed apps, DB tables, feature flags |

---

## 2. Section-by-Section Guide ⇄ Code Sync

| Guide § | Claim | Code status |
|---------|-------|-------------|
| §1.1 Enable Scope Context (+ 4 dimensions) | ✔ | Fields exist: `enable_scope_context`, `enable_scope_company/cost_center/project/department` |
| §1.2 Scope selectors auto-populate | ✔ | `scope_context_ui.js` + `set_scope_context` API persist to `User Scope Context` |
| §1.3 Scope Filter Exclusions (add `Project`) | ⚠️ | Exclusions honored by `scope_query.py` (list SQL only). **Does NOT relax the `BOQ Header.validate()` enforcement** — see Finding F2. The guide's promise that adding `Project` lets you "switch projects freely" is only partially true. |
| §1.4 Scope drift alert + Error Log | ✔ | Exact message in `boq_filters.js:522`; `log_boq_scope_drift` writes `"BOQ Scope Drift"` Error Log |
| §2.1 BOQ Header New (Title/Project/BOQ Type) | ⚠️ | Fields exist. **But** `project` is force-set from User Scope Context on every New header and throws if none exists — behavior works only if scope was set in §1. Manual project selection is overwritten. |
| §2.2 WBS Tree inline rollup | ✔ | `boq_structure_tree.js` renders item count + totals per node |
| §2.3 Lock: Draft→Pricing→Frozen→Locked | ✔ | `VALID_TRANSITIONS`, `locked_by`/`locked_date` set in `boq_header.py`; baseline revisions auto-created |
| §3.1/3.2 Structure group/leaf | ✔ | `BOQ Structure` fields `parent_structure`, `is_group`, `wbs_code` |
| §3.2 leaf-only validation message | ✔ | Exact message at `boq_item.py:59` |
| §3.3 rollup columns | ✔ | `item_count`, `total_contract_value`, `total_budgeted_cost` on JSON + list JS |
| §4.1 BOQ Item — **Title** field | ❌ | **No `title` field on BOQ Item.** The free-text field is `cost_item` ("Cost Item (Placeholder)"). A new tester cannot find "Title" — see Finding F3. |
| §4.2 Breadcrumb | ✔ | `frm.dashboard.set_headline(breadcrumb.join(" → "))` in `boq_item.js` |
| §4.3 Quick Create Leaf Structure | ✔ | `boq_item.js` button "Create Leaf Structure" + dialog |
| §5.1 Onboarding banner | ✔ | `boq_item_stage.js` + exact localStorage key `ct_boq_stage_onboarding_dismissed` |
| §5.2 BOQ Item Stage cascade | ✔ | Fields exist; cascade UI verified |
| §6 Cascade blocker states (red/orange) | ✔ | CSS + `__ct_boq_blocked` engine; master form + tests reference it |
| §7 Transaction grid blocker (8 doc types) | ✔ | `boq_filters.js` `childTables`; gate fields via install.py custom fields (verified in DB) |
| §7.1 gate matrix | ✔ | expense `Direct`, `is_progress_billing`, Timesheet designation — all match |
| §7.3 collapsed-row dim / §7.4 project re-block | ✔ | implemented; known framework limitation disclosed in Appendix B |
| §8 VO lifecycle (all 5 parts) | ⚠️ | Server logic ✔ (statuses, FIDIC 25%, justification, PDF upload, P0-1, idempotency, create structure/item). **But** the automated test suite claiming "27/27 VO" is RED (Finding F1). **And** §8.4 "omitted item hidden from dropdowns (`exclude_zero_revised` active)" is false for the standard UI (Finding F5). |
| §9 Cost Estimation Engine | ✔ | Math, supersede/restore, est-cost refresh, non-template message, rate priority PI→PO→History→ItemPrice — all verified; 17/17 tests pass |
| §9.2 permissions | ✔ | Price History: SM full, Owner/PM read-only, Site Engineer none |
| §10 Cost Database (Phase 2) | ✔ | 3 endpoints verified; idempotency + Arabic headers; 10/10 tests pass |
| §11 VFC — pencil icon | ⚠️ | Button is **grid icon + "Form Config"**, not a pencil (Finding F6). Backend 39/39 tests pass. |
| §12.1 Settings reference | ✔ | All listed settings/fields exist |
| §12.2 cache-bust versions | ❌ | 4 of 5 version numbers are stale (Finding F4) |
| §12.3 Scope Drift audit | ✔ | verifed (see §1.4) |
| §13 Feature checklist | ⚠️ | Mostly ✔; the VO omit-hidden item + cost timer ✔; verified the parts noted above |

---

## 3. Live Test Execution Results (Appendix A claims)

Executed on the `localhost` site (DB `_6d52b48c328b294e`).

| Suite (guide's claim) | Claimed | Run result | Status |
|-----------------------|---------|------------|--------|
| Cost Estimation Engine | 17/17 | 17 tests ran | ✅ PASS |
| Cost Database API | 10/10 | 10 tests ran | ✅ PASS |
| VFC Backend | 39/39 | 39 tests ran | ✅ PASS |
| VO Quantity Revision ("27/27") | passed | `test_variation_orders`: **23 tests, 22 errors** | ❌ FAIL |
| Quantity Revisions (part of VO suite) | — | `test_quantity_revisions`: **30 tests, 30 errors** | ❌ FAIL |
| Gate Transitions ("All passing") | passed | `test_transaction_validation`: **13 tests, 13 errors** | ❌ FAIL |
| Scope Context ("All passing") | passed | manual runner (17 registered tests) — not executable under `bench run-tests` | ⚠️ not reproducible |
| Link Queries (referenced by VO suite) | — | `test_boq_link_queries`: **8 tests, 8 errors** | ❌ FAIL |

**Bottom line:** 3 doc/UI-heavy suites are green and were not the source of the reported numbers; 4 suites are red and their guide/advisory claims are stale.

---

## 4. Findings (ordered by severity)

### 🟥 F1 — CRITICAL: Scope-context enforcement breaks BOQ Header creation and 4 test suites

`construction/construction/doctype/boq_header/boq_header.py:21` `sync_project_from_scope_context` (added in commit `59db661`) **unconditionally** throws:

> "Project comes from Scope Context. Set a Project in the top bar before creating a BOQ Header."

when the current user has no `User Scope Context` with a project — for **any** user including Administrator, and **even when `enable_scope_context = 0`** in Construction Settings (current DB state). Compare `overrides/scope_enforcement.py` and `variation_order.py`, which both correctly gate on the flag and skip Administrator.

Consequences:
1. `test_variation_orders`, `test_quantity_revisions`, `test_boq_link_queries` fail en-masse (their setup creates BOQ Headers without a scope record; the cost-engine suite passes only because *it* seeds a `User Scope Context` in `setUp`).
2. A brand-new user on a fresh site **cannot create a BOQ Header from the UI at all** until an Administrator (or the user through the top-bar, which only renders when scope is enabled) creates a scope record.
3. Manual project selection on the form is overridden by the scope project — contradicting GUIDE §2.1 ("select your project").

**Required fix (pick one):**
- (A) Gate the throw on `enable_scope_context` and `skip Administrator` + allow the doc's own `project` to take precedence when scope context is disabled — this restores the guide's described behavior and unbreaks the tests. *(Recommended.)*
- (B) Keep the strict behavior but update the guide §2.1 + §1.3 to say BOQ Headers *require* a scope project, and fix the 4 test suites to seed scope context records.

### 🟥 F2 — HIGH: Guide §1.3 promise is misleading

§1.3 says adding `Project` to Scope Filter Exclusions lets users "switch projects freely" and resolves the permission error on the BOQ Header new form. The exclusion is applied only in the SQL query layer (`scope_query.py`); the `validate()` enforcement in Finding F1 is **not** affected by it. A user who adds `Project` to exclusions still cannot create a BOQ Header with a project different from their scope (or without any scope). Guide must be reworded (or code relaxed per F1-A).

### 🟥 F3 — HIGH: Guide §4.1 references a nonexistent "Title" field on BOQ Item

BOQ Item has no `title` field; the free-text description field is `cost_item` ("Cost Item (Placeholder)"). A first-time tester looking for "Title:" will not find it. Update guide to use **Cost Item** (or rename the UI label).

### 🟠 F4 — MEDIUM: Cache-bust table §12.2 is stale (4/5)

| File | Guide says | hooks.py actual |
|------|-----------|-----------------|
| `modern_theme.css` | `?v=2.5.6` | `?v=2.5.7` |
| `ct_link_control.js` | `?v=13` | `?v=16` |
| `boq_filters.js` | `?v=5` | `?v=6` |
| `filter_fix.js` | `?v=7` | `?v=11` |
| `scope_context_form_defaults.js` | `?v=3` | `?v=3` ✔ |

Update the guide to the current numbers (they will bump again with each deploy; consider removing the table and pointing at hooks.py as the source of truth).

### 🟠 F5 — MEDIUM: §8.4 "omitted item hidden from dropdowns" is not true in the UI

`exclude_zero_revised` exists only as an **opt-in API filter** (`boq_link_queries.get_boq_items`), driven by nothing in the standard UI. Neither `boq_filters.js` (transaction grids) nor `variation_order.js` (VO lines) pass it. In the normal UI, an omitted BOQ Item (revised qty = 0) still appears in item dropdowns. The guide should say the omission is filtered only via the API flag, or the JS queries should pass `exclude_zero_revised: 1` by default.

### 🟠 F6 — LOW: VFC trigger is not a "pencil icon"

§11.1 & the checklist say "click the pencil icon". The actual control is a **grid icon button labeled "Form Config"** (`add_inner_button` in `vite_layout_controls.js`). Update guide wording to "the **Form Config** button (grid icon, top-right)". Also §11.2 says "Current Sections tab" but the panel tabs are **Layout / Fields / Sections / Presets** — align names.

### 🟡 F7 — LOW (schema notes, not blockers)
- BOQ Quantity Revision uses `delta_qty` ("Delta Quantity"); guide says "Delta = 26" (§8.2 step 10) — keep column name in guide to avoid confusion.
- Cost Analysis status field is `analysis_status` and Arabic field is `description_ar` — guide's prose already matches.
- `test_scope_context.py` is a manual runner (T-001…T-017), not a `unittest` class; the guide's "14 tests" count is off (17 registered).

---

## 5. Deployment Readiness (current live state)

| Check | Result |
|-------|--------|
| Bench apps registered | frappe 16.18.1, erpnext 16.18.3, construction 0.0.1 ✔ |
| Sites | `localhost`, `v16.localhost` (same DB `_6d52b48c328b294e`, `allow_tests`, `developer_mode`) |
| Assets | `sites/assets/construction` symlinked to app public dir; CSS/JS/dist present ✔ |
| DB tables with data | BOQ Header 13, BOQ Item 25, VO 24, Form Layout Profile 86 |
| Gate custom fields (`expense_category`, `is_progress_billing`) | Present in all 8 child doctypes ✔ |
| Scope Settings (live) | Scope Context **OFF**, Cascade On, Variation Orders On, Scope dims: Co/CC/Proj on, Dept off |
| Git | clean working tree on `develop` |

**Headline deployment caveat:** with `enable_scope_context = 0` and no scope record for the tester login, **step §2.1 (create BOQ Header) will fail** with the Setting message from F1 unless the tester first enables Scope Context and sets a project in the top bar (as §1.1–1.2 instruct). The guide's own sequence is self-consistent **if** the tester performs §1 exactly; but this is fragile and one misstep (e.g., enabling the flag but not selecting a project) produces a dead-end with no visible path forward.

---

## 6. Recommended Actions (before handing to users)

1. **Fix F1** – gate `sync_project_from_scope_context` on `enable_scope_context` + Administrator bypass, honoring an explicitly-set `project` when scope is off. This alone restores the 4 red suites.
2. **Fix F2, F3, F5** – update the guide wording (Project selection, `cost_item`, omit/`exclude_zero_revised`), or make the code/UI match the guide. Prefer updating the guide to document real behavior, and optionally pass `exclude_zero_revised` by default.
3. **Fix F4, F6** – refresh cache-buster numbers and the VFC button naming.
4. **Re-run** the 7 suites (expect all green) and re-run the Playwright VO manual test on the fresh scope-enabled flow.
5. **Smoke-test a first-run user** on a fresh site: login → §1 enable scope → pick company/project → §2 create+lock BOQ. Confirm no dead-ends.

---

## 7. Remediation Verification — 2026-08-20

All release blockers and guide discrepancies from this review are resolved.

| Finding | Resolution | Verification |
|---|---|---|
| F1 — BOQ Header scope enforcement | Validation now respects `enable_scope_context`, bypasses Administrator, and preserves an explicitly supplied project. | VO 23/23, Quantity Revisions 30/30, Transaction Validation 13/13, BOQ Link Queries 9/9, BOQ Properties 17/17 |
| F2 — Scope exclusion wording | Guide now correctly states that exclusions affect list-query filtering, not BOQ Header validation. | Guide reviewed against `scope_query.py` and BOQ Header controller |
| F3 — BOQ Item field name | Guide now uses **Cost Item**, the actual BOQ Item field. | Schema and guide match |
| F4 — Cache-bust versions | Guide now matches `hooks.py`; `boq_filters.js` advanced to `?v=8` with the final UI fix. | `hooks.py` and guide cross-check |
| F5 — Omitted items in UI dropdowns | Transaction grids and VO lines now pass `exclude_zero_revised=1`; the BOQ-item link query supports the VO's `is_variation_item` filter. | Quantity Revisions 30/30, VO 23/23, JavaScript syntax checks |
| F6 — VFC control wording | Guide now identifies the **Form Config** grid-icon button and the **Sections** tab. | Guide reviewed against `vite_layout_controls.js` |
| F7 — schema/test notes | Guide uses **Delta Quantity** and reports the 17 Scope Context integration checks. The manual runner's stale helper import was corrected. | Scope Context 17/17 |

### Current Release Validation

| Suite | Result |
|---|---|
| Variation Orders | 23/23 ✅ |
| Quantity Revisions | 30/30 ✅ |
| Transaction Validation | 13/13 ✅ |
| BOQ Link Queries | 9/9 ✅ |
| BOQ Properties | 17/17 ✅ |
| Scope Context integration runner | 17/17 ✅ |
| Cost Analysis Engine | 17/17 ✅ |
| Cost Database API | 10/10 ✅ |
| VFC Backend | 39/39 ✅ |
| Asset build | `bench build --app construction` ✅ |

**Deployment decision:** The application and the accompanying user guide are ready for user deployment. Run the documented first-user smoke test after deploying to the target site.
