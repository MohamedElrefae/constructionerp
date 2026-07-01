# Engineering Department Directive: AI Orchestration and Memory System

**To:** Lead Developer / AI Operations  
**From:** Head of Engineering Department  
**Date:** June 29, 2026  
**Subject:** Revised, live-code-verified plan for AI memory, schema drift control, and multi-agent delivery

---

## 1. Executive Summary

This directive revises the previous AI orchestration plan against the live repository at:

`/home/mohamed/frappe-bench/apps/construction`

The original plan is directionally correct, but it assumed a future `.ai/` directory and a generic `modules/` DocType path. The live app already has a repo-local memory system under `docs/ai/`, root memory files, MCP helper scripts, a post-commit MemoryGraph hook, and Frappe DocTypes under:

`construction/construction/doctype/*/*.json`

The revised goal is not to replace the current system in one risky move. The goal is to reach a 100% current-state-aligned orchestration system by hardening what already exists, adding the missing automation from the original plan, and making every agent workflow verify live code before acting.

---

## 2. Live-Code Verification Summary

Verification was performed on June 29, 2026 from the construction app root.

| Check | Live Evidence | Result |
|---|---|---|
| Git repository root | `git status --short` works in `/home/mohamed/frappe-bench/apps/construction`; bench root is not the git root | Verified |
| Current branch | `develop` from `scripts/ai_context_check.py` | Verified |
| Latest commit | `f6c239a` from `scripts/ai_context_check.py` | Verified |
| Root memory files | `AGENTS.md`, `SESSION_MEMORY.md`, `ADR.md` exist | Verified |
| AI docs directory | `docs/ai/CONTEXT_INDEX.md`, `docs/ai/SCHEMA_FACTS.md`, `docs/ai/CODING_PATTERNS.md`, `docs/ai/USER_GUIDE.md` exist | Verified |
| Existing context checker | `scripts/ai_context_check.py` exists and passes with 33 checks, 0 failures | Verified |
| Existing MCP scripts | `scripts/mcp_store.py`, `scripts/mcp_recall.py`, `scripts/session_end.py`, `scripts/seed_memory.py` exist | Verified |
| Existing git hook installer | `scripts/install_git_hooks.sh` installs `.git/hooks/post-commit` for MCP commit capture | Verified |
| Proposed `.ai/` directory | No `.ai/` directory exists today | Not current |
| Proposed `ai_memory_pruner.py` | No `scripts/ai_memory_pruner.py` exists today | Missing |
| Proposed `schema_drift_checker.py` | No `scripts/schema_drift_checker.py` exists today | Missing |
| Proposed `modules/` schema path | Live DocTypes are under `construction/construction/doctype` | Corrected |

Current checker result:

```text
Checks passed: 33
Checks failed: 0
ALL CHECKS PASSED - Safe to seed AI memory.
```

Important caveat: the checker passes but is incomplete for the current app. It treats several live DocTypes as "extra" and `docs/ai/SCHEMA_FACTS.md` contains stale field counts for multiple DocTypes. This must be fixed before relying on memory automation as a release gate.

---

## 3. Current Memory Architecture

The live repo already uses this structure:

| Tier | Current File(s) | Live Status | Revised Rule |
|---|---|---|---|
| Strategic memory | `AGENTS.md`, `ADR.md`, `docs/ai/CONTEXT_INDEX.md`, `docs/ai/CODING_PATTERNS.md` | Present | Human or lead-agent edits only; every change must cite live code or an ADR |
| Schema memory | `docs/ai/SCHEMA_FACTS.md` | Present but stale in places | Must be generated or verified from DocType JSON before agent planning |
| Tactical memory | `SESSION_MEMORY.md` | Present | Session and sprint context; prune or summarize when it grows too large |
| Ephemeral memory | No standardized current files | Missing | Add `docs/ai/active/` or `.ai/active/` only after migration decision |
| MCP cache | MemoryGraph scripts and post-commit hook | Present | Treat MCP as derived cache; repo files always win |

### Decision: Do Not Immediately Move Everything to `.ai/`

The original directive proposed:

```text
.ai/
├── memory/
├── active/
└── scripts/
```

That is not the current state. Moving now would break existing references in `docs/ai/CONTEXT_INDEX.md`, `scripts/ai_context_check.py`, `scripts/session_end.py`, and agent habits around root memory files.

Revised path:

1. Keep `AGENTS.md`, `ADR.md`, `SESSION_MEMORY.md`, and `docs/ai/` as the canonical structure for this cycle.
2. Add `docs/ai/active/` for orchestration baton files first, because it fits the current docs layout.
3. Add compatibility notes before any later `.ai/` migration.
4. Only migrate to `.ai/` after all scripts and prompts support both paths.

