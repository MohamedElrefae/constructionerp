# F06 — Variation and approval-history protection: engineering evidence

**Date:** 2026-10-13
**Candidate:** construction `1e46488` · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost, enforcement ON, five ordinary sessions (PM, Owner, Engineer, ReadOnly, SM) + Administrator setup
**Transport:** site-bound WSGI test clients (per-user login sessions); document REST for lifecycle, multipart upload for the approval PDF
**Status:** 25/25 checks pass (part 1: 12/12 revision lifecycle; part 2: 13/13 VO lifecycle + correction). F06 **Engineering verified** for approval-history scope; VO/material-request handoff detail belongs to F20; F11 matrix remains.

## 1. Fixtures (dedicated, F04 baseline untouched)

Header BOQ-2026-8575 (Locked, project PROJ-0014) + 1 item (qty 10 × 100 × factor 1 = 1000). Approver account f06-owner (Construction Owner, _Test Company/PROJ-0014 permissions + scope) and f06-sm (System Manager, same scope) created alongside F04 users. Final history: Original Lock 0→10, revision 10→12, revision 12→14, VO revision 14→15, correction 15→12 — all Approved; item current 12, header revised 1200, contract 1000.

## 2. Results

| Check | Result |
|---|---|
| T1 PM creates Draft revision, Owner approves over HTTP; projection 12→1400 exactly once | Pass |
| T2 repeat approval is a no-op; no duplicate revision; totals unchanged | Pass |
| T3 approved commercial edit refused (417); totals undisturbed; truly-unchanged resave allowed | Pass |
| T4 approved revision deletion refused (417); record survives | Pass |
| T6 engineer direct revision approval refused (403 — no revision write); readonly create refused (403) | Pass |
| T5 VO Draft→Submitted (PM) → Engineer-approved (SM) → Client-approved (Owner), PDF gate enforced; projection 15/1500 exactly once | Pass |
| T5 engineer client-approval refused (403); readonly submit refused (403) | Pass |
| T5 approved-VO resave: no double projection; commercial edit refused (417) | Pass |
| T7 correction 15→12 restores prior state; 5-record history all Approved | Pass |

## 3. Findings

- **F06-D001 (S1 role-design conflict, open):** Site Engineer holds the workflow engineer-approver role but lacks BOQ Header write, so the BOQ parent gate refuses engineer approval (proven 403). Combined with SoD (submitter cannot self-approve), no all-PM/Engineer/Owner chain can complete a VO when PM submits — this run completed via SM (documented SoD-bypass role, ordinary non-Administrator identity). F11/F20 must reconcile workflow roles with parent permissions: either grant the engineer-approver a scoped write path or redefine the approver role. No code changed by this finding.
- **F06-D002 (S2 test-hygiene note, closed):** revision payloads must carry explicit `revision_type` (default `Original Lock` is rejected at insert), `revision_date`, and FIDIC justification when >25% from contract — callers that omit them get correct 417 refusals, not silent defaults. The Desk form path should be checked to supply the same (F43 case note).
- Fixture handling disclosed: interrupted-run debris (2 Submitted VOs, 2 Draft revisions) deleted — both deletable states; approved records were never deleted (force-delete refused, itself evidence for T4). One mid-session inconsistency of my own (item reset to 10 while history said 12) was repaired back to approved evidence before testing.

## 4. Remaining

F20 transaction-handoff detail (VO→Material Request, cascade messages); F11 full allow/deny matrix reusing these fixtures and sessions; owner UI-29–36 in the consolidated block.

## 5. F06-D001 fix record (2026-10-13) — CLOSED pending owner retest

**Change (one function, `construction/overrides/boq_permissions.py`):** for Variation Order writes only, the parent gate requires BOQ Header READ instead of WRITE. All other child doctypes unchanged. Rationale in code comment: VO commercial integrity is enforced by transition validity, SoD, server-owned audit identities, snapshot immutability and the signed-PDF gate — none of which consult this gate.

**Verification:**
- New regression module `construction/tests/test_vo_approval_parent_gate.py` (5 tests): engineer-approve passes; item write still refused; cross-header move refused; client-approve still Owner-only. **Fail-before proven:** with the fix stashed, 3 fail; restored, 5/5 pass.
- Full intended chain over HTTP with three ordinary identities: PM submits → **Engineer** approves → Owner client-approves (PDF gate), projection exact (13/1300); cross-scope accountant denied (403). 6/6.
- `allow_tests` was enabled only for the regression run and removed afterwards (site_config key deleted, verified).
- Preserved: SoD (self-approval still refused), scope enforcement (ON throughout; cross-scope 403), commercial-field protection (frozen/snapshot refusals re-verified in the same runs), Administrator bypass untouched.
- Changed files uncommitted (fix + test module), held for F38 with the sidebar config change. Owner retest of UI-29–36 happens in the consolidated block.
