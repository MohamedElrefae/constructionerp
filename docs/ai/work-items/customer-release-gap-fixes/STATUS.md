# Customer release corrections — status and next work

**2026-10-04. Partial stabilization milestone; customer release remains blocked.**

The dated sixteen-gap report remains the reference assessment. This ledger records corrections and fresh evidence against branch `codex/customer-release-gap-fixes`, based on `4341542`. It does not erase unfinished acceptance criteria or certify the whole app.

## Verified corrections

- BOQ item rollups run after successful SQL deletion, within the transaction. Direct deletion, deletion of the final item, leaf deletion, explicit deferred-batch flush, and refused linked deletion are covered by real Frappe tests.
- Approved revision commercial inputs, derived values, references and approval attribution cannot change through ordinary document saves. Unchanged history is no longer recalculated from today's BOQ item. Authenticated REST and Desk saves were exercised as Project Manager and System Manager. The existing Approved→Rejected status policy is retained pending the owner's workflow answer; that policy and deletion/reapproval/import paths still need closure.
- BOQ aggregate writers use guarded current reads under MariaDB REPEATABLE READ. Header saves, direct item changes/deletion, deferred flushes, revision/VO projections and cost updates share the transaction guard. Existing-document contention fails with an explicit whole-operation retry; new structure insertion waits at most five seconds before naming and child locks. Guard lock/deadlock failures prevent `frappe.db.commit()` until a full rollback. No automatic retry loop or inner commit was added.
- A non-whitelisted, Administrator-only read-only audit compares stored BOQ header/structure rollups with actual item aggregates. It reports discrepancies and the existing variation/docstatus policy differences. It never repairs customer data.
- Cost-database imports bound uploaded bytes, ZIP expansion/parts/ratios, worksheet and shared-string XML, actual worksheet relationships/coordinates/dimensions/merges, worksheet count, imported rows, traversal and response messages. Worksheets stream and close. The synchronous path accepts at most 2,000 nonempty data rows across the three required sheets, with a separate 50,000 traversed-row safety ceiling; these are safety ceilings, not measured product capacity. Oversize imports require smaller files until an authorized background-import design exists.
- CI now runs thirteen real Python business modules, retains the JS properties, uses the test lockfile, explicitly enables tests only on its disposable site, and provides the PDF renderer/fonts on Ubuntu 24.04. A GitHub run has not been dispatched or observed.
- Fresh installs now receive the existing active bilingual registry's required custom fields rather than relying on historical upgrade patches. Existing fields and values are preserved, missing framework identity fields fail, and absent optional-app DocTypes are skipped. The metadata-only validation mode matches existing additive patches; document validation remains enabled.
- Invalid System Manager import flags are prevented and corrected when DocTypes are non-importable/single. The helper no longer commits the caller's transaction. This narrow correction does not resolve the wider global permission-grant policy.

## All sixteen gaps

