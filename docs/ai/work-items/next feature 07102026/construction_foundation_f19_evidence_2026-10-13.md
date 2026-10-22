# F19 — Existing reports and integrity visibility: engineering evidence

**Date:** 2026-10-13
**Candidate:** construction `09c8cb1` + uncommitted F19 changes · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost, enforcement ON
**Browser:** system Chrome 151 via Playwright (screenshots beside this document)
**Status:** adapter + viewer built; 10/10 browser checks pass. F19 **Engineering verified** for the view scope; owner F19-U01–12 remain for the consolidated block.

## 1. What was built

- `construction/api/construction_reports.py`: allowlisted `report_view` (5 services) with required Company, header match check, per-row document authorization, bounded paging (50/200); `report_export` (same boundary, 2,000 cap, private File attached to the header — covered by the F11 file guard); `integrity_view` (Administrator-only passthrough with read-only contract). Unknown identifiers refused. Finance ledgers not included.
- Desk Page `construction-report-viewer`: six views with basis labels, paging info, export, escaped rendering, stale guards.

## 2. Browser results (10/10, site-asserted maintainer + accountant sessions)

| Check | Evidence |
|---|---|
| S0 serving site proven | Maintainer login (site-unique identity) before every run |
| V0–V-missing | All five views render with basis labels; values shown or honest empty states |
| V-summary-nonempty | 4 of 4 rows on the F08 header (Approved + Superseded) |
| V-integrity-denied-nonadmin | Refused for maintainer |
| V-cross-scope-denied | Refused for Elrefae accountant on _Test Company header |

Serving procedure (standing rule from F18): `default_site` temporarily pointed at the UAT target, proven by site-unique login, restored to v16.localhost afterwards (verified in config).

## 3. Data-hygiene note

View analyses without a project value are invisible to scoped reads (same lesson as reprice). F08 fixture analyses were tagged PROJ-0014 (disclosed fixture fix). Consider requiring project on non-template analyses in a later hardening pass (F38 backlog, not a blocker).
