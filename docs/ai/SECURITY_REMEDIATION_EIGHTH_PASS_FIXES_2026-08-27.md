# Eighth-Pass Remediation — Verification & Fixed Evidence

**Application:** Construction ERP
**Date:** 2026-08-27
**Responds to:** `SECURITY_REMEDIATION_EIGHTH_PASS_INDEPENDENT_VERIFICATION_2026-08-27.md`
**Verdict reached:** **Code findings CLOSED.** Remaining items are release-evidence gates (not code defects).

## 1. What the eighth pass found

No new release-blocking code defect was reproduced in the seventh-pass changes. The
remaining items were:

- **MEDIUM QA**: the index helper, commit-failure propagation, and theme API fixes
  passed independent probes but lacked matching committed regression tests; the
  guard-fatal subprocess test only asserted a success-marker absence (a false
  positive was possible).
- **3 HIGH release gates**: fresh-site/upgrade migration; least-privilege real-HTTP
  matrix; `PERF-BOQ-001` closure/acceptance.

## 2. QA coverage added this pass (committed)

| Test | Location | Coverage |
|---|---|---|
| `test_index_is_correct_accepts_exact_definition` | `test_migration_survival.py` | Exact one-column unique BTREE accepted |
| `test_index_is_correct_rejects_wrong_column` | same | Wrong column rejected |
| `test_index_is_correct_rejects_non_unique` | same | Non-unique rejected |
| `test_index_is_correct_rejects_multi_column` | same | Multi-column rejected |
| `test_index_is_correct_handles_int_and_str_metadata` | same | Int/str metadata + the `0 or 1` coercion bug covered |
| `test_ensure_unique_index_propagates_commit_failure` | same | Injected `frappe.db.commit` failure → aborts (propagates) |
| `test_switch_theme_accepts_core_theme_arg_and_stores_enum` | `test_security_audit_remediation.py` | `theme=` accepted, exact enum persisted, no interior commit |
| `test_switch_theme_rejects_conflict_and_unknown` | same | Conflict + unknown value rejected |
| `test_switch_theme_guest_denied` | same | Guest denied |
| `test_switch_theme_rolls_back_on_failure` | same | Failed write rolls back prior writes in the savepoint |
| Guard subprocess helper strengthened | same | Asserts exact return code + `ReportScopeEnforcementError` text for the fatal case; zero-RC + marker for the guarded-degraded case |

## 3. Release gates — status

### Gate #2 — Least-privilege real-HTTP matrix (partially completed)
A real `bench serve` was run and the security-critical scope endpoints were exercised
over HTTP with separate sessions:

| Session | Login | `get_scope_hierarchy_detail` | `get_project_display_name` | Decision |
|---|---|---|---|---|
| System Manager | 200 | **200** (full data) | **200** (actual project name) | allowed |
| Project Manager | 200 | **403** (PermissionError) | **403** (PermissionError) | denied |
| Site Engineer | 200 | **403** | **403** | denied |
| No-roles user | 200 | **403** | **403** | denied |

Confirmed the HTTP boundary genuinely enforces the permission decision (privileged
sees data; restricted roles get an error, not empty data). Probe users were removed
after the run; server stopped.

### Gate #1 — Fresh-site + upgrade migration
NOT executed here — it requires MariaDB root credentials to create a disposable site,
which are not available in this environment. The **upgrade reconcile** behaviour
(duplicate active MRs → source-link dedup, retained cancelled history, exact unique
index, idempotent second run) IS already covered by the committed regression
`test_mr_upgrade_reconciles_duplicate_active_material_requests`.

### Gate #3 — `PERF-BOQ-001`
Not executed / NOT self-acceptable. The verifier requires written acceptance from a
named human owner with an exact deadline, operating limit, rollback trigger, and
client impact statement. This is an organizational sign-off, not a code change.

## 4. Verification evidence (exact-clean workspace)

```text
Full suite: 254 tests OK (61.3s) + 175 tests OK (41.0s) = 429 — PASS (exit 0)
Adversarial suite: 23/23 OK
Migration survival: 13/13 OK (6 new index/commit tests)
ruff check .            — All checks passed
git diff --check        — clean
git status --porcelain  — CLEAN (no tracked modifications)

Hermeticity:
  test-titled BOQ/VO residue: 0        | HTTP probe users: 0
  enable_scope_context: 0 (baseline)   | MR unique index: correctly defined & UNIQUE
```

## 5. Verdict

> **All seventh-pass code findings are CLOSED and now carry committed regression
> tests.** The suite is hermetic and reproducible from a clean workspace. The
> least-privilege HTTP boundary for the scope endpoints was independently verified
> (privileged allowed, restricted roles denied).
>
> **Still HOLD for an immutable tag** until the owner completes: (a) the fresh-site +
> upgrade-fixture migration (requires MariaDB root), (b) the remaining least-privilege
> HTTP coverage for VO/BOQ/cost/report/theme endpoints, and (c) written acceptance of
> `PERF-BOQ-001` with a named owner + deadline. These are evidence/acceptance steps,
> not code defects.
