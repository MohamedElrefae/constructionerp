# Stage 6 — W6-2 **Buying + Selling batch 02** proposal (2026-09-23)

**Status: PROPOSAL ONLY — owner mark-up pending. No quorum, no import, no catalog change, no evidence re-pin, no production, no Stage-8.**

W6-2 batch 01 is **closed** (owner-approved exact 270-row CSV sha
`b017df47…`, governed cycle complete on `v16.localhost`, commit `073458e`).
This note proposes the **next bounded** Stage 6 scope: matrix row **W6-2**
remainder only — batch 02.

Evidence re-pin is **deferred** to the next catalog cycle that actually
changes the packaged catalog (owner directive: re-pin rides that cycle).

## Exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w602_batch02_rows_2026-09-23.csv` |
| Rows | **48** translation-candidates |
| sha256 | `9a096273f2f7ef05a403edffbb4b75604b73ce7f854382c8fd570f5c329e44ce` |
| Source ledger | `docs/erpnext_ar_missing_review_filled.csv` (4,342 rows; W6-2 raw first-location = 143 buying + 194 selling = 337) |
| Matrix row | W6-2 in `stage6_workflow_matrix_proposal_2026-09-21.md` (remainder after batch 01) |
| Site (if approved to run) | `v16.localhost` test site only |

### Composition

| Attribute | Value |
|---|---|
| Area split | **0 buying** + **48 selling** |
| Pre-filled `msgstr` from vendor review ledger | **1** (`Address` → `العنوان`) |
| Unfilled (AI proposal required at cycle time) | **47** |
| Placeholder rows (`{…}`) | **17** |
| `length` range | 7–119 (all ≤ 120) |
| HTML/template rows | **0** (excluded by same cut rule as batch 01) |
| Overlap with released catalog (2,275) | **0** |
| Overlap with W6-2 batch 01 (270) | **0** |
| Overlap with all prior W6-0b batch rows / payloads / released lists (26 files) | **0** |
| Overlap with 21 technical exclusions | **0** |
| Overlap with 302 a1/a2 dedup exclusions | **0** |

### Cut rules (deterministic; same pipeline as batch 01)

1. Ledger rows with `skip` not yes; non-empty `msgid`.
2. First location path under `erpnext/buying/` or `erpnext/selling/`
   (yields raw 143 + 194 = 337 unique msgids after first-wins dedup).
3. Deduplicate by `msgid`.
4. Bound: `len(msgid) ≤ 120`; drop HTML/template (`<…>`).
5. Drop rows in technical exclusions, a1/a2 dedup exclusions, current
   released catalog, and any prior W6-0b scope/payload/released keys.
6. Subtract the exact batch-01 scope CSV (all 270 keys, including the two
   cycle-fix forms `' Address'` and `'Could not find path for '`).
7. Write CSV sorted by `area`, `source_text`.

CSV columns: `source_text,suggested_ar,locations,area,has_pre_filled`.

### Full W6-2 raw accounting (337 unique first-location msgids)

Mutually exclusive buckets (assignment priority: batch01 → batch02 → HTML →
`len>120` → tech → dedup → prior W6-0b → already-in-catalog). Each raw
msgid lands in **exactly one** row below:

| Bucket | Rows | In batch 02? |
|---|---:|---|
| Batch 01 scope keys present as exact ledger msgids | 268 | no — closed |
| Batch 02 candidates | **48** | **yes — this proposal** |
| HTML/template residual | 5 | **no — excluded** |
| `len > 120` residual (outside short-UI bound) | 15 | **no — excluded** |
| Already in released catalog (`Could not find path for` — fixed/released in batch-01 cycle) | 1 | **no — excluded** |
| Technical / dedup / prior-W6-0b residual (from this raw set) | 0 | — |
| **Total raw unique** | **337** | |

**Identity:** `268 + 48 + 21 = 337`, where residual exclusions
`21 = 5 HTML + 15 len>120 + 1 already-in-catalog`.

Batch-01 **scope CSV** has **270** keys, not 268:

`270 = 268 (in raw 337) + 2 synthetic cycle-fix forms` that are not exact
ledger msgids and therefore **outside** the 337: `' Address'` (leading
space) and `'Could not find path for '` (trailing space). Those two are
never double-counted into the raw total.

**Do not write** `337 = 270 + 48 + 20` (that is 338 and mixes the 270
scope-file size with the 268 raw membership). Correct forms:

- Raw universe: `337 = 268 + 48 + 21`
- Scope files: `270 (batch 01) + 48 (batch 02) + 21 residual − 2 synthetic outside raw − …` is **not** a raw identity; use the raw line above.

### Exclusion category overlap (clarified)

Independent flag checks on the raw 337 **before** priority assignment:

| Pair | Overlap rows | How counted in the table |
|---|---:|---|
| HTML **and** `len>120` | **3** | Once only — HTML bucket (HTML checked first) |
| Already-in-catalog **and** batch 01 | 85 | Once only — batch-01 bucket (batch 01 checked first; these are the 85 rows batch-01 released into the current catalog) |
| batch 01 **and** batch 02 | **0** | — |
| batch 02 **and** catalog / HTML / `len>120` / tech / dedup | **0** | — |
| tech / dedup / prior-W6-0b **and** batch 01 or batch 02 | **0** | — |

