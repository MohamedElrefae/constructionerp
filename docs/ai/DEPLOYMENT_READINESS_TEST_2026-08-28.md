# Deployment Readiness Test — End-User Deployment Evidence

**Application:** Construction ERP
**Date:** 2026-08-28
**Snapshot:** `release-candidate-v1` @ `cac1e8a` (clean worktree)
**Answer:** **YES — deployable to end users with documented operating limits.** Two
real deployment-blocking defects were found by this pass and fixed. Two formal
signatures remain with the project owner (below).

## 1. Real deployment-blocking bugs found & fixed (both invisible to unit tests)

| # | Defect | Impact | Fix | Verified |
|---|---|---|---|---|
| 1 | `reprice_cost_analyses` returned **500 for every user** over HTTP (`frappe.request.data` is raw bytes → `'bytes' object has no attribute 'get'`) | Cost-repricing API completely unusable in production | `_read_request_payload()` helper: parse JSON body when it yields a dict, else fall back to `frappe.form_dict` | Re-tested over live HTTP: **200** with correct summary on BOTH JSON and form transports |
| 2 | `bench migrate` **crashed** (`frappe.clear_doctype_cache` does not exist in this Frappe version — called from `setup_variation_order_custom_field`) | Every deployment/upgrade would fail at migrate | Use `frappe.clear_cache(doctype="Material Request")` | `bench --site v16.localhost migrate` → **exit 0**; post-migrate invariants verified (generated column + exact unique index, no duplicate active VOs) |

## 2. Real-HTTP least-privilege authorization matrix (live `bench serve`, token-auth sessions)

| Check | System Manager | Project Manager | Site Engineer | No-roles | Guest |
|---|---|---|---|---|---|
| Scope hierarchy detail (SM-only) | **200** | 403 | 403 | 403 | 403 |
| Project display (read-perm or own-scope) | **200** | 403 | 403 | 403 | 403 |
| Theme strict route, valid enum | **200** | 200 (own) | 200 (own) | 200 (own) | 403 |
| Theme strict route, lowercase `dark` | 417 | 417 | 417 | 417 | 403 |
| Theme legacy shim, lowercase `dark` | 417 | 417 | 417 | 417 | 403 |
| Theme legacy shim, valid enum | **200** | 200 | 200 | 200 | 403 |
| Protected report (General Ledger) | 403* | 403 | 403 | 403 | 403 |
| VO transition — real name | 200† | 200† | 200† | **404** | 403 |
| VO transition — missing name | 404 | 404 | 404 | **404** | 403 |
| Repricing API | **200** | **200** | 403 | 403 | 403 |

\* ERPNext report-role configuration (General Ledger's permitted roles do not include
System Manager on this site) — fail-safe deny, standard setup step before rollout.
† Authorized roles (SM/PM/Site Engineer hold Variation Order write per DocType
permissions) correctly receive real responses; the **existence-oracle protection
applies to unauthorized callers**: the no-roles user gets an **identical 404 for a
real and a missing VO** — confirmed by the matrix.

Both theme dotted routes enforce the **identical strict contract** (the ninth-pass
legacy-route bypass is closed over HTTP too).

## 3. PERF-BOQ-001 — measured evidence (real creation path, deferred rollups + final rollup)

| Items | Total elapsed | SQL statements | Peak RSS delta | Totals correct |
|---|---|---|---|---|
| 100 | 1.66 s | 3,390 | 2.1 MB | ✓ |
| 150 | 2.43 s | 4,957 | 1.5 MB | ✓ |
| 200 | 3.46 s | 6,607 | 1.8 MB | ✓ |
| 300 | 6.03 s | 9,907 | 1.5 MB | ✓ |
| 1,000 | 28.41 s | 33,007 | 6.0 MB | ✓ |
| 10,000 | measured to 8,225 items in 579 s — **aborted** | 271,432 | — | — |

**Root cause identified with data:** per-item cost grows linearly with batch size
(16 ms/item at 25 → 124 ms/item at 8,225) — the NestedSet sibling insert shifts
O(k) rows per insert → **O(n²) total**. Model: `14n + 0.00675n² ms` → 10k ≈ 13.6 min
in a single transaction.

**Documented operating limit (enforced guardrail):** imports up to **1,000 rows per
BOQ complete in <30 s** and are supported; 2,000 ≈ 55 s; larger imports must be
chunked or deferred until the nested-set bulk-insert optimization is implemented.
**Rollback trigger:** abort any single import exceeding 5 minutes.
**Formal acceptance:** the owner must still sign PERF-BOQ-001 acceptance (or
schedule the optimization) — the measured data above is the basis for that decision.

Harness: `construction/perf_boq_capture.py` (`bench ... execute
construction.perf_boq_capture.run --kwargs '{"sizes": [100, 1000], "cleanup": false}'`),
tracks and removes everything it creates.

## 4. Deployment smoke (main site)

- `bench --site v16.localhost migrate` → **exit 0**
- Post-migrate: `custom_variation_order_active` generated column present, `uniq_mr_one_active_vo` exact one-column UNIQUE BTREE verified, no duplicate active VOs
- Full suite after both fixes: **430/430 (254 + 176) OK**
- Hermeticity: all test-titled residue 0, perf-harness residue 0, `enable_scope_context = 0`, public files 126 (no test-generated files)

## 5. What remains with the project owner (not code)

1. **Fresh-site install evidence** — requires MariaDB root credentials to create a disposable site (unavailable in this environment). The upgrade path IS exercised: migrate runs clean on the live site and the duplicate-MR reconcile is covered by `test_mr_upgrade_reconciles_duplicate_active_material_requests`.
2. **PERF-BOQ-001 written acceptance** — accept the documented 1,000-row operating limit (with the rollback trigger above), or schedule the bulk-insert optimization; signature required either way.
3. **Pre-rollout config steps**: grant financial-report roles (e.g. Accounts Manager) to users who must run General Ledger & co. (standard ERPNext setup).

## 6. Verdict

> **GO for end-user deployment** on the current `release-candidate-v1` head, with the
> documented 1,000-row import operating limit and the two owner signatures above.
> The two defects this pass caught (repricing 500, migrate crash) would have broken
> production on day one; both are fixed and regression-verified over the real HTTP
> boundary and a real migrate.
