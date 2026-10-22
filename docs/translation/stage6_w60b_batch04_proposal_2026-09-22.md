# Stage 6 — W6-0b **batch 4** proposal (2026-09-22)

**Status: PROPOSAL for owner approval of this exact batch only — no quorum, no import, no other batch, no production, no Stage-8.**

Batch 3 is closed (owner acceptance, same day): governance, import, UAT,
browser, and evidence gates passed (`6cbd6c6`, `d0f9c5d`). This note presents **batch 4
only** for the next approval gate.

## Batch 4 — exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w60b_batch04_rows_2026-09-22.csv` |
| Rows | **271** translation-candidates (all `app=frappe`, `length ≤ 40`) |
| sha256 | `21dcdd54164c5086b84ecd1e2c87979d6c1436fa663efced949b1fea573bad64` |
| Priority basis | Next deterministic slice of the ranked short-UI plan (tier 2 after batches 1–3 consumed prior slices) |
| Batch index | `04` of `07` in `stage6_w60b_batch_plan_2026-09-22.csv` (sha256 `12625007de564d363fc88842c5af3ef8cc7325bc0aec56bc513acecc9a65a97d`) |

Composition (classification unchanged from the plan):

| Attribute | Value |
|---|---|
| Tier | **271 × tier 2** (high desk-surface use; no remaining tier 0 accounting / tier 1 core chrome) |
| Accounting workflow flag | 0 |
| Placeholder rows (`{…}`) | 7 |
| Overlap with released catalog (`approved_ar_overrides.csv`, 1,183 rows) | **0** |
| Overlap with batch 1 | **0** |
| Overlap with batch 2 | **0** |
| Overlap with batch 3 | **0** |

Sample rows (not exhaustive): client/auth UI tokens (`Client Id`, `Client URI`, `Client script`,
`Code Challenge`, `Click here`, `Click to Set Filters`, `Child Doctype`), form controls and alerts
(`Compact view`, `Compress HTML`, `Condition`, `Configuration`, `Configure columns`, `Connection`,
`Contains`, `Context`, `Continue`, `Continuous`), data/document controls (`Copy link`, `Count`,
`Create`, `Created At`, `Creation`, `Current`, `Custom`).

## Documented technical exclusions (not translated)

| File | Rows | sha256 |
|---|---|---|
| `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` | **21** | `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` |

Same 21 `EXCEPTION-technical` rows from the original W6-0b cut
(symbols-only, HTML tag, newline, or JS `${…}`) — **keep vendor rendering;
no translation**. They are outside the 1,894 translation-candidates and
outside every batch CSV; retained as documented exclusions for AI-R
suppress-check whenever a batch cycle runs.

Prior-approved a1/a2 exclusions (302 rows) remain outside the 1,894
candidates entirely (`stage6_w60b_dedup_exclusions_2026-09-22.csv`).

### Batch-4 source tokens flagged for quorum (not pre-excluded)

A subset of batch 4 consists of technical, acronym, or code tokens that may become
source-equal / `EXCEPTION-technical` **at quorum time** if Arabic is not appropriate
(retained in the scope CSV so the owner has full visibility):
e.g. `Client Id`, `Client URI`, `CSS`, `Code Challenge`, `CRON`, `DocType`, and similar.
The disposition decision stays with the A1/A2/A3 panel + AI-R after approval —
this proposal does **not** move them out of scope unilaterally.

### Site-override reconciliation note (plan §12)

Live test-site probe will detect any existing `ar` Translation rows whose
`source_text` matches a batch-4 key with non-empty text. Those will be reconciled
at cycle time same as batches 1–3 (preserve genuine site overrides; import only genuine
state changes). **No rows are pre-removed from the 271-row CSV.**

## Remaining plan (not for approval now)

| Batch | Rows | Status |
|---|---:|---|
| 01 | 271 | **closed** (owner-accepted, `55006db`) |
| 02 | 271 | **closed** (owner-accepted, `ba66a80`) |
| 03 | 271 | **closed** (owner-accepted, `6cbd6c6`, `d0f9c5d`) |
| **04** | **271** | **presented for approval** |
| 05 | 270 | deferred — no approval requested |
| 06 | 270 | deferred |
| 07 | 270 | deferred |
| **Σ remaining after 03** | **1,081** | every candidate in exactly one batch |

## Boundary

- Proposal-only: approving batch 4 authorizes **only** the 271-row CSV above
  (sha256 above) to enter the governed cycle (AI proposal → quorum → AI-R →
  DRY_RUN → IMPORT → browser evidence → re-pin) **on the test site** when you
  say go.
- **No** AI proposal panel, quorum, import, catalog change, production
  mutation, Stage-8 work, or batches 05–07 is started by this note.
- Expanding batch 4 beyond 271 rows requires a new exact CSV + sha.

## Owner mark-up requested

- [ ] **Approve batch 4 only** — the 271-row CSV (sha256 above) as the exact
      W6-0b batch-4 translation scope.
- [ ] Acknowledge the shared 21 technical rows as permanent non-translation
      exclusions for W6-0b (unchanged from batches 1–3).
- [ ] Leave batches 05–07 unapproved until a later proposal.
- [ ] Any direct term overrides for batch-4 strings → terminology sheet before
      a future quorum panel.
