# Security Remediation Eighth-Pass Independent Verification

**Review date:** 2026-08-27  
**Branch:** `release-candidate-v1`  
**Verified snapshot:** `8fdd2967cd3f9eed6a2280975d6a17383d2e02cc`  
**Code-fix commit:** `870e4ce`  
**Basis:** direct source review, isolated counterexample probes, live MariaDB inspection, static checks, one complete test run, and before/after database/filesystem manifests. Supplied summaries and earlier reports were not used as proof.  
**Code verdict:** **Seventh-pass code findings CLOSED.**  
**Release verdict:** **HOLD / NO TAG** until the remaining release-evidence gates are completed.

## Executive conclusion

The seventh-pass remediations are materially correct. The previously reproduced report-guard startup failure now aborts startup, the repricing collision now uses exact child-row identity, the compatibility exports are committed, the MR index helper validates the exact definition and propagates commit failure, and the theme override accepts Frappe's core argument/value contract.

The exact tracked snapshot reproduced 419 passing tests and the run was hermetic: the database residue counts, scope flag, MR index, source diff, and public-file manifest were unchanged after execution.

No new release-blocking code defect was reproduced in the seventh-pass changes. This is not yet an authorization to tag or deploy because fresh/upgrade installation, real-HTTP least-privilege testing, and `PERF-BOQ-001` closure/acceptance remain outstanding. There is also a medium QA-coverage gap: several fixes passed independent probes but do not yet have precise committed regression tests.

## Independent evidence

| Check | Result |
|---|---|
| Exact HEAD | `8fdd2967cd3f9eed6a2280975d6a17383d2e02cc` |
| Tracked source state | Clean; SHA-256 of `git diff --binary HEAD` was the empty hash `e3b0c442...b855` |
| Untracked state | The prior seventh-pass independent audit remains untracked; it is an audit artifact and was not loaded by tests |
| Frappe / ERPNext | Clean |
| Static checks | `ruff`, Python compilation, JS syntax, and `git diff --check`: passed |
| Main cohort | 254/254 passed in 74.304 seconds |
| Legacy/Frappe cohort | 165/165 passed in 52.957 seconds |
| Total | 419/419 passed in 127.261 seconds |
| Scope baseline | `enable_scope_context = 0` before and after |
| Test residue | 0 matching BOQ Headers, Structures, Items, VOs, or MR reconciliation rows after the run |
| Public files | Stable before/after: 127 files; manifest `e41c2b03...0215` |
| MR index | One-column UNIQUE BTREE on `custom_variation_order_active` |
| Fresh-site install | Not run in this independent pass |
| Upgrade fixture | Not run in this independent pass |
| Real-HTTP role matrix | Not run |
| 1k/10k BOQ evidence | Not supplied or executed |

## Seventh-pass finding closure matrix

| Previous finding | Independent result | Status |
|---|---|---|
| Guard import/install failure continued startup | Blocking `report_guard` returned process code 1 with `construction.ReportScopeEnforcementError`; blocking only `scope_report` returned code 0 with `_fail_closed_guard` active | **CLOSED** |
| `cost_stream` collision on shared item/supplier | In-memory counterexample with M and L rows sharing the same item/supplier updated exactly one eligible child; committed database regression also passed | **CLOSED** |
| Green suite depended on uncommitted exports | `DASHBOARD_REPORTS` and `FINANCIAL_REPORTS` are committed in `scope_report.py`; tracked diff is empty | **CLOSED** |
| Weak MR index-definition validation | `_index_is_correct` returned true only for the exact one-column unique BTREE definition and false for wrong/multi-column definitions; live index matches; commit-failure probe propagated `RuntimeError` | **CLOSED** |
| Theme API incompatibility | Live rollback-contained probe accepted `theme="Dark"`, stored exact enum value, rejected conflicting/unknown arguments, changed Dark→Light inside the transaction, and restored Dark after rollback | **CLOSED** |

## Remaining prioritized matrix

