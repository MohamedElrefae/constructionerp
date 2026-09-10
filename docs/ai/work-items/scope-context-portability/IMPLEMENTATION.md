# Implementation record — workflow Phases 0 and 1

**Date:** 2026-09-11 (Africa/Cairo)  
**State:** Phase 0 complete under the owner's consultant directive. Phase 1 complete and source frozen; all independent review blockers closed. Project commit awaits separate owner authorization.

The owner authorized Phase 0 completion and Phase 1 in `CONSULTANT_DIRECTIVE_2026-09-11.md`. Canonical r5 and the working handoff remain byte-identical to `SOURCE_BINDINGS.json`. The execution addendum records the authorized native plan-review substitute and the concrete permission boundary.

## Isolation and authority

- Worktree: `/home/mohamed/frappe-bench/worktrees/scope-context-portability`
- Branch: `feature/scope-context-portability`
- Base: `e7be48855bde540464ea302e53c9bfca62b7c462`
- Original ERP checkout: `/home/mohamed/frappe-bench/apps/construction`; its 59 dirty entries are existing work. No ERP services, exports, history or data were modified or rerun.
- No project files staged or committed; no push, merge, deployment or ERP operation. Git commits in regression tests belong only to disposable fixture repositories.
- Workflow state remains local. SQLite owns checkpoints/jobs/events/grants; STATE.json and JSONL are derived exports. No external MemoryGraph writes.

## Phase 0 completion

Five role prompts are owner-approved with exact SHA bindings. Schema-v1 contracts cover state export, result envelope, finding, repair packet and approval token. Role/packet/explanation templates and a pre-initialization structure validator are present. The isolated Python 3.12.3 environment uses hash-pinned dependencies, including LangGraph 1.2.11 and SQLite checkpointer 3.1.1, without adding Frappe runtime dependencies.

| Native capability | Verified result |
|---|---|
| Bundled Codex 0.153.0-alpha.5 | Headless structured output, distinct native session, Astra High; transport passes inside Bubblewrap. Older PATH Codex was rejected by the provider and is not the adapter default. |
| `/usr/bin/opencode-cli` 1.14.33 | Headless structured output and session identity; observed `opencode-go/gpt-5.6-luna` pinned; transport passes inside Bubblewrap. No global symlink change. |
| Antigravity | Desktop is installed; `agy` CLI remains absent. The owner explicitly authorized a separate native Codex plan-review session. No Antigravity run is claimed. |
| Permission boundary | Positive source-write and negative control/Git-write probes pass. Reviewers have read-only source; peer/control artifacts are hidden. Gated operations remain owner-executed. Unsandboxed processes using the same OS account are within the trusted owner boundary. |

A DNS regression caused a later transport probe to time out when `/run` was masked. The wrapper now exposes only the resolver data required by `/etc/resolv.conf`; local runtime sockets remain hidden. Both native transports then passed. The failed observation is retained and the aggregate report points to the final passing report.

## Phase 1 implementation

The engine provides persistent conditional routing, independent native dispatch, quorum collection, owner interrupts, complete unresolved repair packets, and durable escalation budgets. It distinguishes implementation defects, design defects, optional backlog work and owner decisions. Agents return structured stdout; the runner validates bindings and writes durable artifacts.

Job inputs are durable in SQLite before artifact export. Native workers survive coordinator exit, record process/session identity and collect terminal results exactly once. Uncertain launch outcomes pause for owner reconciliation. A single retry requires proof that no native child started. Backup rollback invalidates old grants and requires explicit recovery evidence.

Candidate snapshots include modes, symlink targets, deletions and untracked files. A temporary Git index produces the candidate tree without changing the real index. Required owner-defined offline validations are captured against that candidate; failing tests cannot be overridden by a verifier PASS. COMMIT authorization binds the exact parent/tree/manifest and the engine reconciles only an owner-executed commit. It does not execute commits or ERP operations.

The seven operator commands are `doctor`, `init`, `status`, `run`, `approve`, `pause`, and `resume`. Monitoring releases the writer lock between collection passes so owner pause/status operations remain available. A restart rechecks current owner decisions, candidate, plan and authorization before launching a prepared job.

Flit sdist, direct wheel, wheel rebuilt from sdist and fresh-venv installation are tested. The Construction app distribution excludes orchestrator source/runtime and offline tests; legacy setuptools discovery has matching exclusions.

## Independent review and verification

The owner explicitly authorized the scoped source/test/plan transfer to Codex, excluding private ERP data and credentials. The first independent native review returned four P1 findings. All four were repaired with regression tests:

| Finding | Repair and proof |
|---|---|
| COMMIT token accepted at a PLAN gate | Gate scope must match at both admission and reducer; rejection leaves no grant/event. |
| Crash between artifact write and job insertion | SQLite persists exact inputs first; replay materializes identical packet/spec/schema bytes. Three crash points tested. |
| Monitoring prevents owner pause | Lock is held only per authoritative pass; a second-process CLI pause succeeds while monitoring. |
| Resumed dispatch bypasses current preconditions | Dispatch applies pending owner events and rechecks source/plan/job/grant bindings; pause and two drift cases launch no child. |

The bounded follow-up accepted three repairs and identified an additional approval replay case: a durable pause could precede a stale checkpoint. Approval now synchronizes pending decisions without dispatch before admitting a token; invalid owner resume requests are also rejected before event storage. Regression tests prove the paused workflow remains resumable.

Current full regression result: **93 passed**, including subprocess kill/resume, owner commit reconciliation in throwaway repositories, permission controls, contracts, adapters, routing and packaging. Ruff checks and tracked whitespace checks pass. The final independent bounded review returned **PASS**, with no remaining P1 findings in the repair scope; the original full review and both follow-ups are preserved. Source freeze is recorded in `evidence/phase-1-code-freeze.json`; unit tests are not claimed as the full Phase 2 qualification or real pilot acceptance.

## Evidence and next gate

- `evidence/phase-0-capabilities.json`: aggregate Phase 0 exit, approved fallback and final transport references.
- `evidence/phase-0-role-prompt-bindings.json`: owner-approved prompt bytes and directive binding.
- `evidence/phase-0-boundary.json`: permission boundary observations.
- `evidence/phase-1-native-transport.json`: retained failed DNS-regression observation.
- `evidence/phase-1-native-transport-final.json`: passing Codex/OpenCode transports.
- `evidence/phase-1-independent-review.json`: original independent BLOCKED verdict, preserved.
- `evidence/phase-1-independent-review-r2.json`: preserved follow-up identifying the approval replay case.
- `evidence/phase-1-independent-review-r3.json`: final bounded **PASS**, native session `01a08d90-02e9-7113-beb5-040d1bbcb4de`.
- `evidence/phase-1-code-freeze.json`: frozen source manifest SHA `1a31afa2fba2e00be53d03913a574040e4053d898c492ba2ce0bc183cabce67d`.
- `evidence/phase-1-validation.json`: local test/doctor/packaging and integrity results.

Raw native observations remain under ignored `orchestrator/var/`. No real pilot checkpoint has been initialized. Phase 2 qualification, Phase 3 checker pilot and ERP adoption remain pending. A project commit requires separate explicit owner authorization under canonical §10.
