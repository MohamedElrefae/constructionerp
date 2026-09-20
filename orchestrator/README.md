# Local workflow orchestrator

For the consolidated operator guide, approval examples, troubleshooting runbook, technical architecture, agent contracts, and extension guidance, see the [end-to-end orchestration system manual](../docs/ai/ORCHESTRATION_SYSTEM_MANUAL.md).

Phase 0 is complete under the owner-supplied [consultant directive](../docs/ai/work-items/scope-context-portability/CONSULTANT_DIRECTIVE_2026-09-11.md). Phase 1 implements the engine, native transports and operator interface. The full Phase 2 qualification and real Phase 3 pilot remain separate gates; no ERP adoption has occurred. See the [implementation record](../docs/ai/work-items/scope-context-portability/IMPLEMENTATION.md).

## Setup and checks

Use the isolated environment from the worktree root:

```sh
uv venv --python python3.12 orchestrator/.venv
uv pip sync --python orchestrator/.venv/bin/python --require-hashes orchestrator/requirements.txt
orchestrator/.venv/bin/python -m pytest orchestrator/tests -q
orchestrator/.venv/bin/python orchestrator/cli.py doctor --json
```

Run namespace tests in the host terminal: an outer desktop execution sandbox can deny the `NETLINK_ROUTE` operation used to create the validation network namespace. Do not remove the isolation to make those tests pass. `doctor` checks the host worktree, pinned dependency versions, native executable versions/hashes and filesystem protection. A native invocation can still fail later because authentication, provider availability or limits change; those failures block advancement.

The exact lock is `requirements.txt`. Its input is `requirements.in`; regeneration is an intentional change using `uv pip compile --generate-hashes`. Frappe is never imported by this runtime. Flit sdist/wheel/rebuild/install checks and legacy setuptools discovery tests exclude `orchestrator/` and `tests_offline/` from the Construction app distribution.

## Authority and independent sessions

LangGraph checkpoints and structured jobs/events/grants share `orchestrator/var/checkpoints.db`. The checkpointer and application use separate connections to that one WAL database, avoiding transaction races with checkpoint background writes. The operator lock serializes coordinators. `STATE.json`, inbox/outbox views and the JSONL ledger are exports only. Synchronous checkpoints precede exported state updates; tampering with an export cannot advance the graph.

Native workers run independently of the coordinator, capture their session identity and retain observations under `orchestrator/var/jobs/`. A restart reattaches to a live worker or accepts its terminal result once. An uncertain launch pauses rather than launching again. Only a proven launcher failure before process creation is eligible for one infrastructure retry. LangSmith tracing is disabled around graph execution. No external memory service stores workflow state.

Pinned native roles are in `roles.json`:

- Architect, plan reviewer and verifier: separate Codex processes/sessions, bundled CLI 0.153.0-alpha.5, `gpt-6-astra`, High.
- Builder: `/usr/bin/opencode-cli` 1.14.33, observed default `opencode-go/gpt-5.6-luna`.
- Quorum roles use separate configured sessions. Antigravity remains unavailable; its authorized Codex substitute is explicit. No Antigravity execution is claimed.

Bubblewrap makes the control code and Git metadata read-only, hides control-store/peer-work-item artifacts, and exposes only selected plan/build evidence to the job. Reviewers receive a read-only source mount. Native authentication/session directories retain their vendor access requirements. Unsandboxed processes owned by the same OS user remain part of the trusted owner boundary; a terminal-only convention is not proof of OS isolation.

Native prompts use a small transport wrapper (`result_json`, `explanation`, `plan_text` strings). The runner validates the inner schema-v1 result and checks job, candidate, plan, prompt and requirement bindings. Native identity comes from the observed process/stream rather than the model's claims. New finding IDs are allocated centrally; exact duplicate identities are reused. A repair packet carries every unresolved finding. Reviewer PASS clears rechecked findings; it never creates owner approval.

The native transport currently supports code candidates. ERP `DRY_RUN` and `IMPORT` execution/approval are disabled pending adoption. The Stage 4 wire schemas do not imply that adoption integration has shipped.

## Operator commands

All commands emit JSON and use exit 0 for success, 1 for failure, 2 for usage errors. Run them from the trusted owner terminal. Use `--root /absolute/worktree` before the command to select another initialized execution worktree.

```sh
orchestrator/.venv/bin/python orchestrator/cli.py doctor --json
orchestrator/.venv/bin/python orchestrator/cli.py init --work-item example --plan docs/example-plan.md --scope /path/to/owner-scope.json --stage 1 --json
orchestrator/.venv/bin/python orchestrator/cli.py status --json
orchestrator/.venv/bin/python orchestrator/cli.py run --json
orchestrator/.venv/bin/python orchestrator/cli.py approve --token-file /path/to/owner-token.json --json
orchestrator/.venv/bin/python orchestrator/cli.py pause --reason "Owner inspection" --json
orchestrator/.venv/bin/python orchestrator/cli.py resume --reason "Inspection complete" --json
```

