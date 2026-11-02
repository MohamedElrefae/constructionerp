# Construction ERP — Developer / AI Coding Agent Technical Handover

## Document control
- Revision: v3, consolidated through 2026-10-27 WBS-only scope reset and coverage outline
- Owner/repository: MohamedElrefae/constructionerp
- Historical branch: develop
- Pinned reviewed SHA: a19bf8efec0b32c2bc71454aaddf42f6583c69e3
- Language: English
- Status: Investigation/handover, NOT approved implementation PLAN, write grant or release certification.
- Companion: Business Workflow and Owner Decisions Handover v3
- Supersedes earlier technical scope recommendations where conflicting. Preserve old evidence but adopt latest WBS boundary.

## 1. Actual work and verification limits

Remote develop was checked more than once, most recently during the Oct27 restart before the later mapping discussion, and resolved to the pinned SHA. It was not freshly rechecked when these files were generated. Do not assume a local checkout is identical or clean.

No repository modifications, issues, branches, commits, pushes, schema changes, native tests, CI execution/inspection, migration or deployment were performed. All defects remain source-derived candidates unless explicitly noted as confirmed source behavior. Original user report claimed successful CI; assistant did not independently verify it.

No named disposable site/execution channel was supplied. GitHub connector provides source reads/searches, not Bench execution. Notebook artifact generation is NOT runtime verification of Construction ERP. No native test suite was generated/executed by the assistant.

Current user asks for saved references before next step, not code changes.

## 2. Latest scope — overrides earlier scope creep

Immediate first increment:
- new project execution NestedSet tree, separate from commercial BOQ Structure;
- optional execution_node link on existing BOQ Item Stage;
- controlled mapping and navigation;
- linked/unlinked mapping coverage;
- permissions, lifecycle and upgrade preservation.

Excluded:
- standalone Execution Allocation Plan/Line and duplicate allocated_qty;
- measurement ledger implementation or legacy certified_qty migration;
- progressive billing/certificates/previous-cumulative calculation implementation;
- broad VO redesign/automatic redistribution;
- financial correction/receipt changes;
- scheduling/subcontract engine;
- Stage generator in initial increment (recommended follow-up because exact distribution complicates sequential inserts).

The owner has accepted future billing requirements and VO reconsideration, but explicitly instructed returning to WBS. Do not treat every commercial defect as a blocker to creating a tree. Only paths exercised/worsened by mapping block this feature.

## 3. Governance and safety startup

Read actual current files before edits:
AGENTS.md; docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md; docs/ai/CONTEXT_INDEX.md; SESSION_MEMORY.md relevant sections; root AGENT_WORKFLOW.md; SCHEMA_FACTS.md; applicable ADR/work-item contracts and release-gap ledger.

Root workflow read in session describes separate architect → plan reviewer → owner PLAN grant → builder/tests → independent verifier → owner commit authorization. Applicability to this workstream must be verified; don't claim a governed task exists or roles ran.

Run in actual task checkout:
```bash
git rev-parse --show-toplevel
git status --short
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
git rev-parse HEAD
python3 scripts/schema_drift_checker.py
python3 scripts/ai_context_check.py
```
Inspect staged/unstaged/untracked changes, base/upstream divergence and installed versions/site metadata. Commands were NOT run here. Do not use --update to hide drift, or auto reset/pull/switch/migrate shared work. Record final HEAD/status and actual files read.

Confidentiality: repo standard requires private implementation/findings; user synthesis called repository public. Visibility/disclosure scope not reconciled. Never assume read authorization grants public upload, PR, CI or external memory publication. Follow exact confirmation requirements for remote writes.

## 4. Owner business facts relevant to current scope

Stage = item-specific execution portion; BOQ item can span many buildings/floors. Example concrete1000m³ =10×(20+25+25+25+5). Same floor node reused by different item Stages.

