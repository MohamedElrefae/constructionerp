# Implementation record — workflow Phases 0 and 1

**Date:** 2026-09-11 (Africa/Cairo)  
**State:** Phases 0 and 1 closed at authorized commit `4b77803af418cea8459c4cb7d9a0248674845da3`. Phase 2 synthetic verification **PASSED (110/110)** after the owner-authorized P2-F001 collector correction. Source freeze regenerated; amendment remains uncommitted.

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

## Phase 2 execution — 2026-09-11

The owner authorized synthetic verification against commit `4b77803af418cea8459c4cb7d9a0248674845da3`. Added 17 graph-level scenarios under `verification/phase2/`, outside the frozen orchestrator source. The final combined run completed **108 passed / 2 failed** (110 total); all 93 frozen regression tests passed. The new suite used SYNTHETIC delayed sessions, the actual native output parser over fabricated bytes, real local SQLite checkpoints, and throwaway Git repositories. No provider sessions or ERP sites were used.

The two failing cases share one implementation defect: `Engine._collect` discards `MALFORMED_RESULT` and `EVIDENCE_UNAVAILABLE` and persists only `WorkflowError`. Both correctly pause advancement; the persistent classification required by canonical §6.2 is missing. See `evidence/phase-2-findings.md` for the exact reproduction and proposed bounded correction. No correction was applied to frozen code.

The run also proves actual `VACUUM INTO` snapshot rollback detection and owner reconciliation, post-commit/pre-record recovery in a disposable repository, owner-grant preservation across a code repair, complete unresolved finding packets, quorum completion through AI-R, both escalation thresholds across engine restart, and one retry for a proven non-launch. The retained subprocess test kills a coordinator with a detached synthetic worker; it is not a native-provider pilot.

All scenario executions, including the initial harness corrections, are recorded in `evidence/phase-2-validation.json` with three retained JUnit XML reports. The first assembly run used two incorrect fixtures (quorum expected release before AI-R and an invalid normalized-artifact reference); both were corrected outside the frozen source before the final run. No frozen defect was hidden by those corrections.

All 51 frozen files and both checker scripts match their recorded bytes; HEAD remains the owner-authorized commit, and the index is empty. No new project commit or ERP operation occurred. Only verification fixtures, evidence, this implementation record and local session memory changed. Phase 2 has not passed and Phase 3 remains blocked. Canonical §10 requires owner authorization before the proposed frozen-engine correction, followed by a complete Phase 2 rerun. Stage 4 composition/private-site integration remains outside this execution proof; only its existing wire contracts were exercised.

## Authorized P2-F001 correction and Phase 2 completion

The owner explicitly authorized a bounded amendment to `Engine._collect`. The collector now preserves only a recognized `WorkflowError` failure-code prefix from the existing schema allowlist. It does not persist diagnostic suffixes or untrusted exception bodies. Unknown exceptions retain the existing type-only diagnosis; jobs remain subject to the same reconciliation pause and no automatic retry is added.

The final complete rerun passed **110 tests, 0 failed**: all 93 frozen regressions plus all 17 Phase 2 scenarios. The malformed-output regression additionally injects a synthetic private exception suffix and verifies that it never enters the workflow database or exported state. The passing run and all earlier failed runs remain in `evidence/phase-2-validation.json`; final raw JUnit evidence is `evidence/phase-2-run-04.xml`. P2-F001 is resolved by that report; the original finding record remains historical evidence.

Only `orchestrator/engine.py` changed among the 51 frozen files. All other 50 frozen files and both checker scripts are byte-identical. The source freeze was regenerated only after the complete suite passed, with the previous digest and owner amendment recorded. New source-manifest SHA: `4e01059e861249015363eabb487731477952c3943f0160f582f33485ebb1cc5c`.

HEAD remains `4b77803af418cea8459c4cb7d9a0248674845da3`; the index is empty. No project commit, merge, push, native-provider dispatch or ERP site operation occurred. Phase 2's owner-directed synthetic suite is complete. Real pilot and ERP integration acceptance are not claimed; this authorization did not start Phase 3 or authorize a commit.

## Phase 3 kickoff — owner decision required before plan review

