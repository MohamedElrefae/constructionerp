# Security Remediation — Second-Pass Independent Verification

**Application:** Construction ERP  
**Verification date:** 2026-08-24  
**Code reviewed:** `develop` at `b157c15` plus the current uncommitted remediation worktree  
**Verdict:** **CONDITIONAL NO-GO — several important fixes are real, but the “all findings remediated / production ready” claim remains unsupported**

## 1. Executive conclusion

This second remediation pass materially improves the application. The outer Variation Order transition savepoint is now correctly positioned, BOQ tree children are bound to their authorized header, cross-BOQ Material Request title collisions are reduced, Construction Settings escaping is more complete, BOQ XLSX values are sanitized, real PDF File linkage is substantially validated, the parent BOQ Item is locked during cost-analysis approval, and the full test run no longer changes the Git status of Frappe or ERPNext.

The attached walkthrough is still not acceptable as a production sign-off. It treats implementation as proof, calls sequential tests concurrency tests, labels tests after scenarios they do not exercise, and claims 100% hermeticity while test files accumulate on the site filesystem. It also omits open risks from the independent verification, including fail-open scope/report enforcement, role-less VO approvals, private-file import bypass through raw site URLs, incomplete PDF escaping, O(N²) BOQ write performance, runtime theme writes into app source, N+1 repricing, explicit commits, and silent financial fallbacks.

The accurate release statement is:

> The remediation is progressing and all discovered tests are green. The build is not yet a reproducible or independently proven production candidate. Release remains blocked by the High findings and invalid verification claims below.

## 2. Reproduced verification evidence

### 2.1 Dedicated remediation suite

```text
bench --site v16.localhost run-tests --app construction \
  --module construction.tests.test_security_audit_remediation

8 tests passed, 0 failed, 0 errors
Observed runtime: 1.034 seconds
```

The count and pass result are verified. The attached report's `0.887s` timing is environment/run-specific and was not reproduced exactly.

### 2.2 Full application suite

```text
bench --site v16.localhost run-tests --app construction

Cohort 1: 254 passed, 0 failed, 0 errors — 63.169 seconds
Cohort 2: 152 passed, 0 failed, 0 errors — 23.558 seconds
Total: 406 passed
```

The 8 remediation tests are part of the 152-test cohort, not additional to the 406 total.

### 2.3 Git worktree stability

Before and after both test commands, SHA-256 hashes of `git status --porcelain=v1 -uall` were identical:

| Repository | Result |
|---|---|
| `apps/frappe` | Clean before and after |
| `apps/erpnext` | Clean before and after |
| `apps/construction` | Dirty before and after with the same hash; unchanged by tests, but **not clean** |

This verifies Git-worktree stability. It does not establish total filesystem hermeticity.

### 2.4 Filesystem pollution

The security tests manually write invalid PDF fixtures under `sites/v16.localhost/private/files`. Database rollback does not remove these files. At verification time, 13 `fake_*.pdf` files had accumulated; the targeted and full runs created additional 22-byte fixtures.

Therefore the statement “100% worktree hermeticity” must be replaced with: **“Git status was stable; site-file cleanup is not hermetic.”**

### 2.5 Static quality gates

- `git diff --check` still reports two blank-line-at-EOF defects.
- Targeted Ruff analysis reports 14 findings.
- Several warnings during the suite report malformed PDF cross-reference data (`incorrect startxref pointer`), because tests accept minimal/header-only PDF fixtures.
- The Construction remediation is extensive and uncommitted; the release artifact is not reproducible from the stated commit.

## 3. Verification of the remediation matrix

