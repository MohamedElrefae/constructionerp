# F01 — Kickoff decision request (owner action needed to unblock F02 and the environment-dependent packages)

**Date:** 12 October 2026
**Decision owner:** Mohamed (GM / product owner)
**Prepared by:** Engineering (F01 execution)
**Program:** [Foundation master plan](construction_foundation_remediation_master_plan_2026-10-12.md) · [Work register](construction_foundation_work_register_2026-10-12.md) · [Gap ledger](construction_foundation_gap_ledger_2026-10-12.md)

The plan's week-1 rule requires named responsibility and a named UAT target; without them, F02 and every site-dependent package (F04–F15, F16–F23 qualification, F31+) cannot start. F01's source-level work is complete (gap ledger, K-01/UAT-D005 reproductions, F03/F24/F25/F28/F29 source reviews); this document requests the four appointments and the site choice, with the facts needed to decide in one pass.

## 0. Decision record — 2026-10-12 (all four items confirmed)

| Item | Decision |
|---|---|
| Engineering lead | **Mohamed** |
| Finance/QS reviewer | **Mohamed** |
| Environment operator | **Mohamed** |
| Isolated UAT site / URL | **v16rehearsal.localhost** (existing site on this bench; owner-selected) |

One person holds all three roles. Per plan §3, self-review is permitted for engineering delivery but must not be labeled independent human review; consequential finance/security/data changes seek proportionate qualified review where available. F01 is recorded Engineering verified in the register; F02 (isolation validation, baseline backup, restore test) and F13 (runtime alignment) proceed next.

## 1. Decisions requested (four names + one site)

| # | Decision | Options / guidance | Blocks |
|---|---|---|---|
| 1 | **Engineering lead** — accountable for implementation, technical review and candidate evidence | Must be a named person. If the same solo engineer holds several roles, say so explicitly: self-review is allowed for engineering delivery but must **not** be labeled independent human review (plan §3). | F02–F45 sequencing |
| 2 | **Finance/QS reviewer** — reviews accounting/commercial examples, factor/pricing/cancellation worked examples | Required to close F04 fixtures and F07's no-double-margin evidence; Finance/QS sign-off is a Gate 3 condition. | F04, F05–F10, F44 |
| 3 | **Operator** — owns environment, backups, recovery rehearsal, monitoring | Required for F02 target preparation, F32/F33 recovery and monitoring evidence. | F02, F31–F33 |
| 4 | **Isolated UAT site / URL** | See §2 options and constraints. | F02, F03 site reconciliation, F04, F11, F16+ |

**Requested decision date:** within this week (plan week-1 rule). If any appointment or the site cannot be confirmed, record the blocker, decision owner and next decision date — do not leave fields "To assign" (per plan F01 completion rule).

## 2. UAT target — observed facts and options

Sites currently present on this bench (from local inspection, read-only): `localhost`, `v16.localhost`, `v16rehearsal.localhost`, `v16rehearsal.localhost_rej`, `v16rehearsalpublic`. **All share this bench's app checkout** (`/home/mohamed/frappe-bench/apps/construction`). The correction ledger (STATUS.md, 2026-10-05) records that these three original sites were raised for backup/migration authorization and that **no answer means no authority** — this request does not assume that authority, and no site was contacted or changed.

| Option | Description | Trade-offs |
|---|---|---|
| **A — new site on this bench** | `bench new-site <name>.localhost` on the current checkout, its own database | Fast. Database isolated; **app code is shared** — acceptable only if treated as disposable and never upgraded implicitly (F02 rule). Workable for Gate 1 testing while code stays frozen at `c9e6803c`. |
| **B — new site on a separate bench** | Fresh bench (own apps copy), site on it | Strongest isolation; honest upgrade/rollback and DDL-patch replay evidence (G12/F31); more setup time and disk. |
| **C — reuse an existing site** | localhost / v16.localhost / v16rehearsal.localhost after explicit backup + authorization | Rejected by default: their old schemas were flagged as unsafe to integrate with release source without coordinated upgrades; would also mix test remnants with this program's fixtures unless the owner re-confirms the recorded classification (184 orphan revisions / 25 test VOs). |

Recommendation for discussion at kickoff: **A for immediate F02/F03/F04 progress, B before any install/upgrade/migration qualification (F31/F32)** — the final choice belongs to the operator and owner.

## 3. What happens after the decision

1. **F02** (operator): baseline backup + tested restore on the chosen target; sandbox outbound integrations; record versions — no shared-site upgrade occurs implicitly.
2. **F03 close-out**: installed metadata/effective-permission reconciliation against the source inventory, then F03 completes on the named candidate/site.
3. **F04** (Finance/QS + engineering): ordinary-role matrix and versioned financial fixtures on the target.
4. **F13** (security/release): resolve the runtime constraint conflict (F25-D001: app's five dependency ranges vs CI-pinned vendor ranges; F25-D002 audit runtime) **before** any install from the built artifacts — installation waits on this decision, per your direction.
5. Then F05–F15 verification and the F16/F27 deployed reproductions proceed on the isolated target.

## 4. Blocker record (per plan F01 rule)

- **Blocked item:** kickoff role/site naming for F01; consequently F02 and all site-dependent packages.
- **Decision owner:** Mohamed. **Next decision date:** requested within this week.
- **Work that continues meanwhile:** source-level packages only (F24/F25/F28/F29 evidence follow-ups, F19/F18 service-contract design notes) — none of them may be recorded as runtime or acceptance evidence.

## 5. Verification

This document records an observed, read-only site inventory and prior ledger statements; no site was contacted, upgraded, migrated or reconfigured; no assignment was invented.
