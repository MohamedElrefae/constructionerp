# Private CI status and stabilization audit (2026-10-06)

**Destination:** `MohamedElrefae/constructionerp-private`, branch `codex/customer-release-ci-20261005`, visibility Private (unchanged).
**Publication checkout:** `/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/private-ci-20261005/repo`, HEAD `f63d7395975ff31dbafb2c70c8130ac9a92afbf9`.
**Exact provider environment:** Ubuntu 24.04, Python 3.14.7, Node 24, MariaDB 10.11, disposable Redis; Frappe `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`, ERPNext `2807c9f08fff3f161c0a2e10745a26aa6331ffd5`.

## Final result: green provider CI established

**Run 11** (`f63d739`, 2026-10-05 18:10–18:30:15 UTC) completed successfully:

- Fresh install: PASS (Construction install step green; `list-apps` shows `construction 0.0.5 codex/customer-release-ci-20261005`).
- Fixtures: synthetic `_Test Company` (`_TC`, India, INR, Standard chart) seeded via ERPNext native controller, plus one company-less active calendar-year `Fiscal Year` covering today.
- **Python: 17/17 modules, 234 tests, all `OK`**.
- **JS property tests: 35 pass, 0 fail**.
- Full local log retained at `private-ci-20261005/run11-full.log`.

## Run-by-run stabilization ledger

| Run | SHA | Outcome | Root cause / fix |
| --- | --- | --- | --- |
| 8 | `116562f` | Failed after 3 modules, exit 1 | `test_stage7_bilingual_reports` 7 errors; discovery aborted with `ModuleNotFoundError: No module named 'pytest'` (test imports pytest/hypothesis). |
| 9 | `8f7ea41` | Failed across modules | Added `pytest==9.0.3` + `hypothesis==6.155.1` install step (fixed discovery). New failure: `ValidationError: Party Account _Test Payable - _TC currency (EGP) and document currency (INR) should be same` — synthetic company used EGP/Egypt while Frappe legacy test records are INR/India for `_Test Company`. |
| 10 | `6646a1b` | Failed in `test_stage7_bilingual_reports` (3 errors) | Company aligned to canonical `_Test Company` / INR / India (matches `erpnext/setup/doctype/company/test_records.json`). New failure: `FiscalYearError: Date 2026-10-05 is not in any active Fiscal Year for Elrefae` — company-scoped year missing. |
| 11 | `f63d739` | **PASS** | Fiscal Year fixture changed to a company-less active calendar year (ERPNext applies those to every company; matches the non-installed `Elrefae` company label exercised by bilingual statement tests). All 17 modules green. |

## Changes made (CI harness only)

1. `ci.yml`: new step `Install Python test dependencies` pinning `pytest==9.0.3`, `hypothesis==6.155.1` (versions from the qualified local runtime).
2. `business_fixtures.py`: company switched to canonical `_Test Company` / India / INR; added `_ensure_current_fiscal_year()` seeding one company-less active calendar-year Fiscal Year derived from the current date; refuses to overlap an unrecognized same-name year.
3. `year alignment` — all CI helpers and workflow adjustments are contained within `.github/ci/` and `.github/workflows/`. No application logic, test assertions, fixtures, site data, credentials, reports, or backups were added or modified beyond these CI harness changes. The synthetic fixtures create only disposable CI records in the disposable `test_site`.

## Follow-up

- `STATUS.md` G07 row and the private-CI paragraph now record runs 8–11 and the passing run 11.
- `VERIFICATION.md` private provider CI section updated with the final ledger.
- `publication-manifest.json` `ci_runs` should be extended with runs 8–11 by the lead verifier when finalizing (left untouched here per handover boundary; edits in this session left unstaged).
- Remaining customer-release gates (security dependency qualification, sold workflow/role coverage, capacity/SLA, hosting authority) are unchanged; a green provider CI does not certify release.