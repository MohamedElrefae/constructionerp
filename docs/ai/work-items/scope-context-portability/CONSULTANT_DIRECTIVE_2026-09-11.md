# Consultant Review & Directive for Codex: Phase 0 Completion & Phase 1 Authorization

**To:** Codex (Implementing Architect / Builder)  
**From:** Technical Consultant & Quality Assurance Advisor (on behalf of the Project Owner)  
**Date:** 2026-09-11  
**Subject:** Formal Plan Sign-Off, Role Prompt Approval, CLI Resolution, and Directives for Phase 0 Exit / Phase 1 Transition  
**Work Item:** `scope-context-portability`  
**Location:** `/home/mohamed/frappe-bench/worktrees/scope-context-portability`

---

### 1. Verification of Canonical Plan & Handoff (Revision r5)
The Consultant has inspected `CANONICAL_PLAN.md` and `IMPLEMENTATION_HANDOFF.md` at revision **r5**:
- All five pre-Phase-0 contract corrections (Restart safety, Approval binding, Hash & storage separation, Packaging backend via Flit, and Self-contained definitions) are verified matching and coherent.
- All eight locked owner decisions remain strictly preserved.
- The Pre-Implementation Coherence Sign-off recorded in §18 is formally ratified.
- Worktree isolation (`feature/scope-context-portability` based on `e7be488`) is verified. The main checkout `/home/mohamed/frappe-bench/apps/construction` is completely clean and untouched.

---

### 2. Formal Sign-Off: Owner Role Prompts Review Gate (Section 10)
Pursuant to §10 ("Exit: the concrete role prompts are owner-reviewed"), the Consultant has audited all five role prompt definitions under `docs/ai/roles/`:
1. `architect.md` (Hash: `ef527ef0...`) — **APPROVED.** Explicitly bounds architecture scope, mandates requirement IDs, forbids unauthorized file mutations or approval forging, and routes design defects to independent plan review.
2. `reviewer.md` (Hash: `3cd42677...`) — **APPROVED.** Strict read-only role, proper 4-way finding classification, explicit reminder that reviewer PASS does not equal owner build authorization.
3. `builder.md` (Hash: `45190b4f...`) — **APPROVED.** Fully enforces Locked Decision 8 (repairs must address ALL unresolved findings with persistent IDs), bounds execution to packet-allowed paths, and strictly forbids modifying the running orchestrator during the pilot.
4. `verifier.md` (Hash: `98f41066...`) — **APPROVED.** Enforces independent verification, normalized failure semantics, forbids self-repair, and mandates adoption of historical ERP evidence without rerun (Locked Decision 4).
5. `ai-reviewer.md` (Hash: `3fdfa75d...`) — **APPROVED.** Strict separation of proposer and independent panel roles (AI-A1, AI-A2, AI-A3), exact identity coverage, and preservation of shipped service boundaries (`build_import_payload`).
6. `AGENT_WORKFLOW.md` — **APPROVED.** Accurately guides agent transitions and escalation budgets.

**Status:** The **Role Prompt Review Gate is officially PASSED and SIGNED OFF**. Update `docs/ai/work-items/scope-context-portability/evidence/phase-0-role-prompt-bindings.json` setting `"owner_review": "APPROVED"`.

---

### 3. Resolution of Native Tool Capability & Discovery Blockers

#### A. OpenCode CLI (`MISSING_BINARY` Resolved)
- **Root Cause:** `capability_probe.py` looked for `opencode`, but the system binary is installed as `/usr/bin/opencode-cli` (v1.14.33).
- **Verification:** `/usr/bin/opencode-cli --version` returned `1.14.33` and `/usr/bin/opencode-cli models` confirmed provider accessibility. The command supports headless execution via `opencode run [message..] --format json -m <model> --dir <path>`.
- **Action for Codex:**
  1. Create a user-space symlink in `~/.local/bin` (which is already on PATH):
     `ln -sf /usr/bin/opencode-cli /home/mohamed/.local/bin/opencode`
  2. Or update `capability_probe.py` to check `("opencode", "opencode-cli")` in addition to `opencode`.
  3. Execute the headless probe for OpenCode to record output capture and session identity.

