# Security & Architecture Remediation — Independent Verification Report

**Application:** Construction ERP custom app for Frappe/ERPNext  
**Verification date:** 2026-08-24  
**Reviewed branch/commit:** `develop` at `b157c15` plus uncommitted remediation changes  
**Framework versions:** Construction `0.0.4`, ERPNext `16.18.3`, Frappe `15.x.x-develop`  
**Verification verdict:** **CONDITIONAL NO-GO — remediation is materially improved, but production readiness is not established**

## 1. Executive assessment

The remediation work closes or substantially reduces several findings from the original audit. Permission guards were added to many BOQ endpoints, import and VO-line services now use savepoints, client-controlled scope disabling is ignored, maintenance endpoints were restricted, generic XLSX export fields are permission-filtered, and the two supplied test commands complete successfully.

The prior report nevertheless overstates the result. The claims that **all vulnerabilities are remediated**, the application is **production ready**, and all controls are **verified** are not supported by the current implementation or tests. Multiple security and integrity risks remain, including a Variation Order approval transaction boundary that can preserve an approved status after line processing fails, cross-BOQ Material Request collisions, residual BOQ child-query IDOR, fake PDF approval acceptance, incomplete stored-XSS remediation, private-file authorization gaps, unescaped PDF output, and unsanitized BOQ spreadsheet exports.

The correct management conclusion is:

> The remediation branch is a strong intermediate build, not a releasable production build. Keep the release blocked until the Critical and High residual findings below are closed with adversarial integration tests.

## 2. What was independently verified

### 2.1 Test execution

The following commands were executed against `v16.localhost`:

```text
bench --site v16.localhost run-tests --app construction \
  --module construction.tests.test_security_audit_remediation

Result: 8 tests passed, 0 failed, 0 errors, 0.394 seconds
```

```text
bench --site v16.localhost run-tests --app construction

Cohort 1: 254 tests passed, 0 failed, 0 errors, 37.847 seconds
Cohort 2: 152 tests passed, 0 failed, 0 errors, 20.493 seconds
Total observed: 406 tests passed
```

The eight remediation tests are included in the second 152-test cohort. They must not be presented as “254 + 8” or added again to the full-suite total.

### 2.2 Static verification

- 187 Python files parsed successfully.
- The modified scope-context and Construction Settings JavaScript files passed `node --check`.
- `git diff --check` found two trailing blank-line defects.
- Targeted Ruff analysis found 12 findings, including an undefined `Any` annotation in `api/export_api.py`.
- No production credential or private-key leak was identified in the earlier source scan.
- No confirmed user-controlled SQL injection was identified in the reviewed paths; the dominant SQL risk is missing or incomplete authorization around raw queries.

### 2.3 Important test-environment side effect

The full test run invoked the white-label migration code and wrote onboarding documents into the Frappe and ERPNext source trees. After the run, Frappe contained new untracked onboarding directories and ERPNext showed 63 modified files. A release test suite must be hermetic: it must not rewrite framework or dependency source code.

These files were not automatically reverted because their pre-test ownership/state was not established.

## 3. Claim-by-claim verification matrix

