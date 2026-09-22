# Stage 6 — W6-0b **batch 6** proposal (2026-09-22)

**Status: PROPOSAL for owner approval of this exact batch only — no quorum, no import, no other batch, no production, no Stage-8.**

Batch 5 is closed (owner acceptance, same day): governance, import, UAT,
browser, and evidence gates passed (`ddb6f3f`, cycle `d26ed54`). This note
presents **batch 6 only** for the next approval gate.

## Batch 6 — exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w60b_batch06_rows_2026-09-22.csv` |
| Rows | **270** translation-candidates (all `app=frappe`, `classification=translation-candidate`) |
| sha256 | `68500fae981aacec08e9841fc858dfd43e7473c7b12156ac8ca528b678d309e0` |
| Priority basis | Next deterministic slice of the ranked short-UI plan (tier 2 after batches 1–5 consumed prior slices) |
| Batch index | `06` of `07` in `stage6_w60b_batch_plan_2026-09-22.csv` (sha256 `12625007de564d363fc88842c5af3ef8cc7325bc0aec56bc513acecc9a65a97d`) |

Composition (classification unchanged from the plan):

| Attribute | Value |
|---|---|
| Tier | **270 × tier 2** (high desk-surface use; no remaining tier 0 accounting / tier 1 core chrome) |
| Accounting workflow flag | 0 |
| `length` range | 2–40 (129 rows ≤ 25; 141 rows 26–40) |
| Placeholder rows (`{…}` / `{}` / `{e}`) | **54** (format tokens retained as-is at import time) |
| Overlap with released catalog (`approved_ar_overrides.csv`, 1,691 rows) | **0** |
| Overlap with batch 1 | **0** |
| Overlap with batch 2 | **0** |
| Overlap with batch 3 | **0** |
| Overlap with batch 4 | **0** |
| Overlap with batch 5 | **0** |
| Overlap with 21 technical exclusions | **0** |

Placeholder rows (54 — format tokens retained as-is at import time), including:
`About {0} minute remaining`, `About {0} minutes remaining`,
`About {0} seconds remaining`, `Added default log doctypes: {}`,
`App not found for module: {0}`, `Assignment of {0} removed by {1}`,
`Bulk {0} is enqueued in background.`, `Cannot access file path {0}`,
`Cannot find file {} on disk`, `Cannot use {0} in order/group by`,
`Contains {0} security fix(es)`, `DocType {0} does not exist.`,
`Document {0} {1} does not exist`, `Email Account {0} Disabled`,
`Error connecting via IMAP/POP3: {e}`, `Error connecting via SMTP: {e}`,
`Failed while calling API {0}`, `Fetching fields from {0}...`,
`Field {0} does not exist on {1}`, `Importing {0} of {1}, {2}`,
plus remaining `{N}`/`{}` validation and file-error templates (full set in CSV).

Sample rows (not exhaustive): file/import/validation errors
(`Cannot find file {} on disk`, `Importing {0} is not allowed.`,
`Document Name must be a string`, `Invalid characters in table name: {0}`),
API/OAuth short UI (`API Key cannot be regenerated`,
`Auth URL data should be valid JSON`, `Frappe Mail OAuth Error`),
permissions and admin constraints (`Amendment Not Allowed`,
`Cannot edit Standard Dashboards`, `Function {0} is not whitelisted.`),
log/retention labels (`Clear Logs After (days)`, `Console Logs can not be deleted`,
`Failing Scheduled Jobs (last 7 days)`), relative time
(`2 years ago`, `3 minutes ago`, `5 days ago`), licensed/geographic terms
(`GNU General Public License`, `Nomatim`, `City`).

### Site-override / catalog note (plan §12)

`City` carries plan `suggested_ar=المدينة` but is **not** pre-applied here;
the live test-site probe at cycle time will detect any existing `ar`
Translation rows whose `source_text` matches a batch-6 key with non-empty text.
Those will be reconciled at cycle time same as batches 1–5 (preserve genuine
site overrides; import only genuine state changes). **No rows are pre-removed
from the 270-row CSV.**

## Documented technical exclusions (not translated)

| File | Rows | sha256 |
|---|---|---|
| `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` | **21** | `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` |

Same 21 `EXCEPTION-technical` rows from the original W6-0b cut
(symbols-only, HTML tag, newline, or JS `${…}`) — **keep vendor rendering;
no translation**. They are outside the 1,894 translation-candidates and
outside every batch CSV; retained as documented exclusions for AI-R
suppress-check whenever a batch cycle runs. Batch 6 has **0 overlap** with them.

Prior-approved a1/a2 exclusions (302 rows) remain outside the 1,894
candidates entirely (`stage6_w60b_dedup_exclusions_2026-09-22.csv`,
sha256 `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b`).

### Batch-6 source tokens flagged for quorum (not pre-excluded)

A subset of batch 6 consists of technical, acronym, or code tokens that may become
source-equal / `EXCEPTION-technical` **at quorum time** if Arabic is not appropriate
(retained in the scope CSV so the owner has full visibility):
e.g. `API Endpoint Args should be valid JSON`, `API Key cannot be regenerated`,
`Auth URL data should be valid JSON`, `Failed while calling API {0}`,
`Frappe Mail OAuth Error`, `Go to this URL after completing the form`.
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
| **06** | **270** | **presented for approval** |
| 07 | 270 | deferred — no approval requested |
| **Σ remaining after 05** | **540** | every candidate in exactly one batch |

## Boundary

- Proposal-only: approving batch 6 authorizes **only** the 270-row CSV above
  (sha256 above) to enter the governed cycle (AI proposal → quorum → AI-R →
  DRY_RUN → IMPORT → browser evidence → re-pin) **on the test site** when you
  say go.
- **No** AI proposal panel, quorum, import, catalog change, production
  mutation, Stage-8 work, or batch 07 is started by this note.
- Expanding batch 6 beyond 270 rows requires a new exact CSV + sha.

## Owner mark-up requested

- [ ] **Approve batch 6 only** — the 270-row CSV (sha256 above) as the exact
      W6-0b batch-6 translation scope.
- [ ] Acknowledge the shared 21 technical rows as permanent non-translation
      exclusions for W6-0b (unchanged from batches 1–5).
- [ ] Leave batch 07 unapproved until a later proposal.
- [ ] Any direct term overrides for batch-6 strings → terminology sheet before
      a future quorum panel.
