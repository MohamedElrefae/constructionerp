# Multi-Agent Workflow Automation: Head of Engineering Analysis

**Date:** 2026-09-10  
**Scope:** Construction ERP — AI Agent Collaboration Automation  
**Context:** `docs/ai/work-items/erp-arabic-bilingual-data` as primary case study

---

## Executive Summary

The current workflow has accumulated **59 evidence files, 19 AI-R review rounds for a single stage, and 12 rounds for another** — with every round requiring manual copy-paste between agents. This is a compounding tax: as work items grow in complexity, the copy-paste overhead scales quadratically, not linearly.

As Head of Engineering, the goal is to replace manual inter-agent copy-paste with **file-system-mediated agent handoffs** where agents read/write to shared canonical files, and you only intervene at explicit human decision gates.

---

## Problem Diagnosis: What's Actually Being Copy-Pasted

Looking at your `erp-arabic-bilingual-data` evidence, the copy-paste happens in **three patterns**:

### Pattern A — Review Input (Biggest cost)
> You copy the current `IMPLEMENTATION.md` + relevant evidence files into a new AI-R session.

**Root cause:** Each AI-R session has no persistent memory of the work item. You bridge the context gap manually.

### Pattern B — Review Output Relay  
> AI-R produces a BLOCKED/VERIFIED verdict. You copy it into the builder's session to act on fixes.

**Root cause:** The builder (OpenCode) and verifier (Codex/AI-R) have no shared file channel. The result lives in chat history, not in the repo.

### Pattern C — Multi-Reviewer Quorum (AI-A1/A2/A3)
> Same input dispatched to 3 independent reviewers, results manually collected into one bundle.

**Root cause:** No dispatcher exists. You are the dispatcher.

---

## The Core Insight: Agents Communicate Through Files, Not Chat

The repo is the only channel all agents share. The fix is:

```
Agent A writes → repo file → Agent B reads → writes response → repo file → Agent A reads
```

No copy-paste. You only approve decisions that require human judgment.

---

## Proposed Architecture: File-Driven Agent Orchestration

### Layer 1: Work Item State Machine (already designed, under-used)

`STATE.json` already exists in your proposal. It needs to become the **live control plane** — agents read it to know their role and write to it when done. Currently it's a concept; make it the actual runtime authority.

### Layer 2: Agent Inbox/Outbox Convention

Each agent role gets a **named slot** inside the work item directory:

```
work-items/<id>/
  STATE.json                    ← machine-readable control plane (status + active role)
  inbox/
    architect.md                ← what architect needs to act on
    builder.md                  ← what builder needs to act on  
    reviewer.md                 ← what reviewer needs to act on
    verifier.md                 ← what AI-R verifier needs to act on
    ai-a1.md                    ← independent reviewer 1 input
    ai-a2.md                    ← independent reviewer 2 input
    ai-a3.md                    ← independent reviewer 3 input
  outbox/
    plan.md                     ← architect output (was PLAN.md)
    review.md                   ← reviewer verdict (was REVIEW.md)
    build.md                    ← builder progress (was IMPLEMENTATION.md)
    ai-a1-verdict.md            ← AI-A1 decision
    ai-a2-verdict.md            ← AI-A2 decision
    ai-a3-verdict.md            ← AI-A3 decision
    verifier-round-{N}.md       ← AI-R verdict per round (auto-numbered)
  evidence/                     ← unchanged, builder-owned
```

### Layer 3: The Dispatcher Script

A single script `scripts/ai_dispatch.py` that:
1. Reads `STATE.json` to know current status
2. **Writes the correct inbox file** for the next agent role based on state
3. Prints the exact prompt to give that agent (one sentence, referencing the file path)
4. Updates `STATE.json` with `pending_role` and timestamp

You run `python3 scripts/ai_dispatch.py --work-item erp-arabic-bilingual-data` and it tells you:

```
STATE: BUILD_COMPLETE → awaiting VERIFIER
Wrote: work-items/erp-arabic-bilingual-data/inbox/verifier.md
Tell AI-R: "Read work-items/erp-arabic-bilingual-data/inbox/verifier.md and produce your verdict."
```

