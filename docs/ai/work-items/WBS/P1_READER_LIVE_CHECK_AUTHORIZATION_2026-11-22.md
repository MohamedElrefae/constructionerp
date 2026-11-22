# P1 reader live-check — owner authorization packet

**Status: NOT AUTHORIZED. Preparation only.** Prepared 22 November 2026 after the two reconnect-claim
repair cycles. This packet asks for decisions; it performs no site action, write, or process start.
No site has been contacted since those cycles.

## Why this packet

The two repaired code paths (offline observer, live `FreshAuthorityReader`) have only offline
evidence. The live reader is access-decision code and has never run against a site. This packet is
the smallest live check that exercises the repaired reader on real data, and defines its exact scope
so the owner can approve or refuse each line. It does **not** by itself close P1: connection
provenance stays closed as unverified, and clean install/upgrade, two-worker revocation, concurrency
and commercial-preservation gates remain separate scopes.

## Verified target facts (read-only, 22 November 2026)

| Item | Value |
| --- | --- |
| Site | `wbs-p1-lab.localhost` only. Never `v16.localhost` or `localhost`. |
| Database | `_wbsce5cf13289ec` (MariaDB, from `site_config.json`) |
| Served app | `/home/mohamed/frappe-bench/apps/construction`, branch `local/app-consolidated-20261117`, HEAD `9098c0a` |
| Candidate | worktree `wbs-p1-source-bound`, HEAD `f530913`, plus the repaired files |
| Lab fixtures | 26 Projects, 29 nodes, 17 counters from prior runs (`r1/site-baseline.json`); `wbs.*@example.test` users disabled; `f21-d001-*` users enabled |
| Evidence root | `/home/mohamed/wbs-p1-evidence` (mode `0700`), index `EVIDENCE_INDEX.json` |

**Wiring fact that shapes the ask:** the lab site resolves `construction` from `apps/construction`,
not from the candidate worktree. The repaired reader is not in `apps/construction` today. A live
check therefore requires binding the candidate code to the lab first.

## Ask 1 — code binding to the lab (choose one)

| Option | Effect | Cost/risk |
| --- | --- | ---|
| **A1 (recommended)** | Overlay the candidate's 7 sealed modules + 2 doctype controllers from the worktree into `apps/construction`, after backing up the current files to the evidence root; restore them in `finally`. | The shared app serves every site on this bench, so the overlay window exposes other sites to the candidate code. Narrow window; backup/restore verified. |
| **A2** | Provision a dedicated bench rooted at the worktree with its own site. | Isolated, but creates a new bench/site and is a larger provisioning step. |

Exact A1 file set (from `CONSTRUCTION_SERVING_MODULES`):
`construction/services/execution_tree_access.py`, `execution_tree.py`, `execution_tree_rules.py`,
`construction/api/execution_tree_api.py`, `construction/setup/execution_tree_schema.py`,
`construction/construction/doctype/execution_breakdown_node/execution_breakdown_node.py`,
`construction/construction/doctype/execution_code_counter/execution_code_counter.py`.
Backup path: `/home/mohamed/wbs-p1-evidence/r4/app-overlay-backup/`. Restore verified by hash before
the run ends. `________________` (A1 / A2 / refuse)

## Ask 2 — Step 0: read-only inventory (no writes)

Before any check, inventory the exact target and record it in the evidence root: served app hashes vs
the candidate; every user's effective roles, Project membership, User Permissions and shares; the
fixture Projects/nodes/counters; native DocPerm/Custom DocPerm for Project; active scope settings.
Purpose: decide whether a meaningful **allowed** and **denied** non-admin pair already exists, or
whether minimal fixtures must be created (Ask 3). Read-only; no site mutation. `________________`

## Ask 3 — actors for the reader check (choose one)

The reader check needs a positive control first: an allowed non-admin must succeed before any denial
counts. The runbook records that `f21-d001-*` users carry no roles and `wbs.*` users are disabled, so
a probe with them would test the wrong thing.

| Option | Effect |
| --- | --- |
| **B1** | Use an existing enabled non-admin pair if Ask 2 proves one is meaningful. No writes. |
| **B2** | Create minimal new synthetic actors + one fixture Project/Company, exact names in a private manifest, random passwords never logged, `send_welcome_email=0`; disable referenced users in cleanup. Site writes, new records. |

`________________` (B1 / B2 / refuse). If B2: approve the exact names and the Company/Project creation
explicitly. Fixture writes are new, inventoried records only; never adopt or alter existing users.

## Ask 4 — the reader check itself (Mode I, in-process)

Run on `wbs-p1-lab.localhost` only, as a bounded script under `bench --site wbs-p1-lab.localhost`,
calling `construction.services.execution_tree_access.authorize(project, operation)` with
`frappe.set_user(<actor>)`. No HTTP route, no transport.

| Check | Actor | Operation | Pass condition |
| --- | --- | --- | --- |
| K1 | allowed non-admin | `read` | decision `allowed=True` with expected reason; no writes; connection rolled back and closed |
| K2 | second allowed non-admin (if any) | `read` | permitted read |
| K3 | denied non-admin | `read` | `AccessDenied`; no Project metadata/nodes disclosed; no writes |
| K4 | Administrator | `read` | allowed (proves the repaired seal/transaction path live) |
| K5 | any | — | reader transaction is `REPEATABLE-READ`, `tx_read_only=1`; every queried table InnoDB; snapshot rolled back and connection closed |

The script records only sanitized outcomes (actor class, operation, decision/reason, rollback/close
booleans), never rows, credentials or response bodies. Evidence under the evidence root, hashed into
the index. `________________`

## Ask 5 — optional observer snapshot (separate sensitive scope)

The limited observer (`docs/ai/work-items/WBS/tools/b2_limited_observer.py`) can capture the
persisted state around K3/K5 for denial/preservation evidence. Its payload is raw private business
data (all rows of five BOQ tables + all protected `DocShare` rows). Both broad flags must be true to
run. This is a distinct sensitive-data authorization; it is **not** required for the reader check.
`________________` (approve exact scope / refuse / defer)

## Cleanup and stop conditions

- Restore the app overlay (A1) and verify hashes; remove ephemeral credentials/sessions in `finally`.
- B2 fixtures: disable referenced users; delete only exact allowlisted objects after independent
  ownership/dependency checks; never touch pre-existing records; retain issued-code Projects/counters
  as inert evidence by default.
- Stop and report if: the target/DB identity differs; a served hash differs from the candidate; a
  positive control fails (all denials then inconclusive); any write occurs outside the named site; a
  denial discloses another Project's data; cleanup cannot be independently verified.

## What this proves / does not prove

**Proves:** the repaired reader works live for allowed and denied non-admin actors on the lab, is
read-only, and cleans up; the candidate code binding is sound. **Does not prove:** connection
provenance (closed as unverified), HTTP route/transport behavior, two-worker revocation, concurrency,
clean install/upgrade, or commercial-data preservation. Those remain open P1 gates.

## Sign-off

| Role | Name | Decision | Date |
| --- | --- | --- | --- |
| Owner | Mohamed Elrefae | | |
