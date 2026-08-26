# Security Remediation Sixth-Pass Independent Verification

**Review date:** 2026-08-27  
**Candidate branch:** `release-candidate-v1`  
**Candidate commit:** `fade6b146f2c831a607c92065a9ddd25bb8b6da4`  
**Review basis:** checked-out source, live MariaDB schema, isolated adversarial probes, static analysis, and independently executed tests. Earlier remediation reports were not treated as evidence.  
**Decision:** **NO-GO — do not tag, merge, or deploy this candidate yet.**

## Executive conclusion

The candidate contains several real improvements and all 413 automated tests pass. That is not enough to issue a production GO. Independent probes reproduced three high-risk defects that the green suite does not cover:

1. report-scope enforcement fails open if its security module cannot be imported during worker startup;
2. the upgrade reconciler cannot deduplicate existing Material Request conflicts because it tries to write a generated column, then logs and continues if the unique invariant cannot be installed; and
3. the public bulk-repricing API accepts `cost_stream` but does not apply it, so a filtered repricing request can alter rows outside the requested stream.

The full test run also committed BOQ fixtures into the test database and changed the site's public-file manifest. The 1k/10k BOQ benchmark remains unexecuted, has no documented named risk owner or deadline, and therefore is not an accepted risk.

The current commit must not receive an immutable release tag. Fix the release blockers, add regression coverage that reproduces the failures described below, rerun on a clean fresh site, and then repeat this verification.

## Independent evidence summary

| Check | Independent result |
|---|---|
| Source identity | `release-candidate-v1` at `fade6b146f2c831a607c92065a9ddd25bb8b6da4` |
| Construction tracked diff after tests | Empty; SHA-256 of `git diff --binary HEAD` was `e3b0c442...b855` |
| Frappe and ERPNext worktrees | Clean |
| Construction worktree | No tracked modifications, but pre-existing untracked reports/documentation remain |
| Static checks | `ruff check .`, Python compilation, JavaScript syntax, `git diff --check`: passed |
| Main test cohort | 254/254 passed in 58.316 seconds |
| Legacy/Frappe test cohort | 159/159 passed in 38.982 seconds |
| Total | 413/413 passed in 97.298 seconds |
| Adversarial suite | 15/15 passed independently in 21.528 seconds |
| Scope baseline | `Construction Settings.enable_scope_context = 0` after tests |
| MR live invariant | `uniq_mr_one_active_vo` exists and is UNIQUE on this already-reconciled site |
| Public-file manifest | Changed from 162 files (`b2e072ce...c5f46`) to 131 files (`abb23ca3...2574`) during the full run |
| Database hermeticity | Failed: the full run added five BOQ Headers, three BOQ Structures, and three BOQ Items at 2026-08-27 03:34:33 |
| Fresh-site installation | Not independently performed; still an open release gate |

## Verified improvements

The following changes were substantiated by code inspection and targeted execution:

- The BOQ rollup deferral context manager is nested-call safe and restores the previous flag in `finally`.
- The import path defers per-item rollups and performs an explicit final rollup.
- The hostile-XLSX pre-scan runs before `openpyxl.load_workbook`, applies aggregate uncompressed-size limits, and the test uses a handcrafted ZIP fixture plus a workbook-loader spy.
- The Variation Order transition path performs authorization before returning an idempotent result, takes a row lock, revalidates after the lock, and normalizes inaccessible/missing denials.
- The public hierarchy-detail and project-display endpoints deny a permission-less user in the tested cold-cache path.
- The adversarial test class removed its own BOQ/VO/revision records in the independent targeted run and restored `enable_scope_context=0`.
- The database rejects a second non-cancelled Material Request for the same Variation Order on the current reconciled schema; a cancelled request does not occupy the generated unique key.
- The application, Frappe, and ERPNext tracked source trees were not modified by the test execution.

These verified improvements should be retained while fixing the remaining defects.

## Prioritized issue matrix

