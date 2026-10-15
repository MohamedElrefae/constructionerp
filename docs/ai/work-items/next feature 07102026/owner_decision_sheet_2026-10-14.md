# Owner decision sheet — foundation program (2026-10-14)

Four decisions block F42, F41, F27 and customer delivery. Owner decisions recorded 2026-10-14 below. No commit or publication is implied; publication and customer delivery require separate approval.

## D1 — F42: customer and workload assumptions

**Background.** No productivity baseline exists. F37 workload qualification and any
customer-facing performance statement need an owner-defined realistic dataset first.

**Decision: APPROVED 2026-10-14** as the initial Egypt-SME reference test baseline (not a capacity promise). Concurrent users and operation volumes to be recorded before F37. **Recommendation (approved):** a minimal workload profile — 1 company, 2 projects, one BOQ of
~200 items with structures, ~50 analyses, 5 VOs, 6 months of purchase history — as the
reference dataset for F37 and F31 volume checks.

**Consequences.**
- *Approve:* F37 can run on the DBA-provisioned sites; performance statements stay scoped
  to this profile (no blanket scale claims).
- *Defer:* F37 stays blocked; F31 proceeds functionally with no volume evidence.

### Reference workload profile (D1, Egypt-SME initial baseline)

| Dimension | Value |
|---|---|
| Companies / projects | 1 company, 2 projects |
| BOQ | ~200 items with structures, one header |
| Cost data | ~50 analyses, 5 variation orders |
| Purchase history | 6 months |
| Concurrent users | **to record before F37** (nominal: PM + buyer + engineer sessions) |
| Operation volumes | **to record before F37** (imports/hour, transactions/hour, report runs/hour) |

Status: test baseline only — not a capacity promise, not a scale claim.

## D2 — F41: handover walkthrough

**Background.** Maintainer guide, runbook (§0.3–0.6) and override inventory are written.
The walkthrough itself needs qualified sites.

**Decision: APPROVED 2026-10-14** — walkthrough after F31/F32. **Scope (approved):** on the rehearsal
site, covering: scope-context administration, permission-reconciliation reruns, backup and
restore rehearsal, and the report-audience grant procedure.

**Consequences.**
- *Approve:* F41 closes with operator sign-off; production readiness gains a trained operator.
- *Defer:* handover stays document-only; production decisions wait regardless.

## D3 — F27: bridge audience and authorization

**Background.** The MCP bridge (`erpnext-mcp-server/`) runs Administrator-backed by
DocType allowlist with no per-user permission or scope check. Retrieval is fixed and
verified (3/3 rows); authorization is not qualified.

**Decision: APPROVED 2026-10-14** — bridge restricted to authorized operators; customer access prohibited until per-user authorization is qualified. **Standing rule:** Qualify it later under
full F27 with a per-user authorization boundary (session-user passthrough + scope check),
or restrict it permanently to operator tooling.

**Consequences.**
- *Restrict to operators:* no customer exposure; AI-assisted reads stay an internal tool.
- *Qualify for customers:* requires the authorization build + matrix evidence first; do not
  expose the current Administrator-backed endpoint to customer users under any timeline
  pressure.

## D4 — Curated delivery route (F28-D003)

**Background.** `bench get-app` ships the whole checkout, including `docs/ai/` program
evidence that must not reach customers. A curated set is defined (`docs/DISTRIBUTION.md`)
and mechanically verified (1,243 files, never-ship absent, links resolve), but the route
itself is undecided.

**Decision: APPROVED 2026-10-14** — prepare a curated Git delivery route, subject to verification. **Constraint (approved, corrected):** the customer candidate lives in a **separate clean repository**, not an orphan branch of this one — an orphan branch does not isolate the repo's other branches, tags or private history. Verify every included file and every reachable ref before any publication. No repository history changes or publication are authorized now. **Method (prepared, not published):** fresh `git init`, copy of the customer set only, single squashed commit, no remotes; verification = exactly one reachable commit, `git log --all` clean of never-ship paths, file-by-file hash match against the staged manifest.

**Consequences.**
- *Approve:* delivery becomes reviewable and re-verifiable on every change; internal
  evidence stays in history but out of customer hands only if the gate runs on every merge.
- *Defer:* no customer artifact exists; F31 final `get-app` qualification cannot run.