The owner signed off Phase 2 and authorized Phase 3. The uncommitted controller amendment and Phase 2 evidence remain preserved in this control worktree. To avoid mixing them into a pilot candidate, a clean local clone at commit `4b77803af418cea8459c4cb7d9a0248674845da3` was created at `/home/mohamed/frappe-bench/worktrees/scope-context-portability-pilot`, retaining branch `feature/scope-context-portability`. The amended frozen controller runs from this worktree using `cli.py --root` against that clean execution target. Its committed controller copy is not the running controller. No baseline commit was created.

CLI initialization succeeded with all seven requirement IDs and narrow source/test paths. A stdlib+pytest environment was provisioned from the local cache without network downloads. Native dispatch was initially rejected by automatic approval review for lacking explicit source/payload transfer consent; the owner then explicitly authorized the scoped Codex transfer. No workaround was used.

The actual native architect session `01a08da7-aa29-7731-b936-d11580e628df` returned BLOCKED with owner-decision finding SCP-001. The graph allocated the finding and paused at `DECISION / decision-0`, before plan review or builder dispatch. The real baseline contains 22 Variation Order fields while SCHEMA_FACTS documents 18. Preserving Check 8B therefore conflicts with the all-pass fresh-copy gate within the current allowed paths. No synthetic defect was introduced.

The native draft/explanation, checkpoint summary, and a proposed documentation-only patch/scope amendment are in the `phase-3-*` evidence files. A local read-only call to the existing guarded schema renderer confirmed the four field additions and valid schema invariants; nothing was applied. The proposed patch changes the two field counts, four missing rows and generated verification date only. Actual source in the execution target remains unchanged. Apparent workflow-document deletions seen by the native architect were its masked mount view; host Git confirms no actual tracked deletions.

Next gate: owner authorization to add only `docs/ai/SCHEMA_FACTS.md` to the pilot scope, followed by renewed architecture and independent plan review. The separate Owner PLAN gate still precedes builder work. No project commit, main-ERP checkout modification, site interaction or builder session occurred.

## Phase 3 authorized reconciliation and reviewer evidence pause — 2026-09-12

The owner-authorized reconciliation archived rejected architect job `job-c1b769164762f806bc4c0b0a` as OWNER_RECONCILED, preserving its raw output and evidence. The fresh architect job `job-8e3944c2b9cf5637a53cac50` accepted the schema feedback and returned a valid PROPOSED result. Proposed plan SHA-256: `8c1c763d6c81a39b010de5c6ad5f319d084ecb2f90027e4cb6a09a90bd292dc1`. The approved four-field documentation scope remains intact.

Independent reviewer job `job-0c6a7cc3df086796fa2d7353` returned FAILED / EVIDENCE_UNAVAILABLE: the original canonical contract exists on the host but is hidden by the work-item sandbox mount. Engine._prepare includes only the new proposed plan in read_artifacts after architecture completes. The graph correctly paused with no active jobs and no owner PLAN grant. This is recorded as P3-F001 in `evidence/phase-3-reviewer-contract-finding.json`. Review PASS and builder authorization are not claimed.

Proposed bounded repair: expose both the original configured contract and current proposal as explicit read-only artifacts, deduplicated; add a targeted visibility regression, rerun the complete Phase 2 suite, and regenerate the freeze. Canonical section 10 requires owner approval before changing the frozen engine. No engine repair or further native retry has been applied. Pilot tracked source remains unchanged; no builder dispatch, project commit or ERP operation occurred.

## Authorized P3-F001 correction — 2026-09-12

Engine._prepare now exposes the configured canonical contract and active proposed plan as deduplicated explicit read-only artifacts. The new regression runs the real adapter sandbox and verifies both documents are readable, neither writable, and unrelated peer results hidden. Initial qualification had a fixture baseline error and a host namespace denial; both runs are retained. Final full rerun: **111 passed, 0 failed** in 55.83 seconds. Ruff and whitespace checks passed. Only engine.py and its corresponding test changed against the prior freeze; checker scripts remain identical and the index is empty.

New source manifest: `2753ff07fbe93f84a8e4bfb6e687a966cf52e27476d3c9140a4fa9eed2e6c5c9`. Owner-authorized reviewer retry follows; no PLAN grant, builder dispatch, commit or ERP operation is implied.

