# Stage 6 — W6-0b **batch 7** proposal (2026-09-22)

**Status: PROPOSAL for owner approval of this exact batch only — no quorum, no import, no other batch, no production, no Stage-8.**

Batch 6 is closed (owner acceptance, same day): governance, import, UAT,
browser, and evidence gates passed (`3c25b25`). This note
presents **batch 7 only** for the next approval gate.

## Batch 7 — exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w60b_batch07_rows_2026-09-22.csv` |
| Rows | **270** translation-candidates (all `app=frappe`, `classification=translation-candidate`) |
| sha256 | `1716d01c20129b86d629034d2c826a17a3029feb44b7006e1e19b7faa9bc76d4` |
| Priority basis | Final deterministic slice of the ranked short-UI plan (tier 2 after batches 1–6 consumed prior slices) |
| Batch index | `07` of `07` in `stage6_w60b_batch_plan_2026-09-22.csv` (sha256 `12625007de564d363fc88842c5af3ef8cc7325bc0aec56bc513acecc9a65a97d`) |

Composition (classification unchanged from the plan):

| Attribute | Value |
|---|---|
| Tier | **270 × tier 2** (high desk-surface use; no remaining tier 0 accounting / tier 1 core chrome) |
| Accounting workflow flag | 0 |
| `length` range | 3–40 (166 rows ≤ 25; 104 rows 26–40) |
| Placeholder rows (`{…}` / `{}` / `{e}`) | **53** (format tokens retained as-is at import time) |
| Overlap with released catalog (`approved_ar_overrides.csv`, 1,949 rows) | **0** |
| Overlap with batch 1 | **0** |
| Overlap with batch 2 | **0** |
| Overlap with batch 3 | **0** |
| Overlap with batch 4 | **0** |
| Overlap with batch 5 | **0** |
| Overlap with batch 6 | **0** |
| Overlap with 21 technical exclusions | **0** |

Placeholder rows (53 — format tokens retained as-is at import time), including:
`Not Permitted to read {0}`, `OTP Secret Reset - {0}`, `Parentfield not specified in {0}: {1}`,
`Password not found for {0} {1} {2}`, `Patch type {} not found in patches.txt`,
`Path {0} is not within module {1}`, `Path {0} it not a valid path`,
`Please enable {} before continuing.`, `Please update {} before continuing.`,
`Queuing {0} for Submission`, `Row #{}: Fieldname is required`,
`Series Updated for {}`, `Skipping {0} of {1}, {2}`,
`Snippet and more variables:  {0}`, `Successfully imported {0}`,
`Successfully updated {0}`, `The Condition '{0}' is invalid`,
`The field {0} is mandatory`, `The role {0} should be a custom role.`,
`The selected document {0} is not a {1}.`, `There is no task called \"{}\"`,
`To enable server scripts, read the {0}.`, `To generate password click {0}`,
`To know more click {0}`, `Un-following document {0}`,
plus remaining `{N}`/`{}` validation and file-error templates (full set in CSV).

Sample rows (not exhaustive): file/import/validation errors
(`Patch type {} not found in patches.txt`, `Row #{}: Fieldname is required`,
`Parentfield not specified in {0}: {1}`, `Path {0} is not within module {1}`),
permissions/admin UI (`OAuth`, `Occurrences`, `OpenLDAP`, `Outgoing`,
`Outlook.com`, `PATCH`, `PID`, `PUT`, `Packages`, `Parameter`),
log/retention labels (`Offset must be a non-negative integer`,
`Official Documentation`, `Order By must be a string`),
relative/notifications (`Skipping {0} of {1}, {2}`,
`Successfully imported {0}`, `Successfully updated {0}`),
licensed/geographic terms (`GNU General Public License`, `Nomatim`, `City`).

### Site-override / catalog note (plan §12)

No batch-7 keys carry a non-empty `suggested_ar` in the plan. The live
test-site probe at cycle time will detect any existing `ar` Translation rows
whose `source_text` matches a batch-7 key with non-empty text. Those will be
reconciled at cycle time same as batches 1–6 (preserve genuine site overrides;
import only genuine state changes). **No rows are pre-removed from the
270-row CSV.**

## Documented technical exclusions (not translated)

| File | Rows | sha256 |
|---|---|---|
| `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` | **21** | `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` |

Same 21 `EXCEPTION-technical` rows from the original W6-0b cut
(symbols-only, HTML tag, newline, or JS `${…}`) — **keep vendor rendering;
no translation**. They are outside the 1,894 translation-candidates and
outside every batch CSV; retained as documented exclusions for AI-R
suppress-check whenever a batch cycle runs. Batch 7 has **0 overlap** with them.

Prior-approved a1/a2 exclusions (302 rows) remain outside the 1,894
candidates entirely (`stage6_w60b_dedup_exclusions_2026-09-22.csv`,
sha256 `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b`).

### Batch-7 source tokens flagged for quorum (not pre-excluded)

A subset of batch 7 consists of technical, acronym, or code tokens that may become
source-equal / `EXCEPTION-technical` **at quorum time** if Arabic is not appropriate
(retained in the scope CSV so the owner has full visibility):
e.g. `OAuth`, `Occurrences`, `OpenLDAP`, `Outgoing`, `Outlook.com`,
`PATCH`, `PID`, `PUT`, `Packages`, `Parameter`, `Pass`, `Polling`,
`Proceed`, `Prof`, `Profile`, `Purple`, `Queue`, `Queue(s)`, `Queues`,
`Range`, `Readme`, `Reason`, `Redirects`, `Release`, `Reminder`.
The disposition decision stays with the A1/A2/A3 panel + AI-R after approval —
this proposal does **not** move them out of scope unilaterally.

## Remaining plan (not for approval now)

| Batch | Rows | Status |
|---|---:|---|
| 01 | 271 | **closed** (owner-accepted, `55006db`) |
| 02 | 271 | **closed** (owner-accepted, `ba66a80`) |
| 03 | 271 | **closed** (owner-accepted, `6cbd6c6`, `d0f9c5d`) |
| 04 | 271 | **closed** (owner-accepted, `396ae87`) |
| 05 | 270 | **closed** (owner-accepted, `d26ed54`) |
| 06 | 270 | **closed** (owner-accepted, `3c25b25`) |
| **07** | **270** | **presented for approval** |
| **Σ remaining after 06** | **270** | every candidate in exactly one batch |

## Boundary

- Proposal-only: approving batch 7 authorizes **only** the 270-row CSV above
  (sha256 above) to enter the governed cycle (AI proposal → quorum → AI-R →
  DRY_RUN → IMPORT → browser evidence → re-pin) **on the test site** when you
  say go.
- **No** AI proposal panel, quorum, import, catalog change, production
  mutation, Stage-8 work, or further batches is started by this note.
- Expanding batch 7 beyond 270 rows requires a new exact CSV + sha.

## Owner mark-up requested

- [ ] **Approve batch 7 only** — the 270-row CSV (sha256 above) as the exact
      W6-0b batch-7 translation scope.
- [ ] Acknowledge the shared 21 technical rows as permanent non-translation
      exclusions for W6-0b (unchanged from batches 1–6).
- [ ] Leave any further batches unapproved until a later proposal.
- [ ] Any direct term overrides for batch-7 strings → terminology sheet before
      a future quorum panel.