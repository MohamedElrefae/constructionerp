# Session Report: rc-1.1 Follow-up Sprint (WP1–WP7)

**To:** Manager / Product Owner
**From:** Engineering (AI-assisted session)
**Date:** 2026-06-21
**Branch:** `develop`
**Commits added:** 13 (`4607021`..`818b6eb`)
**Files changed:** 29 (+1,415 / -134 lines)
**Status:** Awaiting manager review and approval before proceeding to next sprint

---

## 1. Executive Summary

This session executed 7 work packages defined in `docs/NEXT_SPRINT_PLAN.md` as post-`rc-1.1` follow-up items. **6 of 7 work packages are complete**; WP5 (Project-wise Profitability) is deferred as "pending client decision" per manager direction (see §6).

All changes are committed to `develop` and pushed to remote. No regression to `rc-1.1` signed-off behavior. Test suite: **34 tests pass, 0 failures, 0 errors.**

---

## 2. Work Package Status

| WP | Title | Status | Commits | Key Files |
|----|-------|--------|---------|-----------|
| WP1 | Integrate broader-app work audit | ✅ Complete | `4607021`, `c6eaab8` | `docs/evidence/broader_app_audit_log.md` |
| WP2 | Convert scratch test to formal migration test | ✅ Complete | `d1f9f88`, `1f07ea0` | `construction/tests/test_migration_survival.py` |
| WP3 | Consolidate handover documents | ✅ Complete | `818b6eb` | `docs/handover/INDEX.md` + 7 migrated docs |
| WP4 | Gate VFC logging behind debug flag | ✅ Complete | `da95e89`, `dcf40d1` | `vfc_config.js`, `boot.py`, `hooks.py` |
| WP5 | Install Project-wise Profitability report | ⏳ Pending client decision | — | (deferred — see §6) |
| WP6 | Add Option B admin toggle | ✅ Complete | `573718d`, `82228cd` | `construction_settings.json`, `scope_report.py` |
| WP7 | Audit logging for restricted-user report access | ✅ Complete | `2f72d6f`, `d783115`, `b3799d6` | `scope_report.py`, `scope_report_access_log/`, `test_option_a_plus.py` |

---

## 3. What Was Built — Detailed

### WP1: Broader-App Audit (0.5 day)
- Audited 76 backup files from prior sessions in `/home/mohamed/frappe-bench/` root.
- Classified into 17 categories (scope context, BOQ, theme, VFC, accounting, Arabic localization, deployment, etc.).
- Result: No fragmentation found. All backup files are reference/historical only — no lost code.
- Deliverable: `docs/evidence/broader_app_audit_log.md` (141 lines).
- Side fix: `erpnext-mcp-server/server.py` — `AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)` to prevent FileHandler crash on first run.

### WP2: Migration Survival Test (0.5 day)
- Converted informal "scratch" test into formal `unittest` test class.
- **7 tests** verify after every `bench migrate`:
  - Construction Settings fields survive
  - User Scope Context DocType exists
  - BOQ Item `cost_item` field (not `item_code`)
  - Option A+ scope query injection hook registered
  - Option B report overrides applied
  - Scope Report Access Log DocType exists (WP7)
  - Construction Settings Option B toggle field exists (WP6)
- Deliverable: `construction/tests/test_migration_survival.py` (77 lines).
- Run via: `bench --site v16.localhost run-tests --app construction` or Python unittest runner.

### WP3: Handover Documentation Cleanup (1 day)
- Created `docs/handover/` directory with `INDEX.md` (document index + status).
- Migrated 7 handover docs from repo root into `docs/handover/`:
  - `BOQ_STRUCTURE_BLOCKER_HANDOFF.md` (scope context/permissions briefing)
  - `SCOPE_CONTEXT_STANDARDIZATION_APPROVAL_REPORT.md` (manager approval)
  - `SENIOR_ENGINEER_AUDIT_REPORT.md` (audit reference)
  - `TYPOGRAPHY_CURRENT_FONT_IMPLEMENTATION_REPORT.md` (font system)
  - `VFC_PROJECT_TABS_DEBUG_REPORT.md` (VFC debug plan)
  - `CONSTRUCTION_ERP_AI_MEMORY_PLAN_v2.2.md` (AI memory architecture — archived)
  - `AGENTS_HANDOFF.md` (typography handoff — superseded)
