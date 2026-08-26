# Fourth-Pass Remediation — Fifth-Pass Independent Verification

**Application:** Construction ERP  
**Verification date:** 2026-08-24  
**Code reviewed:** `develop` at `b157c15` plus the current uncommitted remediation worktree  
**Submitted claim:** `GO-CANDIDATE — security blockers cleared; 409 tests pass`  
**Independent verdict:** **NO-GO — 409 tests pass, but a new cross-scope data disclosure is proven and the test suite commits persistent business records**

## 1. Executive conclusion

This remediation is a substantial improvement over the fourth-pass candidate. The scope bootstrap deadlock is fixed, the Variation Order idempotent response now follows a permission check, workflow audit identities are server-owned, hostile XLSX declarations are pre-scanned before `openpyxl`, theme deletion uses the same sanitized path as creation, and all 409 discovered application tests pass.

Production sign-off is still unsafe. Independent adversarial testing proved that a logged-in user with no read permission on Company, Project, Cost Center, or Department can call whitelisted scope APIs and retrieve the complete hierarchy. The same user received 21 companies and resolved the name of a project they could not read. The root cause is permission-bypassing `frappe.get_all` in security-sensitive hierarchy APIs.

The dedicated security tests are also not tenant-safe. Their explicit commits persist BOQ Headers, Variation Orders, BOQ Items/Structures, and Quantity Revisions, but teardown tracks only files, themes, users, and scope contexts. The test database currently contains many records with the dedicated test titles, including records created by the two independent runs in this verification.

Finally, report-patch installation still fails open, BOQ lifecycle performance remains slow, transaction boundaries and cost repricing remain unresolved, the MR uniqueness decision is deferred, and the candidate is still an uncommitted 65-entry worktree. These are incompatible with the previously defined production release gate.

## 2. Independently reproduced evidence

### 2.1 Static gates

| Gate | Result |
|---|---|
| `git diff --check` | **PASS** |
| `ruff check .` | **PASS — All checks passed** |
| Python compilation across the app | **PASS** |
| JavaScript syntax check across the app | **PASS** |
| `apps/frappe` and `apps/erpnext` | **Clean** |
| App version | **0.0.5** |
| Construction worktree | **65 status entries: 55 tracked + 10 untracked entries** |
| Tracked diff | **55 files, 2,044 insertions, 920 deletions** |

### 2.2 Dedicated adversarial suite

```text
bench --site v16.localhost run-tests --app construction \
  --module construction.tests.test_security_audit_remediation

Running 11 tests
Ran 11 tests in 129.043s
OK
```

The 11-test count is verified. The hostile-XLSX test alone took approximately **126 seconds**, almost all of it before the test starts its elapsed-time measurement.

### 2.3 Complete application suite

```text
bench --site v16.localhost run-tests --app construction

Cohort 1: 254 tests in 71.831s  — OK
Cohort 2: 155 tests in 159.736s — OK
Total:    409 tests in 231.567s — OK
```

**Result:** **409/409 passed, zero failures, zero errors.** The count and successful exit are verified. The submitted timings of 59.97s and 137.3s were not reproduced, but the difference does not change the pass result.

The nominal 100-item BOQ performance test took approximately **26.2 seconds** end to end. It still does not establish acceptable production scalability.

### 2.4 Git and site-file hermeticity

The dedicated and full runs both preserved these baselines exactly:

| Evidence | Before | After |
|---|---|---|
| Construction status hash | `b221ddef...f44949d` | Same |
| Construction diff hash | `a4284f26...aec6863` | Same |
| Site public/private file count | 163 | 163 |
| Site file manifest | `9a7e5427...93a52` | Same |

This is a genuine improvement: Git and site files were hermetic in these runs.

### 2.5 Proven unauthorized hierarchy disclosure

The test account `test_user2@example.com` returned:

```text
Project read permission:     False
Company read permission:     False
Cost Center read permission: False
Department read permission:  False
```

Under that same session:

```python
get_scope_hierarchy_detail()
```

returned a hierarchy containing **21 companies**, including their cost-center, project, and department relationships. Calling:

```python
get_project_display_name("PROJ-0005")
```

returned:

```python
{"project_name": "_Test BOQ Other Project"}
```

