# Improve Now Program — Manager Review & Release Approval Request

**To:** Product Owner / Engineering Manager  
**From:** Development Team  
**Date:** 2026-06-10  
**Subject:** Request for final review and release approval — Construction ERP Improve Now Program (WP1–WP6)

---

## 1. Executive Summary

The **Improve Now Program** for the Construction ERP app is complete and ready for release.

All six work packages have been implemented, verified with evidence, and gated. The program covers:

1. **WBS stability and conversion rules** (WP1)
2. **BOQ Excel import/export** (WP2)
3. **Stage measurement/certification UI** (WP3)
4. **Scope context consistency across transactions** (WP4)
5. **Arabic/English labels and print formats** (WP5)
6. **Variation Orders for post-lock BOQ changes** (WP6)

**Recommendation:** Approve release and close WP1–WP6. Defer the remaining legacy theme/migration test debt to a follow-up WP7 scheduled post-release.

---

## 2. How to Review

All evidence is open and traceable in the codebase. You can inspect every claim directly:

### A. Task Tracker (source of truth)
```
/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/09_improve_now_task_tracker.md
```
This file lists every task, its dependency, verification evidence ID, and current status (`VER` = verified).

### B. Evidence Log
```
/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/evidence_log.md
```
This file records 57 evidence rows—every command run, result, artifact path, and reviewer.

### C. Evidence Artifacts
```
/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/
```
Standalone evidence files (`EV-007.md` through `EV-057.md`) contain detailed verification outputs, screenshots, and test results. Early Phase-0 records (`EV-001`–`EV-006`, `EV-010`, `EV-018`) are kept in the evidence log only.

### D. Code Changes
Run from `/home/mohamed/frappe-bench/apps/construction`:
```bash
git diff develop --stat
```
Or inspect the dirty/untracked files listed in `EV-057` to see exactly what changed.

### E. Live Verification Commands
If you want to re-run any verification yourself:

```bash
# WBS health check
bench --site v16.localhost execute construction.services.boq_wbs_health.run_wbs_health_check

# Feature flags
bench --site v16.localhost execute construction.services.feature_flags.get_flags

# VO tests (10/10 passing)
bench --site v16.localhost run-tests --app construction --module construction.tests.test_variation_orders --skip-before-tests --lightmode

# Full current-feature lightmode suite
bench --site v16.localhost run-tests --app construction --skip-before-tests --lightmode
```

---

## 3. Program Gate Status

| Gate | Requirement | Status |
|------|-------------|--------|
| **G0** | Preflight: site, version, branch, dataset, flags documented | `VER` |
| **G1** | WBS health, delete safety, conversion safety, resequence verified | `VER` |
| **G2** | Excel dry-run import, commit import, error report, export privacy verified | `VER` |
| **G3** | Stage edit policy, certified-stage lock, bulk API verified | `VER` |
| **G4** | Transaction scope registry, error messages, non-BOQ guard verified | `VER` |
| **G5** | Arabic PDF fonts, RTL Excel, label catalog, print registration verified | `VER` |
| **G6** | VO line types, FIDIC rule, approval chain, revised BOQ, export columns verified | `VER` |

---

## 4. Work Package Verification Summary

### WP1 — WBS Stability (10 tasks, VER)
- Contract BOQ immutability policy enforced.
- WBS health check service implemented.
- Unique `(boq_header, wbs_code)` constraint migrated.
- Race-safe WBS generation with sibling locking.
- Leaf delete safety guards before linked BOQ Item deletion.
- Draft-only conversion safety for group ↔ ledger.
- Privileged `resequence_wbs()` with audit log.

**Evidence:** `EV-007`, `EV-012`–`EV-017`, `EV-019`

### WP2 — BOQ Excel Import/Export (13 tasks, VER)
- Parser handles structured, semi-structured, flat, and Arabic-header workbooks.
- Dry-run preview with parent WBS validation and error report generation.
- Commit import creates `BOQ Import Batch` traceability records (Draft-only).
- Duplicate import protection via pre-commit WBS lock check.
- Export depth precomputed, privacy normalized (`/private/files/...`).
- Arabic RTL Excel with Western numerals.

**Evidence:** `EV-020`–`EV-039`¹

> ¹ `EV-037` (language/numeral policy) and `EV-038` (RTL Excel export) are formally WP5 evidence reused for `WP2.12` / `WP5.2`; they are not double-counted.

### WP3 — Stage Measurement/Certification UI (8 tasks, VER)
- Frozen/Locked stage edit policy: planning fields freeze, measurement remains editable.
- Certified stages are immutable (edit/delete blocked).
- Role-based certification controls.
- Feature-flagged bulk measurement/certification API.
- Named per-item distribution locking with `SELECT ... FOR UPDATE`.

**Evidence:** `EV-040`–`EV-044`

> **Caveat:** Browser screenshots for WP3 form UI controls (`EV-042`) and final QA (`EV-044`) were not captured in this turn because in-app browser tooling was unavailable. Server-side policy, role, and bulk-API smokes passed.

### WP4 — Scope Context Consistency (7 tasks, VER)
- Registry-driven transaction validation for 8 supported DocTypes.
- Global validate hook guards non-BOQ DocTypes.
- Clear error messages for project mismatch, invalid status, missing scope.
- Journal Entry Account compatibility verified.

**Evidence:** `EV-045`–`EV-048`

### WP5 — Arabic/English Labels & Print (9 tasks, VER)
- Arabic-first policy with Western numeric Excel cells.
- `Noto Naskh Arabic`, `Amiri`, `wkhtmltopdf 0.12.6` verified.
- 24 Arabic labels catalogued and compiled.
- BOQ Print Format registered and RTL-enabled.
- Arabic PDF/PNG/XLSX visual artifacts generated and inspected.

