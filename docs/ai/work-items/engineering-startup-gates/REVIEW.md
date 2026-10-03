# Engineering startup gates — independent review

Review date: 2026-10-04. Owner authorized sub-agent planning/implementation, parent verification and a local commit. Implementation worktree: `worktrees/engineering-startup-gates`, branch `codex/engineering-startup-gates`, implementation parent `ba0e64bc88863ccb6756df4d7438bebb8ed8349b`. Main integration target before commit: `f77adf576b9f9fbb1a4e8e2576f47c437520b101` on `develop`. Intervening main commits changed bilingual evidence and its regression runner; none changed reviewed controller files.

## Decision

The bounded startup integration is suitable to commit for future development. New Construction/native code tasks automatically require the six context files, record their actual Git baseline, execute both existing local checkers before role dispatch, and reject invalid evidence before launch or acceptance. Immutable snapshots are readable and read-only under the real Bubblewrap mount boundary. Builder results receive fresh checker proof for their resulting candidate.

This is verified source integration with offline/synthetic qualification. It is not a completed native-provider qualification, migration of the older running controller, or certification of customer release readiness. The full engine suite is not green: its unchanged historical provenance failures remain open. None of the customer application findings closes because this startup policy exists.

## Independent verification

| Check | Parent-observed result | Scope and limit |
|---|---|---|
| Complete offline engine: `orchestrator/.venv/bin/python -m pytest orchestrator/tests -q --disable-warnings --tb=short` | **268 passed, 18 failed; 146.80 seconds** | Includes existing Phase 2 synthetic engine/routing/recovery tests and all **23 new startup tests**. No provider jobs. |
| Historical failure comparison with prior main review log | **18 identical failed test IDs; no new failures or removed failures** | All fail the preserved Stage 4 historical service-hash binding; frozen expected hashes and adoption fixtures remain unchanged. Prior main baseline was 245 passed / 18 failed. |
| Non-browser dashboard: `dashboard/.venv/bin/python -m pytest dashboard/tests --ignore=dashboard/tests/test_ui_integration.py --ignore=dashboard/tests/test_ui_week3.py --ignore=dashboard/tests/test_ui_plan_approval.py -q --disable-warnings --tb=short` | **71 passed; 47.58 seconds** | API, bootstrap/recovery, permissions, registry, context and subprocess tests. Browser/UI suites excluded. |
| `python3 scripts/schema_drift_checker.py` | **PASS: 21 schema-owning DocTypes; 1 override-only folder** | Current repository JSON versus facts; no deployed database validation. |
| `python3 scripts/ai_context_check.py` | **11 passed, 0 failed** | Current local checkout consistency only. |
| Ruff check/format on all nine changed/new Python files; `git diff --check` | **PASS** | Formatting/static/whitespace checks; no Frappe runtime claims. |
| Older controller checkout | **Clean at `eb30de04ab200cb8ba2288bcf80bd0c4268a9e18`** | No controller/state/configuration migration or grant replacement performed. |

The engine suite and final dashboard suite ran outside the outer tool sandbox with reviewed fixture-only execution. Startup tests retained their own network-isolated read-only Bubblewrap sandbox. The outer sandbox blocks its namespace capability; removing isolation would conceal a real deployment requirement. The non-browser dashboard first stalled inside that outer sandbox at an existing Starlette/AnyIO synchronous thread portal; the isolated case passed outside it in 0.25 seconds, then the complete non-browser suite passed. Interrupted/timed-out runs are not counted as passes. One attempted affected-suite command referenced a nonexistent filename and collected no tests; the final complete suite supersedes it.

Hash-locked Python 3.12 environments were provisioned separately for the controller and Starlette dashboard. They are ignored local tooling, not application dependency changes. Review/test summaries are recorded here; temporary detailed logs remain local under `/tmp/engineering-gates-parent-*` and are not required for ordinary startup.

## Findings corrected before acceptance

1. Fixed completion-report replay so recovery can reuse only successful, still-bound immutable proof; no evidence overwrite.
2. Fixed timeout handling for children that close output pipes while continuing to run; tests verify process-group termination and combined output bounds.
3. Preserved failed-check diagnostics privately with bounded bytes, 0700 directories and 0600 files; agents receive hashes and report references.
4. Narrowed instruction pinning so ordinary schema features can update explicitly scoped factual files while normative instructions remain fixed; a real BOQ JSON/facts/handover fixture reaches verification with fresh proof.
5. Rejected apparent glob write scope intersecting mandatory context and guarded scope adoption, without changing the global legacy candidate matcher.
6. Excluded interpreter cache paths from checker bindings so bytecode caches do not create false schema/source drift.
7. Replaced an existing bootstrap test's shared developer repository with disposable Git source and disabled hooks in that fixture. The initial run exposed a shared-repository post-commit hook; only the two clean worktrees/branches created by those test attempts were removed. No broad pruning or unrelated branch cleanup occurred.

Parent independently read the startup module, engine lifecycle diff, preflight/projection/dashboard/bootstrap changes, tests, checker source inputs, builder plan/report and guide integration. Frozen role prompts, canonical contracts and historical expected source hashes were not edited. The wrapper adds required snapshot-reading instructions without rewriting approved role files. Mechanical readability is proved; an agent's understanding or truthful reading remains subject to substantive review.

## Future task instructions

Use the updated controller and a fresh execution worktree containing this committed guide and checkers. Dashboard bootstrap records the policy; CLI initialization selects it automatically for real Construction/native tasks. Both checkers run automatically before dependent dispatch and after builder completion. Do not duplicate those commands as claims of personal execution when the coordinator ran them.

For features that change schema facts, handover state or factual navigation, add the exact relative file paths to the approved write scope. Broad directory/glob scope does not permit mandatory-context changes. Normative instruction changes need a separately reviewed task/reconciliation. Checkers contain curated expectations such as DocType names and endpoint counts: a legitimate architecture change may require reviewing their expectations and declaring those checker paths in scope; suppressing a failure is not an acceptable substitute.

Failures block dependent launch or result acceptance. Inspect the immutable failed report and private diagnostic references; reconcile the actual candidate/known job state through the existing owner recovery process. This task does not add an automatic schema-facts generator or an unrestricted startup repair loop. Evidence never grants PLAN/COMMIT approval or release permission.

Existing initialized checkpoints intentionally remain legacy and do not gain this policy through a silent code upgrade. Interrupted old bootstrap attempts without an initialized checkpoint fail explicitly until reviewed reconciliation. No claim is made that the older `scope-context-portability` checkout now enforces these rules. Qualification and any migration of that controller require their own bounded task.

## Commit and data boundary

Stage only the reviewed startup source/tests, operating notes and the six prior engineering/report documentation files. Preserve other main work and integrate onto the current `develop` parent. The owner directly authorized this maintenance commit; no synthetic native approval token or historical grant is created. Source and relevant checks were reviewed explicitly; use `git -c core.hooksPath=/dev/null` only for these local commits because the installed post-commit hook transmits private commit data to external memory without an authorized destination. Do not change global hook settings.

No Git push, production deployment, provider execution, ERP import, live migration or site mutation is part of this task. Customer business correctness, permissions, installation/upgrade recovery and release proof remain governed by the professional standard and open gap report.
