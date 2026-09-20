# Canonical Plan — LangGraph Workflow Orchestration and Offline Pilot

| Field | Value |
|---|---|
| Work item | `scope-context-portability` |
| Document | CANONICAL_PLAN.md (single source of truth for this work item) |
| Revision | **r5 (canonical)** — includes the five pre-Phase-0 contract corrections |
| Date | 2026-09-11 |
| Status | **PLAN COHERENCE REVIEW COMPLETE** — Phase 0 remains unstarted; owner execution authorization is separate |
| Execution location | Isolated git worktree, branch `feature/scope-context-portability`, from `develop` |

> **Purpose.** This file is the canonical, self-contained implementation plan for the `scope-context-portability` work item. It exists so that a fresh AI session (e.g., Codex, acting as architect or builder) can implement the plan **without reading the prior conversation**. It contains: the locked owner decisions, the verified repository baseline, the platform-selection rationale, the complete r5 design (including all pre-Phase-0 corrections), the phase plan with exit gates, the acceptance criteria, the risk register, the correction log, and the exact technical contracts. If any section conflicts with an older document, **this file wins**.

---

## 0. Executive summary

Replace manual copy-paste between AI agents with a **LangGraph `StateGraph`** orchestrator that drives native CLI agents (Codex, Antigravity, OpenCode) through file-mediated dispatch packets and validated structured results. Build it in an isolated worktree, prove it on a small offline pilot (making `ai_context_check.py` portable), then adopt the historical `erp-arabic-bilingual-data` work and run pending Stage 4 under orchestration. Human gates remain human; commits require explicit owner authorization; historical evidence is never rerun or rewritten.

**Why LangGraph:** persistent workflow state, conditional routing, approval pauses (`interrupt`), and resumable execution, without forcing native agents into LangChain abstractions. Alternatives (OpenClaw, Hermes, Temporal) were evaluated and rejected for this initial single-machine scope (§3).

**End state:** the owner approves decisions; agents communicate through files; the repository and the SQLite checkpoint are the only sources of truth.

---

## 1. Locked owner decisions (non-negotiable)

These decisions are binding. Any implementation that violates them is out of scope.

1. **Commits require explicit owner authorization.** The orchestrator may stage and create a commit only with a valid, single-use, owner-issued `COMMIT` token (§7.5). This supersedes the earlier automatic-commit choice.
2. **The pilot remains offline.** Neither checker requires a Frappe site, `--site`, or `TARGET_SITE`. The metadata linter already resolves paths relative to the script; the context checker contains the hard-coded root.
3. **Stage 4 retains the full independent review panel:** proposal first, then separate AI-A1/A2/A3 reviews, followed by AI-R verification.
4. **Adopt completed ERP work and historical evidence without rerunning or reverifying it.** Historical counts and hashes are descriptive, not execution inputs.
5. **Implement real native-agent dispatch; printing a prompt is a diagnostic/manual fallback only.** Full pilot acceptance requires all four core roles to execute natively (§12.1).
6. **Implement quorum support before the pilot that exercises it.**
7. **Read workflow state from LangGraph checkpoints.** `STATE.json` remains an export. The SQLite checkpoint database is the single authoritative state store; the JSONL ledger is an exported audit record only (§4.2).
8. **Builder repair packets include all unresolved findings and links to the approved contract,** not only newly discovered findings.

**Supplementary decisions (2026-09-10, resolving former open questions):**

- `orchestrator/` lives **inside the app repository** with its own environment and dependencies; explicit packaging exclusions and a wheel/install packaging test are mandatory (§4.1).
- Retain all logs and checkpoints for the pilot; revisit retention only at adoption time.
- Role prompts in `docs/ai/roles/` govern both orchestrated and non-orchestrated manual sessions (single source of role instructions).
- CLI invocations and model pinning are resolved by the Phase 0 capability probe; the probe report is the authority.

---

## 2. Verified baseline facts (2026-09-10)

These facts were re-verified against the live repository. They replace any conflicting prior claims. Do not re-litigate them; record blockers if they change.

| # | Fact | Implication |
|---|---|---|
| 1 | `scripts/ai_context_check.py` is **not import-safe**: all checks and `sys.exit()` run at module import (no `if __name__ == "__main__":` guard); hard-codes `REPO_ROOT = Path("/home/mohamed/frappe-bench/apps/construction")` (line 31); Check 8B shells out to `schema_drift_checker.py` via that constant. | Pilot must add import safety and derive root from `__file__`. |
| 2 | `scripts/lint_scope_metadata.py` is already import-safe (proper `main()` guard) and resolves its base path from `os.path.dirname(__file__)`. | Pilot must prove this with tests; refactor only if a real gap is found. |
| 3 | Neither checker imports `frappe`; neither requires a site, `--site`, or `TARGET_SITE`. | Pilot is offline by construction. |
| 4 | Both scripts are tracked in git and currently unmodified; a clean worktree from `develop` contains exactly the code the pilot must receive. | Pilot starts from a clean, known baseline. |
| 5 | The entire `erp-arabic-bilingual-data` body of work (all Stages 0–4 code, `docs/ai/work-items/`, `construction/data/localization/`, `construction/data/bilingual/`) is **uncommitted** on `feature/erp-arabic-bilingual-data` at `e7be488`. | The isolated worktree will not contain it; adoption uses a separate, explicitly configured ERP execution target (§7.6). |
| 6 | Stage 4 historical export authority: the immutable evidence manifest `docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-4-initial-export-manifest.json` records export `account_catalog_20260910_121018.json`, SHA-256 `206ecfae…`, recorded 2026-09-10T12:10:18Z. The live governed manifest may advance after authorized imports, while builder evidence `evidence/stage-4-export.md` describes the earlier 2026-09-09 export (SHA `d9699243…`). | Historical adoption records the immutable initial-export manifest and never regenerates that export. The live governed manifest remains the current service authority and must not redefine historical adoption provenance. |
| 7 | `PROPOSAL_PENDING` does not exist in the 2026-08-23 workflow vocabulary. | Defined here as a Stage-4 sub-status (§11.2), not a work-item status. |
| 8 | No `langgraph` dependency, `docs/ai/roles/` directory, or `AGENT_WORKFLOW.md` exists yet. Python 3.14.5 is available system-wide. | Phase 0 creates all of these. |
| 9 | The Stage 4 bundle service's **current public boundary is `build_import_payload(bundle, now_utc=None)`** with internal, non-caller-selectable governed-manifest resolution (`_governed_manifest_path()` → `_load_governed_manifest()` → `_reload_verified_export()` → `validate_bundle()`). `load_candidate_from_export` appears in historical review narratives only and does **not** exist in the shipped service. | The orchestrator consumes the shipped interface; it must not rebuild the completed service to a stale interface (§11.3, §11.4). |
| 10 | `pyproject.toml` declares `flit_core.buildapi` with `flit_core >=3.4,<4`; legacy `setup.py` also uses bare `find_packages()` and `include_package_data=True`. | Standard PEP 517 builds use Flit. A Python package under `orchestrator/` could also be discovered by the legacy setuptools path. Keep both paths isolated and test the actual Flit artifacts (§4.1). |

