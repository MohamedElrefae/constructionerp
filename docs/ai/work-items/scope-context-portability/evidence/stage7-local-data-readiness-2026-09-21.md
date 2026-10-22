# Stage 8 path readiness — local test transactions evidence (2026-09-21)

Owner-posted local test transactions (v16.localhost only):
`ACC-JV-2026-00001` (EGP 10,000 Debtors → Sales) and `ACC-JV-2026-00002`
(EGP 4,000 Cash → Debtors), posted via Journal Entries; the earlier Sales
Invoice draft `ACC-SINV-2026-00001` (EGP 10,000) remains **unposted and
untouched**.

## Read-verified live ledger state (console, read-only)

- 4 GL Entry rows for Elrefae; both JVs `docstatus=1`.
- AR outstanding `Prestiga-Biz` = **EGP 6,000** (10,000 − 4,000).

## Viewer readiness fix (owner-reported defect, resolved)

The Bilingual Report Viewer's General Ledger option failed because it had
no From/To date controls. Fixes:
1. **Viewer date fields** (من تاريخ/إلى تاريخ, Date controls + call via the
   primary action) and out-of-order render guard (a stale call can no
   longer overwrite the latest result).
2. **Endpoint `._ensure_required` extended**: General Ledger defaults
   from/to from the fiscal-year bounds; Accounts Receivable defaults
   `report_date`/`ageing_based_on`/`party_type`/`group_by_party`; Trial
   Balance keeps the fiscal-year default. Vendor shapes (AR Aging returns
   a 6-value tuple) are handled without vendor edits.
3. **GL label resolution fixed**: the mapping now keys both the bare
   account name AND the full doc identity (`1310 - Debtors - E →
   المدينون`), so GL lines localize instead of silently falling back to
   English.

Endpoint tests 9/9 OK; the stale `assert_called_once` test updated to
`>= 1` (the vendor default-fiscal-year lookup re-runs justified by the
date-window contract).

## Arabic reports verified live through the governed viewer (ar session)

- **General Ledger** (`both`): 16 rows — bilingual account lines
  `1110 - Cash - E — النقدية`, `1310 - Debtors - E — المدينون`;
  totals/closing rows in Arabic (`الإجمالي`, `الإغلاق…`).
- **Trial Balance** (`both`): 3 rows — `1110 - Cash - E — النقدية`
  (opening 4,000 Dr), `1310 - Debtors - E — المدينون` (10,000/4,000),
  `الإجمالي` — reflecting the Cash/Debtors/Sales movement.
- **Accounts Receivable aging** (`both`): Arabic headers و`Prestiga-Biz`
  rows for both posted JVs (`ACC-JV-2026-00001`, `ACC-JV-2026-00002`) plus
  the customer summary — the outstanding 6,000 aging movement rendered in
  the live viewer.

## Preflight

`uat_preflight.py` PASS run executed before the browser evidence
(redis PINGs, site 200, fresh ar Desk boot 10,752 entries + bucket key;
unconditional logout) — as the standing hard gate.

## Boundary

This proves **local test-data readiness** on `v16.localhost` only — the
other Stage-8 gates (real production data, backup/restore rehearsal,
explicit production authorization) remain as owner-stated. No catalog
change (no new `_()` msgids) — no evidence re-pin needed.