Independent native reviewer retry `job-eb36e5f169894f960d989f64` (session `01a0925b-0edb-7390-9bc9-3fc6c7cd775e`) returned **PASS**, with no findings. Both canonical and proposed-plan hashes were confirmed in captured tool events. P3-F001 is resolved. The graph is waiting at Owner PLAN gate `plan-3f7f6e2b096c64ad049178b4`, bound to plan `8c1c763d6c81a39b010de5c6ad5f319d084ecb2f90027e4cb6a09a90bd292dc1` and scope `f748d729630d1f063433bc4c615643b61e075f3123b3f722cadf8784aa6a191f`. Full bindings and review explanation are recorded in `evidence/phase-3-contract-visibility-retry.json`. No PLAN token has been issued or consumed; no builder has been dispatched. Pilot tracked source remains unchanged.

## Phase 3 PLAN grant and builder handoff failure — 2026-09-12

The exact owner token was recorded and accepted: `owner-plan-grant-phase3-pilot`. OpenCode builder `job-0b3f130e287b123d9b20a0b8` launched in native session `ses_f6d92fe1cffeMIGqB5Jdi8lIrX`. It performed source reads but no implementation. Collection rejected its result as MALFORMED_RESULT; the graph paused for reconciliation while preserving the standing PLAN grant.

P3-F002 records three handoff issues: no checkpoint-derived approval attestation in the builder packet; OpenCode commentary concatenated with final JSON by the parser; and incorrect external schema-path selection by the builder. Its final envelope also uses invalid status/verdict values and must remain rejected. The process identities are stopped, tracked pilot source is unchanged, and raw output is preserved. See `evidence/phase-3-builder-reconciliation.json` for the bounded amendment and reconciliation proposal. No engine/adapter repair or retry was applied; no commit or ERP operation occurred.

## Authorized P3-F002 amendment — 2026-09-12

Builder packets now attest to the checkpoint-confirmed PLAN grant, including gate, plan/scope hashes, stage and execution root without consumable tokens. Schema references point into the execution root. OpenCode parsing groups final response fragments by native message identity and excludes earlier commentary; ambiguous/malformed results remain rejected and engine schema validation is unchanged. All **116 tests passed** (111 existing plus five new regressions) in 56.15 seconds; Ruff and whitespace checks pass. Checker bytes remain unchanged. Source freeze: `f2e60c309c81a8e40ddf013bd2f49b8a405eafd1be30ee7b6b3061cd2535d250`. The owner-approved reconciliation evidence is preserved byte-for-byte; builder retry follows under the standing grant.

## Phase 3 native repair routing and escalation — 2026-09-12

P3-F002 native retry succeeded: OpenCode builder result was accepted, followed by independent Codex verification and two automatic OpenCode repair dispatches under the standing PLAN grant. Three verifier cycles returned BLOCKED. The final builder evidence records 15 passing tests, 11 context checks and scope lint across 19 DocTypes. The final verifier confirms SCP-002 repaired but still blocks on SCP-003 (unguarded help/invalid-option/relocated-linter subprocesses) and SCP-004 (complete frozen-source pre/post equality and package-absence evidence). The graph escalated at 3 unsuccessful cycles, with unchanged_rounds=2, gate `decision-20`; no jobs remain active.

Latest candidate: `e49ab5027d062f931ef9153ad5771388dd51ec1d8415929098fe5715e34c2ce8`. Five source/test/documentation files are changed, all in approved paths. The checkpoint retains prior SCP-002 even though latest reviewer prose resolves it; this discrepancy is recorded without editing authority state. Full history, candidate bindings and reviewer explanation: `evidence/phase-3-escalation.json`. Owner intervention is required by the escalation policy before further work. Phase 3 is not VERIFIED_FOR_RELEASE and no COMMIT gate was reached. No project commits, staging, push, merge or ERP/site operations occurred. Running engine freeze remains unchanged after the 116-test qualification.

## Owner escalation reset and bounded continuation — 2026-09-12