| Prior report claim | Independent status | Evidence and correction |
|---|---|---|
| Missing BOQ permissions and IDOR fully fixed | **Partial** | `require_boq_access()` and multiple endpoint guards are real improvements. However, the non-root branch of `get_children()` filters only by `parent_structure` and omits the authorized `boq_header`, allowing a cross-header parent substitution. The guard also does not itself enforce the custom active scope promised by its docstring. |
| BOQ import failure is atomic | **Code improved; test invalid** | The commit phase now uses a savepoint and rollback. The regression test uses a nonexistent file, which fails before the savepoint and before any database mutation, so it does not prove rollback. A fault must be injected after at least one structure/item insert. |
| VO approval is fully atomic | **Not fixed end-to-end** | The savepoint begins inside `on_update`, after Frappe has already executed the parent VO `db_update`. `transition_variation_order()` still catches `ValidationError` and returns normally. A line failure can therefore roll back line mutations but leave the VO status as `Approved by Client`, which the request can then commit. |
| Report impersonation is blocked | **Partial** | Non-System-Manager impersonation is blocked by `_resolve_user()`. The regression test calls that helper directly rather than the whitelisted report endpoint. The application import hook still catches monkeypatch installation failures and continues after logging, so the security control remains fail-open. |
| Client `enforce_scope=False` bypass is removed | **Verified for link-query parameter handling** | `_extract_enforce_scope()` strips the parameter and `should_enforce_scope()` uses server settings. This does not fix global write-scope enforcement, which still disables itself on settings errors and only logs project/company mismatches. |
| Material Request generation is idempotent | **Not safely implemented** | The VO row is locked, but lookup uses only `title = "VO Procurement: VO-nnn"`. VO numbers repeat per BOQ Header, so different BOQs can collide and return the wrong Material Request. There is no explicit VO link or database uniqueness constraint. The test pre-creates a same-title MR and proves the collision behavior rather than safe idempotency; it does not call the method twice. |
| Cleanup endpoint is no longer remotely callable | **Verified** | `@frappe.whitelist()` was removed and `System Manager` is required. The function still catches per-record errors and always returns success, which should be corrected for reliable CLI/migration use. |
| Translation tools are restricted | **Substantially verified** | Mutating tools now require `System Manager`, explicit commits were removed, and review-queue inserts no longer bypass permissions. Boolean request parsing still uses `bool(value)`, so strings such as `"false"` are interpreted as true. |
| BOQ structure conversions check permissions | **Implemented; negative integration coverage missing** | Both conversion methods call `self.check_permission("write")`. Add tests as Read-Only and as a user with access to a different BOQ/project. |
| Stored XSS is eliminated | **Not fixed** | Escaping was added to several hierarchy rows and safe DOM construction was added to the scope dropdown. Orphan Project and Department labels/names and quick-create company attributes remain concatenated into HTML without escaping in `construction_settings.js`. |
| Spreadsheet formula injection is eliminated | **Partial** | The generic export path sanitizes formula-leading cells. `BOQExportService` still writes attacker-controlled BOQ titles, Project names, node titles, units and references directly through openpyxl. The test exercises only the helper return value, not the generated XLSX XML or BOQ exports. |
| Export field-level authorization is fixed | **Partial** | Generic exports now intersect requested fields with permitted fields. The automatic path still specially allows standard fields without a documented policy, and BOQ-specific exports use their own static data loader. Add real users with restricted permlevels and inspect generated files. |
| Client approval attachment is validated | **Not fixed** | The code validates a File only if a matching File happens to exist. If no File exists, any string ending in `.pdf` still passes. It does not require attachment to this VO, check read permission, MIME type, magic bytes, privacy, malware state, or immutable hash. |
| Layout API transaction handling is fixed | **Verified for the four edited calls** | Explicit commits were removed from the edited layout methods. Other request handlers in theme, scope, workspace and compatibility APIs still contain explicit commits and were not covered by the claim. |
| Cost import/repricing is fully remediated | **Partial** | Type and row-level permission checks were added and errors trigger rollback. N+1 price lookups remain, upload/ZIP expansion limits remain incomplete, and the tests do not inject a late-row failure or concurrent request. |
| Arbitrary file read is fixed | **Partial** | Obvious traversal and paths outside the site are blocked. The resolver still accepts paths to any file inside the site without checking the corresponding `File` document, owner, privacy, attachment target, or current user’s read permission. Prefix validation should use `os.path.commonpath`, not `startswith`. |
| Theme path traversal is fixed | **Partial** | The generated name is sanitized and writes use `os.replace`. Runtime saves still write generated files into the installed app source tree; an empty/colliding sanitized name is possible. This remains unsafe in immutable or multi-container deployments. |
| Silent failures are eliminated | **Not fixed** | Broad exceptions were changed from `pass` to warning logs, but the operations still continue with stale cost data or incomplete scope validation. Logging a swallowed financial/authorization error is observability, not integrity enforcement. |
| Full test suite proves production readiness | **False** | Tests pass, but security tests contain false positives, a performance test was weakened to time an almost empty calculation while still claiming “100 items,” and the suite mutates framework source. Green results are necessary but not sufficient evidence. |

## 4. Residual issue matrix and exact closure prompts

