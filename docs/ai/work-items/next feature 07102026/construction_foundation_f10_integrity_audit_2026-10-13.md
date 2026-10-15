# F10 — Legacy data and integrity reconciliation: read-only audit

**Date:** 2026-10-13
**Candidate:** construction `1e46488` · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost (SELECT-only queries; zero writes performed)
**Legacy scope:** records on projects other than PROJ-0014/0015/0016 (F04–F09 fixtures excluded). 18 legacy headers, 34 legacy items, 35 attached + 178 orphan revisions, 33 VOs, 2 stages, 0 legacy cost analyses.
**Status:** audit complete; no repairs executed. F10 **In progress** until owner classification + reviewed corrections.

## 1. Clean (no discrepancy)

| Area | Evidence |
|---|---|
| BOQ line totals (34 legacy lines) | 0 mismatches vs qty × contract × factor |
| Factors | 0 null/zero/negative |
| Stage quantities and certification | 2 legacy stages, both empty Not Started; 0 certified>measured, 0 duplicates, 0 orphans |
| VO line links | 0 orphan item references |
| Legacy cost analyses | 0 exist — legacy items carry no cost basis (F07 flows on them use manual/legacy paths) |

## 2. Discrepancies (no repair performed)

| ID | Records | Expected vs actual | Severity | Proposed repair (requires owner approval each) |
|---|---|---|---|---|
| F10-D001 | 6 Locked headers: 0274 (5000 vs 12000), 0638/0642 (0 vs 1800), 0646/0650/0654 (9000 vs 10800) | Stored contract ≠ recomputed line sum | **S1** wrong-money on Locked records | Recalculate via supported rollup on an isolated copy first; owner approves per-header correction; never blanket SQL |
| F10-D002 | 178 Approved revisions with header AND item both deleted | Orphaned approval history (matches known test-remnant class) | **S1** data hygiene | Owner confirms test classification → reviewed archival with ID list preserved; operational stragglers (if any) reconciled first |
| F10-D003 | 6 items (0646/0650/0654 pairs) with 2–3 conflicting Approved revisions each, none matching item current (e.g., current 90 vs approved 100/126/50) | Ambiguous approved basis | **S1** | Owner classifies test vs operational; operational items get a surviving basis via new correction revision with history preserved |
| F10-D004 | 4 orphan structures (headers 1514/1521/1525/1527 deleted); empty test groups, 0 items, 0 children | Dangling WBS nodes | S2 | Owner confirms → reviewed delete (no dependents verified) |
| F10-D005 | 8 client-approved VOs (0274-VO-002 + 7 concurrency VOs) with lines lacking `created_quantity_revision` | Pre-idempotency history without revision linkage | S2 | Backfill linkage only where approval evidence exists; otherwise document as historical |
| F10-D006 | 8 items with current_revised_qty 0 but quantity > 0 (incl. Arabic-titled live-looking rows on 0002/0006) | Never projected/baselined | S2 | Reviewed baseline-factory run after owner confirms the quantities are real |

Cross-note: BOQ-2026-0274 items also show current 0 (part of D006) while its header shows the D001 total gap — the two findings interact on that header; correct it as one reviewed case.

## 3. Method

All `SELECT` via `bench mariadb` (no Frappe writes possible in that path). Fixture separation by project (PROJ-0014/15/16 excluded). No backup/restore, migration, commit or push in this task.