These examples are not authorization to initialize or run the real checker pilot. Finish the required phase gates first. `run` waits for native jobs until a gate/completion; `--once` returns after one collection pass. Interrupting the coordinator leaves monitored workers alive. `init` is exclusive to one work item per execution worktree and does not launch a job. Its scope file contains:

```json
{
  "allowed_paths": ["scripts/example.py", "tests_offline/"],
  "requirements": ["R1"],
  "validation_commands": [["python3", "-m", "pytest", "tests_offline/", "-q"]],
  "requirement_paths": {"R1": ["scripts/example.py"]}
}
```

Use complete argv arrays, never agent-provided command text. The runner captures required offline validations in a network-isolated, read-only source view. A verifier PASS cannot override failing required validations. Candidate freezing includes tracked/untracked changes, deletions, modes and symlink targets; it rejects undeclared files and later file-set drift. Git's real index is not changed.

`requirement_paths` enables conservative unchanged-blocker snapshots using normalized reproduction descriptions and the relevant source hashes. Without a usable mapping, the total three-cycle limit applies; the system does not invent normalized evidence. Two identical normalized snapshots also escalate. Only `resume --reset-escalation-budget --reason ...` records an explicit new budget.

For multiple stages, use `init --stages 1,2,3`; an optional `stage_contracts` mapping in the scope input supplies each stage's scope. After the verified owner commit is reconciled, `run --advance-stage` starts the next stage from that commit with a new plan gate. A changed scope is supplied by the owner while paused using `resume --scope-file /path/to/revised-scope.json --reason ...`; it returns through architecture and review and invalidates the standing plan authorization.

## Owner grants and commit reconciliation

Approval JSON must match `schemas/v1/approval-token.json`, have status `ISSUED`, and bind the pending gate shown by `status`. A PLAN grant binds plan/scope/root/branch/stages and survives ordinary code fixes. A COMMIT grant binds the exact candidate, manifest, parent, tree and owner commit job. Invalid/stale or consumed token documents are rejected.

The orchestrator **does not execute Git commit, push, merge, deployment or ERP import**. A COMMIT grant records a reserved owner-operation intent under `orchestrator/var/operations/<job_id>/intent.json`. The owner performs the explicitly authorized commit, using exactly the candidate tree and a `Workflow-Job: <job_id>` trailer. A pre-existing staged index must be reconciled first. Then:

```sh
orchestrator/.venv/bin/python orchestrator/cli.py run --record-owner-commit --json
```

This only reads Git, verifies the sole parent/full tree/trailer, atomically records completion and consumes the grant. A mismatch pauses; it does not rewrite or repeat a commit. A successful feature commit does not set `RELEASED`.

## Recovery

A paused in-flight owner inspection can resume without relaunch. Uncertain jobs require explicit owner inspection; do not infer non-execution from a clean worktree. For a dead/unknown job the owner has reconciled, `resume --abandon-job <id> --reconciliation-evidence /path/to/inspection.md --refresh-candidate --reason ...` records the decision and a new reviewed source baseline for the next attempt. The command refuses known live processes. Existing evidence is retained.

`run --backup-to /path/to/backup.db` uses SQLite's consistent backup API and does not dispatch. Restore the database only while the coordinator is stopped; preserve external job/operation observations and the rollback watermark. A detected rollback blocks dispatch and approval creation. `resume --ack-restored-backup --reconciliation-evidence /path/to/recovery-review.md --reset-escalation-budget --reason ...` requires explicit owner review, refuses live observed workers or changed Git HEAD, invalidates old grants and re-enters architecture with a fresh candidate. A post-backup Git operation requires a newer consistent backup or a separately reviewed recovery plan; it is never repeated automatically. The JSONL ledger is never replayed as authority.

## Probes and contracts

`capability_probe.py` discovers `opencode` or `opencode-cli`, prefers the bundled Codex, and supports a no-tools Codex probe. `probe_transports.py --report /path/to/new-report.json` exercises both real adapters without engineering work. Both use normal native authentication and keep raw observations locally under gitignored `var/probes/`. Use a new report path to retain each observation.

`schema_source.py` regenerates the five self-contained JSON schemas; tests detect source/schema drift. `validate.py document <schema-name> <file>` validates a standalone document without accepting it into workflow state. `validate.py structure <work-item> --contracts-only` permits the pre-initialization skeleton without fabricating STATE.json.