| Attached report claim | Status | Independent correction |
|---|---|---|
| VO approval transaction boundary fixed | **Verified in code and fault-injection test** | The outer savepoint now begins before `vo.status` changes and rolls back the parent plus line effects. Improve `raise e` to bare `raise`, use a collision-safe savepoint name, and verify post-request commit behavior, but the original atomicity defect is substantially closed. |
| Cross-BOQ MR collision fixed | **Substantially implemented** | Lookup now uses `custom_variation_order` and a full VO-name title fallback. The custom field is not unique/indexed, and the method selects an arbitrary first Item/Company when source data is missing, which can corrupt procurement data. |
| MR concurrency race fixed and tested | **Implementation plausible; test claim false** | VO `FOR UPDATE` should serialize this endpoint for one VO. The named test is entirely sequential and uses one database transaction; it does not create concurrent workers/connections or prove the race is closed. |
| BOQ tree IDOR fixed | **Verified for header/parent binding** | Parent ownership is checked and every query includes `boq_header`. The test runs as Administrator, so separate restricted-user IDOR/scope coverage is still required. |
| PDF gate fully fixed | **Partial** | Production logic now requires a File, exact VO attachment, read permission, disk presence and `%PDF-` prefix. However, production code contains an `frappe.flags.in_test` branch that manufactures and inserts valid PDF Files during validation. This makes security behavior different under test and hides invalid legacy fixtures. Only five header bytes are checked; malformed PDFs still produce parser warnings. |
| Stored XSS fixed | **Implemented in the reviewed hierarchy UI; not regression tested** | Previously missed orphan and quick-create values are now escaped. “UI Security Escaping Verification” is not an automated test name or recorded test result. DOM construction plus malicious-payload tests are still preferable to string templating. |
| Formula injection fixed | **Substantially verified for BOQ XLSX** | The generated workbook is inspected and BOQ item cells are neutralized. The title assertion is weak because the static label already precedes the malicious value. Generic XLSX sanitization is shared, but not every export route/artifact is tested. |
| All PDF Jinja expressions escaped | **False** | `generic_export_list_pdf.html` remains entirely unescaped. BOQ template `<title>` expressions remain raw. `escape_html_for_pdf()` is imported but unused. The three edited templates are not sufficient coverage of all PDF exports. |
| Private-file import authorization fixed | **False / incomplete** | `_resolve_file_path()` checks File permission only when a File record is resolved. If no File record matches, it still searches raw `/files`, `/private/files`, and site paths and accepts the first existing file without authorization. The named regression test checks only `../../etc/passwd` and `/etc/passwd`; it never creates two users or an unauthorized private File. |
| Scope enforcement is fail-closed | **False** | Settings read errors still set `enabled=False`; no active scope still returns; `ignore_permissions` bypasses the boundary; only company/project are enforced; and the report monkeypatch import still logs and continues on failure. The regression test exercises only BOQ Header creation and may be satisfied by the BOQ controller rather than the wildcard scope hook. |
| Cost-analysis first-approval race fixed | **Implemented; not concurrency tested** | Locking the parent BOQ Item is the correct serialization direction. The cited test submits two analyses sequentially; it does not use independent concurrent transactions. |
| Tests no longer pollute worktrees | **Git-only verified** | Frappe and ERPNext remain clean, and Construction status is stable. Site private-file fixtures still accumulate, so full hermeticity is false. |
| Real 100-item performance benchmark added | **Misleading benchmark** | The test builds 100 items, but times only the final `calculate_total_value()` call. The complete test took 22.4 seconds and uses direct `db.set_value` to bypass normal item save/rollup hooks. It therefore excludes the original O(N²) import/save bottleneck from the asserted interval. |
| All audit findings, including Medium/Low, are remediated | **False** | The report omits unresolved performance, N+1 repricing, runtime app-source CSS writes, fail-open security hooks, role separation, explicit commits, cache revocation delay, dead code and swallowed financial errors. |

## 4. Residual release-blocking matrix