---

## 3. Platform selection (locked)

**Decision: LangGraph.** Use it as the workflow engine; write only the adapters and Construction-specific rules.

| Option | Verdict | Reason |
|---|---|---|
| **LangGraph** | **Selected** | Persistent `StateGraph` + SQLite checkpoints give durable state, conditional routing, approval interrupts, and resumable execution without forcing native agents into LangChain agent abstractions. Codex/Antigravity/OpenCode remain independent CLI processes. |
| OpenClaw | Rejected for now | Credible agent hub with external-harness support, but does not provide out-of-the-box implementation of this exact workflow. Re-evaluate if a ready-made agent dashboard becomes the priority. |
| Hermes Agent | Rejected for now | Useful as a participating agent; documented delegation primarily creates Hermes workers, which does not preserve native coding tools. |
| Temporal | Rejected for now | Durable workflows and approval handling, but adds operational infrastructure beyond this initial local, single-machine workflow. Re-evaluate for company-wide multi-machine deployment. |

**Key LangGraph mechanics relied upon:**

- `interrupt()` for human gates: the graph halts; `approve` resumes exactly one named gate.
- Checkpoint resumption: LangGraph resumes an interrupted node from its beginning. Therefore side-effecting actions (dispatch, commit, import) must be **separate nodes** from approval nodes, and side-effecting nodes must re-verify their preconditions inside the node (§4.3).
- Conditional edges for routing: implementation defect → builder; design defect → architect; optional → backlog; disagreement → owner pause (§7.2).

---

### 3.1 Scope

Build the isolated in-repository orchestrator, execute the offline checker pilot, and then adopt only pending ERP Stage 4 work. Phase gates in §10 govern this sequence; historical ERP implementation and evidence are not reopened.

### 3.2 Non-goals and authorization boundary

No replacement coding agents, Frappe runtime changes, vendor edits, MCP permission expansion, or general company task platform. One work item runs per execution worktree; independent read-only reviews may run concurrently. No push, merge, or deployment automation. Code commits and test-site imports remain separately owner-authorized. The orchestrator may create its workflow artifacts and dispatch approved builder work; this is distinct from permission to commit or mutate ERP data.

### 3.3 Definitions (binding)

- **Canonical JSON / H(value)**: UTF-8 JSON with sorted object keys, `ensure_ascii=False`, separators `(',', ':')`, no NaN/Infinity, hashed with SHA-256. Array order is significant; each contract specifies its ordering. This matches the shipped `canonical_sha256` serialization for valid JSON values.
- **Plan revision**: immutable approved plan bytes identified by `plan_revision_hash`. **Scope contract**: the objective, allowed paths/operations, acceptance criteria, and validation commands, identified by `scope_hash = H(scope_contract)`. A PLAN grant binds these, not changing implementation bytes (§7.5).
- **Code candidate**: the frozen source manifest in §5.2; `candidate_id = H(manifest)`. Its base commit is the recorded stage-start HEAD. Later stages may start from an authorized preceding commit; moving a base during a stage requires reconciliation and renewed affected review.
- **Stage 4 proposal candidate**: the private proposal projection and governed export binding defined in §5.3. Its `candidate_id` is neither the source-manifest hash nor the completed bundle/payload hash.
- **Finding ID**: work-item-scoped stable ID (`SCP-NNN` for the pilot), allocated without collision by the orchestrator when accepting the first reviewer finding. Remediation retains the ID.
- **Review cycle**: one build/repair → verification round returning an accepted verifier verdict for a stage. Architecture → plan-review revision rounds also count toward the same stage budget, so routing back to architecture cannot evade escalation. Parallel panel responses are collected as one review round; duplicates do not increment it.
- **Finding snapshot**: `(finding_id, classification, reproduction_digest, relevant_evidence_digest)`. Hash normalized failure semantics and relevant code/test assertions, excluding timestamps, run IDs, timing noise and unrelated evidence. Record the normalized material alongside the digests. If normalization cannot be established, rely on the total cycle limit rather than claiming an unchanged blocker.
- **Unchanged blocker**: at least one blocking finding has the same snapshot across two consecutive accepted review rounds. Stable IDs alone do not establish this. Changing only log timestamps does not establish progress.
- **Quorum**: all configured independent reviewer decisions. Stage 4 requires AI-A1, AI-A2 and AI-A3 with complete row coverage on the same proposal candidate (§11.4).
- **Repair packet**: all unresolved findings and snapshots, approved contract references, current candidate identity and round. Optional backlog suggestions are labeled non-blocking.
- **Dispatch mode**: `native` or explicit diagnostic `manual`; manual dispatch never satisfies native-pilot acceptance.
- **Adoption**: recording completed work and historical evidence pointers without re-execution or retrospective verification.

---

## 4. Architecture and runtime

### 4.1 Runtime isolation and packaging