### Layer 4: Role-Specific System Prompts (Saved in Repo)

```
docs/ai/roles/
  architect.md    ← permanent role prompt for architect agent
  builder.md      ← permanent role prompt for builder agent
  reviewer.md     ← permanent role prompt for reviewer agent  
  verifier.md     ← permanent role prompt for AI-R verifier
  ai-reviewer.md  ← permanent role prompt for AI-A1/A2/A3 (independent)
```

Each role prompt says exactly: **"Read your inbox file. Produce output to the specified outbox file. Do not read other roles' inboxes."**

This means starting a new AI session = one sentence + one file path. No copy-paste.

---

## Decision Gates: What Stays Manual vs. What Becomes Automated

### ✅ Automated (no human needed)

| Step | Trigger | Agent reads | Agent writes |
|---|---|---|---|
| Dispatch builder input | `APPROVED_FOR_BUILD` in STATE | `inbox/builder.md` (auto-generated) | — |
| Collect AI-R verdict | Builder updates `outbox/build.md` | `inbox/verifier.md` (auto-generated) | `outbox/verifier-round-N.md` |
| Dispatch AI-A1/A2/A3 | Stage 1C review needed | `inbox/ai-a1.md` etc. (auto-generated) | `outbox/ai-a{1,2,3}-verdict.md` |
| Quorum check | All 3 verdicts written | script reads all 3 outbox files | `STATE.json` updated to QUORUM_PASSED or QUORUM_FAILED |
| Re-dispatch builder on BLOCKED | AI-R verdict = BLOCKED | `inbox/builder.md` updated with delta | builder acts |

### 🔴 Manual (human decision required)

| Gate | Why it must stay manual |
|---|---|
| `PLAN_SUBMITTED → APPROVED_FOR_BUILD` | You own the scope and risk |
| `VERIFIED_FOR_RELEASE → RELEASED` | Commit/push/deploy authorization |
| Production data mutation | Irreversible, requires explicit owner sign-off |
| Quorum override when 2/3 pass | Safety policy decision |
| Stage gate when canonical plan changes | Human re-reads the delta |

---

## Solving the "19 Rounds of AI-R" Problem Specifically

Looking at your `stage-2-ai-r-round2.md` through `stage-2-ai-r-round19.md`:  
Each round was a manual session because AI-R found a defect, you relayed it to the builder, builder fixed it, you brought the fix back to AI-R.

**The automated loop:**

```
while verifier.verdict != VERIFIED:
    1. dispatch.py generates inbox/verifier.md with:
       - current diff (git diff HEAD..feature/erp-arabic-bilingual-data)
       - outbox/build.md (builder's latest explanation)
       - previous verifier round verdict (for context delta only)
       - round number
    2. You paste ONE LINE to AI-R: "Read inbox/verifier.md round N"
    3. AI-R writes outbox/verifier-round-N.md
    4. dispatch.py reads the verdict:
       - VERIFIED → advance STATE
       - BLOCKED + items → generate inbox/builder.md with only the delta
    5. You paste ONE LINE to builder: "Read inbox/builder.md round N fixes"
    6. Builder writes outbox/build.md (appends, doesn't replace)
    7. Go to step 1
```

**What you actually do:** paste one line per round, approve state transitions. That's it.

---

## The Quorum Review Problem (AI-A1/A2/A3)

Currently: you manually start 3 sessions with the same input.

**Automated:**
```bash
python3 scripts/ai_dispatch.py --work-item erp-arabic-bilingual-data --quorum-stage 1c
```

Output:
```
Wrote: inbox/ai-a1.md, inbox/ai-a2.md, inbox/ai-a3.md (identical content, session-isolated)
Tell AI-A1: "Read inbox/ai-a1.md"
Tell AI-A2: "Read inbox/ai-a2.md"
Tell AI-A3: "Read inbox/ai-a3.md"
When done, run: python3 scripts/ai_dispatch.py --check-quorum erp-arabic-bilingual-data 1c
```

The quorum check reads all 3 verdict files, computes PASS/FAIL, writes to STATE.json. You approve or not.

