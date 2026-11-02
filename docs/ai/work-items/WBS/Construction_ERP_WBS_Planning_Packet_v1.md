<!-- 00_START_HERE.md -->

# WBS Planning Packet — Start Here
Date: 2026-10-27
Owner: Mohamed Elrefae
Repository: MohamedElrefae/constructionerp
Historical baseline: a19bf8efec0b32c2bc71454aaddf42f6583c69e3 (develop when checked)
Status: REMOTE DRAFT FOR LOCAL RECONCILIATION. Not an approved implementation PLAN or execution grant.

## Purpose
Give a local architect enough direction to verify the actual checkout and produce bounded executable plans, without re-opening settled business scope or building progressive billing.

## Authority order
Higher-priority platform instructions and explicit current owner instructions; applicable repository governance/contracts; locally verified source and installed metadata; this packet and v3 handovers as reference. Stop and report material conflicts. Do not invent a grant or workflow state.

## Read order
1. Actual repository governance: AGENTS.md, PROFESSIONAL_ENGINEERING_STANDARD.md, CONTEXT_INDEX.md, root AGENT_WORKFLOW.md, relevant SESSION_MEMORY.md/ADRs/work-item state.
2. Supplied Business and Technical Handover v3. These are separate earlier deliverables, NOT included in this ZIP. Ask owner for them if unavailable; never claim reading missing files.
3. 01_MASTER_SCOPE.md
4. 02_DECISIONS.md
5. 03_LOCAL_ARCHITECT_INSTRUCTIONS.md
6. 04_WORK_PACKAGES.md
7. 05_VERIFICATION_MATRIX.csv
8. 06_STATUS_AND_EVIDENCE_TEMPLATE.md
9. 07_OWNER_REVIEW_CHECKLIST.md

## First permitted task requested by this packet
Read/inspect and propose. Run repository-mandated non-mutating startup checks subject to local authority. Inspect environment configuration without exposing secrets. Produce a local reconciliation report and proposed plans. Do not edit app source, initialize an orchestrator work item, install/update dependencies, migrate, run database-writing native tests, commit/push/publish/deploy unless separately authorized.

## First return to owner
Actual checkout/branch/HEAD/status; check results; files read; relevant changes from historical baseline; orchestrator readiness; named disposable test route (or missing target); decisions D01–D10; exact proposed scopes/commands; blockers. Gate: READY FOR OWNER PLAN REVIEW or BLOCKED, with reasons. Neither label grants implementation.

## Scope in one sentence
A separate project execution tree linked optionally to existing BOQ Item Stages, with controlled mapping and a permission-aware mapping coverage report; preserve existing commercial structure, quantities and history.

## Stop conditions
Unexpected unrelated edits, governance conflict, unknown site, unsafe validation command, scope expansion, source/baseline changes invalidating evidence, required business rule unresolved, or uncertainty over an already-running job. Preserve work and report; no automatic reset/retry/bypass.


---

<!-- 01_MASTER_SCOPE.md -->

# WBS Master Scope and Architecture — Draft for Local Review

## 1. Outcome
Organize existing item-specific execution portions by reusable buildings/floors/zones, without creating a second quantity source or changing commercial quantity/certification semantics.

## 2. Existing and proposed relationships
Existing: BOQ Header → BOQ Structure → BOQ Item → BOQ Item Stage.
Proposed: Project → Execution Breakdown Node tree; Stage.execution_node → execution leaf.
Many Stages may reference a leaf. BOQ Item location mapping derives through its Stages; no single node on item master. No blanket uniqueness(item,node), because multiple portions can exist at one location.
Names Execution Breakdown Node, execution_node and ebs_code are proposed; verify naming conventions before final schema.

## 3. Included
Project-scoped execution tree; optional Stage link; authorized create/map/relink policies; node/Stage/item navigation; count-based mapping coverage; protected references/tree lifecycle; nullable, repeat-safe upgrade; focused tests and documentation.

## 4. Excluded
Separate Allocation Plan/allocated_qty; Stage generator; new measurement ledger; payment application/certificate; certified_qty reinterpretation; previous-certified calculations; scheduling; subcontract engine; broad VO rewrite; automatic redistribution/repair; direct historical progress attribution.

Future business facts are retained only as compatibility context: sequential multi-item payments; approved-only opening;350submitted/330certified then600→270; external consultant approval recorded internally; partial acceptance and item corrections. They do not authorize billing work.

