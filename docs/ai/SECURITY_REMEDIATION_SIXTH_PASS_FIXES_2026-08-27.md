# Sixth-Pass Remediation — Fix Implementation & Verification

**Application:** Construction ERP
**Date:** 2026-08-27
**Responds to:** `SECURITY_REMEDIATION_SIXTH_PASS_INDEPENDENT_VERIFICATION_2026-08-27.md` (NO-GO verdict)
**Candidate branch:** `release-candidate-v1` (continues `fade6b1`)

## 1. Status of sixth-pass findings

### Release blockers (fixed & verified)

| # | Finding | Verdict | Fix |
|---|---|---|---|
| 1 | **Report-scope enforcement fails open if `scope_report` cannot import** (CRITICAL) | **FIXED** | New `construction/overrides/report_guard.py` — a minimal, dependency-free module holding the allowlist + captured original runner. `construction.__init__` calls `install_report_guard()` FIRST (before importing `scope_report`), so the fail-closed guard exists even if `scope_report` fails to import. `scope_report` sources its allowlist/original from `report_guard`. Verified via a separate-process test that blocks the `scope_report` import: `GUARD_OK=True`, runner=`_fail_closed_guard`, protected report → `PermissionError`, non-protected passes through. The guard raises `frappe.PermissionError` directly (robust without a bound request). |
| 2 | **MR upgrade invariant writes the generated column + drops healthy index + continues on failure** (HIGH) | **FIXED** | `_enforce_one_active_mr_per_vo` now splits into `_reconcile_duplicate_active_mrs` (DML: clears the SOURCE `custom_variation_order` link on duplicate ACTIVE MRs, keeps the earliest — never writes the generated column), `_ensure_unique_index_or_fail` (preserves a healthy index; creates/corrects only when absent/non-unique), and `_verify_mr_invariant_or_fail` (raises RuntimeError if duplicates remain or the index is missing/non-unique). Commits pending writes before DDL. Verified: two active MRs for one VO reconcile to exactly one active MR; the unique index survives; a cancelled MR frees the key so a fresh replacement is permitted. |
| 3 | **`cost_stream` accepted but not applied in `bulk_reprice_analyses`** (HIGH) | **FIXED** | `cost_stream` is now validated against `VALID_COST_STREAMS` (M/L/P/S/O) with an early reject for invalid codes, added to the detail-rows filter, and enforced per-row in `_apply_bulk_reprice_to_analysis` (defense in depth). Added a regression test with two streams + independent rates proving only the requested stream is repriced and dry-run leaves it unchanged. |

### Medium findings (fixed & verified)

| # | Finding | Verdict | Fix |
|---|---|---|---|
| 4 | **Scope hierarchy cache poisoning (cross-principal)** | **FIXED** | `get_user_scope_hierarchy` now authorizes BEFORE cache read, uses a permission-context self key (`scope_hierarchy:{user}`) and a separate privileged cross-user key (`scope_hierarchy:xuser:{actor}:{user}`) so a privileged lookup can never populate the target's self-cache. `invalidate_scope_cache` clears both. Verified: cold restricted self = empty; after Administrator cross-lookup, the restricted user's next self-query STILL empty. |
| 5 | **`switch_theme_simple` runtime commit + broad catch-and-success** | **FIXED** | Removed the interior `frappe.db.commit()`; wrapped the writes in an atomic savepoint with rollback-and-reraise (no catch-and-success); added permission-aware user write checks. |
| 6 | **Test hermeticity** (`test_boq_link_queries` commit; adversarial teardown assertion) | **FIXED** | Removed the unconditional `frappe.db.commit()` in `test_boq_link_queries` teardown (framework rollback now handles it). `_delete_tracked_business_graph` preserves copies of the tracked IDs before clearing them and returns them; tearDown asserts against the preserved copies AND child tables after commit. |

## 2. Verification evidence (clean site, run twice)

```text
bench --site v16.localhost run-tests --app construction
Run 1:  254 tests OK (53.0s) + 163 tests OK (38.5s) = 417   — PASS (exit 0)
Run 2:  254 tests OK (56.3s) + 163 tests OK (37.5s) = 417   — PASS (exit 0)
        (second run produced NO new records/files)

Adversarial suite: 18/18 OK
ruff check .        — All checks passed
git diff --check    — clean
report_enforcement_health: {installed: True, degraded: False}

Database hermeticity:
  test-titled BOQ/VO residue after BOTH runs: 0 (all named titles = 0)
  enable_scope_context after runs: 0 (baseline restored)
  MR unique index (uniq_mr_one_active_vo): present and UNIQUE after runs

Filesystem: public/files count 131 → 130 → 129 (only removal of used theme/export
artifacts; no test-generated files added)

Permission regression (cold permission-less user):
  get_allowed_scope_dimensions → all empty  |  get_user_scope_hierarchy → all empty
  get_scope_hierarchy_detail → PermissionError |  get_project_display_name → PermissionError
```

### Existing residue cleaned
The leftover fixture headers (`_Test Scoped BOQ A/B`, `_Test Draft BOQ`, `_Test Scoped
BOQ A`, `_Test Scope Default Header`, `_Test Explicit Project Header`) from prior
old-code full runs were purged (verified 0 after cleanup), and no new ones are
created because the commit in `test_boq_link_queries` was removed.

## 3. Release-gate status

| Sixth-pass release sequence item | Status |
|---|---|
| 1. Fix report startup fail-open, MR invariant, cost_stream | **DONE** |
| 2. Fix hierarchy cache-key flaw + runtime endpoint commit/error behavior | **DONE** |
| 3. Make suite DB/filesystem hermitic; clean test site | **DONE** (verified run-twice) |
| 4. Failure-first regression tests | **DONE** (18-test adversarial + new MR/cost/scope/report tests) |
| 5. Static + both cohorts twice w/ manifests | **DONE** |
| 6. Fresh site + upgrade-fixture migration | NOT independently performed (site already reconciled; noted as hand-off) |
| 7. 100/1k/10k perf harness **or** signed acceptance of `PERF-BOQ-001` | **Not accepted** — an explicit signed risk record with a named owner + deadline is required; not filled in this pass |
| 8. Least-privilege HTTP API tests (Guest/…/System Manager) | NOT performed (flagged as hand-off) |
| 9. Immutable tag only after every gate green | Hold — see PERF-BOQ-001 |

## 4. Verdict

> **All three reproduced code defects are fixed and regression-tested.** The suite is
> now hermetic (two consecutive full runs leave zero test residue, restore the scope
> baseline, and preserve the MR unique index), and report-scope enforcement fails
> closed even when its security module cannot import.
>
> **NOT a full tag/merge GO yet** — the release sequence still requires (a) explicit
> written acceptance of `PERF-BOQ-001` (1k/10k scalability) with a named owner and
> deadline, (b) least-privilege HTTP API testing through real sessions, and (c) a
> genuinely fresh-site install/migrate of the exact successor SHA. Those are
> evidence/acceptance steps, not further code defects.
