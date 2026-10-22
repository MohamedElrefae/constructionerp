# Stage 6 — W6-1 Accounting report-supporting subset proposal (2026-09-21)

**Status: PROPOSAL — owner approval of this exact subset begins the governed W6-1 cycle.**
Subsets of broader batches remain deferred; no translations committed; no runtime import.

## Scope honored from owner decision (2026-09-21)

Only the strings that directly support the report/print pilot surfaces are in this subset:

| Screen group | Basis (vendor locations) | Unique strings |
|---|---|---|
| Journal Entry | `journal_entry/*` | 37 |
| Payment Entry | `payment_entry/*` | 56 |
| General Ledger detail (report UI + validation) | `general_ledger*` | 33 |
| Trial Balance report UI | `trial_balance*` | 9 |
| **One aging report: Accounts Receivable** | `accounts_receivable*` (aging buckets included) | 19 |
| Invoice/print-status surfaces | tokens within the included rows | included above |

**Total: 147 unique msgid rows** — exact rows persisted in
`docs/translation/stage6_w61_accounting_subset_rows_2026-09-21.csv` (kept in
repository with original locations/notes; no runtime import yet).

AP Aging (Accounts Payable) remains a separate decision, per owner rule.

## Readiness split inside the subset

- **77 rows** already carry a reviewed Arabic proposal (`msgstr` non-empty
  with reviewer attribution from the 2026-08 ledger round) — they go
  straight to the quorum recording (A1/A2/A3 confirm or exception) on
  approval.
- **70 rows** have no approved Arabic yet — they are the AI-proposal work
  for the quorum panel; proposals are drafted at review time, not before.

## Governed cycle after your approval (test site)

1. AI proposal for the 70 unapproved rows (records drafted per glossary).
2. Independent AI-A1/A2/A3 quorum in separate recorded review passes on all
   147 rows, with dispositions for every item.
3. AI-R verifies the exact bundle and payload hash.
4. `import_released_overrides(dry_run=True)` DRY_RUN — expected drift 0
   against payload; then `dry_run=False` IMPORT on the test site.
5. Live readback + browser evidence on one `ar` session (same headless
   method as Stage 4).
6. One evidence re-pin closes the batch (the "evidence-index-head" staleness
   brought by each subsequent commit resets then).

## Owner mark-up requested

- [ ] Approve the 147-row W6-1 subset (this file + rows CSV) for the cycle.
- [ ] Confirm AR Aging (not AP) as the pilot's single aging report.
- [ ] Any direct owner-mandated term changes inside these rows.
