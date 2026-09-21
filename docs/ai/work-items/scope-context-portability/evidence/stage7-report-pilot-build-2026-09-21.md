# Stage 7 — report/print pilot: build status (2026-09-21)

## Delivered now (test site, vendor files untouched)

1. **Governed bilingual report API** (`construction/api/bilingual_reports.py`):
   `localized_report(report_name, filters, mode)` — fail-closed pilot
   allowlist (General Ledger, Trial Balance, Accounts Receivable), role
   gated (`Accounts User/Manager/System Manager`), delegates to the
   Stage-4 extension-point service; vendor `execute` runs read-only under
   the caller's own permissions; source structures never mutated.
2. **Site tests** (`construction/tests/test_stage7_bilingual_reports.py`,
   4 tests, bench-run OK): fail-closed unknown report; ar/both/en modes.
3. **Live render validation** (console, read-only): the governed wrapper
   executes the real vendor workers for Elrefae (GL + TB) without error and
   returns the vendor row shape; the transform applies when
   `account_name_ar` data is present.

## Honest boundary: no GL transactions exist on the test site

`tabGL Entry` is empty for every company on `v16.localhost`, so the
GL/Trial-Balance pilots render only Opening/Total rows. Arabic label
rendering on populated reports is joke-verified against real ledger data
only when live transactions exist — which is a Stage 8 gate (production
site) exactly like the Wave-1 master data deferral. The transform itself
is unit-tested with a real account mapping (mapping keyed by
`account_name` → `account_name_ar`, 81 owned rows).

## Drawn scope vs remaining Stage-7 items (owner-owned)

- AR Aging + BOQ print/export: pilot surfaces defined; BOQ print/export
  implementation and the desk-side viewer button are the next build steps
  after your go (same vendor-file-clean approach).
- The viewer/button UI is intentionally not yet shipped — the governed API
  is standalone and additive; nothing vendor-side.

## Re-pin cadence note

No translation rows or catalog rows changed in this increment; no Stage-2
evidence re-pin required. The next catalog/UI batch re-pin covers this
cycle's HEAD later anyway.