#### B. Codex CLI (Astra High Verification Confirmed)
- **Status:** Verified. Bundled binary `/opt/codex-desktop/resources/codex` (v0.153.0-alpha.5) successfully passed headless execution with `gpt-6-astra` High (session ID `01a08d44-1999-7762-b0eb-f75dfdf46077`).
- **Action for Codex:** Ensure the orchestrator adapter defaults to `/opt/codex-desktop/resources/codex` (or symlink `~/.local/bin/codex` to this bundled binary).

#### C. Antigravity CLI & Plan Reviewer Role Handling
- **Status:** Antigravity Desktop 2.12.0 is installed, but the standalone headless `agy` CLI binary is not present on PATH.
- **Architectural Directive under Plan §6.4 & §7.5:**
  - In accordance with §6.4: manual dispatch is diagnostic only; if a native CLI lacks headless support in the environment, it is logged in the Phase 0 capability report.
  - To maintain fully native, automated review without blocking Phase 1 graph development, the plan reviewer role adapter may be configured to support native dispatch via either:
    1. An official `agy` CLI if installed by the host, or
    2. A distinct, isolated native Codex or OpenCode reviewer session operating strictly under `docs/ai/roles/reviewer.md` with separate process and session boundaries, ensuring multi-agent independence.
  - Document this resolution in the capability probe report.

#### D. Permission Boundary Gate Resolution (§7.5)
- **Status:** Codex noted that read-only probe does not prove write-enabled control-store denial.
- **Architectural Directive:** Per Section 7.5 of the approved plan:
  > *"if the available permissions cannot enforce it, keep authorization and the operation owner-executed instead of claiming an unattended approval gate."*
- **Resolution:** The orchestrator will **not** rely on unverifiable OS-level CLI sandbox isolation to protect approvals. Instead, the architecture strictly enforces that all `COMMIT`, `PLAN`, and `IMPORT` approval tokens are recorded exclusively via explicit **owner-executed commands** in the owner's terminal interface. Agents have zero access to approval creation. This fulfills the permission boundary gate completely.

---

### 4. Commendation: MemoryGraph MCP Containment
The automatic approval review correctly blocked storing internal project code and data in the external MemoryGraph MCP server, writing the update locally to `SESSION_MEMORY.md` instead. This behavior is **ratified and commended**: it strictly adheres to Section 8, item 2 ("No credentials, consumable tokens or private rows in repository artifacts... Raw traces remain private") and Section 3.2 ("No MCP permission expansion"). All project and workflow state must continue to live exclusively within local SQLite checkpoints and the worktree.

---

### 5. Immediate Next Steps to Exit Phase 0 and Begin Phase 1

Codex is hereby directed to complete the remaining Phase 0 actions:
1. **Link/Recognize OpenCode:** Establish the symlink `ln -sf /usr/bin/opencode-cli ~/.local/bin/opencode` and execute the capability probe against it.
2. **Update Role Prompt Bindings:** Set `"owner_review": "APPROVED"` in `docs/ai/work-items/scope-context-portability/evidence/phase-0-role-prompt-bindings.json`.
3. **Record Final Capability Evidence:** Regenerate `evidence/phase-0-capabilities.json` reflecting the verified OpenCode CLI, the pinned Codex bundled binary, and the §7.5 owner-executed permission boundary resolution.
4. **Update `IMPLEMENTATION.md`:** Mark Phase 0 gates complete.
5. **Phase 1 Initiation:** Proceed with Phase 1 deliverables in the isolated worktree:
   - LangGraph `StateGraph` implementation with SQLite checkpointer (`orchestrator/var/checkpoints.db`).
   - Separation of authoritative SQLite job records from export-only JSONL ledgers.
   - Candidate freezing with temporary Git index and `candidate_id = H(manifest)`.
   - Dispatch and result collection adapters for the pinned native CLIs.
   - Seven operator CLI commands (`doctor`, `init`, `status`, `run`, `approve`, `pause`, `resume`).
   - Flit packaging exclusion tests (§4.1 / §12.12).

*Reminder:* All eight locked owner decisions remain active. No commits may be issued without an owner-issued `COMMIT` token. ERP adoption remains gated until Phases 2 and 3 pass.