## 5. Data/behavior invariants
- Preserve commercial wbs_code/tree and all quantity/rate/revision fields.
- Stage, authoritative item/header project, node and parent project must agree.
- New assignment uses eligible leaf; define disabled behavior explicitly.
- Existing records valid with NULL/unmapped link; no name-based backfill.
- Mapping/relink is planning authority, not accidentally measurement authority.
- No historical measured/certified remapping without reviewed explicit policy.
- Protect referenced descendants as well as direct leaf when moving/deleting ancestors.
- No change to quantities/status via report read or mapping operation.
- Node codes unique per project under concurrency; final format/lock/index local design.
- Counts, searches, navigation and export share authorized scope.
- Mapping complete is not quantity-balanced/executed/certified/financially complete.

## 6. Stage-save integration hazard
Historical reviewed controller uses fixed immutable/planning field lists; new execution_node is not automatically protected. Ordinary Stage validation also checks full distribution, potentially blocking mapping-only saves after VO imbalance.
Local architect must compare alternatives: clear rejection of out-of-balance mapping, or explicitly authorized narrow mapping-only route. No generic ignore_validate or setter bypass. Historical mapping policy must be explicit, audited and compatible with actual framework lifecycle. No blanket ledger/VO redesign to solve a mapping problem.

## 7. Coverage view
Required Project; header/Structure subtree/item/mapping state/node subtree/Stage status/search filters.
Node filter plus Unlinked must explain contradiction or clear incompatible filter.
Summary: total Stages, healthy-linked, unlinked, link-issues, count completeness, items without Stages separately. Define disjoint categories and denominator so all counts reconcile.
Rows: mapping status, commercial code, item identity, Stage code/name, existing planned qty+unit, execution code/path, Stage status, navigation.
Item grouping Full/Partial/Unmapped/Needs Review/No Stages, with precise definitions. Invalid links never healthy.
Optional per-item planned quantity context only. No mixed-unit or unrelated-item quantity grand total; no initial capacity comparison or quantity percentage.
Actions navigate/filter/authorized export. No inline qty editing, bulk automatic mapping, splitting or progress changes.

## 8. Increment structure
P0 local reconciliation and plan review; P1 tree; P2 Stage mapping/reference protections; P3 coverage/navigation; P4 integrated acceptance/handover. P4 is final gate, not a substitute for per-package tests. Safe commit boundaries must be validated locally.

## 9. Acceptance boundary
Requires local baseline evidence, allowed/denied ordinary-user routes, Stage mapping across lifecycle states, tree reference safety, code concurrency where claimed, report reconciliation, clean/repeated upgrade and unchanged legacy quantities/history. No production-readiness claim from source reads or agent PASS alone.


---

<!-- 02_DECISIONS.md -->

# Decision Register — WBS First Increment

## Settled current owner scope
WBS now; billing later. Existing Stages represent item execution portions. Formal payment approval is item-line based, not mandatory Stage metadata. Preserve existing quantities/history/certified_qty meaning. Revisit VO only in a separately justified scope. No native tests or source changes occurred in prior review.

## Local recommendations requiring explicit resolution
| ID | Decision | Recommended starting position | Gate |
|---|---|---|---|
| D01 | Legacy Stage mapping | Remain unmapped by default; authorized explicit mapping | P2 |
| D02 | Measured/certified mapping/relink | No automatic mapping; choose reviewed historical mapping policy and audit | P2 |
| D03 | Out-of-balance mapping save | Compare rejection vs narrow invariant-preserving route; no silent bypass | P2 |
| D04 | Mapping permission | Planning-level document authority and scope; deny measurement-only relink | P2 |
| D05 | Leaf/disabled node | New assignments only eligible leaves; preserve references, show warning on disabled | P1/P2 |
| D06 | Referenced tree change | Block structural changes affecting referenced subtree initially; define title/code edits | P1/P2 |
| D07 | Header eligibility | No new Contract-only restriction without checking existing Locked Tender usage | P2 |
| D08 | Code generation | Stable unique per project, no auto-history renumbering; choose format locally | P1 |
| D09 | Coverage denominator | Healthy linked / all eligible Stage records; invalid links separate; zero=N/A | P3 |
| D10 | Active scope semantics | Reuse audited permission boundary, verify node access before Stage exists | P1 |

For each decision record selected rule, rationale, actor, date, affected requirements and test. Routine code choices delegated to architect within governance; consequential history/access/business choices escalate. No need to reopen future payment questionnaires.

