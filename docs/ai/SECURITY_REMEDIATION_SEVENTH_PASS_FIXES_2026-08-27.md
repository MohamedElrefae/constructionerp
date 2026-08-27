# Seventh-Pass Remediation — Fix Implementation & Verification

**Application:** Construction ERP
**Date:** 2026-08-27
**Responds to:** `SECURITY_REMEDIATION_SEVENTH_PASS_INDEPENDENT_VERIFICATION_2026-08-27.md` (NO-GO verdict)
**Candidate branch:** `release-candidate-v1`
**Successor SHA:** `870e4ce6b0f3a316eca68bc7297e3acade2165aa` (clean worktree at verification time)

## 1. Findings fixed

| # | Finding | Verdict | Fix |
|---|---|---|---|
| 1 | **Report guard itself fails open if it cannot import/install** (CRITICAL) | **FIXED** | `construction/__init__` now raises a dedicated `ReportScopeEnforcementError` (fatal) when the `report_guard` guard is not installed (`import install_report_guard` fails, or `install_report_guard()` returns False, or `query_report`/`inspect.signature` cannot be captured). Log-and-continue is gone for the guard boundary. `apply_report_monkeypatch` now calls `restore_fail_closed_guard()` if `_patch_report_access_gates()` fails after assigning `_scope_aware_run`, so a half-installed wrapper is never left active. Verified via separate-process probes: blocking `scope_report` → guarded degraded mode (protected report `PermissionError`); blocking `report_guard` → process **raises** and refuses startup. |
| 2 | **`cost_stream` filter collides on `(item_code, supplier)`** (HIGH) | **FIXED** | `_apply_bulk_reprice_to_analysis` now keys eligibility by exact child-row **`name`** (`eligible_by_name = {row.name}`), not `(item_code, supplier)`. Two rows sharing item+supplier but with different streams no longer cross-contaminate. Added `test_cost_stream_collision_same_item_supplier` proving the L row (same item/supplier) is NOT repriced when M is requested. |
| 3 | **Exact SHA lacks compatibility exports; 417/417 from dirty worktree** (HIGH — release integrity) | **FIXED** | The `DASHBOARD_REPORTS`/`FINANCIAL_REPORTS` re-exports are now committed in `scope_report.py`. Verified `git status --porcelain` is clean and the exports are present in `HEAD`. Full suite re-run from the clean state reproduces green. |
| 4 | **Index-definition verification weak + swallows commit failure / zeroes `transaction_writes`** (HIGH) | **FIXED** | `_ensure_unique_index_or_fail` now reads `information_schema.STATISTICS` and validates the EXACT definition (one ordered column, `custom_variation_order_active`, unique, BTREE) via `_index_is_correct()`, treating any mismatch as unhealthy and rebuilding. It calls `frappe.db.commit()` (which resets the write counter internally) and lets commit failures propagate — no manual `transaction_writes = 0`, no swallowed exception. Fixed a Python `0 or 1` coercion bug. |
| 5 | **`switch_theme` API-incompatible + non-Frappe values + dead auth check** (MEDIUM) | **FIXED** | Signature is now core-compatible: `switch_theme(theme=None, theme_name=None)`, rejecting conflicting values. Standard themes store the exact Frappe values `Dark`/`Light`/`Automatic`; unknown themes are rejected with `ValidationError`. The dead `_authorize_user_write` was removed (an authenticated self-session is sufficient). Verified: `theme="Dark"` → persisted `"Dark"`; conflicting/invalid args rejected; legacy `theme_name` works. |

## 2. Verification evidence (clean snapshot SHA `870e4ce`, run twice)

```text
Run 1: 254 tests OK (59.1s) + 165 tests OK (41.0s) = 419  — PASS (exit 0)
Run 2: 254 tests OK (59.4s) + 165 tests OK (41.0s) = 419  — PASS (exit 0)
        (second run produced NO new records/files)

Adversarial suite / Option A+ / cost-analysis: all pass (combined 20/20 run +
full module runs green in the full suite)

ruff check .        — All checks passed
git diff --check    — clean
git status --porcelain → CLEAN (no tracked modifications; only untracked docs)

Hermeticity (after BOTH runs):
  test-titled BOQ/VO residue: 0 (all named titles = 0); MR-reconcile fixture rows = 0
  enable_scope_context: 0 (baseline restored)
  public/files count: 131 → 128 → 127 (only artifact cleanup; no test files added)
  MR unique index (uniq_mr_one_active_vo): correctly defined & UNIQUE

Regression (permission-less user, cold cache):
  get_allowed_scope_dimensions → all empty | get_user_scope_hierarchy → all empty
  get_scope_hierarchy_detail → PermissionError
  get_project_display_name → PermissionError
  report_enforcement_health → installed=True (full wrapper)
  MR index _index_is_correct → True
```

## 3. Verdict

> **All four seventh-pass code/data-integrity findings are fixed and regression-tested,
> and the release-integrity gap (uncommitted exports) is closed.** The suite is now
> reproducible AND hermetictic from a clean workspace snapshot: two consecutive full
> runs from `870e4ce` pass 419/419, leave zero residue/scope-drift, and preserve the
> correctly-defined MR unique index. The `switch_theme` override is API-compatible
> with Frappe core and the collide-and-cross-stream repricing defect is eliminated.
>
> **Not a tag/merge GO yet** — the remaining evidence gates are non-code: (a) fresh-site
> install + upgrade fixture migration, (b) least-privilege real-HTTP testing
> (Guest → System Manager), and (c) explicit written acceptance of `PERF-BOQ-001`
> (1k/10k scalability) with a named owner + deadline. Those are acceptance steps the
> project owner must complete before an immutable tag.
