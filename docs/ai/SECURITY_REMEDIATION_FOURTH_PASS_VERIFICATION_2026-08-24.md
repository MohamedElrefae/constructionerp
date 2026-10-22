# Third-Pass Security Remediation — Fourth-Pass Independent Verification

**Application:** Construction ERP  
**Verification date:** 2026-08-24  
**Code reviewed:** `develop` at `b157c15` plus the current uncommitted Construction worktree  
**Submitted claim:** `COMPLETE — 152/152 tests pass, 0 lint errors, Production-ready`  
**Independent verdict:** **NO-GO — static checks pass, but the full suite fails with 45 errors and release-blocking security defects remain**

## 1. Executive conclusion

The submitted walkthrough is not reliable production evidence. Its `152/152` result is only one test cohort, not the full Construction application suite. The independent full run discovered **406 tests**: the 254-test cohort failed with **45 errors**, while the separate 152-test cohort passed. The overall result was therefore **FAILED**, not production-ready.

The most immediate showstopper is the new fail-closed scope implementation. When scope enforcement is enabled, a normal user who has no existing `User Scope Context` cannot save the first context record: the wildcard document hook demands an active context before allowing the context itself to be created. This bootstrap deadlock caused the 45 errors in the full suite.

Independent review also found a proven authenticated Variation Order information-disclosure/authorization bypass, forgeable segregation-of-duties audit fields, broader scope bypass and fail-open paths, pre-validation XLSX denial-of-service exposure, and performance/test-evidence gaps. Several third-pass changes are valuable and should be retained, but they do not support a production GO.

## 2. Independent execution evidence

### 2.1 Static gates

| Check | Result |
|---|---|
| `git diff --check` | **PASS** |
| `ruff check .` from `apps/construction` | **PASS — All checks passed** |
| Python AST parse across the app | **PASS** |
| `node --check` for JavaScript files | **PASS** |
| `apps/frappe` Git state | **Clean before and after tests** |
| `apps/erpnext` Git state | **Clean before and after tests** |
| `apps/construction` Git state | **Already dirty: 62 status entries; 54 tracked files changed plus untracked files** |

The submitted `0 lint errors` statement is now reproducible. Static cleanliness does not override failing integration tests or runtime authorization defects.

### 2.2 Dedicated adversarial module

```text
bench --site v16.localhost run-tests --app construction \
  --module construction.tests.test_security_audit_remediation

Ran 8 tests in 107.959s
OK
```

**Result:** **8/8 passed**, not 152. Approximately 106 seconds were consumed by the hostile-XLSX test's own in-memory workbook construction. The module currently contains exactly eight `test_*` methods.

### 2.3 Full application suite

```text
bench --site v16.localhost run-tests --app construction

Cohort 1: 254 tests in 52.722s — FAILED (errors=45)
Cohort 2: 152 tests in 126.263s — OK
Total discovered: 406 tests — OVERALL FAILED
```

The 45 errors originate from the scope bootstrap path:

```text
set_scope_context()
  -> scope_doc.save()
  -> wildcard scope_enforcement.validate()
  -> no existing active scope
  -> frappe.PermissionError
```

The submitted `Ran 152 tests in 108.9s — OK` excerpt therefore omits the failing 254-test cohort and does not match the independently observed 152-test cohort time.

### 2.4 Repository and site side effects

| Check | Before full run | After full run | Result |
|---|---:|---:|---|
| Construction status hash | `65c803e5...d3fbd` | Same | Source tree unchanged by tests |
| Construction diff hash | `f60c0f25...b7c` | Same | Tracked diff unchanged by tests |
| Site public/private file count | 166 | 167 | **Net +1 file** |
| Site file manifest | `15ddf341...3361e` | `f3356aa1...a002` | **Changed** |

Multiple theme CSS files were created or modified during the run. Moving runtime CSS out of the app repository protects Git immutability, but the suite is not site-filesystem hermetic.

### 2.5 Direct authorization reproduction