- Updated `AGENTS.md`: branch `feature/vite-ui-v1` → `develop`, commits 117 → 185, latest commit, active workstreams → WP1-WP7.
- Updated `SESSION_MEMORY.md`: project snapshot, in-progress section, new session log entry (2026-06-21).
- Fixed cross-references in `NEXT_SPRINT_PLAN.md`, `USER_GUIDE.md`, `VFC_FORM_CONFIG_DEBUG_REPORT_TO_MANAGER.md`.
- Note: Root-level directories (`01 scope context/`, `02BOQ Integratiom/`, `03 ACCOUNTING INTEGRATAION/`, `teme debug/`, `forms config/`) are outside the git repo boundary and documented as external references in INDEX.md.

### WP4: VFC Debug Flag (0.5 day)
- Added `vfc_debug_logging` boolean field to Construction Settings (default OFF).
- `boot.py` reads the flag and passes `vfc_debug_logging` to `window` via `boot_session` hook.
- `hooks.py` registers the boot hook.
- `vfc_config.js` (new, 23 lines) checks `window.vfc_debug_logging` before emitting `console.log` / `console.warn`.
- Wrapped `console.log` calls in `vfc_layout_engine.js`, `vite_layout_controls.js`, `vfc_layout_engine_tests.js` behind the flag.
- Result: VFC console noise eliminated in production unless admin explicitly enables the toggle.

### WP6: Option B Admin Toggle (1 day)
- Added `enable_option_b_report_access_bypass` boolean field to Construction Settings DocType (default ON for backward compatibility).
- Added `_user_has_active_scope_context(user)` helper in `scope_report.py` — checks User Scope Context record + toggle state.
- Wired the gate into `_scope_aware_is_permitted`, `_scope_aware_get_report_doc`, `_scope_aware_run`:
  - If toggle ON and user has scope context → Option B bypass active (backward compatible).
  - If toggle OFF → Option B bypass disabled; restricted users get Option A+ scope enforcement only.
- Tests: 4 toggle tests (default ON, toggle OFF denies, toggle ON grants, toggle OFF logs denial).
- Result: Admin can now disable Option B report bypass without a code change.

### WP7: Audit Logging for Restricted-User Report Access (1.5 days)
- **New DocType:** `Scope Report Access Log` (134-line JSON schema):
  - Fields: `user`, `report_name`, `decision` (Granted/Denied), `reason`, `request_path`, `scope_dimensions` (JSON), `option_b_bypass_active`, `timestamp`.
  - Non-submittable, auto-created via `frappe.get_doc({...}).insert()`.
- **`_log_report_access()` helper** in `scope_report.py`:
  - Captures user, report name, decision, reason, scope dimensions, bypass state.
  - **Critical fix:** `getattr(frappe.request, "path", "")` raises `RuntimeError` (not `AttributeError`) when called outside an HTTP request context because `frappe.request` is a `LocalProxy`. The original `except Exception: pass` silently swallowed this, causing the audit log to never create entries. Fixed with explicit `try: ... except RuntimeError: path = ""`.
- **Grant logging:** Wired into all three Option B bypass points (`is_permitted`, `get_report_doc`, `run`).
- **Denial logging:** Added to `_scope_aware_is_permitted` and `_scope_aware_get_report_doc` — logs denied attempts when a restricted non-scoped user hits the gate. Reason field captures `"Option B bypass not available"` when scope record exists but toggle is OFF.
- **Tests:** 5 new tests (34 total pass):
  - `test_audit_log_granted_on_is_permitted` — grants logged
  - `test_audit_log_denied_on_is_permitted_no_scope` — denial without scope
  - `test_audit_log_denied_on_is_permitted_toggle_off` — denial with toggle off
  - `test_audit_log_granted_on_get_report_doc` — grants via get_report_doc
  - `test_audit_log_granted_on_run` — grants via run
- Result: Every restricted-user access to an allowlisted report is now auditable with full context.

---

## 4. Test Results

| Test Suite | Tests | Failures | Errors | Status |
|------------|-------|----------|--------|--------|
| `test_option_a_plus.py` (Option A+ scope + Option B toggle + audit log) | 34 | 0 | 0 | ✅ Pass |
| `test_migration_survival.py` (post-migrate checks) | 7 | 0 | 0 | ✅ Pass |