Executed the exact authorized reset command. Standing PLAN grant remained valid. Native builder `job-95c14f13265eceab3a38e3b4` patched the help/invalid-option/relocated-linter subprocess environments and reported 15 passing tests, but returned a truncated snapshot SHA-256; strict schema validation paused collection for reconciliation. The raw result and stopped process evidence are preserved in `evidence/phase-3-reset-reconciliation.json`. No engine code changed.

The separately authorized execution channel then completed SCP-004 capture from a Git-tree snapshot of the current candidate: all 802 source files, contents, Git modes and symlink targets match before and after the clean-copy suite; all prescribed tests/checkers and changed-directory commands passed. Package-absence checks confirmed no installed Construction/Frappe/ERPNext. Full inventories, commands and hashes are in `evidence/phase-3-complete-source-validation.json`; raw logs and capture script remain in control runtime. Candidate `c2af221d73b069cdddaa92dad7d4caec072246854dbde1bb09dfae2df7267d41` is preserved separately from the pre-repair checkpoint. Independent AI-R acceptance remains pending; no result was synthesized or checkpoint advanced. No staging, commits or ERP/site operations occurred.

## Preserved candidate reconciliation and current evidence capture — 2026-09-12

Executed the exact authorized reconciliation/refresh command, abandoned `job-95c14f13265eceab3a38e3b4`, and verified candidate c2af221d73b0 / tree b9c328ff603414f652713f61cf745829a728e07d before dispatch. Standing PLAN grant remained active. Native continuation added drift-child tests, producing candidate `532f0175dc88f19d111a42c498b60eb0bd832d412af12d4d7df7247b48d6b133`; 17 tests and both checkers pass. AI-R confirms SCP-002/SCP-003 resolved but still blocks on SCP-004 source-equality evidence. The graph escalated on two unchanged-blocker rounds (2 unsuccessful cycles), gate `decision-28`.

The operator repeated the authorized complete-source capture for this exact current candidate: 802 files matched frozen-tree source before/after tests, package absence confirmed, sanitized environment (including GIT_* removal), all fresh-copy and unrelated-CWD checks passed. Evidence: `evidence/phase-3-current-complete-source-validation.json`. This does not substitute for independent AI-R PASS. The native read_artifacts list exposes only plans and builder logs; the resume command records reconciliation evidence by hash but does not deliver the operator report to AI-R. The precise delivery gap and final state are in `evidence/phase-3-preserved-candidate-resume.json`. No engine changes, checkpoint edits, commits or ERP operations occurred.

## P3-F003 verifier evidence visibility amendment — 2026-09-12

The engine now discovers candidate-bound validation reports for reviewer and verifier jobs, validates candidate/manifest/tree bindings, hashes and deduplicates them, copies them into immutable job runtime artifacts, and exposes only those explicit files through the read-only sandbox. Stale, forged, malformed, symlinked and unrelated reports remain excluded. The isolation regression verifies verifier access, immutability and peer-result isolation.

The complete Phase 2 suite passed **117 tests, 0 failures** in 57.13 seconds. Ruff and whitespace checks pass, and every file in the renewed freeze matches its recorded hash. The amendment record is `evidence/phase-3-verifier-evidence-visibility.json`; the runtime freeze is `orchestrator/var/freeze/manifest.json`. AI-R retry has not been executed and no commit or ERP operation occurred.

## P3-F003 AI-R retry handoff — 2026-09-12

The owner-authorized reset command was executed, but AI-R was not launched. The controller safely rejected dispatch with `Candidate file set drift`. The exported state reports `BUILD_COMPLETE` and candidate `532f0175dc88f19d111a42c498b60eb0bd832d412af12d4d7df7247b48d6b133`, while persisted engine configuration still contains the original empty candidate `38e04df7...`; dispatch therefore fails its binding check. No second refresh was attempted because refresh invalidates the standing PLAN grant.

The complete handoff, command result, Git identity, and required recovery steps are recorded in `evidence/phase-3-p3-f003-retry-handoff.json`. Another agent should reconcile the SQLite candidate/config binding to the owner-authorized candidate and tree, preserve `owner-plan-grant-phase3-pilot`, verify the candidate-bound 802-file evidence, and only then retry AI-R. No files were staged, no commit was created, and no ERP operation occurred.

