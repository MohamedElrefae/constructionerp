# F04 — Financial fixtures and ordinary-role matrix (v16rehearsal.localhost)

**Date:** 2026-10-13
**Candidate:** construction `1e46488` · frappe 16.51.1 · erpnext 16.50.0
**Enforcement posture:** fixtures created while OFF (observed starting state); ON enable + readback still pending per §9 sequence. Scope-dependent evidence collected before ON is labeled accordingly.
**Status:** fixtures + role matrix complete; enforcement enable, login and F11/F12 evidence pending.

## 1. Fixture homes (two companies)

| Project | Company | Cost center | Use |
|---|---|---|---|
| PROJ-0014 (F04 Fixture Project A1) | _Test Company | Main - _TC | Primary BOQ + PM/engineer scope |
| PROJ-0015 (F04 Fixture Project A2) | _Test Company | Main - _TC | Second-project isolation case |
| PROJ-0016 (F04 Fixture Project B1) | Elrefae | Main - E | Cross-company denial case |

## 2. Independent worked examples (computed before entry, verified after save)

Rule basis: [confirmed financial rules](../customer-release-gap-fixes/FINANCIAL_RULES.md) — additive pricing on direct cost; factor > 0 multiplies quantities and values; missing factor defaults to 1.

| Item (BOQ-2026-8566) | Inputs | Expected (independent) | Stored | Match |
|---|---|---|---|---|
| F04 concrete works | qty 10 × contract 100 × factor 0.5; direct 60 | line 500; budget 300 | 500 / header budget accumulates 300 | Yes |
| F04 additive pricing 120 | direct 100 + OH 10% + profit 10% (additive) | sell 120; line 1×120×1 = 120 | 120 | Yes |
| F04 default factor | qty 5 × 20, factor omitted → 1 | line 100 | 100 (factor stored 1) | Yes |
| F04 zero basis | qty 10 × direct 0 × factor 1 | line 0, valid evidence | 0 | Yes |
| Header rollup | 500+120+100+0 contract; 300+100+100+0 budget | contract 720; budget 500 | 720 / 500 | Yes |

125-allowance variant (direct 100 + 10% + 10% + 5% tender allowance = 125) is a pricing-rule case for F07 cost-analysis approval flow, not a BOQ-line attribute — recorded here, executed under F07.

**Structural finding:** each non-group BOQ Structure auto-creates its BOQ Item (`create_boq_item`; unique key on `structure`). Fixtures update the auto-created rows in place via normal save; direct second-item insert under one leaf is refused by design. F05 must cover this path.

## 3. Ordinary-role matrix

| User | Roles | User Permissions | Scope context | Purpose |
|---|---|---|---|---|
| f04-pm@v16rehearsal.local | Project Manager | Company _Test Company; Project PROJ-0014 | _Test Company / Main - _TC / PROJ-0014 | Allowed company/project workflows |
| f04-engineer@v16rehearsal.local | Site Engineer | Company _Test Company; Project PROJ-0014 | same | Allowed measurement-stage workflows |
| f04-accountant@v16rehearsal.local | Accountant | Company Elrefae; Project PROJ-0016 | Elrefae / Main - E / PROJ-0016 | Cross-company denial vs A-fixtures |
| f04-readonly@v16rehearsal.local | Read-Only | none | none | Missing-scope + read-only denial |

Setup performed as Administrator (exempt behavior proves nothing about containment — ordinary-user proof belongs to F11). Passwords: F04 accounts created without login credentials in this step; login evidence requires credential set + enforced-scope session (pending).

## 4. Pending (in order)

1. Operator: set `enable_scope_context = 1`, record readback + timestamp + related flags; refresh sessions/caches.
2. Credential-set + ordinary-role login verification (F02 formal login test).
3. F11/F12 allow/deny matrix on these fixtures; re-run anything scope-dependent collected while OFF.
4. Zero-manual-restoration and revision/finance-posting examples under F07/F06 on these fixtures.

No rehearsal data was modified; all F04 records are namespaced `F04`. Pre-existing 23 headers / 213 revisions untouched.
