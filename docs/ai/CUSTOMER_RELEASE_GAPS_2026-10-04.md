# Construction ERP — Customer Release Gap Report

**Prepared for:** Mohamed Elrefae, product owner and civil engineer

**Date:** 2026-10-04

**Purpose:** Define the corrections, business decisions, and verification needed before selling the app as a supported professional product.

**Companion:** [Professional engineering standard for future AI sessions](PROFESSIONAL_ENGINEERING_STANDARD.md)

## 1. Consultant's judgment

Continue developing this app. It has a credible Frappe/ERPNext foundation and useful construction domain work. I would not recommend replacing it wholesale merely because AI helped write it. I would also not sign off the current evidence as sufficient for a general customer production release.

Some parts show sound engineering: document permission guards, parameterized SQL, indexes, variation approval locks and savepoints, retry protection, constrained BOQ imports, private export handling, and a documented isolated recovery rehearsal. Other parts permit incorrect commercial state or lack the verification needed to support the product reliably. These differences matter more than whether a human or AI typed the code.

The immediate priority is to make commercial calculations and history trustworthy, then demonstrate that installation, customer permissions, daily workflows, upgrades, and recovery work together on a defined release. New features remain possible, but changes to these affected areas should include their correction and regression coverage first. A polished interface and a large test count cannot substitute for that proof.

This report is a release readiness assessment across the product lifecycle. It is not a certification that every module, endpoint, line of code, accounting rule, or deployment has been audited.

## 2. Evidence boundaries and baseline

| Item | Record |
| --- | --- |
| Repository | `/home/mohamed/frappe-bench/apps/construction` |
| HEAD rechecked for this report | `48f370f6a50689258d1d400c27886618186387f7` |
| Review history | Article review and expanded consultant review on 2026-10-03; core findings rechecked in source on 2026-10-04 |
| Working tree | Modified; this is not an immutable release candidate |
| Work already in progress | Brand bilingual registry, hooks, patches, tests, regression script, and other work-item evidence/documents; the shared working tree continued changing during report preparation |
| Customer delivery model | Owner has not decided; recommendations below are proposals |
| Operations performed for these reports | Read source and existing evidence; write local documentation and agent startup instructions |
| Operations not performed | Application fixes, live database checks, migrations, deployment, commit, or customer data changes |

The earlier review used several repository snapshots. Its expanded source review began at `db5d23e`; the advance to `48f370f` changed review documentation and evidence scripts rather than the inspected core runtime. This report rechecks the principal financial code in the current working tree. Future agents must recheck each finding against their own candidate; this report is not a timeless inventory.

Earlier checks recorded in [local session memory](../../SESSION_MEMORY.md):

| Check | Result in the earlier review | What it establishes |
| --- | --- | --- |
| Offline tooling tests | 72 passed | Tooling/context behavior; these tests intentionally do not import the app or Frappe/ERPNext |
| AI context check | 11 checks passed | Selected repository facts agree with the context checker |
| Scope metadata lint | Passed for 19 DocTypes | Selected metadata conventions hold |
| Targeted Ruff checks | Undefined-name checks passed | A limited class of Python errors was absent in selected paths |
| Python AST parsing | 259 files parsed at that snapshot | Syntax validity, not business correctness or runtime coverage |
| Local JS property suite | Could not start: missing `fast-check` | A local dependency blockage; no product test verdict |
| Live-site business, HTTP permissions, browser, upgrade, load suites | Not run in the review | No new pass result may be inferred |

Isolated probes exercised actual extracted controller functions using fake database/context objects. They are useful defect evidence, but are not equivalent to reproducing the issue on a running customer site. The concurrency result was an interleaving model, not a two-connection MariaDB experiment. Historical test reports and the recovery rehearsal remain useful evidence for their recorded versions and conditions; they do not automatically approve this release.

## 3. How to use the gap register

All gaps below are **open** as of this report. Suggested accountable roles are responsibilities to assign, not people already appointed.

- **Confirmed defect:** Source and/or isolated execution demonstrate the problematic behavior. Correct it and add a regression that fails before the fix.
- **Business decision:** Existing behavior needs a clear owner-approved meaning before the agent chooses a formula or reversal rule.
- **Verification gap:** Readiness has not been demonstrated. It may close with passing evidence, or reveal a defect needing a fix.
- **Maintenance risk:** Improve during affected work; it does not automatically require a large rewrite before the first sale.
- **Conditional scope gap:** A feature can be excluded from a release if exclusion is explicit and enforced across its reachable paths.

