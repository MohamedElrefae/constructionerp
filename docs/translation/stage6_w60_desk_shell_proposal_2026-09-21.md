# Stage 6 — W6-0 desk-shell file-list proposal (2026-09-21)

**Status: PROPOSAL for owner mark-up — no translations, no runtime import.**

Basis: vendor gap ledger (`docs/arabic_coverage_gap_report_2026-08-22.csv`,
2,861 frappe rows; the vendor-side `.po` for frappe is clean upstream, so the
W6-0 batch must carry Construction-owned overrides rather than vendor file
edits). Exact msgid rows are cut from this CSV under the machine-checkable
filters below; nothing ships without your per-batch approval.

## Proposed cut (candidate counts from the live ledger)

| Candidate set (filter description) | msgid count | Content | Proposed priority | Owner decision |
|---|---|---|---|---|
| W6-0a — Desk verbs/nouns core (Filter/Save/Submit/Cancel/Delete/New/Export/Refresh/Sort/Search/Print/Edit/Assign etc.) | 362 | everyday desk actions across list/menu/toolbars | P1 | ☐ |
| W6-0b — Short UI strings ≤40 chars (labels, tooltips, menu captions) | (subset of 2,140; cut after dictionary/dedup against a1/a2 glossary) | nav + forms + dashboard labels | P2 | ☐ |
| W6-0c — plural/long/dynamic templates (message formats, errors) | remainder of the 2,861 | dialogs/error surfaces | P3 (defer early) | ☐ |

Notes:
1. The 6 Stage-1C labels + the 34-row released payload already cover the
   initial desktop/workspace surface — W6-0 does not duplicate those rows.
2. W6-0a's 362 rows need decomposition before quorum (some appear as
   system/technical strings that must be disposition-exceptions instead
   of translations). The per-batch exact CSV follows your W6-0 approval,
   with the same governed cycle as W6-1
   (proposal → quorum → AI-R → DRY_RUN → IMPORT → browser evidence → re-pin).
3. All runs keep the Stage-2 contract cadence: each catalog batch closes
   with one evidence re-pin.
4. Every batch ends in a governed dry-run gate expecting zero-drift; rows
   already satisfied live as site overrides are excluded from the payload
   per §12.

## Owner mark-up requested

- [ ] Approve W6-0a as the next batch (exact CSV cut on approval).
- [ ] Adjust scope/priority of W6-0b/c.
- [ ] Confirm the desk-shell black-box term choices within the batch (any
      direct overrides go in the terminology sheet before the panel runs).
