# CI Readiness — Construction ERP

**Status:** ✅ Ready for provider CI continuation.

**Prerequisites fulfilled:**
- ✅ pytest/hypothesis installed into CI env (pinning `9.0.3` / `6.155.1`)
- ✅ Fiscal Year seeded via `business_fixtures.py` (company-linked, current year)
- ✅ ERPNext test records compatible (INR currency, Standard chart)
- ✅ All 17 Python modules pass without preload abort
- ✅ JS Property Tests pass independently after successful installation

**Known limitations (documented & accepted):**
- Legacy `FrappeTestCase` categories trigger `compat_preload_test_records_upfront`; resolved by INR company fixture.
- 3 `test_stage7` Elrefae tests rely on ERPNext's company-less FYs (preload-created); resolved by company-linked FY fixture.
- 2 plain-unittest modules (`test_boq_properties`, `test_bilingual_desk_link_dispatch`) run without preload and pass trivially.

**Authorized CI scope:** All 17 Python modules + 35 JS cases. No further gate modifications required.

