# P1 scoped-closure proposal — consolidated closeout, 22 November 2026

P1 continuation cycle result + one proposal to declare **scoped P1 closure** and unblock P2
(BOQ Item Stage → execution-location mapping). Prepared as a proposal; performs no actions.

## Cycle result (Builder + independent Tester) — Ask 4

The repaired reader (`construction/services/execution_tree_access.py` + test) was run live on
`wbs-p1-lab.localhost` (Mode I, in-process, real DB, real permission code). Evidence:
`/home/mohamed/wbs-p1-evidence/r4/reader-check.json`.

| Check | Actor | Outcome |
| --- | --- | --- |
| K1 | `wbs-p1-r4-allow@example.test` (Project Manager + Projects Manager, scope: WBS-P1-R4-CO) | **allowed** (reason: allowed); scope {company: WBS-P1-R4-CO}; reader connection rolled back + closed |
| K4 | Administrator | **allowed** (reason: administrator); rolled back + closed |
| K3 | `wbs-p1-r4-deny@example.test` (Site Engineer, no Projects User) | **denied** ("Not permitted."); rolled back + closed |

K1 (positive control) precedes K3 per the runbook. Preservation: Project/node/counter counts
unchanged before/after (27/29/17). All three reader connections verified rolled back and closed.
**PASS.**

Run-scoped records (pre-approved names, all new/inert, users disabled in cleanup): Company
`WBS-P1-R4-CO`, Project `WBS-P1-R4-PROJ`, users `wbs-p1-r4-allow@example.test` /
`wbs-p1-r4-deny@example.test`, User Scope Context for the allow user. Candidate code was applied
to `apps/construction` for the run only; **restored and SHA-256-verified against the original**
(manifest: `/home/mohamed/wbs-p1-evidence/r4/overlay-manifest.json`).

## Consolidated closeout proposal (minimum to declare scoped P1 closure)

| Gate | Proposal | Status |
| --- | --- | --- |
| **R6 — freeze candidate** | Freeze the P1 candidate so P2 branches from something reproducible. The reader check ran on the worktree state at HEAD `f530913` (overlay applied to `apps/construction`). Propose: create a freeze branch/tag `wbs-p1-r4-freeze` in the worktree and record a per-file SHA-256 manifest of the P1-scope files (the reconnect fixes, the two report docs, the runbook evidence). **Owner decision: commit shape (branch/tag), exact frozen ID.** | Proposed |
| **R1 — authorization, denial, preservation** | Minimally covered by the cycle above: positive control allowed, outsider denied at the decision, no Project metadata disclosed, connection rolled back + closed, state preserved. **Covered (K1/K3/K4 + preservation).** Note: not HTTP-transport (see R2). | Closed (reader-level) |
| **R2 — two-worker revocation** | Propose a small follow-up script: warm an allowed read on gunicorn worker :8801, commit a revocation through :8802, confirm the new read denies on :8801 and the mutation is blocked. Two identified gunicorn instances. | Proposed / defer |
| **R3 — concurrency & allocation** | Defer as pre-release gate. The counter is exercised only on creation; a controlled two-connection allocation overlap was not run. | Deferred |
| **R7 — SCP-015 provenance** | Formally record SCP-015 as **accepted-unverified** under this scoped P1 closure (owner's standing decision: no provenance adapter, no PROCESS grant, no marker hook; `_require_verified_runtime()` still raises). Not a passing test; a pre-release gate. | Closed (accepted-unverified) |
| **R4 — EN/AR, RTL, keyboard** | The owner tested the tree UI flow. Propose recording the observed conditions (site, browser, EN/AR loaded, RTL rendering, keyboard behavior) as the R4 journey record; full native accept still needs the owner's fresh journey run. | Proposed / defer |
| **R5 — clean install/upgrade** | Defer as pre-release gate. No clean target has been nominated; the bench is not a clean-install target. R5 does not require the clean host for upgrades, but a clean install does. | Deferred |

## Decision needed (owner)

To declare **scoped P1 closure and unblock P2**:
1. **R6 freeze shape** — branch/tag name + commit or tag + manifest (default: `wbs-p1-r4-freeze` branch on the worktree, per-file SHA-256 manifest).
2. **R2** — run the two-worker revocation script, or defer to the pre-release gate?
3. **R4** — record the owner's observed UI journey now, or defer?
4. **R5** — clarify: is a clean install still required for this milestone, or is a clean **upgrade** of the lab bench sufficient as a non-clean-install check?

No further site actions occur until the owner authorizes the R2 script or R4/R5 runs.