Using a logged-in test user without demonstrated Variation Order privileges, calling:

```python
transition_variation_order("BOQ-2026-0274-VO-002", "Approved by Client")
```

returned:

```python
{
    "success": True,
    "name": "BOQ-2026-0274-VO-002",
    "status": "Approved by Client",
    "total_contract_delta": 7000.0,
    "already_at_status": True,
}
```

This occurs because `boq_api.py:343-351` returns the idempotent response before the write-permission check at lines 353-356. It is a proven authenticated IDOR/information disclosure and an authorization-order defect.

## 3. Claim-by-claim correction

| Component | Independent status | Correction |
|---|---|---|
| 1. Template XSS and column widths | **Substantially verified** | All four templates are now exercised, dangerous values are escaped, and widths are converted to bounded numeric values. This is a genuine improvement. Renderer network/local-resource restrictions are still not demonstrated. |
| 2. Fail-closed scope enforcement | **FAILED / release blocker** | The first scope cannot be established, queries fail open on settings-read errors, finance-report roles bypass all scoped document reads/writes, `ignore_permissions` bypasses scope, `Project` is globally skipped, and query scope is taken from session defaults rather than the canonical context record. |
| 3. VO segregation of duties | **Incomplete and bypassable** | Role checks exist, but client-supplied audit identities are preserved with `value or session.user`. A caller can prepopulate `submitted_by` or approval-user fields and defeat identity-based checks. System Manager is also expressly exempt. |
| 4. VO concurrency and locking | **Locking improved; endpoint authorization failed** | `SELECT ... FOR UPDATE` is present and serializes the transition path. However, the idempotent branch precedes permission checks and leaks VO data. The concurrency test verifies only one revision, not one created item/structure, and accepts either one or two successful requests. |
| 5. XLSX merged-range protection | **Incomplete / DoS remains** | Limits are checked only after `openpyxl.load_workbook`. A crafted XLSX can force expensive merged-cell materialization during load before application validation runs. The test calls the helper on an already-built worksheet, not the real upload/parse path. |
| 6. BOQ rollup optimization | **Improved, not proven scalable** | The rollup is set-based and import deferral was added. Normal item/structure saves still trigger whole-header/tree aggregation. The new test builds only six items, contains no timer or query ceiling, and does not create the claimed 50-node tree. A separate 100-item lifecycle test took about 21.8 seconds. |
| 7. Material Request index | **Partially verified** | The live database has `idx_mr_custom_vo`, but the existing Custom Field still reports `search_index=0` and `unique=0`. Installation only sets `search_index` when creating a missing field, and index errors are silently swallowed. |
| 8. Cost database bulk reprice | **Partially improved; N+1 remains** | Exact repeated keys are memoized, but each analysis is loaded separately and every distinct detail key still calls `get_suggested_rate`. Per-analysis exceptions allow partial writes. This is caching, not a bulk preload. |
| 9. Theme CSS cleanup | **Incomplete** | Safe test names are removed. Real theme names are autonamed from `theme_name`; the writer sanitizes the filename while `on_trash` uses the raw name, so names containing spaces or punctuation leave orphan CSS. Errors are swallowed and `theme_current.css` is not reconciled. |
| 10. Clean request transactions | **Verified only for the two named files** | Explicit commits were removed from `scope_context_api.py` and `modern_form_api.py`. Multiple whitelisted handlers in `theme_api.py`, plus other runtime services, still commit internally. The new adversarial teardown also commits a global setting. |
| 11. Dead code removal | **Verified** | `construction/run_cleanup.py` is deleted and the dedicated absence test passes. |
| 12. Adversarial suite | **Misrepresented and unsafe** | It contains 8 tests, not 152. The dedicated suite shrank from 11 to 8 and the full discovery count fell from 409 to 406. Teardown swallows errors, deletes every Material Request in the site, and commits global configuration. Several tests do not exercise or measure what their names and walkthrough claim. |

## 4. Prioritized issue matrix