| Severity | File and location | Residual risk | Exact closure prompt |
|---|---|---|---|
| **CRITICAL — Showstopper** | `api/boq_api.py:340-347`, `services/quantity_revisions.py:251-322`, Frappe `model/document.py:564-572` | VO status is written before `on_update`; the inner savepoint cannot roll it back. The API swallows the validation exception, allowing an approved parent with unapplied/partial lines. | **“Move the transaction boundary to `transition_variation_order` before changing `vo.status`. On any exception from `vo.save`, roll back that outer savepoint and re-raise; do not return a normal error dict after database writes. Add a two-line VO test that fails on line 2, commits the request boundary, then proves the VO remains `Approved by Engineer` and that no revisions, structures, items, or line links exist.”** |
| **CRITICAL — Showstopper** | `api/boq_api.py:417-480` | MR idempotency is keyed by a non-unique title. `VO-001` exists under many BOQs, so one project may receive another project’s MR. | **“Add a `variation_order` Link field to Material Request (or an immutable mapping DocType), create a database unique constraint for active MR generation, lock the VO, query only by that link, and require a dedicated procurement action permission. Replace the existing test with two BOQs both having `VO-001`, two parallel calls for one VO, and assertions that each VO maps to exactly one correct MR.”** |
| **HIGH — Security/Data Risk** | `api/boq_api.py:29-57` | Non-root tree queries do not bind the parent to the authorized header; an accessible header plus a foreign parent name can expose another BOQ’s children and financial rollups. | **“For every tree branch, include `boq_header = %(boq_header)s` and verify the supplied parent belongs to that same header before querying. Add a two-project negative test using an accessible header and an inaccessible parent from the other header.”** |
| **HIGH — Security/Data Risk** | `construction/doctype/variation_order/variation_order.py:96-125` | A nonexistent `fake.pdf` still satisfies the approval gate. | **“Require a real File record; reject when none exists. Require `attached_to_doctype='Variation Order'` and `attached_to_name=self.name`, current-user read permission, PDF MIME type plus `%PDF-` magic-byte validation, private storage, size limits, hash/audit metadata, and malware-scan status where available. Add negative tests for nonexistent, foreign, renamed non-PDF, public, and unauthorized files.”** |
| **HIGH — Security/Data Risk** | `construction/doctype/construction_settings/construction_settings.js:173-226` | Stored XSS remains in orphan rows and quick-create attributes. A malicious master-data name can execute in a System Manager session. | **“Remove all remaining database-value string interpolation from hierarchy HTML. Build elements with jQuery/DOM `.text()` and `.attr()`, including orphan Projects, orphan Departments, and all company quick-create buttons. Add jsdom tests with quotes, `<img onerror>`, SVG, ampersands and Unicode control characters.”** |
| **HIGH — Security/Data Risk** | `api/export_api.py:455+`, `templates/generic_export_pdf.html:180-185`, `services/boq_export_service.py:405-440,529-607`, BOQ PDF templates | Generic/BOQ PDFs render unescaped database values, while BOQ XLSX exports bypass the new formula sanitizer. This permits spreadsheet formulas and HTML/remote-resource injection during PDF generation. | **“Create one shared export-sanitization module used by generic and BOQ exports. Write untrusted XLSX values explicitly as strings and neutralize formula prefixes. Escape every PDF value and prohibit remote/file URL resolution. Test the generated XLSX XML and rendered HTML/PDF using malicious BOQ titles, node titles, Project names, units and references.”** |
| **HIGH — Security/Data Risk** | `services/boq_import_service.py:756-789` | Any site-local private XLSX can be parsed without File permission, exposing other users’ attachments through import/error behavior. | **“Accept only a File document ID or canonical file URL. Resolve it through the File DocType and require read permission, ownership/attachment authorization, expected privacy, XLSX MIME/magic bytes and size/ZIP-expansion limits. Use `os.path.commonpath` as defense in depth and reject raw absolute paths entirely.”** |
| **HIGH — Security/Data Risk** | `overrides/scope_enforcement.py:24-63`, `construction/doctype/boq_header/boq_header.py:21-49`, `construction/__init__.py:3-12` | Scope remains fail-open and mismatches are warnings. Supplying a Project bypasses BOQ scope auto-fill; report-patch installation failure only logs and continues. | **“For protected DocTypes, enforce company/project/cost-center scope on both create and update and throw on mismatch. Fail closed or fail health/startup when scope configuration or the report patch cannot load. Add out-of-scope create/update/read/report tests at the HTTP boundary and cache-revocation tests.”** |
| **HIGH — Performance/Scalability** | `construction/doctype/boq_header/boq_header.py:121-210`, `boq_item.py:41-51`, `boq_structure.py:18-40`, `tests/test_boq_integration.py:247-263` | Full-tree rollups and three updates per structure still run on every item/structure save. The former 100-item benchmark was deleted and now measures only one empty/light query, masking the bottleneck. | **“Restore a real benchmark that creates 100, 1,000 and 10,000 items outside the timed section, then times an actual rollup and records query counts. Add deferred rollups for imports/bulk writes and replace per-structure updates with set-based/bulk SQL. Do not weaken thresholds to make the test green.”** |
| **HIGH — QA/Release Integrity** | `tests/test_security_audit_remediation.py`, `tests/test_migration_survival.py:69-77`, `api/theme_api.py:3173-3202` | Security tests do not exercise their claimed failure points, and full tests rewrite Frappe/ERPNext source files. Results are not hermetic or reliable release evidence. | **“Rewrite remediation tests as end-to-end adversarial tests: inject failures after the first DB mutation, perform actual HTTP/whitelisted calls as restricted users, inspect committed DB state after request completion, verify generated artifacts, and execute real concurrent calls. Mock or isolate white-label migration persistence so tests never write dependency source. In CI, assert all app repositories are clean before and after tests.”** |
| **MEDIUM** | `construction/doctype/boq_cost_analysis/boq_cost_analysis.py:85-106` | Locking only already-approved rows does not serialize the zero-row case; two first approvals can still race. | **“Lock the parent BOQ Item row before checking/superseding analyses, enforce the invariant transactionally, and add a concurrent first-approval test.”** |
| **MEDIUM** | `construction/doctype/construction_theme/construction_theme.py:830-851` | Runtime theme saves mutate installed app assets and sanitized names can collide. | **“Store generated CSS in site-scoped File/storage or generate immutable assets during deployment. Use a stable hash/UUID filename, never write under `apps/`, and test multi-worker/container consistency.”** |
| **MEDIUM** | `construction/doctype/boq_item/boq_item.py:155-173`, `construction/utils/scope_validation.py:19-27`, `construction/__init__.py:3-12` | Exceptions are logged but the operation continues with stale financial data or disabled validation. | **“Catch only explicitly recoverable exceptions. Re-raise database/schema/authorization failures and attach a correlation ID. Add fault-injection tests proving no save succeeds with stale cost or unknown scope state.”** |
| **LOW** | `api/export_api.py:315`, diff formatting | Targeted Ruff finds undefined `Any`, import-order issues and formatting defects; `git diff --check` is not clean. | **“Import `Any` from `typing` or use built-in annotations, run Ruff on the modified modules, fix `git diff --check`, and make both mandatory CI gates.”** |

