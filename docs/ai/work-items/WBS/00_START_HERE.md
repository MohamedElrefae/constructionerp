# WBS Planning Packet — Start Here
Date: 2026-10-27
Owner: Mohamed Elrefae
Repository: MohamedElrefae/constructionerp
Historical baseline: a19bf8efec0b32c2bc71454aaddf42f6583c69e3 (develop when checked)
Status: REMOTE DRAFT FOR LOCAL RECONCILIATION. Not an approved implementation PLAN or execution grant.

## Purpose
Give a local architect enough direction to verify the actual checkout and produce bounded executable plans, without re-opening settled business scope or building progressive billing.

## Authority order
Higher-priority platform instructions and explicit current owner instructions; applicable repository governance/contracts; locally verified source and installed metadata; this packet and v3 handovers as reference. Stop and report material conflicts. Do not invent a grant or workflow state.

## Read order
1. Actual repository governance: AGENTS.md, PROFESSIONAL_ENGINEERING_STANDARD.md, CONTEXT_INDEX.md, root AGENT_WORKFLOW.md, relevant SESSION_MEMORY.md/ADRs/work-item state.
2. Supplied Business and Technical Handover v3. These are separate earlier deliverables, NOT included in this ZIP. Ask owner for them if unavailable; never claim reading missing files.
3. 01_MASTER_SCOPE.md
4. 02_DECISIONS.md
5. 03_LOCAL_ARCHITECT_INSTRUCTIONS.md
6. 04_WORK_PACKAGES.md
7. 05_VERIFICATION_MATRIX.csv
8. 06_STATUS_AND_EVIDENCE_TEMPLATE.md
9. 07_OWNER_REVIEW_CHECKLIST.md

## First permitted task requested by this packet
Read/inspect and propose. Run repository-mandated non-mutating startup checks subject to local authority. Inspect environment configuration without exposing secrets. Produce a local reconciliation report and proposed plans. Do not edit app source, initialize an orchestrator work item, install/update dependencies, migrate, run database-writing native tests, commit/push/publish/deploy unless separately authorized.

## First return to owner
Actual checkout/branch/HEAD/status; check results; files read; relevant changes from historical baseline; orchestrator readiness; named disposable test route (or missing target); decisions D01–D10; exact proposed scopes/commands; blockers. Gate: READY FOR OWNER PLAN REVIEW or BLOCKED, with reasons. Neither label grants implementation.

## Scope in one sentence
A separate project execution tree linked optionally to existing BOQ Item Stages, with controlled mapping and a permission-aware mapping coverage report; preserve existing commercial structure, quantities and history.

## Stop conditions
Unexpected unrelated edits, governance conflict, unknown site, unsafe validation command, scope expansion, source/baseline changes invalidating evidence, required business rule unresolved, or uncertainty over an already-running job. Preserve work and report; no automatic reset/retry/bypass.
