# Engineering startup gates — bounded implementation plan

Owner request: delegate planning and implementation to a sub-agent; parent independently verifies and commits. This task extends new code-task startup, without manufacturing native grants or changing existing historical state.

## Read and baseline

Read `AGENTS.md`, professional standard sections 1–4, `CONTEXT_INDEX.md`, relevant October 4 session notes, root `AGENT_WORKFLOW.md`, canonical workflow plan sections 0–4, and workflow review WP-A/WP-C. Actual checkout: `worktrees/engineering-startup-gates`, branch `codex/engineering-startup-gates`, full HEAD `ba0e64bc88863ccb6756df4d7438bebb8ed8349b`. Parent copied six instruction/report files from current main; these pre-existing changes belong to the parent. Startup checkers passed: schema consistency and context 11/11.

## Contract and compatibility

- New Construction/native code-task initialization selects explicit versioned engineering startup policy. Dashboard bootstrap includes that policy and mandatory context. Minimal synthetic repositories remain explicitly distinguishable; previously initialized configurations without a policy retain legacy behavior and are not rewritten or restarted.
- Mandatory context: root AGENTS/workflow/session memory, professional standard, context index, schema facts. Add them to existing read-only context mechanism; fail closed for missing/escaping/symlink files or overlapping write scope.
- Preserve approved role files, owner PLAN/COMMIT grants, SQLite transition authority, role independence and historical records. Changing instructions cannot create or broaden authority.
- Normative AGENTS, professional standard and root workflow remain pinned for the whole task. Factual SESSION_MEMORY, SCHEMA_FACTS and CONTEXT_INDEX may change only when their exact relative path is explicitly declared in scope; broad directory/glob scope alone is insufficient. Each job still reads immutable snapshots. Scoped builder factual updates require fresh candidate/checker evidence before acceptance, allowing real schema features and handovers without a separate task. Unapproved factual changes still block.

## Implementation

1. Add focused `orchestrator/engineering_startup.py` policy/context validation and immutable startup evidence helpers. Trusted coordinator captures actual checkout Git root/branch/full and short HEAD/status. Required scripts run through existing read-only-source, offline Bubblewrap boundary, with timeout/output limits and recorded interpreter/argv/exit/output.
2. Bind successful evidence to candidate identity, mandatory context hashes, and checker inputs. Check before/after commands, before native launch, and before accepting completion; context/source changes invalidate affected evidence. Record failed attempts with actionable diagnostics and launch no dependent job.
3. Wire initialize/prepare/dispatch/accept without altering sealed role prompts. Existing snapshot references gain original relative paths; startup packet exposes evidence and tells roles to read supplied snapshots and truthfully report Files Read. Check that exact context/evidence snapshots are readable and read-only using the same sandbox mounts as native dispatch.
4. Dashboard fresh bootstrap supplies required policy/context; reconciliation distinguishes old recorded manifests from new bootstrap defaults so old tasks are not retroactively changed.

## Meaningful verification

- Successful fixture startup with actual command execution and sandbox context visibility.
- Real repository checker path passes on this checkout, without providers or site/database operations.
- Missing professional standard, unreadable/escaping context and failing checker block dispatch.
- Timeout/output bounds fail clearly; command cannot modify source, Git metadata or control store.
- Context tampering after preparation or during a native job, and concurrent Git/source changes, invalidate evidence before dispatch/acceptance.
- All engineering roles receive mandatory provenance and startup report; no owner grant manufactured, builder still needs PLAN.
- Legacy/historical configurations remain compatible; real new code tasks cannot disable required policy through omission.
- Focused new tests, complete offline engine suite (baseline historical hash failures reported separately), applicable dashboard bootstrap/recovery tests, source formatting and context checks.

## Exclusions and completion

No historical controller migration, role prompt edits, ERP imports/recovery fix, Frappe site provisioning, remote memory, provider execution, commits or pushes by builder. Parent owns independent verification, commit and instruction/report updates. Completion requires reviewed code/test evidence, recorded limitations, and an authorized parent commit; passing startup checks alone does not establish Frappe business correctness.
