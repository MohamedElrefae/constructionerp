# Security Remediation Seventh-Pass Independent Verification

**Review date:** 2026-08-27  
**Branch:** `release-candidate-v1`  
**Claimed successor SHA:** `371716265bcbae5b024c6c46f69001fd4f7daffd`  
**Verification basis:** checked-out code, `fade6b1..3717162` diff, live schema, isolated counterexample probes, static checks, a targeted adversarial run, and one complete 417-test run. The supplied remediation summary and prior reports were treated only as claims to test.  
**Decision:** **NO-GO — do not tag, merge, or deploy `3717162`.**

## Executive conclusion

Several sixth-pass remediations are real: the complete current-workspace suite is now database/filesystem-hermetic in this run, the scope self-cache is no longer poisoned by an Administrator cross-lookup, the explicit runtime theme commit was removed, the MR migration edits the source link rather than the generated column, and a blocked `scope_report` import leaves the new guard active.

However, the release claim is not yet valid:

1. the new report guard is itself caught-and-continued if it cannot import or install, reproducing the same fail-open condition one layer earlier;
2. the `cost_stream` fix identifies eligible children by `(item_code, supplier)`, so two different streams sharing that pair collide and both are repriced; and
3. the exact claimed SHA does not contain the compatibility exports required by `test_option_a_plus`; the 417/417 run passes only with a tracked, uncommitted modification to `scope_report.py`.

The MR migration is improved but still does not verify the unique index's column definition and explicitly swallows commit failure before resetting Frappe's transaction-write counter. These are incompatible with a fail-fast migration claim.

## Independent verification results

| Check | Result |
|---|---|
| Candidate identity | `371716265bcbae5b024c6c46f69001fd4f7daffd` on `release-candidate-v1` |
| Candidate worktree | **Dirty:** tracked modification in `construction/overrides/scope_report.py` |
| Difference from SHA | Adds `DASHBOARD_REPORTS` and `FINANCIAL_REPORTS` re-exports; not present in `3717162` |
| Static checks on current workspace | `ruff`, Python compilation, JS syntax, `git diff --check`: passed |
| Full current-workspace suite | 417/417 passed: 254 in 75.609s + 163 in 55.442s |
| Targeted adversarial suite | 18/18 passed in 27.665s |
| Cost-analysis suite | 19/19 passed in 3.001s |
| Report/Option A+ suite | 59/59 passed in 14.558s, but used the uncommitted compatibility imports |
| Database after full run | 0 matching test BOQ Headers, Structures, Items, VOs, and MR-reconcile rows |
| Scope setting after run | `enable_scope_context = 0` |
| Public-file manifest | Stable before/after: 129 files, SHA-256 `5fc862a9...c2ed7a` |
| MR live index | UNIQUE on `custom_variation_order_active` on this site |
| Frappe/ERPNext worktrees | Clean |
| Fresh-site/upgrade fixture | Not independently executed |
| Least-privilege HTTP matrix | Not executed |
| 1k/10k BOQ benchmark | Still open |

The hermeticity result is accepted for this run. The second claimed clean run was not repeated because independently reproduced code blockers already prevent a GO.

## Prioritized issue matrix

