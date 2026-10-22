# SCP-007 Status — Historical Evidence, Verification Tasks Open

**Work item:** `workspace-desk-coverage-v2`
**Candidate:** `d8be079d388472a42494d35a8e9ccc0b058d8163c55f21337ce3e3c5401554df`
**Date:** 2026-10-01
**Purpose:** Record the honest status of WDC-R1/R2/R6 after the Architect's Finding 2.

---

## 1. Why this is not a re-bound validation report

The SCP-007 measurements were taken on `2026-09-30` against the **live Frappe site**
`v16.localhost`, which served the installed app at
`/home/mohamed/frappe-bench/apps/construction`. At that time the installed app carried
retired candidate `341715dd…`.

That installed app has since been reverted to `develop` base and is **no longer the
candidate**:

| Tree | Workspace JSON sha | Cards | Links |
|---|---|---|---|
| Installed `apps/construction` (current) | `70f2ccdb450173ca…` | 4 | 10 |
| v2 candidate worktree | `7794fa70659850d7…` | 5 | 16 |

Re-measuring the site now would measure **base**, not this candidate. Binding the prior
measurements to `d8be079d…` would assert data collected against different content.

**Therefore SCP-007 is NOT re-bound. It is carried as historical evidence with verification
tasks explicitly open.** No completion is claimed.

## 2. What the prior measurement established (candidate `341715dd…`)

Retained because the 19 app-side files in v2 are **byte-identical** to that candidate
(verified: 19/21 manifest content hashes match; the 2 differences are the orchestrator files
G1 superseded). The structural and permission logic is therefore unchanged, and these results
transfer as *reasoning*, not as a v2 capture:

- `DocPerm[Scope Report Access Log]` grants read only to `System Manager` and `Auditor`.
- Effective permissions via `frappe.has_permission()` with **real single-role users** and no
  role monkeypatching: denied to Project Manager, Accountant, Site Engineer.
- Desk link visibility: PM 14/16, Accountant 11/16, System Manager 16/16, Auditor 6/16,
  Site Engineer 12/16.
- Direct `frappe.get_list()` denial, each identity confirmed to retain normal `User`-doctype
  access so denial is targeted rather than blanket.
- Rollback: 31 → 31 users, drift 0, no probe identities remaining.
- LTR static measurement: 5 cards, 16 links, 0 child tables, max card 20, max label 23, no
  RTL or bidi characters.

Source: `raw-logs/scp007-independent-recheck.txt`
(SHA-256 `8da3c9dc8715760c679f02a8dfc89135db51365d2af1c0bad18664057256efd9`).

## 3. Open verification tasks (WDC-R1 / WDC-R2 / WDC-R6)

| # | Task | Requirement | Blocker |
|---|---|---|---|
| 1 | **Live site re-measurement on v2** | WDC-R6 | Candidate must be installed into `apps/construction`, which mutates the live bench app. Not authorised; base cleanliness was a deliberate foundation. |
| 2 | **English/LTR browser coverage** | WDC-R1 | Requires a browser session against the candidate. The architect plan states static checks cannot establish wrapping, clipping or routing. **Never produced.** |
| 3 | **PO source ↔ compiled catalog binding** | WDC-R2 | Requires captured parsing/compilation evidence binding source to compiled catalog, plus runtime lookup. **Never produced.** |
| 4 | **v15 compatibility disposition** | WDC-R1 | No v15 runtime verification performed and none is claimed. Requires either evidence or an explicit reviewed amendment. |

Tasks 2–4 are substantive implementation/verification work, not repackaging. They are
scheduled for the Builder/Verifier legs of this cycle once a test harness or staging site
deployment is authorised, or they remain open at acceptance.

## 4. Superseded artefact

`scp007-permissions-and-desk-validation.json` remains on file as the retired-candidate-bound
report. It is **not** valid for `d8be079d…` and must not be treated as satisfying WDC-R1/R2/R6
for this candidate. Its `verdict` was already `PARTIALLY_SATISFIES` with four residual gaps
disclosed; that verdict stands, and the binding is now formally historical.
