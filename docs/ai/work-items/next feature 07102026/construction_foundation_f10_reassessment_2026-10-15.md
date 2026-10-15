# F10 — Legacy findings reassessed against the copied dataset (evidence)

Date: 2026-10-15 · Dataset: lab copy of rehearsal backup `20261014_234948`
(`f31upgrade.localhost`, DB `_0f3b34ab355fd9df`). Read-only SQL; **no repairs applied**.
Ambiguous financial history is preserved pending the owner's decision in each case.

## D001 — Locked headers, stored ≠ recomputed (same 6 IDs, exact amounts)

| Header | Stored | Recomputed | Items |
|---|---|---|---|
| BOQ-2026-0274 | 5,000.00 | 12,000.00 | 2 |
| BOQ-2026-0638 | 0.00 | 1,800.00 | 3 |
| BOQ-2026-0642 | 0.00 | 1,800.00 | 3 |
| BOQ-2026-0646 | 9,000.00 | 10,800.00 | 3 |
| BOQ-2026-0650 | 9,000.00 | 10,800.00 | 3 |
| BOQ-2026-0654 | 9,000.00 | 10,800.00 | 3 |

Impact: S1 wrong-money on Locked records. Copy-trial proposal (NOT applied): per-header
correction to the recomputed sum only with business approval per header — the stored value
may encode an approved commercial position the line history does not show. Awaiting owner call.

## D002 — 197 orphan Approved revisions (copy) vs 178 (rehearsal Oct-13)

Header+item deleted, approval history remains. Copy-trial proposal: reviewed archival with
the ID list (list retained in lab working notes, not customer data); no deletion of
approved history without steward sign-off.

## D003 — 8 items with 2–7 conflicting Approved revisions

BOQI-BOQ-2026-0646-0648 (2), -0650-0651 (3), -0650-0652 (2), -0654-0655 (3), -0654-0656 (2),
-8575-8576 (7), -8758-8759 (2), -8873-8874 (2). Ambiguous basis — none selected.
Copy-trial proposal: surviving basis via a NEW correction analysis (creates history, never
rewrites it), per item, with QS approval each.

## D004 — 4 orphan structures, no dependents

Copy-trial proposal: reviewed delete (safe — dangling nodes, empty test groups confirmed).

## D005 — 11 approved VOs without revision linkage (copy) vs 8 (rehearsal)

Pre-idempotency history. Copy-trial proposal: document as historical; backfill only with
real source evidence, never invented linkage.

## D006 — 9 unprojected items (qty > 0, no revised quantity)

Copy-trial proposal: confirm quantities real, then a reviewed baseline run.

## 54 missing file paths — individually classified

Source-site enumeration (File records vs filesystem, 2026-10-15; full ID list in
`/tmp/opencode/f10-missing-files.json`, working notes only):

- **All 54** attach to one header: BOQ Header `BOQ-2026-0002`.
- **All 54 public** (`is_private=0`); **zero** signed-approval or client-approval names.
- 34 × `.html` (print outputs), 20 × `.xlsx` (export workbooks), all timestamped April 11–13.
- Classification: **regenerable print/export test residue** — not required attachments,
  not signed evidence. Recoverability: re-print / re-export on demand. Remediation: none
  required; record as residue. No content recreated, no fake evidence generated. Optional
  reviewed record cleanup is an owner call.

## Copy-trial outcomes (lab copy `f31upgrade.localhost`, 2026-10-15 — owner-approved decision)

- **D004 closed:** 4 orphan structures deleted after verified zero dependents on all axes
  (162→158 structures, 0 orphans). Controller deletion impossible (on_trash demands the
  missing parent), so exact-ID removal with counts; gaps benign.
- **D002 archived, deletion open:** 197 Approved revisions dumped to
  `f10-orphan-revisions-archive-2026-10-15.json` (219KB, durable). Long tail spans deleted
  test-series and operational headers — steward must classify before any deletion.
- **D005 closed as documented limitation:** all 11 VO lines reference items with zero
  revisions anywhere; no evidence exists to link. No backfill.
- **D001/D003/D006 reconciled together, unresolved:** overlaps mapped (0646/0650/0654
  families appear in all three; 0274 pair; Arabic test items on 0002/0006). Intended
  business quantities cannot be established from test patterns alone — brought to owner
  per directive (no uniform generated-data assumption applied to money).
- **54 paths:** residue classification accepted; new export proven on lab copy
  (`F19_price_history_20261015_035958.json`, 9 rows, basis + identity columns present).

### ID list (54 File records, content absent on source site)