## Explicitly deferred
Ledger schema/migration, partial certification redesign, financial corrections, VO rate rules/duplicate-line repair, Stage distribution revision, Stage generator, certificate sequence/reversal. Track candidates; escalate only if mapping exercises/worsens the path.


---

<!-- 03_LOCAL_ARCHITECT_INSTRUCTIONS.md -->

# Local Architect — First Assignment

## Task
Reconcile this draft packet with actual source, governance and environment; return locally executable subplans for owner review. Do not implement.

## Startup
Run mandated checks from actual task checkout if authorized:
```
git rev-parse --show-toplevel
git status --short
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
git rev-parse HEAD
python3 scripts/schema_drift_checker.py
python3 scripts/ai_context_check.py
```
Record argv,cwd,exit,status and baseline. Inspect changes without discarding them. No automatic pull/reset/worktree switch. Do not regenerate facts to conceal mismatch. Inspect installed versions only through authorized non-mutating means; never reveal secrets/site data.

## Source targets
Stage JSON/Python/JS/list; boq_operational,boq_lookups,variation_orders,quantity_revisions,boq_transactions,boq_lifecycle; commercial Structure implementation; hooks,boq_permissions,scope_query and project scope helpers; report/export conventions; install/patch/translation/schema conventions; relevant tests. Read full local files, not prior truncated excerpts.
Correct transaction path: construction/services/boq_transaction_validation.py, not transaction_validation.py.

## Orchestrator readiness
Read orchestrator/README.md, docs/ai/ORCHESTRATION_SYSTEM_MANUAL.md, applicable qualification/engineering-startup records. Verify current actual readiness; earlier README says qualification/pilot gates remain. Existing environment doctor may be proposed/run only under local authority. Do not initialize/dispatch work or alter pinned environment by implication. Offline checks != native Frappe acceptance. Select ONE workflow authority; no competing T3/repository builders in same worktree.

## Native verification proposal
Identify exact disposable site, code binding,versions,baseline fixtures,backup/recovery and cleanup. Confirm ownership/authority before any site-writing test. Inspect smoke helpers: prior ones COMMIT/direct-delete and may have incomplete cleanup. No production tests. No database connector substitute for lifecycle evidence.

## Required outputs
LOCAL_RECONCILIATION.md; resolved decision register; PLAN_P1/P2/P3 with exact paths/dependencies/acceptance/test commands; requirement-evidence map; readiness/blocker report.
Commands must be fixed argv arrays compatible with orchestrator; no placeholders passed as executable validation. Distinguish repo/offline/native/browser tests, write effects, permissions and required environment. No source-string-only tests as substitute for behavior.

## Plan review
Separate reviewer verifies scope, history,permissions,mapping bypass risks,tests,upgrade,coherent commit boundaries. Return design defects to architect; record deferred unrelated findings. Owner PLAN grant binds final scope through applicable engine; a Markdown PASS isn't a grant.

## Do not do
Source edits, migrations,new workflow init,dependency upgrades,public upload,commit/push/merge/deploy; no fabricated startup/test results or consultant approvals. No implementation of future billing to make tree feel complete.


---

<!-- 04_WORK_PACKAGES.md -->

# Work Packages — Briefs, Not Executable Approved Plans

## P0 — Reconciliation/plan readiness
Inputs: governance, v3 handovers, packet, actual checkout.
Outputs: exact baseline,state,check results,decisions,test target,subplans. No app edits. Missing native environment must be recorded; do not call tests passed. Can draft plans while environment pending, but no native acceptance without it.

## P1 — Execution tree foundation
Scope: proposed DocType/schema/controller/tree UI,project/company derivation,parent/leaf rules,code uniqueness,scope-aware read/write/search,tree lifecycle policy.
Paths to verify locally: construction/construction/doctype/execution_breakdown_node/; cohesive service/API only if necessary; hooks/permission integration; tests/docs/translations.
Tests: project/parent relationships,cycles/group conversion,ordinary allowed/denied users,concurrent code uniqueness if claiming it,clean/repeated install/upgrade.
Safe intermediate: tree exists with no Stage links; no BOQ auto-item creation. Referenced-subtree rules must be implemented no later than P2.
Commit: coherent verified candidate after separate owner authorization.