| Severity | File and location | Risk | Exact fix / prompt for the coding agent |
|---|---|---|---|
| **CRITICAL (Showstopper)** | `construction/__init__.py:16-67`; `construction/overrides/report_guard.py:103-136` | The new guard protects against `scope_report` import failure, but not against failure of `report_guard` itself or failure inside `install_report_guard`. Both are caught and startup continues. A separate-process probe blocked only `construction.overrides.report_guard`; `construction` imported successfully with `_GUARD_OK=False`, `_REPORT_ENFORCEMENT_OK=False`, and the original `frappe.desk.query_report.run` active. The log accurately admitted isolation was disabled, but logging is not fail-closed enforcement. | **Prompt:** “Make inability to import or install `report_guard` a fatal startup/readiness error. In `construction.__init__`, if `_GUARD_OK` is false, raise a dedicated exception and prevent the worker from becoming ready; do not log-and-continue. Do the same if `query_report` cannot be captured. Add separate-process tests that independently block (a) `scope_report`, (b) `report_guard`, (c) `frappe.desk.query_report`, and (d) `inspect.signature`; case (a) may run in guarded degraded mode, while cases (b–d) must fail process readiness. Also restore `_fail_closed_guard` if `_patch_report_access_gates()` fails after `_scope_aware_run` is assigned.” |
| **HIGH (Security/Data Risk)** | `construction/services/cost_database_service.py:190-209`; incomplete regression at `construction/tests/test_cost_analysis_engine.py:783-845` | Eligible rows are indexed by `(item_code, supplier)`, which is not a unique child-row identity. If an M row and L row share the same item and supplier, requesting stream M treats both as M. An isolated no-database probe supplied one eligible M child but the function counted two updates. The regression uses different item codes for the two streams, so it cannot catch this collision. | **Prompt:** “Filter repricing by exact child-row `name`, not `(item_code, supplier)`. Build `eligible_detail_names = {row.name}` from the filtered database rows and skip every `doc.details` child whose `name` is absent. Add a regression with two children sharing the same item code and supplier but using different cost streams; request M and prove the L child's rate, audit fields, modified timestamp, and totals contribution remain unchanged. Repeat for dry-run and atomic rollback.” |
| **HIGH (Release Integrity)** | Commit `3717162`; dirty `construction/overrides/scope_report.py`; `construction/tests/test_option_a_plus.py:369-370` | The exact SHA is not the code that produced the green result. `test_option_a_plus` imports `DASHBOARD_REPORTS` from `scope_report`, but the committed file imports/re-exports only `ALLOWED_REPORTS`. The required two imports exist only as an uncommitted worktree diff. Therefore 417/417 is not reproducible from the claimed immutable candidate. | **Prompt:** “Commit the compatibility exports intentionally (or update all callers to import them from `report_guard`), then require a clean worktree before testing. Record the new exact SHA before execution. Run the suite from a clean detached checkout/archive of that SHA, not from the development worktree, and include `git status --porcelain` plus SHA in the evidence. Never tag a commit whose passing tests depended on uncommitted files.” |
| **HIGH (Security/Data Risk)** | `construction/install.py:1225-1294` | `_ensure_unique_index_or_fail` considers any index with the expected name and `Non_unique=0` healthy; it never verifies `Column_name`, order, or exact definition. A wrongly defined unique index can pass when no duplicates exist and allow future duplicate active VOs. The function also catches and ignores `frappe.db.commit()` failure, then manually sets `transaction_writes=0`, undermining the stated fail-fast behavior and potentially hiding an incomplete transaction. | **Prompt:** “Verify the exact index definition from `information_schema.STATISTICS`: one ordered column, `custom_variation_order_active`, unique BTREE, with no extra columns. Treat any mismatch as unhealthy and rebuild it. Never swallow commit failure and never manually zero `transaction_writes`; let a failed commit abort migration. Separate DML reconciliation and DDL into an explicit migration boundary supported by Frappe/MariaDB. Add tests for a same-named unique index on the wrong column, a multi-column index, and injected commit failure; every invalid state must abort or be repaired deterministically.” |
| **MEDIUM** | `construction/overrides/switch_theme_simple.py:9-96`; override registered in `construction/hooks.py:213-215` | Atomic rollback is improved, but the override is not API-compatible with Frappe's endpoint. Core calls `switch_theme(theme=...)`; the override accepts only `theme_name`, so standard clients can get an unexpected-keyword error. It also stores lowercase `dark`/`light` for standard themes while Frappe stores the Select values `Dark`, `Light`, or `Automatic`. `_authorize_user_write` cannot deny because its inner comparison tests a local value that was just copied from `frappe.session.user`. No endpoint regression covers these behaviors. | **Prompt:** “Make the override signature compatible with core: accept `theme` and optionally normalize legacy `theme_name`, rejecting conflicting values. Preserve exact Frappe values `Dark`, `Light`, and `Automatic`. Simplify authorization to an explicit authenticated-self policy; do not claim a permission check that can never deny. Add RPC-level tests using the same payload as the Desk client, plus Guest denial, invalid theme rejection, custom-theme switching, injected failure rollback, and no interior commit.” |
| **MEDIUM / OPEN RELEASE GATE** | BOQ performance harness and release evidence | Only the bounded 100-item regression exists. The 1k/10k end-to-end elapsed/query/memory/lock evidence, named risk owner, and exact deadline remain absent. The 100-item adversarial test took 22.1 seconds overall in the full run, while its internal ceiling excludes final rollup/reload. | **Prompt:** “Execute the real 100/1k/10k BOQ performance harness against the exact clean successor SHA. Capture complete API lifecycle elapsed time, SQL count, peak memory, lock/wait time, and totals. Either meet predeclared ceilings or obtain written acceptance from a named human owner with an exact deadline, operating limit, rollback trigger, and client impact statement.” |

