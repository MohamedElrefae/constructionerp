# Stage 6 — W6-0b **batch 2** proposal (2026-09-22)

**Status: PROPOSAL for owner approval of this exact batch only — no quorum, no import, no other batch, no production, no Stage-8.**

Batch 1 is closed (owner acceptance, same day): governance, import, UAT,
browser, and evidence gates passed (`55006db`). This note presents **batch 2
only** for the next approval gate.

## Batch 2 — exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w60b_batch02_rows_2026-09-22.csv` |
| Rows | **271** translation-candidates (all `app=frappe`, `length ≤ 40`) |
| sha256 | `187361ab36ea2ab75f32355bce0b2b1c274b52bebd339b0c19ea3822436895db` |
| Priority basis | Next deterministic slice of the ranked short-UI plan (tier 2 after batch 1 consumed tier 0–1 + top tier-2) |
| Batch index | `02` of `07` in `stage6_w60b_batch_plan_2026-09-22.csv` (sha256 `12625007de564d363fc88842c5af3ef8cc7325bc0aec56bc513acecc9a65a97d`) |

Composition (classification unchanged from the plan):

| Attribute | Value |
|---|---|
| Tier | **271 × tier 2** (high desk-surface use; no remaining tier 0 accounting / tier 1 core chrome) |
| Accounting workflow flag | 0 |
| Placeholder rows (`{…}`) | 25 |
| Overlap with released catalog (`approved_ar_overrides.csv`) | **0** |
| Overlap with batch 1 | **0** |

Sample rows (not exhaustive): validation/help short UI
(`Column width cannot be zero.`, `Both login and password required`,
`Mandatory fields required:`), relative-date filters
(`This Month`, `Last 30 Days`, `Next Quarter`), Desk/onboarding chrome
(`Apply Filters`, `Remind Me`, `Rebuild Tree`, `Undo last action`),
brand/format tokens (`Frappe Blog`, `Tabloid`, `Page Height (in mm)`).

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

### Batch-2 source tokens flagged for quorum (not pre-excluded)

A short prefix of batch 2 is format/code tokens that may become
source-equal / EXCEPTION-technical **at quorum time** if Arabic is not
appropriate (still listed in the scope CSV so the owner sees them):
`A7`–`A9`, `B0`–`B10`, `C5E`, `CSS`, `DLE`, `ESC`, `BCC`,
`SWATCHES`, `XMLHttpRequest Error`, and similar. Decision stays with the
A1/A2/A3 panel + AI-R after approval — this proposal does **not** move
them out of scope unilaterally.

### Site-override reconciliation note (plan §12)

Live test-site probe found a handful of existing `ar` Translation rows whose
`source_text` matches (or case-matches) a batch-2 key with non-empty text —
e.g. `Country` → `البلد`, `Reset to default` → `إعادة تعيين للافتراضي`,
`Not permitted` → `غير مسموح`. Those will be reconciled at cycle time
same as batch 1 (preserve equivalent site overrides; import only genuine
state changes). **No rows are pre-removed from the 271-row CSV.**

## Remaining plan (not for approval now)

| Batch | Rows | Status |
|---|---:|---|
| 01 | 271 | **closed** (owner-accepted, `55006db`) |
| **02** | **271** | **presented for approval** |
| 03 | 271 | deferred — no approval requested |
| 04 | 271 | deferred |
| 05 | 270 | deferred |
| 06 | 270 | deferred |
| 07 | 270 | deferred |
| **Σ remaining after 01** | **1,623** | every candidate in exactly one batch |

## Boundary

- Proposal-only: approving batch 2 authorizes **only** the 271-row CSV above
  (sha256 above) to enter the governed cycle (AI proposal → quorum → AI-R →
  DRY_RUN → IMPORT → browser evidence → re-pin) **on the test site** when you
  say go.
- **No** AI proposal panel, quorum, import, catalog change, production
  mutation, Stage-8 work, or batches 03–07 is started by this note.
- Expanding batch 2 beyond 271 rows requires a new exact CSV + sha.

## Owner mark-up requested

- [ ] **Approve batch 2 only** — the 271-row CSV (sha256 above) as the exact
      W6-0b batch-2 translation scope.
- [ ] Acknowledge the shared 21 technical rows as permanent non-translation
      exclusions for W6-0b (unchanged from batch 1).
- [ ] Leave batches 03–07 unapproved until a later proposal.
- [ ] Any direct term overrides for batch-2 strings → terminology sheet before
      a future quorum panel.
