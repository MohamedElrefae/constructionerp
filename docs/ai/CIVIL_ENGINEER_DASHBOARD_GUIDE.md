# Civil Engineer Dashboard — End-to-End User Guide

**Audience:** civil engineers and project owners who need to inspect, govern, and approve AI-assisted repository work without operating the orchestration CLI.

**Release:** Week 3 dashboard, commit `737365a`.

## 1. What the dashboard does

The dashboard is a local control room for AI-supported engineering work. It lets you:

- register an existing initialized worktree and monitor its workflow state;
- create a new isolated work item from an owner brief;
- inspect the plan, review snapshot, scope, AI context, findings, evidence, Git diff, and audit exports;
- adopt a reviewed scope and grant a PLAN approval only after the displayed bindings are verified;
- view the parked Stage 4 ERP export-manifest projection.

It does **not** run builders, reviewers, verifiers, or ERP imports from the dashboard. It has no pause, resume, reset-budget, role-reconfiguration, commit, push, deployment, or ERP-data-write control. A PLAN approval records authority for the orchestrator; it does not itself dispatch an agent.

> **Stage 4 rule:** `erp-arabic-bilingual-data` is parked. The dashboard may display its sanitized manifest status, but it will reject bootstrap, scope adoption, review creation, and plan approval for that work item.

## 2. Start the dashboard safely

Run these commands from the dashboard worktree:

```bash
cd /home/mohamed/frappe-bench/worktrees/scope-context-portability
dashboard/.venv/bin/python -m dashboard.app
```

The default address is `http://127.0.0.1:8080` (or the local address printed by Uvicorn). Keep the service bound to loopback. Do not expose it through a public interface, reverse proxy, or tunnel without a separate reviewed deployment design.

On first start, the system writes one temporary credential file:

```text
dashboard/var/initial_credentials.txt
```

It is mode `0600`. Sign in with the displayed `engineer` account and immediately create a permanent password. The temporary credential file is removed after successful password setup. Do not copy its password into tickets, prompts, logs, commits, or chat.

## 3. Daily operating flow

### Step 1 — Sign in and orient yourself

1. Open the local dashboard URL.
2. Sign in. If prompted, set the permanent password.
3. Read the task list. Select a task and check its workflow **status**, **stage**, **gate**, active jobs, and last poll time.
4. Open **AI Context & Memory** before making a decision. It exposes the current task's copies of `AGENTS.md`, `SESSION_MEMORY.md`, schema facts, coding patterns, and their provenance.

Treat a missing or stale context file as a decision blocker until it is resolved in the repository. Do not guess a convention from memory.

### Step 2 — Register an existing task

Use **Register Existing Worktree** when a worktree already has a valid, initialized orchestration database.

1. Paste the absolute path of the intended worktree.
2. Confirm the displayed work-item name and branch.
3. Register it.

Registration validates containment, worktree identity, and checkpoint database availability. It does not create a branch, modify the worktree, or start agents. If registration fails, correct the path or task initialization outside the dashboard; do not bypass path validation.

### Step 3 — Bootstrap a new task (when authorized)

Use **Bootstrap Task** only for a genuinely new, approved work item.

1. Choose a unique lowercase work-item name.
2. Write a concise owner brief: engineering outcome, constraints, accepted deliverables, and required validation.
3. Confirm the selected base reference.
4. Submit once and retain the resulting task ID.

Bootstrap is recoverable and idempotent, but it intentionally refuses to overwrite an existing worktree, branch, or `owner-brief.md`. If it reports reconciliation required, stop and ask the technical maintainer to inspect the recorded action rather than retrying with a new name.

### Step 4 — Inspect before approval

For a selected task, review these screens in this order:

| Screen | What to decide |
|---|---|
| **State** | Is the task at the expected stage and gate? Are active jobs empty before a PLAN decision? |
| **Plan & Approval** | Does the plan satisfy the owner brief? Are `gate_id`, plan revision, scope, and roles hashes the ones you intend to approve? |
| **Review context** | Is the review snapshot fresh and attached to the current plan and scope? |
| **AI Context & Memory** | Do repository conventions and current sprint notes support the proposed work? |
| **Findings & backlog** | Are any blocking or high-severity findings unresolved? |
| **Evidence** | Do the submitted artifacts and tests support the claim? |
| **Diff** | Does the proposed change remain inside the authorized work scope? |
| **Settings** | Are the role identities, model pins, and timeouts expected? |