---

## 4. Live DocType Inventory

The live app currently has 19 DocType folders (18 with schema JSON, 1 override-only):

| Folder | DocType | Field Count | Notes |
|---|---:|---:|---|
| `boq_header` | BOQ Header | 12 | |
| `boq_import_batch` | BOQ Import Batch | 18 | |
| `boq_item` | BOQ Item | 48 | |
| `boq_item_stage` | BOQ Item Stage | 16 | |
| `boq_quantity_revision` | BOQ Quantity Revision | 35 | |
| `boq_structure` | BOQ Structure | 29 | |
| `construction_settings` | Construction Settings | 26 | |
| `construction_theme` | Construction Theme | 94 | |
| `costitem` | CostItem | 9 | |
| `direct_labor_designation` | Direct Labor Designation | 2 | |
| `form_layout_profile` | Form Layout Profile | 13 | |
| `journal_entry` | Journal Entry | — | Override only: no `.json` schema; extends ERPNext core Journal Entry with searchable Account dropdown |
| `modern_theme_settings` | Modern Theme Settings | 10 | |
| `plantresource` | PlantResource | 5 | |
| `scope_report_access_log` | Scope Report Access Log | 12 | |
| `user_desk_theme` | User Desk Theme | 25 | |
| `user_scope_context` | User Scope Context | 10 | |
| `variation_order` | Variation Order | 18 | |
| `vo_line` | VO Line | 27 | |

### Schema Drift Found During Plan Review

`docs/ai/SCHEMA_FACTS.md` is not fully aligned with live DocType JSON:

| DocType | SCHEMA_FACTS Count | Live Count | Status |
|---|---:|---:|---|
| BOQ Item | 33 | 48 | Drift |
| BOQ Structure | 16 | 29 | Drift |
| BOQ Header | 11 | 12 | Drift |
| Construction Settings | 13 | 26 | Drift |
| Form Layout Profile | 12 | 13 | Drift |
| Construction Theme | 94 | 94 | Aligned |
| CostItem | 9 | 9 | Aligned |
| PlantResource | 5 | 5 | Aligned |
| User Scope Context | 10 | 10 | Aligned |

This confirms the original plan's warning: schema memory can drift even while the codebase is healthy.

---

## 5. Revised Automation Plan

### 5.1 Highest Priority: Schema Drift Checker

Create:

`scripts/schema_drift_checker.py`

Required behavior:

1. Discover DocType JSON files from `construction/construction/doctype/*/*.json`.
2. Extract each DocType name, folder name, field count, fieldname, fieldtype, options, required flag, unique flag, and hidden flag.
3. Compare the live snapshot against a generated snapshot block in `docs/ai/SCHEMA_FACTS.md`.
4. Exit with code `1` if:
   - a DocType is missing from schema facts,
   - a field is missing,
   - a field type changed,
   - a field count differs,
   - `BOQ Item` gains `item_code` or `item_name`,
   - `BOQ Item.cost_item` stops being a `Data` field,
   - `BOQ Structure` loses `lft`, `rgt`, `old_parent`, `is_group`, or `wbs_code`.
5. Provide `--update` mode to regenerate the schema snapshot after human review.

Acceptance command:

```bash
cd /home/mohamed/frappe-bench/apps/construction
python3 scripts/schema_drift_checker.py
```

### 5.2 Update the Existing Context Checker

Revise:

`scripts/ai_context_check.py`

Required changes:

1. Replace the fixed 14-DocType registry with the current 19 live DocType folders (18 schema + 1 override).
2. Stop treating `boq_import_batch`, `boq_quantity_revision`, `scope_report_access_log`, `variation_order`, `vo_line`, and `journal_entry` as dynamically computed extras.
3. Update patch coverage to include `v6_7`, `v6_8`, `v7_0_migrate_quantity_revisions.py`, `v7_1`, and `v7_2`.
4. Replace the stale "expected 34 functions" theme API note with the live count: 17 whitelisted endpoints and 33 functions.
5. Call or mirror `schema_drift_checker.py` so context checks fail when schema facts drift.

Acceptance command:

```bash
python3 scripts/ai_context_check.py
```

Expected result after the fixes:

```text
Checks failed: 0
ALL CHECKS PASSED - Safe to seed AI memory.
```

### 5.3 Add Memory Pruning

Create:

`scripts/ai_memory_pruner.py`

Revised behavior from the original plan:

1. Target `SESSION_MEMORY.md`, not a non-existent `SESSION_LOG.md`.
2. Default threshold: 300 lines in the append-only session log section.
3. Do not require Ollama as the only path. Use deterministic local summarization by default and allow optional `--ollama-model`.
4. Preserve recent entries verbatim.
5. Move older summarized entries into a "Compressed Session History" block.
6. Never delete the original file without writing a timestamped backup under `docs/ai/archive/`.

Acceptance command:

```bash
python3 scripts/ai_memory_pruner.py --dry-run
```

### 5.4 Harden Git Hooks

Current hook behavior:

`scripts/install_git_hooks.sh` installs a post-commit hook that stores commit metadata in MemoryGraph MCP using `scripts/mcp_store.py`.

Required enhancement:

1. Keep post-commit MCP capture.
2. Add optional post-commit pruning:
   - run `scripts/ai_memory_pruner.py --auto`,
   - never fail the commit if pruning fails,
   - log failures to `logs/ai_mcp_audit.log`.
3. Add a pre-agent command, not a pre-commit hook, for schema drift:

```bash
python3 scripts/schema_drift_checker.py && python3 scripts/ai_context_check.py
```

Reason: schema drift should block agent execution before planning or implementation, but should not surprise normal developer commits until the team explicitly adopts it as a commit gate.

---

## 6. Revised Orchestration Baton

Use the current docs structure first:

```text
docs/ai/
├── CONTEXT_INDEX.md
├── SCHEMA_FACTS.md
├── CODING_PATTERNS.md
├── USER_GUIDE.md
├── active/
│   ├── PLAN.md
│   ├── REVIEW.md
│   ├── IMPLEMENTATION.md
│   └── FINAL_DIFF.md
└── archive/
    └── session-history/
```

Do not introduce `.ai/` until compatibility is added to:

- `docs/ai/CONTEXT_INDEX.md`
- `scripts/ai_context_check.py`
- `scripts/session_end.py`
- agent prompt templates
- MCP seed scripts

### Baton File Rules

| File | Owner | Required Gate |
|---|---|---|
| `docs/ai/active/PLAN.md` | Codex architect | Human approval before implementation |
| `docs/ai/active/REVIEW.md` | Reviewer agent | Human skim before implementation |
| `docs/ai/active/IMPLEMENTATION.md` | Builder agent | Must list files changed and tests run |
| `docs/ai/active/FINAL_DIFF.md` | Codex final reviewer | Must compare plan, implementation log, and git diff |

Each baton file must include:

- repo path,
- branch,
- latest commit hash at start,
- files read,
- files changed,
- tests run,
- known gaps.

---

## 7. Standard Operating Procedure

### Phase 0: Pre-Agent Verification

Run:

```bash
cd /home/mohamed/frappe-bench/apps/construction
python3 scripts/schema_drift_checker.py
python3 scripts/ai_context_check.py
git status --short
```

Hard stop if either checker fails.

### Phase 1: Planning

Codex reads:

- user request or GitHub issue,
- `AGENTS.md`,
- `SESSION_MEMORY.md`,
- `docs/ai/CONTEXT_INDEX.md`,
- `docs/ai/SCHEMA_FACTS.md`,
- relevant live Python, JavaScript, and DocType JSON files.

Codex writes:

`docs/ai/active/PLAN.md`

Hard gate: human approval.

### Phase 2: Adversarial Review

Reviewer reads:

- `docs/ai/active/PLAN.md`,
- `docs/ai/SCHEMA_FACTS.md`,
- referenced live code.

Reviewer writes:

`docs/ai/active/REVIEW.md`

Hard gate: human approval or explicit skip.

### Phase 3: Implementation and Test Loop

Builder reads approved plan and review, edits code, and runs the smallest meaningful test set first, then broader tests when shared behavior is touched.

Builder writes:

`docs/ai/active/IMPLEMENTATION.md`

Required content:

- files changed,
- commands run,
- pass/fail result,
- deviations from plan,
- unresolved risk.

### Phase 4: Final Review

Codex reads:

- `docs/ai/active/PLAN.md`,
- `docs/ai/active/REVIEW.md`,
- `docs/ai/active/IMPLEMENTATION.md`,
- `git diff`,
- live files touched by the implementation.

Codex writes:

`docs/ai/active/FINAL_DIFF.md`

Final verdict must be one of:

- `PASS`,
- `PASS_WITH_NOTES`,
- `FAIL_FIX_REQUIRED`.

### Phase 5: Commit and Memory Capture

After human approval:

1. Commit on a feature branch.
2. Let post-commit MCP capture run.
3. Run memory pruning when enabled.
4. Archive completed baton files under `docs/ai/archive/`.