Both functions are whitelisted. `get_scope_hierarchy_detail` has no role/permission gate and uses `frappe.get_all`, while `get_project_display_name` deliberately uses `get_all` “without requiring direct Project permissions.” This is a confirmed authenticated IDOR/metadata disclosure.

### 2.6 Proven database pollution from security tests

After the independent dedicated and full runs, the database contained:

| Dedicated-test title/data | Persisted count |
|---|---:|
| BOQ Header — `Tree Rollup Test` | 11 |
| BOQ Header — `VO Approval Concurrency` | 18 |
| BOQ Header — `VO IDOR Guard` | 7 |
| BOQ Header — `VO Segregation Test` | 11 |
| Variation Orders linked to the listed test BOQs | 39 |
| Quantity Revisions linked to `VO Approval Concurrency` | 17 |

Recent rows were created during this verification. The concurrency test commits at setup and in each worker. Teardown commits cleanup but never records or deletes the BOQ/VO/revision graph. The statement that teardown now deletes “only tracked IDs” is incomplete because most committed business IDs are not tracked at all.

### 2.7 Live MR schema

The physical database index exists:

```text
idx_mr_custom_vo(custom_variation_order)
```

The live Custom Field metadata still reports:

```text
search_index = 0
unique = 0
```

The reconciler code is improved, but this candidate has not been migrated into a clean, verifiably reconciled release site, and no one-VO-to-one-current-MR database invariant exists.

## 3. Fourth-pass blocker status

| Previous blocker | Current status | Independent correction |
|---|---|---|
| Scope bootstrap deadlock | **Fixed for the tested lifecycle** | A restricted Project Manager can establish and update the first context; forged writes for another user are denied in the regression test. |
| VO financial-data leak on idempotent branch | **Fixed** | Write permission is checked before the idempotent response. An inaccessible existing VO and a nonexistent VO still return distinguishable errors, so an existence oracle remains. |
| Forgeable VO workflow audit identities | **Substantially fixed** | Persisted audit identities are used for SOD comparisons, current-stage actors are overwritten from the session, and unrelated audit-field tampering is reverted. |
| Pre-load XLSX merged-range DoS | **Production path materially fixed** | ZIP/XML pre-scan now runs before `openpyxl.load_workbook`. Aggregate prescan limits and the adversarial fixture still need correction. |
| Canonical query-side scope | **Improved, but broader scope API security failed** | Query conditions use canonical context and fail closed on settings errors. Separate whitelisted hierarchy/display endpoints bypass all read permissions, and report monkeypatch startup still fails open. |
| Test isolation | **Filesystem fixed; database failed** | Source and site-file manifests are stable. Explicit commits leave large graphs of business test data behind. |
| Theme CSS lifecycle | **Substantially fixed** | Creation/deletion now share the sanitized path and default CSS is removed. Coverage should include spaces, punctuation, Unicode, and failure paths. |
| MR index reconciliation | **Code improved; release state incomplete** | Index exists, but live metadata is still `search_index=0`; uniqueness remains a deferred product decision. |

## 4. Prioritized issue matrix

