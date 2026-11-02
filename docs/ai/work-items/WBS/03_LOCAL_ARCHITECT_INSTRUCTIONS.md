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