| Severity | File and location | The risk, in plain language | Exact fix / prompt for the coding agent |
|---|---|---|---|
| **CRITICAL (Showstopper)** | `construction/__init__.py:10-36`; `construction/overrides/scope_report.py:134-192` | If `construction.overrides.scope_report` itself fails to import, the code logs that protected reports are denied but never installs the deny guard. An isolated startup probe produced `_REPORT_ENFORCEMENT_OK=False` while `frappe.desk.query_report.run` remained the original unscoped runner. A worker can therefore start and serve protected reports without the intended tenant filter. | **Prompt:** “Make report-scope enforcement fail closed across module-import and early-initialization failures. Do not catch-and-continue when the security module cannot import; either make worker readiness/startup fail or install a guard from a minimal module that has no dependency on `scope_report`. Prefer supported Frappe hooks over an import-time monkeypatch. Add a separate-process startup test that deliberately blocks importing `construction.overrides.scope_report` and proves the process refuses readiness or that every protected report raises `frappe.PermissionError`. Do not pass the test by manually assigning `_degraded_guard_run`.” |
| **HIGH (Security/Data Risk)** | `construction/install.py:1145-1199` | Upgrade deduplication writes `NULL` into `custom_variation_order_active`, but that field is a STORED generated column. MariaDB recomputes it from `docstatus` and `custom_variation_order`, so both conflicting rows remain active. Unique-index creation then fails with error 1062; the exception is only logged and migration continues without the promised invariant. A temporary-table reproduction confirmed exactly this behavior. The function also drops a healthy unique index on every reconciliation, creating an avoidable enforcement gap and table-lock risk. | **Prompt:** “Rewrite `_enforce_one_active_mr_per_vo` as a fail-fast, idempotent schema migration. Resolve legacy duplicates by changing source/business fields according to an approved data policy—such as cancelling the duplicate MR or clearing its `custom_variation_order` link—not by updating the generated column. Preserve a healthy existing unique index; create it only when absent or incorrect. After reconciliation, query for duplicate active VOs and verify the exact unique index definition. If either check fails, raise and abort migration. Add an upgrade test that starts with two active MRs linked to one VO and verifies deterministic remediation, a working unique constraint, and allowed replacement after cancellation.” |
| **HIGH (Security/Data Risk)** | `construction/api/cost_database_api.py:84-118`; `construction/services/cost_database_service.py:15-148`; `construction/construction/doctype/boq_cost_analysis_detail/boq_cost_analysis_detail.json:22` | The whitelisted endpoint documents and accepts `cost_stream`, but the repricing service never reads that parameter after receiving it. A request intended to reprice only Materials, Labor, Plant, Subcontract, or Overhead can update other streams. That is a financial-data integrity error. No regression test covers the advertised `cost_stream` filter. | **Prompt:** “Implement `cost_stream` filtering in `bulk_reprice_analyses` against `BOQ Cost Analysis Detail.cost_stream`. Build a `parent -> eligible child names/rows` index and update only eligible rows. Reject invalid stream codes. Add a database regression test with at least two streams and independently changing rates; call the public/service API with one stream and prove the other stream, totals, modified timestamps, and audit trail remain unchanged. Test dry-run and atomic rollback with the same filter.” |
| **MEDIUM** | `construction/api/scope_context_api.py:119-197` | The cache key is only `scope_hierarchy:{user}`. A privileged cross-user lookup uses `ignore_permissions=True` and stores the full hierarchy under the target user's key. The target user then receives that privileged result before any permission check. Reproduction: cold self-query returned 0/0/0/0; after Administrator queried the same user, self-query returned 21 companies, 46 cost centers, 13 projects, and 276 departments. This is a hierarchy disclosure and can also influence consumers of the cached hierarchy. | **Prompt:** “Prevent cross-principal scope-cache poisoning. Never cache an `ignore_permissions=True` result under a key consumed by the target user's self-query. Prefer computing the hierarchy under the target user's permission context; otherwise use a separate actor/evaluation-mode cache key and keep privileged management data out of user caches. Perform authorization before cache lookup. Add a regression test: cold restricted user gets empty sets, Administrator inspects that user, then the restricted user's next request must still get empty sets.” |
| **MEDIUM** | `construction/overrides/switch_theme_simple.py:8-83`; active override in `construction/hooks.py:211-215` | A live whitelisted endpoint still commits at line 68, contradicting the stated runtime-commit gate. If later request work fails, the theme mutation cannot participate in the request rollback. The broad exception handler then performs another write and returns a success message, which can hide partial or inconsistent state. | **Prompt:** “Remove `frappe.db.commit()` from the whitelisted theme override and let the request transaction own commit/rollback. Replace the broad catch-and-success fallback with a controlled exception or an atomic savepoint that restores every changed record. Use permission-aware document writes for the current user. Add fault-injection tests after each write proving no partial User/User Desk Theme state survives and the client receives an error.” |
| **MEDIUM** | `construction/tests/test_boq_link_queries.py:16-44,225-294` | The test creates fixtures in `setUp`, then calls `frappe.db.commit()` in one test's `finally`. That commits setup headers, structures, items, projects, user, and scope context before teardown calls rollback. The independent full run added five headers, three structures, and three items; repeated prior runs are visible in the database. A passing suite that changes shared site data is unsafe as release evidence. | **Prompt:** “Make `TestBOQLinkQueries` hermetic. Remove the unconditional commit, or isolate the case in a savepoint/transaction and restore by exact tracked IDs in reverse dependency order. Track the created user, User Scope Context, headers, items, structures, and projects. Add a before/after database manifest assertion in an external harness so test cleanup cannot validate itself with already-cleared tracking lists. Run the suite twice and prove the second run produces no new records or files.” |
| **MEDIUM** | `construction/tests/test_security_audit_remediation.py:778-845` and BOQ import path | Only 100 items are tested. The timer stops before `recalculate_phase1_totals()` and reload, so it does not measure the complete import/rollup lifecycle. It records no SQL-query count, peak memory, or lock duration and does not execute 1k/10k cases. In the full run the 100-item test itself took about 18.1 seconds overall. The expressly requested scalability evidence is absent. | **Prompt:** “Create a release-gate performance harness outside the unit suite for 100, 1,000, and 10,000 BOQ items through the real preview/commit API and final rollup. Record end-to-end elapsed time, SQL query count, peak process memory, database lock/wait time, and result totals on documented hardware/data. Keep the 100-item functional regression in CI, but attach the 1k/10k capture to the release evidence. Define pass/fail ceilings before execution. If deferring the 10k gate, create a signed risk record with a named human owner, exact deadline, operational guardrail, and rollback trigger.” |
| **MEDIUM** | `construction/services/cost_database_service.py:61-140,171-201,269-306` | Repricing removes some lookup N+1 queries but still loads and saves one document per analysis. It loads all history rows for every selected item with `limit_page_length=0`, so memory is unbounded. `rows_for_doc` is computed and unused. Creating the same savepoint again at line 140 does not “commit” or release it. The scalability claim is therefore stronger than the implementation. | **Prompt:** “Finish the repricing scalability work: index eligible detail rows by parent once, avoid scanning the entire detail list per analysis, chunk analysis and item-code batches, fetch only the latest needed history row per matching key in SQL, and enforce a configurable batch ceiling. Remove the second same-name savepoint and its false ‘commit’ comment; use one savepoint with rollback-on-error and let the request transaction commit. Add query-count and peak-memory tests at representative batch sizes.” |
| **LOW** | `construction/tests/test_security_audit_remediation.py:151-164` | `_delete_tracked_business_graph()` clears all tracked lists before the following “no tracked row may survive” loops execute. Those loops therefore test empty lists and cannot detect residue. The independent database check happened to show this class cleaned its targeted records, but the assertion itself is ineffective. | **Prompt:** “Copy the tracked IDs before deletion, perform cleanup, and assert against the preserved copies after commit. Also query child tables by the preserved parent IDs. Add a deliberate cleanup-failure test proving teardown fails when one tracked document survives.” |