“Release gate” means required for the capabilities actually offered to customers. A capability may be deferred only when the release truly excludes or disables it, including APIs and imports, and the customer documentation agrees. Hiding a menu does not remove an unsafe route. Do not waive known arithmetic or approval-history defects in a capability being sold.

| ID | Gap | Classification | Release treatment | Suggested accountable role |
| --- | --- | --- | --- | --- |
| G01 | Direct BOQ Item deletion leaves stale totals | Confirmed defect | Correct before BOQ release | Backend engineer |
| G02 | Approved quantity revision can be substantively edited | Confirmed defect | Correct before revisions/VO release | Backend engineer + domain owner |
| G03 | Cancelling sole approved cost analysis lacks fallback | Confirmed behavior + business decision | Define and implement before cost analysis release | Domain owner + backend engineer |
| G04 | Zero factor means different things in item and totals | Confirmed defect + business decision | Correct before BOQ release | Domain owner + backend engineer |
| G05 | Shared BOQ aggregate updates may overwrite newer totals | Concurrency risk | Prove invariant; correct if needed | Backend engineer |
| G06 | Cost and selling margins may be applied at two levels | Business decision | Resolve and test before pricing claims | Domain owner |
| G07 | CI does not run Python business tests | Verification gap | Add reliable business release gates | Technical release owner |
| G08 | Scope and authorization behavior needs customer-role proof | Policy + verification gap | Define and verify release access boundary | Security/backend reviewer |
| G09 | Cost database workbook path lacks equivalent bounds | Robustness gap | Bound and test offered import paths | Backend engineer |
| G10 | Dependency audit and version evidence are incomplete | Verification gap | Verify complete deployed stack | Technical release owner |
| G11 | Representative end-to-end capacity is unproven | Verification gap | Publish measured supported limits | Technical/operations owner |
| G12 | Fresh install and legacy upgrade need candidate evidence | Verification gap | Prove safe installation and upgrade | Technical release owner |
| G13 | Global overrides and version support need controlled coverage | Maintenance risk + compatibility gap | Verify supported versions; refactor selectively | Framework/UI maintainer |
| G14 | Backend evidence and actual feature wiring can diverge | Conditional scope gap | Trace every promised workflow | Product owner + UI/backend engineer |
| G15 | Customer operations and recovery need a complete delivery plan | Verification + operational gap | Establish before handling real customer records | Product owner + operations owner |
| G16 | Readiness claims are not tied to one release candidate | Evidence/process gap | Produce an honest release evidence bundle | Technical release owner |

## 4. Financial correctness and commercial history

### G01 — Direct BOQ Item deletion recalculates too early

**Evidence:** [BOQ Item controller](../../construction/construction/doctype/boq_item/boq_item.py), `on_trash()` and `_trigger_header_rollup()` at lines 44–55. The local Frappe deletion implementation calls `on_trash` before deleting the row, then calls `after_delete`. The isolated probe left a stored header total of 300 after deleting an item worth 100 from items worth 100 + 200; the remaining items totaled 200. Leaf-structure deletion has an additional rollup and is a different route.

**Customer impact:** A successful direct deletion can leave a BOQ summary disagreeing with its remaining lines. Reports and decisions based on that summary can be wrong without an obvious error.

**Required correction:** Recalculate after successful removal using a supported lifecycle event, while preserving protection before deletion. Coordinate direct deletion, structure deletion, deferred batch rollups, and transaction failure. Do not merely subtract the displayed value without accounting for the other aggregate fields.

**Acceptance:** On a disposable Frappe site, test one of several items, the last item, structure/cascade removal, linked-document deletion refusal, and a deferred batch. After commit, relevant header and structure totals equal the remaining eligible lines. Failed deletion changes neither rows nor totals. Add a read-only reconciliation to identify already inconsistent data before proposing any repair.

### G02 — Approved quantity revision history is mutable

