# Construction ERP — Next Sprint Plan (Post-`rc-1.1`)

> **Release context:** `rc-1.1` is signed off. This plan converts the GM certificate follow-up items into an executable, AI-agent-friendly sprint.
>
> **Plan version:** 1.0  
> **Planned start:** immediately after `rc-1.1` client handoff  
> **Sprint goal:** close the 7 post-release follow-up items with zero regression to the `rc-1.1` signed-off scope.

---

## 1. Executive Summary

| # | Follow-up Item | Priority | Owner | Estimated Effort |
|---|----------------|----------|-------|------------------|
| 1 | Audit and integrate preserved broader-app work | High | Tech Lead | 2–3 days |
| 2 | Remove or convert `scratch_test.py` / `survival_test.py` | Medium | Backend Dev | 0.5 day |
| 3 | Convert/update remaining handover documents | Medium | Tech Writer / Lead | 1–2 days |
| 4 | Gate VFC diagnostic logging behind a debug flag | High | Frontend Dev | 1 day |
| 5 | Install Project-wise Profitability report (client-dependent) | Medium | Backend Dev | 0.5–1 day |
| 6 | Add Admin Settings toggle for Option B | High | Backend + Frontend | 1–2 days |
| 7 | Add audit logging for restricted-user report access | High | Backend Dev | 1–2 days |

**Sprint duration estimate:** 7–10 working days with one full-stack developer and one QA.

---

## 2. Source of Truth & Constraints

### 2.1 Source of Truth
- `docs/GM_SIGN_OFF_CERTIFICATE.md` — lists the 7 follow-up items.
- `docs/GM_RECOMMENDATION_EXECUTION_PLAN.md` — release execution baseline.
- `construction/overrides/scope_report.py` — Option A+ / Option B implementation.
- `construction/construction/doctype/construction_settings/construction_settings.json` — admin settings schema.
- `AGENTS.md` — project conventions (MUST read first for every implementation session).

### 2.2 Hard Constraints
- **No regression to `rc-1.1` signed-off behavior.**
- All SQL remains parameterized.
- All new API endpoints require `@frappe.whitelist()`.
- Code remains Python 3.10 quote-nesting compatible.
- All modified JS files need cache-buster bump in `hooks.py`.
- Run `python3 scripts/lint_scope_metadata.py` before any scope-related commit.
- All tests from `rc-1.1` (50 backend + 31 Node + 10 UAT) must still pass.

### 2.3 Branch Strategy
```
main / feat/scope-context-option-a-plus-clean  ← release tag rc-1.1 here
                │
                ▼
       develop (integration branch for next sprint)
                │
                ├── feat/integrate-broader-app-work
                ├── feat/remove-scratch-test
                ├── feat/update-handover-docs
                ├── feat/vfc-debug-flag
                ├── feat/project-wise-profitability
                ├── feat/option-b-admin-toggle
                └── feat/option-b-audit-log
```

> **AI agent note:** Create feature branches from `develop`. Rebase onto latest `develop` before each PR. Do **not** push to `feat/scope-context-option-a-plus-clean` or move the `rc-1.1` tag.

---

## 3. Work Package 1 — Audit and Integrate Preserved Broader-App Work

### 3.1 Context
Before `rc-1.1` alignment, the main worktree contained broader-app work that was **not** part of the release scope. It was preserved in:
- Git branch: `backup/main-worktree-2026-06-20` (commit `dce164e`)
- Filesystem archive: `/tmp/construction-main-worktree-backup-2026-06-20`

Diff summary vs. `feat/scope-context-option-a-plus-clean`:
- 76 files changed, ~6,396 insertions / ~5,434 deletions.
- Notable additions: `construction/tests/test_boq_import_status_smoke.py`, docs for BOQ Excel finish, MCP server changes, theme/typography fixes, VO quantity revision test changes.

### 3.2 Objective
Determine which preserved changes are production-ready and should be re-integrated into `develop`, and which should remain in the backup/archive.