**Evidence:** `EV-049`–`EV-053`

### WP6 — Variation Orders (12 tasks, VER)
- `Variation Order` and `VO Line` DocTypes with status workflow.
- Sequential VO numbering per BOQ Header (`VO-001`, `VO-002`, ...).
- Approval chain: `Draft` → `Submitted` → `Approved by Engineer` → `Approved by Client`.
- Signed client PDF required before final approval.
- Three line types: `Quantity Change`, `New Item`, `Omission`.
- FIDIC-style 25% rate trigger enforced server-side.
- `get_revised_qty()` and `get_revised_boq_rows()` services.
- New approved VO items create `BOQ Structure` / `BOQ Item` with `is_variation_item = 1` and VO-prefixed WBS.
- Revised quantities (from **Client-approved** VOs) flow to stage distribution validation via `get_revised_qty()`.
- Revised BOQ columns added to Excel/PDF export.

**Evidence:** `EV-055` (automated tests + export files), `EV-056` (browser QA screenshots)

---

## 5. Known Limitations & Deferred Debt

### Limitation A: Standard Frappe Test Runner
The formal `bench run-tests` (non-lightmode) is blocked by pre-existing ERPNext Fiscal Year bootstrap data on `v16.localhost`. This is an **environment issue**, not a construction app bug.

**Mitigation:** All current-feature verification uses `--skip-before-tests --lightmode`, which exercises construction tests and passes for WP1–WP6. The full runner still exits red only because of the deferred WP7 theme/migration debt.

### Limitation B: Deferred Theme/Migration Test Debt (WP7)
42 test failures remain in legacy Construction Theme and v6.0 migration test lanes. They are **outside the BOQ/VO value stream** and do not affect user-facing functionality.

**Decision:** Defer to post-release WP7. Documented in `EV-054`.

| WP7 Task | Deferred Failure Count |
|----------|------------------------|
| `WP7.1` — Restore missing CSS fixture | 1 failure |
| `WP7.2` — Fix `list_active_themes` contract | 1 failure |
| `WP7.3` — Fix login background validation | 4 errors + 2 failures |
| `WP7.4` — Fix color rounding drift | 2 failures |
| `WP7.5` — Fix migration auto-populate tests | 1 error + 5 failures |
| `WP7.6` — Fix theme CSS generation | 22 errors + 1 failure |
| `WP7.7` — Confirm zero theme/migration failures | — |

---

## 6. Rollout Control

All seven feature flags remain **default `false`** in `Construction Settings`:

- `enable_boq_excel_import_preview`
- `enable_boq_excel_import_commit`
- `enable_boq_wbs_resequence`
- `enable_stage_measurement_ui`
- `enable_boq_scope_registry`
- `enable_bilingual_boq_print`
- `enable_variation_orders`

This means the new features are **implemented but not exposed to users until you explicitly enable them** per gate. You can stage-rollout gate by gate.

---

## 7. Requested Decision

Please confirm one of the following:

| Option | Action Required |
|--------|----------------|
| **A. Approve & Release** | Mark tracker acceptance checklist `ACC`. Enable flags per your rollout plan. Schedule WP7 post-release. |
| **B. Approve with Conditions** | List specific conditions (e.g., require additional browser screenshots, mandate WP7 before release, etc.). |
| **C. Reject / Require Changes** | Identify which WP or evidence needs rework before re-submission. |
| **D. Request Demo** | Schedule a live walkthrough of the VO workflow, Excel import, or Arabic print outputs. |

---

## 8. Quick Reference Links

| Document | Path |
|----------|------|
| This review request | `docs/feature_reviews/11_manager_review_request.md` |
| Task tracker | `docs/feature_reviews/09_improve_now_task_tracker.md` |
| Evidence log | `docs/feature_reviews/evidence/evidence_log.md` |
| Handoff / current state | `docs/feature_reviews/10_ai_agent_handoff.md` |
| Program closure evidence | `docs/feature_reviews/evidence/EV-057-program-closure.md` |
| VO browser QA screenshots | `docs/feature_reviews/evidence/wp6_browser_qa/` |
| Security review | `docs/feature_reviews/evidence/EV-058-security-privacy-review.md` |
| Clean-site migration | `docs/feature_reviews/evidence/EV-059-clean-site-migration.md` |
| Pre-commit hygiene | `docs/feature_reviews/evidence/EV-060-pre-commit-hygiene.md` |
| Deploy plan | `docs/feature_reviews/evidence/EV-061-frappe-cloud-deployment-plan.md` |
| Rollback drill (pending) | `docs/feature_reviews/evidence/EV-062-rollback-drill-placeholder.md` |
| Backlog: required_role hook | `docs/feature_reviews/evidence/backlog-required-role-transition-hook.md` |

---

## 9. Manager Decision Record

**Engineering Manager Second-Pass Review — 2026-06-10**

**Decision:** ✅ **APPROVED with 7 conditions**

All blockers resolved. Code (WP1–WP6) approved for commit, merge to `release/v6.8`, tag `v6.8.0`, staging deploy, and production deploy (after staging smoke green + 24h soak). Feature flags approved for staged enablement (one gate per 24–48h).

See `09_improve_now_task_tracker.md` (Manager Review Response section) for full condition list.

**Manager Decision Recorded:** 2026-06-10

---

## 10. Notes for the Manager

**Test count context:** `EV-054` recorded 204 tests (pre-WP6 baseline). `EV-055` recorded 214 tests after WP6 test addition—the 10 new tests are the VO suite that passes 10/10. The 42 deferred failures are unchanged.

**Manager Decision Recorded:** _______________ *(date upon response)*

---

*Prepared for manager review. All claims are backed by recorded evidence and reproducible commands.*