## Reproduction details for release blockers

### 1. Report enforcement startup failure

In a new Python process, import interception deliberately raised only for `construction.overrides.scope_report`. Importing `construction` completed instead of failing. The observed state was:

```text
ENFORCEMENT_OK False
RUNNER_MODULE frappe.desk.query_report
RUNNER_NAME run
```

This directly disproves the source comment and error message claiming protected reports remain denied when that import fails.

### 2. Generated-column deduplication failure

A temporary MariaDB table reproduced the production expression. Two active rows referenced `VO-1`; executing the migration's equivalent `SET generated_column = NULL` left both generated values as `VO-1`. Creating the unique index then failed:

```text
MR-1  docstatus=0  custom_variation_order=VO-1  active=VO-1
MR-2  docstatus=0  custom_variation_order=VO-1  active=VO-1
ERROR 1062: Duplicate entry 'VO-1'
```

The temporary table was connection-scoped and did not alter application data.

### 3. Scope hierarchy cache poisoning

Using the existing permission-less test user and clearing the key before and after the probe:

```text
UNCACHED_SELF     companies=0  cost_centers=0  projects=0  departments=0
PRIVILEGED_CROSS companies=21 cost_centers=46 projects=13 departments=276
CACHED_SELF       companies=21 cost_centers=46 projects=13 departments=276
```

