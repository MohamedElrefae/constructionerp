# Production Verification & Security Remediation — Third-Pass Independent Audit

**Application:** Construction ERP  
**Verification date:** 2026-08-24  
**Code reviewed:** `develop` at `b157c15` plus the current uncommitted remediation worktree  
**Independent verdict:** **NO-GO — the 409-test result is real, but “every finding remediated” and “100% production ready” are false**

## 1. Executive conclusion

The latest remediation closes several serious defects and the claimed test count is reproducible. In particular, the dedicated suite now uses two real threads with independent Frappe/MariaDB connections for Material Request creation, the Variation Order approval path has an outer savepoint, approval PDFs are parsed with `pypdf`, raw site paths are no longer accepted by the BOQ import resolver, and generated theme CSS no longer writes under the Git-tracked app directory.

Those improvements do not justify production sign-off. Independent review found unresolved High-risk defects in export-template escaping, scope fail-closed behavior, Variation Order separation of duties and concurrent approval, hostile XLSX resource handling, and BOQ write performance. The full suite also pollutes site storage, the remediation exists only in a large dirty worktree, and the walkthrough materially misstates what several tests and role rules actually prove.

No confirmed Critical issue such as exposed production credentials, unauthenticated remote code execution, or directly demonstrated unrestricted database compromise was found in this pass. Multiple High findings remain release blockers.

## 2. Reproduced evidence

### 2.1 Adversarial remediation suite

```text
bench --site v16.localhost run-tests --app construction \
  --module construction.tests.test_security_audit_remediation

Running 11 old-frappe-test-class-category tests for construction
Ran 11 tests in 1.712s
OK
```

**Result:** **11/11 passed.** This count is verified.

The Material Request test starts two OS threads. Each thread calls `frappe.init()`, opens its own connection with `frappe.connect()`, invokes the endpoint, commits independently, and destroys its context. Both calls returned the same Material Request name. This is real database concurrency evidence, although the test has no synchronization barrier and does not assert the database row count or the exact `already_existed` flags claimed by the walkthrough.

### 2.2 Full application suite

```text
bench --site v16.localhost run-tests --app construction

Cohort 1: 254 passed — 71.337s
Cohort 2: 155 passed — 24.477s
Total:    409 passed — 95.814s
```

**Result:** **409/409 passed, 0 failures, 0 errors.** The total is verified. The walkthrough's reported **25.7-second total was not reproduced**; the independent run took approximately **95.8 seconds**.

Passing tests prove only their assertions. They do not negate the uncovered paths below.

### 2.3 Repository and filesystem state

| Check | Independent result |
|---|---|
| `apps/frappe` | Clean before and after tests |
| `apps/erpnext` | Clean before and after tests |
| `apps/construction` | Unchanged by tests but already dirty: 52 status entries; 45 tracked files in the diff plus untracked files |
| Construction tracked diff | 1,236 insertions and 717 deletions before untracked content |
| Construction status hash | Stable: `03510c0d...d5c7a8` |
| Construction diff hash | Stable: `b6ee3bfd...8ab34e` |
| Site public/private file count | **127 before full suite → 167 after full suite** |
| Site file manifest | Changed: `b6771870...e1394c` → `271daa65...6ca09` |

The dedicated 11-test suite was site-file hermetic in this run. The full suite was not: test theme saves created or rewrote approximately 50 `public/files/css/theme_*.css` paths and left a net 40 additional files. Moving writes out of `apps/` fixed Git-source mutation, but it did not fix lifecycle cleanup or test hermeticity.

### 2.4 Static checks

| Gate | Result |
|---|---|
| `git diff --check` | Pass |
| Python AST parse across app | Pass |
| `node --check` for modified JavaScript | Pass |
| Ruff on changed/new Python | **Fail: 7 findings** |
| Targeted high-confidence credential patterns | No matches |
| Dedicated secret-history scanner | Not available in this environment; Git-history leak clearance is not proven |

The statement “Static Analysis & Linting: 0 errors” is therefore inaccurate. Only the narrower `git diff --check` claim is verified.