| Severity | File and location | Risk | Exact closure prompt |
|---|---|---|---|
| **HIGH — Security/Data Risk** | `services/boq_import_service.py:756-825` | A raw site-local private file is accepted when no File record resolves, bypassing File permission. XLSX decompression/worksheet limits are also incomplete. | **“Remove raw path fallback from all HTTP import flows. Require a File document ID or exact file URL that resolves to a File record; require session-user read permission and attachment/ownership authorization. Reject raw absolute, `/files`, `/private/files`, and site-relative paths without a File. Add two-user tests with an unauthorized private XLSX plus compressed/uncompressed ZIP-bomb, row, column, merged-range and timeout limits.”** |
| **HIGH — Security/Data Risk** | `overrides/scope_enforcement.py:24-60`, `construction/doctype/boq_header/boq_header.py:21-58`, `construction/__init__.py:3-11` | Security boundaries still fail open on settings/patch errors, missing scope and `ignore_permissions`; cost center is not enforced. | **“Make protected DocType scope validation fail closed for settings/cache errors. Require an active authorized scope where policy demands it; validate company, project and cost center on create and update; do not use ignore_permissions as a scope bypass. Fail health/startup if the report security patch is not installed. Test the wildcard hook directly and through HTTP as an out-of-scope user.”** |
| **HIGH — Business Authorization** | `construction/doctype/variation_order/variation_order.py:74-104`, `api/boq_api.py:326-362` | Any role with VO write permission can execute submit, Engineer approval and Client approval; no distinct approver roles are enforced. | **“Define explicit Submitter, Engineer Approver and Client Approver roles/workflow actions. Validate the session role for every transition, record immutable approver identity/time, prevent self-approval where required, and add negative HTTP tests for each role-transition pair.”** |
| **HIGH — Data Integrity** | `api/boq_api.py:441-508`, `install.py:1062-1078` | Missing line Item/Company data silently falls back to an arbitrary first database record. The VO link is neither unique nor explicitly indexed. | **“Delete all arbitrary `frappe.db.get_value(..., {}, ...)` fallbacks. Require an explicit valid company and item for every line and fail atomically when missing. Add an indexed/unique VO-to-active-MR invariant or mapping table, then test real concurrent calls using independent DB connections and assert item/company/project correctness.”** |
| **HIGH — Security/QA Integrity** | `construction/doctype/variation_order/variation_order.py:122-143`, `tests/test_variation_orders.py` | Production validation manufactures File records only during tests, so tests do not exercise production behavior and can conceal invalid fixtures. | **“Remove every `frappe.flags.in_test` branch from the PDF security validator. Build valid attached PDF fixtures in test setup, clean both File rows and physical files in teardown, and validate actual PDF parsing—not only five magic bytes. Assert the site file directory is unchanged after the suite.”** |
| **HIGH — Output Injection** | `templates/generic_export_list_pdf.html`, `templates/boq_header_print.html:5`, `templates/boq_print_format.html:5` | Some PDF paths still render raw untrusted values into HTML. Depending on the renderer, this can inject markup or remote resources. | **“Audit every PDF/print template and apply context-appropriate escaping to all database and client-controlled values, including titles and generic list cells. Remove unused double-escaping helpers, block remote/file URL loading in PDF generation, and add rendered-HTML/PDF tests with `<img>`, SVG, CSS URL and attribute-breaking payloads.”** |
| **HIGH — Performance/Scalability** | `construction/doctype/boq_header/boq_header.py:121-210`, `boq_item.py:41-51`, `boq_structure.py:18-40`, `tests/test_boq_integration.py:245+` | Normal creation/update still triggers full rollups repeatedly; the current benchmark hides the expensive section outside the timer and took 22.4s for 100 items. | **“Benchmark the complete normal API/import workflow, including hooks, for 100/1,000/10,000 items and record SQL query counts. Add deferred rollups for bulk operations and set-based structure updates. The timed assertion must include item creation/update or explicitly have a separate end-to-end threshold; do not use db.set_value to bypass production hooks.”** |
| **MEDIUM — Concurrency Evidence** | `construction/doctype/boq_cost_analysis/boq_cost_analysis.py:85-110`, `tests/test_cost_analysis_engine.py:270-305` | Parent locking is sensible, but the test is sequential and cannot demonstrate race safety. | **“Add an integration test using two independent connections/transactions synchronized at a barrier, submit competing first approvals, and prove exactly one Approved row remains without deadlock or lost update.”** |
| **MEDIUM — Test Hermeticity** | `tests/test_security_audit_remediation.py:305-320`, site `private/files` | Invalid PDF files are written directly and survive rollback; 13 fixtures have accumulated. | **“Use a temporary/site test directory with guaranteed teardown or register cleanup callbacks that delete both File rows and physical content. Snapshot Git status and site-file manifests before/after CI. Fail CI on any unexplained artifact.”** |
| **MEDIUM — Deployment Architecture** | `construction/doctype/construction_theme/construction_theme.py:830-851` | Theme saves still modify CSS inside the installed app, unsafe for immutable or multi-worker deployments. | **“Move generated theme CSS to site-scoped storage or immutable build artifacts. Never write runtime state under `apps/`; use hashed filenames and test cross-worker consistency.”** |
| **MEDIUM — Performance/Authorization** | `services/cost_database_service.py:53-128`, `services/resource_price_service.py:19-103` | Bulk repricing still performs multiple queries per detail and catches per-analysis failures. | **“Bulk-load latest prices for all relevant keys, update in bounded batches, validate scope before querying, and add query-count limits plus a failure-atomicity test.”** |
| **MEDIUM — Fail-open errors** | `boq_item.py:155-173`, `construction/utils/scope_validation.py`, `construction/__init__.py` | Errors are logged then ignored, allowing stale financial values or disabled security validation. | **“Catch only recoverable exceptions; re-raise database, schema and authorization failures. Add fault-injection tests proving no financial or scoped document save succeeds after these failures.”** |
| **LOW — Release hygiene** | Current Construction worktree and lint output | Construction is not clean, the remediation is uncommitted, `diff --check` fails, and Ruff reports 14 findings. | **“Fix diff/Ruff gates, remove duplicate/unused imports and utilities, commit the reviewed remediation, migrate a fresh site, build assets, and rerun all evidence from the exact release commit.”** |