- Keep `orchestrator/` inside the app repository, with a gitignored `orchestrator/.venv`, Python ≥3.11, and dedicated hash-pinned dependencies. Include LangGraph, the SQLite checkpointer, Pydantic and test tools; build/install tools belong to this development environment, not app runtime dependencies.
- The orchestrator does not import Frappe. Offline pilot jobs require no site; ERP jobs carry the separate execution descriptor in §7.6. Provider network access remains through native CLIs.
- **Preserve the declared Flit backend.** In `pyproject.toml`, explicitly set `[tool.flit.module] name = "construction"`; add `[tool.flit.sdist] exclude = ["orchestrator/", "tests_offline/"]`. Do not configure these directories as Flit external data. Keep the existing `<4` backend compatibility constraint; Phase 0 pins a compatible build-tool version rather than silently upgrading the backend.
- **Protect the retained legacy path.** Change `setup.py` package discovery to `find_packages(exclude=("orchestrator", "orchestrator.*", "tests_offline", "tests_offline.*"))`. If package-data exclusions are supplied, the valid `setup()` keyword is a mapping, e.g. `exclude_package_data={"orchestrator": ["*"], "tests_offline": ["*"]}`; it is not a function call. Package discovery exclusion is the primary legacy control. Runtime `.venv`/`var` content must also be gitignored.
- **Packaging proof:** build an sdist and wheel using the declared PEP 517 Flit backend, inspect their contents, rebuild a wheel from the sdist, and install that wheel with `--no-deps` into a fresh temporary venv. Assert no `orchestrator/`, `tests_offline/`, workflow runtime state, or workflow dependencies enter the app distribution. Assert the `construction` package is present without importing its Frappe-dependent initializer. Separately test the retained setuptools discovery configuration. These are Phase 1 checks; no packaging build is required merely to approve this document.
- Sources: [Flit module and distribution configuration](https://flit.pypa.io/en/stable/pyproject_toml.html#contents-of-distribution-files), [setuptools package-data configuration](https://setuptools.pypa.io/en/latest/userguide/datafiles.html).
- Orchestrator code commits require separate authorization (§10). No build configuration is changed by this documentation revision.

### 4.2 State authority

- **The SQLite checkpoint database is the single authoritative state store** (`orchestrator/var/checkpoints.db`, WAL mode, single writer). Authoritative records are the LangGraph checkpoint data **and** the structured **job records in SQLite** (dispatches, results, approvals, transitions, commits).
- The JSONL ledger (`orchestrator/var/ledger/`) is an **exported audit record only** — a derived, append-only mirror for human and tooling inspection. It is never read for control flow and is never replayed or independently used to rebuild state.
- `STATE.json` in the work-item directory follows the same rule: an atomic export (write temp + rename) regenerated after every committed transition; never read for control flow.
- **Backup and recovery**: per-run SQLite backups use a consistent snapshot (`VACUUM INTO` or online backup API). Recovery restores the SQLite snapshot only; the JSONL mirror is then **regenerated from the restored database**. Doctor (§9) verifies checkpoint integrity and that mirror regeneration matches the restored authority. Restoring a snapshot enters the recovery pause described in §4.3 before any dispatch or token use.
- Checkpoint state records: work item, stage, plan revision hash, `candidate_id`, active jobs, completed dependencies, approvals, escalation counters, pause reason, and schema version. All state documents carry `schema_version` and migrate forward only.
- Work-item statuses are `DRAFT`, `PLAN_SUBMITTED`, `NEEDS_REVISION`, `APPROVED_FOR_BUILD`, `BUILD_IN_PROGRESS`, `BUILD_COMPLETE`, `CHANGES_REQUESTED`, `VERIFIED_FOR_RELEASE`, `RELEASED`, `CANCELLED`, and `PAUSED`. Planning goes DRAFT → PLAN_SUBMITTED → APPROVED_FOR_BUILD (after review and owner grant), with NEEDS_REVISION returning to PLAN_SUBMITTED. Build goes BUILD_IN_PROGRESS → BUILD_COMPLETE → VERIFIED_FOR_RELEASE, with CHANGES_REQUESTED returning to build or architecture review as classified. PAUSED saves `pause_reason` and `resume_to`; resume rechecks dependencies. Owner cancellation ends active work. Commit completion is a separate job record; RELEASED requires an independently authorized, externally completed release record, never merely a commit. Stage-scoped sub-statuses (§11.2) live in `stages`.

### 4.3 Execution integrity

- Use a per-work-item execution lock. Dispatch, result, approval and commit records live in authoritative SQLite with unique `(work_item, stage, role, candidate_id, attempt)` keys. JSONL is export-only. Duplicate results never advance twice.
- Persist a dispatch intent before attempting process creation and record the native session identity as soon as available. The gap between starting a process and recording its identity is explicitly an uncertain outcome, not a safe retry opportunity.
- A local idempotency key does not make an external CLI idempotent. Separate approval, dispatch, collection and commit nodes; recheck authoritative job and authorization records on replay.

| Reconciliation situation | Action |
|---|---|
| Intent recorded and execution never attempted, or a recorded launcher error establishes that no child process was created | One infrastructure retry is allowed; retain the logical job key and audit the launch attempt. |
| Known session still alive | Reattach the monitor; do not launch another session. |
| Valid archived terminal result for the recorded job/session/candidate | Validate and adopt once, regardless of whether it changed files. |
| Launch may have occurred; session is dead/unknown and terminal result is missing or invalid | Pause for reconciliation. Clean source files, absent markers, no partial output and an untouched site lock do not establish non-execution. |
| Commit/import outcome uncertain | Reconcile the external operation; never automatically repeat it. |

**Commit reconciliation:** before execution, persist a commit intent containing `job_id`, `token_id`, repository identity, branch, `expected_parent_sha`, `expected_tree_oid`, `candidate_id` and manifest hash in SQLite. Flush an atomic verify marker with the same fields before invoking Git. Reserve the token for this job; it cannot be used by another job. On restart:

1. Confirm the recorded repository/branch and inspect HEAD without changing it.
2. Require HEAD's sole parent to equal `expected_parent_sha`, its full tree to equal `expected_tree_oid`, and its full delta to equal the manifest. Record a `Workflow-Job: <job_id>` trailer in the planned commit and verify it as additional correlation.
3. On an exact match, record completion and consume the token transactionally in SQLite. Only then mark the verify marker complete; never delete the sole recovery evidence before database completion is durable.
4. If HEAD is unchanged, advanced differently, or identity is ambiguous, pause. Do not issue another commit automatically, even if a marker exists.

After restoring a database backup, execution remains recovery-paused until jobs and operation intents that could postdate that snapshot are reconciled against native sessions, markers and Git/site evidence. A restored snapshot must not reactivate an old approval token. External evidence aids reconciliation; it does not replace SQLite as workflow authority.

Human gates use interrupts in nodes without external side effects. `approve` resumes one identified gate; a resumed node must observe the existing recorded grant/reservation rather than issue another.

### 4.4 Observability

Structured JSONL artifacts derive **from** the authoritative SQLite records: a run log per run (`orchestrator/var/logs/<run_id>.jsonl`) and the audit ledger (`orchestrator/var/ledger/`), both exported only (§4.2). Correlation IDs (`run_id` → `job_id` → native `session_id`) flow through every record. `status --json` emits machine-readable state exported from the checkpoint for scripting.

---

## 5. Artifacts, candidates, and files

### 5.1 Layout

```
work-items/<id>/
  STATE.json                     <- export only (4.2)
  inbox/<role>.md                <- current-role view, regenerated per dispatch
  outbox/                        <- latest results per role (convenience view)
  runs/<run_id>/
    inputs/                      <- immutable dispatch packets (prompt, candidate ref)
    candidate/                   <- code manifest and synthesized-tree archive only
    results/<job_id>.json        <- immutable validated result (SQLite acceptance governs routing)
    explanations/<job_id>.md     <- human-readable rationale for the result
    evidence/                    <- command logs: cmd, cwd, UTC start/end, exit code
```

- JSON results are validated and accepted into SQLite before they drive routing; Markdown explains the decision. A Markdown verdict without a valid JSON twin does not advance the graph.
- The execution runner captures new command evidence; the graph links it and never rewrites it. Historical evidence remains byte-identical.
- Private Account exports and populated business-data bundles stay in `<site>/private/stage4/`. Repository artifacts carry manifest references and non-sensitive summaries only. The orchestrator scans generated packets for configured private markers and refuses to dispatch a packet that embeds private rows.

### 5.2 Code candidate freezing

A code candidate is a canonical manifest `{kind: "code", base_commit, branch, entries}`. `base_commit` is stage-start HEAD and is also the expected commit parent. Sort entries by repository-relative POSIX path. Each entry records path, kind (`file|symlink|deleted`), mode and content SHA-256; symlink content is its target text and is never followed. Deleted entries have null mode/content and require absence in the target tree.

- Include all approved added/modified/deleted paths, including eligible untracked files. Compare against the stage base; plain `git diff` alone misses untracked content, although Git diffs do represent tracked deletions and mode changes.
- Reject traversal, duplicate paths and undeclared changed files in the execution candidate. Exclude generated run state, checkpoint/marker files and the snapshot's own destination to avoid recursive candidates.
- Synthesize the exact target tree from the base and frozen entries using a separate temporary Git index; archive that tree under `runs/<run_id>/candidate/`. Eligible untracked bytes are included in the synthesized tree, not copied afterward from a changing worktree.
- Derive `candidate_id = H(manifest)`. Recheck source bytes and the expected parent before testing, review and commit; changed candidate content invalidates affected verification and COMMIT authorization, not the standing PLAN grant (§7.5).
- Approved, non-sensitive documentation may be included only when frozen and reviewed. Subsequent machine status/evidence exports are not silently added to the commit.

### 5.3 Private Stage 4 identities and artifact storage

Use distinct names for distinct objects; never compare them as if interchangeable:

| Field | Exact meaning |
|---|---|
| `export_sha256` | SHA-256 of the governed export file bytes, checked through the existing governed-manifest contract. |
| `proposal_sha256` | H of a private projection `{schema: "stage4-proposal/v1", export_sha256, rows}`. Sort rows by identity; each contains `identity`, `english`, `is_group`, and the complete `proposal` object. Exclude A2 decisions and review-generated top-level row flags. |
| Stage 4 `candidate_id` | H of `{kind: "stage4-proposal", export_sha256, proposal_sha256}`. It identifies the immutable proposal reviewed by the panel. |
| `bundle_sha256` | The shipped `canonical_sha256(completed_bundle)`, including composed A2 fields and review flags. It must equal the bundle hash returned by `build_import_payload`. |
| `payload_sha256` | H of the exact `result["payload"]` list returned by `build_import_payload`, retaining its array order. It is computed by the integration layer; the service does not return a field with this name. |

The proposer freezes its private projection before review. Each reviewer writes a separate private decision artifact and a non-sensitive result envelope bound to the proposal `candidate_id`. A deterministic composer adds A2 decisions to a new completed bundle, sorting bundle rows by identity and preserving the frozen proposal projection. Adding these decisions does not change the proposal candidate. Changing any proposal field creates a new candidate and requires all panel roles to review that new candidate.

Proposal rows, decision rows, completed bundles, payloads and private snapshots remain under the configured `<site>/private/stage4/` job directories. They must never be archived under repository `runs/.../candidate/`. Repository/state envelopes contain only opaque private artifact references, hashes, counts and non-sensitive status. Raw native tool transcripts that can contain rows stay in private storage; validate/redact before publishing summaries. The pre-dispatch scanner is one check, not a guarantee for subsequently generated output. Credentials and consumable authorization tokens are never included in model-visible prompts or transcripts.

---

## 6. Native-agent adapter contract

### 6.1 Roles

| Role | Default tool |
|---|---|
| Architect | Codex |
| Plan reviewer | Antigravity |
| Builder | OpenCode |
| Final verifier / AI-R | Separate Codex session |
| Account proposer | Separate OpenCode session |
| AI-A1 linguistic reviewer | Separate Antigravity session |
| AI-A2 domain reviewer | Separate Codex session |
| AI-A3 structural reviewer | Separate OpenCode session |

Configured models are pinned in role config; actual tool/model/session identities are recorded in every result. Independent reviewers receive the same frozen candidate and **never** receive peer verdicts.

### 6.2 Adapter responsibilities

Each adapter must **launch, monitor, collect, and validate** a native session:

- Launch with the rendered dispatch packet; enforce per-role timeouts (default 45 min soft warn / 60 min hard kill, configurable).
- Monitor liveness; detect CLI auth/permission prompts (the orchestrator never answers them).
- Collect the result envelope and evidence; validate against the JSON schema before anything touches the graph.

**Failure classes — all block advancement and are recorded:** `MISSING_BINARY`, `AUTH_FAILURE`, `DENIED_ACTION`, `MALFORMED_RESULT`, `EVIDENCE_UNAVAILABLE`, `TIMEOUT`. Agent-work failures are never auto-retried. An infrastructure failure may retry once only when the launcher establishes no child was created (§4.3); absence of partial output is insufficient. Auth, denial and timeout outcomes after launch require reconciliation or owner action.

### 6.3 Result envelope (schema v1)

`schema_version, job_id, work_item, stage, role, tool, model, session_id, dispatch_mode, candidate_kind, candidate_id, plan_revision_hash, prompt_version, status (COMPLETE|FAILED), verdict, findings[], evidence_paths[], started_utc, finished_utc`. Stage 4 envelopes also carry the applicable named hashes from §5.3 and opaque private artifact references. The orchestrator allocates new finding IDs and validates existing ones; it records tool/session metadata from adapter observations, not solely agent claims. Malformed or schema-violating output = `MALFORMED_RESULT`.

### 6.4 Manual fallback (diagnostic only — does not satisfy native acceptance)

If a CLI cannot run headless (determined by the Phase 0 probe, §10), dispatch for that role degrades to printing the packet and awaiting a manually placed result file. The job is flagged `dispatch_mode: manual`; the fallback is loud in `status` output and in the ledger. **Manual mode supports diagnostics and development only.** It does not satisfy the native-pilot acceptance criterion: full pilot acceptance remains blocked until all four core roles (architect, plan reviewer, builder, AI-R) execute natively through their adapters (§12.1). If the Phase 0 probe shows Antigravity cannot operate acceptably headless, that is a **blocking finding on Phase 0 exit**, not a downgrade of acceptance.

---

## 7. Routing, findings, escalation, and approvals

### 7.1 Normal sequence

**Architecture -> plan review -> owner approval -> build -> tests -> independent verification -> commit authorization -> commit.**

### 7.2 Finding routes

| Classification | Action |
|---|---|
| Implementation defect | Return to OpenCode (builder) with a repair packet (§3.3) |
| Design defect | Return to Codex architecture, then Antigravity plan review |
| Optional improvement | Record in backlog without blocking |
| Unresolved disagreement or business decision | Pause for owner decision |

### 7.3 Architecture revisions

An architecture revision records the affected requirements and the impact on existing implementation and evidence. A changed plan revision receives renewed owner approval (§7.5); ordinary code fixes within the existing revision do not. Dependent verification becomes stale; unaffected evidence remains available and referenced.

### 7.4 Escalation

Pause (`PAUSED`, `pause_reason=ESCALATED`) after **three** unsuccessful review cycles for a stage, or **two** consecutive cycles with the same unchanged blocker (§3.3). Counters persist in the checkpoint across route changes and restarts; only an explicit owner escalation-reset decision records a new budget. A plan revision alone does not silently reset counters.

### 7.5 Approvals and commit binding

Only the owner-facing approval interface records grants in SQLite; agent JSON and a token digest in a prompt cannot confer approval. Native agent configurations must deny the approval command/control store. Phase 0 probes this boundary; if the available permissions cannot enforce it, keep authorization and the operation owner-executed instead of claiming an unattended approval gate.

Common authorization fields are `token_id`, `work_item`, `gate_id`, `scope`, `issuer`, `issued_utc` and `status`. Add the scope-specific bindings below. A single issuance cannot approve another gate/job.

| Scope | Binding and lifecycle |
|---|---|
| `PLAN` | `plan_revision_hash`, `scope_hash`, repository identity, execution branch and planned stage(s). Consumed once to establish a standing plan grant. Ordinary code edits and approved repair cycles retain that grant. Any plan/scope revision requires a new grant; the old grant is retained as history, not silently applied to the new revision. |
| `COMMIT` | Code `candidate_id`, manifest hash, repository identity, branch, `expected_parent_sha`, `expected_tree_oid` and commit job ID. Reserve before attempting the operation, consume after reconciled success. Candidate/parent/tree changes invalidate it. |
| `DRY_RUN` / `IMPORT` | Separate scopes and separate issuances with the ERP descriptor and artifact hashes in §7.6. A dry-run grant never authorizes apply. |

Code commit preparation must use a temporary index containing only the frozen candidate over `expected_parent_sha`. If the real index contains pre-existing staged changes, pause without altering them. Run applicable formatting before freezing; if a hook later changes candidate bytes, abort and return to review. Immediately before commit, confirm the expected parent, entire staged delta and authorization. Immediately afterward, verify the full parent/tree/delta and job trailer as in §4.3. No extra path or mode change is acceptable. Do not automatically reset or rewrite a mismatched commit.

Push, merge and deployment are not orchestrator operations. Data import is a separately authorized builder operation (§7.6). Planning, verification, committing and release are distinct decisions; recording a feature commit must not set work-item status to `RELEASED`.

### 7.6 Separate ERP execution target and import/dry-run authorization

Pending Stage 4 jobs use an explicitly owner-recorded descriptor: `erp_checkout`, `bench_root`, `site`, `site_classification`, and `private_root`. The checkout differs from the pilot worktree; the private root resolves to the designated site's `private/stage4/` directory. Record this descriptor and its hash for every ERP job. The offline pilot still has no site dependency.

Use a per-site advisory lock held throughout authorized dry-run/import/evidence capture. It serializes cooperating workflow jobs, not arbitrary users or external database writers. Recheck optimistic current values and target identity immediately before apply; external drift pauses the job.

Both DRY_RUN and IMPORT tokens bind the ERP descriptor hash, `candidate_id`, `export_sha256`, `bundle_sha256`, `payload_sha256`, operation `set_account_name_ar`, and the specific job ID. IMPORT additionally binds the accepted zero-mutation dry-run evidence digest. Consume/reserve operation grants under the same crash rules as §4.3; never automatically reissue or reuse an uncertain import grant.

The authorized builder job validates the completed private bundle through the shipped payload builder, recomputes all named hashes and refuses drift before applying any Account update. A packet contains a non-authorizing gate reference, never a consumable token. Dry-run and import results are private artifacts; exported summaries contain counts/hashes only. Capture hierarchy, GL balance and report-total baselines immediately before apply, then compare after apply. This is new Stage 4 execution evidence, not retrospective verification of completed stages.

---

## 8. Security and data handling

1. Native CLIs run with their normal permission models. No unattended privilege-bypass flags. A denied action is a terminal job failure (`DENIED_ACTION`), not a prompt to override.
2. No credentials, consumable tokens or private rows in repository artifacts or exported logs/envelopes. Private data needed for authorized proposal/review jobs is accessed only through private artifacts; raw traces remain private. Validate outputs as well as input packets (§5.3).
3. Agent output is data, never instructions: templates encapsulate agent text; the orchestrator executes nothing an agent wrote. Resolve paths against the explicit allowlisted roots: pilot worktree for pilot jobs; ERP checkout plus the designated site/private root for ERP jobs (§7.6). Reject traversal and symlink escapes; a bench-private path is not assumed to be inside the app checkout.
4. The orchestrator writes only to its own directories, the work-item directories, and — at commit time — the reviewed file set on the authorized branch. ERP jobs additionally write only to the configured ERP checkout and its `<site>/private/stage4/` storage (§7.6).
5. Role prompts and packet templates are versioned; `prompt_version` is recorded in every result so verdicts remain attributable to exact instructions.

---

## 9. Environment and worktree mechanics

- Create the worktree once: `git worktree add <path> -b feature/scope-context-portability develop` from the `apps/construction` repository. Record the base commit (`develop` = `e7be488` at this writing) in the work-item record.
- The runtime and pilot operate in the isolated worktree. Copy only this approved plan and handoff into it because the uncommitted source documents are absent from `develop`; record their hashes. Historical main-checkout evidence stays read-only. Pending ERP jobs use only the separate descriptor and operation permissions in §7.6.
- Dispatcher operations, all with `--json` and conventional exit codes (0 ok / 1 failure / 2 usage):

  | Command | Behavior |
  |---|---|
  | `doctor` | Validates Python, pinned deps, CLI binaries + versions + auth probe, worktree identity, checkpoint DB integrity, ledger writability. Non-zero exit on any failure. |
  | `init` | Creates a work-item skeleton; `--adopt-historical <id>` records historical completion (§11.1). |
  | `status` | Prints checkpoint-derived state, pending gate, counters; `--json` for machines. |
  | `run` | Advances the graph until the next human gate or completion. |
  | `approve` | Issues a bound token (§7.5) and resumes the named gate. |
  | `pause` / `resume` | Owner-controlled halt and continuation with reason recorded. |

---

## 10. Implementation phases

### Phase 0 — Contracts, role prompts, and capability probe (est. 1-2 days)

Deliverables: JSON schemas v1 (state export, result envelope, finding, repair packet, approval token); packet/explanation templates; structure validation; permanent role prompts under `docs/ai/roles/`; pinned `requirements.txt`; and a **native-CLI capability probe report** (per tool: headless mode, output capture, exit codes, session identity, permission behavior) — this probe is the go/no-go input for adapter design.

**Exit:** the concrete role prompts are owner-reviewed; schemas validate positive/negative samples of the already-defined contracts; all required native CLI probes pass and the report is recorded. A missing capability blocks exit. Use harmless read-only probe prompts and private temporary output; Phase 0 does not implement the pilot or mutate ERP data.

### Phase 1 — Graph and native adapters (est. 3-5 days)

Deliverables: checkpointing, dispatch, approvals, routing, restart reconciliation, structured results, candidate freezing, quorum collection, job records, `doctor`, packaging exclusions, and the packaging test.

**Exit:** orchestrator unit tests green; a scripted stub adapter completes the happy path including a kill-and-resume mid-dispatch; `doctor` green in the worktree; the packaging test passes. The orchestrator is then **frozen** (code SHA recorded): while the pilot builder changes checker scripts, the running orchestrator does not change; any orchestrator change afterward requires owner approval and a Phase 2 re-run. A separate commit authorization is requested for the orchestrator code itself; lack of that authorization pauses the commit, not silently authorizes it.

### Phase 2 — Workflow verification with synthetic results (est. 1-2 days)

Explicitly labeled `SYNTHETIC` adapter results drive the graph through: implementation-defect routing, design-defect routing, backlog handling, owner-decision pause, quorum pass/fail/incomplete, duplicate-result rejection, stale-approval rejection, escalation at three cycles, escalation at two unchanged blockers, restart with in-flight dispatch, commit-binding invalidation on candidate change, PLAN grant persistence during code fixes, hash separation during A2 composition, private-snapshot containment, failure-before-launch retry, uncertain-launch pause, post-commit/pre-record crash, backup-restore reconciliation, and every adapter failure class (§6.2).

**Exit:** all scenarios pass. Rules: never manufacture defects in the real pilot; synthetic runs never count as proof that native adapters work.

### Phase 3 — Real `scope-context-portability` pilot (est. 2-3 days)

The pilot builder changes the checker scripts; all four core native roles (architect, plan reviewer, builder, AI-R) run through the real task.

Technical requirements (verified against the live scripts, §2):

1. `ai_context_check.py`: derive the repository root from the script location (`Path(__file__).resolve().parents[1]`) — remove the hard-coded absolute path; Check 8B must pass the derived root to its `schema_drift_checker.py` subprocess.
2. Make the module import-safe: wrap execution in `main()` behind `if __name__ == "__main__":`; importing must neither run checks nor call `sys.exit`.
3. Add explicit non-interactive CLI handling via `argparse` (e.g., `--repo-root` override, `--json` summary, `--help`); no prompting; never require `--site` or `TARGET_SITE`.
4. Preserve existing checks and failure semantics; missing or malformed required input fails clearly (recorded FAIL, exit 1) rather than traceback.
5. `lint_scope_metadata.py`: preserve existing offline behavior and path independence; refactor only if tests expose a real gap.
6. Offline tests live in a new repo-root `tests_offline/` (outside the Frappe-importing app package, with its own `conftest.py`) so that fresh-clone `pytest tests_offline/` never imports `construction/__init__.py`. Cover: scope-field violation detection, malformed/unparseable DocType JSON, schema-drift subprocess handling, execution from a changed working directory, execution against a repository copy at a different absolute path, import safety, and CLI exit codes.
7. Fresh-clone gate: copy the worktree content to a clean directory and prove `pytest tests_offline/` plus both checkers pass there with no site and no venv dependency beyond stdlib/pytest.

**Exit:** AI-R verifies the pilot candidate; the owner issues a commit token; the commit contains exactly the verified changes. ERP adoption begins only after Phases 2 and 3 pass.

---

## 11. ERP adoption (`erp-arabic-bilingual-data`)

### 11.1 Adoption entry

Precondition: Phases 2-3 passed. `init --adopt-historical erp-arabic-bilingual-data` records Stages 0-3 and the completed Stage 4 builder work (governed export machinery, report extension-point spike, review-bundle schema/validator including the fixed-path verification) as historical completion with evidence pointers and their recorded hashes. Counts and hashes are stored as descriptive metadata; the Stage 4 export binding records the **current manifest** reference (§2 fact 6). Nothing is rerun, regenerated, or reverified. Pending Stage 4 work starts at sub-status **`PROPOSAL_PENDING`** — not a new build. If adoption encounters an identity conflict that prevents continuation, the graph pauses with the conflict record; completed work is never reopened automatically.

### 11.2 Stage 4 sub-status machine

`PROPOSAL_PENDING -> PROPOSAL_FROZEN -> PANEL_REVIEW -> (revised values -> PANEL_RENEWAL) -> BUNDLE_VALIDATED -> AI_R_VERIFICATION -> OWNER_PAYLOAD_AUTHORIZATION -> DRY_RUN -> IMPORT_AUTHORIZATION -> IMPORT -> POST_IMPORT_EVIDENCE -> STAGE_4_VERIFIED`

### 11.3 Execution sequence (against the actual shipped interface)

1. Dispatch the independent proposer with instructions to read the current governed export through the configured ERP/private context. Private artifact references are transport context, not caller-selectable authority parameters to `build_import_payload`. Preserve the shipped boundary and resolve identity conflicts by pausing; do not recreate historical services or exports.
2. Freeze the private proposal projection and derive its `candidate_id` as specified in §5.3. No A2 decision is present yet.
3. Dispatch independent AI-A1, AI-A2 and AI-A3 sessions on that same frozen projection, with no peer verdicts. Each returns its own private per-row decisions plus a non-sensitive envelope bound to the proposal candidate.
4. Require exact identity coverage, distinct reviewer sessions, evidence/rationale for exceptions and no unresolved blocking rows. A suggested Arabic value change returns to the proposer; freeze a new proposal and renew all three reviews. Do not silently alter the proposal while composing A2 fields.
5. Compose the completed bundle deterministically from the frozen proposal plus accepted A2 decisions/flags. Prove its proposal projection still matches the reviewed candidate, then call `build_import_payload(bundle, now_utc=<current UTC>)`. This existing public entry resolves the governed manifest, verifies export bytes and enforces identity/English plus proposal/A2 contracts. `validate_bundle` alone is diagnostic, not sufficient authority. Never pass a manifest path, caller identity map or expected SHA to the payload builder.
6. Record `bundle_sha256 = canonical_sha256(bundle)` and verify it equals `result["manifest"]["bundle_sha256"]`. Compute `payload_sha256 = H(result["payload"])` separately. Compose panel evidence according to §11.4 and obtain AI-R verification bound to the proposal candidate, bundle, payload, export and panel-result digests.
7. Present the reviewed payload summary, exceptions and exact bindings for owner DRY_RUN authorization. The authorized job recomputes the bindings and captures zero-mutation evidence.
8. Request a distinct IMPORT authorization bound to that dry-run evidence. The authorized builder performs only `set_account_name_ar` with optimistic current-value checks and captures post-import hierarchy, GL balance and report-total comparisons. Any changed input invalidates operation grants and requires new review of the changed artifacts.

Completed services and historical suites are not rerun for adoption. Existing validator calls for the newly populated bundle and tests of the new orchestration layer remain required. Stages 5–8 wait for Stage 4 verification.

### 11.4 Composed validation: shipped service plus panel evidence

The shipped service enforces proposal/A2 rules. The orchestration layer enforces the additional panel contract without changing that service:

- AI-A1/A2/A3 must each have a valid result for the exact proposal `candidate_id`, with one decision for every governed identity, no duplicates/extras and private row-specific rationale for documented exceptions. Proposer and reviewers use distinct sessions; reviewers are independent of each other. Missing coverage or an unresolved blocker fails the gate.
- Verify A2 fields composed into the completed bundle match the accepted A2 decision artifact. Verify the completed bundle's proposal projection equals the panel-reviewed projection. Adding review metadata changes `bundle_sha256` but does not invalidate an unchanged proposal candidate.
- Persist a non-sensitive verification manifest containing `candidate_id`, `export_sha256`, `proposal_sha256`, `bundle_sha256`, `payload_sha256` and each panel artifact digest. AI-R approves this exact manifest. Subsequent changes invalidate the affected AI-R/operation authorization; a proposal change additionally renews the full panel.
- Stage 4 advancement requires the shipped payload-builder check AND complete panel validation AND AI-R verification. No aggregate envelope claiming approval can replace per-row coverage. After an authorized import, AI-R accepts the new post-import equality evidence before `POST_IMPORT_EVIDENCE` advances to `STAGE_4_VERIFIED`; this does not rerun historical suites.

---

## 12. Acceptance criteria

References such as §12.1 and §12.12 identify numbered criteria in this section.

1. **Native-pilot handoff (blocking)**: all four core pilot roles — architect (Codex), plan reviewer (Antigravity), builder (OpenCode), and AI-R verifier (Codex) — execute through their native adapters without manual context copying. `manual` dispatch mode (§6.4) is a diagnostic fallback only and does not satisfy this criterion.
2. Correct builder, architect, backlog, and owner routing, demonstrated by the Phase 2 synthetic suite and the Phase 3 real pilot.
3. Restart and duplicate-result handling without duplicate advancement: reconciliation is driven from authoritative SQLite job records (§4.2), and the JSONL audit mirror is never independently replayed.
4. Persistent escalation counters across route changes/restarts; normalized blocker snapshots ignore timestamp-only changes. The canonical §3.3 supplies the complete definitions.
5. PLAN grants survive ordinary code repair; revised plans require renewal. Reject stale COMMIT/DRY_RUN/IMPORT grants and incomplete/stale per-row panel decisions. Distinct proposal, bundle and payload hashes remain distinguishable under changes to review metadata.
6. Site-free pilot tests passing from an isolated repository copy (Phase 3 fresh-clone gate).
7. An explicitly authorized commit whose **entire commit delta** (added/modified/deleted paths, modes, symlink targets) matches the frozen manifest exactly, with no unrelated staged changes (§7.5). The post-commit verify marker is marked complete only after authoritative completion is durable (§4.3).
8. Preservation of existing ERP work, private data, and historical evidence — byte-identical.
9. `doctor` green on a fresh worktree setup, from documentation alone.
10. Private-data containment: no private rows or credentials in repository artifacts or exported envelopes/logs. Proposal/bundle/payload snapshots and raw data-bearing transcripts remain in designated private storage (§5.3).
11. Documentation landed with the orchestrator commit: role prompts, operator guide for the seven commands, and a `docs/ai/CONTEXT_INDEX.md` entry for this work item.
12. **Packaging exclusion proof**: actual Flit sdist, direct wheel, sdist-derived wheel and installed files exclude workflow code/state and offline tests while including the app package; legacy setuptools discovery also excludes those packages (§4.1).

---

## 13. Risk register

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| R1 | A native CLI lacks usable headless operation (esp. Antigravity) | High | High | Phase 0 probe gates design; manual fallback is diagnostic-only (§6.4); probe failure blocks Phase 0 exit rather than downgrading acceptance |
| R2 | CLI authentication expires mid-run | Med | Med | `doctor` auth probe; adapters detect auth-failure output -> `AUTH_FAILURE`, pause, no advancement |
| R3 | Checkpoint/SQLite corruption | Low | High | WAL; consistent per-run SQLite snapshot (`VACUUM INTO` / online backup API); recovery restores the snapshot and regenerates the JSONL audit mirror from it — never replays the mirror in isolation (§4.2); `doctor` integrity check verifies both |
| R4 | Orchestrator defects block ERP adoption | Med | High | Adoption gated on Phases 2-3; the existing manual process remains the documented fallback |
| R5 | Scope creep toward full automation | Med | Med | Non-goals (§3.2); every human gate preserved; per-event owner authorization |
| R6 | Confusion between the dirty ERP checkout and the clean worktree | Med | High | Orchestrator touches only the pilot worktree; Stage 4 ERP jobs target a separately configured ERP checkout + site lock (§7.6); `doctor` asserts both paths are distinct and each job's path root is validated (§8 item 3) |
| R7 | Historical evidence reinterpreted as current authority | Low | Med | Adoption binds to the manifest (§2 fact 6); counts stored as descriptive metadata only |
| R8 | Prompt drift between runs silently changes review meaning | Med | Med | Versioned role prompts; `prompt_version` recorded in every result envelope |

---

## 14. Open questions — resolved (2026-09-10)

1. **Exact headless invocations and model pinning per tool** — the resolution method is fixed: the Phase 0 capability probe (§10). Actual availability remains to be measured, not claimed as already proven. Probe output is the authority; if a tool cannot operate acceptably headless, Phase 0 exit blocks with that finding (§6.4).
2. **`orchestrator/` placement** — **inside the app repository** (owner-selected), with its own environment/dependencies and explicit packaging exclusions + wheel/install proof (§4.1, §12.12).
3. **Checkpoint/log retention** — retain all for this work item and the pilot; retention revisited only at adoption time.
4. **Role prompts for manual sessions** — yes: `docs/ai/roles/` prompts are the single source of role instructions for orchestrated and non-orchestrated manual sessions alike.

---

## 15. Effort estimate

| Phase | Estimate |
|---|---|
| Phase 0 — contracts, prompts, probe | 1-2 days |
| Phase 1 — graph + adapters | 3-5 days |
| Phase 2 — synthetic verification | 1-2 days |
| Phase 3 — real pilot | 2-3 days |
| ERP adoption (Stage 4 pending work) | ~1 day + review latency |
| **Total** | **8-13 working days** |

---

## 16. Correction history and pre-Phase-0 closure (r5, 2026-09-11)

Earlier revisions selected LangGraph, restored native acceptance, separated SQLite authority from audit exports, retained historical ERP completion, and corrected the shipped service interface. R5 supersedes earlier descriptions of the mechanisms below; no earlier correction-table wording overrides these contracts.

| Bounded correction | Final disposition | Implementation proof |
|---|---|---|
| Restart safety | Retry only after established non-launch; missing output/clean files/locks are insufficient. Durable parent/tree/job commit intent and recovery pause cover uncertain external outcomes (§4.3). | Failure-before-launch, unknown-session, post-commit/pre-record and backup-restore cases (§10 Phase 2). |
| Approval binding | PLAN establishes a standing revision/scope grant; code candidates and operation-specific hashes bind COMMIT/DRY_RUN/IMPORT (§7.5–7.6). | Ordinary fixes retain PLAN; changed revision/candidate/payload/site rejects the affected grant. |
| Hash and storage separation | Code candidate, proposal candidate, completed bundle and payload have distinct definitions. Panel decisions do not mutate the reviewed proposal; sensitive snapshots remain private (§5.2–5.3, §11). | A2 composition, changed-Arabic renewal, distinct hash assertions and output containment. |
| Actual packaging backend | Preserve Flit, configure module/sdist explicitly, use valid setuptools mapping syntax for the retained legacy path (§4.1). | Flit sdist/wheel/install and legacy discovery tests (§12.12). |
| Self-contained definitions | Scope, non-goals, review cycle, normalized finding snapshot, unchanged blocker, quorum and repair packets appear in canonical §3.1–3.3. Both documents use identical numbering. | Documentation reference and cross-document contract checks. |

The eight locked owner decisions remain unchanged. This is a documentation-only correction, not an execution, commit or import authorization.

## 17. Handoff checklist for implementation

Before execution, record owner authorization to begin Phase 0. That authorization is distinct from this consultant coherence sign-off and from later commit/import grants.

During Phase 0 setup:

- [ ] Create the isolated `feature/scope-context-portability` worktree from verified `develop`; record its base.
- [ ] Copy only the approved canonical plan/handoff into it with source hashes; preserve the ERP checkout.
- [ ] Prepare the dedicated environment and pinned dependencies; locate the required CLIs and resolve authentication without exposing credentials.
- [ ] Present concrete role prompts for owner review before engineering-role dispatch. Read-only capability probes use bounded diagnostic prompts.
- [ ] Record probe results for all required native roles; do not relax acceptance on failure.
- [ ] Validate schemas against the final contracts in this document, including the Phase 2 negative scenarios.

## 18. Pre-implementation coherence sign-off

**Consultant verdict (2026-09-11): COHERENT — ready for owner sign-off of the entire plan.** The five bounded corrections are resolved before Phase 0, with no remaining design decision deferred under those findings. The canonical plan and working handoff have identical numbered contracts, the original eight locked decisions are preserved, and section references have been checked. Packaging guidance was checked against the declared Flit backend and official Flit/setuptools documentation; bundle/payload definitions were checked against the shipped service's serializer and return fields without executing ERP code.

Phase 0 still measures native CLI capability, authentication and dependency compatibility. Later phases prove implementation correctness through the specified tests. Those are explicit implementation gates, not claims that the tools or code have already passed. This sign-off is not owner execution, commit, import or deployment authorization.

*Revision r5 (canonical), 2026-09-11. The five bounded corrections are resolved in the document before Phase 0. Implementation evidence is still to be produced under the phase gates. No Phase 0 execution, commits, ERP reruns or data mutation are performed by this revision.*