Run command:
```bash
bench --site v16.localhost console <<'PYEOF'
from construction.tests.test_option_a_plus import TestOptionBReportAccessGate
import unittest, sys
suite = unittest.TestLoader().loadTestsFromTestCase(TestOptionBReportAccessGate)
result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
print(f"Ran {result.testsRun}, failures={len(result.failures)}, errors={len(result.errors)}")
PYEOF
```

**Known pre-existing issue:** Purchase Invoice test records fail to load in the Frappe test runner because `Cost Center: Main - E` does not belong to `_Test Company`. This is a fixture/data issue, not a code regression. It does NOT affect `test_option_a_plus.py` or `test_migration_survival.py`, which run via a standalone Python unittest runner.

---

## 5. Migration Impact

`bench --site v16.localhost migrate` was run to create the `tabScope Report Access Log` table. The migration is idempotent — re-running on a production site will:
1. Create the `Scope Report Access Log` DocType and table.
2. Add `enable_option_b_report_access_bypass` field to Construction Settings (default ON).
3. Add `vfc_debug_logging` field to Construction Settings (default OFF).

No data loss. No destructive schema changes.

---

## 6. WP5 — Pending Client Decision (Manager Direction)

**Per manager discussion (2026-06-21):** WP5 (Project-wise Profitability) is deferred as "pending client decision" for the following reasons:

1. **The standard ERPNext `Project-wise Profitability` report pulls from GL entries only** (invoices, expenses, journals keyed to a Project). It does NOT reflect BOQ-driven construction costs (contract value, revised quantities, certified quantities, VO deltas).

2. **Installing it now would show a generic accounting view** that may confuse the client — the numbers won't match their construction reality.

3. **Recommended path forward (after BOQ reports are finalized):**
   - **Option A:** Install the standard report as-is (pure GL view). Fast (0.5 day) but potentially misleading.
   - **Option B:** Build a custom **Construction Profitability report** that joins BOQ `total_revised_value` + `quantity_certified` + VO deltas + GL actuals. This is the number the client actually cares about. Slower (3–5 days) but accurate.

4. **Decision needed from manager/client:**
   - Does the client want a profitability report now (GL-only), or wait for the BOQ-integrated version?
   - Is there a target date for BOQ report finalization?

**Action recorded in `SESSION_MEMORY.md` §3 Task 5.**

---

## 7. Items Requiring Manager Approval

| # | Item | Why approval is needed |
|---|------|------------------------|
| 1 | **Acceptance of WP1–WP7 completion** | Confirm the 6 completed work packages meet the acceptance criteria in `NEXT_SPRINT_PLAN.md` |
| 2 | **WP5 deferral** | Confirm "pending client decision" status is acceptable; confirm whether to pursue Option A (standard report) or Option B (custom report) after BOQ reports |
| 3 | **Next sprint direction** | After approval, the next logical workstreams are: (a) BOQ report finalization, (b) Form Layout Engine Phase 3+, (c) BOQ Accounting Integration. Which should be prioritized? |
| 4 | **Option B toggle default** | WP6 ships with `enable_option_b_report_access_bypass` defaulting to ON (backward compatible). Confirm this is the desired production default, or should it default to OFF? |
| 5 | **Audit log retention policy** | WP7 audit logs retain all entries indefinitely. No auto-deletion. Confirm this is acceptable, or specify a retention period (e.g., 90 days, 1 year). |

---

## 8. Files Changed (Cumulative — 29 files, +1,415 / -134)

### New files (8)
- `construction/construction/doctype/scope_report_access_log/__init__.py`
- `construction/construction/doctype/scope_report_access_log/scope_report_access_log.js`
- `construction/construction/doctype/scope_report_access_log/scope_report_access_log.json`
- `construction/construction/doctype/scope_report_access_log/scope_report_access_log.py`
- `construction/public/js/vfc_config.js`
- `construction/tests/test_migration_survival.py`
- `docs/evidence/broader_app_audit_log.md`
- `docs/handover/INDEX.md`

### Modified files (10)
- `AGENTS.md` — branch, commit count, workstreams
- `SESSION_MEMORY.md` — snapshot, sprint section, session log
- `construction/boot.py` — VFC debug flag in boot_session
- `construction/construction/doctype/construction_settings/construction_settings.json` — 2 new fields
- `construction/hooks.py` — boot hook registration
- `construction/overrides/scope_report.py` — WP4 logging, WP6 toggle, WP7 audit + denial logging
- `construction/public/js/vfc_layout_engine.js` — gated console.log
- `construction/public/js/vfc_layout_engine_tests.js` — gated console.log
- `construction/public/js/vite_layout_controls.js` — gated console.log
- `construction/tests/test_option_a_plus.py` — +197 lines (WP6 toggle + WP7 audit tests)