## 5. Required release acceptance criteria

Production release may be reconsidered only after all of the following are true:

1. Every Critical and High residual issue above is closed in code.
2. VO failure tests prove the parent status and all child effects roll back after the request transaction completes.
3. Material Request linkage is database-backed and collision/concurrency tested across multiple BOQs.
4. Read-Only and out-of-scope users are denied through actual whitelisted/HTTP entry points, not only helper calls.
5. Approval requires a real, authorized, attached and validated PDF File.
6. Both generic and BOQ PDF/XLSX outputs pass injection tests on the generated artifacts.
7. Private-file import authorization and XLSX resource limits are tested.
8. Real 100/1,000/10,000-item rollup benchmarks and query-count limits pass without weakening tests.
9. The complete suite leaves Construction, Frappe and ERPNext worktrees byte-for-byte clean.
10. Ruff, `git diff --check`, Python parsing, JavaScript syntax checks, asset build and migration tests all pass.
11. The remediation is committed and reviewed; the current build contains extensive uncommitted changes and therefore is not a reproducible release candidate.
12. A final three-role UAT is completed with Read-Only, Project Manager/Site Engineer and System Manager/Construction Owner accounts using production-like permissions and data volumes.

## 6. Final release verdict

> **CONDITIONAL NO-GO**
>
> The remediation has moved the application meaningfully closer to release and the current automated suite is green. It has not, however, eliminated all showstopper security and data-integrity risks, and several “verification” tests do not test what their names claim. Production deployment should remain blocked until the acceptance criteria above are independently demonstrated.