## 3. Claim-by-claim correction

| Walkthrough claim | Status | Independent correction |
|---|---|---|
| Every second-pass finding is remediated | **False** | Scope fail-open paths, PDF/HTML injection, BOQ O(N²) writes, N+1 repricing, explicit commits, test artifacts, and release reproducibility remain open. New review also identified a concurrent VO approval race and hostile merged-range XLSX expansion. |
| All PDF/print interpolation is safely escaped | **False** | The three named templates have many correct `| e` changes, but `generic_export_pdf.html:5` still renders raw values. A live render produced `RAW_SCRIPT_PRESENT=True`. `boq_print_format.html` also places client-controlled column width into an HTML style attribute without type validation or escaping. |
| The XSS regression test proves all three named templates and the stated payloads | **False** | The test renders only `generic_export_list_pdf.html` and `boq_header_print.html`; it never renders `boq_print_format.html` or `generic_export_pdf.html`. It uses `<script>` plus `<img onerror>`, not the walkthrough's claimed SVG/attribute-breaking payload. |
| Material Request concurrency is fixed | **Substantially verified for this endpoint** | The VO row lock serializes calls for one VO and the real two-thread test returned one name. However, `custom_variation_order` is neither indexed nor unique, the lookup performs an unindexed `OR` scan, and the test does not assert one creator/one `already_existed` result or an exact DB count. |
| Theme saves preserve repository immutability | **Verified, but incomplete** | Runtime CSS now goes to site storage and all Git hashes remained stable. The full test suite leaked net 40 site CSS files because `on_trash` clears cache but does not delete generated CSS. |
| Variation Order role authorization matches the walkthrough | **False** | Actual states are `Draft → Submitted → Approved by Engineer → Approved by Client`. Project Manager/Construction Owner submit; Site Engineer **or Project Manager/Construction Owner/System Manager** can perform Engineer approval; Construction Owner/System Manager can Client-approve. The test proves PM submit and Site Engineer Engineer-approval—the opposite of parts of the prose. No self-approval rule is enforced. |
| Private-file isolation is fixed | **Verified for the tested cross-owner private File case** | User B is correctly blocked from resolving User A's unattached private File. Additional attachment-to-target binding and resource-exhaustion cases remain untested. |
| Scope boundary enforcement is fail-closed | **False** | An active mismatched project is rejected. A non-admin with no scope still bypasses wildcard write checks and query filtering; report settings failures pass through to the original unscoped report; startup patch failure is logged and ignored. |
| 409 tests in 25.7 seconds | **Count verified; timing false in independent run** | 409 passed, but the observed total was 95.814 seconds. One nominally passing 100-item performance test alone took 29.5 seconds end-to-end. |
| 100% production ready | **False** | High security/data/availability findings remain, site artifacts leak, static lint is not clean, and no exact committed release candidate exists to reproduce. |

## 4. Prioritized issue matrix