Formal consultant payment approval occurs on BOQ item lines in a multi-item payment, supported by separate detailed Stage/measurement sheet. Missing certificate metadata on Stages is NOT itself a defect. Do not require approval date/attachment/payment period on every Stage.

No arbitrary attribution of item-level certified difference to Stage quantities. Existing certified_qty semantics require real-data inspection later. Preserve now.

Future-only rules:
- sequential applications; drafts/rejected/unapproved cancelled attempts have no certified balance effect;
- next opening =last eligible approved certified cumulative;
-350submitted/330certified then600submitted →270current claim; if580certified then next opening580;
- only accepted measurements currently eligible;
- company engineer records external consultant approval; consultant login optional;
- negative item corrections can coexist with overall positive payment; ordinary whole-negative payment unusual, final exception possible;
- partial acceptance, audited distribution changes and below-certified reductions with reconciliation accepted;
- VO may be redesigned if justified, no blanket rewrite grant.

## 5. Evidence inventory — distinguish reads from searches

### Fully returned central source reads across session
- construction/services/boq_lookups.py
- construction/services/boq_operational.py
- construction/services/variation_orders.py
- construction/services/boq_transactions.py
- construction/services/quantity_revisions.py
- construction/services/boq_lifecycle.py
- construction/services/revised_boq_queries.py
- construction/services/boq_transaction_validation.py
- construction/services/boq_accounting.py
- construction/services/boq_scope_registry.py
- construction/construction/doctype/boq_item/boq_item.py
- construction/construction/doctype/boq_structure/boq_structure.py
- construction/construction/doctype/boq_header/boq_header.py and boq_header.json
- construction/construction/doctype/boq_item_stage/boq_item_stage.py (re-read at final scope reset)
- construction/construction/doctype/boq_item_stage/boq_item_stage.json
- construction/construction/doctype/boq_item_stage/boq_item_stage.js
- construction/construction/doctype/boq_quantity_revision/boq_quantity_revision.py
- construction/construction/doctype/variation_order/variation_order.py
- construction/construction/doctype/vo_line/vo_line.py
- construction/overrides/boq_permissions.py
- construction/api/boq_api.py
- construction/tests/test_boq_item_stage.py
- AGENTS.md; AGENT_WORKFLOW.md; docs/ai/CONTEXT_INDEX.md

### Partial/truncated
- PROFESSIONAL_ENGINEERING_STANDARD.md
- SCHEMA_FACTS.md
- test_variation_orders.py
- test_quantity_revisions.py

### Searches/listings, not full reads
- directory and tests inventory
- quantity_certified literal search: schema/docs/reference results; no indexed app writer found
- certified_qty and measured_executed_qty consumer searches
- Stage list JS Over Measured snippet
- export service mapping snippets
- is_progress_billing consumers and dated engineering report snippets
- hooks.py references discovered, not fully read

Correction: construction/services/transaction_validation.py was requested and failed because path doesn't exist. Correct file read: boq_transaction_validation.py. Do not perpetuate wrong path.

Search results often referenced pinned SHA, but GitHub search indexes branch content; verify actual returned refs/full pinned files. No connector line numbers; do not invent line ranges. Public GitHub fetch attempts failed; connector reads succeeded.

## 6. Existing schema and proposed relationship

Commercial: Header → Structure → Item → Stage.
Header native JSON lacks company/cost_center; company derives from Project.company unless installed customization proves otherwise. Types Tender/Contract/Variation; statuses Draft/Pricing/Frozen/Locked.
Structure NestedSet uses wbs_code, parent_structure,lft,rgt,old_parent,is_group; leaf insert auto-creates Item.
Item uses free-text cost_item, NOT ERPNext item_code/item_name. Fields include quantity/unit/factor/has_stages/original_qty/current_revised_qty/current_revised_unit_price/last_quantity_revision and hidden progress fields.
Stage direct item/header/structure/project links; no parent-stage hierarchy; planned/measured/certified/percent/status; native schema not submittable and lacks separate approval evidence workflow.

