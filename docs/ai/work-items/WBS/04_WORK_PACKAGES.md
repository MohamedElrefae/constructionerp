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