| Severity | File & location | The risk in simple terms | Exact fix / prompt for the AI coding agent |
|---|---|---|---|
| **HIGH — Security/Data Risk** | `construction/templates/generic_export_pdf.html:5`; `construction/templates/boq_print_format.html:164`; `construction/services/boq_export_service.py:75-109` | A malicious document name closes the HTML `<title>` and injects raw markup; this was reproduced in a live render. A caller can also supply a non-numeric `column_config.width`, which is inserted raw into a style attribute. PDF engines may process injected HTML, local/remote resources, or active content. | **“Audit every export and print template by output context. Add `| e` to `doctype` and `docname` in `generic_export_pdf.html`. Never interpolate raw client column widths: parse as a finite number, clamp to an allowed range such as 1–100, and reject strings/NaN/Infinity. Render and test all four templates with title-breaking, attribute-breaking, SVG, `<img>`, CSS URL, `file://` and remote URL payloads. Assert no raw tag/resource survives before calling `get_pdf`, and configure the renderer to deny local and remote resource access unless explicitly allowlisted.”** |
| **HIGH — Security/Data Risk** | `construction/overrides/scope_enforcement.py:32-53`; `construction/overrides/scope_query.py:81-88`; `construction/overrides/scope_report.py:805-812`; `construction/__init__.py:3-11`; `construction/construction/doctype/boq_header/boq_header.py:21-32` | Scope security still fails open. If a restricted user has no active scope, queries and document writes receive no scope condition. If report settings or the import-time security patch fail, the application continues unscoped. This can expose or modify data outside the intended project/company boundary. | **“Define one explicit fail-closed policy for protected users and DocTypes. When scope is enabled, reject protected reads/writes/reports if no valid active scope exists or settings/cache loading fails. Do not return the original unfiltered report on a security-control exception. Make patch-install failure a startup/health-check failure. Align `scope_query`, wildcard `validate`, BOQ controllers and report wrappers to the same policy; include company, project, cost center and department. Add direct hook, ORM list, document insert/update and HTTP report tests for no-scope, stale-scope, settings-error and patch-error cases.”** |
| **HIGH — Business Authorization** | `construction/construction/doctype/variation_order/variation_order.py:74-135`; `construction/construction/doctype/variation_order/variation_order.json:150-194` | Role checks exist, but duties are not separated. A Project Manager can submit and perform Engineer approval; a Construction Owner/System Manager can perform every stage. The same person can approve their own transaction, contrary to a strict multi-party approval workflow. The walkthrough also describes roles/states that do not exist. | **“Write and approve a precise transition matrix for Submitter, Engineer Approver and Client Approver. Enforce one role set per transition, prohibit the same user from approving their own prior stage where segregation of duties is required, and persist immutable user/time fields for every action. Remove broader roles from stage checks unless the owner explicitly accepts them. Add positive and negative endpoint tests for every role-transition pair, including multi-role users, self-approval, direct `doc.save`, API calls and stale-document attempts.”** |
| **HIGH — Data Integrity/Race Condition** | `construction/api/boq_api.py:327-353`; `construction/services/quantity_revisions.py:223-315`; `construction/construction/doctype/variation_order/variation_order.py:292-326` | Client approval does not lock the Variation Order before reading and saving it. Two concurrent approvers can both see an unprocessed line. Quantity changes can create duplicate revisions; New Item lines can create duplicate BOQ structures/items before either transaction writes the marker. The current concurrency test covers Material Requests, not VO approval. | **“At the start of every VO transition, lock the Variation Order row with `SELECT ... FOR UPDATE`, reload the current status and line markers after acquiring the lock, and reject stale transitions. Add database uniqueness/idempotency invariants for one revision per VO line and one created item/structure per New Item line. Add a two-connection barrier-synchronized client-approval test for Quantity Change and New Item, assert exactly one revision/item/structure, and verify rollback/deadlock behavior.”** |
| **HIGH — Availability/Security** | `construction/services/boq_import_service.py:755-899` | The XLSX safety limits can be bypassed by one enormous merged range. The code expands every cell in every merged range before enforcing row/column limits, so a tiny compressed workbook can drive billions of dictionary entries and exhaust memory/CPU. Columns beyond 100 are silently truncated rather than rejected. Legacy OLE files are accepted by the signature check even though `openpyxl` cannot read them. | **“Before loading or expanding cells, reject workbooks whose declared dimensions exceed MAX_ROWS/MAX_COLS. For every merged range, reject or clip ranges outside those limits and enforce a small maximum total merged-cell area, not only a range count. Validate ZIP member count, individual member sizes, total expansion and compression ratios using overflow-safe bounded accumulation. Accept only formats the parser supports. Reject excess columns instead of silently discarding them. Add adversarial XLSX fixtures for one giant merge, many merges, oversized dimensions, XML/ZIP bombs and parser timeout/memory ceilings.”** |
| **HIGH — Performance/Scalability** | `construction/construction/doctype/boq_item/boq_item.py:41-51`; `construction/construction/doctype/boq_structure/boq_structure.py:18-40`; `construction/construction/doctype/boq_header/boq_header.py:130-219`; `construction/tests/test_boq_integration.py:247-288` | Every item/structure save triggers full header and full-tree rollups, followed by three writes per structure. This produces quadratic behavior during imports and bulk creation. The “passing” 100-item test took 29.5 seconds because its one-second assertion times only a final single aggregate call after all expensive hooks have already run. | **“Create an explicit bulk/deferred-rollup context for imports and batch edits, then perform one set-based header/tree rollup at transaction end. Replace three per-row `set_value` calls with a bounded set-based update or bulk write. Benchmark the complete normal API/import lifecycle—not only the last query—for 100, 1,000 and 10,000 items, record SQL query counts and peak memory, and fail CI on agreed end-to-end thresholds.”** |
| **MEDIUM — Data Integrity/Performance** | `construction/api/boq_api.py:441-451`; `construction/install.py:1062-1078`; live `tabMaterial Request` schema | The API-level VO lock currently prevents same-endpoint duplication, but the database has no index or uniqueness rule for `custom_variation_order`. Direct inserts, future code paths, or lock regressions can create duplicates, and the `OR custom_variation_order/title` lookup scans the Material Request table. Live schema inspection confirmed `unique=0`, `search_index=0`, and no index on either lookup column. | **“Add an indexed authoritative VO-to-current-MR invariant. Prefer a unique mapping/current-MR field on Variation Order or a dedicated mapping table that handles cancellation explicitly. Backfill and deduplicate existing records, remove title-based identity after migration, and assert the query plan uses the new index. Keep the VO row lock as defense in depth and enhance the test with a start barrier, exact DB count, one creator result and one `already_existed=True` result.”** |
| **MEDIUM — Performance/Error Handling** | `construction/services/cost_database_service.py:52-129` | Bulk repricing loads each analysis separately, calls rate lookup per detail, and catches each analysis failure into an `errors` list while continuing. Large jobs cause N+1 queries and can leave a partly repriced dataset that looks successful unless the caller inspects every error. | **“Preload all required analyses, details and latest price keys in bounded set-based queries. Validate all inputs and permissions first. Use a single transaction or clearly documented per-batch atomic transactions; if partial mode is allowed, return `success=False` whenever any error occurs. Add query-count ceilings, 1k/10k-detail benchmarks and fault-injection tests proving the selected atomicity contract.”** |
| **MEDIUM — Test/Filesystem Integrity** | `construction/construction/doctype/construction_theme/construction_theme.py:428-452, 805-856`; theme tests | Site-scoped CSS avoids dirtying Git but generated files are never deleted when test themes/documents are removed. The full suite left 40 net additional files, so repeated CI or tenant operations accumulate stale CSS and disk usage. CSS write failures are logged while the document save succeeds, leaving stale UI state. | **“Give generated CSS a managed lifecycle: delete the theme-specific file on `on_trash`, reconcile orphan files, write an authoritative current-file reference, and surface generation failure to the caller or enqueue a retry with health status. Update test teardown to remove generated files. Snapshot the site file manifest in CI and fail on unexplained changes.”** |
| **MEDIUM — Transaction Architecture** | `construction/api/scope_context_api.py:220-239`; `construction/api/modern_form_api.py:160,204,238`; multiple methods in `construction/api/theme_api.py` | Whitelisted request handlers explicitly commit inside lower-level workflows. A later failure cannot roll back earlier changes, making multi-step operations partly applied and harder to compose safely. | **“Remove routine `frappe.db.commit()` calls from whitelisted/service functions and let Frappe own request transaction boundaries. Where an irreversible external/file operation requires a boundary, isolate it behind an after-commit job or document and test the compensation strategy. Add fault-injection tests after each multi-step mutation to prove all-or-nothing behavior.”** |
| **MEDIUM — QA Safety** | `construction/tests/test_security_audit_remediation.py:34-57, 303-370, 540-584` | Test teardown swallows cleanup failures and deletes every Material Request and item in the test database, not only records created by the test. The concurrency and XSS tests also assert less than the walkthrough claims. This can hide leaks and destroy unrelated test fixtures while producing a green result. | **“Track exact IDs created by each test and delete only those records in dependency order. Never swallow teardown exceptions; collect and fail on cleanup errors. Add a connection start barrier and exact result/count assertions to concurrency tests. Parameterize the XSS test across every template and every output context. Add before/after database and filesystem manifests to the suite.”** |
| **MEDIUM — Release Reproducibility** | Current Construction repository: `develop` at `b157c15`, app version `0.0.4`, 52 dirty status entries | The tested product cannot be reconstructed from the stated commit. A deployment made from this working directory can differ from another machine or from the client handover artifact. Ruff also has seven outstanding findings. | **“Resolve Ruff findings, review and remove unrelated changes, commit the exact remediation, tag/version it, migrate a fresh disposable site, build assets, then rerun static checks, 409 tests, adversarial tests, schema/index checks and side-effect manifests from that exact clean commit. Attach command logs and commit SHA to the release evidence.”** |
| **LOW — Hazardous Dead Code** | `construction/run_cleanup.py:1-32`; related one-off source-rewrite scripts | `run_cleanup.py` contains a stale developer-specific absolute path/site, performs destructive SQL immediately when executed, uses string-formatted SQL, swallows errors, and commits partial deletion. This is dangerous AI-era residue even though it is not an HTTP endpoint. | **“Delete obsolete one-off cleanup/source-rewrite scripts from the deployable package. If cleanup remains required, convert it into an idempotent versioned patch with parameterized queries, explicit allowlists, preflight/dry-run output, transaction rollback and tests. Do not execute destructive work at module import/top level.”** |