So the **listed exclusion counts 5 + 15 + 1 = 21 are already
non-overlapping** (mutually exclusive under the priority order). The raw
HTML∩`len>120` = 3 does not add a 4th residual row.

Synthetic batch-01 keys not present as exact ledger msgids (kept in batch 01
only; not in the 337): `' Address'`, `'Could not find path for '`.
`Advance Payment` is in the raw 337 and in batch 01 (was already-released
in the old catalog at `e522739` at proposal time — still counted once under
batch 01, not under the “already-in-catalog residual” bucket).

### Sample rows (not exhaustive)

Pre-filled:
`Address` → `العنوان`.

Unfilled (AI proposal at cycle time): POS lifecycle
(`POS has been closed at {0}. Please refresh the page.`, `POS invoice {0}
created successfully`), delivery-schedule validations, sales-opportunity
labels (`Sales Pipeline by Stage`, `Sales Opportunities by Campaign`),
subcontracting/hold labels, plus remaining Selling desk strings (full set
in CSV).

### Batch source tokens flagged for quorum (not pre-excluded)

Technical/identifier tokens retained in the scope CSV for full visibility;
disposition stays with A1/A2/A3 + AI-R after approval, e.g. `doctype`,
`doc_type`, `quotation_item`, `discount applied`, `{}  To Deliver`,
`Total Only`, `Sold by`, `Reason for hold:`. This proposal does **not**
move them out of scope unilaterally.

### Site-override / catalog note (plan §12)

At cycle time a live test-site probe will detect existing `ar` Translation
rows whose `source_text` matches a batch key with non-empty text. Genuine
site overrides are preserved; import only applies genuine state changes.
**No rows are pre-removed from the 48-row CSV.**

Note: batch 01’s Address strip-collision used the leading-space form
`' Address'` (preserved, not catalogued). Batch 02’s key is the exact
ledger msgid `Address` (7 chars, no leading space) — different key,
**0 overlap** with batch 01 and with the released catalog.

## Documented technical exclusions (unchanged, not in this batch)

| File | Rows | sha256 |
|---|---|---|
| `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` | **21** | `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` |

Shared W6-0b a1/a2 dedup exclusions (302) remain outside candidates
(`stage6_w60b_dedup_exclusions_2026-09-22.csv`,
sha256 `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b`).
**0 overlap** with either set.

## Remaining plan (not for approval now)

| Scope | Rows | Status |
|---|---:|---|
| W6-0b batches 01–07 (short-UI) | 1,894 | **closed** (batch 7 accepted `a0f01cb`) |
| W6-2 batch 01 (scope file) | 270 | **closed** (`073458e`) — of which **268** sit in the raw 337; **2** synthetic keys outside raw |
| **W6-2 batch 02 (this proposal)** | **48** | **presented for approval** |
| W6-2 residual exclusions (raw) | **21** | **5 HTML + 15 `len>120` + 1 already-released** — not proposed |
| W6-3 Stock | 789 raw / bounded TBD | not proposed |
| W6-4 Projects + BOQ | 61 + 90 | not proposed |
| W6-5 Setup | 484 | not proposed |
| W6-6 Deferred modules | ~849 | not proposed |
| W6-7 Frappe framework remainder | per frappe ledger | not proposed |

After batch 02, the W6-2 short-UI universe under these cut rules is
**exhausted**. Raw identity:

**`337 = 268 (batch 01 in raw) + 48 (batch 02) + 21 (residual exclusions)`**

with `21 = 5 + 15 + 1` (mutually exclusive buckets; HTML∩`len>120` = 3
already counted only under HTML). Batch-01 file size 270 = 268 + 2
synthetic keys outside the raw 337.

## Boundary

- Proposal-only: approving batch 02 authorizes **only** the 48-row CSV above
  (sha256 above) to enter the governed cycle (site recon → AI proposal →
  quorum → AI-R → DRY_RUN → IMPORT → browser evidence → evidence re-pin)
  **on the test site** when you say go.
- **No** AI proposal panel, quorum, import, catalog change, evidence
  re-pin, production mutation, Stage-8 work, or further batches is started
  by this note.
- Expanding beyond 48 rows requires a new exact CSV + sha256.
- Matrix row W6-2 owner box stays ☐ until you mark it.

## Owner mark-up requested

- [ ] **Approve W6-2 batch 02 only** — the 48-row CSV (sha256 above) as the
      exact next Stage 6 translation scope (Buying + Selling remainder).
- [ ] Acknowledge shared 21 technical rows remain permanent non-translation
      exclusions (unchanged).
- [ ] Acknowledge the **21** raw residual exclusions stay out of scope
      (**5 HTML + 15 `len>120` + 1 already-released**; mutually exclusive
      under cut priority — not 20).
- [ ] Leave W6-3…W6-7 unapproved until a later proposal.
- [ ] Any direct term overrides for batch strings → terminology sheet before
      a future quorum panel.