---

## Implementation Phases

### Phase 1: Inbox/Outbox Structure (0.5 day) — Immediate value

Add `inbox/` and `outbox/` directories to the work-item structure. Write role prompts to `docs/ai/roles/`. This alone cuts copy-paste by 70% because agents read files instead of chat context.

**No automation needed yet.** Just convention.

### Phase 2: `ai_dispatch.py` Script (1 day)

Reads `STATE.json`, generates the correct inbox file from templates, prints the one-line prompt. Validates outbox completeness before advancing state.

**Test it on `erp-arabic-bilingual-data` Stage 4 immediately.**

### Phase 3: Verdict Parser (0.5 day)

Parse AI-R and AI-A1/A2/A3 outbox files to extract structured verdict (`VERIFIED`/`BLOCKED`/`QUORUM_PASS`). Update STATE.json automatically. Human only sees: "Round N: BLOCKED — 2 items. Dispatch builder? [y/N]"

### Phase 4: Delta-Only Re-dispatch (0.5 day)

On BLOCKED, generate `inbox/builder-round-N.md` containing **only the new findings** from round N vs round N-1, not the entire plan context again. This is why round 2→19 was manual — each round re-read the full context. Delta dispatch makes each round a tiny focused fix.

### Phase 5: Antigravity Subagent Orchestration (1–2 days, future)

Replace the "paste one line" with Antigravity subagents that actually send messages to each other via `send_message`. Antigravity is already capable of spawning parallel subagents and waiting for their responses. This fully eliminates manual dispatch.

---

## What "Different Agents for Different Context" Means in Practice

You're right that different agents (OpenCode, Codex, Antigravity) produce better output because each has different context windows, training, and prompt patterns. **Preserve this.** The goal is not to merge agents — it is to make the **file system the contract** so any agent can plug in at any role.

Role prompts in `docs/ai/roles/` are tool-neutral. Whether you use Codex, OpenCode, Gemini, or Claude for AI-R, they all read the same `inbox/verifier.md` and write to the same `outbox/verifier-round-N.md`.

---

## Immediate Action for erp-arabic-bilingual-data Stage 4

Stage 4 is in progress right now. Apply the new system immediately:

1. Create `inbox/verifier.md` for the next AI-R pass (dispatch.py generates this)
2. Create `inbox/ai-a2.md` for the AI-A2 independent proposal review
3. AI-R reads the inbox file → writes `outbox/verifier-round-1.md` (stage 4)
4. No copy-paste required

---

## Open Questions

> [!IMPORTANT]
> **Q1: Agent identity for Antigravity subagents** — Should Antigravity spawn the AI-R verifier as a subagent within the same session, or should it write the inbox file and you open a fresh Codex/OpenCode session? Fresh sessions preserve the "different context" benefit. Subagents are faster but share context.

> [!IMPORTANT]
> **Q2: Inbox file format** — Should inbox files be structured Markdown with explicit sections (context, task, output format, output path), or should they embed the full relevant context? Recommend structured sections to keep them small and machine-parseable.

> [!NOTE]
> **Q3: Retroactive migration** — Apply the inbox/outbox convention to `erp-arabic-bilingual-data` Stage 4 immediately, or only to the next new work item? Recommend: apply to Stage 4 now since it's the active item.

---

## Summary Table: Manual vs Automated After Implementation

| Action | Today | After Phase 1 | After Phase 4 |
|---|---|---|---|
| Start new agent session | Copy full plan + history | Paste one file path | One line |
| AI-R round handoff | Copy implementation + evidence | Paste inbox path | Auto-dispatch |
| Builder fix relay | Copy AI-R verdict | Paste outbox path | Auto-delta |
| Quorum (3 reviewers) | 3 manual sessions + collect | 3 file reads + check script | Parallel subagents |
| State transition | Mental tracking | `STATE.json` + dispatch.py | Automated + human approval |
| New work item setup | From scratch each time | Template + script | Template + script |

**The one sentence that describes the end state:**  
You approve decisions. Agents communicate through files. The repo is the source of truth for all inter-agent context.