---

## 8. Line-by-Line Review of the Original Plan

| Original Claim | Live-Code Verdict | Revision |
|---|---|---|
| Memory is broken because all memory is treated equally | Partially true | Current memory is tiered informally; formalize lifecycle and pruning |
| Use `SCHEMA_FACTS.md` as strategic memory | Correct | Keep it under `docs/ai/SCHEMA_FACTS.md`, but regenerate from live JSON |
| Add `ARCHITECTURE_RULES.md` | Not current | Use existing `AGENTS.md`, `ADR.md`, and `CODING_PATTERNS.md`; add a new file only if duplication is avoided |
| Use `CURRENT_SPRINT_CONTEXT.md` and `AGENT_ROLES.md` | Not current | Current tactical file is `SESSION_MEMORY.md`; add baton files under `docs/ai/active/` |
| Use `SESSION_LOG.md` and `DEBUG_TRACE.md` | Not current | Use `SESSION_MEMORY.md` and optional active logs |
| Add `scripts/ai_memory_pruner.py` | Missing | Implement against `SESSION_MEMORY.md` with backup and dry-run |
| Add `scripts/schema_drift_checker.py` | Missing | Implement against `construction/construction/doctype/*/*.json` |
| Parse DocTypes in `modules/` | Incorrect for this repo | Correct path is `construction/construction/doctype` |
| Lock MCP read/write by phase | Not enforced in code | Treat MCP as cache now; add governance in scripts and prompts later |
| Standardize `.ai/` directory | Not current | Use `docs/ai/active/` now; migrate later if needed |
| Codex creates `PLAN.md` | Correct concept | Write `docs/ai/active/PLAN.md` |
| Gemini creates `REVIEW.md` | Correct concept | Write `docs/ai/active/REVIEW.md` |
| OpenCode creates `IMPLEMENTATION.md` | Correct concept | Write `docs/ai/active/IMPLEMENTATION.md` |
| Codex creates `FINAL_DIFF.md` | Correct concept | Write `docs/ai/active/FINAL_DIFF.md` |
| Post-commit pruner archives scratchpad | Not current | Existing post-commit stores MCP commit memory only; add pruning explicitly |

---

## 9. Implementation Backlog to Reach 100%

### P0 - Must Do First

1. Create `scripts/schema_drift_checker.py`.
2. Update `docs/ai/SCHEMA_FACTS.md` from live DocType JSON.
3. Update `scripts/ai_context_check.py` so all 19 current DocType folders are expected (18 schema + 1 override).
4. Add `docs/ai/active/` and `docs/ai/archive/` directories with `.gitkeep`.

### P1 - Operational Hardening

5. Create `scripts/ai_memory_pruner.py`.
6. Update `scripts/install_git_hooks.sh` to optionally run memory pruning post-commit.
7. Update `docs/ai/CONTEXT_INDEX.md` with the active/archive baton paths.
8. Add a short pre-agent command block to `AGENTS.md`.

### P2 - Agent Governance

9. Add baton templates for `PLAN.md`, `REVIEW.md`, `IMPLEMENTATION.md`, and `FINAL_DIFF.md`.
10. Add MCP write policy documentation: repo is source of truth, MCP is cache.
11. Add a final-review checklist requiring `git diff` plus live-file reads.

---

## 10. Acceptance Criteria

The plan reaches "100% current-state aligned" only when all of the following are true:

1. `python3 scripts/schema_drift_checker.py` exits `0`.
2. `python3 scripts/ai_context_check.py` exits `0`.
3. `docs/ai/SCHEMA_FACTS.md` matches all 18 schema-owning live DocType JSON files (the `journal_entry` override has no schema to track).
4. `docs/ai/CONTEXT_INDEX.md` points to the actual memory and baton paths.
5. `docs/ai/active/` contains templates or active baton files.
6. `scripts/ai_memory_pruner.py --dry-run` exits `0`.
7. `scripts/install_git_hooks.sh` documents the post-commit MCP and pruning behavior.
8. No agent prompt references non-existent `modules/`, `.ai/`, `SESSION_LOG.md`, or `DEBUG_TRACE.md` as mandatory paths.

---

## 11. Final Engineering Direction

Approved direction:

Keep the current repo-local memory model, harden it with schema drift automation, add an active orchestration baton under `docs/ai/active/`, and defer a `.ai/` migration until compatibility is proven.

This gives the team the benefits of the original plan without breaking the working memory structure already present in the app.

**Signed,**  
Head of Engineering Department  
AI and ERP Infrastructure Division