| Severity | File & location | The risk in simple terms | Exact fix / prompt for the AI coding agent |
|---|---|---|---|
| **CRITICAL — Showstopper** | `construction/overrides/scope_enforcement.py:60-69`; `construction/api/scope_context_api.py:147-153,220-224` | With scope enabled, an ordinary user needs an existing scope in order to save the record that creates their first scope. The feature locks users out and caused 45 full-suite errors. | **“Fix scope bootstrap atomically. Exempt only the narrowly defined `User Scope Context` create/update path from the generic scoped-document requirement, while validating that `doc.user == frappe.session.user` unless an explicitly authorized administrator acts, validating every requested dimension against User Permissions, and preventing arbitrary context writes. Do not use a blanket `ignore_permissions` bypass. Add HTTP and direct-service tests where a new restricted user establishes, changes, clears, and attempts to forge another user's context. Run the complete app suite and require zero errors.”** |
| **HIGH — Security/Data Risk** | `construction/overrides/scope_enforcement.py:29-31,48-69`; `construction/overrides/scope_query.py:47-60,64-104`; `construction/__init__.py:3-11` | Scope protection can be bypassed through `ignore_permissions`, Guest, broad finance-report roles, the global Project exclusion, or a settings-read failure. Read enforcement uses possibly stale session defaults instead of the canonical context. Users may see or modify data outside their assigned company/project. | **“Create one centralized scope-policy service used by document hooks, query conditions, reports, and endpoints. Define explicit protected DocTypes and explicit service-only bypass tokens; never reuse report-view exemptions for document writes. Fail closed when configuration or canonical context loading fails. Remove Guest and broad finance-role bypasses unless a documented policy explicitly requires them. Derive conditions from the validated canonical `User Scope Context`, synchronize defaults only as a cache, and test no-scope, stale-default, settings-error, Project, finance-role, Guest, `ignore_permissions`, background-job, and migration paths.”** |
| **HIGH — Authorization/IDOR** | `construction/api/boq_api.py:334-356` | Any authenticated caller who guesses a Variation Order name and target status can reach the already-at-status branch before permission validation and receive its name, status, and financial delta. This was reproduced directly. | **“Move `frappe.has_permission('Variation Order', 'write', doc=vo, throw=True)` immediately after the locked row is found and before comparing or returning status. Avoid disclosing whether an inaccessible name exists; use the application's standard permission-safe response. Apply scope checks before all returns. Add endpoint tests for unauthorized users against both normal and already-at-target paths and assert identical non-disclosing denial.”** |
| **HIGH — Business Integrity** | `construction/construction/doctype/variation_order/variation_order.py:130-160`; `variation_order.json` audit fields | Read-only form fields are not an immutable server audit trail. The code keeps caller-provided `submitted_by`, `engineer_approved_by`, and `client_approved_by`, allowing forged identities to evade segregation-of-duties comparisons. | **“Treat all workflow audit fields as server-owned. On each valid state transition, overwrite the relevant actor and timestamp from `frappe.session.user` and server time; reject any client alteration outside that transition. Compare against the persisted pre-transition document, not incoming values. Decide and document whether System Manager may override SOD, require an explicit audited override reason if so, and add malicious-payload tests that prepopulate or alter every audit field through REST, `doc.save`, and the transition endpoint.”** |
| **HIGH — Availability/Security** | `construction/services/boq_import_service.py:153-173,889-940`; `construction/tests/test_security_audit_remediation.py:451-472` | `openpyxl` loads the workbook before application range limits are checked. A small compressed file declaring a huge merge can consume excessive CPU/memory during library parsing. The current test spends about 106 seconds building the fixture and never invokes `parse_workbook` on the saved file. | **“Pre-scan the XLSX ZIP and worksheet XML with bounded streaming before calling `openpyxl.load_workbook`. Enforce member count, per-member and total uncompressed bytes, compression ratio, XML size, dimensions, merge count, and total merge area before object materialization. Then parse in read-only or an isolated resource-limited worker where compatible. Replace the in-memory helper test with a hand-crafted small hostile XLSX passed through the real File resolution and `parse_workbook` path; assert rejection within a strict time and memory budget.”** |
| **HIGH — Performance/Scalability** | `construction/construction/doctype/boq_header/boq_header.py:155-201`; `boq_item.py:41-51`; `boq_structure.py:18-40`; `boq_import_service.py:352-374`; adversarial test lines 507-534 | Set-based SQL improves one aggregation, but normal saves repeatedly aggregate the full tree. The claimed 50-node performance proof is actually six items with no duration or query assertion. Observed 100-item setup remains slow. | **“Make rollup deferral a nest-safe context manager that restores the previous flag in `finally`, use it in every batch/import path, and perform one bounded rollup at transaction end. Avoid complete-tree aggregation for a single-item edit where an ancestor-path delta is safe. Add end-to-end benchmarks for 100, 1,000, and 10,000 items through real APIs, with elapsed-time, SQL-query-count, and peak-memory ceilings. Make the test fail when thresholds are exceeded.”** |
| **HIGH — QA/Release Evidence** | `construction/tests/test_security_audit_remediation.py:35-73`; entire dedicated test module | Teardown deletes all Material Requests and items in the site, hides cleanup exceptions, changes a global setting with an explicit commit, and then rolls back. Tests can destroy unrelated fixtures, conceal leaks, and affect later cohorts. The report then presents a selected green cohort as the full result. | **“Rewrite test isolation: generate a per-test prefix, track every created document/file, and delete only those exact IDs in dependency order. Never swallow teardown exceptions; fail with collected cleanup errors. Restore settings and flags to their captured prior values without committing global state inside unit teardown. Restore the removed security regressions. Have CI publish every cohort and fail the job if any cohort fails; never report a partial cohort as the total suite.”** |
| **MEDIUM — Data Integrity/Operations** | `construction/install.py:1062-1084`; live `Material Request.custom_variation_order` metadata | The physical index exists on this site, but migration behavior is not reconciliatory: existing field metadata remains unindexed in DocType metadata, exceptions are ignored, and duplicates remain allowed. Other code paths could create multiple MRs for one VO. | **“Make installation/migration idempotently reconcile the existing Custom Field and verify the physical index instead of swallowing errors. Decide the authoritative one-VO-to-MR rule, deduplicate existing data, and enforce it with a database-backed invariant that handles cancelled MRs explicitly. Add schema assertions and an `EXPLAIN` test after fresh install and upgrade from an existing field.”** |
| **MEDIUM — Performance/Atomicity** | `construction/services/cost_database_service.py:52-136` | The method avoids only duplicate exact lookups. Distinct rows still cause repeated rate queries and analysis loads; caught errors can leave a partly updated batch. | **“Replace per-analysis/per-key lookup with bounded bulk queries for analyses, details, and latest applicable prices, then resolve rates in memory. Validate permissions and inputs before mutation. Choose all-or-nothing transaction semantics or an explicit partial mode; in atomic mode re-raise on any failure. Add query-count ceilings, 1k/10k-detail benchmarks, and fault-injection rollback tests.”** |
| **MEDIUM — Filesystem Integrity** | `construction/construction/doctype/construction_theme/construction_theme.py:448-460,836-855`; `construction_theme.json:4` | Theme names can contain spaces/punctuation. CSS creation sanitizes the name, but deletion uses the raw name, leaving orphaned files. Deleting an active/default theme can also leave `theme_current.css` stale, and cleanup errors are silent. | **“Use one shared `get_theme_css_path(name)` helper for both write and delete, including identical sanitization and path containment checks. On trash, reconcile or remove `theme_current.css` when it points to the deleted theme. Do not silently swallow deletion errors; log with the exact path and fail or queue retry according to policy. Add tests with spaces, Unicode, punctuation, default-theme deletion, failed unlink, and before/after site manifests.”** |
| **MEDIUM — Transaction Architecture** | `construction/api/theme_api.py:325,387,512,557,2315,2341,3099`; `construction/services/feature_flags.py:37`; `construction/api/workspace_api.py:66` | The two named APIs were cleaned, but other request/service code still commits internally. A later failure may be unable to roll back earlier database changes, producing partially applied workflows. | **“Audit all non-migration production `frappe.db.commit()` calls. Remove commits from whitelisted endpoints and reusable services so Frappe owns the request transaction. Move filesystem or external effects to an after-commit job or implement tested compensation. Document the small set of legitimate migration/batch boundaries and add fault-injection tests after every step of multi-write endpoints.”** |
| **LOW — Technical Debt/Test Accuracy** | `construction/tests/test_security_audit_remediation.py:385-446,451-472,507-534` | Test names and prose overstate what is proven: concurrent New Item creation does not assert one structure/item, the XLSX test bypasses the parser, and the rollup test creates six items with no performance metric. This encourages false confidence. | **“Rename tests to their exact guarantees or strengthen them. For VO concurrency assert exact revision, BOQ Item, BOQ Structure, processed-marker, result, and error counts. For XLSX call the public import path. For rollups build the stated node counts and measure the complete lifecycle. Include the executed test names/counts and raw timings in the generated release report.”** |
| **LOW — Release Reproducibility** | Current Construction worktree; `construction/__init__.py:1` | The tested code is not represented by a clean commit and the app version remains `0.0.4`. Another machine cannot reproduce the exact candidate from `b157c15`. | **“After all blockers pass, review and commit only the intended remediation, bump the release version, build/migrate a fresh disposable site, and rerun static checks, the complete test suite, schema checks, secret/dependency scans, and filesystem/database side-effect manifests from the exact clean commit. Attach the SHA and logs to the handover.”** |