| File name | URL | Attached to |
|---|---|---|
| BOQ_BOQ-2026-0002_20260414_1946447c9161.html | /files/BOQ_BOQ-2026-0002_20260414_1946447c9161.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_2334095d5178.html | /files/BOQ_BOQ-2026-0002_20260413_2334095d5178.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_23335834f6bf.xlsx | /files/BOQ_BOQ-2026-0002_20260413_23335834f6bf.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_072121f7fd22.html | /files/BOQ_BOQ-2026-0002_20260413_072121f7fd22.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_072058d234db.html | /files/BOQ_BOQ-2026-0002_20260413_072058d234db.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_0720359221f3.html | /files/BOQ_Header_BOQ-2026-0002_20260413_0720359221f3.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_070435.html | /files/BOQ_BOQ-2026-0002_20260413_070407e25d1a.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_070407e25d1a.html | /files/BOQ_BOQ-2026-0002_20260413_070407e25d1a.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_070341.html | /files/BOQ_Header_BOQ-2026-0002_20260413_07031611c8b4.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_07031611c8b4.html | /files/BOQ_Header_BOQ-2026-0002_20260413_07031611c8b4.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_0702471fd6bf.html | /files/BOQ_BOQ-2026-0002_20260413_0702471fd6bf.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_07020744a2d0.html | /files/BOQ_Header_BOQ-2026-0002_20260413_07020744a2d0.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_07012798228e.xlsx | /files/BOQ_Header_BOQ-2026-0002_20260413_07012798228e.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_070059.html | /files/BOQ_Header_BOQ-2026-0002_20260413_070016d9bbad.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_070016d9bbad.html | /files/BOQ_Header_BOQ-2026-0002_20260413_070016d9bbad.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_06593793c915.html | /files/BOQ_Header_BOQ-2026-0002_20260413_06593793c915.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_064238b0f313.xlsx | /files/BOQ_BOQ-2026-0002_20260413_064238b0f313.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_064155efa610.xlsx | /files/BOQ_BOQ-2026-0002_20260413_064155efa610.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_06410466d007.xlsx | /files/BOQ_BOQ-2026-0002_20260413_06410466d007.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_064024d31841.xlsx | /files/BOQ_BOQ-2026-0002_20260413_064024d31841.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_06384954b61b.xlsx | /files/BOQ_Header_BOQ-2026-0002_20260413_06384954b61b.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_06381746b386.xlsx | /files/BOQ_Header_BOQ-2026-0002_20260413_06381746b386.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_063555.html | /files/BOQ_Header_BOQ-2026-0002_20260413_063507874741.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_063530691f9c.html | /files/BOQ_BOQ-2026-0002_20260413_063530691f9c.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_063507874741.html | /files/BOQ_Header_BOQ-2026-0002_20260413_063507874741.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_0634364f3f24.html | /files/BOQ_Header_BOQ-2026-0002_20260413_0634364f3f24.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260413_063405b681b6.html | /files/BOQ_BOQ-2026-0002_20260413_063405b681b6.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260413_063332c0fa08.html | /files/BOQ_Header_BOQ-2026-0002_20260413_063332c0fa08.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260412_112323807b78.html | /files/BOQ_Header_BOQ-2026-0002_20260412_112323807b78.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260412_11225697587f.html | /files/BOQ_BOQ-2026-0002_20260412_11225697587f.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260412_1122274346ba.html | /files/BOQ_BOQ-2026-0002_20260412_1122274346ba.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260412_1116159977b7.html | /files/BOQ_BOQ-2026-0002_20260412_1116159977b7.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260412_111513c4be3a.html | /files/BOQ_Header_BOQ-2026-0002_20260412_111513c4be3a.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260412_103936ed32e3.html | /files/BOQ_Header_BOQ-2026-0002_20260412_103936ed32e3.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260412_103514720916.xlsx | /files/BOQ_Header_BOQ-2026-0002_20260412_103514720916.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260412_1034053942c4.html | /files/BOQ_BOQ-2026-0002_20260412_1034053942c4.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260412_10335424dca0.html | /files/BOQ_BOQ-2026-0002_20260412_10335424dca0.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260412_103346f17946.html | /files/BOQ_Header_BOQ-2026-0002_20260412_103346f17946.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260412_001404fc435d.html | /files/BOQ_Header_BOQ-2026-0002_20260412_001404fc435d.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260412_001348.html | /files/BOQ_BOQ-2026-0002_20260412_0013012a07fa.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260412_001338114264.xlsx | /files/BOQ_BOQ-2026-0002_20260412_001338114264.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260412_0013012a07fa.html | /files/BOQ_BOQ-2026-0002_20260412_0013012a07fa.html | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260412_001251d24df7.html | /files/BOQ_Header_BOQ-2026-0002_20260412_001251d24df7.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260412_001224b226c6.html | /files/BOQ_BOQ-2026-0002_20260412_001224b226c6.html | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260411_2309427c9296.xlsx | /files/BOQ_BOQ-2026-0002_20260411_2309427c9296.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260411_2309386801e0.xlsx | /files/BOQ_Header_BOQ-2026-0002_20260411_2309386801e0.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260411_230350fe0da0.xlsx | /files/BOQ_BOQ-2026-0002_20260411_230350fe0da0.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260411_230213a6fd48.xlsx | /files/BOQ_BOQ-2026-0002_20260411_230213a6fd48.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260411_230129e4b257.xlsx | /files/BOQ_Header_BOQ-2026-0002_20260411_230129e4b257.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_Header_BOQ-2026-0002_20260411_225619a8c02f.xlsx | /files/BOQ_Header_BOQ-2026-0002_20260411_225619a8c02f.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260411_224851095d1c.xlsx | /files/BOQ_BOQ-2026-0002_20260411_224851095d1c.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260411_213356400eb4.xlsx | /files/BOQ_BOQ-2026-0002_20260411_213356400eb4.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260411_202747f1f4ff.xlsx | /files/BOQ_BOQ-2026-0002_20260411_202747f1f4ff.xlsx | BOQ Header BOQ-2026-0002 |
| BOQ_BOQ-2026-0002_20260411_202204264ae6.xlsx | /files/BOQ_BOQ-2026-0002_20260411_202204264ae6.xlsx | BOQ Header BOQ-2026-0002 |
