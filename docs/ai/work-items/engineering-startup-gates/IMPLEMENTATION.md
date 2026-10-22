# Engineering startup gates — implementation and evidence

## Result and authority

Implemented under the owner's direct instruction to delegate planning/building, independently verify, and commit. This is a bounded engine change, not a claimed native orchestrator role execution or a new manufactured PLAN/COMMIT grant. Parent approved the builder's local plan and independently reviews the result. Protected role prompt files and the historical `scope-context-portability` worktree/state are unchanged.

New Construction/native code tasks receive `engineering-startup/v1`. The engine supplies six mandatory context files through immutable, read-only snapshots; coordinator startup records the actual execution checkout Git root/branch/full and short HEAD/status and executes both repository checkers before dependent role dispatch. Failures block launch with recorded evidence and bounded owner-only diagnostics.

The engine checks evidence bindings at preparation, immediately before launch, and when accepting results. Mandatory instruction drift, changed context snapshots, Git baseline drift, or unexpected checker input changes invalidate affected evidence. Builder changes are handled explicitly: the resulting candidate must pass fresh checker proof. The engine does not regenerate schema facts automatically.

## Files changed by builder

- `orchestrator/engineering_startup.py`: versioned policy selection, safe required paths, task-level normative context hashes, explicitly scoped factual context updates, checker input fingerprints, Git baseline, offline startup execution, bounded diagnostics and report replay/binding checks.
- `orchestrator/engine.py`: new-task policy registration; preparation, dispatch and acceptance guards; startup evidence and original context-path provenance in role packets; fresh builder-candidate proof; guarded scope adoption.
- `orchestrator/preflight.py`: visible mandatory context/static policy check; existing checkpoints identify legacy policy without auto-migration.
- `orchestrator/dashboard_api.py`: policy-aware mandatory provenance for task projections.
- `dashboard/bootstrap.py`: new-task policy/default context and recorded bootstrap manifest; legacy checkpoint reconciliation retains its original configuration; uninitialized old attempts fail explicitly before policy-changing initialization.
- `dashboard/app.py`: base repository context summary displays the professional guide/root workflow and consistent mandatory flags.
- `orchestrator/tests/test_engineering_startup.py`: negative, positive and replay tests, including a disposable real BOQ schema/facts feature.
- `dashboard/tests/test_api.py`, `dashboard/tests/test_bootstrap_recovery_ownership.py`: summary/default policy/recovery checks and disposable-source bootstrap isolation. The latter previously created worktrees in the developer repository; the test now commits its brief only in a temporary Git repository with hooks disabled.

Parent owns the engineering guide, root instructions/index, prior reports, session notes, final independent verification and commit.

## Operational behavior for future work

1. Use the qualified updated controller and a fresh worktree containing the committed standard/context/checkers. CLI initialization selects the policy automatically for Construction/native code tasks; dashboard new-task bootstrap records it explicitly.
2. Define the actual task and bounded scope. Normative `AGENTS.md`, professional standard and root `AGENT_WORKFLOW.md` remain pinned and excluded from agent write scope. A task changing these instructions needs separately reviewed reconciliation.
3. Ordinary schema features may explicitly declare `docs/ai/SCHEMA_FACTS.md`; handovers may explicitly declare `SESSION_MEMORY.md`; factual navigation changes may explicitly declare `docs/ai/CONTEXT_INDEX.md`. Only exact relative paths permit such updates. Broad directory/glob entries cannot silently authorize mandatory-context changes. Existing owner PLAN scope/hash and grant requirements continue to govern implementation.
4. Startup checkers execute in a read-only source sandbox, with network namespace isolation and hidden read-only control/work-item mounts. Each checker is limited to 30 seconds and 256 KiB combined stdout/stderr. The coordinator captures the interpreter and outcomes. Raw bounded logs remain in private coordinator storage with directory mode 0700/file mode 0600; roles receive digests and report references, not raw log contents.
5. Role packets identify original relative paths and immutable snapshot paths; roles must read them and truthfully report Files Read. Mechanically supplying readable context is demonstrated; the engine cannot prove an agent understood every sentence.
6. If instructions, source or schema drift, inspect recorded evidence and resolve the specific failure. Do not overwrite frozen reports, edit authoritative grants, silently use another checkout, or run `--update` to mask an unintended schema discrepancy.
7. Existing initialized old checkpoints remain explicitly legacy; they do not gain these checks merely because the controller code is newer. No active controller was upgraded by this task. Old bootstrap attempts without a completed checkpoint require explicit policy reconciliation; the engine does not create a general legacy opt-out for fresh real tasks.

The report only establishes local checkout/context consistency. Remote branch freshness, deployed database correctness, Frappe lifecycle/permissions/financial behavior, and release readiness require the relevant additional evidence.

## Builder verification

- Startup on implementation checkout: schema checker passed; context checker 11/11 passed before implementation.
- New engineering startup tests: **23 passed** with real network-isolated Bubblewrap and synthetic agents. These include missing guide, disabled policy, source/control/Git write denial, missing sandbox mounts, snapshot/instruction/factual drift, concurrent source changes, scope/adoption constraints, owner gate preservation, real checker fixture, real schema/facts/handover fixture, builder candidate proof, timeout/output/privacy limits, cache filtering and successful report replay.
- Existing core engine tests: **49 passed** before later narrow factual/scope additions; full regression evidence below supersedes that intermediate run.
- Affected dashboard suites (`test_api`, `test_read_only_context`, `test_bootstrap_recovery_ownership`): **27 passed** before final source formatting. Parent independently reruns final affected/full suites.
- Ruff checks and formatting passed for all changed/new Python files before parent independent review.
- Complete offline engine and non-browser dashboard suites started against the final code. Builder logs: `/tmp/engineering-startup-builder-full.log` and `/tmp/engineering-startup-builder-dashboard.log`. Final results are recorded below; tests running were not counted as passes.

No provider execution, native role qualification, ERP/site/database mutation, migration, production deployment or historical replay was performed. SQLite/test commits were confined to disposable fixtures. Bubblewrap tests required reviewed execution outside the tool sandbox because its network namespace capability is restricted inside that sandbox; isolation requirements were preserved.

## Final suite results

Builder complete offline engine suite: **268 passed / 18 failed in 142.93 seconds**. The 18 failures match the known main-controller historical Stage 4 source-hash guards; frozen historical hashes were not changed. This is increased coverage with unchanged baseline failures, not a fully green qualification claim.

Independent parent complete offline engine suite: **268 passed / 18 failed in 146.80 seconds**, matching builder results and unchanged historical guard failures.

Non-browser dashboard initially stalled inside the outer tool sandbox in the existing synchronous `TestClient` case `test_server_side_review_derivation_and_mismatch_rejection`; parent faulthandler output identified its first request/AnyIO portal wait. The parent reran that isolated case outside the outer sandbox (**1 passed**) and then the entire non-browser dashboard suite against the frozen implementation: **71 passed in 47.58 seconds**. Three browser/UI suites were excluded; no browser qualification is claimed. See [independent review](REVIEW.md).