**Evidence:** [BOQ Quantity Revision controller](../../construction/construction/doctype/boq_quantity_revision/boq_quantity_revision.py), `validate_approval_integrity()` at lines 109–119. When old and new status are both `Approved`, validation passes without comparing commercial fields. The actual extracted `validate()` accepted a change from revised quantity 100 to 110 and recalculated revised value to 1,100 at rate 10. The DocType is not submittable and grants writer roles access to relevant editable fields. `track_changes` supplies history; it does not prohibit edits. `on_update()` stamps approval identity when missing rather than reapplying the commercial projection.

**Customer impact:** An approved record can stop representing what was approved or what was applied to the BOQ. That undermines auditability of quantities and variations.

**Required correction:** Protect approved commercial fields on the server, including item/header identity, baseline quantities/rates, revised quantities/rates, and approval identity. Define the small set of harmless metadata changes, if any. Use a new adjustment/reversal record for a commercial correction. Review allowed status transitions, approval actors, and system-generated baseline paths; do not assume a client-supplied status or revision type establishes authority.

**Acceptance:** Test ordinary authorized writer roles and privileged roles through document save and real HTTP. Substantive approved edits fail; allowed unchanged saves or metadata edits behave as specified. Approval and any permitted rejection/reversal keep the item projection and history consistent. Retry does not duplicate application. Verify imports and internal write paths cannot bypass the rule accidentally.

### G03 — Cancelling the only approved cost analysis leaves its cost in place

**Evidence:** [BOQ Cost Analysis controller](../../construction/construction/doctype/boq_cost_analysis/boq_cost_analysis.py), `on_cancel()` and `restore_prior_analysis_if_any()` at lines 27–28 and 137–152. Item cost is refreshed only when a prior `Superseded` submitted analysis is found. With none, the isolated probe performed no item refresh. BOQ Item saving also preserves existing estimated cost when no approved analysis is found.

**Customer impact:** The item can continue using a cancelled analysis without an explicit active basis. Whether the number should be retained is a domain decision; silently retaining it as if still approved is unsafe.

**Owner decision:** Should cancellation restore the preceding manual estimate, restore a prior analysis, or mark the item as awaiting a new approved basis? Specify what users see and what reports may treat as approved. Do not have the agent arbitrarily choose zero.

**Acceptance:** Implement the chosen policy with provenance and a reason. Test sole-analysis cancellation, restoration of a prior analysis, cancellation of an older superseded analysis while another remains active, and concurrent submit/cancel. Prior selection follows explicit business chronology, not just a mutable `modified` timestamp. Item, header, and structure totals agree with the resulting basis.

### G04 — Zero factor creates inconsistent calculations

**Evidence:** [BOQ Item controller](../../construction/construction/doctype/boq_item/boq_item.py), lines 122–139, 183–202; [BOQ Header controller](../../construction/construction/doctype/boq_header/boq_header.py), aggregate calculations; [revision totals service](../../construction/services/quantity_revisions.py), lines 206–220. Validation accepts zero. Python uses `flt(factor) or 1.0`, whereas aggregate SQL uses `COALESCE(factor, 1.0)`. The probe produced line total 100 for quantity 10, price 10, factor 0, while the SQL expression multiplies by 0.

**Owner decision and correction:** Either zero is a valid multiplier and must mean zero everywhere, or it is invalid and must be rejected everywhere. Define missing-factor defaults separately. Centralize or otherwise align the domain calculation across controller, approval service, SQL totals, reports, imports, and exports.

**Acceptance:** Test missing/default factor, zero, positive fraction, one, and invalid inputs under the chosen policy. Line, budget, revised, structure, and header values agree at the documented currency/quantity precision. An API or import must not accept an input the UI rejects.

### G05 — Different item transactions share an insufficiently proven total update protocol

**Evidence:** [revision totals service](../../construction/services/quantity_revisions.py), lines 206–220, reads the aggregate before writing the header. Variation processing locks individual items. Transactions touching different items can still affect the same header. An isolated model demonstrated a previously calculated 310 overwriting a newer 330. This is a credible race requiring live validation, not a proven incident on MariaDB.

**Required work:** Establish a consistent transaction protocol across all mutations that affect the header. The protocol must account for MariaDB isolation and snapshots, deterministic lock order, and existing item locks. Adding a header lock after an old snapshot has been established is not by itself proof of correctness. Select serialization/current reads or another demonstrably correct strategy with acceptable performance.

