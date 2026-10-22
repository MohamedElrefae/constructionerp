# F18 — Cost database workbench UI: engineering browser evidence

**Date:** 2026-10-13
**Candidate:** construction `09c8cb1` + uncommitted F18 changes · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost, enforcement ON
**Browser:** system Chrome 151 via Playwright (Desk JS executed; screenshots retained beside this document)
**Status:** 8/8 browser checks pass. UI engineering evidence complete, separate from API tests. Owner acceptance (F18-U01–12) remains for the consolidated block.

## 1. What was built

Desk Page `cost-database-workbench` (`page/cost_database_workbench/`): Import section (company, workbook attach, template download, Validate→preview with proposed Item/UOM lists and conflict display, armed Confirm→commit with persisted counts) and Reprice section (company required + optional filters, prospective preview, confirm). Busy guards, stale-preview disarm on file change, timeout unknown-outcome messaging, Arabic-first labels, escaped rendering.

## 2. Browser results (8/8, maintainer + readonly sessions)

| Check | Evidence |
|---|---|
| U1 page loads with scope bar and identity | Title + `_Test Company` scope + f18-maintainer |
| U2/U3 preview shows no-save-yet + proposed F18UI-1 | `import-preview.png` |
| U4 confirm armed only after clean preview | Button state asserted |
| U5 commit reports persisted counts | "Committed: 1 items, 1 price rows" (`import-commit.png`) |
| U6/U7 reprice prospective preview + commit | Empty-result path correctly shown (`reprice.png`) |
| U8 readonly refused with no commit path | 403 + disabled Confirm (`readonly-denied.png`) |

Polish note for F43: empty reprice preview still arms Confirm (commits a no-op). Harmless but should stay disabled on empty results.

## 3. Serve-routing correction (affects cited HTTP evidence)

During this session it was proven that `bench serve` on this bench serves **v16.localhost regardless of Host header** (Administrator login with v16.localhost-only credentials succeeded under a v16rehearsal Host). Consequences:
- All authenticated browser/curl evidence in this program used site-bound clients and is correctly attributed — except the early F02/F13 curl checks (login-page render, guest denial), which are behaviorally identical on both sites but were served from v16.localhost. Those two claims are re-labeled accordingly; no safety conclusion depended on site-specific data.
- For this UI run only, `default_site` was temporarily pointed at v16rehearsal.localhost (disclosed), verified by successful maintainer login, then restored to v16.localhost (verified in config).
- F43 browser runs must assert the serving site (e.g., login with a site-unique identity) before recording UI evidence.