| ID | Current status | What must happen before closure |
| --- | --- | --- |
| G01 | Deletion fix and read-only discrepancy audit verified | Assess affected existing data on a named authorized site; review and authorize any reconciliation. Confirm supported framework versions. |
| G02 | Commercial edit protection verified; partially open | Owner confirms approved-history reversal policy; test deletion, direct approval creation, rejection/reapproval, new corrections and import paths; reconcile approvals and BOQ projections. |
| G03 | Pending construction decision; unchanged | Confirm cancellation fallback when no prior approved analysis exists, then implement/test linked cost and provenance restoration. |
| G04 | Pending pricing decision; unchanged | Confirm whether zero factor is valid; make controller, SQL, report and export arithmetic agree, with actual controller regressions. |
| G05 | Reproduced race corrected; current-read and contention regressions verified | Recheck the integrated candidate under the promised workload and supported framework/database matrix. Existing legacy migration/patch bypasses belong to the upgrade review; approval policy/history closure remains G02/G03. No automatic retry or throughput guarantee is claimed. |
| G06 | Pending pricing decision; unchanged | Define direct cost versus selling price and where overhead/profit apply; test the resource-analysis→item→header→export path with one margin application. |
| G07 | Business suite passes locally; CI configured | Observe the committed candidate's actual GitHub CI run. Current property suite contains legacy placeholders; passing test count alone is not comprehensive coverage. |
| G08 | Invalid native import flags corrected; wider review open | Decide selected scope versus authorization and customer isolation. Verify non-admin read/write/import/export/attachment access matrix and replace unjustified broad permission grants. |
| G09 | Import guards and service regressions verified | Bind to the final integrated candidate and operating request/proxy limits. Measure admitted worst-case workbooks for the promised workload; this batch makes no throughput/RAM guarantee. |
| G10 | Local inventory and conflicts recorded; open | Resolve candidate environment constraints in an isolated reproducible runtime, review installed Python/JS/framework/OS dependencies and security advisories, and produce a repeatable approved deployment inventory. Do not upgrade the shared working environment blindly. |
| G11 | Open | Define the sold workload (projects, BOQ lines, users, imports), measure response time/memory and concurrent correctness, then publish only evidenced capacity. |
| G12 | Automatic fresh install and schema idempotence verified; partial | Upgrade a representative prior-version copy, migrate twice, compare financial/history/file data and constraints, and demonstrate recovery. A new empty site is not upgrade or restore evidence. |
| G13 | Evidence for installed v16 stack only; open | Declare and pin the supported matrix, review global overrides, verify advertised versions. No v15 qualification is claimed. |
| G14 | Backend/REST/Desk-save paths and one native PDF test verified; partial | Test actual UI wiring and sold workflows with normal users. Reconcile the concurrent bilingual report task; browser behavior and Arabic visual correctness are not established by this batch. |
| G15 | Owner's delivery decision remains open | Decide hosting/customer isolation and support; define monitoring, support responsibilities, backup retention/RPO/RTO; execute a timed restore drill. |
| G16 | Local branch evidence only; release blocked | Integrate with concurrent changes, choose one immutable candidate, run its applicable release gates, document known limitations and independent qualified review, then obtain actual release authority. |

## Pending owner choices

The consultant owns routine software implementation and test choices. Only these construction/commercial questions were submitted for this batch, and no answers have been received:

1. Is factor zero legitimate? For direct cost 100, overhead 10%, profit 10%, confirm the proposed selling price 121, with margins applied once.
2. When the only approved cost analysis is cancelled, restore the prior manual estimate with provenance, require a replacement approved cost basis, or retain an explicitly unapproved estimate?
3. Preserve an approved quantity revision permanently and correct through a new revision, or provide a separate audited reversal workflow? Merely setting Rejected currently does not undo its financial projection.

A preselected answer is not approval. Existing behavior for these decisions has not been silently changed.

## Consultant recommendation for the next implementation batch

The earlier G05 probe found stored contract 110 versus actual 120. The correction now produces 120/120 on the same two-thread sequence; twelve real transaction regressions also cover old snapshots, different-item approvals, repeated approval, header saves/freezing, cost approval/cancellation restoration, deletion, deferred batches, contention, an explicit complete-operation retry, savepoint/commit refusal and rollback. The concurrent WBS insertion test also passes. Read [the transaction protocol](TRANSACTION_PROTOCOL.md) before adding a new BOQ writer.

The next financial implementation depends on the three owner answers: implement G03/G04/G06 and complete G02 policy enforcement. Independent technical next work is the G08 access matrix and G12 representative upgrade/restore checks. The writer inventory found legacy migration parent rewiring outside the NestedSet lifecycle and intermediate commits; treat that as an upgrade risk requiring its own fixtures and reviewed correction. Security/capacity/delivery evidence must match what is actually sold. This is continued development, not a blanket production-readiness claim.

## Parallel work and integration

The main checkout advanced separately to `dd4ea6d00860a2778382ddd9078dc02baa2c4463` during this review and contains an active bilingual financial-report task. Its files, including `construction/hooks.py`, are untouched in the main checkout. This branch adds only two hook entries in installation/migration lists; reconcile those with the other task when integrating. Do not overwrite, stash, commit or discard its work. This branch is not installed on the existing customer/development sites.

## Local commits

- `e8b9a43`: financial snapshot protection, post-delete/current aggregate guards, read-only audit and transaction regressions.
- `403f01f`: bounded cost-database workbook handling and tests.
- `d4f071e`: required fresh-install schema/permission correction and business CI.

The code candidate is `d4f071e`; `TESTED_FILES.json` binds thirty source/test/CI files. Documentation is committed separately. These local commits are on the isolated branch, not merged, pushed or released. Private external-memory commit hooks were disabled for these commits so repository findings remain local.