## Counterexample evidence

### Report guard failure

The probe blocked only `construction.overrides.report_guard` and then imported the app:

```text
GUARD_OK False
ENFORCEMENT_OK False
RUNNER_MODULE frappe.desk.query_report
RUNNER_NAME run
```

This is a running fail-open state. The application must refuse readiness when no guard can be installed.

### `cost_stream` collision

The probe created two in-memory analysis children:

- `ROW-M`: item `ITEM-X`, supplier `None`, stream M;
- `ROW-L`: item `ITEM-X`, supplier `None`, stream L.

Only `ROW-M` appeared in the filtered database-row input, but a request for M produced:

```text
REQUESTED_STREAM M
ELIGIBLE_ROW_IDS ['ROW-M']
DETAILS_COUNTED_AS_UPDATED 2
```

No application data was written by this probe.

### Dirty-candidate mismatch

The worktree diff adds only:

```python
DASHBOARD_REPORTS,
FINANCIAL_REPORTS,
```

to imports in `scope_report.py`. `test_option_a_plus.py` imports `DASHBOARD_REPORTS` from that module. The exact SHA lacks this export, so the green test evidence belongs to a different source state.

## Verified remediations worth retaining

- Blocking only `scope_report` import leaves `_fail_closed_guard` active and protected reports raise `PermissionError`.
- Scope-cache authorization occurs before cache access and privileged cross-user results use a separate key; the previously reproduced self-cache poisoning path is closed.
- The MR reconciler now clears the source `custom_variation_order` on extras instead of writing the generated field, preserves the healthy live index, and the targeted duplicate/replacement test passes.
- The whitelisted theme override no longer calls `frappe.db.commit()` and now rolls back its savepoint before re-raising.
- `test_boq_link_queries` no longer commits setup fixtures.
- Adversarial teardown preserves tracked IDs and checks parents/children after cleanup.
- One complete current-workspace run was hermetic by both database counts and public-file manifest.

## Remaining evidence gates

Even after fixing the code findings, the release still needs:

1. a clean exact successor SHA and tests executed from that immutable snapshot;
2. fresh-site install plus upgrade-site migration using a legacy duplicate-MR fixture;
3. least-privilege real-HTTP testing for Guest, permission-less user, Site Engineer, Project Manager, Accounts User, and System Manager; and
4. closure or formally authorized acceptance of `PERF-BOQ-001` with a named owner and date.

## Final verdict

**NO-GO.** Hermeticity is materially improved and 417 tests pass in the current workspace, but the exact commit is not reproducible, report enforcement still has a fatal fail-open boundary, and the financial repricing filter still crosses streams under a valid duplicate-key data shape. Do not create an immutable release tag for `3717162`.
