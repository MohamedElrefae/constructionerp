# F07 — Cost projection and cancellation: engineering evidence

**Date:** 2026-10-13
**Candidate:** construction `1e46488` · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost, enforcement ON, ordinary sessions (Owner/PM/Engineer/Accountant) + Administrator setup
**Transport:** site-bound WSGI test clients; document REST + run_method submit/cancel
**Status:** 18/18 checks pass. F07 **Engineering verified** for projection/cancellation scope; report/guide agreement (F19/F40) and owner UI-16–23 remain.

## 1. Fixtures

BOQ-2026-8571 item (manual est 50, qty 10 × 100 × factor 1) + zero-manual item (est 0) on fresh leaves. Analyses use one detail row (10 units @ 10, no wastage) → direct 100/unit. Independent values: 100+10%+10%+0% = 120; with 5% allowance = 125.

## 2. Results (18/18)

| Check | Result |
|---|---|
| T1 A1 submit projects 100/120 with Approved-Analysis basis | Pass |
| T2 resubmit: values stable, no compounding, no new history | Pass (returns 200 — see note) |
| T3 A2 (5% allowance) projects 125; A1 → Superseded | Pass |
| T4 cancel A2 restores A1 (100/120, Approved) | Pass |
| T4 cancel A1 restores manual snapshot (50/50, Manual) | Pass |
| T5 engineer create refused at 403 (no create right); cross-scope company mismatch refused; totals unchanged | Pass |
| T6 zero-manual cycle: submit then cancel restores 0 with Manual basis | Pass |

## 3. Notes

- **F07-D001 (S3 API hygiene, open):** resubmitting an approved analysis returns 200 and recomputes identical values instead of refusing. Financially inert (no compounding proven), but a stricter refusal would be clearer. Not a money defect; revisit only if F38 triages it.
- Cancellation chains follow `supersedes_analysis` with manual-snapshot fallback; superseded-history cancellation cannot replace the active basis (code path reviewed, not separately executed).
- F04/F05/F06 baselines untouched (dedicated leaves on the shared F05 header; F04 header and F06 header/history unchanged).
