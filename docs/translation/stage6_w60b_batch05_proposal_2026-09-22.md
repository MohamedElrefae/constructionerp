# Stage 6 — W6-0b **batch 5** proposal (2026-09-22)

**Status: PROPOSAL for owner approval of this exact batch only — no quorum, no import, no other batch, no production, no Stage-8.**

Batch 4 is closed (owner acceptance, same day): governance, import, UAT,
browser, and evidence gates passed (`396ae87`). This note presents **batch 5
only** for the next approval gate.

## Batch 5 — exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w60b_batch05_rows_2026-09-22.csv` |
| Rows | **270** translation-candidates (all `app=frappe`, `length ≤ 25`) |
| sha256 | `56f6432688d902fe8de5d2d2dfdccc501a36d78ec6534973c1f9cede3ad43544` |
| Priority basis | Next deterministic slice of the ranked short-UI plan (tier 2 after batches 1–4 consumed prior slices) |
| Batch index | `05` of `07` in `stage6_w60b_batch_plan_2026-09-22.csv` (sha256 `12625007de564d363fc88842c5af3ef8cc7325bc0aec56bc513acecc9a65a97d`) |

Composition (classification unchanged from the plan):

| Attribute | Value |
|---|---|
| Tier | **270 × tier 2** (high desk-surface use; no remaining tier 0 accounting / tier 1 core chrome) |
| Accounting workflow flag | 0 |
| Placeholder rows (`{…}`) | **8** |
| Overlap with released catalog (`approved_ar_overrides.csv`, 1,439 rows) | **0** |
| Overlap with batch 1 | **0** |
| Overlap with batch 2 | **0** |
| Overlap with batch 3 | **0** |
| Overlap with batch 4 | **0** |
| Overlap with 21 technical exclusions | **0** |

Placeholder rows (8 — format tokens retained as-is at import time):

`Please select {0}`, `Row {0}`, `Sync {0} Fields`, `Unsupported {0}: {1}`,
`User {0} is disabled`, `Welcome to {0}`, `'{0}' is not a valid IBAN`,
`'{0}' is not a valid URL`.

Sample rows (not exhaustive): OAuth/OTP/auth short UI (`OAuth Client Role`,
`OAuth Error`, `OAuth Scope`, `OTP SMS Template`, `OpenID Configuration`,
`Password Email Sent`, `Show footer on login`), permissions and validation
(`Permission Inspector`, `Permission Levels`, `Permissions Error`,
`Not a valid user`, `Not Nullable`), email/job/pending state (`Pending Emails`,
`Pending Jobs`, `Pull Emails`, `Sender Email`, `Unhandled Emails`,
`Partial Success`), workflow/sync controls (`Select Workflow`,
`Sync {0} Fields`, `Workflow Builder ID`, `Transition Tasks`), time/relative
labels (`1 day ago`, `2 hours ago`, `2 weeks ago`).

## Documented technical exclusions (not translated)

| File | Rows | sha256 |
|---|---|---|
| `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` | **21** | `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` |

Same 21 `EXCEPTION-technical` rows from the original W6-0b cut
(symbols-only, HTML tag, newline, or JS `${…}`) — **keep vendor rendering;
no translation**. They are outside the 1,894 translation-candidates and
outside every batch CSV; retained as documented exclusions for AI-R
suppress-check whenever a batch cycle runs. Batch 5 has **0 overlap** with them.

Prior-approved a1/a2 exclusions (302 rows) remain outside the 1,894
candidates entirely (`stage6_w60b_dedup_exclusions_2026-09-22.csv`,
sha256 `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b`).

### Batch-5 source tokens flagged for quorum (not pre-excluded)

A subset of batch 5 consists of technical, acronym, or code tokens that may become
source-equal / `EXCEPTION-technical` **at quorum time** if Arabic is not appropriate
(retained in the scope CSV so the owner has full visibility):
e.g. `OAuth Client Role`, `OAuth Scope`, `OpenID Configuration`, `OTP SMS Template`,
`Not Nullable`, `Section ID`, `Payload Count`, and similar.
The disposition decision stays with the A1/A2/A3 panel + AI-R after approval —
this proposal does **not** move them out of scope unilaterally.

### Site-override reconciliation note (plan §12)

Live test-site probe will detect any existing `ar` Translation rows whose
`source_text` matches a batch-5 key with non-empty text. Those will be reconciled
at cycle time same as batches 1–4 (preserve genuine site overrides; import only genuine
state changes). **No rows are pre-removed from the 270-row CSV.**

## Remaining plan (not for approval now)

| Batch | Rows | Status |
|---|---:|---|
| 01 | 271 | **closed** (owner-accepted, `55006db`) |
| 02 | 271 | **closed** (owner-accepted, `ba66a80`) |
| 03 | 271 | **closed** (owner-accepted, `6cbd6c6`, `d0f9c5d`) |
| 04 | 271 | **closed** (owner-accepted, `396ae87`) |
| **05** | **270** | **presented for approval** |
| 06 | 270 | deferred — no approval requested |
| 07 | 270 | deferred |
| **Σ remaining after 04** | **810** | every candidate in exactly one batch |

## Boundary

- Proposal-only: approving batch 5 authorizes **only** the 270-row CSV above
  (sha256 above) to enter the governed cycle (AI proposal → quorum → AI-R →
  DRY_RUN → IMPORT → browser evidence → re-pin) **on the test site** when you
  say go.
- **No** AI proposal panel, quorum, import, catalog change, production
  mutation, Stage-8 work, or batches 06–07 is started by this note.
- Expanding batch 5 beyond 270 rows requires a new exact CSV + sha.

## Owner mark-up requested

- [ ] **Approve batch 5 only** — the 270-row CSV (sha256 above) as the exact
      W6-0b batch-5 translation scope.
- [ ] Acknowledge the shared 21 technical rows as permanent non-translation
      exclusions for W6-0b (unchanged from batches 1–4).
- [ ] Leave batches 06–07 unapproved until a later proposal.
- [ ] Any direct term overrides for batch-5 strings → terminology sheet before
      a future quorum panel.