**Acceptance:** Use two real independent database connections and explicit synchronization to exercise different-item approvals on one header. After both commit, stored totals equal authoritative item state. Also test repeated approval, cost approval/cancellation, item editing, and header status changes that share the invariant. Assert no partial effects on injected failure. Any deadlock retry is bounded and replays an idempotent whole operation.

### G06 — Define direct cost, overhead, profit, and selling rate precisely

**Evidence:** [BOQ Cost Analysis controller](../../construction/construction/doctype/boq_cost_analysis/boq_cost_analysis.py), `calculate_totals()` and `update_boq_item_estimated_cost()`. Analysis `total_unit_cost` includes overhead and profit and becomes item `est_unit_cost`; the item then adds its own overhead and profit. Direct cost 100, with 10% overhead and 10% profit at both levels, yields analysis 121 and item selling suggestion 146.41.

**Assessment:** This is observed behavior, not proof that the owner intended a single margin. It becomes a defect if the customer expects 121 or interprets estimated cost as direct cost.

**Required specification:** Define direct resource cost, analysis unit basis, wastage, overhead base, profit base, estimated budget cost, suggested selling rate, contract rate, factor, and revision effect. State whether multiple margin layers are intentional. Explain what stays fixed after contract locking. Code comments invoking contract standards do not certify contractual compliance.

**Acceptance:** Owner-approved worked examples, independently calculated from the code, produce matching values on forms, reports, export, and approval. Include zero quantities, fractional quantities, rounding, analysis quantities other than one, and a revision/reversal. Labels describe the values actually calculated.

## 5. Security, bounded work, and release automation

### G07 — CI installation success is not business-test success

**Evidence:** [CI workflow](../../.github/workflows/ci.yml) installs Frappe/ERPNext/construction, builds assets, verifies installation, and runs JS print property tests. It has no Python business-test execution step. Passing offline tooling tests does not fill that gap.

**Required work:** Run the relevant business suites automatically on a disposable site, including regression coverage for G01–G06, workflow transitions, transaction rollback, and ordinary-user permissions. Preserve focused fast checks for development. Restore the local JS test dependency through the project's dependency process; record the actual result once it runs.

**Acceptance:** A deliberately introduced representative financial or permission regression makes the gate fail. The corrected release passes its Python business suite, scoped role/HTTP checks, JS tests, and essential browser smoke flows. Record exact versions and commands. A skipped or dependency-blocked suite is not counted as passed.

### G08 — Separate document permissions, selected scope, and customer isolation