### Migrated files (7 — git rename, 0% change)
- `AGENTS_HANDOFF.md` → `docs/handover/AGENTS_HANDOFF.md`
- `docs/BOQ_STRUCTURE_BLOCKER_HANDOFF.md` → `docs/handover/BOQ_STRUCTURE_BLOCKER_HANDOFF.md`
- `CONSTRUCTION_ERP_AI_MEMORY_PLAN_v2.2.md` → `docs/handover/CONSTRUCTION_ERP_AI_MEMORY_PLAN_v2.2.md`
- `SCOPE_CONTEXT_STANDARDIZATION_APPROVAL_REPORT.md` → `docs/handover/SCOPE_CONTEXT_STANDARDIZATION_APPROVAL_REPORT.md`
- `SENIOR_ENGINEER_AUDIT_REPORT.md` → `docs/handover/SENIOR_ENGINEER_AUDIT_REPORT.md`
- `TYPOGRAPHY_CURRENT_FONT_IMPLEMENTATION_REPORT.md` → `docs/handover/TYPOGRAPHY_CURRENT_FONT_IMPLEMENTATION_REPORT.md`
- `VFC_PROJECT_TABS_DEBUG_REPORT.md` → `docs/handover/VFC_PROJECT_TABS_DEBUG_REPORT.md`

### Other modified docs (3)
- `docs/NEXT_SPRINT_PLAN.md` — cross-reference fixes
- `docs/VFC_FORM_CONFIG_DEBUG_REPORT_TO_MANAGER.md` — cross-reference fix
- `docs/ai/USER_GUIDE.md` — cross-reference fixes
- `erpnext-mcp-server/server.py` — audit log directory fix (1 line)

---

## 9. Commits (13 total, oldest first)

| Hash | Message |
|------|---------|
| `4607021` | docs: add broader-app work audit log (WP1) |
| `d1f9f88` | test: convert survival scratch test to formal test (WP2) |
| `da95e89` | feat: gate VFC diagnostic logging behind debug flag (WP4) |
| `573718d` | feat: add Admin Settings toggle for Option B report bypass (WP6) |
| `2f72d6f` | feat: add audit logging for restricted-user report access (WP7) |
| `cd53030` | docs: add NEXT_SPRINT_PLAN (WP3/docks) |
| `c6eaab8` | Merge branch 'feat/integrate-broader-app-work' into develop |
| `1f07ea0` | Merge branch 'feat/remove-scratch-test' into develop |
| `dcf40d1` | Merge branch 'feat/vfc-debug-flag' into develop |
| `82228cd` | Merge branch 'feat/option-b-admin-toggle' into develop (resolved conflicts) |
| `b3799d6` | Merge branch 'feat/option-b-audit-log' into develop |
| `d783115` | fix: audit log _log_report_access RuntimeError and add denial logging (WP7) |
| `73439f3` | fix: ensure MCP audit log parent directory exists before FileHandler init |
| `818b6eb` | docs: consolidate handover documents into docs/handover/ and update AGENTS/SESSION memory (WP3) |

---

## 10. Next Steps (After Manager Approval)

1. **If WP1–WP7 approved:** Tag `develop` as `rc-1.2` (or per manager's versioning preference) and deploy to client site.
2. **If WP5 Option A chosen:** Install standard `Project-wise Profitability` report via fixture/patch (0.5 day).
3. **If WP5 Option B chosen:** Scope custom Construction Profitability report joining BOQ + GL data (3–5 days).
4. **BOQ report finalization:** Continue BOQ Accounting Integration (`services/boq_accounting.py`, `services/boq_transaction_validation.py`) to feed accurate data into profitability reporting.
5. **Form Layout Engine Phase 3+:** Continue per `docs/handover/VFC_PROJECT_TABS_DEBUG_REPORT.md`.

---

*Prepared by: Engineering (AI-assisted session, Cursor agent)*
*Review requested by: Mohamed Elrefae*
*Date: 2026-06-21*