## P2 — Stage mapping and reference safety
Depends P1. Optional execution_node; normal-route validation; explicit create/map/relink authorization; historical mapping policy; out-of-balance behavior; reference guards including ancestors; UI filtered node selection.
No quantity/revision/status rewrite; no auto-backfill. Inspect fixed planning/immutable lists. Do not blindly add field to every list and make legacy mapping impossible.
Tests: Draft,Locked,certified,measured,out-of-balance;REST/import/custom API where exposed;ordinary users;clear/relink;delete/move/convert referenced nodes;legacy preservation;rollback.
Safe intermediate: cannot map before reference protections exist. If safe split impossible combine relevant P1/P2 changes; don't force unsafe commits.

## P3 — Coverage and navigation
Depends P2. Filters/authorized counts/linked-unlinked-issues/item grouping/noStages/units/navigation/export.
No quantities edited,no new source-of-truth totals,no hidden report bypass.
Tests: count reconciliation,zeroStages,N/A,node descendants,incompatible filters,invalid links,permissions/export,read-no-writes,reasonable bounded query behavior on representative data.

## P4 — Integrated acceptance gate
User journey create tree→map Stages→reload→coverage→forbidden relink/move→verify history unchanged. Clean/repeated upgrade,existing regressions on touched routes,supported-version evidence per declared matrix. Final actual baseline/diff/evidence/handover. Release/deployment separate.

## Per implementation package
Architect plan→separate plan review→owner PLAN grant→builder implements+tests→separate verifier checks exact candidate/evidence→repair cycle if needed→owner exact COMMIT grant→owner commit/reconciliation via repository workflow.
Do not automatically commit/push. README says engine records/reconciles owner commit rather than performing it. Never claim reviewer PASS=owner approval. Reconcile next package base after commit.

## Scope change rule
Any generator,ledger,certificate,AllocationPlan,financial adjustment or broad VO redesign returns to owner as separate request. Necessary narrow mapping defect fix must identify reproduced path,affected files and explicit changed invariant.


---

<!-- 06_STATUS_AND_EVIDENCE_TEMPLATE.md -->

# WBS Status and Evidence Record

## Identity
Work item:
Package:
Actual root/branch/HEAD:
Base/upstream and freshness:
Working-tree changes (own/unrelated/untracked):
Site (disposable and authorized?):
Runtime/framework/database versions:
Agent role/session identity (observed, not self-invented):
Workflow authority/task state:

## Files actually read
Path | revision/hash | full/partial | relevant sections

## Startup and validation
Command argv | cwd | baseline | environment | exit | evidence path | outcome
Mark NOT RUN explicitly. Offline/mock/native/browser evidence separately. Don't embed secrets.

## Decisions
ID | selected rule | rationale | decision maker/date | requirements/tests

## Findings
ID | requirement | Confirmed source behavior / Candidate defect / Runtime-reproduced defect / Business decision / Not yet reviewed | reproduction | impact | scope disposition | status

## Candidate
Allowed paths:
Actual changed paths:
Diff/candidate binding:
Quantity/history preservation result:
Tests fail-before/pass-after where relevant:
Unresolved findings:
Reviewer identity/verdict/evidence:
Independent verifier identity/verdict/evidence:
Owner PLAN grant reference (if actually issued):
Owner COMMIT grant/reference and reconciled commit (if actually issued/executed):
No release/deployment inference.

## Handover
Completed:
Not executed:
Blocked:
Next exact action:
Scope exclusions confirmed:
Final HEAD/status:


---

<!-- 07_OWNER_REVIEW_CHECKLIST.md -->

# Owner / Manager Review Checklist

## Before PLAN grant
- Local facts/checkers recorded; no lost unrelated work.
- Scope stays execution tree+Stage mapping+coverage.
- No duplicate quantity owner,billing,ledger migration or generator.
- D01–D10 resolved or deliberately gated per package.
- Native test route and exact disposable target identified before site-writing work.
- New link permission and out-of-balance mapping handling explicit.
- Historical references and quantities preserved.
- Paths/commands/candidate/approvals bound through actual workflow.
- Plan has separate reviewer evidence,not merely builder agreement.

## Before COMMIT authorization
- Exact candidate/diff reviewed;undeclared changes absent.
- Required validations actually passed on candidate;native/offline distinguished.
- Ordinary allowed/denied routes tested.
- Migrations repeat-safe,no quantity/history rewrites.
- Independent verification findings resolved/deferred with justification.
- Commit tree/base/intention match applicable workflow;safe intermediate state.
- Public upload,merge,release and deployment not implied.

## Before completion acceptance
- End-to-end mapping journey works.
- Coverage doesn't misrepresent mapping as progress.
- Unmapped legacy records remain valid.
- Final verified baseline and known limits documented.
