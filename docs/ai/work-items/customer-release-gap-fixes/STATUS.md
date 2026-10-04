# Customer release corrections — status and next work

**2026-10-05. Owner financial rules implemented; customer release remains blocked.**

The dated sixteen-gap report remains the reference assessment. This ledger records corrections and fresh evidence against branch `codex/customer-release-gap-fixes`, based on `4341542`. It does not erase unfinished acceptance criteria or certify the whole app.

## Verified corrections

- BOQ item rollups run after successful SQL deletion, within the transaction. Direct deletion, deletion of the final item, leaf deletion, explicit deferred-batch flush, and refused linked deletion are covered by real Frappe tests.
- Approved quantity history is now permanent: status reversal, deletion and edits are blocked, including legacy Rejected records with approval attribution. Direct document approval projects quantities once, stamps the actual actor, validates item identity/current previous quantity, and refuses Draft/old-history replay. Original Lock creation is confined to the baseline service. New correction records and authenticated requests are verified; reader/import/legacy reconciliation remains open.
- Cost approval uses additive direct-cost pricing (100 + 10% overhead + 10% profit = 120), with an optional configurable tender tax allowance. Cancellation restores prior approved costs/percentages or the captured manual estimate, including zero and edits between approval cycles. Positive factors are enforced in controllers and real workbook previews; legacy invalid factors are not normalized. See [the complete financial contract](FINANCIAL_RULES.md).
- An additive version/provenance patch preserves legacy commercial amounts. Unresolved Legacy Review items cannot be repriced or newly approved without reviewed restoration evidence. Synthetic preservation/replay checks passed; a representative customer conversion remains open.
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
| G02 | Permanent history and new corrections verified; partial | Reconcile historical approvals/projections, unify revised-report readers and complete import/permission route coverage on the integrated candidate. |
| G03 | Owner manual-restoration policy implemented and verified | Review/convert representative legacy records with missing provenance; verify sold UI and final candidate. |
| G04 | Positive factor policy and regression paths verified | Assess/correct old invalid factors on an authorized data copy; complete all report readers and final candidate verification. |
| G05 | Reproduced race corrected; current-read and contention regressions verified | Recheck the integrated candidate under the promised workload and supported framework/database matrix. Existing legacy migration/patch bypasses belong to the upgrade review; approval policy/history closure remains G02/G03. No automatic retry or throughput guarantee is claimed. |
| G06 | Owner additive direct-cost rule implemented and verified | Review/convert legacy margin-inclusive bases and audit all pricing/resource/report consumers before release. Configured allowance is not statutory invoice-tax certification. |
| G07 | Business suite passes locally; CI configured | Observe the committed candidate's actual GitHub CI run. Current property suite contains legacy placeholders; passing test count alone is not comprehensive coverage. |
| G08 | Invalid native import flags corrected; wider review open | Decide selected scope versus authorization and customer isolation. Verify non-admin read/write/import/export/attachment access matrix and replace unjustified broad permission grants. |
| G09 | Import guards and service regressions verified | Bind to the final integrated candidate and operating request/proxy limits. Measure admitted worst-case workbooks for the promised workload; this batch makes no throughput/RAM guarantee. |
| G10 | Local inventory and conflicts recorded; open | Resolve candidate environment constraints in an isolated reproducible runtime, review installed Python/JS/framework/OS dependencies and security advisories, and produce a repeatable approved deployment inventory. Do not upgrade the shared working environment blindly. |
| G11 | Open | Define the sold workload (projects, BOQ lines, users, imports), measure response time/memory and concurrent correctness, then publish only evidenced capacity. |
| G12 | Automatic fresh install and schema idempotence verified; partial | The final additive schema and workspace correction migrate twice on an isolated fresh-site fixture. Still upgrade a representative prior-version copy, compare customer financial/history/file data and constraints, and demonstrate recovery. Fresh-site and synthetic records are not representative upgrade/restore evidence. |
| G13 | Evidence for installed v16 stack only; open | Declare and pin the supported matrix, review global overrides, verify advertised versions. No v15 qualification is claimed. |
| G14 | Backend/REST/Desk-save paths and one native PDF test verified; partial | Test actual UI wiring and sold workflows with normal users. Reconcile the concurrent bilingual report task; browser behavior and Arabic visual correctness are not established by this batch. |
| G15 | Owner's delivery decision remains open | Decide hosting/customer isolation and support; define monitoring, support responsibilities, backup retention/RPO/RTO; execute a timed restore drill. |
| G16 | Local branch evidence only; release blocked | Integrate with concurrent changes, choose one immutable candidate, run its applicable release gates, document known limitations and independent qualified review, then obtain actual release authority. |

## Confirmed owner decisions

- Factor must be positive; reject explicit zero. Missing factor defaults to 1.
- Sum overhead, profit and applicable configured tender tax percentages on direct cost, once. The owner's 100 + 10% + 10% example is 120.
- Cancel the current cost analysis by restoring eligible prior approval or captured manual estimate, with provenance.
- Preserve approved quantity revisions; record corrections as new revisions.

These are explicit conversation answers, not UI defaults. The consultant owns routine implementation/test decisions. Delivery/customer isolation, promised workload and operational recovery targets still need the owner's separate decisions.

## Consultant recommendation for the next implementation batch

The earlier G05 probe found stored contract 110 versus actual 120. The correction now produces 120/120 on the same two-thread sequence; twelve real transaction regressions also cover old snapshots, different-item approvals, repeated approval, header saves/freezing, cost approval/cancellation restoration, deletion, deferred batches, contention, an explicit complete-operation retry, savepoint/commit refusal and rollback. The concurrent WBS insertion test also passes. Read [the transaction protocol](TRANSACTION_PROTOCOL.md) before adding a new BOQ writer.

The financial answers are implemented in this branch. Next work is the G08 access matrix, revised-report reader reconciliation and G12 representative legacy conversion/upgrade/restore checks. The writer inventory found legacy migration parent rewiring outside the NestedSet lifecycle and intermediate commits; treat that as an upgrade risk requiring its own fixtures and reviewed correction. Security/capacity/delivery evidence must match what is actually sold. This is continued development, not a blanket production-readiness claim.

## Parallel work and integration

The main checkout was observed at `7839e67` at final inspection, with an untracked bilingual-wave1-masters-population work item. It advanced independently during this review. Its files, including `construction/hooks.py`, were untouched. This branch adds the earlier bilingual-schema hook entries and removes the redundant pre-page sidebar migration hook; reconcile these with concurrent changes during integration. Do not overwrite, stash, commit or discard its work. This branch is not installed on the existing customer/development sites.

## Local commits

- `e8b9a43`: financial snapshot protection, post-delete/current aggregate guards, read-only audit and transaction regressions.
- `403f01f`: bounded cost-database workbook handling and tests.
- `d4f071e`: required fresh-install schema/permission correction and business CI.
- `a01ac75`: confirmed additive pricing, positive factors, recoverable cost provenance and permanent quantity approvals.
- `efda04d`: correct native workspace insertion and sidebar migration ordering.

The final code candidate is `efda04d12c7105d010e63a4365a6eeceb0f42989`; `TESTED_FILES.json` binds the current source/test/schema/setup/CI files and local successful log hashes. `FIRST_BATCH_TESTED_FILES.json` preserves the earlier thirty-file candidate evidence. Documentation is committed separately. These local commits are on the isolated branch, not merged, pushed or released. Private external-memory commit hooks were disabled for these commits so repository findings remain local.
