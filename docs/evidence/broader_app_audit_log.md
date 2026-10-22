# Broader-App Work Audit Log

**Date:** 2026-06-20
**Audit branch:** `feat/integrate-broader-app-work` (from `develop`)
**Backup reference:** `backup/main-worktree-2026-06-20` (commit `dce164e`)
**Release reference:** `feat/scope-context-option-a-plus-clean` (commit `06897fc` / tag `rc-1.1`)

---

## 1. Executive Summary

- **76 files** differ between the backup and the release.
- **65 of 76** are **formatting-only** changes: the backup branch was formatted with a different linter configuration (multi-line breaking, trailing whitespace, extra blank lines). The release branch was properly ruff-formatted. **These carry zero feature delta** and are **Category C — Superseded.**
- **11 files** exist **only** in the backup — these are genuine preserved additions that were never integrated into the release. All are documentation or standalone test files.
- **2 files** exist only in the release (the GM sign-off certificate and the Option B acceptance doc).

**Recommendation:** Integrate the 11 new files after migrating them into the canonical directory structure. Do NOT touch the 65 formatting-changed files — the release versions are the correct baseline.

---

## 2. File Classification

### Category A — Ready to Integrate (11 files)

These files are new additions that exist only in the backup. They carry no risk of regression because they do not modify existing code.

| # | File (backup path) | Type | Proposed Destination | Rationale |
|---|--------------------|------|---------------------|-----------|
| A1 | `BOQ_EXCEL_IMPORT_SCOPE_FINISH_PLAN.md` | Plan document | `docs/` | Migrate from root to canonical docs/ |
| A2 | `RESTORED_WORK_FOLLOWUP_REPORT.md` | Follow-up report | `docs/` | Migrate from root to canonical docs/ |
| A3 | `TYPOGRAPHY_HANDOFF_MISMATCH_FINISH_REPORT.md` | Handoff report | `docs/` | Migrate from root to canonical docs/ |
| A4 | `docs/scope_context_option_b_design.md` | Design document | `docs/` (already canonical) | Preserve as-is, already in docs/ |
| A5 | `docs/feature_reviews/BOQ_EXCEL_IMPORT_UI_TEST_PLAN.md` | Test plan | `docs/feature_reviews/` | Preserve as-is |
| A6 | `docs/feature_reviews/CONSULTANT_REVIEW_REQUEST_BOQ_EXCEL_FINISH.md` | Review request | `docs/feature_reviews/` | Preserve as-is |
| A7 | `docs/feature_reviews/CONSULTANT_REVIEW_RESPONSE_BOQ_EXCEL_FINISH.md` | Review response | `docs/feature_reviews/` | Preserve as-is |
| A8 | `docs/feature_reviews/evidence/EV-068-wp2-finish-scope.md` | Evidence doc | `docs/feature_reviews/evidence/` | Preserve as-is |
| A9 | `construction/tests/playwright_browser.js` | Playwright test | `construction/tests/` | Standalone; does not affect existing tests |
| A10 | `construction/tests/playwright_smoke.js` | Playwright smoke test | `construction/tests/` | Standalone; does not affect existing tests |
| A11 | `construction/tests/test_boq_import_status_smoke.py` | Manual smoke test | `construction/tests/` | Standalone; run via `bench execute`, not auto-discovered |

### Category B — Needs Rework Before Integration (1 file)

| # | File | Issue | Recommended Action |
|---|------|-------|-------------------|
| B1 | `erpnext-mcp-server/server.py` | Backup replaces 8 explicit Tool definitions with compact inline format (+14/-79). Release keeps explicit definitions. | **Architectural decision needed.** The backup version is more compact but the release version is more readable and self-documenting. Recommend keeping the release version unless there's a specific maintainability concern. |

### Category C — Superseded by `rc-1.1` (65 files)

**Every other file** in the backup diff is a formatting-only change. The backup branch carried code formatted with a different linter configuration. The release (`feat/scope-context-option-a-plus-clean`) carries the correctly ruff-formatted version of all these files.

**Do NOT merge from backup.** The release version is the authoritative baseline.

Key examples:

| File | Lines Changed | Pattern |
|------|---------------|---------|
| `construction/overrides/scope_report.py` | +72/-729 | Backup has pre-Option B version (729 fewer lines). **Release is the correct version.** |
| `construction/api/scope_context_api.py` | +2/-28 | Backup removes `get_scope_dimension_permissions` API endpoint. **Release includes this endpoint.** |
| `construction/public/js/vfc_layout_engine.js` | +20/-75 | Formatting-only (line wrapping). |
| `construction/services/boq_import_service.py` | +42/-113 | Formatting-only (line wrapping). |
| `construction/patches/v7_0_migrate_quantity_revisions.py` | +67/-84 | Formatting-only (trailing whitespace, blank lines). |
| `scripts/ai_context_check.py` | +30/-20 | Formatting-only (emoji icon, line wrapping). |
| All other files in the diff | various | Formatting-only. |

### Category D — Archive Only (0 files)

All new files (Category A) are candidates for integration. No files warrant indefinite archiving without review.

---

## 3. Integration Plan (Category A)

### Step 1 — Migrate root-level docs to `docs/`
```bash
git checkout backup/main-worktree-2026-06-20 -- BOQ_EXCEL_IMPORT_SCOPE_FINISH_PLAN.md
git mv BOQ_EXCEL_IMPORT_SCOPE_FINISH_PLAN.md docs/BOQ_EXCEL_IMPORT_SCOPE_FINISH_PLAN.md

git checkout backup/main-worktree-2026-06-20 -- RESTORED_WORK_FOLLOWUP_REPORT.md
git mv RESTORED_WORK_FOLLOWUP_REPORT.md docs/RESTORED_WORK_FOLLOWUP_REPORT.md

git checkout backup/main-worktree-2026-06-20 -- TYPOGRAPHY_HANDOFF_MISMATCH_FINISH_REPORT.md
git mv TYPOGRAPHY_HANDOFF_MISMATCH_FINISH_REPORT.md docs/TYPOGRAPHY_HANDOFF_MISMATCH_FINISH_REPORT.md
```

### Step 2 — Cherry-pick canonical-path docs
```bash
git checkout backup/main-worktree-2026-06-20 -- \
    docs/scope_context_option_b_design.md \
    docs/feature_reviews/BOQ_EXCEL_IMPORT_UI_TEST_PLAN.md \
    docs/feature_reviews/CONSULTANT_REVIEW_REQUEST_BOQ_EXCEL_FINISH.md \
    docs/feature_reviews/CONSULTANT_REVIEW_RESPONSE_BOQ_EXCEL_FINISH.md \
    docs/feature_reviews/evidence/EV-068-wp2-finish-scope.md
```

### Step 3 — Add standalone test files
```bash
git checkout backup/main-worktree-2026-06-20 -- \
    construction/tests/playwright_browser.js \
    construction/tests/playwright_smoke.js \
    construction/tests/test_boq_import_status_smoke.py
```

### Step 4 — Verify no regression
```bash
bench --site v16.localhost run-tests --module construction.tests.test_option_a_plus
bench --site v16.localhost run-tests --module construction.tests.test_scope_context
node construction/tests/test_scope_context_report_filters.js
ruff check construction/overrides/scope_report.py construction/tests/test_option_a_plus.py
```

---

## 4. Files NOT Touched (Rationale)

### `docs/GM_SIGN_OFF_CERTIFICATE.md` — Release-only
This file was created during the release sign-off. It is not in the backup and should remain untouched.

### `docs/scope_context_option_b_acceptance.md` — Release-only
The backup does not have this file. The release version is the authoritative acceptance document.

### All 65 formatting-changed files — Superseded
Every `.py`, `.js`, and `.css` file that differs between backup and release does so only in formatting. The release versions have been linted with `ruff` and tested. Merging the backup versions would reintroduce formatting drift and risk regression.

---

## 5. Risks

| Risk | Mitigation |
|------|------------|
| Some Category A docs reference file paths or branch names from the pre-release state | Review each doc after migration and update paths if needed |
| `test_boq_import_status_smoke.py` is a manual smoke, may require manual setup | Document preconditions in the file header; do NOT add to CI |
| Playwright tests have no CI integration yet | Keep as standalone files; add to CI in a later sprint |

---

## 6. Audit Metadata

- **Auditor:** Development Lead (auto-generated by AI agent)
- **Diff command:** `git diff feat/scope-context-option-a-plus-clean..backup/main-worktree-2026-06-20 --stat`
- **File-by-file review:** conducted for all 76 differing paths
- **Classification method:** manual review of diff content for each file