| Severity | File & location | The risk in simple terms | Exact fix / prompt for the AI coding agent |
|---|---|---|---|
| **HIGH — Security/Data Risk** | `construction/api/scope_context_api.py:25-87,259-346,380-390` | Security-sensitive hierarchy functions use `frappe.get_all`, which bypasses normal Frappe permissions. A user with no read permission on any scope dimension retrieved all 21 companies and a restricted project name. This exposes tenant/project structure and can undermine scope selection authorization. | **“Replace permission-bypassing `frappe.get_all` in all user-facing scope hierarchy and display APIs with permission-enforcing `frappe.get_list`/document checks plus applicable User Permission filters. Restrict `get_scope_hierarchy_detail` to System Manager or an explicit approved management role; otherwise return only the caller's permitted dimensions. Make `get_project_display_name` require Project read permission and active-scope membership, using a non-disclosing denial. Audit every whitelisted function in `scope_context_api.py` for IDOR. Add HTTP tests using a user with `has_permission=False` on Company/Project/Cost Center/Department and assert zero unauthorized names or existence signals.”** |
| **HIGH — QA/Data Integrity** | `construction/tests/test_security_audit_remediation.py:41-88,401-481` | The concurrency test commits the setup and worker transactions, while teardown does not track or delete BOQ Headers, VOs, lines, structures, items, or revisions. Repeated test runs permanently contaminate the database and can distort numbering, reports, performance, and later tests. | **“Make the dedicated suite database-hermetic. Track the exact BOQ Header, Variation Order, child, BOQ Structure, BOQ Item, Quantity Revision, File, theme, user, and scope-context IDs created by every test. For committed concurrency fixtures, delete the complete graph in reverse dependency order from an Administrator cleanup transaction and fail on any residue. Prefer a disposable test site for multiconnection tests. Add before/after database manifests or exact prefix counts and fail if any test-owned row remains.”** |
| **HIGH — Security Control Availability** | `construction/__init__.py:3-11`; `construction/overrides/scope_report.py:107+` | If the report-security monkeypatch fails after a Frappe upgrade or import error, the app logs the error and continues serving requests without that protection. This is still fail-open despite the remediation's “all blockers fixed” statement. | **“Remove the import-time catch-and-continue security architecture. Prefer supported Frappe hooks over monkeypatching. If a patch is unavoidable, make installation idempotent, verify the exact wrapped functions/signatures at startup, expose a failing health check, and stop workers or deny protected reports when installation fails. Add fault-injection tests that force `apply_report_monkeypatch()` to raise and prove no protected report executes unscoped.”** |
| **HIGH — Performance/Scalability** | `construction/construction/doctype/boq_header/boq_header.py:155-201`; BOQ Item/Structure save hooks; `construction/tests/test_boq_integration.py` | The existing 100-item lifecycle still takes about 26.2 seconds. No 1k/10k test, query ceiling, or memory ceiling exists. Large real BOQs may become operationally unusable or time out. | **“Complete the deferred performance gate before rollout. Implement nest-safe rollup deferral for every batch path, reduce whole-tree recomputation for single-row changes, and benchmark real create/edit/import APIs at 100, 1,000, and 10,000 items. Record end-to-end time, SQL query count, lock time, and peak memory; agree production limits and make CI fail when exceeded.”** |
| **MEDIUM — Scope Authorization** | `construction/overrides/scope_enforcement.py:34-75`; `construction/api/scope_context_api.py:40-82` | `_validate_own_scope_context_write` accepts a non-empty dimension whenever the computed allowed set is empty because it checks `value and allowed_set and value not in allowed_set`. The hierarchy helper itself uses permission-bypassing `get_all`. Normal link permission caught the tested case, but the security hook is not independently fail-closed and can be bypassed by server code using permission overrides. | **“Build one permission-correct `get_allowed_scope_dimensions(user)` service and use it in both the API and wildcard hook. Treat an empty allowed set as ‘nothing allowed,’ never ‘allow all.’ Validate `if value and value not in allowed_set: deny`. Do not rely on later Link validation or ordinary document permissions as the primary boundary. Add direct hook tests with empty sets, restricted User Permissions, `ignore_permissions=True`, malformed links, and cross-company dimensions.”** |
| **MEDIUM — Authorization/DoS** | `construction/api/boq_api.py:334-349` | The endpoint locks a VO row before determining whether the caller may access it. Unauthorized callers can distinguish nonexistent names from inaccessible existing names and can acquire locks on known records before being denied. | **“Perform a permission-safe non-locking document lookup and authorization check first, returning the same non-disclosing denial for missing and inaccessible names. Then acquire `FOR UPDATE`, reload status and security-relevant fields, and revalidate permission/scope before mutation or idempotent return. Add tests for missing vs inaccessible responses and an unauthorized lock-contention test.”** |
| **MEDIUM — XLSX/QA Resource Handling** | `construction/services/boq_import_service.py:781-834`; adversarial test lines 486-519 | `_prescan_xlsx` limits individual members but does not independently enforce aggregate uncompressed bytes; the public resolver does, but the parser service should be safe on its own. The test uses `openpyxl.merge_cells` to construct the bomb, consuming about 126 seconds before timing begins, so the claimed fast test is misleading. | **“Enforce overflow-safe aggregate uncompressed bytes inside `_prescan_xlsx` itself. Construct hostile XLSX fixtures by writing minimal ZIP/XML members directly—never ask openpyxl to materialize the bomb. Start timing before fixture handling or separate fixture generation from the timed parser assertion, mock/spy on `openpyxl.load_workbook`, and assert it is never called for rejected input. Keep the complete test under an agreed CI limit such as one second.”** |
| **MEDIUM — Transaction Architecture** | `construction/api/theme_api.py:325,387,512,557,2315,2341,3099`; `construction/api/workspace_api.py:66`; `construction/services/feature_flags.py:37` | Runtime endpoints and services still commit internally. Later failures cannot reliably roll back earlier changes, creating partially applied workflows. This was an explicit production gate, not post-rollout cleanup. | **“Complete the runtime commit audit before production. Remove internal commits from whitelisted endpoints/reusable services, allow Frappe to own request transactions, and move irreversible filesystem/external work to after-commit jobs or tested compensation flows. Add failure injection after every step and assert full rollback.”** |
| **MEDIUM — Performance/Atomicity** | `construction/services/cost_database_service.py:52-136` | Bulk repricing still loads analyses individually and queries every distinct rate key. Per-analysis exception handling can leave a partially repriced dataset. | **“Bulk-load analyses, details, and applicable prices in bounded queries; resolve rates in memory. Define atomic or explicit partial mode. In atomic mode, validate all permissions first and roll back the entire batch on any error. Add query-count ceilings, 1k/10k-detail benchmarks, and fault-injection tests.”** |
| **MEDIUM — Data Integrity/Deployment** | `construction/install.py:1062-1100`; live Material Request Custom Field | The index reconciler is better, but index errors are logged and installation continues, live metadata remains `search_index=0`, and duplicate VO-linked MRs are still allowed at database level. | **“Make migration verify and fail if the required index/metadata cannot be reconciled. Run it on a fresh install and an upgrade fixture and assert live metadata plus `SHOW INDEX`. Decide the cancelled-MR behavior, deduplicate existing mappings, and implement a database-backed one-current-MR-per-VO invariant with concurrency tests.”** |
| **MEDIUM — Release Reproducibility** | Current worktree: `develop` at `b157c15`; 65 status entries | The passing candidate cannot be reconstructed from the stated commit. The release evidence mixes uncommitted source, old persistent test data, and an unmigrated live metadata state. | **“After fixing the remaining blockers, remove test residue on a disposable site, commit only reviewed changes, tag/version the candidate, migrate/build a fresh site, and rerun static checks, all 409 tests, DB/file manifests, schema assertions, secret-history scan, and dependency scan from the exact SHA. Attach raw logs and hashes.”** |