### 3.3 Step-by-Step Tasks
1. **Create audit branch** from `develop`.
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feat/integrate-broader-app-work
   ```
2. **Generate a clean diff** between `feat/scope-context-option-a-plus-clean` and `backup/main-worktree-2026-06-20`.
   ```bash
   git diff feat/scope-context-option-a-plus-clean..backup/main-worktree-2026-06-20 --stat
   git diff feat/scope-context-option-a-plus-clean..backup/main-worktree-2026-06-20 > /tmp/broader_app_diff.patch
   ```
3. **Classify every changed file** into one of:
   - A. Ready to integrate now (tested, relevant, low risk).
   - B. Needs rework before integrate (partial, risky, or conflicts with rc-1.1).
   - C. Superseded by rc-1.1 (discard).
   - D. Archive-only (keep in backup; do not integrate).
4. **Create an audit log** at `docs/evidence/broader_app_audit_log.md` with file, classification, and rationale.
5. **Cherry-pick / merge category A changes** in logical chunks. Prefer subsystem PRs so review can isolate behavior changes from documentation, tooling, and visual polish.
6. **Run the full rc-1.1 test suite** after each chunk.
7. **Open PR(s)** to `develop`.

### 3.4 Deliverables
- `docs/evidence/broader_app_audit_log.md`
- Multiple subsystem PRs integrating approved broader-app work, rather than one large merge:
  - Tests / QA evidence
  - MCP server / tooling
  - Docs / handover updates
  - Theme / typography / UI polish
  - Business-logic changes as their own PR
- Updated `SESSION_MEMORY.md` if architecture changes

### 3.5 Acceptance Criteria
- [ ] Every changed file from the backup is classified.
- [ ] Category A changes are integrated into `develop`.
- [ ] 50/50 backend tests + 31/31 Node tests + 10/10 UAT still pass.
- [ ] No `rc-1.1` feature behavior changes.

### 3.6 Risks
| Risk | Mitigation |
|------|------------|
| Cherry-pick conflicts with rc-1.1 code | Resolve manually; if conflict is non-trivial, downgrade file to Category B |
| Unintended behavior change | Re-run full test suite after each chunk |
| Archive deletion | Do not delete `/tmp/construction-main-worktree-backup-2026-06-20` until sprint end |

---

## 4. Work Package 2 — Remove or Convert `scratch_test.py`

### 4.1 Context
- File found: `construction/scratch/survival_test.py` (note: plan item says `scratch_test.py`; verify both names).
- It simulates a migration survival test by calling `whitelabel_patch()` and `create_system_themes()`.
- It is not part of the formal test suite and is not discoverable by `bench run-tests`.

### 4.2 Objective
Either (a) convert it into a proper unit test, or (b) remove it if equivalent coverage already exists.

### 4.3 Step-by-Step Tasks
1. **Search for all scratch / survival files across the entire bench**:
   ```bash
   find /home/mohamed/frappe-bench -name "*scratch*" -o -name "*survival*" -o -name "*tmp*test*"
   ```
2. **Check existing test coverage**:
   - Search for tests of `whitelabel_patch` and `create_system_themes`.
   - If coverage exists and is reliable, delete the scratch file.
   - If coverage is missing or incomplete, convert it to a formal test in `construction/tests/`.
3. **If converting:**
   - Use `unittest.TestCase` and Frappe test fixtures.
   - Replace `print()` with assertions.
   - Do not call `frappe.connect()` manually; rely on test runner.
   - Clean up created data in `tearDown`.
4. **Run tests**:
   ```bash
   bench --site v16.localhost run-tests --module construction.tests.test_<new_name>
   # or if deleted, ensure existing tests still pass
   ```
5. **Open PR** to `develop`.

### 4.4 Deliverables
- Deleted `construction/scratch/` directory OR new formal test file.
- Updated `construction/tests/__init__.py` if a new test module is added.

### 4.5 Acceptance Criteria
- [ ] No `scratch_test.py` or `survival_test.py` remains outside the formal test suite.
- [ ] Existing theme/migration tests still pass.
- [ ] If converted, new test passes and cleans up after itself.

---

## 5. Work Package 3 — Convert/Update Remaining Handover Documents

### 5.1 Context
Multiple handover / draft documents exist in repo root and subdirectories. Some are outdated or duplicated. The goal is to consolidate them into the canonical `docs/` directory and update them to reflect `rc-1.1` reality.

### 5.2 Candidate Documents to Review
| Path | Status | Proposed Action |
|------|--------|-----------------|
| `/home/mohamed/frappe-bench/BOQ_STRUCTURE_BLOCKER_HANDOFF.md` | Root-level duplicate | Move/review against `docs/BOQ_STRUCTURE_BLOCKER_HANDOFF.md` |
| `/home/mohamed/frappe-bench/01 scope context/*.md` | Legacy scope-context plans | Archive or migrate relevant parts to `docs/scope_context_*` |
| `/home/mohamed/frappe-bench/02BOQ Integratiom/*.md` | Legacy BOQ plans | Archive or migrate relevant parts to `docs/boq_*` |
| `/home/mohamed/frappe-bench/03 ACCOUNTING INTEGRATAION/*.md` | In-progress accounting docs | Keep; add front-matter linking to current state |
| `/home/mohamed/frappe-bench/AGENTS_HANDOFF.md` | Possibly stale | Review against `AGENTS.md`; merge or delete |
| `/home/mohamed/frappe-bench/apps/construction/AGENTS_HANDOFF.md` | Possibly stale | Same as above |
| `/home/mohamed/frappe-bench/apps/construction/VFC_PROJECT_TABS_DEBUG_REPORT.md` | VFC debug report | Convert to VFC troubleshooting guide or archive |
| `/home/mohamed/frappe-bench/apps/construction/SESSION_MEMORY.md` | Living doc | Update after each work package |

### 5.3 Step-by-Step Tasks
1. **Inventory all `.md` files** outside `docs/`:
   ```bash
   find . -maxdepth 3 -name "*.md" -not -path "*/docs/*" -not -path "*/node_modules/*" -not -path "*/env/*" | sort
   ```
2. **Classify each** as: migrate to `docs/`, archive, update in place, or delete.
3. **Migrate** handover documents into `docs/handover/` with consistent front matter.
4. **Update** `AGENTS.md` and `SESSION_MEMORY.md` to reflect current branch (`develop`) and any architecture changes.
5. **Create an index** `docs/handover/INDEX.md` listing all handover docs and their purpose.
6. **Open PR** to `develop`.

### 5.4 Deliverables
- `docs/handover/INDEX.md`
- Migrated/updated handover documents
- Clean root directory (no duplicate handover files)

### 5.5 Acceptance Criteria
- [ ] Every `.md` outside `docs/` is accounted for in the inventory.
- [ ] No duplicate handover documents remain in repo root.
- [ ] `AGENTS.md` remains accurate.
- [ ] No code changes introduced.

---

## 6. Work Package 4 — Gate VFC Diagnostic Logging Behind a Debug Flag

### 6.1 Context
VFC (Form Layout Engine) emits many `console.log` / `console.warn` statements in:
- `construction/public/js/vfc_layout_engine.js`
- `construction/public/js/vite_layout_controls.js`
- `construction/public/js/vfc_layout_engine_tests.js`

These are useful for development but pollute production browser consoles and may leak internal state.

### 6.2 Objective
Replace unconditional `console.log` / `console.warn` with a debug-gated helper so logging is silent unless explicitly enabled.

### 6.3 Step-by-Step Tasks
1. **Add a global debug flag** in `construction/public/js/vfc_config.js` (or reuse `window.VFC_DISABLED` concept):
   ```js
   window.VFC_DEBUG = window.VFC_DEBUG || false;
   ```
2. **Create a helper** `vfc_debug_log(level, ...args)`:
   ```js
   function vfc_debug_log(level, ...args) {
       if (!window.VFC_DEBUG) return;
       const fn = level === 'warn' ? console.warn : (level === 'error' ? console.error : console.log);
       fn('[VFC]', ...args);
   }
   ```
3. **Replace all VFC `console.log` / `console.warn` calls** in the three files with `vfc_debug_log`.
4. **Expose the toggle via both mechanisms**:
   - A Construction Settings checkbox: `enable_vfc_debug_logging` (default 0) for admin-controlled global debugging.
   - A URL param: `?vfc_debug=1` for support-only one-off diagnosis without changing persistent settings.
5. **Bump JS cache buster** in `construction/hooks.py`.
6. **Run VFC tests** and browser smoke tests.
7. **Open PR** to `develop`.

### 6.4 Deliverables
- `construction/public/js/vfc_config.js` (new or updated)
- Updated VFC JS files
- New field `enable_vfc_debug_logging` in Construction Settings JSON
- Updated `construction/hooks.py` cache buster

### 6.5 Acceptance Criteria
- [ ] No unconditional VFC `console.log` / `console.warn` remain in production code.
- [ ] When `enable_vfc_debug_logging` is off and no URL param, browser console is silent during VFC attach.
- [ ] When enabled, logs appear as before.
- [ ] VFC form rendering and tests still pass.
- [ ] Cache buster bumped in `hooks.py`.

---

## 7. Work Package 5 — Install Project-wise Profitability Report

### 7.1 Context
- `Project-wise Profitability` is in the allowlist (`ALLOWED_REPORTS`) but is not installed in the test/production database.
- UAT returned 404 for this report.
- Client requirement is TBD; this work package is conditional.

### 7.2 Objective
Make the report available if the client confirms they need it, and re-run UAT.

### 7.3 Step-by-Step Tasks
1. **Confirm client requirement** (Product/GM). Do not implement this work package until the client confirms the report is needed; keep it in "pending client decision" status otherwise.
2. **Locate the report JSON**:
   - Check ERPNext source for `project_wise_profitability` report definition.
   - Typical location: `apps/erpnext/erpnext/projects/report/project_wise_profitability/`.
3. **Install the report** into the client site via one of:
   - `bench --site <site> export-fixtures` / `import-fixtures`, OR
   - A custom patch in `construction/patches/v6_x/install_project_wise_profitability.py`, OR
   - Manual DocType import if it is a custom report.
4. **Add fixture JSON** (if needed) under `construction/construction/report/` or `construction/fixtures/`.
5. **Re-run the 10-report UAT** including Project-wise Profitability.
6. **Update `docs/scope_context_option_b_acceptance.md`** with new UAT result.
7. **Open PR** to `develop` only after client confirmation.

### 7.4 Deliverables
- Patch or fixture to install the report
- Updated UAT evidence
- Updated acceptance doc

### 7.5 Acceptance Criteria
- [ ] Client confirmed requirement, or this work package is explicitly deferred as "pending client decision."
- [ ] Report loads without 404 for scoped restricted users.
- [ ] Scope filters are enforced on the report.
- [ ] 11/11 allowlisted reports pass UAT (zero 403s).

### 7.6 Risks
| Risk | Mitigation |
|------|------------|
| Report is not part of standard ERPNext install | Document and escalate to client; may require custom report development |
| Report has different filter names than expected | Update `scope_report.py` dimension mapping if needed |

---

## 8. Work Package 6 — Add Admin Settings Toggle for Option B

### 8.1 Context
Option B (report access gate bypass) is currently **always active** when `enable_scope_context` is on and the user has an active scope. There is no admin toggle to disable Option B independently.

### 8.2 Objective
Add a Construction Settings checkbox `enable_option_b_report_access_bypass` that controls whether Option B patches are applied.

Default the checkbox to **ON** to preserve `rc-1.1` behavior. This avoids surprising existing restricted scoped users after upgrade while giving admins a documented secure-mode switch.

### 8.3 Step-by-Step Tasks
1. **Add field** to `construction_settings.json`:
   ```json
   {
       "default": "1",
       "fieldname": "enable_option_b_report_access_bypass",
       "fieldtype": "Check",
       "label": "Enable Option B Report Access Bypass",
       "description": "Allow scoped restricted users to access the allowlisted financial reports without explicit report permissions.",
       "depends_on": "enable_scope_context"
   }
   ```
2. **Add field to `field_order`** after `enable_scope_context` or in a new "Scope Report Access" section.
3. **Update `construction/overrides/scope_report.py`**:
   - In `_user_has_active_scope_context`, also check the new flag.
   - If flag is disabled, return `False` (Option A+ filter rewriting still works, but Option B bypass is off).
4. **Update `construction/services/feature_flags.py`** if the flag should be part of `IMPROVE_NOW_FLAGS` (optional; recommended for consistency).
5. **Add/update tests** in `construction/tests/test_option_a_plus.py`:
   - Test that Option B bypass does not apply when flag is disabled.
   - Test that the default enabled state preserves `rc-1.1` Option B behavior.
6. **Run tests**:
   ```bash
   bench --site v16.localhost run-tests --module construction.tests.test_option_a_plus
   ```
7. **Update user guide** to explain the toggle.
8. **Open PR** to `develop`.

### 8.4 Deliverables
- Updated `construction_settings.json`
- Updated `scope_report.py`
- Updated tests
- Updated user guide

### 8.5 Acceptance Criteria
- [ ] Toggle appears in Construction Settings when Scope Context is enabled.
- [ ] When toggle is ON, Option B behavior matches `rc-1.1`.
- [ ] When toggle is OFF, restricted scoped users get 403 on allowlisted reports they do not have permission for.
- [ ] Option A+ filter rewriting still works in both states.
- [ ] All existing tests pass.

---

## 9. Work Package 7 — Add Audit Logging for Restricted-User Report Access

### 9.1 Context
When Option B is enabled, scoped restricted users can access allowlisted reports without explicit report permissions. This is a security bypass and must be auditable.

### 9.2 Objective
Log every successful and denied access attempt to an allowlisted report by a restricted scoped user.

### 9.3 Step-by-Step Tasks
1. **Design audit log storage**:
   - **Option A (recommended):** Create a new DocType `Scope Report Access Log` with fields:
     - `user` (Link → User)
     - `report_name` (Data)
     - `company`, `cost_center`, `project`, `department` (Data or Link)
     - `access_granted` (Check)
     - `denial_reason` (Data)
     - `timestamp` (Datetime, default now)
     - `request_path` (Data, optional)
   - **Option B:** Use Frappe `Activity Log` if appropriate (less structured).
2. **Create DocType** `Scope Report Access Log` with permissions only for System Manager / Auditor roles.
3. **Add logging helper** in `construction/overrides/scope_report.py`:
   ```python
   def _log_report_access(report_name, granted, reason=None):
       # create Scope Report Access Log doc
   ```
4. **Call the helper** in:
   - `_scope_aware_is_permitted` (when returning True for scoped user)
   - `_scope_aware_get_report_doc` (when bypassing)
   - `_scope_aware_run` (when rewriting filters and running)
   - Optionally when access is denied (non-allowlisted report, or missing scope).
5. **Respect privacy/retention**:
   - Batch or queue writes if performance is a concern.
   - Add a configurable retention setting if compliance confirms a required period.
   - If no client/compliance policy is available by implementation time, retain logs and file a follow-up cleanup-job decision instead of silently deleting audit evidence.
6. **Add tests**:
   - Verify log entry created on access.
   - Verify log entry created on denial.
   - Verify no log entry for unrestricted users.
7. **Add a read-only report** or list view for auditors.
8. **Open PR** to `develop`.

### 9.4 Deliverables
- New DocType `Scope Report Access Log`
- Updated `scope_report.py` with logging calls
- Tests in `construction/tests/test_option_a_plus.py` or new file
- Optional audit report/list view

### 9.5 Acceptance Criteria
- [ ] Every restricted scoped user access to an allowlisted report creates a log entry.
- [ ] Log captures user, report, scope dimensions, granted/denied, timestamp.
- [ ] Unrestricted users do not create log entries.
- [ ] Log DocType is only readable by System Manager / Auditor.
- [ ] No noticeable performance degradation on report load.

### 9.6 Risks
| Risk | Mitigation |
|------|------------|
| Performance impact from per-request log write | Use `frappe.enqueue` for log writes if load is high |
| Log table grows unbounded | Implement retention job from day one |

---

## 10. Cross-Cutting Testing Strategy

### 10.1 Automated Tests to Run After Every PR
```bash
# Backend
bench --site v16.localhost run-tests --module construction.tests.test_option_a_plus
bench --site v16.localhost run-tests --module construction.tests.test_scope_context

# Frontend / Node
node construction/tests/test_scope_context_report_filters.js
node /tmp/opencode/test_option_b_uat.js

# Linter
ruff check construction/overrides/scope_report.py construction/tests/test_option_a_plus.py
```

### 10.2 Manual UAT After All Work Packages
- Log in as restricted scoped user.
- Open each of the 11 allowlisted reports.
- Confirm zero 403s, correct scope filters, and no console errors.
- If audit logging is enabled, confirm entries appear in `Scope Report Access Log`.
- If Option B toggle is off, confirm 403s return.

### 10.3 Regression Checklist
- [ ] `rc-1.1` test suite still passes.
- [ ] BOQ lifecycle works.
- [ ] Variation Orders work.
- [ ] Theme / RTL / Arabic localization works.
- [ ] Scope Context top-bar works.

---

## 11. Execution Sequence & Dependencies

```
Week 1
├── Day 1–2: WP1  Audit broader-app work + start integration
├── Day 2–3: WP2  Remove/convert scratch test
├── Day 3–4: WP4  VFC debug flag
└── Day 4–5: WP6  Option B admin toggle

Week 2
├── Day 1–2: WP7  Audit logging
├── Day 2–3: WP5  Project-wise Profitability (only if client confirms)
├── Day 3–4: WP3  Handover document cleanup
└── Day 4–5: Integration testing, UAT, PR merges to develop
```

### Dependency Notes
- WP6 (Option B toggle) should be completed before WP7 (audit logging) because the toggle changes the control flow that the audit logger must observe.
- WP5 is client-dependent and can run in parallel.
- WP1 should start first because integrated broader-app work may affect other packages.

---

## 12. Definition of Done

The sprint is complete when:
1. All 7 follow-up items are resolved or explicitly deferred with GM approval.
2. All PRs are merged into `develop`.
3. `rc-1.1` regression test suite passes.
4. `AGENTS.md` and `SESSION_MEMORY.md` are updated.
5. `develop` is ready for the next release branch.

---

## 13. Appendices

### Appendix A — AI Agent Quick Reference
- **App root:** `/home/mohamed/frappe-bench/apps/construction`
- **App name:** `construction`
- **Current release branch:** `feat/scope-context-option-a-plus-clean`
- **Next sprint integration branch:** `develop`
- **Site:** `v16.localhost`
- **Settings DocType:** `Construction Settings`
- **Option B code:** `construction/overrides/scope_report.py`
- **VFC code:** `construction/public/js/vfc_layout_engine.js`, `construction/public/js/vite_layout_controls.js`

### Appendix B — Files Likely to Change
| Work Package | Files |
|--------------|-------|
| WP1 | TBD by audit |
| WP2 | `construction/scratch/survival_test.py`, possibly `construction/tests/test_theme_migration.py` |
| WP3 | `docs/handover/*`, `AGENTS.md`, `SESSION_MEMORY.md` |
| WP4 | `construction/public/js/vfc_layout_engine.js`, `construction/public/js/vite_layout_controls.js`, `construction/public/js/vfc_layout_engine_tests.js`, `construction/construction/doctype/construction_settings/construction_settings.json`, `construction/hooks.py` |
| WP5 | `construction/patches/v6_x/install_project_wise_profitability.py`, `construction/fixtures/*`, `docs/scope_context_option_b_acceptance.md` |
| WP6 | `construction/construction/doctype/construction_settings/construction_settings.json`, `construction/overrides/scope_report.py`, `construction/services/feature_flags.py`, `construction/tests/test_option_a_plus.py`, `docs/USER_GUIDE.md` |
| WP7 | `construction/construction/doctype/scope_report_access_log/*`, `construction/overrides/scope_report.py`, `construction/tests/test_option_a_plus.py` |

### Appendix C — Review & Open Questions

> **This section captures the planner's review comments and should be resolved before implementation starts.**

1. **WP1 scope:** The backup diff is large (76 files). Should we integrate it as one PR or split by subsystem (tests, MCP server, docs, theme)? **Recommendation:** split by subsystem for safer review.
2. **WP2 naming:** The GM certificate says `scratch_test.py`, but the repo contains `construction/scratch/survival_test.py`. **Action:** search the entire bench before deciding. Initial local check found `construction/scratch/survival_test.py` and no `scratch_test.py` in the app.
3. **WP4 toggle mechanism:** Use both a Construction Settings checkbox and `?vfc_debug=1`.
4. **WP5 client decision:** Keep Project-wise Profitability in a "pending client decision" bucket until the client confirms they need it.
5. **WP6 default value:** Default `enable_option_b_report_access_bypass` to **ON** for backward compatibility, with user guide documentation explaining how admins can disable it.
6. **WP7 retention:** Confirm required audit-log retention with GM/compliance. If unavailable before implementation, retain logs by default and defer cleanup-job policy rather than deleting audit evidence.
7. **Branch naming:** The repo currently has `develop` and `feature/vite-ui-v1`. Is `develop` the actual next-sprint integration branch? **Action:** verify with tech lead; the plan assumes `develop`.

---

*End of plan.*
