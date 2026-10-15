# F20 — Native transaction handoff improvements: integration-field evidence

**Date:** 2026-10-13
**Candidate:** construction `09c8cb1` + uncommitted changes · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost, enforcement ON, Administrator + PM sessions, site-bound clients
**Status:** 12/12 Draft handoffs + submit/reopen evidence. F20 **Engineering verified** for the reconciliation scope; transacting-role grants + owner UI-37–44 remain.

## 1. Common row matrices (all 8, Draft saves)

Dedicated Locked header BOQ-2026-8642 (PROJ-0014). One attributed row per doctype, all saved 200: MR/PO/PR/PI/SI/SE/Timesheet/JE with their gate fields (expense_category Direct ×6, is_progress_billing ×1, designation Project Manager ×1).

## 2. Corrections observed (not app defects)

- Header/structure auto-fill from the item works; attribution survives save + reload + amend (amended MR keeps boq_item/header).
- Incomplete attribution refused with row-level messages (header-without-item 417).
- Fixture gaps closed on UAT (disclosed test data): EGP→INR Currency Exchange 0.64; row schedule dates after transaction date; per-row warehouse on stock items; INR document currency matching party accounts.
- PO submit captures Resource Price History (rate 100, source Purchase Order, company _Test Company). MR submit→cancel→amend cycle preserves attribution.

## 3. Persona handoffs (2026-10-14, owner-directed mapping)

Seven UAT accounts (disclosed fixtures; passwords to operator separately, rotate before UI block):

| Persona | Account | Native roles | Lifecycle proven |
|---|---|---|---|
| Site requester | f20-requester | Stock User | MR create/submit/cancel |
| Buyer | f20-buyer | Purchase User | PO create/submit/cancel |
| Storekeeper | f20-store | Stock User | PR + SE full cycles |
| Accounts payable | f20-ap | Accounts User | PI create/submit/cancel (see D002) |
| Accounts receivable | f20-ar | Accounts Manager | SI full cycle |
| Assigned employee | f20-emp | Employee (+ mapped Employee master HR-EMP-00001) | TS create; submit denied by design (417) |
| Accountant | f20-acc | Accounts User | JE create/submit/cancel via docstatus |

26/26 persona checks: lifecycles as above + 3 cross-company denials (403). Minimal read-only additions with full standard-row replication: Account read for Stock User, Item read for Accounts Manager (both required by ERPNext link/account validation during posting).

## 5. Permission findings and corrections (2026-10-14, owner-directed review)

**One permission system (owner policy):** native roles/DocPerm + native User Permissions + Construction scope (authorization boundary) + Construction business guards. All applicable checks must pass for ordinary users; Construction roles never substitute for native transacting rights and vice versa. Persona = test account; role = native responsibility.

**Custom-DocPerm replacement rule (confirmed):** custom rows REPLACE standard rows per doctype (owner verified in framework). My F18 grants wiped 8 doctypes site-wide; repaired by replicating 51 standard rows. Reconciliation process: `scripts/permission_reconciliation.py` (report + `--baseline` diff, non-zero on undocumented drift) with checked-in [baseline](permission_reconciliation_baseline_2026-10-14.json) — 14 customized doctypes (8 mine + Address/VAT pre-existing). "Copy first" alone is insufficient; rerun + diff at F31/F41. Also removed one stray standard row my failed first attempt left behind (Company/Maintainer full rights — inert while customs exist, dangerous otherwise).

**F20-D002 WITHDRAWN (my misreading):** the framework DOES check cancel on the submitted→cancelled transition (`check_docstatus_transition`); AP's cancel succeeded because installed DocPerm grants Accounts User cancel=1 on Purchase Invoice (verified in both tables). "Write means cancel" is NOT policy. AP evidence stands as legitimate behavior.

**F20-D003 RESOLVED:** ERPNext's `validate_employee_role` hook strips Employee/Self-Service roles on User save unless an Employee master maps `user_id`. Created HR-EMP-00001 for f20-emp; role persists; Timesheet creation verified with the pure Employee role. Persona matrix updated (emp = Employee role, not Projects User).

## 4. Findings

- **F20-D001 status:** handoffs pass for all 7 personas → Fixed awaiting owner retest (UI-37–44). Production staffing/grants remain owner decisions.
- **F20-D002 (framework behavior):** `Document.cancel()` runs through WRITE permission (`_cancel` → `save`), not the cancel flag — AP cancelled a PI despite cancel=0. SoD designs must treat cancel rights as write rights.
- **F20-D003 (unresolved vendor observation):** the Employee role is silently dropped on every User save on this site (ORM append/save/commit loses it; raw SQL persists; Projects User persists normally). Persona uses Projects User instead. For F38/vendor follow-up; no workflow depends on granting Employee.