Proposed new tree: Execution Breakdown Node, ebs_code unique per project with DB-backed invariant; project ownership, same-project parent, valid leaf selection; company derived. Exact naming/field schema not approved.
Stage optional execution_node. Many Stages may map to same leaf. BOQ item relationship derived through Stages. No single node on item master; no duplicate item allocation layer; no unconditional item+node uniqueness.

## 7. Specific WBS integration findings and blockers

### New link is not automatically protected
Stage controller enumerates planning fields in FROZEN_LOCKED_IMMUTABLE_FIELDS, CERTIFIED_IMMUTABLE_FIELDS and enforce_measurement_field_policy. Adding execution_node alone won't put it under these lists.
Define explicit create/map/relink authorization and historical rules. Measurement-only users must not accidentally gain location-relink authority. Do not merely freeze it everywhere without a reviewed way to map legacy records.

### Mapping-only save runs full distribution validation
BOQItemStage.validate always calls validate_stage_quantities, which rechecks distribution. An old VO imbalance can block saving ONLY the new link. Test Draft/Locked/certified/out-of-balance records.
Plan either clear rejection or narrowly reviewed audited mapping-only operation proving protected quantities unchanged. No generic ignore_validate/db_set shortcut. Frappe db.set_value bypasses ORM lifecycle; justify every direct setter and preserve invariants.

### Tree history
Protect referenced leaf AND referenced descendants when moving/deleting an ancestor. Define group conversion, project change, disabled references, code/path renumbering. Recommended first increment: block history-changing structural moves/deletions of referenced subtrees. Distinguish title edits from structural identity; policy must be explicit.

### Upgrade
No automatic name-based mapping; nullable field leaves existing records valid/unlinked. No quantity, revision pointer, measured or certified value changes. No inferred node-level historic progress. Migration repeat-safe and no destructive repair.

## 8. Existing quantity/VO path — preserve and isolate

Header first Locked transition → create_lock_baseline. Header lock/current reads initialize original/current qty/rates; approved Original Lock revision/pointer; totals. Coarse early return if ANY item has pointer doesn't establish full legacy baseline completeness.

VO requires Locked; Contract-only gate NOT established. Existing tests create Tender then lock. Do not silently narrow accepted header types for WBS; inspect allowed scope and retain commercial workflow unless explicitly changed.

VOLine validates same header/leaf for change/omission; New Item same-header group/title/unit/positive qty/rate. Client approval → quantity_revisions.process_approved_vo_lines: header lock, sorted item locks, savepoint, mutations, totals, rollback/rethrow.

Approved revision lifecycle → _project_new_approval → apply_approved_revision: validates stored approval, locks item/header, protects historical reapplication, updates current_revised_qty/rate/pointer via direct setter, not item.quantity. Does not redistribute Stages.
New Item creates Structure leaf and auto-created Item under same header, populates fields, rebuilds tree, original_qty0/current projection, approved New Variation Item revision and created_* line refs.

Locks/savepoints are mechanisms, not all-path atomicity/idempotency proof. No real concurrency ran.

## 9. Existing Stage policy

Nonnegative planned/measured/certified; certified≤measured; percent0..100. Draft/Pricing planned total≤capacity without tolerance in that branch; Frozen/Locked exact within0.001.
Stage named lock construction:boq_stage_distribution:{item}, released commit/rollback. Capacity helper reads before later item FOR UPDATE; inspect snapshot semantics if altering quantity paths.
Frozen/Locked existing planning fields immutable. Certified state=statusCertified OR certified_qty>0; defined field set freezes quantity/status/description (not literally all metadata). JS mirrors freeze and suggests adjustment Stage; no complete adjustment semantics established.
Measurement-only policy returns on new docs. Parent-read exception exists for Stage create/write; native DocPerm still relevant.
Deletion guard blocks certified or referenced Stage, NOT explicitly measured>0 alone. Don't repeat claim all measured Stages are protected or all reductions cause permanent DB deadlock.

