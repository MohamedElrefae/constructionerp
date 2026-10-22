# F17 — Import review, error files and traceability: evidence

**Date:** 2026-10-13
**Candidate:** construction `09c8cb1` + uncommitted F16/F17 changes · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost, enforcement ON, PM/Accountant sessions + Administrator setup
**Status:** 17/17 checks pass + 4/4 regression (incl. new description test). F17 **Engineering verified**; owner UI-50/51/53 + F40 guide wording remain.

## 1. Results (17/17)

| Area | Evidence |
|---|---|
| Structured mode | Detected, clean preview, committed; WBS hierarchy correct (1.1.1 under 1.1) |
| Semi-structured mode | Detected, committed with batch |
| Multi-sheet | Preferred sheet name (`BOQ`, incl. Arabic aliases) wins regardless of order |
| Ambiguous rows | Flagged with row number; commit without resolutions refused (417); zero silent writes |
| Error file | Generated with Source Row/Sheet/Error columns; stored private + attached to header; owner downloads and reads it; cross-scope denied (403) |
| Traceability | Preview rows carry row_no + sheet_name; all committed items batch-tagged (16/16) |
| Limits (documented, code + behavior) | 25 MiB file, 10,000 rows, 20 header-scan rows, 2,000 async threshold, 100 columns, ZIP/XML prescan; just-over-limit proven in F14 |

## 2. Fix in this package (F17-D001, S2)

Imported items carried NULL `cost_item` (description lived only on the structure) across all modes — item lists/reports/exports keyed on it showed blanks. `_update_imported_item` now carries the structure title onto the item; 23 existing NULL rows on dedicated F14/F16/F17 headers backfilled (disclosed data step, test fixtures only). Regression test added (4/4 module pass).

## 3. Remaining

Dialog surfacing of the error-file download link (F16 dialog points at it in text; a one-click download belongs to F43 UI polish); F40 format-limits wording; owner acceptance in the consolidated block.
