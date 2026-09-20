# Stage 6 — Production workflow matrix proposal (2026-09-21)

**Status: PROPOSAL ONLY — owner mark-up pending. No translations committed, no runtime import.**

Basis: vendor gap ledgers (`docs/erpnext_ar_missing_review_filled.csv` — 4,342
rows with 2,064 pre-filled reviewed msgstr; frappe side in
`docs/frappe_ar_missing_review.csv`), the current catalog inventory (15,106
total / 7,339 empty), and the Stage-1C released payload (34 runtime
overrides, verified). Per plan §11 the gate is "No unapproved English in the
agreed production workflow matrix"; big-bang rollout on all 7,339 strings is
forbidden.

## Proposed batches (owner mark-up column)

| Batch | Area (from vendor locations) | Rows (erpnext pre-filled/file) | Screens touched (user workflow) | Proposed priority | Owner decision (approve/defer) |
|---|---|---|---|---|---|
| W6-0 | Desk shell + navigation (incl. remaining global UI beyond the 6 Stage-1C labels) | frappe views/desk subset (see frappe_ar_missing_review) | Everyday desk lookups, navbar, sidebar | P1 | ☐ |
| W6-1 | Accounting — books screens (journal entry, payment entry, GL detail, invoices' print-status tiles) | 1,265 (subset: ~250 user-visible flow strings) | Accounting documents the bilingual reports pilot depends on | P1 | ☐ |
| W6-2 | Buying + Selling masters & documents (PO, PR, SO, DN, Sales Invoice create/print) | 143 + 194 | Purchase/sales desk lifecycle | P2 | ☐ |
| W6-3 | Stock — Warehouse, Receipts, Stock Entry, valuation reports (`stock`) | 789 | Warehouse/stock desk | P2 | ☐ |
| W6-4 | Projects + BOQ adjacency (`projects`, subcontracting) | 61 + 90 | Project/BOQ desk (construction primary flow) | P2 | ☐ |
| W6-5 | Setup/admin (`setup`, Settings) | 484 | System setup only | P3 | ☐ |
| W6-6 | Manufacturing, assets, CRM, support, EDI remaining | 481 + 220 + 91 + 31 + 26 | Deferred flows | P3 | ☐ |
| W6-7 | Frappe framework UI remainder (frappe_ar_missing_review) | per frappe file | Framework interfaces | P2 | ☐ |

Notes:
1. Rows above are *candidate strings within area*, not commitments; the
   per-batch exact list is cut from the referenced CSVs once a batch has
   owner approval.
2. Batch W6-1 doubles as the pad under the Stage-7 report/print pilot
   (Trial Balance + General Ledger + one aging) so the report UI layer is
   not half-English.
3. Every batch follows the same governed review machine used by Stage 1C/4
   (proposal → independent A1/A2/A3 quorum → AI-R bundle verify → DRY_RUN →
   IMPORT on the test site), and each catalog batch ends with one evidence
   re-pin.

## Owner decisions recorded so far (2026-09-20/21)

1. Stage 2 evidence re-pin: **executed once** (commit `baa1057`); next re-pin
   is deferred until the first approved Stage 6/7 catalog change.
2. Registry: Cost Center / Warehouse / Project added as **`planned` only**
   (identity sections + trees disabled; Project does not inherit
   Account-style tree semantics).
3. Report/print pilot scope (Stage 7, in principle): **Trial Balance,
   General Ledger, ONE aging report first, ONE BOQ print/export**; AR Aging
   and AP Aging are separate reports — include only one of them in the
   first pilot pass.
4. Stage 8: fully deferred until Stages 6–7 pass; no production mutation.
