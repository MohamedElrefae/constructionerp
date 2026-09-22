# Stage 6 — W6-0b **batch 3** proposal (2026-09-22)

**Status: PROPOSAL for owner approval of this exact batch only — no quorum, no import, no other batch, no production, no Stage-8.**

Batch 2 is closed (owner acceptance, same day): governance, import, UAT,
browser, and evidence gates passed (`ba66a80`). This note presents **batch 3
only** for the next approval gate.

## Batch 3 — exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w60b_batch03_rows_2026-09-22.csv` |
| Rows | **271** translation-candidates (all `app=frappe`, `length ≤ 40`) |
| sha256 | `21ac507ede96f72e86e4825aca1a6888a5b38ca56ffed7c35682b16dc475a89a` |
| Priority basis | Next deterministic slice of the ranked short-UI plan (tier 2 after batches 1–2 consumed prior tier-2 slices) |
| Batch index | `03` of `07` in `stage6_w60b_batch_plan_2026-09-22.csv` (sha256 `12625007de564d363fc88842c5af3ef8cc7325bc0aec56bc513acecc9a65a97d`) |

Composition (classification unchanged from the plan):

| Attribute | Value |
|---|---|
| Tier | **271 × tier 2** (high desk-surface use; no remaining tier 0 accounting / tier 1 core chrome) |
| Accounting workflow flag | 0 |
| Placeholder rows (`{…}`) | 64 |
| Overlap with released catalog (`approved_ar_overrides.csv`) | **0** |
| Overlap with batch 1 | **0** |
| Overlap with batch 2 | **0** |

Sample rows (not exhaustive): form/list navigation and feedback
(`Move cursor to above row`, `Navigate to main content`,
`Showing only first {0} rows out of {1}`, `You changed the value of {0}`),
login/portal/auth short UI (`Invalid Login. Try again.`,
`Passwords do not match`, `Your verification code is {0}`,
`Login with {0}`), workspace/settings labels (`Workspace Settings`,
`Default Workspace`, `API Logging`, `Amended From`), color/format tokens
(`Orange`, `Pink`, `Red`, `Yellow`, `Arial`, `UUID`).

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

### Batch-3 source tokens flagged for quorum (not pre-excluded)

A prefix of batch 3 is short format/code/config tokens that may become
source-equal / EXCEPTION-technical **at quorum time** if Arabic is not
appropriate (still listed in the scope CSV so the owner sees them):
`OR`, `UUID`, `nonce`, `on_submit`, `CMD`, `Config`, `Arial`, `Re:`,
`Timeout`, `Package`, `Portal`, `Partial`, `Hello`, `Dear`, `Thanks`, and
similar. Decision stays with the A1/A2/A3 panel + AI-R after approval —
this proposal does **not** move them out of scope unilaterally.

### Site-override reconciliation note (plan §12)

Live test-site probe may find existing `ar` Translation rows whose
`source_text` matches (or case-matches) a batch-3 key with non-empty text.
Those will be reconciled at cycle time same as batches 1–2 (preserve
equivalent site overrides; import only genuine state changes). **No rows are
pre-removed from the 271-row CSV.**

## Remaining plan (not for approval now)

| Batch | Rows | Status |
|---|---:|---|
| 01 | 271 | **closed** (owner-accepted, `55006db`) |
| 02 | 271 | **closed** (owner-accepted, `ba66a80`) |
| **03** | **271** | **presented for approval** |
| 04 | 271 | deferred — no approval requested |
| 05 | 270 | deferred |
| 06 | 270 | deferred |
| 07 | 270 | deferred |
| **Σ remaining after 02** | **1,352** | every candidate in exactly one batch |

## Boundary

- Proposal-only: approving batch 3 authorizes **only** the 271-row CSV above
  (sha256 above) to enter the governed cycle (AI proposal → quorum → AI-R →
  DRY_RUN → IMPORT → browser evidence → re-pin) **on the test site** when you
  say go.
- **No** AI proposal panel, quorum, import, catalog change, production
  mutation, Stage-8 work, or batches 04–07 is started by this note.
- Expanding batch 3 beyond 271 rows requires a new exact CSV + sha.

## Owner mark-up requested

- [ ] **Approve batch 3 only** — the 271-row CSV (sha256 above) as the exact
      W6-0b batch-3 translation scope.
- [ ] Acknowledge the shared 21 technical rows as permanent non-translation
      exclusions for W6-0b (unchanged from batches 1–2).
- [ ] Leave batches 04–07 unapproved until a later proposal.
- [ ] Any direct term overrides for batch-3 strings → terminology sheet before
      a future quorum panel.