## 5. Items genuinely closed or materially improved

The following should be credited in the final report once merged and revalidated:

- Outer transaction rollback around VO status transition.
- BOQ tree header/parent binding.
- Removal of remote cleanup whitelisting.
- Server-authoritative handling of the link-query `enforce_scope` parameter.
- Generic permitted-field filtering.
- Spreadsheet sanitization integration for BOQ XLSX cells.
- More complete Construction Settings hierarchy escaping.
- Parent BOQ Item locking for cost-analysis approval.
- Frappe/ERPNext Git worktree stability during the full suite.
- Restoration of a real 100-item data setup, although the measured performance boundary still needs correction.

## 6. Release acceptance criteria

Do not issue a GO verdict until:

1. Every High residual above is fixed and adversarially tested.
2. No production security code changes behavior under `frappe.flags.in_test`.
3. Private imports require authorized File records and enforce resource-expansion limits.
4. VO roles are separated and every transition has positive and negative role tests.
5. MR generation has no arbitrary data fallback and is proven under true concurrency.
6. Every PDF/export route is injection-tested, including generic list PDF.
7. Scope/report controls fail closed and are tested through the actual HTTP/whitelisted boundary.
8. End-to-end 100/1,000/10,000-item benchmarks include normal hooks and query counts.
9. Git repositories and site file manifests are unchanged by the full suite.
10. The exact committed release candidate passes tests, migration, asset build, Ruff and `git diff --check` from a fresh site.

## 7. Correct final verdict

> **CONDITIONAL NO-GO**
>
> The remediation has closed several previously demonstrated defects, and 406 tests pass. The test suite and report still overstate concurrency, private-file authorization, fail-closed scope enforcement, PDF coverage, hermeticity and performance. Production release should remain blocked until the High findings and evidence gaps are resolved on a clean, committed release candidate.