**Evidence:** [BOQ access helper](../../construction/api/boq_api.py), lines 9–18, checks document permission but not the active User Scope Context. Permission query hooks are useful but do not automatically govern every `get_all`, raw SQL, or custom document route. Frappe documents that `get_list` applies permissions and `get_all` bypasses them. [Database API](https://docs.frappe.io/framework/user/en/api/database)

**Assessment:** This does not prove access outside ERPNext User Permissions or leakage between customer sites. A user authorized for projects A and B may nevertheless see B through a custom route while selecting A. Decide whether that selection is a convenience filter or an authorization boundary.

**Required work:** Specify and consistently enforce the chosen rule. Test every promised read/write route, standard REST, reports, link search, exports, and private attachments. Verify company/project/BOQ relationships server-side. Make administrative exceptions explicit. Do not solve a permission error by granting broad access.

**Acceptance:** Guest, permissionless user, site engineer, project manager, accountant, read-only user, owner, and System Manager have documented expected behavior for applicable routes. Unauthorized requests fail without state changes or sensitive output. Context switches behave consistently. Customer-site isolation is checked in the chosen deployment arrangement.

### G09 — Apply safe resource bounds to cost database Excel imports

**Evidence:** [cost database API](../../construction/api/cost_database_api.py), line 41, reads the uploaded stream; [cost database service](../../construction/services/cost_database_service.py), around lines 481 and 1215, loads and iterates the workbook without equivalent explicit archive/row limits to the [BOQ import service](../../construction/services/boq_import_service.py). The BOQ importer already has meaningful limits, including a synchronous threshold; do not assume another parser inherits them.

**Customer impact:** An authenticated expensive upload can monopolize resources. No public denial-of-service exploit was demonstrated in this review.

**Required work:** Enforce input bytes before unbounded materialization, XLSX expanded size/member and worksheet bounds before expensive parsing, and row/column limits. Preserve file ownership, private storage, safe paths, and bounded error reports. Align limits with worker memory and supported customer size. Define async behavior only if implemented; do not advertise an async path that currently rejects large jobs.

**Acceptance:** Small valid files import, files just over each limit fail cleanly, and bounded crafted malformed/compressed fixtures cannot produce partial records or uncontrolled resource use. Test preview, commit, and repeated import with the actual customer role. Use small safe fixtures, not a real decompression bomb.

### G10 — Audit and reproduce the deployed dependency stack

**Evidence:** [app project metadata](../../pyproject.toml) has an empty dependency list, while framework dependencies are managed through Bench. Package-only dependency auditing therefore does not demonstrate coverage of the complete deployed environment. CI uses v16 and `npm install` for the property suite.

**Required work:** Inventory the resolved Frappe, ERPNext, construction, Python, Node, database, Redis, and application JS dependency versions. Audit the installed Python environment and relevant JS lockfiles, assess findings, and retain a reproducible build process. Empty app dependencies alone are not a vulnerability. Do not introduce conflicting framework packages into app metadata merely to satisfy an audit command.

**Acceptance:** A new environment can reproduce the supported release from recorded versions/locks. Vulnerability results include the actual runtime and relevant assets; significant reachable issues have fixes or specific reviewed dispositions. Supported runtime versions are tested rather than copied from old documentation.

## 6. Performance, upgrades, and usable features

### G11 — Establish realistic capacity and response time limits

**Evidence:** Header/structure rollups recalculate aggregates, potentially repeatedly during item saves. Deferred bulk rollups are a positive optimization. [Performance report](../performance_report.md) and [BOQ capture harness](../../construction/perf_boq_capture.py) provide starting material, but the review did not establish current end-to-end customer workload capacity. Fixture insertion or estimated asset timing does not measure real import preview/commit, report execution, or concurrent approval.

**Required work:** Define representative project sizes and daily/peak activity, then measure query counts, response time percentiles, memory, worker/queue behavior, database waits, and financial correctness. Include realistic roles and scope filters. Use small, medium, and large fixtures within documented implemented limits, and demonstrate safe rejection beyond them.

**Acceptance:** Publish supported BOQ/import sizes and concurrent activity from measured results, with environment details. Both speed and invariants pass under the promised workload. No unbounded list, report, export, or job prevents other customers from working. Improvement priorities follow measurements and query plans.

### G12 — Prove fresh installation and safe upgrade of existing data

**Evidence:** The [installation module](../../construction/install.py) and patch chain contain substantial setup, permission, scope, and reconciliation behavior. Work that deduplicates records or changes unique indexes requires special care because MariaDB DDL may commit independently of normal application rollback.

**Required work:** Test a clean supported stack plus upgrade from a representative prior version. Include legacy duplicate fixtures and company/project relationships. Run migration again to prove idempotence. Check row counts, commercial values, names, links, permissions, and customer settings; installation must not silently reset customer choices.

**Acceptance:** Clean install and repeated upgrade pass on the release candidate. Reconciliation preserves history and relationships under a documented domain rule. The recovery plan handles schema and data changes; reverting Git alone is not presented as a database rollback. No reinstall/drop-site operation is used on customer data to make tests pass.

### G13 — Control framework overrides and compatibility claims

**Evidence:** [VFC layout engine](../../construction/public/js/vfc_layout_engine.js), [Link control override](../../construction/public/js/overrides/ct_link_control.js), and [report override](../../construction/overrides/scope_report.py) rely on framework behavior/prototype replacement. Existing guards are useful. Several modules mix multiple concerns, and formulas are repeated. CI currently demonstrates a v16 setup path rather than a v15/v16 matrix.

**Required work:** Declare which versions the commercial release supports. Exercise global adapters, native forms, link searches, report permissions, and layouts on each supported combination. Prefer supported extension points for new work. Refactor a fragile affected area into a small adapter or calculation service when its benefit is demonstrated; file length alone is not a release blocker.

**Acceptance:** Every advertised framework version has reproducible functional evidence. An unsupported version fails clearly or is excluded from product requirements. Overrides retain core behavior, install once, and do not silently disable permission enforcement. Maintain a concise compatibility checklist for upgrades.

### G14 — Verify actual feature wiring, not only backend helpers

**Evidence:** Existing work-item documents for [transactional link resolution](work-items/transactional-link-resolution/SCOPE.md) and [search query convention](work-items/search-query-convention/SCOPE.md) describe unwired/latent sidecar behavior. Their documented issues were not independently reproduced in this review. They should not be confused with the native Desk route. Current Brand work is also unfinished; that is not itself proof of a defect.

**Required work:** Inventory what will be sold. For each feature, trace the real user action through asset registration, request arguments, permission checks, persistence, reload, reports, and exports. Explicitly list experimental or unwired helpers as excluded. Do not connect an unused path merely because its unit tests pass without verifying its live argument and response contract.

**Acceptance:** Promised workflows pass in the actual browser as a customer role. English/Arabic, RTL, applicable theme modes, empty/error states, and key report/print/export results agree. No release documentation claims an unfinished feature is complete. An excluded path has no reachable unsafe effect.

## 7. Customer operations and truthful release evidence

### G15 — Decide delivery, support, monitoring, and recoverability

**Positive evidence:** A [2026-09-22 isolated restore rehearsal](work-items/scope-context-portability/evidence/stage8-restore-rehearsal-drill-2026-09-22.md) covers a useful test-site recovery scenario, including database/files/configuration concerns. The [runbook](../runbook.md) and [preflight script](../../scripts/preflight_check.sh) are starting points. Backup freshness alone does not prove a complete restorable customer backup.

**Recommendation, pending owner choice:** Start with a small supported customer pilot and one Frappe site/database per customer. Sites share application code when placed on the same Bench; separate sites alone do not provide independent version rollout or complete infrastructure isolation. Choose separate benches or controlled upgrade cohorts where needed. Frappe's site model supports separate site databases. [Sites documentation](https://docs.frappe.io/framework/user/en/basics/sites)

**Required work:** Establish hosting responsibility, TLS and session/secret handling, least-privilege administration, customer onboarding, monitoring of failed jobs/errors/queue and disk pressure, incident handling, and a named technical support owner. Decide acceptable data loss and recovery time (RPO/RTO), retention, offsite backup protection, and the process for upgrades. Verify database, public/private files, and required encryption configuration without storing secrets in the repository or report.

**Acceptance:** Restore a representative customer-like dataset to an isolated environment for the supported release, check known financial totals and attachment access, and record actual duration and data coverage. Test backup failure notification and recovery ownership. Provide customer instructions for issue reporting, maintenance windows, support scope, and safe updates. Do not promise service levels that have not been agreed and tested.

### G16 — Bind professional readiness claims to the shipped candidate

**Evidence:** The repository contains substantial historical evidence and status labels, but the working tree is modified and no complete commercial release bundle was verified in this review. Historical “all passed” statements describe their original scope and candidate.

**Required work:** Create a release manifest containing app/framework versions, exact source/build identity, migrations, supported capabilities, known exclusions, test results, permission evidence, capacity limits, restore evidence, and named technical/domain approval. Capture included uncommitted content by artifact digest if testing before commit; release from an identifiable version through the authorized workflow.

**Acceptance:** Another person can reproduce the checks and identify the exact artifact delivered. No required test is silently skipped. Builder self-review is labeled as such; AI-generated statements are not represented as human approval or independent review. When findings close, record fix, regression, candidate, reviewer, and remaining limits rather than erasing the original finding.

## 8. Relationship to the supplied article

The attached transcript is incomplete and uses illustrative startup stories. This report assesses your repository; it does not validate the article's anecdotes or predict bankruptcy.

| Article concern | Assessment for this app | Action |
| --- | --- | --- |
| Uncontrolled database access/connections | Frappe manages the main connection lifecycle; no per-route custom connection-exhaustion defect established | Measure deployed worker/database capacity; G11 |
| Missing indexes | Existing index definitions and unique constraints are positive; not every production query/index was verified | Inspect installed indexes and expensive query plans; G11–G12 |
| Concurrent state corruption | Existing locks/savepoints/idempotency are positive; shared-header totals still need proof | G05 and failure/retry tests |
| Unreliable commercial state | Specific BOQ deletion, factor, revision, and cancellation concerns were found | G01–G06 |
| Expensive unbounded processing | Workbook path bounds and realistic workload evidence need improvement | G09–G11 |
| Uncapped LLM billing | No relevant production LLM billing defect was established in this review | If adding metered services, budget and enforce limits before sale |
| Panic fixes and growing code entanglement | Global adapters, duplicated formulas, and stale context make undisciplined future changes risky | Follow the companion engineering standard |

## 9. Recommended execution order

### Phase A — Stabilize commercial truth

Resolve factor, cancellation, and cost-margin meanings with worked examples. Fix G01, G02, G04 and implement the agreed G03/G06 behavior. Prove the shared-total concurrency invariant in G05. Preserve approved history. Audit existing totals read-only; design any correction separately with a named site, backup, scope, and evidence.

**Exit:** Failed-before/fixed-after regressions plus real-site financial and concurrency evidence. No known commercial inconsistency remains in the included workflows.

### Phase B — Make regressions visible and access safe

Implement G07's automated business gates, decide scope semantics, prove ordinary-user HTTP/file access, bound every included import, and record the resolved dependency/support matrix. Keep native workflow governance where applicable.

**Exit:** A candidate passes meaningful business/security gates on the supported stack. Test blockage is resolved or explicitly prevents release.

### Phase C — Prove customer lifecycle and capacity

Run fresh install, existing-data upgrade, real browser workflow, representative load, and restore checks. Declare measured limits and finish the delivery/support plan. Refactor only where these checks reveal a problem or the next feature benefits from a clear boundary.

**Exit:** A reproducible release bundle establishes usable features, safe upgrade, capacity, and recovery for the offered scope.

### Phase D — Controlled commercial pilot

Use the agreed delivery model, a clearly scoped pilot, trained users, monitored operation, and a named support engineer. Record real usage problems and improve before expanding the sales promise. Avoid promising unlimited capacity or complete framework-version support without evidence.

No reliable completion date can be given before the policy decisions and live checks. Estimate each work package after its reproduction and affected paths are understood; do not compress the whole register into an invented one-week promise.

## 10. Closure record template

Copy this for each gap; do not prefill a pass:

```text
Gap ID and title:
Status: Open / In progress / Fixed awaiting verification / Closed / Explicitly excluded
Accountable owner:
Included customer capability:
Business decision and owner evidence, if required:
Reproduction and expected outcome:
Fix location and source/build identity:
Regression commands, environment, and actual results:
HTTP/browser/concurrency/migration/recovery evidence, as applicable:
Existing-data assessment and authorized repair, if needed:
Reviewer identity and review type:
Remaining limits or reason for exclusion:
Closure date:
```

The companion standard improves how future work is done. Writing these reports does not fix or close any runtime gap above.

## 11. Report preparation verification and source fingerprints

On 2026-10-04, all 31 local links across the two reports resolved, fenced blocks were balanced, and the tracked diff had no whitespace errors. The read-only context checker was rerun with the repository's Python environment: **11 passed, 0 failed**. These checks validate documentation/context; no live business tests were added or rerun for report preparation.

The following SHA-256 values identify the principal source files rechecked for this report. They are not a complete release manifest, and do not freeze other shared working-tree content. Compare them before assuming a finding still describes unchanged code.

```text
d5a453fe6263f2e7dbcc96a30509091d395af4f4bea3ffe522db9d596b739dd4  construction/construction/doctype/boq_item/boq_item.py
d2dd5b32461ffba375f57a79a56cedb4256d27df9b35839e6c38d7bafa611599  construction/construction/doctype/boq_header/boq_header.py
9d7d11dd39b2c38f0c3c5e3ecf61a3902472334023c2b6104782a3ea13e8de16  construction/construction/doctype/boq_quantity_revision/boq_quantity_revision.py
df393ccb5b3906c2ba9a65830c8efb7c257ab651d017d1beb0ce018e51f88f06  construction/construction/doctype/boq_cost_analysis/boq_cost_analysis.py
efd370919249b18af3fe50434ce7a51282d1736e0e4bbc9adfb404e142e34c62  construction/services/quantity_revisions.py
fc449dea0f4bb4c1f80561d4abb2cf926ba5e1f26652f772f015b3bd3b6ae214  .github/workflows/ci.yml
```