## 10. Quantity/report consumers and separate backlog

boq_lookups.effective_boq_quantity returns current if notNone else original quantity.
variation_orders.get_revised_qty returns quantity on unlocked/no-pointer, else current fallback.
Draft qty100/current80/no pointer →80vs100. Normal item save aligns projection; legacy/inconsistent fixture still relevant. _get_parent_quantity_for_stage_distribution catches any Exception and falls back to quantity; do not copy silently into new functionality.

revised_boq_queries uses original_qty for original, direct current for revised, COALESCE for omissions. Define consumer lifecycle before global helper replacement.
quantity_certified literal search found no app writer; not proof no dynamic writes. Revised BOQ report sums Stage quantities; export uses revised-row totals. Don't use hidden item fields as reliable migration source without reconciliation.
Stage list recognizes over-measurement; server doesn't impose generic measured≤planned. WBS shouldn't add such cap.
Header original totals exclude variation items; Structure line_total rollup doesn't use same exclusion. Separate semantics/backlog, not mandatory tree blocker.
boq_api.get_boq_header_scope_context references absent native company/cost_center; installed custom fields unverified. Separate bounded defect investigation.

## 11. Accounting attribution findings — future billing, not WBS work

boq_scope_registry supports8types including Sales Invoice via is_progress_billing. Flag has consumers (client gating/server scope/custom-field setup); dated claim unused is wrong.
boq_transaction_validation loops registered child table, calls boq_accounting.validate_transaction_row. Checks completeness/existence/header/structure/project/status/stage-item relationship; not accepted evidence eligibility, certified opening or payment sequence.
Omission guard rejects newly attributed omitted items, preserves unchanged historical reference bound to current persisted parent. New negative correction row may be blocked later; candidate billing integration issue. Don't weaken guard for WBS.
Stages require no formal certificate metadata merely to map location. Future approval info at certificate header/item-line level; no master-field overwrite or arbitrary Stage apportionment.

## 12. Coverage report proposal — not final approved schema

Name: Execution Stage Mapping Coverage.
Required Project; filters header, Structure subtree,item,Linked/Unlinked/All,node/subtree,Stage status,search.
Node filter+Unlinked contradictory: explain/clear, not silent empty.
Counts total/linked/unlinked; count completeness, zero→N/A; items without Stages separate. Integrity-invalid links excluded from healthy completeness and separately counted/warned with transparent reconciliation (exact UX to define).
Rows: mapping state, commercial wbs_code, item ref/title,Stage code/name,planned qty,UOM,ebs_code,node path,Stage status,navigation.
Item grouping Full/Partial/Unmapped/NoStages based on existing Stage count only. Not quantity/physical/financial completeness.
Optional per-item linked/unlinked planned totals; no mixed-unit quantity grand total, no initial capacity comparison or qty percentage.
Warning for invalid/cross-project/missing/group/disabled assignment according to policy. No hidden data leak via counts/exports; use authorized dataset consistently.
Initial actions navigate/filter/export; no inline qty/measure/certify or unrestricted bulk relinking. No silent name matching/splitting/generation.

## 13. WBS acceptance gates

| Gate | Required evidence |
|---|---|
| G1 | Actual checkout/HEAD/status, governance and both startup checkers |
| G2 | Server relation checks Stage→Item→Header→Project=node.project; leaf/disabled policy |
| G3 | Ordinary allowed/denied users for create/map/relink/list/search/report/export; REST/import equivalents |
| G4 | Mapping-only save on Draft/Locked/certified/out-of-balance; no quantity changes |
| G5 | Delete/reparent/convert/project-change/reference ancestor controls; concurrent code creation uniqueness |
| G6 | Linked/unlinked counts/filter descendants/noStage/invalid warnings/UOM/permission consistency |
| G7 | Clean install/repeated upgrade, existing fields/history unchanged, nullable mapping |