Evidence files are intentionally restricted to safe text formats (`.json`, `.md`, `.txt`, `.xml`, `.patch`, `.csv`), are size-limited, and can be unavailable when filesystem permissions are unsafe. A `403 evidence unavailable: unsafe permissions` response is a safety stop—not an instruction to change permissions from the dashboard.

### Step 5 — Adopt scope or approve a plan

These are governed actions, not routine buttons.

**Adopt Scope** only when the scope proposal is complete, minimal, and tied to the approved engineering outcome. Confirm that candidate write paths exclude unrelated ERP files and private data.

**Approve Plan** only when all displayed bindings match your reviewed snapshot:

- pending PLAN gate ID;
- work-item and review ID;
- plan revision hash;
- scope hash;
- role configuration hash;
- no active jobs;
- `plan_granted` is still false.

The dashboard revalidates these values under the orchestrator execution lock. A conflict or stale-snapshot error means the decision was not applied; reload, review the new state, and obtain a fresh owner decision. Never try to reuse an old approval token.

### Step 6 — Export evidence for a review record

Use the export controls to download:

- **State JSON** — current projection;
- **Reviews JSON** — review history;
- **Audit JSONL** — sanitized workflow events and a final metadata record.

Audit exports are capped at 1,000 events and 512 KiB, redact credentials and host paths, and include truncation headers/metadata. If truncated, retain the export as partial evidence and ask a maintainer for an authoritative database review; do not treat it as a complete audit trail.

## 4. Reading common states

| Display | Meaning | Owner action |
|---|---|---|
| `DRAFT / PROPOSAL_PENDING` with PLAN gate | Plan awaits an explicit owner decision. | Inspect; approve only if bindings match. |
| Active jobs present | An orchestrator job is running or reconciling. | Wait; do not issue a competing governed action. |
| `PAUSED` | A recorded blocker needs an owner or technical decision. | Read the categorized reason and findings. |
| `403` for evidence | Unsafe path, ownership, or permission condition. | Stop and request authorized host maintenance. |
| `409 Conflict` | Stale review, duplicate action, or another executor owns recovery. | Reload and reconcile; do not repeat blindly. |
| Stage 4 `PARKED` / `unverified_permissions` | Read-only manifest is visible but its filesystem permissions are not trusted. | Do not mutate Stage 4; raise an infrastructure follow-up. |

## 5. Practical safety checklist

Before any governed action, confirm:

- The correct worktree and work item are selected.
- The displayed plan and scope are the versions you reviewed.
- No active job or recovery action exists.
- No blocker is being silently waived.
- The dashboard is local and the browser session is private.
- You understand that approval is authority to proceed in the orchestration lifecycle, not evidence that ERP data is correct.

At session end, export the needed records, log the engineering decision in the project process, and log out. The dashboard's session cookie expires after one hour.

## 6. Troubleshooting and escalation

| Problem | Safe response |
|---|---|
| Cannot log in | Check the local service is running; on first run use the temporary credential file once, then set a permanent password. |
| Task is missing | Register its existing initialized worktree; do not create a duplicate task for the same workflow. |
| Bootstrap/review/approval returns `409` | Another attempt may own the action or state changed. Reload and ask for reconciliation if it persists. |
| Diff/evidence request times out | Preserve the error and ask the technical maintainer. Do not disable limits. |
| Stage 4 status looks concerning | It is intentionally inspection-only. Record the concern; do not use the dashboard to repair, import, or dispatch Stage 4 work. |

For technical escalation, use [AI Agent Continuation Report](AI_AGENT_CONTINUATION_REPORT.md). The broader command-line workflow and authority model are documented in [Orchestration System Manual](ORCHESTRATION_SYSTEM_MANUAL.md).