## P3-F003 AI-R retry reconciliation and outcome — 2026-09-12

The next agent reconciled the pilot worktree and SQLite state without invalidating the standing PLAN grant.

Reconciliation actions:

- Reverted `orchestrator/engine.py` and `orchestrator/tests/test_engine.py` in the pilot worktree to base commit `4b77803af418cea8459c4cb7d9a0248674845da3`. These files are controller amendments that belong to the control worktree running `cli.py --root`; their presence in the pilot execution target caused the candidate file set to drift from the owner-authorized `532f0175...` candidate.
- Added `docs/ai/work-items/scope-context-portability/evidence/` to the config `generated` list so workflow-generated validation evidence is excluded from candidate recheck.
- Updated the SQLite `workflow_meta` `config` candidate binding from the original empty candidate `38e04df7...` / tree `b72f470d...` to the owner-authorized candidate `532f0175dc88f19d111a42c498b60eb0bd832d412af12d4d7df7247b48d6b133` / tree `2f546c2b88f288a258a3c603ab88ab2b380b06c0`. All other config fields, including the consumed `owner-plan-grant-phase3-pilot`, were preserved.

Verification:

- Live `recheck` against the updated config passed.
- A fresh `freeze` of the current pilot working tree reproduced candidate `532f0175...` and tree `2f546c2b...`.
- The candidate-bound 802-file complete-source evidence (`evidence/phase-3-current-complete-source-validation.json`) matches the same candidate/tree and reports `complete_source_equality_before=true`, `complete_source_equality_after=true`, and confirmed package absence.

AI-R retry:

- Engine `run --once` dispatched builder job `job-585711c603d12775030d7c70` under the standing PLAN grant and candidate `532f0175...`.
- The OpenCode native worker failed immediately with exit code 1 and stderr `Session not found`; stdout was empty.
- Collection classified the result as `MALFORMED_RESULT` and paused the graph at `DECISION` gate `decision-30`, pause reason `MALFORMED_RESULT`, attempt 16, cursor 31.

No project files were staged, no commit was created, no merge/push occurred, and no ERP/site operation was performed. The workflow remains paused before any `COMMIT` gate. Further action requires owner reconciliation/decision. Full details are in `evidence/phase-3-ai-r-retry-outcome.json`.

## P3-F003 owner-authorized builder resume and second session failure — 2026-09-12

The Owner authorized resuming the workflow with an escalation-budget reset for candidate `532f0175...` / tree `2f546c2b...`, authorizing the exact command:

```bash
orchestrator/.venv/bin/python orchestrator/cli.py \
  --root /home/mohamed/frappe-bench/worktrees/scope-context-portability-pilot \
  resume \
  --reason "Owner authorized retry following OpenCode session resolution and P3-F003 verification" \
  --reset-escalation-budget
```

The command was executed from the control repository. The consumed `owner-plan-grant-phase3-pilot` remained valid and the candidate binding stayed at `532f0175...` / `2f546c2b...`.

Outcome:

- Resume event added at seq 32 with `reset_budget=true`.
- The engine dispatched a new builder job `job-09ecd862eaf1f5bc23bcb21e`.
- The OpenCode native worker again failed immediately with exit code 1 and stderr `Session not found`; stdout was empty.
- Collection classified the result as `MALFORMED_RESULT` and paused the graph at `DECISION` gate `decision-32`, pause reason `MALFORMED_RESULT`, attempt 17, cursor 33.

The `Session not found` failure is therefore not transient; it recurred on the owner-authorized retry. This indicates an environment or provider-side issue with the OpenCode CLI session initialization, not a workflow binding or candidate-drift problem.

No project files were staged, no commit was created, no merge/push occurred, and no ERP/site operation was performed. The workflow remains paused at a `DECISION` gate before any `COMMIT` gate. Further action requires owner decision after investigating the OpenCode native transport/session state. Full details are in `evidence/phase-3-builder-resume-outcome.json`.

## P3-F003 Codex AI-R verifier verdict — 2026-09-12