## 5. Findings genuinely closed or materially improved

The following work should be retained and credited:

- Outer savepoint around the complete Variation Order status change and line processing.
- BOQ tree parent/header IDOR binding.
- Removal of the whitelisted destructive cleanup endpoint.
- Registered-File-only BOQ import resolution and cross-owner private File rejection.
- Approval PDF linkage, permission, file existence, magic-byte and real parser checks; the production `frappe.flags.in_test` manufacturing bypass is removed.
- BOQ XLSX spreadsheet-formula neutralization for the tested cells.
- Removal of arbitrary fallback Item/Company selection in Material Request creation.
- Real two-thread/two-connection Material Request regression test.
- Site-scoped theme CSS storage instead of writes under `apps/construction`.
- Correct escaping in the tested generic-list and BOQ-header print fields.
- Frappe and ERPNext repository immutability during tests.
- No obvious hardcoded credential matched the targeted working-tree patterns used in this pass.

These closures are meaningful; they simply do not close the entire audit.

## 6. Required release gate

Do not issue a production GO until all of the following are true:

1. Every High finding above is fixed and has a negative/adversarial regression test.
2. Scope controls reject no-scope and control-failure cases through real ORM/document/report endpoints.
3. Every PDF template and context is injection-tested, including client-controlled layout configuration.
4. Concurrent VO approval and MR creation are proven with barrier-synchronized independent transactions and database invariants.
5. Hostile workbook dimensions/merged ranges cannot exceed bounded memory or execution time.
6. End-to-end BOQ creation/import performance passes agreed 100/1,000/10,000-item limits.
7. Full-suite database and site-file manifests are unchanged except for explicitly approved fixtures.
8. Ruff, syntax, JavaScript and diff checks all pass.
9. The exact release commit is clean, versioned, migrated and built on a fresh disposable site.
10. A separate secret-history scan and dependency vulnerability scan are attached to release evidence.

## 7. Correct replacement verdict

> **NO-GO**
>
> The remediation is materially improved and all 409 discovered tests pass. Production readiness is not established. High-risk output injection, scope fail-open behavior, Variation Order authorization/concurrency, hostile XLSX resource exhaustion, and BOQ scaling defects remain. The suite also changes site storage, static lint is not clean, and the tested code is not a committed reproducible release candidate.