Some gates are plan evidence prerequisites, some implementation acceptance tests. Don't claim all must be completed before writing any PLAN; distinguish planning from edits and release.

## 14. Separate regression backlog retained from previous handovers

R1 +VO then existing Stage measurement; R2 −VO/omission across evidence states; R3 duplicate target item in VO; R4 later VO on variation item; R5 helper divergence incl0/None; R6 original/revised/tree totals; R7 stale VO; R8 real concurrent VO/distribution; R9 measured Stage deletion; R10 partial certification progression; R11 bulk failures/retry.

Duplicate VO example: current1000; lineA1100, lineB1200, both deltas from1000; lookup(VO,item) may reuse first revision while VO sums both deltas. Candidate, not reproduced. Prefer rejection unless sequential semantics approved.
Variation item original_qty0 but quantity=initial VOqty; VOLine uses quantity baseline while revision uses original_qty →different percentage/rate trigger. No validated FIDIC compliance;25% code policy is not contractual certification.

## 15. Existing tests and execution precautions

test_variation_orders retrieved test creates full revised Stage AFTERVO, not pre-existing imbalance. Large test files truncated, no full coverage assertions.
test_boq_item_stage smoke helpers expect returned{success,error} for disabled/Guest while API throws; Guest permission may fail before role text. Reconcile interface before using as evidence.
Smoke helpers COMMIT/direct-delete cleanup, may not cover baseline revisions. NEVERrun on production/shared site. ThreadPoolExecutor alone doesn't prove controlled overlapping race. Use independent connections/barriers when required.

No code-based test replay or mocked substitute was executed here. No pretend fail-before/pass-after.

## 16. Next bounded implementation plan outline

WP0 actual startup/context + close mapping policy decisions.
WP1 execution node schema/controller/tree UI: same-project nesting,code uniqueness,authorized tree access,reference lifecycle.
WP2 optional Stage link: validation,explicit field-change permission,existing mapping policy,UI queries; no qty semantics changes.
WP3 mapping report/navigation with authorized counts/exports; labels separating commercial/execution codes.
WP4 focused tests, migration preservation, regressions on touched routes, bilingual strings/schema facts via proper regeneration.

Exact paths provisional:
construction/construction/doctype/execution_breakdown_node/
construction/construction/doctype/boq_item_stage/ (existing)
construction/services/execution_breakdown.py (if cohesive service needed)
construction/api/execution_api.py (only required thin endpoints)
construction/construction/report/execution_stage_mapping_coverage/
focused tests, hooks/permission integration and translations/schema documentation.

Do not add files merely because listed. Inspect existing service/permission conventions and exact hook order before final PLAN. Server controllers protect standard REST/import, not only custom API. Native checkers and named-site tests before implementation acceptance.

## 17. Restart and authority

Ask manager for named disposable Bench/site and agent execution logs, no credentials. No environment answer yet. Continue source review independently; don't repeatedly ask broad billing questions.

External tool workflow:list→describe→call. GitHub get_file_contents(owner,repo,path,sha). Remote writes require exact target/content confirmation; no public publication inference.

Frappe reference: https://docs.frappe.io/framework/user/en/api/database (direct setters bypass ORM); https://docs.frappe.io/framework/user/en/api/document ; https://docs.frappe.io/framework/user/en/api/tree .

Ready prompt:
> Read both v3 handovers. Keep English and WBS-only scope: separate execution tree,optional existing Stage link,controlled mapping and coverage. Preserve commercial BOQ Structure,quantities,revision history and existing certified_qty meaning. Defer billing,new ledger,AllocationPlan and generator. Verify actual checkout/governance/startup checkers and disposable site before edits/tests. Close G2–G5 mapping policies, draft exact bounded PLAN through applicable governance. No native test/source edit occurred previously. Treat defects as candidates until reproduced; don't require unrelated commercial redesign before tree work. No deployment/publication authority implied.