Per the Phase 3 Verifier Dispatch directive, the failed OpenCode builder was acknowledged, the checkpoint was owner-advanced to `BUILD_COMPLETE` with `next_roles=['verifier']` (cursor held at the last applied event; no refresh, no grant change), and the independent native verifier was dispatched.

- Verifier job `job-e7fef639e1a0e34b2deae40d` (Codex `gpt-6-astra`, native session `01a09445-5c45-76b0-89a8-350711d06684`) ran with the P3-F003 candidate-validation report mounted as an explicit read-only artifact. Visibility is confirmed: the verdict explicitly cites the report's inventories.
- Verdict: **COMPLETE / BLOCKED** with genuine findings:
  - SCP-002 and SCP-003 remain blocking and unchanged.
  - SCP-004 is partially resolved: all 802 source entries verified equal to frozen base plus candidate, but the gate executions ran under `/tmp`, outside the permitted execution root, so a compliant in-root gate is still required.
  - New SCP-005: plan section 5 requires retained tests for all five scope dimensions; only `project` is covered, while `company`, `cost_center`, `department` and `branch` lack negative cases.
- The engine auto-dispatched builder job `job-fc24a15e55ab85b109bde818` per routing; it failed immediately with `Session not found`. Collection paused the graph at `DECISION` gate `decision-35` (`MALFORMED_RESULT`, attempt 19, cursor 35).

Per the directive this is escalated as genuine unverified defects. No `OWNER_COMMIT` gate was reached; no commit, push, or ERP operation occurred. Full details are in `evidence/phase-3-ai-r-verdict.json`.

## Builder channel resolution and Codex AI-R PASS — 2026-09-12

Per the Builder Channel Resolution directive, the failed OpenCode builder result (`job-fc24...`, already collected as `ACCEPTED`) was acknowledged; no active job remained to abandon. The `builder` role was re-pinned from OpenCode to the proven native Codex tool (`/opt/codex-desktop/resources/codex`, `gpt-6-astra`, `0.153.0-alpha.5`, effort high) in `orchestrator/roles.json` in both worktrees and in the SQLite config, preserving the builder prompt pin `45190b...`. `orchestrator/roles.json` was added to the config `generated` list so the controller pin file cannot pollute the execution candidate. Doctor passes (`binary:codex`, integrity, configured root).

The engine then ran the full authorized loop in one resume:

- Event 36 `refresh_candidate` (current tree re-frozen; PLAN grant consumed, unaffected), event 37 `resume`.
- Codex builder `job-0c114c5f...` (session `01a09450-...`) returned **COMPLETE / PASS** with new candidate `89f613f9...` / tree `5b5f87ff...`, covering the SCP-005 five-dimension repair and the SCP-004 in-root gate.
- Independent Codex verifier `job-fa5a2cc5...` (session `01a09455-...`, distinct session) returned **COMPLETE / PASS** with no findings.

Workflow is now `VERIFIED_FOR_RELEASE` with empty findings, parked strictly at `COMMIT` gate `commit-703536a0492e00f385d3f844`. No owner `COMMIT` token was issued or consumed, `record-owner-commit` was not executed, and no Git commit, push, merge, or ERP operation occurred. Awaiting separate explicit `COMMIT` authorization. Full details are in `evidence/phase-3-codex-builder-ai-r-pass.json`.

## Phase 3 owner commit recorded — 2026-09-12

Per the Owner Commit Approval directive, the single-use `COMMIT` token `owner-commit-grant-phase3-pilot` (job `commit-phase3-pilot`) was approved for gate `commit-703536a0492e00f385d3f844`, binding candidate `89f613f9...`, parent `4b77803a...`, and tree `5b5f87ff...`.

The owner commit `72da63dc693e320ea8b73d5bdf7000c4fda57f07` was created on `feature/scope-context-portability` in the pilot worktree with exactly the five verified candidate files and the `Workflow-Job: commit-phase3-pilot` trailer. Parent, tree, and trailer all verified to match the token intent. `run --record-owner-commit` reconciled it: workflow is `VERIFIED_FOR_RELEASE` with `committed=true` and no pending gate.

The production ERP checkout (`apps/construction`) and live database were untouched; nothing was pushed or merged to origin. Full details are in `evidence/phase-3-owner-commit.json`.