The probe restored Administrator as the session user and deleted the cache key afterwards.

### 4. Full-suite database residue

The five headers committed by the independent full run were:

```text
BOQ-2026-2150  _Test Scoped BOQ A
BOQ-2026-2151  _Test Scoped BOQ B
BOQ-2026-2152  _Test Draft BOQ
BOQ-2026-2156  _Test Scope Default Header
BOQ-2026-2157  _Test Explicit Project Header
```

They have three linked BOQ Structures and three linked BOQ Items. They were deliberately left in place so the finding remains reviewable; no cleanup or source mutation was authorized by this audit.

## BOQ 1k/10k scalability risk status

**Risk ID:** `PERF-BOQ-001`  
**Status:** **OPEN — not accepted**  
**Reason:** no 1k/10k execution evidence, no query or memory ceiling, no named human owner, and no exact deadline were found in the candidate.  
**Required owner:** unassigned; a real accountable person must be named.  
**Required deadline:** unassigned; an exact calendar date must be approved.  
**Mandatory guardrail until closure:** do not claim or contractually promise 10k-item capacity; enforce a documented import-size ceiling derived from measured safe capacity.  
**Release treatment:** this risk can be accepted only by the authorized project owner after the three high-risk code defects are fixed. A report cannot accept risk on the owner's behalf.

## Required release sequence

1. Fix the report startup fail-open, MR upgrade invariant, and `cost_stream` repricing defect.
2. Fix the hierarchy cache-key flaw and runtime endpoint commit/error behavior.
3. Make the complete test suite database- and filesystem-hermetic; clean the test site using an explicitly reviewed, exact-ID cleanup plan.
4. Add the failure-first regression tests described in the issue matrix.
5. Run static checks and both test cohorts twice, capturing before/after database and filesystem manifests.
6. Install and migrate `fade6b1`'s successor on a genuinely fresh site and on an upgrade fixture containing legacy duplicate MRs.
7. Execute the 100/1k/10k performance harness, or obtain explicit written acceptance of `PERF-BOQ-001` with a named owner and date.
8. Perform least-privilege API tests using real HTTP sessions for Guest, permission-less user, Site Engineer, Project Manager, Accounts User, and System Manager.
9. Only after every mandatory gate is green should the exact verified commit receive an immutable signed release tag.

## Final verdict

**NO-GO.** The 413/413 result is valid as a test count, but it does not prove production readiness. The current candidate has reproduced security/data-integrity defects, an unsafe upgrade path for one database invariant, incomplete scalability evidence, and a non-hermetic full suite. No immutable release tag should be created for `fade6b1`.