## 5. Verified improvements to retain

- The first-scope bootstrap lifecycle now passes.
- Query scope uses the canonical context and settings failures deny scoped reads.
- Guest no longer receives scoped query rows through the wildcard query condition.
- VO permission now precedes the idempotent financial response.
- VO audit identities and timestamps are controlled server-side for tested transitions.
- VO row locking and exact revision/item/structure assertions pass under two connections.
- XLSX ZIP/XML pre-scan runs before `openpyxl.load_workbook` on the production parser path.
- Theme write/delete path sanitization is centralized.
- The dedicated suite contains 11 tests again.
- All 409 application tests and all static gates pass.
- Git source and site-file manifests are stable across both independent runs.

## 6. Required release gate

Do not issue a production GO until:

1. The whitelisted scope hierarchy/project disclosure is fixed and negative HTTP tests pass.
2. Report enforcement cannot silently disappear on startup failure.
3. Security tests leave zero committed business data, not merely zero files.
4. Scope authorization uses permission-enforcing queries and empty allowed sets deny all values.
5. BOQ 100/1k/10k performance meets agreed time/query/memory limits.
6. Runtime internal commits have an approved and fault-tested transaction model.
7. Cost repricing and MR duplication have approved scalability/atomicity invariants.
8. The exact clean, migrated release commit passes all gates on a fresh disposable site.

## 7. Correct replacement verdict

> **NO-GO — NOT PRODUCTION READY**
>
> The 409-test pass is genuine and the primary fourth-pass defects are materially improved. Production readiness is not established because unauthorized users can retrieve the complete scope hierarchy and restricted project metadata; the security suite commits persistent business records; report protection still fails open at startup; BOQ performance and transaction gates remain unresolved; and no clean reproducible release candidate exists.

