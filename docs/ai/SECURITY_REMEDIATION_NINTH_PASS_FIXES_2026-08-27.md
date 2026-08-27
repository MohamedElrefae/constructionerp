# Ninth-Pass Remediation — Fix Implementation & Verification

**Application:** Construction ERP
**Date:** 2026-08-27
**Responds to:** `SECURITY_REMEDIATION_NINTH_PASS_INDEPENDENT_VERIFICATION_2026-08-27.md`
**Candidate branch:** `release-candidate-v1`
**Successor SHA:** `9f48e9048ca6e100e549a5f6eed4069c5aad92cf` (clean worktree)

## 1. Findings fixed

| # | Finding | Verdict | Fix |
|---|---|---|---|
| 1 | **Legacy `construction.overrides.switch_theme.switch_theme` still whitelisted with a looser contract** (MEDIUM — data integrity) | **FIXED** | The legacy module is now a **thin deprecated shim** that delegates entirely to `switch_theme_simple.switch_theme(theme=..., theme_name=...)` and performs **no independent reads or writes** (150 loose lines → 39-line shim). Both dotted routes enforce the identical strict contract. Verified by re-running the ninth-pass counterexample shape (Website User, lowercase `dark`): strict route REJECTS, legacy route now ALSO REJECTS (`ValidationError: Unknown theme 'dark'...`); a valid enum via the legacy route stores the exact `"Dark"` value. `THEME_CONFIGURATION.md` updated to point at the strict module. |
| 2 | **Fatal-guard subprocess test passed for the wrong reason** (MEDIUM — QA false positive) | **FIXED** | Rewritten per the prompt: the child asserts `type(ex).__name__ == "ReportScopeEnforcementError"` AND `"Refusing startup" in str(ex)` (type name, not `str(ex)` which carries only the message), prints a deliberate `EXPECTED_FATAL_GUARD` marker, and exits **exactly 3**. Any other failure exits 2 (`WRONG_FAILURE_MODE`); import success exits 1. The parent runs the subprocess **once** and asserts `returncode == 3`, the marker present, and both `GUARD_IMPORT_FAILED_OK` and `WRONG_FAILURE_MODE` absent. Determinism verified: correct→3, wrong→2, none→1. |
| 3 | **Theme rollback test raised before any write (ineffective)** (MEDIUM — QA) | **FIXED** | Replaced with a TRUE post-write failure injection: the real `frappe.db.set_value` is wrapped so the write **executes** and then a sentinel exception is raised. Asserts the exact sentinel propagates, the spy counter proves the write executed, and the previous DB value is restored by the savepoint rollback. |
| 4 | **Eighth-pass report said "11 tests"** (LOW — report accuracy) | **CORRECTED** | The eighth-pass evidence doc now states "10 new test methods plus one strengthened existing subprocess path" with exact before/after method counts (security 19→23, migration 7→13). |

## 2. New committed regressions

- `test_legacy_switch_theme_route_enforces_strict_contract` — proves the legacy dotted route is a delegating shim (not an alias), rejects the lowercase bypass with `ValidationError`, stores exact enum values, performs no interior commit, and denies Guest.
- Rewritten `test_report_enforcement_refuses_startup_when_guard_cannot_install` — deterministic exit-code contract (3/2/1) as described above.
- Rewritten `test_switch_theme_rolls_back_on_failure` — true post-write failure injection.

## 3. Verification evidence (clean snapshot `9f48e90`, run twice)

```text
Run 1: 254 tests OK (60.4s) + 176 tests OK (41.2s) = 430 — PASS (exit 0)
Run 2: 254 tests OK (60.5s) + 176 tests OK (41.8s) = 430 — PASS (exit 0)
Targeted: adversarial + migration + Option A+ modules — 59 tests OK

ruff check .        — All checks passed
git diff --check    — clean
git status          — CLEAN worktree at 9f48e90

Hermeticity (after runs):
  Security BOQ % / MR Recon % / VO-RECON-TEST-1 links / all named test-titled headers: 0
  enable_scope_context: 0 (baseline restored)
  HTTP probe users: 0
  MR unique index: correctly defined one-column UNIQUE BTREE

Ninth-pass counterexample re-run (closed):
  strict route lowercase "dark" → ValidationError REJECTED
  legacy route lowercase "dark" → ValidationError REJECTED (was: ALLOWED + wrote it)
  legacy route "Dark" → stored exactly "Dark"
```

## 4. Release-gate status (unchanged from eighth pass)

| Gate | Status |
|---|---|
| Fresh-site + legacy-upgrade migration (isolated sites) | **OPEN** — requires MariaDB root credentials unavailable in this environment; upgrade-reconcile behavior is covered by the committed `test_mr_upgrade_reconciles_duplicate_active_material_requests` |
| Complete real-HTTP least-privilege matrix | **PARTIALLY DONE** — scope hierarchy/detail + project display verified over real HTTP (System Manager 200 with data; PM / Site Engineer / no-roles 403). Remaining endpoints (VO lifecycle, BOQ import, MR generation, repricing, reports, private files, theme routes over HTTP) still need the same capture |
| `PERF-BOQ-001` (100/1k/10k evidence or written acceptance) | **OPEN** — requires a named human owner's written acceptance with deadline, operating limit, rollback trigger, client impact statement; cannot be self-accepted |

## 5. Verdict

> **The one reproduced code defect (conflicting legacy theme RPC contract) is eliminated** — both dotted routes now enforce the identical strict enum/auth/rollback/no-commit contract, and the ninth-pass counterexample no longer reproduces. The two false-positive QA tests are rewritten into deterministic, true-failure-mode regressions, and the report-accuracy correction is recorded.
>
> Two complete 430-test runs from the clean `9f48e90` snapshot pass with zero residue, restored scope baseline, and a correctly-defined MR invariant index.
>
> **HOLD for an immutable tag** remains in force pending the three external evidence gates above — all of which need either infrastructure credentials (MariaDB root), broader HTTP capture, or a human owner's written risk acceptance. None are code defects.