| Severity | Area | Risk | Required action / exact prompt |
|---|---|---|---|
| **HIGH RELEASE GATE** | Fresh-site and upgrade migration | The current site proves the post-migration state, not that a clean installation or a legacy upgrade reaches it safely. MariaDB DDL and legacy duplicate-MR reconciliation must be exercised in their actual lifecycle. | **Prompt:** “Create two isolated sites from the exact `8fdd296` snapshot: one blank fresh install and one upgrade fixture with two active MRs linked to the same VO plus a cancelled MR. Capture install/migrate exit codes and logs. Verify deterministic source-link reconciliation, retained cancelled history, exact generated column and unique index, no duplicate active VO links, idempotent second migrate, and no changes to Frappe/ERPNext source. Destroy or archive only those explicitly named disposable sites after evidence approval.” |
| **HIGH RELEASE GATE** | Least-privilege real-HTTP API matrix | Direct Python calls do not prove authentication, CSRF/method handling, Frappe whitelisting, session identity, response normalization, and role enforcement through the deployed HTTP boundary. | **Prompt:** “Run real HTTP requests with separate sessions for Guest, permission-less user, Site Engineer, Project Manager, Accounts User, and System Manager. Cover scope hierarchy/detail/project display, VO create/transition/idempotent paths, BOQ import preview/commit, MR generation, cost repricing filters, report execution, private file access, and theme switching. Record status code, normalized response, database before/after state, and expected permission decision for every case.” |
| **HIGH RELEASE GATE** | `PERF-BOQ-001` | No 1k/10k end-to-end elapsed time, SQL count, peak memory, or lock evidence exists. No named owner or exact acceptance deadline is recorded. | **Prompt:** “Execute the exact-snapshot 100/1k/10k BOQ performance harness through the real API including final rollup and reload. Capture elapsed time, SQL queries, peak memory, lock/wait time, and totals. If ceilings are not met before release, obtain written acceptance from a named human owner with an exact deadline, maximum supported import size, monitoring threshold, rollback trigger, and client impact statement.” |
| **MEDIUM QA** | Missing/weak committed regression assertions | The index helper, commit-failure propagation, and theme API fixes passed independent probes but have no matching committed automated tests. The guard-fatal test only asserts that a success marker is absent; it does not assert nonzero exit or `ReportScopeEnforcementError`, so unrelated subprocess failure could create a false positive. | **Prompt:** “Add focused committed tests for `_index_is_correct` with correct, wrong-column, non-unique, multi-column, and numeric/string metadata; inject `frappe.db.commit` failure and assert propagation before DDL. Add theme RPC tests for `theme=`, legacy alias, conflict, invalid value, Guest, exact enum persistence, rollback, and absence of interior commit. Strengthen the guard subprocess helper to assert nonzero return code and `ReportScopeEnforcementError` text for fatal cases, while asserting zero return code and the expected marker for guarded-degraded cases.” |

## Probe outputs

### Guard startup boundary

```text
BLOCK_SCOPE_REPORT RC 0
GUARDED_DEGRADED_OK

BLOCK_REPORT_GUARD RC 1
construction.ReportScopeEnforcementError: FATAL ... Refusing startup
```

### Repricing and index helpers

```text
COST_STREAM_UPDATED_COUNT 1
INDEX_CORRECT True
INDEX_WRONG_COLUMN False
INDEX_MULTI_COLUMN False
COMMIT_FAILURE_PROPAGATED commit probe
```

### Theme contract

```text
CORE_THEME_STORED Dark
CONFLICT_REJECTED True
UNKNOWN_REJECTED True
THEME_CHANGED_IN_TX Dark Light
THEME_ROLLBACK_VALUE Dark
```

The theme probes explicitly rolled back and left the Administrator value unchanged.

## Release decision

`8fdd296` is a valid **code-remediation candidate** for the findings examined in the seventh pass. It is **not yet a production release candidate eligible for an immutable tag**. Complete the three high release gates, close the regression-test gap, then re-run static checks and the 419-test suite from the exact final clean SHA. If all evidence remains green, that exact SHA can receive the final GO/tag decision.