## 5. Changes genuinely verified and worth retaining

- Jinja escaping and numeric width sanitization across the four exercised export/print templates.
- Variation Order row locking before the normal mutation path.
- Re-entrant revision existence checks as defense in depth.
- Set-based BOQ structure rollup and deferred rollups during import.
- Strict OpenXML magic-byte handling and bounded post-load worksheet/merge processing.
- Runtime theme CSS stored under the site rather than Git-tracked app directories.
- Explicit commits removed from `scope_context_api.py` and `modern_form_api.py`.
- `run_cleanup.py` removed.
- Ruff, diff, Python syntax, and JavaScript syntax gates pass.
- Frappe and ERPNext repositories remain clean.

## 6. Required release gate

Do not issue a production GO until all of these conditions are met:

1. Fix the scope bootstrap deadlock and rerun the complete suite with zero failures/errors.
2. Remove or formally constrain every scope bypass and prove one canonical fail-closed policy through real HTTP/ORM/document/report paths.
3. Check Variation Order permission and scope before every response, including idempotent paths.
4. Make workflow audit actors immutable and add malicious-field SOD bypass tests.
5. Reject hostile XLSX declarations before `openpyxl` object materialization under a measured resource ceiling.
6. Establish real end-to-end BOQ performance limits and pass them at representative production sizes.
7. Make tests tenant-safe and hermetic; database settings and site-file manifests must return to their captured baseline.
8. Reconcile the MR schema/index and define a database-backed duplication invariant.
9. Remove unjustified runtime commits and prove rollback atomicity with injected failures.
10. Produce a clean, versioned commit and run all release evidence from a fresh site using that exact SHA.

## 7. Correct replacement verdict

> **NO-GO — NOT PRODUCTION READY**
>
> Static checks pass and several remediations are materially improved. However, the full Construction suite fails with 45 scope-related errors; a normal user cannot establish the first scope; an authenticated Variation Order IDOR was reproduced; workflow audit identities are forgeable; hostile XLSX validation occurs too late; and performance, test isolation, and release reproducibility remain inadequate. The `152/152` result is a partial cohort, not the full application result.

